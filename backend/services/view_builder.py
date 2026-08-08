"""任务图层构建器 — 管理员基于 sites/survey/ledger 表发布 views 下的任务视图。

视图定义采用约束式构建：选择基表（sites，提供 geom）与可选关联表
（survey/ledger，按编号关联），筛选条件（年份/世代）经严格校验后以
字面量烘焙进 SQL。所有表名、列名均来自 information_schema 白名单，
不开放自由 SQL。系统创建的视图统一使用 ``task_`` 前缀；删除功能
对 ``views`` 下的所有视图开放。
"""

from __future__ import annotations

import re
from typing import Any

from backend.db.layer_metadata import (
    ADMIN_SCHEMA,
    LAYER_METADATA_TABLE,
    batch_upsert_layer_metadata,
)
from backend.db.pool import ensure_pool, fetch, fetchrow, quote_identifier

VIEW_SCHEMA = "views"
BASE_SCHEMA = "sites"
RELATED_SCHEMAS = ("survey", "ledger")
TASK_VIEW_PREFIX = "task_"
TASK_VIEW_NAME_PATTERN = re.compile(r"^task_[a-z0-9_]{1,40}$")
VIEW_NAME_PATTERN = re.compile(r"^[0-9A-Za-z_一-鿿]{1,63}$")
YEAR_FILTER_PATTERN = re.compile(r"^\d{4}$")
GENERATION_FILTER_VALUES = ("第一代", "第二代", "第三代")
CODE_LIST_MAX_COUNT = 2000
CODE_MAX_LENGTH = 64
CODE_ILLEGAL_CHAR_PATTERN = re.compile(r'["\'\\]')
JOIN_KEY_COLUMN = "编号"
GEOM_COLUMN = "geom"
LOCALITY_COLUMN = "属地"
SITE_NAME_COLUMN = "点位名称"
SITE_NAME_CANDIDATES = ("点位名称", "村", "点位")
SURVEY_DATE_COLUMN = "调查日期"
YEAR_COLUMN = "年份"
GENERATION_COLUMN = "世代"

TaskViewDefinition = dict[str, Any]


async def _list_schema_columns(schema: str) -> dict[str, list[str]]:
    """读取指定 schema 下所有基表的列清单（按表名、列序排列）。"""

    rows = await fetch(
        """
        SELECT c.table_name, c.column_name
        FROM information_schema.columns AS c
        JOIN information_schema.tables AS t
          ON t.table_schema = c.table_schema
         AND t.table_name = c.table_name
        WHERE c.table_schema = $1
          AND t.table_type = 'BASE TABLE'
        ORDER BY c.table_name, c.ordinal_position
        """,
        schema,
    )
    columns_by_table: dict[str, list[str]] = {}
    for row in rows:
        columns_by_table.setdefault(row["table_name"], []).append(row["column_name"])
    return columns_by_table


def _detect_site_name_column(columns: list[str]) -> str | None:
    for candidate in SITE_NAME_CANDIDATES:
        if candidate in columns:
            return candidate
    return None


async def list_builder_sources() -> dict[str, Any]:
    """列出构建器可用的基表与关联表候选。"""

    base_columns = await _list_schema_columns(BASE_SCHEMA)
    base_tables = [
        {
            "table_schema": BASE_SCHEMA,
            "name": name,
            "columns": columns,
            "has_join_key": JOIN_KEY_COLUMN in columns,
            "site_name_column": _detect_site_name_column(columns),
        }
        for name, columns in base_columns.items()
        if GEOM_COLUMN in columns
    ]

    related_tables: list[dict[str, Any]] = []
    for schema in RELATED_SCHEMAS:
        schema_columns = await _list_schema_columns(schema)
        for name, columns in schema_columns.items():
            if JOIN_KEY_COLUMN not in columns:
                continue
            related_tables.append(
                {
                    "table_schema": schema,
                    "name": name,
                    "columns": columns,
                    "has_year": YEAR_COLUMN in columns,
                    "has_generation": GENERATION_COLUMN in columns,
                    "has_survey_date": SURVEY_DATE_COLUMN in columns,
                }
            )

    return {"base_tables": base_tables, "related_tables": related_tables}


