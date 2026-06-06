from __future__ import annotations

import base64
import json
import mimetypes
import re
from datetime import date as date_cls
from pathlib import Path
from typing import Any

import asyncpg

from backend.config import get_settings


VIEW_SCHEMA = "views"
REFERENCE_SCHEMA = "reference"
ADMIN_BOUNDARY_TABLE = "通州区行政区边界"
SURVEY_SCHEMA = "survey"
SURVEY_LARVA_TABLE = "春尺蠖幼虫调查表"
GUO_HUAI_LARVA_TABLE = "国槐尺蠖幼虫调查表"
OTHER_PEST_SURVEY_TABLE = "其他害虫调查表"
MEI_GUO_BAI_E_SURVEY_TABLE = "美国白蛾第一代调查表"
SITE_SCHEMA = "sites"
SITE_TABLE = "杨树点位基础表"
SOPHORA_SITE_TABLE = "国槐点位基础表"
OTHER_PEST_SITE_TABLE = "其他害虫点位基础表"
WHITE_MOTH_SITE_TABLE = "美国白蛾点位基础表"
LOCALITY_COLUMN = "属地"
WHITE_MOTH_SITE_CODE_PATTERN = re.compile(r"^[A-Z]{2}\d{3}$")
WHITE_MOTH_SITE_CODE_EXAMPLE = "MQ001"
WHITE_MOTH_SITE_PREFIX_LOCALITIES = {
    "MQ": "马驹桥镇",
    "TH": "台湖镇",
    "ZW": "张家湾镇",
    "YF": "于家务乡",
    "YL": "永乐店镇",
    "HX": "漷县镇",
    "XJ": "西集镇",
    "LC": "潞城镇",
    "SZ": "宋庄镇",
    "YS": "永顺镇",
    "LY": "梨园镇",
    "WJ": "文景街道",
}
MAP_DYNAMIC_FILTER_COLUMNS = {
    "年份": "年份",
    "危害程度": "危害程度",
    "害虫类型": "害虫类型",
    "虫态": "虫态",
}
MAP_FILTER_VALUE_ORDER = {
    "危害程度": ["白", "无需防治", "轻", "中", "重"],
}
SURVEY_STATUS_FILTER_OPTIONS = [
    {"value": "调查", "label": "调查"},
    {"value": "未调查", "label": "未调查"},
]
SURVEY_STATUS_FILTER_VALUES = {option["value"] for option in SURVEY_STATUS_FILTER_OPTIONS}

_pool: asyncpg.Pool | None = None


class WhiteMothSiteCodeError(ValueError):
    """美国白蛾点位编号格式错误。"""


class WhiteMothSiteDuplicateError(ValueError):
    """美国白蛾点位编号重复。"""


def normalize_filter_values(value: Any) -> list[str]:
    """将单值或多值筛选条件统一为去重后的字符串列表。"""

    raw_values = value if isinstance(value, (list, tuple, set)) else [value]
    values = [
        str(item).strip()
        for item in raw_values
        if item is not None and str(item).strip() != ""
    ]
    return list(dict.fromkeys(values))


def get_white_moth_site_code_rules() -> dict[str, Any]:
    """返回美国白蛾点位编号规则。"""

    return {
        "code_pattern": r"^[A-Z]{2}\d{3}$",
        "code_example": WHITE_MOTH_SITE_CODE_EXAMPLE,
        "prefix_localities": WHITE_MOTH_SITE_PREFIX_LOCALITIES,
    }


def normalize_white_moth_site_code(value: str) -> str:
    """标准化美国白蛾点位编号。"""

    return (value or "").strip().upper()


def resolve_white_moth_site_locality(code: str) -> tuple[str, str]:
    """根据美国白蛾点位编号解析标准编号和属地。"""

    normalized_code = normalize_white_moth_site_code(code)
    if not WHITE_MOTH_SITE_CODE_PATTERN.fullmatch(normalized_code):
        raise WhiteMothSiteCodeError(
            f"编号格式不正确，请输入类似 {WHITE_MOTH_SITE_CODE_EXAMPLE} 的编号"
        )

    prefix = normalized_code[:2]
    locality = WHITE_MOTH_SITE_PREFIX_LOCALITIES.get(prefix)
    if locality is None:
        raise WhiteMothSiteCodeError(
            f"编号格式不正确，请输入类似 {WHITE_MOTH_SITE_CODE_EXAMPLE} 的编号"
        )

    return normalized_code, locality


