from __future__ import annotations

import base64
import json
import mimetypes
from datetime import date as date_cls
from pathlib import Path
from typing import Any

import asyncpg

from backend.config import get_settings


VIEW_SCHEMA = "views"
REFERENCE_SCHEMA = "reference"
ADMIN_BOUNDARY_TABLE = "admin_boundary"
SURVEY_SCHEMA = "survey"
SURVEY_LARVA_TABLE = "chun_chi_huo_larva"
GUO_HUAI_LARVA_TABLE = "guo_huai_chi_huo_larva"
OTHER_PEST_SURVEY_TABLE = "other_pest_inspection"
SITE_SCHEMA = "sites"
SITE_TABLE = "poplar_sites"
SOPHORA_SITE_TABLE = "sophora_sites"
OTHER_PEST_SITE_TABLE = "other_pest_sites"

_pool: asyncpg.Pool | None = None


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

    qualified_table = (
        f"{quote_identifier(REFERENCE_SCHEMA)}.{quote_identifier(ADMIN_BOUNDARY_TABLE)}"
    )
    rows = await fetch(
        f"""
        SELECT
            ST_AsGeoJSON(ST_Transform(t.geom, 4326)) AS geom_json,
            to_jsonb(t) - 'geom' AS properties
        FROM {qualified_table} AS t
        WHERE t.geom IS NOT NULL
        ORDER BY
            COALESCE(t."分类", ''),
            COALESCE(t."区域", '')
        """,
    )
    return records_to_feature_collection(rows)


async def fetch_map_filter_options(view_name: str) -> dict[str, Any]:
    """读取指定视图的筛选选项。"""

    view = await get_map_view(view_name)
    if view is None:
        raise ValueError(f"视图不存在：{view_name}")

    columns = set(view["columns"])
    qualified_view = f"{quote_identifier(VIEW_SCHEMA)}.{quote_identifier(view_name)}"

    townships: list[str] = []
    if "乡镇" in columns:
        rows = await fetch(
            f"""
            SELECT DISTINCT TRIM("乡镇") AS value
            FROM {qualified_view}
            WHERE "乡镇" IS NOT NULL
              AND TRIM("乡镇") <> ''
            ORDER BY value
            """,
        )
        townships = [row["value"] for row in rows if row["value"]]

    return {
        "townships": townships,
        "supports_township_filter": "乡镇" in columns,
        "supports_survey_status_filter": "调查日期" in columns,
    }


async def fetch_view_feature_collection(
    view_name: str,
    filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    """读取指定视图并返回标准 GeoJSON。"""

    view = await get_map_view(view_name)
    if view is None:
        raise ValueError(f"视图不存在：{view_name}")

    allowed_columns = set(view["columns"])
    filters = filters or {}

    where_clauses: list[str] = []
    args: list[str] = []
    for column, value in filters.items():
        if column == "调查状态":
            if "调查日期" not in allowed_columns or value == "":
                continue
            if value == "调查":
                where_clauses.append(f'{quote_identifier("调查日期")} IS NOT NULL')
                continue
            if value == "未调查":
                where_clauses.append(f'{quote_identifier("调查日期")} IS NULL')
                continue
            raise ValueError(f"不支持的调查状态：{value}")
        if column not in allowed_columns:
            raise ValueError(f"不支持的过滤字段：{column}")
        if value == "":
            continue
        args.append(value)
        where_clauses.append(f"{quote_identifier(column)} = ${len(args)}")

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
    town_or_street: str,
    location_name: str,
    location_id: str,
    damage_level: str,
    total_insect_count: int | None,
) -> str:
    """根据点位信息与危害程度生成尺蠖幼虫防治描述。"""

    location_prefix = "".join(
        part.strip()
        for part in [town_or_street, location_name, location_id]
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
    town_or_street: str,
    location_name: str,
    location_id: str,
    damage_level: str,
    total_insect_count: int | None,
) -> str:
    """根据点位信息与危害程度生成春尺蠖防治描述。"""

    return build_chi_huo_larva_description(
        pest_name="春尺蠖",
        town_or_street=town_or_street,
        location_name=location_name,
        location_id=location_id,
        damage_level=damage_level,
        total_insect_count=total_insect_count,
    )


