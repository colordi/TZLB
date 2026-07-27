from __future__ import annotations

import json
from typing import Any

import asyncpg

from backend.config import get_settings

_pool: asyncpg.Pool | None = None


async def _init_connection(connection: asyncpg.Connection) -> None:
    """注册 JSONB codec，使 JSONB 列自动解码为 Python dict/list。"""

    await connection.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


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
            init=_init_connection,
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