async def ensure_pool() -> asyncpg.Pool:
    """按需初始化 asyncpg 连接池。"""

    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=1,
            max_size=6,
            command_timeout=60,
        )
    return _pool


async def close_pool() -> None:
    """关闭数据库连接池。"""

    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


async def fetch(query: str, *args: Any) -> list[asyncpg.Record]:
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        return await connection.fetch(query, *args)


async def fetchrow(query: str, *args: Any) -> asyncpg.Record | None:
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        return await connection.fetchrow(query, *args)


async def list_map_views() -> list[dict[str, Any]]:
    """列出可用于地图展示的视图。"""

    rows = await fetch(
        """
        SELECT
            v.table_name AS name,
            ARRAY_AGG(c.column_name ORDER BY c.ordinal_position)
                FILTER (WHERE c.column_name <> 'geom') AS columns
        FROM information_schema.views AS v
        JOIN information_schema.columns AS c
          ON c.table_schema = v.table_schema
         AND c.table_name = v.table_name
        WHERE v.table_schema = $1
        GROUP BY v.table_name
        HAVING BOOL_OR(c.column_name = 'geom')
        ORDER BY v.table_name
        """,
        VIEW_SCHEMA,
    )
    return [
        {
            "name": row["name"],
            "columns": list(row["columns"] or []),
        }
        for row in rows
    ]


async def get_map_view(view_name: str) -> dict[str, Any] | None:
    views = await list_map_views()
    for view in views:
        if view["name"] == view_name:
            return view
    return None


async def list_reference_layers() -> list[dict[str, Any]]:
    """列出 reference schema 下可叠加展示的空间表。"""

    rows = await fetch(
        """
        SELECT
            t.table_name AS name,
            COALESCE(
                obj_description(
                    (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass,
                    'pg_class'
                ),
                t.table_name
            ) AS label,
            ARRAY_AGG(c.column_name ORDER BY c.ordinal_position)
                FILTER (WHERE c.column_name <> 'geom') AS columns
        FROM information_schema.tables AS t
        JOIN information_schema.columns AS c
          ON c.table_schema = t.table_schema
         AND c.table_name = t.table_name
        WHERE t.table_schema = $1
          AND t.table_type = 'BASE TABLE'
        GROUP BY t.table_schema, t.table_name
        HAVING BOOL_OR(c.column_name = 'geom')
        ORDER BY t.table_name
        """,
        REFERENCE_SCHEMA,
    )
    return [
        {
            "name": row["name"],
            "label": row["label"] or row["name"],
            "columns": list(row["columns"] or []),
            "default_visible": row["name"] == ADMIN_BOUNDARY_TABLE,
        }
        for row in rows
    ]


async def get_reference_layer(layer_name: str) -> dict[str, Any] | None:
    layers = await list_reference_layers()
    for layer in layers:
        if layer["name"] == layer_name:
            return layer
    return None


def sort_filter_values(column: str, values: list[str]) -> list[str]:
    """按业务习惯排序地图筛选项。"""

    if column == "年份":
        return sorted(
            values,
            key=lambda value: (0, int(value)) if value.isdigit() else (1, value),
        )

    value_order = MAP_FILTER_VALUE_ORDER.get(column)
    if value_order:
        order_index = {value: index for index, value in enumerate(value_order)}
        return sorted(values, key=lambda value: (order_index.get(value, 999), value))

    return sorted(values)


async def fetch_distinct_filter_values(qualified_view: str, column: str) -> list[str]:
    """读取指定视图字段的非空去重值。"""

    quoted_column = quote_identifier(column)
    rows = await fetch(
        f"""
        SELECT DISTINCT BTRIM({quoted_column}::text) AS value
        FROM {qualified_view}
        WHERE {quoted_column} IS NOT NULL
          AND BTRIM({quoted_column}::text) <> ''
        """,
    )
    values = [row["value"] for row in rows if row["value"]]
    return sort_filter_values(column, values)


