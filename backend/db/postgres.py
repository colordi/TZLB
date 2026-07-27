from __future__ import annotations

import base64
import json
import mimetypes
import re
from datetime import date as date_cls
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg

from backend.config import get_settings
from backend.services.pest_registry import (
    SURVEY_IMPORT_GUO_HUAI_INCHWORM,
    SURVEY_IMPORT_MEI_GUO_BAI_E,
    SURVEY_IMPORT_OTHER_PEST,
    SURVEY_IMPORT_SPRING_INCHWORM,
    get_pest_config,
)


VIEW_SCHEMA = "views"
REFERENCE_SCHEMA = "reference"
ADMIN_BOUNDARY_TABLE = "通州区行政区边界"
SURVEY_SCHEMA = "survey"
SURVEY_LARVA_TABLE = "春尺蠖幼虫调查表"
GUO_HUAI_LARVA_TABLE = "国槐尺蠖幼虫调查表"
OTHER_PEST_SURVEY_TABLE = "其他害虫调查表"
MEI_GUO_BAI_E_SURVEY_TABLE = "美国白蛾调查表"
SITE_SCHEMA = "sites"
SITE_TABLE = "杨树点位基础表"
SOPHORA_SITE_TABLE = "国槐点位基础表"
OTHER_PEST_SITE_TABLE = "其他害虫点位基础表"
WHITE_MOTH_SITE_TABLE = "美国白蛾点位基础表"
LOCALITY_COLUMN = "属地"
# 前缀 2～3 位字母 + 3 位数字；三位前缀用于区分与两位前缀的冲突（如 LY / LYI / LYU）
WHITE_MOTH_SITE_CODE_PATTERN = re.compile(r"^[A-Z]{2,3}\d{3}$")
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
    "YZ": "杨庄街道",
    "YQ": "玉桥街道",
    "LY": "梨园镇",
    "WJ": "文景街道",
    "JK": "九棵树街道",
    "ZC": "中仓街道",
    "XH": "新华街道",
    "LYI": "潞邑街道",
    "LYU": "潞源街道",
    "BY": "北苑街道",
    "TY": "通运街道",
    "LH": "临河里街道",
}
# 其他害虫点位编号固定 QT 前缀 + 4 位序号（与现有数据一致），编号不含属地信息
OTHER_PEST_SITE_CODE_PREFIX = "QT"
OTHER_PEST_SITE_CODE_PATTERN = re.compile(r"^QT\d{4}$")
OTHER_PEST_SITE_CODE_EXAMPLE = "QT0001"
OTHER_PEST_SITE_CODE_SERIAL_WIDTH = 4
OTHER_PEST_SITE_LOCALITIES = tuple(dict.fromkeys(WHITE_MOTH_SITE_PREFIX_LOCALITIES.values()))
MAP_DYNAMIC_FILTER_COLUMNS = {
    "年份": "年份",
    "世代": "世代",
    "危害程度": "危害程度",
    "害虫类型": "害虫类型",
    "虫态": "虫态",
}
MAP_FILTER_VALUE_ORDER = {
    "危害程度": ["白", "无需防治", "轻", "中", "重"],
    "世代": ["第一代", "第二代", "第三代"],
}
MAP_POINT_DEDUPE_KEYS = ("编号", "点位编号", "location_id", "locationId")
MAP_SURVEY_DATE_KEYS = ("调查日期", "survey_date", "report_time")
SURVEY_STATUS_FILTER_OPTIONS = [
    {"value": "调查", "label": "调查"},
    {"value": "未调查", "label": "未调查"},
]
SURVEY_STATUS_FILTER_KEY = "调查状态"
SURVEY_STATUS_FILTER_VALUES = {option["value"] for option in SURVEY_STATUS_FILTER_OPTIONS}
MAP_MAX_LIMIT = 5000
BBox = tuple[float, float, float, float]

_pool: asyncpg.Pool | None = None


class WhiteMothSiteCodeError(ValueError):
    """美国白蛾点位编号格式错误。"""


class WhiteMothSiteDuplicateError(ValueError):
    """美国白蛾点位编号重复。"""