def _escape_literal(value: str) -> str:
    return value.replace("'", "''")


def _normalize_code_list(raw: Any) -> list[str]:
    """规范化编号清单：去空白、去重，并做防注入校验（不限定编号格式）。"""

    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)):
        raise ValueError("编号清单必须是数组")

    codes: list[str] = []
    for item in raw:
        code = str(item if item is not None else "").strip()
        if not code:
            continue
        if len(code) > CODE_MAX_LENGTH:
            raise ValueError(f"编号长度超过 {CODE_MAX_LENGTH} 字符：{code[:20]}…")
        if any(char.isspace() for char in code) or CODE_ILLEGAL_CHAR_PATTERN.search(code):
            raise ValueError(f"编号含非法字符（空格、引号或反斜杠）：{code}")
        codes.append(code)

    deduped = list(dict.fromkeys(codes))
    if len(deduped) > CODE_LIST_MAX_COUNT:
        raise ValueError(f"编号清单最多支持 {CODE_LIST_MAX_COUNT} 条")
    return deduped


def _validate_definition(
    definition: TaskViewDefinition,
    *,
    base_columns_by_table: dict[str, list[str]],
    related_columns_by_table: dict[str, list[str]],
) -> dict[str, Any]:
    """校验任务视图定义，返回规范化后的定义。校验失败抛出 ValueError。"""

    name = str(definition.get("name") or "").strip()
    if not TASK_VIEW_NAME_PATTERN.match(name):
        raise ValueError(
            "视图名称须以 task_ 开头，仅含小写字母、数字和下划线（最长 44 字符）"
        )

    display_name = str(definition.get("display_name") or "").strip()
    if not display_name:
        raise ValueError("任务名称不能为空")

    base_table = str(definition.get("base_table") or "").strip()
    base_columns = base_columns_by_table.get(base_table)
    if base_columns is None:
        raise ValueError(f"基础点位表不存在或不在白名单内：{base_table}")
    if GEOM_COLUMN not in base_columns:
        raise ValueError(f"基础点位表缺少 geom 字段：{base_table}")

    site_name_column = definition.get("site_name_column")
    if site_name_column is not None:
        site_name_column = str(site_name_column).strip() or None
    if site_name_column is None:
        site_name_column = _detect_site_name_column(base_columns)
    if site_name_column is not None and site_name_column not in base_columns:
        raise ValueError(f"点位名称列不存在于基础点位表：{site_name_column}")

    related_table = definition.get("related_table")
    if related_table is not None:
        related_table = str(related_table).strip() or None

    filters = definition.get("filters") or {}
    if not isinstance(filters, dict):
        raise ValueError("筛选条件必须是对象")
    year_filter = str(filters.get(YEAR_COLUMN) or "").strip()
    generation_filter = str(filters.get(GENERATION_COLUMN) or "").strip()
    code_list = _normalize_code_list(filters.get("codes"))
    if code_list and JOIN_KEY_COLUMN not in base_columns:
        raise ValueError(f"基础点位表缺少编号字段，无法按编号清单筛选：{base_table}")

    related_columns: list[str] | None = None
    if related_table is not None:
        if JOIN_KEY_COLUMN not in base_columns:
            raise ValueError(f"基础点位表缺少编号字段，无法关联调查/台账表：{base_table}")
        related_columns = related_columns_by_table.get(related_table)
        if related_columns is None:
            raise ValueError(f"关联表不存在或不在白名单内：{related_table}")
        if JOIN_KEY_COLUMN not in related_columns:
            raise ValueError(f"关联表缺少编号字段：{related_table}")
        if year_filter:
            if not YEAR_FILTER_PATTERN.match(year_filter):
                raise ValueError("年份筛选必须是 4 位数字")
            if YEAR_COLUMN not in related_columns:
                raise ValueError(f"关联表缺少年份字段，无法按年份筛选：{related_table}")
        if generation_filter:
            if generation_filter not in GENERATION_FILTER_VALUES:
                raise ValueError(
                    f"世代筛选仅支持：{'、'.join(GENERATION_FILTER_VALUES)}"
                )
            if GENERATION_COLUMN not in related_columns:
                raise ValueError(f"关联表缺少世代字段，无法按世代筛选：{related_table}")
    elif year_filter or generation_filter:
        raise ValueError("未选择关联表时不能设置年份/世代筛选")

    return {
        "name": name,
        "display_name": display_name,
        "base_table": base_table,
        "base_columns": base_columns,
        "site_name_column": site_name_column,
        "related_table": related_table,
        "related_columns": related_columns,
        "year_filter": year_filter,
        "generation_filter": generation_filter,
        "codes": code_list,
    }


