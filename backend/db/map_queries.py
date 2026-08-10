from __future__ import annotations

import json
from datetime import date as date_cls
from datetime import datetime
from typing import Any

import asyncpg

from backend.db.pool import fetch, quote_identifier

VIEW_SCHEMA = "views"
REFERENCE_SCHEMA = "reference"
ADMIN_BOUNDARY_TABLE = "通州区行政区边界"
LOCALITY_COLUMN = "属地"
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


def normalize_filter_values(value: Any) -> list[str]:
    """将单值或多值筛选条件统一为去重后的字符串列表。"""

    raw_values = value if isinstance(value, (list, tuple, set)) else [value]
    values = [
        str(item).strip()
        for item in raw_values
        if item is not None and str(item).strip() != ""
    ]
    return list(dict.fromkeys(values))


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
    # 任务视图 LEFT JOIN 调查表后，未调查点位的年份/世代为 NULL。
    # 按调查属性筛选时仍应保留这些点（否则新增点位会被默认年份筛掉）。
    null_inclusive_columns = {"年份", "世代"}

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
        column_sql = quote_identifier(column)
        match_sql = f"BTRIM({column_sql}::text) = ANY(${len(args)}::text[])"
        if column in null_inclusive_columns:
            where_clauses.append(f"({column_sql} IS NULL OR {match_sql})")
        else:
            where_clauses.append(match_sql)

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