def build_select_filter_field(
    key: str,
    label: str,
    options: list[str] | list[dict[str, str]],
    default_value: str = "",
) -> dict[str, Any]:
    normalized_options = [
        option
        if isinstance(option, dict)
        else {
            "value": option,
            "label": option,
        }
        for option in options
    ]
    return {
        "key": key,
        "label": label,
        "type": "select",
        "options": normalized_options,
        "default_value": default_value,
    }


def resolve_filter_default_value(column: str, values: list[str]) -> str:
    if column == "年份" and values:
        return values[-1]
    return ""


def records_to_feature_collection(rows: list[asyncpg.Record]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(row["geom_json"]) if row["geom_json"] else None,
                "properties": (
                    json.loads(row["properties"])
                    if isinstance(row["properties"], str)
                    else dict(row["properties"] or {})
                ),
            }
            for row in rows
        ],
    }


async def fetch_admin_boundary_feature_collection() -> dict[str, Any]:
    """读取行政区边界并返回标准 GeoJSON。"""

    return await fetch_reference_layer_feature_collection(ADMIN_BOUNDARY_TABLE)


async def fetch_reference_layer_feature_collection(layer_name: str) -> dict[str, Any]:
    """读取 reference schema 指定空间表并返回标准 GeoJSON。"""

    layer = await get_reference_layer(layer_name)
    if layer is None:
        raise ValueError(f"参考图层不存在：{layer_name}")

    qualified_table = f"{quote_identifier(REFERENCE_SCHEMA)}.{quote_identifier(layer_name)}"
    rows = await fetch(
        f"""
        SELECT
            ST_AsGeoJSON(
                CASE
                    WHEN ST_SRID(t.geom) = 4326 THEN t.geom
                    WHEN ST_SRID(t.geom) = 0 THEN ST_SetSRID(t.geom, 4326)
                    ELSE ST_Transform(t.geom, 4326)
                END
            ) AS geom_json,
            to_jsonb(t) - 'geom' AS properties
        FROM {qualified_table} AS t
        WHERE t.geom IS NOT NULL
        """,
    )
    return records_to_feature_collection(rows)


async def create_white_moth_site(
    *,
    code: str,
    site_name: str,
    longitude: float,
    latitude: float,
) -> dict[str, Any]:
    """新增美国白蛾点位。"""

    normalized_code, locality = resolve_white_moth_site_locality(code)
    qualified_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(WHITE_MOTH_SITE_TABLE)}"
    )

    try:
        row = await fetchrow(
            f"""
            INSERT INTO {qualified_table} (
                "编号",
                {quote_identifier(LOCALITY_COLUMN)},
                "点位名称",
                geom
            )
            VALUES (
                $1,
                $2,
                $3,
                ST_SetSRID(ST_MakePoint($4, $5), 4326)
            )
            RETURNING
                gid,
                "编号" AS code,
                {quote_identifier(LOCALITY_COLUMN)} AS locality,
                COALESCE("点位名称", '') AS site_name,
                ST_X(geom) AS longitude,
                ST_Y(geom) AS latitude
            """,
            normalized_code,
            locality,
            (site_name or "").strip(),
            longitude,
            latitude,
        )
    except asyncpg.UniqueViolationError as exc:
        raise WhiteMothSiteDuplicateError(f"编号已存在：{normalized_code}") from exc

    return dict(row or {})


