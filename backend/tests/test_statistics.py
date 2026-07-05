from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.routers.statistics import get_white_moth_daily
from backend.services.statistics import (
    WHITE_MOTH_DAILY_SQL,
    get_white_moth_daily_statistics,
    serialize_white_moth_daily_row,
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


class FakeConnection:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.fetch_calls: list[str] = []

    async def fetch(self, query: str, *args):
        self.fetch_calls.append(query)
        return self.rows


class FakeRow(dict):
    def __getitem__(self, key):
        return super().__getitem__(key)


def build_row(
    survey_date: date = date(2026, 6, 1),
    treatment_plants: int = 210,
    completed_points: int = 51,
) -> FakeRow:
    return FakeRow(
        {
            "日期": survey_date,
            "当日除治量（株）": treatment_plants,
            "累积防治完成点数": completed_points,
            "城区当日受害点位数": 17,
            "城区当日受害株数": 159,
            "城区当日巡查点位数": 18,
            "乡镇当日受害株数": 70,
            "乡镇当日受害点位数": 11,
            "乡镇当日巡查点位数": 26,
            "当日派单数": 28,
        }
    )


class StatisticsServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_white_moth_daily_statistics_returns_columns_and_rows(self) -> None:
        connection = FakeConnection(
            [
                build_row(date(2026, 5, 31), 122, 37),
                build_row(date(2026, 6, 1), 210, 51),
            ]
        )

        with patch(
            "backend.services.statistics.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_white_moth_daily_statistics()

        self.assertEqual(result["columns"][0], {"key": "date", "label": "日期", "type": "date"})
        self.assertEqual(result["rows"][0]["date"], "2026-05-31")
        self.assertEqual(result["rows"][0]["daily_treatment_plants"], 122)
        self.assertEqual(result["rows"][1]["cumulative_completed_points"], 51)
        self.assertEqual(result["rows"][1]["daily_dispatch_points"], 28)
        self.assertEqual(len(connection.fetch_calls), 1)

    async def test_white_moth_daily_statistics_supports_empty_result(self) -> None:
        connection = FakeConnection()

        with patch(
            "backend.services.statistics.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_white_moth_daily_statistics()

        self.assertEqual(result["rows"], [])
        self.assertGreater(len(result["columns"]), 0)

    def test_white_moth_sql_uses_business_tables_not_map_view(self) -> None:
        self.assertIn('survey."美国白蛾调查表"', WHITE_MOTH_DAILY_SQL)
        self.assertIn('ledger."美国白蛾问题点位台账"', WHITE_MOTH_DAILY_SQL)
        self.assertNotIn('views."2026_美国白蛾第 1 代调查"', WHITE_MOTH_DAILY_SQL)
        self.assertIn("COALESCE(\"区域\", '乡镇')", WHITE_MOTH_DAILY_SQL)
        self.assertIn('WHEN l."剪网彻底" = \'是\'', WHITE_MOTH_DAILY_SQL)
        self.assertNotIn('COALESCE(l."防治次数", 0) = 0\n            AND l."剪网彻底" = \'是\'', WHITE_MOTH_DAILY_SQL)
        self.assertIn('lc."完成日期" <= d."日期"', WHITE_MOTH_DAILY_SQL)
        self.assertIn('ORDER BY\n    d."日期" DESC', WHITE_MOTH_DAILY_SQL)

    def test_serialize_row_maps_chinese_columns_to_public_keys(self) -> None:
        row = build_row(date(2026, 6, 2), 341, 70)

        result = serialize_white_moth_daily_row(row)

        self.assertEqual(result["date"], "2026-06-02")
        self.assertEqual(result["daily_treatment_plants"], 341)
        self.assertEqual(result["cumulative_completed_points"], 70)
        self.assertEqual(result["urban_daily_damaged_points"], 17)
        self.assertEqual(result["town_daily_inspected_points"], 26)


class StatisticsRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_white_moth_daily_router_returns_service_result(self) -> None:
        payload = {"columns": [{"key": "date", "label": "日期", "type": "date"}], "rows": []}

        with patch(
            "backend.routers.statistics.get_white_moth_daily_statistics",
            new=AsyncMock(return_value=payload),
        ):
            result = await get_white_moth_daily()

        self.assertEqual(result, payload)

    async def test_white_moth_daily_router_wraps_errors(self) -> None:
        with patch(
            "backend.routers.statistics.get_white_moth_daily_statistics",
            new=AsyncMock(side_effect=RuntimeError("连接失败")),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_white_moth_daily()

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.detail, "读取美国白蛾每日统计失败：连接失败")


if __name__ == "__main__":
    unittest.main()