class OtherPestSiteCodeError(ValueError):
    """其他害虫点位编号或属地错误。"""


class OtherPestSiteDuplicateError(ValueError):
    """其他害虫点位编号重复。"""


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
        "code_pattern": WHITE_MOTH_SITE_CODE_PATTERN.pattern,
        "code_example": WHITE_MOTH_SITE_CODE_EXAMPLE,
        "prefix_localities": WHITE_MOTH_SITE_PREFIX_LOCALITIES,
    }


def normalize_white_moth_site_code(value: str) -> str:
    """标准化美国白蛾点位编号。"""

    return (value or "").strip().upper()


def resolve_white_moth_site_prefix(prefix: str) -> tuple[str, str]:
    """解析已知编号前缀及其属地。"""

    normalized_prefix = normalize_white_moth_site_code(prefix)
    locality = WHITE_MOTH_SITE_PREFIX_LOCALITIES.get(normalized_prefix)
    if locality is None:
        raise WhiteMothSiteCodeError(
            f"未知编号前缀，请输入类似 {WHITE_MOTH_SITE_CODE_EXAMPLE} 的编号"
        )
    return normalized_prefix, locality


def resolve_white_moth_site_locality(code: str) -> tuple[str, str]:
    """根据美国白蛾点位编号解析标准编号和属地。"""

    normalized_code = normalize_white_moth_site_code(code)
    if not WHITE_MOTH_SITE_CODE_PATTERN.fullmatch(normalized_code):
        raise WhiteMothSiteCodeError(
            f"编号格式不正确，请输入类似 {WHITE_MOTH_SITE_CODE_EXAMPLE} 的编号"
        )

    # 字母前缀整体匹配（支持 2～3 位，避免 LYI 被误判为 LY）
    prefix_match = re.fullmatch(r"([A-Z]{2,3})\d{3}", normalized_code)
    prefix = prefix_match.group(1) if prefix_match else ""
    locality = WHITE_MOTH_SITE_PREFIX_LOCALITIES.get(prefix)
    if locality is None:
        raise WhiteMothSiteCodeError(
            f"编号格式不正确，请输入类似 {WHITE_MOTH_SITE_CODE_EXAMPLE} 的编号"
        )

    return normalized_code, locality


async def get_white_moth_site_code_hint(prefix: str) -> dict[str, Any]:
    """按编号前缀返回该属地当前最大编号与建议下一编号。"""

    normalized_prefix, locality = resolve_white_moth_site_prefix(prefix)
    qualified_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(WHITE_MOTH_SITE_TABLE)}"
    )
    escaped_prefix = re.escape(normalized_prefix)
    code_pattern = f"^{escaped_prefix}[0-9]{{3}}$"
    serial_pattern = f"^{escaped_prefix}([0-9]{{3}})$"

    row = await fetchrow(
        f"""
        SELECT MAX(CAST(substring("编号" FROM $1) AS integer)) AS max_serial
        FROM {qualified_table}
        WHERE "编号" ~ $2
        """,
        serial_pattern,
        code_pattern,
    )
    max_serial = row["max_serial"] if row else None
    if max_serial is None:
        return {
            "prefix": normalized_prefix,
            "locality": locality,
            "latest_code": None,
            "latest_serial": None,
            "suggested_next_code": f"{normalized_prefix}001",
        }

    next_serial = int(max_serial) + 1
    return {
        "prefix": normalized_prefix,
        "locality": locality,
        "latest_code": f"{normalized_prefix}{int(max_serial):03d}",
        "latest_serial": int(max_serial),
        "suggested_next_code": (
            f"{normalized_prefix}{next_serial:03d}" if next_serial <= 999 else None
        ),
    }


def get_other_pest_site_code_rules() -> dict[str, Any]:
    """返回其他害虫点位编号规则与可选属地列表。"""

    return {
        "code_pattern": OTHER_PEST_SITE_CODE_PATTERN.pattern,
        "code_example": OTHER_PEST_SITE_CODE_EXAMPLE,
        "code_prefix": OTHER_PEST_SITE_CODE_PREFIX,
        "localities": list(OTHER_PEST_SITE_LOCALITIES),
    }