async def fetch_map_filter_options(view_name: str) -> dict[str, Any]:
    """读取指定视图的筛选选项。"""

    view = await get_map_view(view_name)
    if view is None:
        raise ValueError(f"视图不存在：{view_name}")

    columns = set(view["columns"])
    qualified_view = f"{quote_identifier(VIEW_SCHEMA)}.{quote_identifier(view_name)}"

    localities: list[str] = []
    filter_fields: list[dict[str, Any]] = []
    if LOCALITY_COLUMN in columns:
        localities = await fetch_distinct_filter_values(qualified_view, LOCALITY_COLUMN)
        filter_fields.append(
            build_select_filter_field(
                key=LOCALITY_COLUMN,
                label=LOCALITY_COLUMN,
                options=localities,
            )
        )

    if "调查日期" in columns:
        filter_fields.append(
            build_select_filter_field(
                key="调查状态",
                label="调查状态",
                options=SURVEY_STATUS_FILTER_OPTIONS,
            )
        )

    for column, label in MAP_DYNAMIC_FILTER_COLUMNS.items():
        if column not in columns:
            continue
        values = await fetch_distinct_filter_values(qualified_view, column)
        if not values:
            continue
        filter_fields.append(
            build_select_filter_field(
                key=column,
                label=label,
                options=values,
                default_value=resolve_filter_default_value(column, values),
            )
        )

    return {
        "localities": localities,
        "supports_locality_filter": LOCALITY_COLUMN in columns,
        "supports_survey_status_filter": "调查日期" in columns,
        "filter_fields": filter_fields,
    }


async def fetch_view_feature_collection(
    view_name: str,
    filters: dict[str, str | list[str]] | None = None,
) -> dict[str, Any]:
    """读取指定视图并返回标准 GeoJSON。"""

    view = await get_map_view(view_name)
    if view is None:
        raise ValueError(f"视图不存在：{view_name}")

    allowed_columns = set(view["columns"])
    filters = filters or {}

    where_clauses: list[str] = []
    args: list[Any] = []
    for column, raw_value in filters.items():
        values = normalize_filter_values(raw_value)
        if column == "调查状态":
            if "调查日期" not in allowed_columns or not values:
                continue
            unsupported_values = [
                value for value in values if value not in SURVEY_STATUS_FILTER_VALUES
            ]
            if unsupported_values:
                raise ValueError(f"不支持的调查状态：{unsupported_values[0]}")
            if {"调查", "未调查"}.issubset(values):
                continue
            if "调查" in values:
                where_clauses.append(f'{quote_identifier("调查日期")} IS NOT NULL')
                continue
            if "未调查" in values:
                where_clauses.append(f'{quote_identifier("调查日期")} IS NULL')
                continue
        if column not in allowed_columns:
            raise ValueError(f"不支持的过滤字段：{column}")
        if not values:
            continue
        args.append(values)
        where_clauses.append(
            f"BTRIM({quote_identifier(column)}::text) = ANY(${len(args)}::text[])"
        )

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    qualified_view = f"{quote_identifier(VIEW_SCHEMA)}.{quote_identifier(view_name)}"
    rows = await fetch(
        f"""
        SELECT
            ST_AsGeoJSON(ST_Transform(t.geom, 4326)) AS geom_json,
            to_jsonb(t) - 'geom' AS properties
        FROM (
            SELECT *
            FROM {qualified_view}
            {where_sql}
        ) AS t
        """,
        *args,
    )

    return records_to_feature_collection(rows)


def build_chi_huo_larva_description(
    pest_name: str,
    locality: str,
    location_name: str,
    location_id: str,
    damage_level: str,
    total_insect_count: int | None,
) -> str:
    """根据点位信息与危害程度生成尺蠖幼虫防治描述。"""

    location_prefix = "".join(
        part.strip()
        for part in [locality, location_name, location_id]
        if (part or "").strip()
    )
    location_text = f"{location_prefix}点位，" if location_prefix else ""
    normalized_level = (damage_level or "").strip()
    level_text = normalized_level or "待判定"
    average_insect_count_text = "未记录"
    if total_insect_count is not None:
        average_insect_count_text = f"{(total_insect_count + 4) // 5}头"

    if normalized_level == "重":
        advice = "建议立即组织防治作业，并优先复核周边相邻点位。"
    elif normalized_level == "中":
        advice = "建议尽快安排防治，并持续跟踪虫情变化。"
    elif normalized_level == "轻":
        advice = "建议加强巡查，视虫情发展适时处置。"
    elif normalized_level:
        advice = "建议结合现场情况制定防治措施并复核虫情。"
    else:
        advice = "建议复核现场危害情况并及时补录调查结果。"

    return (
        f"{location_text}调查发现{pest_name}幼虫危害程度为{level_text}，"
        f"平均每标准枝{average_insect_count_text}。{advice}"
    )