def _build_base_output_columns(normalized: dict[str, Any]) -> list[str]:
    """基表输出列：geom、编号（若有）、属地（若有）、点位名称（若有）。"""

    base_columns = normalized["base_columns"]
    outputs = [f"s.{quote_identifier(GEOM_COLUMN)} AS {quote_identifier(GEOM_COLUMN)}"]
    if JOIN_KEY_COLUMN in base_columns:
        outputs.append(
            f"BTRIM(s.{quote_identifier(JOIN_KEY_COLUMN)}::text)"
            f" AS {quote_identifier(JOIN_KEY_COLUMN)}"
        )
    if LOCALITY_COLUMN in base_columns:
        outputs.append(
            f"NULLIF(BTRIM(s.{quote_identifier(LOCALITY_COLUMN)}::text), '')"
            f" AS {quote_identifier(LOCALITY_COLUMN)}"
        )
    site_name_column = normalized["site_name_column"]
    if site_name_column is not None:
        outputs.append(
            f"NULLIF(BTRIM(s.{quote_identifier(site_name_column)}::text), '')"
            f" AS {quote_identifier(SITE_NAME_COLUMN)}"
        )
    return outputs


def _build_related_output_columns(normalized: dict[str, Any]) -> list[str]:
    """关联表输出列：剔除编号及与基表输出冲突的属地/点位名称。"""

    related_columns = normalized["related_columns"] or []
    excluded = {JOIN_KEY_COLUMN, LOCALITY_COLUMN, SITE_NAME_COLUMN, GEOM_COLUMN}
    return [
        f"l.{quote_identifier(column)} AS {quote_identifier(column)}"
        for column in related_columns
        if column not in excluded
    ]


def _build_base_where_sql(normalized: dict[str, Any]) -> str:
    """基表侧 WHERE：geom 非空 + 可选的编号清单过滤。"""

    clauses = [f"s.{quote_identifier(GEOM_COLUMN)} IS NOT NULL"]
    codes = normalized["codes"]
    if codes:
        join_key = quote_identifier(JOIN_KEY_COLUMN)
        literals = ", ".join(f"'{_escape_literal(code)}'" for code in codes)
        clauses.append(f"BTRIM(s.{join_key}::text) IN ({literals})")
    return " AND ".join(clauses)


