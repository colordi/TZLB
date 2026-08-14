from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.routers.statistics import get_yangshu_shiye_summary_statistics
from backend.services.statistics import get_yangshu_shiye_summary
from backend.services.statistics.sql_yangshu_shiye import (
    YANGSHU_SHIYE_PEST_TYPE_SQL,
    YANGSHU_SHIYE_STATUS_SQL,
    YANGSHU_SHIYE_TOTALS_SQL,
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


def build_totals_row(**overrides):
    row = {
        "survey_records": 20,
        "surveyed_points": 18,
        "problem_records": 6,
        "problem_points": 5,
        "last_survey_date": date(2026, 8, 1),
    }
    row.update(overrides)
    return row


class YangshuShiyeSummaryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_assembles_totals_status_and_pest_types(self) -> None:
        connection = SequentialFakeConnection(
            [
                [build_totals_row()],
                [{"status": "待防治", "count": 4}],
                [
                    {
                        "pest_type": "杨小舟蛾",
                        "survey_records": 12,
                        "problem_records": 5,
                        "problem_points": 4,
                        "last_survey_date": date(2026, 7, 30),
                    }
                ],
            ]
        )

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_yangshu_shiye_summary(year=2026)

        self.assertEqual(result["year"], 2026)
        totals = result["totals"]
        self.assertEqual(totals["survey_records"], 20)
        self.assertEqual(totals["no_problem_records"], 14)
        self.assertEqual(totals["problem_rate"], 30.0)
        self.assertEqual(totals["last_survey_date"], "2026-08-01")
        self.assertEqual(totals["ledger_points"], 4)
        self.assertEqual(totals["status_counts"], [{"status": "待防治", "count": 4}])
        self.assertEqual(result["pest_types"][0]["pest_type"], "杨小舟蛾")
        # 三条 SQL 都带同一个年份参数
        self.assertEqual(len(connection.fetch_calls), 3)
        for _, args in connection.fetch_calls:
            self.assertEqual(args, (2026,))

    async def test_summary_tolerates_missing_totals_row(self) -> None:
        connection = SequentialFakeConnection([[], [], []])

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_yangshu_shiye_summary(year=2026)

        self.assertEqual(result["totals"]["survey_records"], 0)
        self.assertIsNone(result["totals"]["last_survey_date"])
        self.assertEqual(result["pest_types"], [])

    def test_sql_targets_yangshu_shiye_business_tables(self) -> None:
        self.assertIn('survey."杨树食叶害虫调查表"', YANGSHU_SHIYE_TOTALS_SQL)
        self.assertIn('survey."杨树食叶害虫调查表"', YANGSHU_SHIYE_PEST_TYPE_SQL)
        self.assertIn('ledger."杨树食叶害虫问题点位台账"', YANGSHU_SHIYE_STATUS_SQL)
        self.assertIn('"年份"', YANGSHU_SHIYE_TOTALS_SQL)
        self.assertIn('"当前状态"', YANGSHU_SHIYE_STATUS_SQL)


class YangshuShiyeSummaryRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_router_returns_service_payload(self) -> None:
        payload = {"year": 2026, "totals": {}, "pest_types": []}
        with patch(
            "backend.routers.statistics.get_yangshu_shiye_summary",
            new=AsyncMock(return_value=payload),
        ):
            result = await get_yangshu_shiye_summary_statistics(year=2026)
        self.assertEqual(result, payload)

    async def test_router_wraps_service_error(self) -> None:
        with patch(
            "backend.routers.statistics.get_yangshu_shiye_summary",
            new=AsyncMock(side_effect=RuntimeError("数据库连接失败")),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_yangshu_shiye_summary_statistics(year=2026)
        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("读取杨树食叶害虫汇总失败", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