def build_spring_inchworm_description(
    locality: str,
    location_name: str,
    location_id: str,
    damage_level: str,
    total_insect_count: int | None,
) -> str:
    """根据点位信息与危害程度生成春尺蠖防治描述。"""

    return build_chi_huo_larva_description(
        pest_name="春尺蠖",
        locality=locality,
        location_name=location_name,
        location_id=location_id,
        damage_level=damage_level,
        total_insect_count=total_insect_count,
    )


def build_guo_huai_inchworm_description(
    locality: str,
    location_name: str,
    location_id: str,
    damage_level: str,
    total_insect_count: int | None,
) -> str:
    """根据点位信息与危害程度生成国槐尺蠖防治描述。"""

    return build_chi_huo_larva_description(
        pest_name="国槐尺蠖",
        locality=locality,
        location_name=location_name,
        location_id=location_id,
        damage_level=damage_level,
        total_insect_count=total_insect_count,
    )


def serialize_date_value(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def build_point_screenshot_index(screenshot_dir: Path) -> dict[str, Path]:
    """扫描本地点位截图目录，返回可唯一匹配的点位截图索引。"""

    if not screenshot_dir.exists() or not screenshot_dir.is_dir():
        return {}

    indexed_paths: dict[str, list[Path]] = {}
    for path in sorted(screenshot_dir.iterdir()):
        if not path.is_file():
            continue

        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type or not mime_type.startswith("image/"):
            continue

        location_id = path.stem.strip()
        if not location_id:
            continue

        indexed_paths.setdefault(location_id, []).append(path)

    return {
        location_id: paths[0]
        for location_id, paths in indexed_paths.items()
        if len(paths) == 1
    }


def encode_image_as_data_url(image_path: Path) -> str | None:
    """读取本地图片并编码为前端可直接使用的 Data URL。"""

    mime_type, _ = mimetypes.guess_type(image_path.name)
    if not mime_type or not mime_type.startswith("image/"):
        return None

    try:
        content = image_path.read_bytes()
    except OSError:
        return None

    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def load_point_screenshot_images(
    location_id: str,
    screenshot_index: dict[str, Path],
) -> list[str]:
    """按点位编号匹配导入记录的默认截图。"""

    normalized_location_id = (location_id or "").strip()
    if not normalized_location_id:
        return []

    image_path = screenshot_index.get(normalized_location_id)
    if image_path is None:
        return []

    data_url = encode_image_as_data_url(image_path)
    return [data_url] if data_url else []


async def fetch_survey_candidates(
    survey_date: date_cls,
    pest_type: str = "春尺蠖",
) -> list[dict[str, Any]]:
    """读取指定日期可导入为工作单的调查记录。"""

    return await fetch_survey_candidates_by_type(
        survey_date=survey_date,
        pest_type=pest_type,
    )


async def fetch_survey_candidates_by_type(
    survey_date: date_cls,
    pest_type: str,
) -> list[dict[str, Any]]:
    """按害虫类型读取指定日期的工作单导入候选记录。"""

    if pest_type == "其他害虫":
        return await fetch_other_pest_survey_candidates(survey_date)
    if pest_type == "春尺蠖":
        return await fetch_spring_inchworm_survey_candidates(survey_date)
    if pest_type == "国槐尺蠖":
        return await fetch_guo_huai_inchworm_survey_candidates(survey_date)
    if pest_type == "美国白蛾":
        return await fetch_meiguobaie_survey_candidates(survey_date)
    raise ValueError(f"暂不支持 {pest_type} 的调查导入")


async def fetch_spring_inchworm_survey_candidates(
    survey_date: date_cls,
) -> list[dict[str, Any]]:
    """读取指定日期的春尺蠖调查导入候选记录。"""

    qualified_larva_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(SURVEY_LARVA_TABLE)}"
    )
    qualified_site_table = f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(SITE_TABLE)}"

    rows = await fetch(
        f"""
        SELECT
            l."编号" AS location_id,
            l."调查日期" AS survey_date,
            l."总虫口数" AS total_insect_count,
            BTRIM(l."危害程度") AS damage_level,
            COALESCE(l."备注", '') AS note,
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(s."村", '') AS location_name
        FROM {qualified_larva_table} AS l
        JOIN {qualified_site_table} AS s
          ON l."编号" = s."编号"
        WHERE l."调查日期" = $1
          AND l."危害程度" IS NOT NULL
          AND BTRIM(l."危害程度") NOT IN ('', '白')
        ORDER BY
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, ''),
            l."编号"
        """,
        survey_date,
    )

    screenshot_index = build_point_screenshot_index(get_settings().point_screenshot_dir)
    candidates: list[dict[str, Any]] = []
    for row in rows:
        location_id = str(row["location_id"] or "").strip()
        locality = (row["locality"] or "").strip()
        location_name = (row["location_name"] or "").strip()
        insect_count = row["total_insect_count"]
        if insect_count is not None:
            insect_count = int(insect_count)

        damage_level = (row["damage_level"] or "").strip()
        candidates.append(
            {
                "survey_date": serialize_date_value(row["survey_date"]),
                "locality": locality,
                "location_id": location_id,
                "location_name": location_name,
                "total_insect_count": insect_count,
                "damage_level": damage_level,
                "note": (row["note"] or "").strip(),
                "images": load_point_screenshot_images(location_id, screenshot_index),
                "description": build_spring_inchworm_description(
                    locality=locality,
                    location_name=location_name,
                    location_id=location_id,
                    damage_level=damage_level,
                    total_insect_count=insect_count,
                ),
            }
        )

    return candidates


