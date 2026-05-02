from __future__ import annotations

from typing import Any

from backend.auth.security import hash_password, verify_password
from backend.config import get_settings
from backend.db.postgres import ensure_pool, fetchrow


AUTH_SCHEMA = "app_auth"
AUTH_USER_TABLE = "users"


def _qualified_users_table() -> str:
    return f'"{AUTH_SCHEMA}"."{AUTH_USER_TABLE}"'


def serialize_user(row: Any) -> dict[str, Any]:
    """将数据库记录转换为对外暴露的用户信息。"""

    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "is_active": bool(row["is_active"]),
        "last_login_at": row["last_login_at"].isoformat() if row["last_login_at"] else None,
    }


async def ensure_auth_storage() -> None:
    """初始化认证表结构并写入默认管理员账号。"""

    settings = get_settings()
    username = settings.auth_default_admin_username.strip()
    password = settings.auth_default_admin_password.strip()
    display_name = settings.auth_default_admin_display_name.strip() or username

    if not username or not password:
        raise RuntimeError("默认管理员账号或密码为空，无法初始化认证模块")

    users_table = _qualified_users_table()
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{AUTH_SCHEMA}"')
            await connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {users_table} (
                    id BIGSERIAL PRIMARY KEY,
                    username TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    last_login_at TIMESTAMPTZ NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await connection.execute(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS auth_users_username_lower_uidx
                ON {users_table} ((LOWER(username)))
                """
            )
            await connection.execute(
                f"""
                INSERT INTO {users_table} (username, display_name, password_hash, is_active)
                VALUES ($1, $2, $3, TRUE)
                ON CONFLICT DO NOTHING
                """,
                username,
                display_name,
                hash_password(password),
            )


async def get_user_by_username(username: str) -> dict[str, Any] | None:
    """按用户名读取用户。"""

    row = await fetchrow(
        f"""
        SELECT
            id,
            username,
            display_name,
            password_hash,
            is_active,
            last_login_at
        FROM {_qualified_users_table()}
        WHERE LOWER(username) = LOWER($1)
        LIMIT 1
        """,
        username.strip(),
    )
    if row is None:
        return None
    return dict(row)


async def get_active_user(username: str) -> dict[str, Any] | None:
    """读取启用中的用户。"""

    user = await get_user_by_username(username)
    if user is None or not user["is_active"]:
        return None
    return serialize_user(user)


async def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """校验用户名与密码，成功时返回用户信息。"""

    user = await get_user_by_username(username)
    if user is None or not user["is_active"]:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            f"""
            UPDATE {_qualified_users_table()}
            SET last_login_at = NOW(),
                updated_at = NOW()
            WHERE id = $1
            """,
            user["id"],
        )

    user["last_login_at"] = None
    return serialize_user(user)
