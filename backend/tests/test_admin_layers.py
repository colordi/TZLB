from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from backend.db.admin import (
    get_dashboard_stats,
    list_enabled_map_views,
    list_enabled_reference_layers,
    list_layer_metadata,
)


class AdminLayerMetadataTest(unittest.IsolatedAsyncioTestCase):
    async def test_list_layer_metadata_syncs_detected_layers_when_table_is_empty(self) -> None:
        updated_at = datetime(2026, 7, 4, tzinfo=timezone.utc)

        async def fake_fetch(query: str, *args):
            normalized_query = " ".join(query.split())
            if normalized_query.startswith("SELECT layer_type, layer_key, sort_order"):
                return []

            if normalized_query.startswith("INSERT INTO"):
                return []

            if normalized_query.startswith("SELECT id, layer_key"):
                self.assertEqual(args, (["虫情总览"], ["通州区行政区边界"]))
                return [
                    {
                        "id": 1,
                        "layer_key": "虫情总览",
                        "layer_type": "view",
                        "display_name": None,
                        "sort_order": 0,
                        "default_visible": False,
                        "is_enabled": True,
                        "updated_at": updated_at,
                    },
                    {
                        "id": 2,
                        "layer_key": "通州区行政区边界",
                        "layer_type": "reference",
                        "display_name": "通州区行政区边界",
                        "sort_order": 0,
                        "default_visible": True,
                        "is_enabled": True,
                        "updated_at": updated_at,
                    },
                ]

            self.fail(f"未预期的查询：{query}")

        fetch_mock = AsyncMock(side_effect=fake_fetch)

        with (
            patch("backend.db.admin.ensure_layer_metadata_storage", new=AsyncMock()),
            patch(
                "backend.db.admin.list_map_views",
                new=AsyncMock(return_value=[{"name": "虫情总览", "columns": ["编号"]}]),
            ),
            patch(
                "backend.db.admin.list_reference_layers",
                new=AsyncMock(
                    return_value=[
                        {
                            "name": "通州区行政区边界",
                            "label": "通州区行政区边界",
                            "columns": ["gid"],
                            "default_visible": True,
                        }
                    ]
                ),
            ),
            patch("backend.db.admin.fetch", new=fetch_mock),
        ):
            payload = await list_layer_metadata()

        self.assertEqual([layer["layer_key"] for layer in payload], ["虫情总览", "通州区行政区边界"])
        insert_calls = [
            call
            for call in fetch_mock.await_args_list
            if "INSERT INTO" in " ".join(call.args[0].split())
        ]
        self.assertEqual(len(insert_calls), 2)
        self.assertEqual(insert_calls[0].args[1:], ("虫情总览", "view", None, 0, False))
        self.assertEqual(
            insert_calls[1].args[1:],
            ("通州区行政区边界", "reference", "通州区行政区边界", 0, True),
        )

    async def test_dashboard_layer_counts_use_synchronized_metadata(self) -> None:
        with (
            patch(
                "backend.db.admin.fetchrow",
                new=AsyncMock(
                    return_value={
                        "total": 3,
                        "admin_count": 1,
                        "investigator_count": 2,
                        "active_count": 3,
                    }
                ),
            ),
            patch(
                "backend.db.admin.list_layer_metadata",
                new=AsyncMock(
                    return_value=[
                        {"layer_type": "view"},
                        {"layer_type": "view"},
                        {"layer_type": "reference"},
                    ]
                ),
            ),
            patch(
                "backend.db.admin.fetch",
                new=AsyncMock(
                    side_effect=[
                        [{"total": 2}],
                        [{"total": 1}],
                    ]
                ),
            ),
        ):
            payload = await get_dashboard_stats()

        self.assertEqual(payload["layers"], {"total": 3, "view_count": 2, "reference_count": 1})
        self.assertEqual(payload["database_views"], 2)
        self.assertEqual(payload["database_reference_layers"], 1)

    async def test_enabled_map_views_exclude_disabled_metadata_rows(self) -> None:
        with (
            patch(
                "backend.db.admin.list_layer_metadata",
                new=AsyncMock(
                    return_value=[
                        {
                            "layer_key": "虫情总览",
                            "layer_type": "view",
                            "display_name": "总览",
                            "sort_order": 0,
                            "default_visible": False,
                            "is_enabled": True,
                        },
                        {
                            "layer_key": "国槐参考点位",
                            "layer_type": "view",
                            "display_name": None,
                            "sort_order": 1,
                            "default_visible": False,
                            "is_enabled": False,
                        },
                    ]
                ),
            ),
            patch(
                "backend.db.admin.list_map_views",
                new=AsyncMock(
                    return_value=[
                        {"name": "虫情总览", "columns": ["编号"]},
                        {"name": "国槐参考点位", "columns": ["编号"]},
                    ]
                ),
            ),
        ):
            payload = await list_enabled_map_views()

        self.assertEqual(payload, [{"name": "虫情总览", "columns": ["编号"], "label": "总览"}])

    async def test_enabled_reference_layers_exclude_disabled_metadata_rows(self) -> None:
        with (
            patch(
                "backend.db.admin.list_layer_metadata",
                new=AsyncMock(
                    return_value=[
                        {
                            "layer_key": "通州区行政区边界",
                            "layer_type": "reference",
                            "display_name": "行政区",
                            "sort_order": 0,
                            "default_visible": True,
                            "is_enabled": True,
                        },
                        {
                            "layer_key": "国槐参考图层",
                            "layer_type": "reference",
                            "display_name": "国槐参考图层",
                            "sort_order": 1,
                            "default_visible": False,
                            "is_enabled": False,
                        },
                    ]
                ),
            ),
            patch(
                "backend.db.admin.list_reference_layers",
                new=AsyncMock(
                    return_value=[
                        {
                            "name": "通州区行政区边界",
                            "label": "通州区行政区边界",
                            "columns": ["gid"],
                            "default_visible": False,
                        },
                        {
                            "name": "国槐参考图层",
                            "label": "国槐参考图层",
                            "columns": ["gid"],
                            "default_visible": False,
                        },
                    ]
                ),
            ),
        ):
            payload = await list_enabled_reference_layers()

        self.assertEqual(
            payload,
            [
                {
                    "name": "通州区行政区边界",
                    "label": "行政区",
                    "columns": ["gid"],
                    "default_visible": True,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
