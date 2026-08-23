from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.routers.statistics import get_statistics_available_years
from backend.services.statistics import get_statistics_years
from backend.services.statistics.sql_years import (
    STATISTICS_MODULE_KEYS,
    STATISTICS_YEARS_SQL,
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
        self.fetch_calls: list[tuple[str, tuple]] = []

    async def fetch(self, query: str, *args):
        self.fetch_calls.append((query, args))
        return self.rows


class StatisticsYearsServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_years_are_grouped_by_module_in_order(self) -> None:
        connection = FakeConnection(
            [
                {"module": "white-moth", "year": 2024},
                {"module": "white-moth", "year": 2026},
                {"module": "ash-borer", "year": 2025},
            ]
        )

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_statistics_years()

        self.assertEqual(connection.fetch_calls[0][0], STATISTICS_YEARS_SQL)
        self.assertEqual(result["white-moth"], [2024, 2026])
        self.assertEqual(result["ash-borer"], [2025])
        # 所有模块键都存在，无数据的模块为空列表
        for key in STATISTICS_MODULE_KEYS:
            self.assertIn(key, result)
        self.assertEqual(result["other-pests"], [])

    async def test_years_support_empty_result(self) -> None:
        connection = FakeConnection()

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_statistics_years()

        self.assertEqual(set(result.keys()), set(STATISTICS_MODULE_KEYS))
        self.assertTrue(all(years == [] for years in result.values()))


class StatisticsYearsRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_years_endpoint_returns_service_payload(self) -> None:
        payload = {key: [2026] for key in STATISTICS_MODULE_KEYS}

        with patch(
            "backend.routers.statistics.get_statistics_years",
            new=AsyncMock(return_value=payload),
        ):
            result = await get_statistics_available_years()

        self.assertEqual(result, payload)

    async def test_years_endpoint_wraps_errors(self) -> None:
        with patch(
            "backend.routers.statistics.get_statistics_years",
            new=AsyncMock(side_effect=RuntimeError("db down")),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_statistics_available_years()

        self.assertEqual(context.exception.status_code, 500)


if __name__ == "__main__":
    unittest.main()
