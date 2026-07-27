from __future__ import annotations

from typing import Any

from backend.auth.store import AUTH_SCHEMA
from backend.db.layer_metadata import list_layer_metadata
from backend.db.map_queries import REFERENCE_SCHEMA, VIEW_SCHEMA
from backend.db.pool import fetch, fetchrow


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