def normalize_other_pest_site_code(value: str) -> str:
    """标准化其他害虫点位编号。"""

    return (value or "").strip().upper()


def validate_other_pest_site(code: str, locality: str) -> tuple[str, str]:
    """校验其他害虫点位编号格式与属地合法性，返回标准化后的（编号, 属地）。"""

    normalized_code = normalize_other_pest_site_code(code)
    if not OTHER_PEST_SITE_CODE_PATTERN.fullmatch(normalized_code):
        raise OtherPestSiteCodeError(
            f"编号格式不正确，请输入类似 {OTHER_PEST_SITE_CODE_EXAMPLE} 的编号"
        )

    normalized_locality = (locality or "").strip()
    if normalized_locality not in OTHER_PEST_SITE_LOCALITIES:
        raise OtherPestSiteCodeError("属地不合法，请从列表中选择乡镇街道")

    return normalized_code, normalized_locality


async def get_other_pest_site_code_hint() -> dict[str, Any]:
    """返回其他害虫点位当前最大编号与建议下一编号（QT 固定前缀）。"""

    qualified_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(OTHER_PEST_SITE_TABLE)}"
    )
    width = OTHER_PEST_SITE_CODE_SERIAL_WIDTH
    code_pattern = f"^{OTHER_PEST_SITE_CODE_PREFIX}[0-9]{{{width}}}$"
    serial_pattern = f"^{OTHER_PEST_SITE_CODE_PREFIX}([0-9]{{{width}}})$"

    row = await fetchrow(
        f"""
        SELECT MAX(CAST(substring("编号" FROM $1) AS integer)) AS max_serial
        FROM {qualified_table}
        WHERE "编号" ~ $2
        """,
        serial_pattern,
        code_pattern,
    )
    max_serial = row["max_serial"] if row else None
    max_serial_allowed = 10**width - 1
    if max_serial is None:
        return {
            "prefix": OTHER_PEST_SITE_CODE_PREFIX,
            "latest_code": None,
            "latest_serial": None,
            "suggested_next_code": f"{OTHER_PEST_SITE_CODE_PREFIX}{1:0{width}d}",
        }

    next_serial = int(max_serial) + 1
    return {
        "prefix": OTHER_PEST_SITE_CODE_PREFIX,
        "latest_code": f"{OTHER_PEST_SITE_CODE_PREFIX}{int(max_serial):0{width}d}",
        "latest_serial": int(max_serial),
        "suggested_next_code": (
            f"{OTHER_PEST_SITE_CODE_PREFIX}{next_serial:0{width}d}"
            if next_serial <= max_serial_allowed
            else None
        ),
    }


async def _init_connection(connection: asyncpg.Connection) -> None:
    """注册 JSONB codec，使 JSONB 列自动解码为 Python dict/list。"""

    await connection.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


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
            init=_init_connection,
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


def normalize_map_dedupe_value(value: Any) -> str:
    return str(value if value is not None else "").strip()


def resolve_map_feature_dedupe_key(feature: dict[str, Any]) -> str:
    properties = feature.get("properties") or {}
    for key in MAP_POINT_DEDUPE_KEYS:
        value = normalize_map_dedupe_value(properties.get(key))
        if value:
            return f"point:{value}"

    geometry = feature.get("geometry")
    if geometry:
        return f"geometry:{json.dumps(geometry, ensure_ascii=False, sort_keys=True)}"

    return ""


def resolve_map_feature_survey_date(properties: dict[str, Any]) -> str:
    for key in MAP_SURVEY_DATE_KEYS:
        value = properties.get(key)
        if value is None:
            continue
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date_cls):
            return value.isoformat()
        normalized = str(value).strip()
        if normalized:
            return normalized
    return ""


def count_non_empty_map_properties(properties: dict[str, Any]) -> int:
    return sum(
        1
        for value in properties.values()
        if value is not None and str(value).strip() != ""
    )


