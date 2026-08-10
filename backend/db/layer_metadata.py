from __future__ import annotations

import json
import re
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


DEFAULT_STYLE: dict[str, Any] = {"color": None, "show_label": False, "label_column": None}


def _parse_style(value: Any) -> dict[str, Any]:
    """解析样式配置 JSONB 字段，缺省键补默认值。"""

    parsed = _parse_default_filters(value)
    return {
        "color": parsed.get("color") or None,
        "show_label": bool(parsed.get("show_label")),
        "label_column": parsed.get("label_column") or None,
    }


def _validate_style(style: Any) -> dict[str, Any]:
    """校验待写入的样式配置，非法时抛 ValueError。"""

    if style is None:
        return dict(DEFAULT_STYLE)
    if not isinstance(style, dict):
        raise ValueError("style 必须是对象")
    color = style.get("color") or None
    if color is not None and not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise ValueError(f"style.color 必须是 #RRGGBB 形式的色值：{color}")
    label_column = style.get("label_column") or None
    if label_column is not None and len(label_column) > 64:
        raise ValueError("style.label_column 超长")
    return {
        "color": color,
        "show_label": bool(style.get("show_label")),
        "label_column": label_column,
    }


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
                ALTER TABLE {layer_table}
                ADD COLUMN IF NOT EXISTS style JSONB NOT NULL DEFAULT '{{}}'::jsonb
                """
            )
            await connection.execute(
                f"""
                ALTER TABLE {layer_table}
                ADD COLUMN IF NOT EXISTS base_table TEXT NULL
                """
            )
            await connection.execute(
                f"""
                ALTER TABLE {layer_table}
                ADD COLUMN IF NOT EXISTS source_definition JSONB NULL
                """
            )
            await connection.execute(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_layer_metadata_type_key
                ON {layer_table} (layer_type, layer_key)
                """
            )
    await backfill_task_view_source_metadata()


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


def _parse_source_definition(value: Any) -> dict[str, Any] | None:
    """解析任务视图源定义 JSONB。"""

    if value is None:
        return None
    if isinstance(value, str):
        if not value.strip():
            return None
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
    if isinstance(value, dict):
        return value
    return dict(value)


