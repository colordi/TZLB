from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from backend.db.postgres import (
    fetch_map_filter_options,
    fetch_view_feature_collection,
    sort_filter_values,
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
        self.assertEqual(args, (["2024", "2025"], ["重"]))


if __name__ == "__main__":
    unittest.main()
