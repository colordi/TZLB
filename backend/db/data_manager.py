"""数据管理模块的 SQL 执行层：行数据 CRUD 与变更审计日志。"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import asyncpg

from backend.db.postgres import ensure_pool, quote_identifier
from backend.services.data_manager import (
    ManagedColumnMeta,
    ManagedTableMeta,
    coerce_value,
    fetch_managed_table_metadata,
    get_table_meta,
    serialize_row,
    serialize_value,
)


CHANGE_LOG_TABLE = "data_change_logs"
ADMIN_SCHEMA = "app_admin"

MAX_PAGE_SIZE = 200


def _qualified_change_log_table() -> str:
    return f'"{ADMIN_SCHEMA}"."{CHANGE_LOG_TABLE}"'


async def ensure_data_change_log_storage() -> None:
    """初始化数据变更日志表结构。"""

    log_table = _qualified_change_log_table()
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{ADMIN_SCHEMA}"')
            await connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {log_table} (
                    id BIGSERIAL PRIMARY KEY,
                    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    action TEXT NOT NULL,
                    operator_id INTEGER NULL,
                    operator_username TEXT NOT NULL,
                    operator_display_name TEXT NOT NULL,
                    schema_name TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    pk_json JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    before_json JSONB NULL,
                    after_json JSONB NULL
                )
                """
            )
            await connection.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_data_change_log_occurred_at
                ON {log_table} (occurred_at DESC)
                """
            )


async def _load_table_meta(
    connection: asyncpg.Connection, schema_name: str, table_name: str
) -> ManagedTableMeta:
    metadata = await fetch_managed_table_metadata(connection)
    return get_table_meta(metadata, schema_name, table_name)


async def list_manageable_tables() -> list[dict[str, Any]]:
    """列出可管理的基表：schema、表名、精确行数、主键信息。

    行数使用实时 COUNT(*)，与数据导出页面的统计口径一致；
    不能用 pg_class.reltuples，那是 ANALYZE 维护的估计值，导入后可能长期过期。
    """

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        metadata = await fetch_managed_table_metadata(connection)
        tables: list[dict[str, Any]] = []
        for (schema_name, table_name), meta in sorted(metadata.items()):
            count_row = await connection.fetchrow(
                f"SELECT COUNT(*) AS row_count FROM {meta.qualified_name}"
            )
            tables.append(
                {
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "row_count": int(count_row["row_count"] if count_row else 0),
                    "has_primary_key": bool(meta.primary_key),
                    "primary_key": list(meta.primary_key),
                }
            )
    return tables


def list_columns(meta: ManagedTableMeta) -> list[dict[str, Any]]:
    """把列元数据转换为前端表单/表格可用的结构。"""

    return [
        {
            "name": column.name,
            "data_type": column.data_type,
            "is_nullable": column.is_nullable,
            "has_default": column.has_default,
            "is_primary_key": column.is_primary_key,
            "is_readonly": column.is_readonly,
            "is_geometry": column.is_geometry,
            "input_kind": column.input_kind,
            "enum_labels": list(column.enum_labels),
        }
        for column in meta.columns
    ]


def _append_range_clause(
    clauses: list[str], args: list[Any], column: ManagedColumnMeta, raw: dict[str, Any]
) -> None:
    """日期/时间列的区间筛选：from 起（含）、to 止（含当天），两端均可省略。"""

    if column.data_type != "date" and not column.data_type.startswith("timestamp"):
        raise ValueError(f"列「{column.name}」不支持区间筛选")
    unknown = set(raw) - {"from", "to"}
    if unknown:
        raise ValueError(f"列「{column.name}」区间筛选仅支持 from/to 参数")
    start = str(raw.get("from") or "").strip()
    end = str(raw.get("to") or "").strip()
    if start:
        args.append(coerce_value(column, start))
        clauses.append(f"{quote_identifier(column.name)} >= ${len(args)}")
    if end:
        end_value = coerce_value(column, end)
        if column.data_type.startswith("timestamp"):
            # 截止时间只精确到日期输入框的当天 00:00，+1 天后改半开区间实现"含当天"
            args.append(end_value + timedelta(days=1))
            clauses.append(f"{quote_identifier(column.name)} < ${len(args)}")
        else:
            args.append(end_value)
            clauses.append(f"{quote_identifier(column.name)} <= ${len(args)}")


def _build_filter_clause(
    meta: ManagedTableMeta, filters: dict[str, Any]
) -> tuple[str, list[Any]]:
    """把过滤条件转成参数化 WHERE 片段。

    字符串值按文本模糊匹配；{"from": ..., "to": ...} 对象仅用于
    date/timestamp 列，生成起止区间条件（to 含当天）。
    """

    clauses: list[str] = []
    args: list[Any] = []
    for name, raw in (filters or {}).items():
        column = meta.get_column(name)
        if column is None or column.is_geometry:
            raise ValueError(f"列「{name}」不支持筛选")
        if isinstance(raw, dict):
            _append_range_clause(clauses, args, column, raw)
            continue
        text = str(raw or "").strip()
        if not text:
            continue
        args.append(f"%{text}%")
        clauses.append(f"CAST({quote_identifier(name)} AS text) ILIKE ${len(args)}")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, args


def _resolve_order_by(meta: ManagedTableMeta, sort: str | None) -> str:
    column_name = (sort or "").strip()
    direction = "ASC"
    if column_name.startswith("-"):
        direction = "DESC"
        column_name = column_name[1:]
    column = meta.get_column(column_name) if column_name else None
    if column is None or column.is_geometry:
        if meta.primary_key:
            order_columns = [f"{quote_identifier(name)} ASC" for name in meta.primary_key]
            return f"ORDER BY {', '.join(order_columns)}"
        first = meta.selectable_columns[0] if meta.selectable_columns else None
        return f"ORDER BY {quote_identifier(first.name)} ASC" if first else ""
    return f"ORDER BY {quote_identifier(column.name)} {direction}"


async def fetch_rows(
    schema_name: str,
    table_name: str,
    *,
    page: int,
    page_size: int,
    sort: str | None,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """分页读取行数据（不含几何列），返回 rows/total/page/page_size。"""

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        meta = await _load_table_meta(connection, schema_name, table_name)
        where, args = _build_filter_clause(meta, filters)
        order_by = _resolve_order_by(meta, sort)
        select_list = ", ".join(
            quote_identifier(column.name) for column in meta.selectable_columns
        )
        total_row = await connection.fetchrow(
            f"SELECT COUNT(*) AS total FROM {meta.qualified_name} {where}",
            *args,
        )
        limit = min(max(page_size, 1), MAX_PAGE_SIZE)
        offset = (max(page, 1) - 1) * limit
        rows = await connection.fetch(
            f"""
            SELECT {select_list}
            FROM {meta.qualified_name}
            {where}
            {order_by}
            LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
            """,
            *args,
            limit,
            offset,
        )
    return {
        "rows": [serialize_row(row) for row in rows],
        "total": total_row["total"] if total_row else 0,
        "page": max(page, 1),
        "page_size": limit,
    }


def _pk_where_clause(meta: ManagedTableMeta, pk_values: dict[str, Any]) -> tuple[str, list[Any]]:
    clauses = [
        f"{quote_identifier(name)} = ${index + 1}"
        for index, name in enumerate(pk_values)
    ]
    return " AND ".join(clauses), list(pk_values.values())


async def insert_row(
    schema_name: str,
    table_name: str,
    *,
    values: dict[str, Any],
    operator: dict[str, Any],
) -> dict[str, Any]:
    """新增记录并写入审计日志，返回新行。"""

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            meta = await _load_table_meta(connection, schema_name, table_name)
            returning_list = ", ".join(
                quote_identifier(c.name) for c in meta.selectable_columns
            )
            if values:
                columns = list(values.keys())
                insert_sql = (
                    f"INSERT INTO {meta.qualified_name} "
                    f"({', '.join(quote_identifier(name) for name in columns)}) "
                    f"VALUES ({', '.join(f'${i + 1}' for i in range(len(columns)))}) "
                    f"RETURNING {returning_list}"
                )
                row = await connection.fetchrow(insert_sql, *values.values())
            else:
                row = await connection.fetchrow(
                    f"INSERT INTO {meta.qualified_name} DEFAULT VALUES RETURNING {returning_list}"
                )
            if row is None:
                raise ValueError("新增记录失败")
            new_row = serialize_row(row)
            pk_snapshot = {name: new_row.get(name) for name in meta.primary_key}
            await _write_change_log(
                connection,
                action="insert",
                operator=operator,
                meta=meta,
                pk_snapshot=pk_snapshot,
                before=None,
                after=new_row,
            )
            return new_row


async def update_row(
    schema_name: str,
    table_name: str,
    *,
    pk_values: dict[str, Any],
    values: dict[str, Any],
    operator: dict[str, Any],
) -> dict[str, Any]:
    """按主键更新记录并写入审计日志，返回更新后的行。"""

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            meta = await _load_table_meta(connection, schema_name, table_name)
            select_list = ", ".join(
                quote_identifier(column.name) for column in meta.selectable_columns
            )
            pk_where, pk_args = _pk_where_clause(meta, pk_values)
            before_row = await connection.fetchrow(
                f"SELECT {select_list} FROM {meta.qualified_name} WHERE {pk_where} FOR UPDATE",
                *pk_args,
            )
            if before_row is None:
                raise ValueError("记录不存在或已被删除")
            set_clause = ", ".join(
                f"{quote_identifier(name)} = ${len(pk_args) + index + 1}"
                for index, name in enumerate(values)
            )
            row = await connection.fetchrow(
                f"""
                UPDATE {meta.qualified_name}
                SET {set_clause}
                WHERE {pk_where}
                RETURNING {select_list}
                """,
                *pk_args,
                *values.values(),
            )
            if row is None:
                raise ValueError("记录不存在或已被删除")
            await _write_change_log(
                connection,
                action="update",
                operator=operator,
                meta=meta,
                pk_snapshot={name: serialize_value(value) for name, value in pk_values.items()},
                before=serialize_row(before_row),
                after=serialize_row(row),
            )
            return serialize_row(row)


async def delete_row(
    schema_name: str,
    table_name: str,
    *,
    pk_values: dict[str, Any],
    operator: dict[str, Any],
) -> dict[str, Any]:
    """按主键删除记录并写入审计日志，返回被删行快照。"""

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            meta = await _load_table_meta(connection, schema_name, table_name)
            select_list = ", ".join(
                quote_identifier(column.name) for column in meta.selectable_columns
            )
            pk_where, pk_args = _pk_where_clause(meta, pk_values)
            row = await connection.fetchrow(
                f"DELETE FROM {meta.qualified_name} WHERE {pk_where} RETURNING {select_list}",
                *pk_args,
            )
            if row is None:
                raise ValueError("记录不存在或已被删除")
            deleted = serialize_row(row)
            await _write_change_log(
                connection,
                action="delete",
                operator=operator,
                meta=meta,
                pk_snapshot={name: deleted.get(name) for name in meta.primary_key},
                before=deleted,
                after=None,
            )
            return deleted


async def _write_change_log(
    connection: asyncpg.Connection,
    *,
    action: str,
    operator: dict[str, Any],
    meta: ManagedTableMeta,
    pk_snapshot: dict[str, Any],
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> None:
    log_table = _qualified_change_log_table()
    await connection.execute(
        f"""
        INSERT INTO {log_table} (
            action, operator_id, operator_username, operator_display_name,
            schema_name, table_name, pk_json, before_json, after_json
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9::jsonb)
        """,
        action,
        operator.get("id"),
        operator.get("username") or "",
        operator.get("display_name") or operator.get("username") or "",
        meta.schema_name,
        meta.name,
        pk_snapshot,
        before,
        after,
    )


def _parse_jsonb(value: Any) -> Any:
    """asyncpg 默认把 jsonb 返回为字符串，这里统一解析为 Python 对象。"""

    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _change_log_item(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": row["id"],
        "occurred_at": row["occurred_at"].isoformat() if row["occurred_at"] else None,
        "action": row["action"],
        "operator_id": row["operator_id"],
        "operator_username": row["operator_username"],
        "operator_display_name": row["operator_display_name"],
        "schema_name": row["schema_name"],
        "table_name": row["table_name"],
        "pk": _parse_jsonb(row["pk_json"]) or {},
        "before": _parse_jsonb(row["before_json"]),
        "after": _parse_jsonb(row["after_json"]),
    }


async def list_change_logs(
    *,
    schema_name: str | None,
    table_name: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """分页读取数据变更日志，按时间倒序。"""

    await ensure_data_change_log_storage()
    log_table = _qualified_change_log_table()
    clauses: list[str] = []
    args: list[Any] = []
    if schema_name:
        args.append(schema_name)
        clauses.append(f"schema_name = ${len(args)}")
    if table_name:
        args.append(table_name)
        clauses.append(f"table_name = ${len(args)}")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        total_row = await connection.fetchrow(
            f"SELECT COUNT(*) AS total FROM {log_table} {where}", *args
        )
        rows = await connection.fetch(
            f"""
            SELECT
                id, occurred_at, action, operator_id, operator_username,
                operator_display_name, schema_name, table_name,
                pk_json, before_json, after_json
            FROM {log_table}
            {where}
            ORDER BY occurred_at DESC, id DESC
            LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
            """,
            *args,
            limit,
            offset,
        )
    items = [_change_log_item(row) for row in rows]
    return items, (total_row["total"] if total_row else 0)


async def get_columns(schema_name: str, table_name: str) -> list[dict[str, Any]]:
    """读取指定表的列元数据（供前端渲染表单）。"""

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        meta = await _load_table_meta(connection, schema_name, table_name)
    return list_columns(meta)
