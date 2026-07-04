from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.db.postgres import (
    fetch_reference_layer_feature_collection,
    fetch_map_filter_options,
    fetch_view_feature_collection,
    list_reference_layers,
    records_to_feature_collection,
    sort_filter_values,
)
from backend.routers.map import (
    get_reference_layers as get_reference_layers_endpoint,
    get_reference_layer_geojson,
    get_view_filter_options,
    get_views,
    parse_bbox,
    parse_limit,
)


class MapFilterOptionsTest(unittest.IsolatedAsyncioTestCase):
    async def test_filter_options_include_dynamic_fields_and_year_default(self) -> None:
        async def fake_fetch(query: str, *args):
            if '"属地"' in query:
                return [{"value": "宋庄镇"}, {"value": "潞城镇"}]
            if '"年份"' in query:
                return [{"value": "2024"}, {"value": "2025"}]
            if '"危害程度"' in query:
                return [{"value": "重"}, {"value": "白"}, {"value": "中"}]
            return []

        with (
            patch(
                "backend.db.postgres.get_map_view",
                new=AsyncMock(
                    return_value={
                        "name": "国槐尺蠖幼虫历年发生情况",
                        "columns": ["编号", "属地", "年份", "危害程度"],
                    }
                ),
            ),
            patch("backend.db.postgres.fetch", new=AsyncMock(side_effect=fake_fetch)),
        ):
            payload = await fetch_map_filter_options("国槐尺蠖幼虫历年发生情况")

        self.assertEqual(payload["localities"], ["宋庄镇", "潞城镇"])
        self.assertEqual(
            payload["filter_fields"],
            [
                {
                    "key": "属地",
                    "label": "属地",
                    "type": "select",
                    "options": [
                        {"value": "宋庄镇", "label": "宋庄镇"},
                        {"value": "潞城镇", "label": "潞城镇"},
                    ],
                    "default_value": "",
                },
                {
                    "key": "年份",
                    "label": "年份",
                    "type": "select",
                    "options": [
                        {"value": "2024", "label": "2024"},
                        {"value": "2025", "label": "2025"},
                    ],
                    "default_value": "2025",
                },
                {
                    "key": "危害程度",
                    "label": "危害程度",
                    "type": "select",
                    "options": [
                        {"value": "白", "label": "白"},
                        {"value": "中", "label": "中"},
                        {"value": "重", "label": "重"},
                    ],
                    "default_value": "",
                },
            ],
        )

    async def test_filter_options_include_survey_status_when_survey_date_exists(self) -> None:
        async def fake_fetch(query: str, *args):
            if '"属地"' in query:
                return [{"value": "宋庄镇"}]
            return []

        with (
            patch(
                "backend.db.postgres.get_map_view",
                new=AsyncMock(
                    return_value={
                        "name": "虫情总览",
                        "columns": ["编号", "属地", "调查日期"],
                    }
                ),
            ),
            patch("backend.db.postgres.fetch", new=AsyncMock(side_effect=fake_fetch)),
        ):
            payload = await fetch_map_filter_options("虫情总览")

        self.assertTrue(payload["supports_survey_status_filter"])
        self.assertIn(
            {
                "key": "调查状态",
                "label": "调查状态",
                "type": "select",
                "options": [
                    {"value": "调查", "label": "调查"},
                    {"value": "未调查", "label": "未调查"},
                ],
                "default_value": "",
            },
            payload["filter_fields"],
        )

    async def test_filter_options_include_deduped_survey_status_counts(self) -> None:
        def make_row(code: str, survey_date: str | None) -> dict:
            return {
                "geom_json": None,
                "properties": {
                    "编号": code,
                    "调查日期": survey_date,
                },
            }

        async def fake_fetch(query: str, *args):
            self.assertNotIn("ST_MakeEnvelope", query)
            self.assertNotIn("LIMIT", query)
            if '"调查日期" IS NOT NULL' in query:
                return [
                    make_row("MQ001", "2026-06-01"),
                    make_row("MQ001", "2026-06-02"),
                    make_row("MQ003", "2026-06-03"),
                ]
            if '"调查日期" IS NULL' in query:
                return [make_row("MQ002", None)]
            return [
                make_row("MQ001", "2026-06-01"),
                make_row("MQ001", "2026-06-02"),
                make_row("MQ002", None),
                make_row("MQ003", "2026-06-03"),
            ]

        with (
            patch(
                "backend.db.postgres.get_map_view",
                new=AsyncMock(
                    return_value={
                        "name": "虫情总览",
                        "columns": ["编号", "调查日期"],
                    }
                ),
            ),
            patch("backend.db.postgres.fetch", new=AsyncMock(side_effect=fake_fetch)),
        ):
            payload = await fetch_map_filter_options("虫情总览")

        self.assertEqual(
            payload["survey_status_counts"],
            {
                "all": 3,
                "completed": 2,
                "pending": 1,
            },
        )

    def test_filter_values_are_sorted_by_business_order(self) -> None:
        self.assertEqual(sort_filter_values("年份", ["2025", "2024"]), ["2024", "2025"])
        self.assertEqual(
            sort_filter_values("危害程度", ["重", "轻", "白", "中"]),
            ["白", "轻", "中", "重"],
        )

    async def test_feature_collection_accepts_multi_value_filters(self) -> None:
        fetch_mock = AsyncMock(return_value=[])

        with (
            patch(
                "backend.db.postgres.get_map_view",
                new=AsyncMock(
                    return_value={
                        "name": "国槐尺蠖幼虫历年发生情况",
                        "columns": ["编号", "年份", "危害程度", "调查日期"],
                    }
                ),
            ),
            patch("backend.db.postgres.fetch", new=fetch_mock),
        ):
            payload = await fetch_view_feature_collection(
                "国槐尺蠖幼虫历年发生情况",
                {
                    "年份": ["2024", "2025"],
                    "危害程度": "重",
                    "调查状态": ["调查"],
                },
            )

        self.assertEqual(payload["features"], [])
        query = fetch_mock.await_args.args[0]
        args = fetch_mock.await_args.args[1:]

        self.assertIn('BTRIM("年份"::text) = ANY($1::text[])', query)
        self.assertIn('BTRIM("危害程度"::text) = ANY($2::text[])', query)
        self.assertIn('"调查日期" IS NOT NULL', query)
        self.assertEqual(args, (["2024", "2025"], ["重"], 1001))

    async def test_feature_collection_applies_bbox_limit_and_has_more_metadata(self) -> None:
        fetch_mock = AsyncMock(
            return_value=[
                {
                    "geom_json": '{"type":"Point","coordinates":[116.5,39.7]}',
                    "properties": {"编号": "MQ001"},
                },
                {
                    "geom_json": '{"type":"Point","coordinates":[116.6,39.8]}',
                    "properties": {"编号": "MQ002"},
                },
                {
                    "geom_json": '{"type":"Point","coordinates":[116.7,39.9]}',
                    "properties": {"编号": "MQ003"},
                },
            ]
        )

        with (
            patch(
                "backend.db.postgres.get_map_view",
                new=AsyncMock(
                    return_value={
                        "name": "美国白蛾调查",
                        "columns": ["编号", "属地"],
                    }
                ),
            ),
            patch("backend.db.postgres.fetch", new=fetch_mock),
        ):
            payload = await fetch_view_feature_collection(
                "美国白蛾调查",
                bbox=(116.1, 39.5, 116.9, 40.1),
                limit=2,
            )

        query = fetch_mock.await_args.args[0]
        args = fetch_mock.await_args.args[1:]

        self.assertIn("ST_MakeEnvelope", query)
        self.assertIn("ST_Intersects", query)
        self.assertIn("LIMIT $5", query)
        self.assertEqual(args, (116.1, 39.5, 116.9, 40.1, 3))
        self.assertTrue(payload["has_more"])
        self.assertEqual(payload["limit"], 2)
        self.assertEqual(payload["returned_count"], 2)
        self.assertEqual(len(payload["features"]), 2)

    def test_feature_collection_dedupes_points_by_code_for_display(self) -> None:
        payload = records_to_feature_collection(
            [
                {
                    "geom_json": '{"type":"Point","coordinates":[116.5,39.7]}',
                    "properties": {
                        "编号": "MQ001",
                        "点位名称": "旧记录",
                        "调查日期": "2026-05-01",
                    },
                },
                {
                    "geom_json": '{"type":"Point","coordinates":[116.5,39.7]}',
                    "properties": {
                        "编号": "MQ001",
                        "点位名称": "新记录",
                        "调查日期": "2026-06-01",
                    },
                },
                {
                    "geom_json": '{"type":"Point","coordinates":[116.6,39.8]}',
                    "properties": {
                        "编号": "MQ002",
                        "点位名称": "未调查记录",
                        "调查日期": None,
                    },
                },
            ],
            dedupe_features=True,
        )

        self.assertEqual(len(payload["features"]), 2)
        self.assertEqual(payload["features"][0]["properties"]["点位名称"], "新记录")
        self.assertEqual(payload["features"][1]["properties"]["编号"], "MQ002")

    async def test_reference_layers_list_spatial_reference_tables(self) -> None:
        with patch(
            "backend.db.postgres.fetch",
            new=AsyncMock(
                return_value=[
                    {
                        "name": "通州区行政区边界",
                        "label": "通州区行政区边界",
                        "columns": ["gid", "区域"],
                    },
                    {
                        "name": "通州区小区边界",
                        "label": "通州区小区边界",
                        "columns": ["gid", "名称"],
                    },
                ]
            ),
        ):
            payload = await list_reference_layers()

        self.assertEqual(
            payload,
            [
                {
                    "name": "通州区行政区边界",
                    "label": "通州区行政区边界",
                    "columns": ["gid", "区域"],
                    "default_visible": True,
                },
                {
                    "name": "通州区小区边界",
                    "label": "通州区小区边界",
                    "columns": ["gid", "名称"],
                    "default_visible": False,
                },
            ],
        )

    async def test_reference_layer_feature_collection_reads_reference_table(self) -> None:
        fetch_mock = AsyncMock(return_value=[])

        with (
            patch(
                "backend.db.postgres.get_reference_layer",
                new=AsyncMock(
                    return_value={
                        "name": "通州区小区边界",
                        "label": "通州区小区边界",
                        "columns": ["gid", "名称"],
                        "default_visible": False,
                    }
                ),
            ),
            patch("backend.db.postgres.fetch", new=fetch_mock),
        ):
            payload = await fetch_reference_layer_feature_collection("通州区小区边界")

        self.assertEqual(payload["features"], [])
        query = fetch_mock.await_args.args[0]
        args = fetch_mock.await_args.args[1:]
        self.assertIn('"reference"."通州区小区边界"', query)
        self.assertIn("ST_AsGeoJSON", query)
        self.assertEqual(args, (1001,))


