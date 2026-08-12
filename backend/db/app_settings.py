"""应用设置（app_admin.app_settings）：管理员在界面上可调的运行时配置。"""

from __future__ import annotations

from backend.db.layer_metadata import ADMIN_SCHEMA
from backend.db.pool import ensure_pool, fetch

APP_SETTINGS_TABLE = "app_settings"


def _qualified_table() -> str:
    return f'"{ADMIN_SCHEMA}"."{APP_SETTINGS_TABLE}"'


async def ensure_app_settings_storage() -> None:
    """初始化应用设置表结构。"""

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{ADMIN_SCHEMA}"')
            await connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {_qualified_table()} (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_by TEXT NOT NULL DEFAULT ''
                )
                """
            )


async def load_app_settings() -> dict[str, str]:
    """读取全部应用设置（key -> value），不存在时返回空字典。"""

    await ensure_app_settings_storage()
    rows = await fetch(f"SELECT key, value FROM {_qualified_table()}")
    return {str(row["key"]): str(row["value"]) for row in rows}


async def load_app_settings_meta(keys: list[str]) -> dict[str, dict[str, str]]:
    """读取指定 key 的更新人与更新时间（ISO 格式），用于界面展示。"""

    if not keys:
        return {}
    await ensure_app_settings_storage()
    rows = await fetch(
        f"SELECT key, updated_by, updated_at FROM {_qualified_table()} WHERE key = ANY($1::text[])",
        list(keys),
    )
    meta: dict[str, dict[str, str]] = {}
    for row in rows:
        updated_at = row["updated_at"]
        meta[str(row["key"])] = {
            "updated_by": str(row["updated_by"] or ""),
            "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at or ""),
        }
    return meta


async def save_app_settings(values: dict[str, str], *, updated_by: str = "") -> None:
    """批量覆盖写入应用设置（按 key upsert）。"""

    await ensure_app_settings_storage()
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            for key, value in values.items():
                await connection.execute(
                    f"""
                    INSERT INTO {_qualified_table()} (key, value, updated_at, updated_by)
                    VALUES ($1, $2, NOW(), $3)
                    ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value,
                        updated_at = NOW(),
                        updated_by = EXCLUDED.updated_by
                    """,
                    key,
                    value,
                    updated_by,
                )