async def fetch_guo_huai_inchworm_survey_candidates(
    survey_date: date_cls,
) -> list[dict[str, Any]]:
    """读取指定日期的国槐尺蠖调查导入候选记录。"""

    qualified_larva_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(GUO_HUAI_LARVA_TABLE)}"
    )
    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(SOPHORA_SITE_TABLE)}"
    )

    rows = await fetch(
        f"""
        SELECT
            l."编号" AS location_id,
            l."调查日期" AS survey_date,
            l."总虫口数" AS total_insect_count,
            BTRIM(l."危害程度") AS damage_level,
            COALESCE(l."备注", '') AS note,
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(s."村", '') AS location_name
        FROM {qualified_larva_table} AS l
        JOIN {qualified_site_table} AS s
          ON l."编号" = s."编号"
        WHERE l."调查日期" = $1
          AND l."危害程度" IS NOT NULL
          AND BTRIM(l."危害程度") NOT IN ('', '白', '无需防治')
        ORDER BY
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, ''),
            l."编号"
        """,
        survey_date,
    )

    screenshot_index = build_point_screenshot_index(
        get_settings().sophora_point_screenshot_dir
    )
    candidates: list[dict[str, Any]] = []
    for row in rows:
        location_id = str(row["location_id"] or "").strip()
        locality = (row["locality"] or "").strip()
        location_name = (row["location_name"] or "").strip()
        insect_count = row["total_insect_count"]
        if insect_count is not None:
            insect_count = int(insect_count)

        damage_level = (row["damage_level"] or "").strip()
        candidates.append(
            {
                "survey_date": serialize_date_value(row["survey_date"]),
                "locality": locality,
                "location_id": location_id,
                "location_name": location_name,
                "total_insect_count": insect_count,
                "damage_level": damage_level,
                "note": (row["note"] or "").strip(),
                "images": load_point_screenshot_images(location_id, screenshot_index),
                "description": build_guo_huai_inchworm_description(
                    locality=locality,
                    location_name=location_name,
                    location_id=location_id,
                    damage_level=damage_level,
                    total_insect_count=insect_count,
                ),
            }
        )

    return candidates


