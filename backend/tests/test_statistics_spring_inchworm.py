from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.routers.statistics import get_spring_inchworm_summary_statistics
from backend.services.statistics import get_spring_inchworm_summary
from backend.services.statistics.sql_spring_inchworm import (
    SPRING_INCHWORM_ADULT_DAMAGE_LEVEL_SQL,
    SPRING_INCHWORM_ADULT_TOTALS_SQL,
    SPRING_INCHWORM_LARVA_DAMAGE_LEVEL_SQL,
    SPRING_INCHWORM_LARVA_TOTALS_SQL,
    SPRING_INCHWORM_RING_TOTALS_SQL,
    SPRING_INCHWORM_STATUS_SQL,
)


class FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakePool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return FakeAcquire(self.connection)


class SequentialFakeConnection:
    def __init__(self, results):
        self.results = list(results)
        self.fetch_calls: list[tuple[str, tuple]] = []

    async def fetch(self, query: str, *args):
        self.fetch_calls.append((query, args))
        return self.results.pop(0)


def build_insect_totals_row(**overrides):
    row = {
        "survey_records": 40,
        "surveyed_points": 36,
        "avg_insect_count": 12.5,
        "total_insect_count": 500,
        "last_survey_date": date(2026, 4, 10),
    }
    row.update(overrides)
    return row


class SpringInchwormSummaryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_assembles_all_sections(self) -> None:
        connection = SequentialFakeConnection(
            [
                [build_insect_totals_row()],
                [{"damage_level": "中度", "count": 9}, {"damage_level": None, "count": 2}],
                [build_insect_totals_row(survey_records=25, surveyed_points=24)],
                [{"damage_level": "轻", "count": 7}],
                [
                    {
                        "survey_records": 30,
                        "surveyed_points": 30,
                        "repair_count": 6,
                        "adult_count": 88,
                        "last_survey_date": date(2026, 3, 1),
                    }
                ],
                [{"status": "已闭环", "count": 3}, {"status": "待防治", "count": 2}],
            ]
        )

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_spring_inchworm_summary(year=2026)

        self.assertEqual(result["year"], 2026)

        adult = result["adult"]
        self.assertEqual(adult["survey_records"], 40)
        self.assertEqual(adult["surveyed_points"], 36)
        self.assertEqual(adult["avg_insect_count"], 12.5)
        self.assertEqual(adult["total_insect_count"], 500)
        self.assertEqual(adult["last_survey_date"], "2026-04-10")
        self.assertEqual(
            adult["damage_levels"],
            [
                {"damage_level": "中度", "count": 9},
                {"damage_level": "未知", "count": 2},
            ],
        )

        larva = result["larva"]
        self.assertEqual(larva["survey_records"], 25)
        self.assertEqual(larva["damage_levels"], [{"damage_level": "轻", "count": 7}])

        ring = result["ring_wrap"]
        self.assertEqual(ring["survey_records"], 30)
        self.assertEqual(ring["repair_count"], 6)
        self.assertEqual(ring["adult_count"], 88)
        self.assertEqual(ring["last_survey_date"], "2026-03-01")

        ledger = result["ledger"]
        self.assertEqual(ledger["ledger_points"], 5)
        self.assertEqual(
            ledger["status_counts"],
            [{"status": "已闭环", "count": 3}, {"status": "待防治", "count": 2}],
        )

        # 六条 SQL 都带同一个年份参数
        self.assertEqual(len(connection.fetch_calls), 6)
        for _, args in connection.fetch_calls:
            self.assertEqual(args, (2026,))

    async def test_summary_tolerates_empty_tables(self) -> None:
        connection = SequentialFakeConnection([[], [], [], [], [], []])

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_spring_inchworm_summary(year=2026)

        self.assertEqual(result["adult"]["survey_records"], 0)
        self.assertIsNone(result["adult"]["avg_insect_count"])
        self.assertEqual(result["adult"]["damage_levels"], [])
        self.assertEqual(result["larva"]["survey_records"], 0)
        self.assertEqual(result["ring_wrap"]["repair_count"], 0)
        self.assertIsNone(result["ring_wrap"]["last_survey_date"])
        self.assertEqual(result["ledger"]["ledger_points"], 0)
        self.assertEqual(result["ledger"]["status_counts"], [])

    def test_sql_targets_spring_inchworm_business_tables(self) -> None:
        self.assertIn('survey."春尺蠖成虫调查表"', SPRING_INCHWORM_ADULT_TOTALS_SQL)
        self.assertIn('survey."春尺蠖幼虫调查表"', SPRING_INCHWORM_LARVA_TOTALS_SQL)
        self.assertIn('survey."春尺蠖围环调查表"', SPRING_INCHWORM_RING_TOTALS_SQL)
        self.assertIn('ledger."春尺蠖问题点位台账"', SPRING_INCHWORM_STATUS_SQL)
        self.assertIn('"受害程度"', SPRING_INCHWORM_ADULT_DAMAGE_LEVEL_SQL)
        self.assertIn('"危害程度"', SPRING_INCHWORM_LARVA_DAMAGE_LEVEL_SQL)


class SpringInchwormSummaryRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_router_returns_service_payload(self) -> None:
        payload = {"year": 2026, "adult": {}, "larva": {}, "ring_wrap": {}, "ledger": {}}
        with patch(
            "backend.routers.statistics.get_spring_inchworm_summary",
            new=AsyncMock(return_value=payload),
        ):
            result = await get_spring_inchworm_summary_statistics(year=2026)
        self.assertEqual(result, payload)

    async def test_router_wraps_service_error(self) -> None:
        with patch(
            "backend.routers.statistics.get_spring_inchworm_summary",
            new=AsyncMock(side_effect=RuntimeError("数据库连接失败")),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_spring_inchworm_summary_statistics(year=2026)
        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("读取春尺蠖汇总失败", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
