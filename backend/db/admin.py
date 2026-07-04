from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import asyncpg

from backend.auth.security import hash_password
from backend.auth.store import AUTH_SCHEMA, USER_ROLES
from backend.db.postgres import (
    REFERENCE_SCHEMA,
    VIEW_SCHEMA,
    ensure_pool,
    fetch,
    fetchrow,
    list_map_views,
    list_reference_layers,
)


ADMIN_SCHEMA = "app_admin"
LAYER_METADATA_TABLE = "layer_metadata"


def _qualified_layer_table() -> str:
    return f'"{ADMIN_SCHEMA}"."{LAYER_METADATA_TABLE}"'


# ──────────────────────────────────────────────
#  Dashboard
# ──────────────────────────────────────────────


async def get_dashboard_stats() -> dict[str, Any]:
    """聚合管理概览的 KPI 数据。"""

    user_count = await fetchrow(
        f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE role = 'admin') AS admin_count,
            COUNT(*) FILTER (WHERE role = 'investigator') AS investigator_count,
            COUNT(*) FILTER (WHERE is_active = TRUE) AS active_count
        FROM "{AUTH_SCHEMA}"."users"
        """
    )

    metadata_layers = await list_layer_metadata()

    # Count views in views schema (dynamic — what actually exists in DB)
    views_row = await fetch(
        """
        SELECT COUNT(DISTINCT v.table_name) AS total
        FROM information_schema.views AS v
        JOIN information_schema.columns AS c
          ON c.table_schema = v.table_schema AND c.table_name = v.table_name
        WHERE v.table_schema = $1
          AND c.column_name = 'geom'
        """,
        VIEW_SCHEMA,
    )

    # Count reference layers
    ref_row = await fetch(
        """
        SELECT COUNT(DISTINCT t.table_name) AS total
        FROM information_schema.tables AS t
        JOIN information_schema.columns AS c
          ON c.table_schema = t.table_schema AND c.table_name = t.table_name
        WHERE t.table_schema = $1
          AND t.table_type = 'BASE TABLE'
          AND c.column_name = 'geom'
        """,
        REFERENCE_SCHEMA,
    )

    return {
        "users": {
            "total": user_count["total"] if user_count else 0,
            "admin_count": user_count["admin_count"] if user_count else 0,
            "investigator_count": user_count["investigator_count"] if user_count else 0,
            "active_count": user_count["active_count"] if user_count else 0,
        },
        "layers": {
            "total": len(metadata_layers),
            "view_count": len(
                [layer for layer in metadata_layers if layer["layer_type"] == "view"]
            ),
            "reference_count": len(
                [layer for layer in metadata_layers if layer["layer_type"] == "reference"]
            ),
        },
        "database_views": views_row[0]["total"] if views_row else 0,
        "database_reference_layers": ref_row[0]["total"] if ref_row else 0,
    }


# ──────────────────────────────────────────────
#  Layer Metadata
# ──────────────────────────────────────────────


LayerMetadataDict = dict[str, Any]


async def ensure_layer_metadata_storage() -> None:
    """初始化图层元数据表结构。"""

    layer_table = _qualified_layer_table()
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{ADMIN_SCHEMA}"')
            await connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {layer_table} (
                    id BIGSERIAL PRIMARY KEY,
                    layer_key TEXT NOT NULL,
                    layer_type TEXT NOT NULL CHECK (layer_type IN ('view', 'reference')),
                    display_name TEXT NULL,
                    sort_order INT NOT NULL DEFAULT 0,
                    default_visible BOOLEAN NOT NULL DEFAULT FALSE,
                    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await connection.execute(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_layer_metadata_type_key
                ON {layer_table} (layer_type, layer_key)
                """
            )


async def sync_layer_metadata() -> list[LayerMetadataDict]:
    """将数据库中真实存在的地图图层补齐到元数据表。"""

    await ensure_layer_metadata_storage()

    map_views = await list_map_views()
    reference_layers = await list_reference_layers()
    detected_layers: list[LayerMetadataDict] = [
        {
            "layer_key": view["name"],
            "layer_type": "view",
            "display_name": None,
            "default_visible": False,
        }
        for view in map_views
    ]
    detected_layers.extend(
        {
            "layer_key": layer["name"],
            "layer_type": "reference",
            "display_name": layer.get("label") or layer["name"],
            "default_visible": bool(layer.get("default_visible")),
        }
        for layer in reference_layers
    )

    rows = await fetch(
        f"""
        SELECT layer_type, layer_key, sort_order
        FROM {_qualified_layer_table()}
        """
    )
    existing_keys = {(row["layer_type"], row["layer_key"]) for row in rows}
    next_sort_order = {"view": 0, "reference": 0}
    for row in rows:
        layer_type = row["layer_type"]
        next_sort_order[layer_type] = max(
            next_sort_order.get(layer_type, 0),
            int(row["sort_order"]) + 1,
        )

    for layer in detected_layers:
        layer_type = layer["layer_type"]
        layer_key = layer["layer_key"]
        if (layer_type, layer_key) in existing_keys:
            continue

        sort_order = next_sort_order[layer_type]
        next_sort_order[layer_type] += 1
        await fetch(
            f"""
            INSERT INTO {_qualified_layer_table()} (
                layer_key,
                layer_type,
                display_name,
                sort_order,
                default_visible,
                is_enabled
            )
            VALUES ($1, $2, $3, $4, $5, TRUE)
            ON CONFLICT (layer_type, layer_key) DO NOTHING
            """,
            layer_key,
            layer_type,
            layer["display_name"],
            sort_order,
            layer["default_visible"],
        )

    return detected_layers


