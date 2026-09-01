from __future__ import annotations

from typing import Any

import asyncpg

from backend.db.postgres import ensure_pool, quote_identifier
from backend.services.data_export.types import (
    ALLOWED_EXPORT_SCHEMAS,
    ExportTableMeta,
    PestExportMeta,
    PEST_TABLE_MAPPING,
)
from backend.services.data_export.workbook import validate_export_schema


async def fetch_export_table_metadata(
    connection: asyncpg.Connection,
    schema_name: str | None = None,
    table_name: str | None = None,
) -> list[ExportTableMeta]:
    if schema_name is not None:
        validate_export_schema(schema_name)

    rows = await connection.fetch(
        """
        SELECT
            t.table_schema,
            t.table_name,
            CASE t.table_type
                WHEN 'VIEW' THEN 'view'
                ELSE 'table'
            END AS object_type,
            ARRAY_AGG(c.column_name ORDER BY c.ordinal_position) AS columns
        FROM information_schema.tables AS t
        JOIN information_schema.columns AS c
          ON c.table_schema = t.table_schema
         AND c.table_name = t.table_name
        WHERE t.table_schema = ANY($1::text[])
          AND t.table_type IN ('BASE TABLE', 'VIEW')
          AND ($2::text IS NULL OR t.table_schema = $2)
          AND ($3::text IS NULL OR t.table_name = $3)
        GROUP BY t.table_schema, t.table_name, t.table_type
        ORDER BY
            CASE t.table_schema WHEN 'survey' THEN 0 WHEN 'ledger' THEN 1 ELSE 2 END,
            CASE t.table_type WHEN 'BASE TABLE' THEN 0 WHEN 'VIEW' THEN 1 ELSE 2 END,
            t.table_name
        """,
        list(ALLOWED_EXPORT_SCHEMAS),
        schema_name,
        table_name,
    )

    tables: list[ExportTableMeta] = []
    for row in rows:
        qualified_table = (
            f"{quote_identifier(row['table_schema'])}.{quote_identifier(row['table_name'])}"
        )
        count_row = await connection.fetchrow(
            f"SELECT COUNT(*) AS row_count FROM {qualified_table}"
        )
        tables.append(
            ExportTableMeta(
                schema_name=row["table_schema"],
                table_name=row["table_name"],
                object_type=row["object_type"],
                columns=tuple(row["columns"] or ()),
                row_count=int(count_row["row_count"] if count_row else 0),
            )
        )

    return tables


async def list_export_tables() -> list[dict[str, Any]]:
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        tables = await fetch_export_table_metadata(connection)
    return [table.to_public_dict() for table in tables]


async def get_export_table_meta(
    connection: asyncpg.Connection,
    schema_name: str,
    table_name: str,
) -> ExportTableMeta:
    tables = await fetch_export_table_metadata(
        connection,
        schema_name=schema_name,
        table_name=table_name,
    )
    if not tables:
        raise ValueError(f"表或视图不存在或不允许导出：{schema_name}.{table_name}")
    return tables[0]


async def _fetch_pest_filter_options(
    connection: asyncpg.Connection,
    pest_type: str,
    table_lookup: dict[tuple[str, str], ExportTableMeta],
) -> tuple[list[str], list[str]]:
    mapping = PEST_TABLE_MAPPING.get(pest_type, [])
    survey_tables = [(s, t) for s, t in mapping if s == "survey"]
    if not survey_tables:
        return [], []

    schema, table_name = survey_tables[0]
    meta = table_lookup.get((schema, table_name))
    if not meta:
        return [], []

    qualified = f"{quote_identifier(schema)}.{quote_identifier(table_name)}"
    has_generation = "世代" in meta.columns

    years: list[str] = []
    rows = await connection.fetch(
        f'SELECT DISTINCT "年份" FROM {qualified} WHERE "年份" IS NOT NULL ORDER BY "年份"'
    )
    years = [str(r["年份"]) for r in rows]

    generations: list[str] = []
    if has_generation:
        rows = await connection.fetch(
            f'SELECT DISTINCT "世代" FROM {qualified} WHERE "世代" IS NOT NULL ORDER BY "世代"'
        )
        generations = [str(r["世代"]) for r in rows]

    return years, generations