def parse_task_view_source_from_viewdef(viewdef: str) -> dict[str, Any]:
    """从 pg_get_viewdef 文本尽量还原 base_table 与 codes 清单。"""

    text = viewdef or ""
    base_table = None
    quoted = re.search(
        r'FROM\s+sites\.(?:"([^"]+)"|([A-Za-z_][A-Za-z0-9_]*))',
        text,
        flags=re.IGNORECASE,
    )
    if quoted:
        base_table = quoted.group(1) or quoted.group(2)

    codes: list[str] = []
    in_match = re.search(
        r"""IN\s*\(([^)]*)\)""",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # 仅当 IN 子句看起来是编号清单（含引号字面量）时解析
    if in_match and ("编号" in text[max(0, in_match.start() - 80) : in_match.start()]):
        raw_items = in_match.group(1)
        codes = [
            item.replace("''", "'").strip()
            for item in re.findall(r"'((?:[^']|'')*)'", raw_items)
            if item and item.strip()
        ]

    return {
        "base_table": base_table,
        "codes": codes,
    }


async def backfill_task_view_source_metadata() -> None:
    """为缺少 base_table 的 task_* 视图从 viewdef 回填源信息。"""

    rows = await fetch(
        f"""
        SELECT layer_key, base_table, source_definition
        FROM {_qualified_layer_table()}
        WHERE layer_type = 'view'
          AND layer_key LIKE 'task\\_%' ESCAPE '\\'
          AND (base_table IS NULL OR BTRIM(base_table) = '')
        """
    )
    for row in rows:
        view_name = row["layer_key"]
        try:
            viewdef = await fetchrow(
                "SELECT pg_get_viewdef($1::regclass, true) AS definition",
                f"views.{view_name}",
            )
        except Exception:  # noqa: BLE001
            continue
        if not viewdef or not viewdef.get("definition"):
            continue
        parsed = parse_task_view_source_from_viewdef(viewdef["definition"])
        if not parsed.get("base_table"):
            continue
        source_definition = {
            "base_table": parsed["base_table"],
            "codes": parsed.get("codes") or [],
            "backfilled": True,
        }
        await fetch(
            f"""
            UPDATE {_qualified_layer_table()}
            SET
                base_table = $2,
                source_definition = COALESCE(source_definition, $3::jsonb),
                updated_at = NOW()
            WHERE layer_type = 'view' AND layer_key = $1
            """,
            view_name,
            parsed["base_table"],
            json.dumps(source_definition, ensure_ascii=False),
        )


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
            style,
            base_table,
            source_definition,
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
    reference_columns = {
        layer["name"]: layer["columns"] for layer in await list_reference_layers()
    }
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
            "style": _parse_style(row["style"]),
            "base_table": row.get("base_table"),
            "source_definition": _parse_source_definition(row.get("source_definition")),
            "columns": (
                reference_columns.get(row["layer_key"])
                if row["layer_type"] == "reference"
                else None
            ),
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
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
            style,
            base_table,
            source_definition,
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
        "style": _parse_style(row["style"]),
        "base_table": row.get("base_table"),
        "source_definition": _parse_source_definition(row.get("source_definition")),
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
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

        site_add = await _build_site_add_for_view_metadata(row)
        enabled_views.append(
            {
                **view,
                "label": row["display_name"] or view["name"],
                "default_filters": _parse_default_filters(row.get("default_filters")),
                "base_table": row.get("base_table"),
                "site_add": site_add,
            }
        )

    return enabled_views


async def _build_site_add_for_view_metadata(row: LayerMetadataDict) -> dict[str, Any]:
    """根据图层元数据构造 site_add 能力描述。"""

    from backend.db.generic_sites import (
        GenericSiteNotSupportedError,
        build_site_add_config_payload,
        resolve_site_table_profile,
    )

    view_name = row.get("layer_key") or ""
    source = row.get("source_definition") or {}
    base_table = (row.get("base_table") or source.get("base_table") or "").strip() or None
    codes = source.get("codes") if isinstance(source, dict) else None
    if not isinstance(codes, list):
        codes = []
    has_code_list_filter = bool(codes)

    # 仅任务视图开放通用添加点位
    if not str(view_name).startswith("task_"):
        return build_site_add_config_payload(
            enabled=False,
            base_table=base_table,
            has_code_list_filter=has_code_list_filter,
            reason="仅任务视图支持添加点位",
        )
    if not base_table:
        return build_site_add_config_payload(
            enabled=False,
            base_table=None,
            has_code_list_filter=has_code_list_filter,
            reason="任务视图未绑定基础点位表",
        )
    try:
        profile = await resolve_site_table_profile(base_table)
    except GenericSiteNotSupportedError as exc:
        return build_site_add_config_payload(
            enabled=False,
            base_table=base_table,
            has_code_list_filter=has_code_list_filter,
            reason=str(exc),
        )
    return build_site_add_config_payload(
        enabled=True,
        base_table=base_table,
        profile=profile,
        has_code_list_filter=has_code_list_filter,
    )

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
                "style": row["style"],
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
        style = _validate_style(item.get("style"))
        source_definition = item.get("source_definition")
        if source_definition is not None and not isinstance(source_definition, dict):
            raise ValueError("source_definition 必须是对象")
        base_table = item.get("base_table")
        if base_table is not None:
            base_table = str(base_table).strip() or None

        await fetch(
            f"""
            INSERT INTO {qualified} (
                layer_key, layer_type, display_name, sort_order,
                default_visible, is_enabled, default_filters, style,
                base_table, source_definition
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb,
                $9, $10::jsonb
            )
            ON CONFLICT (layer_type, layer_key)
            DO UPDATE SET
                display_name    = COALESCE(EXCLUDED.display_name, {qualified}.display_name),
                sort_order      = EXCLUDED.sort_order,
                default_visible = EXCLUDED.default_visible,
                is_enabled      = EXCLUDED.is_enabled,
                default_filters = EXCLUDED.default_filters,
                style           = EXCLUDED.style,
                base_table      = COALESCE(EXCLUDED.base_table, {qualified}.base_table),
                source_definition = COALESCE(
                    EXCLUDED.source_definition, {qualified}.source_definition
                ),
                updated_at      = NOW()
            """,
            item.get("layer_key"),
            item.get("layer_type"),
            item.get("display_name"),
            item.get("sort_order", 0),
            item.get("default_visible", False),
            item.get("is_enabled", True),
            json.dumps(default_filters, ensure_ascii=False),
            json.dumps(style, ensure_ascii=False),
            base_table,
            (
                json.dumps(source_definition, ensure_ascii=False)
                if source_definition is not None
                else None
            ),
        )

    return await list_layer_metadata()
