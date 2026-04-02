from __future__ import annotations

import json
from datetime import date as date_cls
from typing import Any

import asyncpg

from backend.config import get_settings


VIEW_SCHEMA = "views"
REFERENCE_SCHEMA = "reference"
ADMIN_BOUNDARY_TABLE = "admin_boundary"
SURVEY_SCHEMA = "survey"
SURVEY_LARVA_TABLE = "chun_chi_huo_larva"
SITE_SCHEMA = "sites"
SITE_TABLE = "poplar_sites"

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


def build_spring_inchworm_description(
    town_or_street: str,
    location_name: str,
    location_id: str,
    damage_level: str,
) -> str:
    """根据点位信息与危害程度生成春尺蠖防治描述。"""

    location_prefix = "".join(
        part.strip()
        for part in [town_or_street, location_name, location_id]
        if (part or "").strip()
    )
    location_text = f"{location_prefix}点位，" if location_prefix else ""
    normalized_level = (damage_level or "").strip()

    if normalized_level == "重":
        return f"{location_text}该点位春尺蠖幼虫危害程度为重，需及时开展防治作业。"
    if normalized_level == "中":
        return f"{location_text}该点位春尺蠖幼虫危害程度为中，建议尽快安排防治。"
    if normalized_level == "轻":
        return f"{location_text}该点位春尺蠖幼虫危害程度为轻，需持续关注并适时防治。"
    if normalized_level:
        return f"{location_text}该点位春尺蠖幼虫危害程度为{normalized_level}，建议结合现场情况安排防治。"
    return f"{location_text}该点位春尺蠖幼虫存在危害迹象，建议结合现场情况安排防治。"


def serialize_date_value(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


async def fetch_survey_candidates(survey_date: date_cls) -> list[dict[str, Any]]:
    """读取指定日期可导入为工作单的调查记录。"""

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

    candidates: list[dict[str, Any]] = []
    for row in rows:
        insect_count = row["total_insect_count"]
        if insect_count is not None:
            insect_count = int(insect_count)

        damage_level = (row["damage_level"] or "").strip()
        candidates.append(
            {
                "survey_date": serialize_date_value(row["survey_date"]),
                "town_or_street": (row["town_or_street"] or "").strip(),
                "location_id": str(row["location_id"] or "").strip(),
                "location_name": (row["location_name"] or "").strip(),
                "total_insect_count": insect_count,
                "damage_level": damage_level,
                "note": (row["note"] or "").strip(),
                "description": build_spring_inchworm_description(
                    town_or_street=(row["town_or_street"] or "").strip(),
                    location_name=(row["location_name"] or "").strip(),
                    location_id=str(row["location_id"] or "").strip(),
                    damage_level=damage_level,
                ),
            }
        )

    return candidates
