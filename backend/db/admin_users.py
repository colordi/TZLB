from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import asyncpg

from backend.auth.security import hash_password
from backend.auth.store import AUTH_SCHEMA, USER_ROLES
from backend.db.pool import fetch, fetchrow

UserDict = dict[str, Any]


async def list_users() -> list[UserDict]:
    """列出所有用户。"""

    rows = await fetch(
        f"""
        SELECT id, username, display_name, role, is_active, last_login_at, created_at
        FROM "{AUTH_SCHEMA}"."users"
        ORDER BY created_at
        """
    )
    return [
        {
            "id": row["id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "last_login_at": row["last_login_at"].isoformat() if row["last_login_at"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


async def create_user(
    username: str,
    password: str,
    display_name: str = "",
    role: str = "investigator",
) -> UserDict:
    """创建新用户。"""

    normalized_username = username.strip()
    if not normalized_username:
        raise ValueError("用户名不能为空")

    if role not in USER_ROLES:
        raise ValueError(f"角色必须是 {'/'.join(USER_ROLES)} 之一")

    normalized_password = password.strip()
    if len(normalized_password) < 6:
        raise ValueError("密码长度不能少于 6 位")

    display_name = (display_name or "").strip() or normalized_username
    password_hash = hash_password(normalized_password)

    try:
        row = await fetchrow(
            f"""
            INSERT INTO "{AUTH_SCHEMA}"."users"
                (username, display_name, password_hash, role, is_active)
            VALUES ($1, $2, $3, $4, TRUE)
            RETURNING id, username, display_name, role, is_active, created_at
            """,
            normalized_username,
            display_name,
            password_hash,
            role,
        )
    except asyncpg.UniqueViolationError:
        raise ValueError(f"用户名已存在：{normalized_username}")

    if row is None:
        raise RuntimeError("创建用户失败")

    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


async def update_user(
    user_id: int,
    *,
    display_name: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> UserDict | None:
    """更新用户信息。不能修改用户名。"""

    set_clauses: list[str] = []
    args: list[Any] = []
    arg_index = 0

    if display_name is not None:
        arg_index += 1
        set_clauses.append(f"display_name = ${arg_index}")
        args.append(display_name.strip() or "用户")

    if role is not None:
        if role not in USER_ROLES:
            raise ValueError(f"角色必须是 {'/'.join(USER_ROLES)} 之一")

        # Prevent removing the last admin
        if role != "admin":
            admin_count = await fetchrow(
                f"""SELECT COUNT(*) AS cnt FROM "{AUTH_SCHEMA}"."users" WHERE role = 'admin' AND id != $1""",
                user_id,
            )
            if admin_count and admin_count["cnt"] == 0:
                raise ValueError("不能移除最后一个管理员角色")

        arg_index += 1
        set_clauses.append(f"role = ${arg_index}")
        args.append(role)

    if is_active is not None:
        arg_index += 1
        set_clauses.append(f"is_active = ${arg_index}")
        args.append(is_active)

    if not set_clauses:
        return await get_user_by_id(user_id)

    arg_index += 1
    set_clauses.append(f"updated_at = ${arg_index}")
    args.append(datetime.now(timezone.utc))

    args.append(user_id)
    row = await fetchrow(
        f"""
        UPDATE "{AUTH_SCHEMA}"."users"
        SET {', '.join(set_clauses)}
        WHERE id = ${arg_index + 1}
        RETURNING id, username, display_name, role, is_active, last_login_at, created_at
        """,
        *args,
    )
    if row is None:
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "last_login_at": row["last_login_at"].isoformat() if row["last_login_at"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


async def get_user_by_id(user_id: int) -> UserDict | None:
    """按 ID 读取用户。"""

    row = await fetchrow(
        f"""
        SELECT id, username, display_name, role, is_active, last_login_at, created_at
        FROM "{AUTH_SCHEMA}"."users"
        WHERE id = $1
        """,
        user_id,
    )
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "last_login_at": row["last_login_at"].isoformat() if row["last_login_at"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


async def reset_user_password(user_id: int, new_password: str) -> bool:
    """重置用户密码。返回是否成功。"""

    normalized_password = new_password.strip()
    if len(normalized_password) < 6:
        raise ValueError("密码长度不能少于 6 位")

    password_hash = hash_password(normalized_password)

    row = await fetchrow(
        f"""
        UPDATE "{AUTH_SCHEMA}"."users"
        SET password_hash = $1, updated_at = $2
        WHERE id = $3
        RETURNING id
        """,
        password_hash,
        datetime.now(timezone.utc),
        user_id,
    )
    return row is not None


async def delete_user(user_id: int) -> bool:
    """删除用户。返回是否成功。不允许删除最后一个 admin。"""

    user = await get_user_by_id(user_id)
    if user is None:
        return False

    if user["role"] == "admin":
        admin_count = await fetchrow(
            f"""SELECT COUNT(*) AS cnt FROM "{AUTH_SCHEMA}"."users" WHERE role = 'admin'""",
        )
        if admin_count and admin_count["cnt"] <= 1:
            raise ValueError("不能删除最后一个管理员账号")

    row = await fetchrow(
        f"""DELETE FROM "{AUTH_SCHEMA}"."users" WHERE id = $1 RETURNING id""",
        user_id,
    )
    return row is not None