def map_feature_rank(feature: dict[str, Any]) -> tuple[int, str, int]:
    properties = feature.get("properties") or {}
    survey_date = resolve_map_feature_survey_date(properties)
    return (
        1 if survey_date else 0,
        survey_date,
        count_non_empty_map_properties(properties),
    )


def dedupe_map_features(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped_features: list[dict[str, Any]] = []
    feature_indexes_by_key: dict[str, int] = {}

    for feature in features:
        key = resolve_map_feature_dedupe_key(feature)
        if not key:
            deduped_features.append(feature)
            continue

        existing_index = feature_indexes_by_key.get(key)
        if existing_index is None:
            feature_indexes_by_key[key] = len(deduped_features)
            deduped_features.append(feature)
            continue

        if map_feature_rank(feature) > map_feature_rank(deduped_features[existing_index]):
            deduped_features[existing_index] = feature

    return deduped_features


def records_to_feature_collection(
    rows: list[asyncpg.Record],
    *,
    dedupe_features: bool = False,
) -> dict[str, Any]:
    features = [
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
    ]

    return {
        "type": "FeatureCollection",
        "features": dedupe_map_features(features) if dedupe_features else features,
    }


def normalized_geom_expression(alias: str = "t") -> str:
    return f"""
        CASE
            WHEN ST_SRID({alias}.geom) = 4326 THEN {alias}.geom
            WHEN ST_SRID({alias}.geom) = 0 THEN ST_SetSRID({alias}.geom, 4326)
            ELSE ST_Transform({alias}.geom, 4326)
        END
    """


def build_bbox_clause(arg_start_index: int) -> str:
    return f"""
        ST_Intersects(
            {normalized_geom_expression("t")},
            ST_MakeEnvelope(
                ${arg_start_index},
                ${arg_start_index + 1},
                ${arg_start_index + 2},
                ${arg_start_index + 3},
                4326
            )
        )
    """


def add_feature_collection_metadata(
    payload: dict[str, Any],
    *,
    has_more: bool,
    limit: int | None,
) -> dict[str, Any]:
    payload["has_more"] = has_more
    payload["limit"] = limit
    payload["returned_count"] = len(payload.get("features") or [])
    return payload


async def fetch_admin_boundary_feature_collection() -> dict[str, Any]:
    """读取行政区边界并返回标准 GeoJSON。"""

    return await fetch_reference_layer_feature_collection(ADMIN_BOUNDARY_TABLE)


async def fetch_reference_layer_feature_collection(
    layer_name: str,
    *,
    bbox: BBox | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """读取 reference schema 指定空间表并返回标准 GeoJSON。"""

    layer = await get_reference_layer(layer_name)
    if layer is None:
        raise ValueError(f"参考图层不存在：{layer_name}")

    qualified_table = f"{quote_identifier(REFERENCE_SCHEMA)}.{quote_identifier(layer_name)}"
    where_clauses = ["t.geom IS NOT NULL"]
    args: list[Any] = []
    if bbox is not None:
        args.extend(bbox)
        where_clauses.append(build_bbox_clause(len(args) - 3))
    if limit is not None:
        args.append(limit + 1)
    where_sql = " AND ".join(where_clauses)
    limit_clause = f" LIMIT ${len(args)}" if limit is not None else ""
    rows = await fetch(
        f"""
        SELECT
            ST_AsGeoJSON({normalized_geom_expression("t")}) AS geom_json,
            to_jsonb(t) - 'geom' AS properties
        FROM {qualified_table} AS t
        WHERE {where_sql}{limit_clause}
        """,
        *args,
    )
    has_more = limit is not None and len(rows) > limit
    features = rows if limit is None else rows[:limit]
    return add_feature_collection_metadata(
        records_to_feature_collection(features),
        has_more=has_more,
        limit=limit,
    )


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


async def create_other_pest_site(
    *,
    code: str,
    site_name: str,
    locality: str,
    longitude: float,
    latitude: float,
) -> dict[str, Any]:
    """新增其他害虫点位。编号无唯一约束，插入前显式查重。"""

    normalized_code, normalized_locality = validate_other_pest_site(code, locality)
    qualified_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(OTHER_PEST_SITE_TABLE)}"
    )

    existing = await fetchrow(
        f"""
        SELECT 1
        FROM {qualified_table}
        WHERE "编号" = $1
        LIMIT 1
        """,
        normalized_code,
    )
    if existing is not None:
        raise OtherPestSiteDuplicateError(f"编号已存在：{normalized_code}")

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
        normalized_locality,
        (site_name or "").strip(),
        longitude,
        latitude,
    )

    return dict(row or {})


