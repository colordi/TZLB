from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.routers.statistics import get_ash_borer_summary_statistics
from backend.services.statistics import get_ash_borer_summary
from backend.services.statistics.sql_ash_borer import (
    ASH_BORER_LIGHT_MAX_PLANTS,
    ASH_BORER_LOCALITY_SQL,
    ASH_BORER_MEDIUM_MAX_PLANTS,
    ASH_BORER_TOTALS_SQL,
    ASH_BORER_TREES_PER_POINT,
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
        "survey_records": 15,
        "surveyed_points": 12,
        "excluded_points": 3,
        "last_survey_date": date(2026, 8, 5),
        "agrilus_damaged_plants": 30,
        "agrilus_holes": 120,
        "cossus_damaged_plants": 8,
        "dead_plants": 5,
        "felled_plants": 3,
        "agrilus_none": 6,
        "agrilus_light": 4,
        "agrilus_medium": 1,
        "agrilus_high": 1,
        "cossus_none": 2,
        "cossus_light": 5,
        "cossus_medium": 3,
        "cossus_high": 2,
    }
    row.update(overrides)
    return row


class AshBorerSummaryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_assembles_totals_and_localities(self) -> None:
        connection = SequentialFakeConnection(
            [
                [build_totals_row()],
                [
                    {
                        "locality": "宋庄镇",
                        "survey_records": 10,
                        "surveyed_points": 8,
                        "excluded_points": 2,
                        "agrilus_damaged_plants": 20,
                        "cossus_damaged_plants": 6,
                        "dead_plants": 4,
                        "felled_plants": 2,
                        "agrilus_none": 4,
                        "agrilus_light": 2,
                        "agrilus_medium": 1,
                        "agrilus_high": 1,
                        "cossus_none": 1,
                        "cossus_light": 3,
                        "cossus_medium": 2,
                        "cossus_high": 2,
                        "last_survey_date": date(2026, 8, 5),
                    },
                    {"locality": None, "survey_records": 5},
                ],
            ]
        )

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_ash_borer_summary(year=2026)

        self.assertEqual(result["year"], 2026)
        self.assertEqual(result["trees_per_point"], ASH_BORER_TREES_PER_POINT)
        self.assertEqual(result["damage_level_thresholds"], {"none": 0, "light": 10, "medium": 20})
        totals = result["totals"]
        self.assertEqual(totals["survey_records"], 15)
        self.assertEqual(totals["surveyed_points"], 12)
        self.assertEqual(totals["surveyed_trees"], 360)
        self.assertEqual(totals["excluded_points"], 3)
        self.assertEqual(totals["agrilus_damaged_plants"], 30)
        self.assertEqual(totals["agrilus_holes"], 120)
        self.assertEqual(totals["cossus_damaged_plants"], 8)
        self.assertEqual(totals["dead_plants"], 5)
        self.assertEqual(totals["felled_plants"], 3)
        self.assertNotIn("replanted_plants", totals)
        # 死亡率 = (5 + 3) / (12 × 30) = 2.2%；有虫株率同为受害株 / 360
        self.assertEqual(totals["mortality_rate"], 2.2)
        self.assertEqual(totals["agrilus_infestation_rate"], 8.3)
        self.assertEqual(totals["cossus_infestation_rate"], 2.2)
        self.assertEqual(
            totals["agrilus_damage_levels"],
            {"none": 6, "light": 4, "medium": 1, "high": 1},
        )
        self.assertEqual(
            totals["cossus_damage_levels"],
            {"none": 2, "light": 5, "medium": 3, "high": 2},
        )
        self.assertEqual(totals["last_survey_date"], "2026-08-05")

        self.assertEqual(len(result["localities"]), 2)
        first = result["localities"][0]
        self.assertEqual(first["locality"], "宋庄镇")
        self.assertEqual(first["agrilus_damaged_plants"], 20)
        self.assertEqual(first["excluded_points"], 2)
        self.assertEqual(first["surveyed_trees"], 240)
        self.assertEqual(first["mortality_rate"], 2.5)
        self.assertEqual(first["agrilus_infestation_rate"], 8.3)
        self.assertEqual(first["cossus_infestation_rate"], 2.5)
        self.assertEqual(
            first["agrilus_damage_levels"],
            {"none": 4, "light": 2, "medium": 1, "high": 1},
        )
        self.assertEqual(first["last_survey_date"], "2026-08-05")
        # 空属地归为「未知」，缺失数值归零，点位数为 0 时率值为空
        second = result["localities"][1]
        self.assertEqual(second["locality"], "未知")
        self.assertEqual(second["agrilus_damaged_plants"], 0)
        self.assertEqual(second["excluded_points"], 0)
        self.assertIsNone(second["mortality_rate"])
        self.assertIsNone(second["agrilus_infestation_rate"])
        self.assertEqual(
            second["agrilus_damage_levels"],
            {"none": 0, "light": 0, "medium": 0, "high": 0},
        )
        # 两条 SQL 都带同一个年份参数
        self.assertEqual(len(connection.fetch_calls), 2)
        for _, args in connection.fetch_calls:
            self.assertEqual(args, (2026,))

    async def test_summary_defaults_to_current_year_and_handles_empty(self) -> None:
        connection = SequentialFakeConnection([[], []])

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_ash_borer_summary()

        self.assertEqual(result["year"], date.today().year)
        self.assertEqual(result["trees_per_point"], ASH_BORER_TREES_PER_POINT)
        self.assertEqual(result["totals"]["survey_records"], 0)
        self.assertEqual(result["totals"]["excluded_points"], 0)
        self.assertEqual(result["totals"]["agrilus_holes"], 0)
        self.assertIsNone(result["totals"]["mortality_rate"])
        self.assertIsNone(result["totals"]["last_survey_date"])
        self.assertEqual(
            result["totals"]["agrilus_damage_levels"],
            {"none": 0, "light": 0, "medium": 0, "high": 0},
        )
        self.assertEqual(result["localities"], [])

    def test_sql_excludes_replanted_points(self) -> None:
        self.assertEqual(ASH_BORER_TREES_PER_POINT, 30)
        self.assertIn('survey."白蜡蛀干害虫调查表"', ASH_BORER_TOTALS_SQL)
        self.assertIn('survey."白蜡蛀干害虫调查表"', ASH_BORER_LOCALITY_SQL)
        self.assertIn('"窄吉丁危害（株）"', ASH_BORER_TOTALS_SQL)
        self.assertIn('"属地"', ASH_BORER_LOCALITY_SQL)
        self.assertIn('"换植（株）"', ASH_BORER_TOTALS_SQL)
        self.assertIn('"换植（株）"', ASH_BORER_LOCALITY_SQL)
        self.assertIn('COALESCE("换植（株）", 0) = 0', ASH_BORER_TOTALS_SQL)
        self.assertIn('COALESCE("换植（株）", 0) > 0', ASH_BORER_TOTALS_SQL)
        self.assertIn("excluded_points", ASH_BORER_TOTALS_SQL)
        self.assertIn("excluded_points", ASH_BORER_LOCALITY_SQL)
        self.assertEqual(ASH_BORER_LIGHT_MAX_PLANTS, 3)
        self.assertEqual(ASH_BORER_MEDIUM_MAX_PLANTS, 6)
        self.assertIn("BETWEEN 1 AND 3", ASH_BORER_TOTALS_SQL)
        self.assertIn("BETWEEN 4 AND 6", ASH_BORER_TOTALS_SQL)
        self.assertIn("agrilus_none", ASH_BORER_TOTALS_SQL)
        self.assertIn("cossus_high", ASH_BORER_LOCALITY_SQL)


class AshBorerSummaryRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_router_returns_service_payload(self) -> None:
        payload = {"year": 2026, "totals": {}, "localities": []}
        with patch(
            "backend.routers.statistics.get_ash_borer_summary",
            new=AsyncMock(return_value=payload),
        ):
            result = await get_ash_borer_summary_statistics(year=2026)
        self.assertEqual(result, payload)

    async def test_router_wraps_service_error(self) -> None:
        with patch(
            "backend.routers.statistics.get_ash_borer_summary",
            new=AsyncMock(side_effect=RuntimeError("数据库连接失败")),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_ash_borer_summary_statistics(year=2026)
        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("读取白蜡蛀干害虫汇总失败", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
