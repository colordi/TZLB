from __future__ import annotations

from typing import Any

import asyncpg

from backend.services.survey_import.types import (
    ALLOWED_SCHEMAS,
    BACKEND_GENERATED_ID_TABLES,
    LEDGER_CONFLICT_COLUMNS,
    ColumnMeta,
    TableMeta,
)


async def fetch_survey_table_metadata(connection: asyncpg.Connection) -> dict[str, TableMeta]:
    column_rows = await connection.fetch(
        """
        SELECT
            c.table_schema,
            c.table_name,
            c.ordinal_position,
            c.column_name,
            c.data_type,
            c.udt_name,
            c.is_nullable,
            c.is_identity,
            COALESCE(column_default, '') AS column_default
        FROM information_schema.columns AS c
        JOIN information_schema.tables AS t
          ON t.table_schema = c.table_schema
         AND t.table_name = c.table_name
        WHERE c.table_schema = ANY($1::text[])
          AND t.table_type = 'BASE TABLE'
        ORDER BY c.table_schema, c.table_name, c.ordinal_position
        """,
        list(ALLOWED_SCHEMAS),
    )
    constraint_rows = await connection.fetch(
        """
        SELECT
            tc.table_schema,
            tc.table_name,
            tc.constraint_name,
            tc.constraint_type,
            ARRAY_AGG(kcu.column_name ORDER BY kcu.ordinal_position) AS columns
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON kcu.constraint_schema = tc.constraint_schema
         AND kcu.constraint_name = tc.constraint_name
         AND kcu.table_schema = tc.table_schema
         AND kcu.table_name = tc.table_name
        WHERE tc.table_schema = ANY($1::text[])
          AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
        GROUP BY tc.table_schema, tc.table_name, tc.constraint_name, tc.constraint_type
        ORDER BY
          tc.table_schema,
          tc.table_name,
          CASE tc.constraint_type WHEN 'UNIQUE' THEN 0 ELSE 1 END,
          tc.constraint_name
        """,
        list(ALLOWED_SCHEMAS),
    )
    unique_index_rows = await connection.fetch(
        """
        SELECT
            n.nspname AS table_schema,
            c.relname AS table_name,
            i.relname AS index_name,
            ARRAY_AGG(a.attname ORDER BY key_cols.ordinality) AS columns
        FROM pg_index AS ix
        JOIN pg_class AS c
          ON c.oid = ix.indrelid
        JOIN pg_namespace AS n
          ON n.oid = c.relnamespace
        JOIN pg_class AS i
          ON i.oid = ix.indexrelid
        JOIN unnest(ix.indkey) WITH ORDINALITY AS key_cols(attnum, ordinality)
          ON true
        JOIN pg_attribute AS a
          ON a.attrelid = c.oid
         AND a.attnum = key_cols.attnum
        JOIN information_schema.tables AS t
          ON t.table_schema = n.nspname
         AND t.table_name = c.relname
         AND t.table_type = 'BASE TABLE'
        WHERE n.nspname = ANY($1::text[])
          AND ix.indisunique
          AND ix.indisvalid
          AND ix.indpred IS NULL
        GROUP BY n.nspname, c.relname, i.relname
        ORDER BY n.nspname, c.relname, i.relname
        """,
        list(ALLOWED_SCHEMAS),
    )

    enum_rows = await connection.fetch(
        """
        SELECT t.typname, e.enumlabel
        FROM pg_type AS t
        JOIN pg_enum AS e
          ON e.enumtypid = t.oid
        ORDER BY t.typname, e.enumsortorder
        """
    )

    enum_labels_by_type: dict[str, list[str]] = {}
    for row in enum_rows:
        enum_labels_by_type.setdefault(row["typname"], []).append(row["enumlabel"])

    columns_by_table: dict[tuple[str, str], dict[str, ColumnMeta]] = {}
    for row in column_rows:
        table_key = (row["table_schema"], row["table_name"])
        columns_by_table.setdefault(table_key, {})[row["column_name"]] = ColumnMeta(
            name=row["column_name"],
            data_type=row["data_type"],
            udt_name=row["udt_name"],
            is_nullable=row["is_nullable"] == "YES",
            default=row["column_default"] or "",
            ordinal_position=row["ordinal_position"],
            is_identity=row["is_identity"] == "YES",
            enum_labels=tuple(enum_labels_by_type.get(row["udt_name"], ())),
        )

    conflict_candidates: dict[tuple[str, str], list[tuple[str, ...]]] = {}
    for row in [*constraint_rows, *unique_index_rows]:
        columns = tuple(row["columns"] or ())
        if columns:
            table_key = (row["table_schema"], row["table_name"])
            conflict_candidates.setdefault(table_key, []).append(columns)

    metadata: dict[str, TableMeta] = {}
    duplicate_table_names = {
        table_name
        for _, table_name in columns_by_table
        if sum(1 for _, candidate_name in columns_by_table if candidate_name == table_name) > 1
    }
    for (schema_name, table_name), columns in columns_by_table.items():
        if table_name in duplicate_table_names:
            continue
        conflict_columns, supports_on_conflict = resolve_table_conflict_columns(
            schema_name,
            table_name,
            conflict_candidates.get((schema_name, table_name), []),
            columns,
        )
        metadata[table_name] = TableMeta(
            schema_name=schema_name,
            name=table_name,
            columns=columns,
            conflict_columns=conflict_columns,
            supports_on_conflict=supports_on_conflict,
        )
    return metadata


def choose_conflict_columns(
    candidates: list[tuple[str, ...]],
    columns: dict[str, ColumnMeta],
) -> tuple[str, ...]:
    unique_candidates: list[tuple[str, ...]] = []
    for candidate in candidates:
        if candidate in unique_candidates:
            continue
        if any(column not in columns for column in candidate):
            continue
        unique_candidates.append(candidate)

    multi_column_candidates = [
        candidate for candidate in unique_candidates if len(candidate) > 1
    ]
    if multi_column_candidates:
        return multi_column_candidates[0]

    non_auto_candidates = [
        candidate
        for candidate in unique_candidates
        if not (len(candidate) == 1 and columns[candidate[0]].is_auto_generated)
    ]
    return non_auto_candidates[0] if non_auto_candidates else ()


def resolve_table_conflict_columns(
    schema_name: str,
    table_name: str,
    candidates: list[tuple[str, ...]],
    columns: dict[str, ColumnMeta],
) -> tuple[tuple[str, ...], bool]:
    hardcoded = LEDGER_CONFLICT_COLUMNS.get((schema_name, table_name))
    if hardcoded and all(column in columns for column in hardcoded):
        return hardcoded, False
    return choose_conflict_columns(candidates, columns), True


def is_backend_generated_column(table_meta: TableMeta, column_name: str) -> bool:
    return (
        (table_meta.schema_name, table_meta.name) in BACKEND_GENERATED_ID_TABLES
        and column_name == "id"
    )