async def check_white_moth_site_deletion(code: str) -> dict[str, Any] | None:
    """删除前检查美国白蛾点位：返回点位信息与关联调查记录数。点位不存在返回 None。"""

    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(WHITE_MOTH_SITE_TABLE)}"
    )
    qualified_survey_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(MEI_GUO_BAI_E_SURVEY_TABLE)}"
    )

    row = await fetchrow(
        f"""
        SELECT
            s."编号" AS code,
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(s."点位名称", '') AS site_name,
            ST_X(s.geom) AS longitude,
            ST_Y(s.geom) AS latitude,
            COUNT(i."编号") AS survey_record_count
        FROM {qualified_site_table} AS s
        LEFT JOIN {qualified_survey_table} AS i
          ON BTRIM(i."编号") = s."编号"
        WHERE s."编号" = $1
        GROUP BY s."编号", s.{quote_identifier(LOCALITY_COLUMN)}, s."点位名称", s.geom
        """,
        code,
    )
    if row is None:
        return None
    return {
        "code": row["code"],
        "locality": row["locality"],
        "site_name": row["site_name"],
        "longitude": row["longitude"],
        "latitude": row["latitude"],
        "survey_record_count": row["survey_record_count"],
    }


async def delete_white_moth_site(*, code: str, operator: dict[str, Any]) -> dict[str, Any] | None:
    """删除美国白蛾点位并在同一事务内写入操作日志。点位不存在返回 None。"""

    from backend.db.admin import (
        ADMIN_SCHEMA,
        OPERATION_LOG_ACTION_DELETE_WHITE_MOTH_SITE,
        OPERATION_LOG_TABLE,
        ensure_operation_log_storage,
    )

    await ensure_operation_log_storage()

    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(WHITE_MOTH_SITE_TABLE)}"
    )
    qualified_survey_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(MEI_GUO_BAI_E_SURVEY_TABLE)}"
    )
    qualified_log_table = (
        f'"{ADMIN_SCHEMA}"."{OPERATION_LOG_TABLE}"'
    )

    operator_id = operator.get("id")
    operator_username = operator.get("username") or ""
    operator_display_name = operator.get("display_name") or ""
    operator_role = operator.get("role") or ""

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            deleted = await connection.fetchrow(
                f"""
                DELETE FROM {qualified_site_table}
                WHERE "编号" = $1
                RETURNING
                    gid,
                    "编号" AS code,
                    COALESCE({quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
                    COALESCE("点位名称", '') AS site_name,
                    ST_X(geom) AS longitude,
                    ST_Y(geom) AS latitude
                """,
                code,
            )
            if deleted is None:
                return None

            survey_count_row = await connection.fetchrow(
                f"""
                SELECT COUNT(*) AS survey_record_count
                FROM {qualified_survey_table}
                WHERE BTRIM("编号") = $1
                """,
                code,
            )
            survey_record_count = (
                survey_count_row["survey_record_count"] if survey_count_row else 0
            )

            await connection.execute(
                f"""
                INSERT INTO {qualified_log_table} (
                    action,
                    operator_id,
                    operator_username,
                    operator_display_name,
                    operator_role,
                    site_code,
                    site_name,
                    locality,
                    longitude,
                    latitude,
                    survey_record_count
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                OPERATION_LOG_ACTION_DELETE_WHITE_MOTH_SITE,
                operator_id,
                operator_username,
                operator_display_name,
                operator_role,
                deleted["code"],
                deleted["site_name"],
                deleted["locality"],
                deleted["longitude"],
                deleted["latitude"],
                survey_record_count,
            )

            return {
                "code": deleted["code"],
                "site_name": deleted["site_name"],
                "locality": deleted["locality"],
                "longitude": deleted["longitude"],
                "latitude": deleted["latitude"],
                "survey_record_count": survey_record_count,
            }


async def fetch_map_filter_options(
    view_name: str,
    filters: dict[str, str | list[str]] | None = None,
) -> dict[str, Any]:
    """读取指定视图的筛选选项。

    filters 为当前生效的筛选条件（如年份、世代），调查状态计数会在该
    条件下统计；调查状态本身不作为统计条件，保证计数体现可筛选的全量。
    """

    view = await get_map_view(view_name)
    if view is None:
        raise ValueError(f"视图不存在：{view_name}")

    columns = set(view["columns"])
    qualified_view = f"{quote_identifier(VIEW_SCHEMA)}.{quote_identifier(view_name)}"

    localities: list[str] = []
    filter_fields: list[dict[str, Any]] = []
    survey_status_counts = {"all": 0, "completed": 0, "pending": 0}
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
        count_filters = {
            key: value
            for key, value in (filters or {}).items()
            if key != SURVEY_STATUS_FILTER_KEY
        }
        survey_status_counts = await fetch_survey_status_counts(
            view_name,
            view,
            count_filters,
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
        "survey_status_counts": survey_status_counts,
        "filter_fields": filter_fields,
    }


def build_map_view_filter_clauses(
    allowed_columns: set[str],
    filters: dict[str, str | list[str]] | None,
    args: list[Any],
) -> list[str]:
    filters = filters or {}
    where_clauses: list[str] = []

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

    return where_clauses


async def fetch_survey_status_counts(
    view_name: str,
    view: dict[str, Any],
    filters: dict[str, str | list[str]] | None = None,
) -> dict[str, int]:
    """按去重后的点位统计调查状态。

    先在 filters（如年份、世代）条件下取出记录，按点位去重（与地图
    展示逻辑一致，每个点位只保留最优记录），再根据去重后记录的调查
    日期分类，保证 all = completed + pending。
    """

    allowed_columns = set(view["columns"])
    args: list[Any] = []
    where_clauses = build_map_view_filter_clauses(allowed_columns, filters, args)
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    qualified_view = f"{quote_identifier(VIEW_SCHEMA)}.{quote_identifier(view_name)}"
    rows = await fetch(
        f"""
        SELECT
            ST_AsGeoJSON(ST_Transform(t.geom, 4326)) AS geom_json,
            to_jsonb(t) - 'geom' AS properties
        FROM (
            SELECT *
            FROM {qualified_view} AS t
            {where_sql}
        ) AS t
        """,
        *args,
    )
    features = (
        records_to_feature_collection(rows, dedupe_features=True).get("features") or []
    )
    completed = sum(
        1
        for feature in features
        if resolve_map_feature_survey_date(feature.get("properties") or {})
    )
    return {
        "all": len(features),
        "completed": completed,
        "pending": len(features) - completed,
    }


async def fetch_view_feature_collection(
    view_name: str,
    filters: dict[str, str | list[str]] | None = None,
    *,
    bbox: BBox | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """读取指定视图并返回标准 GeoJSON。"""

    view = await get_map_view(view_name)
    if view is None:
        raise ValueError(f"视图不存在：{view_name}")

    allowed_columns = set(view["columns"])
    args: list[Any] = []
    where_clauses = build_map_view_filter_clauses(allowed_columns, filters, args)

    if bbox is not None:
        args.extend(bbox)
        where_clauses.append(build_bbox_clause(len(args) - 3))

    if limit is not None:
        args.append(limit + 1)
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    limit_clause = f" LIMIT ${len(args)}" if limit is not None else ""
    qualified_view = f"{quote_identifier(VIEW_SCHEMA)}.{quote_identifier(view_name)}"
    rows = await fetch(
        f"""
        SELECT
            ST_AsGeoJSON(ST_Transform(t.geom, 4326)) AS geom_json,
            to_jsonb(t) - 'geom' AS properties
        FROM (
            SELECT *
            FROM {qualified_view} AS t
            {where_sql}
        ) AS t
        {limit_clause}
        """,
        *args,
    )

    has_more = limit is not None and len(rows) > limit
    features = rows if limit is None else rows[:limit]
    return add_feature_collection_metadata(
        records_to_feature_collection(features, dedupe_features=True),
        has_more=has_more,
        limit=limit,
    )


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
    year: int | None = None,
    generation: str | None = None,
    include_images: bool = True,
) -> list[dict[str, Any]]:
    """读取指定日期可导入为工作单的调查记录。"""

    return await fetch_survey_candidates_by_type(
        survey_date=survey_date,
        pest_type=pest_type,
        year=year,
        generation=generation,
        include_images=include_images,
    )


async def fetch_site_points(pest_type: str) -> list[dict[str, str]]:
    """读取指定害虫的全部基础点位，不关联调查记录。"""

    config = get_pest_config(pest_type)
    site_sources = {
        "春尺蠖": (SITE_TABLE, "村"),
        "国槐尺蠖": (SOPHORA_SITE_TABLE, "村"),
        "美国白蛾": (WHITE_MOTH_SITE_TABLE, "点位名称"),
    }
    source = site_sources.get(config.key)
    if source is None:
        raise ValueError(f"{config.key} 暂不支持点位截图管理")

    table_name, name_column = source
    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(table_name)}"
    )
    quoted_name_column = quote_identifier(name_column)
    quoted_locality_column = quote_identifier(LOCALITY_COLUMN)
    rows = await fetch(
        f"""
        SELECT
            BTRIM(COALESCE(s."编号"::text, '')) AS code,
            BTRIM(COALESCE(s.{quoted_name_column}::text, '')) AS name,
            BTRIM(COALESCE(s.{quoted_locality_column}::text, '')) AS locality
        FROM {qualified_site_table} AS s
        WHERE BTRIM(COALESCE(s."编号"::text, '')) <> ''
        ORDER BY
            BTRIM(COALESCE(s.{quoted_locality_column}::text, '')),
            BTRIM(COALESCE(s."编号"::text, ''))
        """
    )
    return [
        {
            "code": str(row["code"] or "").strip(),
            "name": str(row["name"] or "").strip(),
            "locality": str(row["locality"] or "").strip(),
        }
        for row in rows
    ]


async def fetch_survey_candidates_by_type(
    survey_date: date_cls,
    pest_type: str,
    year: int | None = None,
    generation: str | None = None,
    include_images: bool = True,
) -> list[dict[str, Any]]:
    """按害虫类型读取指定日期的工作单导入候选记录。"""

    config = get_pest_config(pest_type)
    strategy_handlers = {
        SURVEY_IMPORT_OTHER_PEST: fetch_other_pest_survey_candidates,
        SURVEY_IMPORT_SPRING_INCHWORM: fetch_spring_inchworm_survey_candidates,
        SURVEY_IMPORT_GUO_HUAI_INCHWORM: fetch_guo_huai_inchworm_survey_candidates,
        SURVEY_IMPORT_MEI_GUO_BAI_E: fetch_meiguobaie_survey_candidates,
    }
    handler = strategy_handlers.get(config.survey_import_strategy or "")
    if handler is None:
        raise ValueError(f"暂不支持 {config.key} 的调查导入")
    return await handler(survey_date, include_images=include_images)


async def fetch_spring_inchworm_survey_candidates(
    survey_date: date_cls,
    include_images: bool = True,
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

    screenshot_index = (
        build_point_screenshot_index(get_settings().point_screenshot_dir)
        if include_images
        else {}
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
    include_images: bool = True,
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

    screenshot_index = (
        build_point_screenshot_index(get_settings().sophora_point_screenshot_dir)
        if include_images
        else {}
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


async def fetch_other_pest_survey_candidates(
    survey_date: date_cls,
    include_images: bool = True,
) -> list[dict[str, Any]]:
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
    include_images: bool = True,
) -> list[dict[str, Any]]:
    """读取指定日期的美国白蛾调查导入候选记录。"""

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

    screenshot_index = (
        build_point_screenshot_index(get_settings().meiguobaie_point_screenshot_dir)
        if include_images
        else {}
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