def _build_select_sql(normalized: dict[str, Any]) -> str:
    """构建任务视图的 SELECT 主体（不含 CREATE VIEW 语句）。"""

    qualified_base = (
        f"{quote_identifier(BASE_SCHEMA)}.{quote_identifier(normalized['base_table'])}"
    )
    base_outputs = _build_base_output_columns(normalized)
    base_where = _build_base_where_sql(normalized)

    if normalized["related_table"] is None:
        select_list = ",\n    ".join(base_outputs)
        return (
            f"SELECT {select_list}\n"
            f"FROM {qualified_base} AS s\n"
            f"WHERE {base_where}"
        )

    qualified_related = (
        f"{quote_identifier(_related_schema_of(normalized['related_table']))}"
        f".{quote_identifier(_related_table_name_of(normalized['related_table']))}"
    )
    join_key = quote_identifier(JOIN_KEY_COLUMN)
    inner_columns = [
        f"BTRIM(r.{join_key}::text) AS {join_key}",
    ]
    inner_columns.extend(
        f"r.{quote_identifier(column)}"
        for column in normalized["related_columns"]
        if column != JOIN_KEY_COLUMN
    )

    where_clauses = [
        f"r.{join_key} IS NOT NULL",
        f"BTRIM(r.{join_key}::text) <> ''",
    ]
    if normalized["year_filter"]:
        where_clauses.append(
            f"r.{quote_identifier(YEAR_COLUMN)}::text"
            f" = '{_escape_literal(normalized['year_filter'])}'"
        )
    if normalized["generation_filter"]:
        where_clauses.append(
            f"r.{quote_identifier(GENERATION_COLUMN)}::text"
            f" = '{_escape_literal(normalized['generation_filter'])}'"
        )

    order_columns = [f"BTRIM(r.{join_key}::text)"]
    related_columns = normalized["related_columns"]
    if SURVEY_DATE_COLUMN in related_columns:
        order_columns.append(f"r.{quote_identifier(SURVEY_DATE_COLUMN)} DESC NULLS LAST")
    elif YEAR_COLUMN in related_columns:
        order_columns.append(f"r.{quote_identifier(YEAR_COLUMN)} DESC NULLS LAST")

    inner_select = (
        f"SELECT DISTINCT ON (BTRIM(r.{join_key}::text))\n"
        f"            {',\n            '.join(inner_columns)}\n"
        f"        FROM {qualified_related} AS r\n"
        f"        WHERE {' AND '.join(where_clauses)}\n"
        f"        ORDER BY {', '.join(order_columns)}"
    )

    select_list = ",\n    ".join(base_outputs + _build_related_output_columns(normalized))
    return (
        f"SELECT {select_list}\n"
        f"FROM {qualified_base} AS s\n"
        f"LEFT JOIN (\n"
        f"    {inner_select}\n"
        f") AS l ON BTRIM(s.{join_key}::text) = l.{join_key}\n"
        f"WHERE {base_where}"
    )


# related_columns_by_table 的键为 "schema.table"，见 _related_whitelist。
def _related_schema_of(qualified_name: str) -> str:
    return qualified_name.split(".", 1)[0]


def _related_table_name_of(qualified_name: str) -> str:
    return qualified_name.split(".", 1)[1]


async def _build_whitelists() -> tuple[
    dict[str, list[str]], dict[str, list[str]]
]:
    """构建基表与关联表白名单。关联表键为 ``schema.table``。"""

    base_columns = await _list_schema_columns(BASE_SCHEMA)
    base_whitelist = {
        name: columns
        for name, columns in base_columns.items()
        if GEOM_COLUMN in columns
    }
    related_whitelist: dict[str, list[str]] = {}
    for schema in RELATED_SCHEMAS:
        schema_columns = await _list_schema_columns(schema)
        for name, columns in schema_columns.items():
            if JOIN_KEY_COLUMN in columns:
                related_whitelist[f"{schema}.{name}"] = columns
    return base_whitelist, related_whitelist


def build_view_sql(
    definition: TaskViewDefinition,
    *,
    base_columns_by_table: dict[str, list[str]],
    related_columns_by_table: dict[str, list[str]],
) -> str:
    """校验定义并渲染 CREATE OR REPLACE VIEW 语句。

    白名单以参数传入，便于无数据库环境下单元测试。
    """

    normalized = _validate_definition(
        definition,
        base_columns_by_table=base_columns_by_table,
        related_columns_by_table=related_columns_by_table,
    )
    qualified_view = (
        f"{quote_identifier(VIEW_SCHEMA)}.{quote_identifier(normalized['name'])}"
    )
    return (
        f"CREATE OR REPLACE VIEW {qualified_view} AS\n"
        f"{_build_select_sql(normalized)}"
    )


def _non_geom_output_columns(normalized: dict[str, Any]) -> list[str]:
    outputs = []
    if JOIN_KEY_COLUMN in normalized["base_columns"]:
        outputs.append(JOIN_KEY_COLUMN)
    if LOCALITY_COLUMN in normalized["base_columns"]:
        outputs.append(LOCALITY_COLUMN)
    if normalized["site_name_column"] is not None:
        outputs.append(SITE_NAME_COLUMN)
    if normalized["related_table"] is not None:
        excluded = {JOIN_KEY_COLUMN, LOCALITY_COLUMN, SITE_NAME_COLUMN, GEOM_COLUMN}
        outputs.extend(
            column
            for column in normalized["related_columns"]
            if column not in excluded
        )
    return outputs