async def list_layer_metadata() -> list[LayerMetadataDict]:
    """列出已注册的所有图层元数据，按 layer_type 分组后按 sort_order 排序。"""

    detected_layers = await sync_layer_metadata()
    view_layer_keys = [
        layer["layer_key"]
        for layer in detected_layers
        if layer["layer_type"] == "view"
    ]
    reference_layer_keys = [
        layer["layer_key"]
        for layer in detected_layers
        if layer["layer_type"] == "reference"
    ]

    rows = await fetch(
        f"""
        SELECT
            id,
            layer_key,
            layer_type,
            display_name,
            sort_order,
            default_visible,
            is_enabled,
            updated_at
        FROM {_qualified_layer_table()}
        WHERE
            (layer_type = 'view' AND layer_key = ANY($1::text[]))
            OR (layer_type = 'reference' AND layer_key = ANY($2::text[]))
        ORDER BY layer_type, sort_order, layer_key
        """,
        view_layer_keys,
        reference_layer_keys,
    )
    return [
        {
            "id": row["id"],
            "layer_key": row["layer_key"],
            "layer_type": row["layer_type"],
            "display_name": row["display_name"],
            "sort_order": row["sort_order"],
            "default_visible": bool(row["default_visible"]),
            "is_enabled": bool(row["is_enabled"]),
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]


async def get_layer_metadata_by_key(layer_type: str, layer_key: str) -> LayerMetadataDict | None:
    """按类型和键读取单条元数据。"""

    await sync_layer_metadata()

    row = await fetchrow(
        f"""
        SELECT
            id,
            layer_key,
            layer_type,
            display_name,
            sort_order,
            default_visible,
            is_enabled,
            updated_at
        FROM {_qualified_layer_table()}
        WHERE layer_type = $1 AND layer_key = $2
        """,
        layer_type,
        layer_key,
    )
    if row is None:
        return None
    return {
        "id": row["id"],
        "layer_key": row["layer_key"],
        "layer_type": row["layer_type"],
        "display_name": row["display_name"],
        "sort_order": row["sort_order"],
        "default_visible": bool(row["default_visible"]),
        "is_enabled": bool(row["is_enabled"]),
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


async def list_enabled_map_views() -> list[dict[str, Any]]:
    """列出地图路由中可展示的已启用点位图层。"""

    metadata_rows = [
        row
        for row in await list_layer_metadata()
        if row["layer_type"] == "view" and row["is_enabled"]
    ]
    views_by_name = {view["name"]: view for view in await list_map_views()}

    enabled_views: list[dict[str, Any]] = []
    for row in metadata_rows:
        view = views_by_name.get(row["layer_key"])
        if view is None:
            continue

        enabled_views.append(
            {
                **view,
                "label": row["display_name"] or view["name"],
            }
        )

    return enabled_views


async def get_enabled_map_view(view_name: str) -> dict[str, Any] | None:
    """读取地图路由中可访问的单个点位图层。"""

    views = await list_enabled_map_views()
    for view in views:
        if view["name"] == view_name:
            return view
    return None


async def list_enabled_reference_layers() -> list[dict[str, Any]]:
    """列出地图路由中可展示的已启用参考图层。"""

    metadata_rows = [
        row
        for row in await list_layer_metadata()
        if row["layer_type"] == "reference" and row["is_enabled"]
    ]
    layers_by_name = {layer["name"]: layer for layer in await list_reference_layers()}

    enabled_layers: list[dict[str, Any]] = []
    for row in metadata_rows:
        layer = layers_by_name.get(row["layer_key"])
        if layer is None:
            continue

        enabled_layers.append(
            {
                **layer,
                "label": row["display_name"] or layer["label"] or layer["name"],
                "default_visible": row["default_visible"],
            }
        )

    return enabled_layers


async def get_enabled_reference_layer(layer_name: str) -> dict[str, Any] | None:
    """读取地图路由中可访问的单个参考图层。"""

    layers = await list_enabled_reference_layers()
    for layer in layers:
        if layer["name"] == layer_name:
            return layer
    return None


async def batch_upsert_layer_metadata(
    items: list[LayerMetadataDict],
) -> list[LayerMetadataDict]:
    """批量更新图层元数据（按 layer_type + layer_key 匹配）。返回更新后的所有元数据。"""

    await ensure_layer_metadata_storage()

    qualified = _qualified_layer_table()
    for item in items:
        await fetch(
            f"""
            INSERT INTO {qualified} (layer_key, layer_type, display_name, sort_order, default_visible, is_enabled)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (layer_type, layer_key)
            DO UPDATE SET
                display_name   = COALESCE(EXCLUDED.display_name, {qualified}.display_name),
                sort_order     = EXCLUDED.sort_order,
                default_visible = EXCLUDED.default_visible,
                is_enabled     = EXCLUDED.is_enabled,
                updated_at     = NOW()
            """,
            item.get("layer_key"),
            item.get("layer_type"),
            item.get("display_name"),
            item.get("sort_order", 0),
            item.get("default_visible", False),
            item.get("is_enabled", True),
        )

    return await list_layer_metadata()


# ──────────────────────────────────────────────
#  User Management
# ──────────────────────────────────────────────


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
