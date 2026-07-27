from __future__ import annotations

from typing import Any

from backend.db.layer_metadata import ADMIN_SCHEMA
from backend.db.pool import ensure_pool, fetch, fetchrow

OPERATION_LOG_TABLE = "点位操作日志"
OPERATION_LOG_ACTION_DELETE_WHITE_MOTH_SITE = "删除美国白蛾点位"
OPERATION_LOG_ACTION_DELETE_OTHER_PEST_SITE = "删除其他害虫点位"


def _qualified_operation_log_table() -> str:
    return f'"{ADMIN_SCHEMA}"."{OPERATION_LOG_TABLE}"'


async def ensure_operation_log_storage() -> None:
    """初始化点位操作日志表结构。"""

    log_table = _qualified_operation_log_table()
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
                    operator_role TEXT NOT NULL,
                    site_code TEXT NOT NULL,
                    site_name TEXT NOT NULL DEFAULT '',
                    locality TEXT NOT NULL DEFAULT '',
                    longitude DOUBLE PRECISION NULL,
                    latitude DOUBLE PRECISION NULL,
                    survey_record_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            await connection.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_op_log_occurred_at
                ON {log_table} (occurred_at DESC)
                """
            )


async def list_operation_logs(
    *, limit: int = 100, offset: int = 0
) -> tuple[list[dict[str, Any]], int]:
    """分页读取点位操作日志，按时间倒序。返回 (items, total)。"""

    log_table = _qualified_operation_log_table()
    await ensure_operation_log_storage()

    total_row = await fetchrow(f"SELECT COUNT(*) AS total FROM {log_table}")
    total = total_row["total"] if total_row else 0

    rows = await fetch(
        f"""
        SELECT
            id,
            occurred_at,
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
        FROM {log_table}
        ORDER BY occurred_at DESC, id DESC
        LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )
    items = [
        {
            "id": row["id"],
            "occurred_at": row["occurred_at"].isoformat() if row["occurred_at"] else None,
            "action": row["action"],
            "operator_id": row["operator_id"],
            "operator_username": row["operator_username"],
            "operator_display_name": row["operator_display_name"],
            "operator_role": row["operator_role"],
            "site_code": row["site_code"],
            "site_name": row["site_name"],
            "locality": row["locality"],
            "longitude": row["longitude"],
            "latitude": row["latitude"],
            "survey_record_count": row["survey_record_count"],
        }
        for row in rows
    ]
    return items, total