async def preview_task_view(definition: TaskViewDefinition) -> dict[str, Any]:
    """校验定义并预览：返回行数、单条抽样行（不含 geom）与清单匹配情况。"""

    base_whitelist, related_whitelist = await _build_whitelists()
    normalized = _validate_definition(
        definition,
        base_columns_by_table=base_whitelist,
        related_columns_by_table=related_whitelist,
    )
    select_sql = _build_select_sql(normalized)

    total_row = await fetchrow(
        f"SELECT count(*) AS total FROM (\n{select_sql}\n) AS preview_t"
    )
    sample_columns = _non_geom_output_columns(normalized)
    sample_select = ", ".join(quote_identifier(column) for column in sample_columns)
    sample_rows = await fetch(
        f"SELECT {sample_select} FROM (\n{select_sql}\n) AS preview_t LIMIT 1"
    )

    codes = normalized["codes"]
    unmatched_codes: list[str] = []
    if codes:
        qualified_base = (
            f"{quote_identifier(BASE_SCHEMA)}"
            f".{quote_identifier(normalized['base_table'])}"
        )
        join_key = quote_identifier(JOIN_KEY_COLUMN)
        literals = ", ".join(f"'{_escape_literal(code)}'" for code in codes)
        matched_rows = await fetch(
            f"SELECT DISTINCT BTRIM(s.{join_key}::text) AS code "
            f"FROM {qualified_base} AS s "
            f"WHERE BTRIM(s.{join_key}::text) IN ({literals})"
        )
        matched_codes = {row["code"] for row in matched_rows}
        unmatched_codes = [code for code in codes if code not in matched_codes]

    return {
        "name": normalized["name"],
        "total": int(total_row["total"]) if total_row else 0,
        "sample_columns": sample_columns,
        "sample_rows": [dict(row) for row in sample_rows],
        "codes_total": len(codes),
        "codes_matched": len(codes) - len(unmatched_codes),
        "codes_unmatched": unmatched_codes,
    }


async def create_task_view(definition: TaskViewDefinition) -> dict[str, Any]:
    """物理创建任务视图，并将其注册到图层元数据表。"""

    base_whitelist, related_whitelist = await _build_whitelists()
    normalized = _validate_definition(
        definition,
        base_columns_by_table=base_whitelist,
        related_columns_by_table=related_whitelist,
    )
    select_sql = _build_select_sql(normalized)
    qualified_view = (
        f"{quote_identifier(VIEW_SCHEMA)}.{quote_identifier(normalized['name'])}"
    )

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            f"CREATE OR REPLACE VIEW {qualified_view} AS\n{select_sql}"
        )

    sort_row = await fetchrow(
        f"""
        SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_sort_order
        FROM {quote_identifier(ADMIN_SCHEMA)}.{quote_identifier(LAYER_METADATA_TABLE)}
        WHERE layer_type = 'view'
        """
    )
    next_sort_order = int(sort_row["next_sort_order"]) if sort_row else 0
    await batch_upsert_layer_metadata(
        [
            {
                "layer_key": normalized["name"],
                "layer_type": "view",
                "display_name": normalized["display_name"],
                "sort_order": next_sort_order,
                "default_visible": False,
                "is_enabled": True,
                "default_filters": {},
            }
        ]
    )
    return {
        "name": normalized["name"],
        "display_name": normalized["display_name"],
    }


async def delete_task_view(view_name: str) -> dict[str, Any] | None:
    """删除 views 下的视图及其图层元数据。视图不存在时返回 None。"""

    if not VIEW_NAME_PATTERN.match(view_name):
        raise ValueError("视图名称不合法")

    exists_row = await fetchrow(
        """
        SELECT 1 AS found
        FROM information_schema.views
        WHERE table_schema = $1 AND table_name = $2
        """,
        VIEW_SCHEMA,
        view_name,
    )
    if exists_row is None:
        return None

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            f"DROP VIEW IF EXISTS "
            f"{quote_identifier(VIEW_SCHEMA)}.{quote_identifier(view_name)}"
        )
        await connection.execute(
            f"""
            DELETE FROM {quote_identifier(ADMIN_SCHEMA)}.{quote_identifier(LAYER_METADATA_TABLE)}
            WHERE layer_type = 'view' AND layer_key = $1
            """,
            view_name,
        )
    return {"name": view_name}