async def fetch_other_pest_survey_candidates(survey_date: date_cls) -> list[dict[str, Any]]:
    """读取指定日期的其他害虫调查导入候选记录。"""

    qualified_survey_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(OTHER_PEST_SURVEY_TABLE)}"
    )
    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(OTHER_PEST_SITE_TABLE)}"
    )

    rows = await fetch(
        f"""
        SELECT
            i."编号" AS location_id,
            i."调查日期" AS survey_date,
            BTRIM(i."虫害类型") AS pest_name,
            BTRIM(i."调查结论") AS survey_result,
            COALESCE(i."详细描述", '') AS description,
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(s."点位名称", '') AS location_name,
            COALESCE(s."寄主树种", '') AS host_plant,
            COALESCE(s."地块类型", '') AS plot_type
        FROM {qualified_survey_table} AS i
        JOIN {qualified_site_table} AS s
          ON i."编号" = s."编号"
        WHERE i."调查日期" = $1
          AND BTRIM(COALESCE(i."调查结论", '')) = '发现问题'
        ORDER BY
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, ''),
            i."编号",
            COALESCE(i."虫害类型", '')
        """,
        survey_date,
    )

    return [
        {
            "survey_date": serialize_date_value(row["survey_date"]),
            "locality": (row["locality"] or "").strip(),
            "location_id": str(row["location_id"] or "").strip(),
            "location_name": (row["location_name"] or "").strip(),
            "pest_name": (row["pest_name"] or "").strip(),
            "host_plant": (row["host_plant"] or "").strip(),
            "plot_type": (row["plot_type"] or "").strip(),
            "survey_result": (row["survey_result"] or "").strip(),
            "description": (row["description"] or "").strip(),
            "note": "",
            "images": [],
        }
        for row in rows
    ]


async def fetch_meiguobaie_survey_candidates(
    survey_date: date_cls,
) -> list[dict[str, Any]]:
    """读取指定日期的美国白蛾第一代调查导入候选记录。"""

    qualified_survey_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(MEI_GUO_BAI_E_SURVEY_TABLE)}"
    )

    rows = await fetch(
        f"""
        SELECT
            BTRIM(i."编号") AS location_id,
            i."调查日期" AS survey_date,
            COALESCE(NULLIF(BTRIM(i."区域"), ''), '乡镇') AS region,
            COALESCE(i.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(i."点位名称", '') AS location_name,
            COALESCE(i."发生位置", '') AS occurrence_position,
            COALESCE(i."绿地性质", '') AS green_space_type,
            COALESCE(i."危害寄主", '') AS pest_hosts,
            COALESCE(i."受害株数", 0) AS damaged_plant_count,
            COALESCE(i."网幕数量", 0) AS web_nest_count,
            COALESCE(i."详细描述", '') AS description,
            COALESCE(i."备注", '') AS note
        FROM {qualified_survey_table} AS i
        WHERE i."调查日期" = $1
          AND BTRIM(COALESCE(i."详细描述", '')) <> ''
          AND (
              COALESCE(i."受害株数", 0) > 0
              OR COALESCE(i."网幕数量", 0) > 0
          )
        ORDER BY
            COALESCE(i.{quote_identifier(LOCALITY_COLUMN)}, ''),
            BTRIM(i."编号")
        """,
        survey_date,
    )

    screenshot_index = build_point_screenshot_index(
        get_settings().meiguobaie_point_screenshot_dir
    )
    candidates: list[dict[str, Any]] = []
    for row in rows:
        location_id = str(row["location_id"] or "").strip()
        damaged_plant_count = row["damaged_plant_count"]
        web_nest_count = row["web_nest_count"]
        candidates.append(
            {
                "survey_date": serialize_date_value(row["survey_date"]),
                "region": (row["region"] or "").strip(),
                "locality": (row["locality"] or "").strip(),
                "location_id": location_id,
                "location_name": (row["location_name"] or "").strip(),
                "occurrence_position": (row["occurrence_position"] or "").strip(),
                "green_space_type": (row["green_space_type"] or "").strip(),
                "pest_hosts": (row["pest_hosts"] or "").strip(),
                "damaged_plant_count": int(damaged_plant_count or 0),
                "web_nest_count": int(web_nest_count or 0),
                "description": (row["description"] or "").strip(),
                "note": (row["note"] or "").strip(),
                "images": load_point_screenshot_images(location_id, screenshot_index),
            }
        )

    return candidates
