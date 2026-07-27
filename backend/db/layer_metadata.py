from __future__ import annotations

import json
from typing import Any

from backend.db.pool import ensure_pool, fetch, fetchrow
from backend.db.map_queries import list_map_views, list_reference_layers

ADMIN_SCHEMA = "app_admin"
LAYER_METADATA_TABLE = "layer_metadata"
LayerMetadataDict = dict[str, Any]


def _qualified_layer_table() -> str:
    return f'"{ADMIN_SCHEMA}"."{LAYER_METADATA_TABLE}"'


def _parse_default_filters(value: Any) -> dict[str, str]:
    """解析 JSONB 字段，兼容 dict（codec 已注册）和 str（未注册）两种返回。"""

    if value is None:
        return {}
    if isinstance(value, str):
        return json.loads(value) if value.strip() else {}
    if isinstance(value, dict):
        return value
    return dict(value)


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
                    default_filters JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await connection.execute(
                f"""
                ALTER TABLE {layer_table}
                ADD COLUMN IF NOT EXISTS default_filters JSONB NOT NULL DEFAULT '{{}}'::jsonb
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
            default_filters,
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
            "default_filters": _parse_default_filters(row["default_filters"]),
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
            default_filters,
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
        "default_filters": _parse_default_filters(row["default_filters"]),
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
                "default_filters": _parse_default_filters(row.get("default_filters")),
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
        default_filters = item.get("default_filters") or {}
        if not isinstance(default_filters, dict):
            raise ValueError("default_filters 必须是对象")
        await fetch(
            f"""
            INSERT INTO {qualified} (
                layer_key, layer_type, display_name, sort_order,
                default_visible, is_enabled, default_filters
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
            ON CONFLICT (layer_type, layer_key)
            DO UPDATE SET
                display_name    = COALESCE(EXCLUDED.display_name, {qualified}.display_name),
                sort_order      = EXCLUDED.sort_order,
                default_visible = EXCLUDED.default_visible,
                is_enabled      = EXCLUDED.is_enabled,
                default_filters = EXCLUDED.default_filters,
                updated_at      = NOW()
            """,
            item.get("layer_key"),
            item.get("layer_type"),
            item.get("display_name"),
            item.get("sort_order", 0),
            item.get("default_visible", False),
            item.get("is_enabled", True),
            json.dumps(default_filters, ensure_ascii=False),
        )

    return await list_layer_metadata()
