from __future__ import annotations

from typing import Any

import asyncpg

from backend.db.postgres import quote_identifier
from backend.services.survey_import.types import (
    BACKEND_GENERATED_ID_TABLES,
    PreparedRow,
    PreparedSheet,
    TableMeta,
)


def has_errors(sheets: list[PreparedSheet]) -> bool:
    return any(sheet.errors for sheet in sheets)


async def mark_database_duplicates(
    connection: asyncpg.Connection,
    sheets: list[PreparedSheet],
    metadata: dict[str, TableMeta],
) -> None:
    for sheet in sheets:
        if sheet.table_name is None or sheet.table_name not in metadata:
            continue
        if sheet.errors:
            continue

        table_meta = metadata[sheet.table_name]
        duplicate_keys: set[tuple[Any, ...]] = set()
        for row in sheet.rows:
            if row.skipped_duplicate or row.conflict_values in duplicate_keys:
                continue
            if await row_exists(connection, table_meta, row):
                row.skipped_duplicate = True
                duplicate_keys.add(row.conflict_values)
                sheet.skipped_duplicate_rows += 1


async def row_exists(
    connection: asyncpg.Connection,
    table_meta: TableMeta,
    row: PreparedRow,
) -> bool:
    qualified_table = (
        f"{quote_identifier(table_meta.schema_name)}.{quote_identifier(table_meta.name)}"
    )
    conditions = [
        f"{quote_identifier(column)} = ${index}"
        for index, column in enumerate(table_meta.conflict_columns, start=1)
    ]
    result = await connection.fetchrow(
        f"""
        SELECT 1
        FROM {qualified_table}
        WHERE {' AND '.join(conditions)}
        LIMIT 1
        """,
        *row.conflict_values,
    )
    return result is not None


async def insert_valid_rows(
    connection: asyncpg.Connection,
    sheets: list[PreparedSheet],
    metadata: dict[str, TableMeta],
) -> None:
    await assign_backend_generated_ids(connection, sheets, metadata)
    for sheet in sheets:
        if sheet.table_name is None or sheet.table_name not in metadata or sheet.errors:
            continue

        table_meta = metadata[sheet.table_name]
        for row in sheet.rows:
            if row.skipped_duplicate:
                continue
            inserted = await insert_row(connection, table_meta, row)
            if inserted:
                sheet.inserted_rows += 1
            else:
                row.skipped_duplicate = True
                sheet.skipped_duplicate_rows += 1


async def assign_backend_generated_ids(
    connection: asyncpg.Connection,
    sheets: list[PreparedSheet],
    metadata: dict[str, TableMeta],
) -> None:
    for sheet in sheets:
        if sheet.table_name is None or sheet.table_name not in metadata or sheet.errors:
            continue

        table_meta = metadata[sheet.table_name]
        if (table_meta.schema_name, table_meta.name) not in BACKEND_GENERATED_ID_TABLES:
            continue
        if "id" not in table_meta.columns:
            continue

        rows_requiring_id = [
            row for row in sheet.rows if not row.skipped_duplicate and "id" not in row.values
        ]
        if not rows_requiring_id:
            continue

        qualified_table = (
            f"{quote_identifier(table_meta.schema_name)}.{quote_identifier(table_meta.name)}"
        )
        await connection.execute(f"LOCK TABLE {qualified_table} IN SHARE ROW EXCLUSIVE MODE")
        next_id = (
            await connection.fetchval(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {qualified_table}")
        ) or 1
        for row in rows_requiring_id:
            row.values["id"] = next_id
            next_id += 1


async def insert_row(
    connection: asyncpg.Connection,
    table_meta: TableMeta,
    row: PreparedRow,
) -> bool:
    ordered_columns = sorted(
        row.values,
        key=lambda name: table_meta.columns[name].ordinal_position,
    )
    placeholders = [f"${index}" for index in range(1, len(ordered_columns) + 1)]
    conflict_columns = ", ".join(quote_identifier(column) for column in table_meta.conflict_columns)
    qualified_table = (
        f"{quote_identifier(table_meta.schema_name)}.{quote_identifier(table_meta.name)}"
    )
    values = [row.values[column] for column in ordered_columns]
    if not table_meta.supports_on_conflict:
        conflict_conditions = [
            f"{quote_identifier(column)} = ${len(values) + index}"
            for index, column in enumerate(table_meta.conflict_columns, start=1)
        ]
        result = await connection.fetchrow(
            f"""
            INSERT INTO {qualified_table} (
                {', '.join(quote_identifier(column) for column in ordered_columns)}
            )
            SELECT {', '.join(placeholders)}
            WHERE NOT EXISTS (
                SELECT 1
                FROM {qualified_table}
                WHERE {' AND '.join(conflict_conditions)}
            )
            RETURNING 1 AS inserted
            """,
            *values,
            *row.conflict_values,
        )
        return result is not None

    result = await connection.fetchrow(
        f"""
        INSERT INTO {qualified_table} (
            {', '.join(quote_identifier(column) for column in ordered_columns)}
        )
        VALUES ({', '.join(placeholders)})
        ON CONFLICT ({conflict_columns}) DO NOTHING
        RETURNING 1 AS inserted
        """,
        *values,
    )
    return result is not None