async def fetch_pest_export_metadata(
    connection: asyncpg.Connection,
    pest_type: str | None = None,
) -> list[PestExportMeta]:
    all_tables = await fetch_export_table_metadata(connection)
    table_lookup = {(t.schema_name, t.table_name): t for t in all_tables}

    pest_types_to_include = [pest_type] if pest_type else list(PEST_TABLE_MAPPING.keys())

    result: list[PestExportMeta] = []
    for pt in pest_types_to_include:
        if pt not in PEST_TABLE_MAPPING:
            raise ValueError(f"不支持的虫种：{pt}")

        tables: list[ExportTableMeta] = []
        for key in PEST_TABLE_MAPPING[pt]:
            table = table_lookup.get(key)
            if table:
                tables.append(table)

        total = sum(t.row_count for t in tables)
        years, generations = await _fetch_pest_filter_options(connection, pt, table_lookup)
        result.append(
            PestExportMeta(
                pest_type=pt,
                tables=tuple(tables),
                total_row_count=total,
                available_years=tuple(years),
                available_generations=tuple(generations),
            )
        )

    return result


async def list_pest_export_types() -> list[dict[str, Any]]:
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        pest_metas = await fetch_pest_export_metadata(connection)
    return [pm.to_public_dict() for pm in pest_metas]


async def fetch_pest_export_metadata_filtered(
    connection: asyncpg.Connection,
    pest_type: str,
    year: str | None = None,
    generation: str | None = None,
) -> PestExportMeta:
    if pest_type not in PEST_TABLE_MAPPING:
        raise ValueError(f"不支持的虫种：{pest_type}")

    all_tables = await fetch_export_table_metadata(connection)
    table_lookup = {(t.schema_name, t.table_name): t for t in all_tables}

    tables: list[ExportTableMeta] = []
    for key in PEST_TABLE_MAPPING[pest_type]:
        table = table_lookup.get(key)
        if not table:
            continue

        conditions, params = _build_filter_params(table, year, generation)
        qualified_table = (
            f"{quote_identifier(table.schema_name)}.{quote_identifier(table.table_name)}"
        )

        if conditions:
            where_clause = " AND ".join(conditions)
            count_row = await connection.fetchrow(
                f"SELECT COUNT(*) AS row_count FROM {qualified_table} WHERE {where_clause}",
                *params,
            )
        else:
            count_row = await connection.fetchrow(
                f"SELECT COUNT(*) AS row_count FROM {qualified_table}"
            )

        filtered_count = int(count_row["row_count"] if count_row else 0)
        tables.append(
            ExportTableMeta(
                schema_name=table.schema_name,
                table_name=table.table_name,
                object_type=table.object_type,
                columns=table.columns,
                row_count=filtered_count,
            )
        )

    total = sum(t.row_count for t in tables)
    years, generations = await _fetch_pest_filter_options(connection, pest_type, table_lookup)

    return PestExportMeta(
        pest_type=pest_type,
        tables=tuple(tables),
        total_row_count=total,
        available_years=tuple(years),
        available_generations=tuple(generations),
    )


def _build_filter_params(
    table: ExportTableMeta,
    year: str | None,
    generation: str | None,
) -> tuple[list[str], list[str]]:
    conditions: list[str] = []
    params: list[str] = []
    columns_set = set(table.columns)
    idx = 0

    if year is not None and "年份" in columns_set:
        idx += 1
        # “年份”在库中是 integer，列侧转 text 比较，避免 integer = text 报操作符不存在
        conditions.append(f'"年份"::text = ${idx}')
        params.append(year)

    if generation is not None and "世代" in columns_set:
        idx += 1
        conditions.append(f'"世代" = ${idx}::text')
        params.append(generation)

    return conditions, params