def build_guo_huai_inchworm_description(
    town_or_street: str,
    location_name: str,
    location_id: str,
    damage_level: str,
    total_insect_count: int | None,
) -> str:
    """根据点位信息与危害程度生成国槐尺蠖防治描述。"""

    return build_chi_huo_larva_description(
        pest_name="国槐尺蠖",
        town_or_street=town_or_street,
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


def build_point_screenshot_index() -> dict[str, Path]:
    """扫描本地点位截图目录，返回可唯一匹配的点位截图索引。"""

    screenshot_dir = get_settings().point_screenshot_dir
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


def load_spring_inchworm_images(
    location_id: str,
    screenshot_index: dict[str, Path],
) -> list[str]:
    """按点位编号匹配春尺蠖导入默认截图。"""

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
            COALESCE(s."乡镇", '') AS town_or_street,
            COALESCE(s."村", '') AS location_name
        FROM {qualified_larva_table} AS l
        JOIN {qualified_site_table} AS s
          ON l."编号" = s."编号"
        WHERE l."调查日期" = $1
          AND l."危害程度" IS NOT NULL
          AND BTRIM(l."危害程度") NOT IN ('', '白')
        ORDER BY
            COALESCE(s."乡镇", ''),
            l."编号"
        """,
        survey_date,
    )

    screenshot_index = build_point_screenshot_index()
    candidates: list[dict[str, Any]] = []
    for row in rows:
        location_id = str(row["location_id"] or "").strip()
        town_or_street = (row["town_or_street"] or "").strip()
        location_name = (row["location_name"] or "").strip()
        insect_count = row["total_insect_count"]
        if insect_count is not None:
            insect_count = int(insect_count)

        damage_level = (row["damage_level"] or "").strip()
        candidates.append(
            {
                "survey_date": serialize_date_value(row["survey_date"]),
                "town_or_street": town_or_street,
                "location_id": location_id,
                "location_name": location_name,
                "total_insect_count": insect_count,
                "damage_level": damage_level,
                "note": (row["note"] or "").strip(),
                "images": load_spring_inchworm_images(location_id, screenshot_index),
                "description": build_spring_inchworm_description(
                    town_or_street=town_or_street,
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
            COALESCE(s."乡镇", '') AS town_or_street,
            COALESCE(s."村", '') AS location_name
        FROM {qualified_larva_table} AS l
        JOIN {qualified_site_table} AS s
          ON l."编号" = s."编号"
        WHERE l."调查日期" = $1
          AND l."危害程度" IS NOT NULL
          AND BTRIM(l."危害程度") NOT IN ('', '白', '无需防治')
        ORDER BY
            COALESCE(s."乡镇", ''),
            l."编号"
        """,
        survey_date,
    )

    candidates: list[dict[str, Any]] = []
    for row in rows:
        location_id = str(row["location_id"] or "").strip()
        town_or_street = (row["town_or_street"] or "").strip()
        location_name = (row["location_name"] or "").strip()
        insect_count = row["total_insect_count"]
        if insect_count is not None:
            insect_count = int(insect_count)

        damage_level = (row["damage_level"] or "").strip()
        candidates.append(
            {
                "survey_date": serialize_date_value(row["survey_date"]),
                "town_or_street": town_or_street,
                "location_id": location_id,
                "location_name": location_name,
                "total_insect_count": insect_count,
                "damage_level": damage_level,
                "note": (row["note"] or "").strip(),
                "images": [],
                "description": build_guo_huai_inchworm_description(
                    town_or_street=town_or_street,
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
            COALESCE(s."乡镇", '') AS town_or_street,
            COALESCE(s."点位名称", '') AS location_name,
            COALESCE(s."寄主树种", '') AS host_plant,
            COALESCE(s."地块类型", '') AS plot_type
        FROM {qualified_survey_table} AS i
        JOIN {qualified_site_table} AS s
          ON i."编号" = s."编号"
        WHERE i."调查日期" = $1
          AND BTRIM(COALESCE(i."调查结论", '')) = '发现问题'
        ORDER BY
            COALESCE(s."乡镇", ''),
            i."编号",
            COALESCE(i."虫害类型", '')
        """,
        survey_date,
    )

    return [
        {
            "survey_date": serialize_date_value(row["survey_date"]),
            "town_or_street": (row["town_or_street"] or "").strip(),
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