class MapRouterQueryParamTest(unittest.TestCase):
    def test_parse_bbox_accepts_valid_bounds(self) -> None:
        self.assertEqual(
            parse_bbox("116.1,39.5,116.9,40.1"),
            (116.1, 39.5, 116.9, 40.1),
        )

    def test_parse_bbox_rejects_invalid_bounds(self) -> None:
        with self.assertRaises(ValueError):
            parse_bbox("116.9,39.5,116.1,40.1")

    def test_parse_limit_uses_default_and_rejects_out_of_range(self) -> None:
        self.assertEqual(parse_limit(None), 1000)
        with self.assertRaises(ValueError):
            parse_limit("5001")


class MapRouterLayerMetadataTest(unittest.IsolatedAsyncioTestCase):
    async def test_views_endpoint_uses_enabled_layer_metadata(self) -> None:
        enabled_views = [{"name": "虫情总览", "columns": ["编号"], "label": "虫情总览"}]

        with patch(
            "backend.routers.map.list_enabled_map_views",
            new=AsyncMock(return_value=enabled_views),
        ):
            payload = await get_views()

        self.assertEqual(payload, enabled_views)

    async def test_reference_layers_endpoint_uses_enabled_layer_metadata(self) -> None:
        enabled_layers = [
            {
                "name": "通州区行政区边界",
                "label": "通州区行政区边界",
                "columns": ["gid"],
                "default_visible": True,
            }
        ]

        with patch(
            "backend.routers.map.list_enabled_reference_layers",
            new=AsyncMock(return_value=enabled_layers),
        ):
            payload = await get_reference_layers_endpoint()

        self.assertEqual(payload, enabled_layers)

    async def test_filter_options_rejects_disabled_view_before_fetching(self) -> None:
        fetch_mock = AsyncMock()

        with (
            patch("backend.routers.map.get_enabled_map_view", new=AsyncMock(return_value=None)),
            patch("backend.routers.map.fetch_map_filter_options", new=fetch_mock),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_view_filter_options("国槐参考点位")

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.detail, "视图不存在或已停用：国槐参考点位")
        fetch_mock.assert_not_awaited()

    async def test_reference_layer_geojson_rejects_disabled_layer_before_fetching(self) -> None:
        fetch_mock = AsyncMock()
        request = type("Request", (), {"query_params": {}})()

        with (
            patch("backend.routers.map.get_enabled_reference_layer", new=AsyncMock(return_value=None)),
            patch("backend.routers.map.fetch_reference_layer_feature_collection", new=fetch_mock),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_reference_layer_geojson("国槐参考图层", request)

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.detail, "参考图层不存在或已停用：国槐参考图层")
        fetch_mock.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
