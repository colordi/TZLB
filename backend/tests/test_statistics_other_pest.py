from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.routers.statistics import get_other_pest_summary_statistics
from backend.services.statistics import get_other_pest_summary
from backend.services.statistics.sql_other_pest import (
    OTHER_PEST_PEST_TYPE_SQL,
    OTHER_PEST_STATUS_SQL,
    OTHER_PEST_TOTALS_SQL,
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
        "survey_records": 36,
        "surveyed_points": 35,
        "problem_records": 18,
        "problem_points": 15,
        "last_survey_date": date(2026, 7, 27),
    }
    row.update(overrides)
    return row


def build_pest_type_row(**overrides):
    row = {
        "pest_type": "蚜虫",
        "survey_records": 30,
        "problem_records": 14,
        "problem_points": 12,
        "last_survey_date": date(2026, 7, 20),
    }
    row.update(overrides)
    return row


class OtherPestSummaryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_assembles_totals_status_and_pest_types(self) -> None:
        connection = SequentialFakeConnection(
            [
                [build_totals_row()],
                [
                    {"status": "待防治", "count": 12},
                    {"status": "待复查", "count": 5},
                ],
                [
                    build_pest_type_row(),
                    build_pest_type_row(
                        pest_type="草履蚧",
                        survey_records=5,
                        problem_records=4,
                        problem_points=4,
                    ),
                ],
            ]
        )

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_other_pest_summary(year=2026)

        self.assertEqual(result["year"], 2026)
        totals = result["totals"]
        self.assertEqual(totals["survey_records"], 36)
        self.assertEqual(totals["surveyed_points"], 35)
        self.assertEqual(totals["problem_records"], 18)
        self.assertEqual(totals["no_problem_records"], 18)
        self.assertEqual(totals["problem_points"], 15)
        self.assertEqual(totals["problem_rate"], 50.0)
        self.assertEqual(totals["last_survey_date"], "2026-07-27")
        self.assertEqual(totals["ledger_points"], 17)
        self.assertEqual(
            totals["status_counts"],
            [{"status": "待防治", "count": 12}, {"status": "待复查", "count": 5}],
        )
        self.assertEqual(len(result["pest_types"]), 2)
        self.assertEqual(result["pest_types"][0]["pest_type"], "蚜虫")
        self.assertEqual(result["pest_types"][0]["last_survey_date"], "2026-07-20")
        # 三条 SQL 都带同一个年份参数
        self.assertEqual(len(connection.fetch_calls), 3)
        for _, args in connection.fetch_calls:
            self.assertEqual(args, (2026,))

    async def test_summary_defaults_to_current_year_and_handles_empty(self) -> None:
        connection = SequentialFakeConnection([[build_totals_row()], [], []])

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_other_pest_summary()

        self.assertEqual(result["year"], date.today().year)
        self.assertEqual(result["totals"]["status_counts"], [])
        self.assertEqual(result["totals"]["ledger_points"], 0)
        self.assertEqual(result["pest_types"], [])

    async def test_summary_tolerates_missing_totals_row(self) -> None:
        connection = SequentialFakeConnection([[], [], []])

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_other_pest_summary(year=2026)

        self.assertEqual(result["totals"]["survey_records"], 0)
        self.assertEqual(result["totals"]["no_problem_records"], 0)
        self.assertEqual(result["totals"]["problem_rate"], 0.0)
        self.assertIsNone(result["totals"]["last_survey_date"])

    def test_sql_targets_other_pest_business_tables(self) -> None:
        self.assertIn('survey."其他害虫调查表"', OTHER_PEST_TOTALS_SQL)
        self.assertIn('survey."其他害虫调查表"', OTHER_PEST_PEST_TYPE_SQL)
        self.assertIn('ledger."其他害虫问题点位台账"', OTHER_PEST_STATUS_SQL)
        self.assertIn('"年份"', OTHER_PEST_TOTALS_SQL)
        self.assertIn('"当前状态"', OTHER_PEST_STATUS_SQL)


class OtherPestSummaryRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_router_returns_service_payload(self) -> None:
        payload = {"year": 2026, "totals": {}, "pest_types": []}
        with patch(
            "backend.routers.statistics.get_other_pest_summary",
            new=AsyncMock(return_value=payload),
        ):
            result = await get_other_pest_summary_statistics(year=2026)
        self.assertEqual(result, payload)

    async def test_router_wraps_service_error(self) -> None:
        with patch(
            "backend.routers.statistics.get_other_pest_summary",
            new=AsyncMock(side_effect=RuntimeError("数据库连接失败")),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_other_pest_summary_statistics(year=2026)
        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("读取其他害虫汇总失败", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
