from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.routers.statistics import (
    get_white_moth_daily,
    get_white_moth_generation_statistics,
    get_white_moth_locality_statistics,
)
from backend.services.statistics import (
    WHITE_MOTH_DAILY_SQL,
    WHITE_MOTH_DISPATCH_FREQUENCY_SQL,
    WHITE_MOTH_GENERATION_SUMMARY_SQL,
    WHITE_MOTH_LOCALITY_ORDER,
    WHITE_MOTH_LOCALITY_SUMMARY_SQL,
    WHITE_MOTH_LOCALITY_UNFEEDBACK_SITES_SQL,
    WHITE_MOTH_SEVERE_PLANT_THRESHOLD,
    get_white_moth_daily_statistics,
    get_white_moth_generation_summary,
    get_white_moth_locality_summary,
    merge_locality_summary_rows,
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
        self.fetch_calls.append((query, args))
        return self.rows


class SequentialFakeConnection(FakeConnection):
    def __init__(self, results):
        super().__init__()
        self.results = list(results)

    async def fetch(self, query: str, *args):
        self.fetch_calls.append((query, args))
        return self.results.pop(0)


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
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_white_moth_daily_statistics()

        self.assertEqual(result["columns"][0], {"key": "date", "label": "日期", "type": "date"})
        self.assertEqual(result["rows"][0]["date"], "2026-05-31")
        self.assertEqual(result["rows"][0]["daily_treatment_plants"], 122)
        self.assertEqual(result["rows"][1]["cumulative_completed_points"], 51)
        self.assertEqual(result["rows"][1]["daily_dispatch_points"], 28)
        self.assertEqual(len(connection.fetch_calls), 1)
        self.assertEqual(connection.fetch_calls[0][1], (None, None))

    async def test_white_moth_daily_statistics_supports_empty_result(self) -> None:
        connection = FakeConnection()

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_white_moth_daily_statistics()

        self.assertEqual(result["rows"], [])
        self.assertGreater(len(result["columns"]), 0)

    async def test_white_moth_daily_statistics_passes_year_and_generation(self) -> None:
        connection = FakeConnection([build_row()])

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            await get_white_moth_daily_statistics(year=2026, generation="第一代")

        self.assertEqual(connection.fetch_calls[0][1], (2026, "第一代"))

    def test_white_moth_sql_uses_business_tables_not_map_view(self) -> None:
        self.assertIn('survey."美国白蛾调查表"', WHITE_MOTH_DAILY_SQL)
        self.assertIn('ledger."美国白蛾问题点位台账"', WHITE_MOTH_DAILY_SQL)
        self.assertNotIn('views."2026_美国白蛾第 1 代调查"', WHITE_MOTH_DAILY_SQL)
        self.assertIn("COALESCE(\"区域\", '乡镇')", WHITE_MOTH_DAILY_SQL)
        self.assertIn("first_damage AS", WHITE_MOTH_DAILY_SQL)
        self.assertIn("DISTINCT ON", WHITE_MOTH_DAILY_SQL)
        self.assertIn('BTRIM("编号")', WHITE_MOTH_DAILY_SQL)
        self.assertIn("first_damage_daily", WHITE_MOTH_DAILY_SQL)
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

    async def test_generation_summary_returns_each_generation_and_dispatch_frequency(self) -> None:
        connection = SequentialFakeConnection(
            [
                [
                    FakeRow(
                        {
                            "as_of_date": date(2026, 7, 11),
                            "year": 2026,
                            "世代": "第一代",
                            "start_date": date(2026, 5, 1),
                            "end_date": date(2026, 6, 20),
                            "surveyed_points": 44,
                            "urban_surveyed_points": 18,
                            "town_surveyed_points": 26,
                            "damaged_points": 17,
                            "urban_damaged_points": 7,
                            "town_damaged_points": 10,
                            "dispatch_count": 21,
                        }
                    )
                ],
                [
                    FakeRow({"世代": "第一代", "dispatch_times": 1, "point_count": 13}),
                    FakeRow({"世代": "第一代", "dispatch_times": 2, "point_count": 4}),
                ],
            ]
        )

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_white_moth_generation_summary()

        self.assertEqual(result["as_of_date"], "2026-07-11")
        self.assertEqual(result["year"], 2026)
        self.assertEqual(result["generations"][0]["start_date"], "2026-05-01")
        self.assertEqual(result["generations"][0]["end_date"], "2026-06-20")
        self.assertEqual(result["generations"][0]["surveyed_points"], 44)
        self.assertEqual(result["generations"][0]["damaged_points"], 17)
        self.assertEqual(result["generations"][0]["dispatch_count"], 21)
        self.assertEqual(
            result["generations"][0]["dispatch_frequency"],
            [
                {"dispatch_times": 1, "point_count": 13},
                {"dispatch_times": 2, "point_count": 4},
            ],
        )
        self.assertEqual(len(connection.fetch_calls), 2)
        self.assertEqual(connection.fetch_calls[0][1], (date.today().year,))
        self.assertEqual(connection.fetch_calls[1][1], (date.today().year,))

    async def test_generation_summary_passes_year_to_sql(self) -> None:
        connection = SequentialFakeConnection(
            [
                [
                    FakeRow(
                        {
                            "as_of_date": date(2025, 7, 11),
                            "year": 2025,
                            "世代": "第一代",
                            "start_date": None,
                            "end_date": None,
                            "surveyed_points": 10,
                            "urban_surveyed_points": 4,
                            "town_surveyed_points": 6,
                            "damaged_points": 3,
                            "urban_damaged_points": 1,
                            "town_damaged_points": 2,
                            "dispatch_count": 5,
                        }
                    )
                ],
                [],
            ]
        )

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_white_moth_generation_summary(year=2025)

        self.assertEqual(result["year"], 2025)
        self.assertIsNone(result["generations"][0]["start_date"])
        self.assertEqual(connection.fetch_calls[0][1], (2025,))
        self.assertEqual(connection.fetch_calls[1][1], (2025,))

    def test_generation_summary_sql_groups_by_generation_and_point_code(self) -> None:
        self.assertIn("first_survey AS", WHITE_MOTH_GENERATION_SUMMARY_SQL)
        self.assertIn("first_damage AS", WHITE_MOTH_GENERATION_SUMMARY_SQL)
        self.assertIn("point_dispatch AS", WHITE_MOTH_GENERATION_SUMMARY_SQL)
        self.assertIn('DISTINCT ON ("世代", BTRIM("编号"))', WHITE_MOTH_GENERATION_SUMMARY_SQL)
        self.assertIn('"调查日期" <= CURRENT_DATE', WHITE_MOTH_GENERATION_SUMMARY_SQL)
        self.assertIn('COALESCE("受害株数", 0) > 0', WHITE_MOTH_GENERATION_SUMMARY_SQL)
        self.assertIn('COUNT(*) FILTER (WHERE COALESCE("受害株数", 0) > 0)', WHITE_MOTH_DISPATCH_FREQUENCY_SQL)
        self.assertIn('GROUP BY "世代", BTRIM("编号")', WHITE_MOTH_DISPATCH_FREQUENCY_SQL)

    def test_locality_summary_sql_uses_ledger_and_metric_rules(self) -> None:
        self.assertIn('ledger."美国白蛾问题点位台账"', WHITE_MOTH_LOCALITY_SUMMARY_SQL)
        self.assertIn('WHEN BTRIM(COALESCE("属地", \'\')) = \'宋庄镇\' THEN \'宋庄镇\'', WHITE_MOTH_LOCALITY_SUMMARY_SQL)
        self.assertIn("ELSE '其他单位'", WHITE_MOTH_LOCALITY_SUMMARY_SQL)
        self.assertIn("first_known_date", WHITE_MOTH_LOCALITY_SUMMARY_SQL)
        self.assertIn("completion_date", WHITE_MOTH_LOCALITY_SUMMARY_SQL)
        # 截止日期仅约束纳入（first_known_date <= $4），完成只看最新状态
        self.assertIn("<= $4::date", WHITE_MOTH_LOCALITY_SUMMARY_SQL)
        self.assertIn(
            "WHERE completion_date IS NOT NULL",
            WHITE_MOTH_LOCALITY_SUMMARY_SQL,
        )
        self.assertNotIn(
            "completion_date <= $4::date",
            WHITE_MOTH_LOCALITY_SUMMARY_SQL,
        )
        self.assertIn("damaged_plants >= $3", WHITE_MOTH_LOCALITY_SUMMARY_SQL)
        self.assertIn("is_collab", WHITE_MOTH_LOCALITY_SUMMARY_SQL)
        self.assertIn("调查日期列表", WHITE_MOTH_LOCALITY_SUMMARY_SQL)
        self.assertIn("下派日期列表", WHITE_MOTH_LOCALITY_SUMMARY_SQL)
        # 未反馈点位：与防治完成率互补 —— completion_date IS NULL（既无彻底剪网也无防治记录）
        self.assertIn(
            "WHERE completion_date IS NULL",
            WHITE_MOTH_LOCALITY_SUMMARY_SQL,
        )
        self.assertIn(
            "completion_date IS NULL",
            WHITE_MOTH_LOCALITY_UNFEEDBACK_SITES_SQL,
        )
        self.assertIn("unfeedback_points", WHITE_MOTH_LOCALITY_SUMMARY_SQL)
        self.assertIn("code <> ''", WHITE_MOTH_LOCALITY_UNFEEDBACK_SITES_SQL)
        self.assertEqual(WHITE_MOTH_SEVERE_PLANT_THRESHOLD, 10)
        self.assertEqual(len(WHITE_MOTH_LOCALITY_ORDER), 23)
        self.assertEqual(WHITE_MOTH_LOCALITY_ORDER[-1], "其他单位")

    def test_merge_locality_summary_rows_fills_missing_and_rates(self) -> None:
        rows = [
            FakeRow(
                {
                    "locality": "张家湾镇",
                    "damaged_points": 10,
                    "damaged_plants": 80,
                    "completed_points": 5,
                    "severe_points": 3,
                    "unfeedback_points": 4,
                    "collab_points": 1,
                }
            ),
            FakeRow(
                {
                    "locality": "其他单位",
                    "damaged_points": 2,
                    "damaged_plants": 4,
                    "completed_points": 0,
                    "severe_points": 0,
                    "unfeedback_points": 0,
                    "collab_points": 2,
                }
            ),
        ]
        unfeedback_sites = [
            FakeRow(
                {
                    "locality": "张家湾镇",
                    "code": "ZW001",
                    "name": "示范点",
                }
            ),
            FakeRow(
                {
                    "locality": "张家湾镇",
                    "code": "ZW002",
                    "name": "公园",
                }
            ),
        ]

        localities = merge_locality_summary_rows(rows, unfeedback_sites)

        self.assertEqual(len(localities), 23)
        zw = next(item for item in localities if item["locality"] == "张家湾镇")
        self.assertEqual(zw["damaged_points"], 10)
        self.assertEqual(zw["completion_rate"], 50.0)
        self.assertEqual(zw["severe_points"], 3)
        self.assertEqual(zw["unfeedback_points"], 2)
        self.assertEqual(
            zw["unfeedback_sites"],
            [
                {"code": "ZW001", "name": "示范点"},
                {"code": "ZW002", "name": "公园"},
            ],
        )
        other = next(item for item in localities if item["locality"] == "其他单位")
        self.assertEqual(other["collab_points"], 2)
        self.assertEqual(other["unfeedback_sites"], [])
        empty = next(item for item in localities if item["locality"] == "宋庄镇")
        self.assertEqual(empty["damaged_points"], 0)
        self.assertEqual(empty["completion_rate"], 0.0)

    async def test_locality_summary_returns_totals_and_fixed_localities(self) -> None:
        connection = SequentialFakeConnection(
            [
                [
                    FakeRow(
                        {
                            "locality": "宋庄镇",
                            "damaged_points": 4,
                            "damaged_plants": 20,
                            "completed_points": 2,
                            "severe_points": 1,
                            "unfeedback_points": 2,
                            "collab_points": 0,
                        }
                    ),
                    FakeRow(
                        {
                            "locality": "其他单位",
                            "damaged_points": 1,
                            "damaged_plants": 5,
                            "completed_points": 1,
                            "severe_points": 0,
                            "unfeedback_points": 0,
                            "collab_points": 1,
                        }
                    ),
                ],
                [
                    FakeRow(
                        {
                            "locality": "宋庄镇",
                            "code": "SZ001",
                            "name": "村口",
                        }
                    ),
                ],
            ]
        )

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_white_moth_locality_summary(
                year=2026,
                generation="第一代",
                as_of_date="2026-06-15",
                severe_plant_threshold=15,
            )

        self.assertEqual(result["year"], 2026)
        self.assertEqual(result["generation"], "第一代")
        self.assertEqual(result["severe_plant_threshold"], 15)
        self.assertEqual(result["totals"]["damaged_points"], 5)
        self.assertEqual(result["totals"]["damaged_plants"], 25)
        self.assertEqual(result["totals"]["completed_points"], 3)
        self.assertEqual(result["totals"]["completion_rate"], 60.0)
        self.assertEqual(result["totals"]["severe_points"], 1)
        self.assertEqual(result["totals"]["unfeedback_points"], 1)
        self.assertEqual(result["totals"]["collab_points"], 1)
        self.assertEqual(len(result["localities"]), 23)
        self.assertEqual(result["as_of_date"], "2026-06-15")
        songzhuang = next(item for item in result["localities"] if item["locality"] == "宋庄镇")
        self.assertEqual(
            songzhuang["unfeedback_sites"],
            [{"code": "SZ001", "name": "村口"}],
        )
        self.assertEqual(connection.fetch_calls[0][1], (2026, "第一代", 15, date(2026, 6, 15)))
        self.assertEqual(connection.fetch_calls[1][1], (2026, "第一代", date(2026, 6, 15)))

    async def test_locality_summary_defaults_year_and_as_of_when_missing(self) -> None:
        connection = SequentialFakeConnection([[], []])

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_white_moth_locality_summary()

        self.assertEqual(result["year"], date.today().year)
        self.assertEqual(result["as_of_date"], date.today().isoformat())
        self.assertIsNone(result["generation"])
        self.assertEqual(
            connection.fetch_calls[0][1],
            (date.today().year, None, 10, date.today()),
        )
        self.assertEqual(
            connection.fetch_calls[1][1],
            (date.today().year, None, date.today()),
        )


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

    async def test_white_moth_generation_router_returns_service_result(self) -> None:
        payload = {"as_of_date": "2026-07-11", "year": 2026, "generations": []}

        with patch(
            "backend.routers.statistics.get_white_moth_generation_summary",
            new=AsyncMock(return_value=payload),
        ) as service_mock:
            result = await get_white_moth_generation_statistics(year=2025)

        self.assertEqual(result, payload)
        service_mock.assert_awaited_once_with(year=2025)

    async def test_white_moth_generation_router_wraps_errors(self) -> None:
        with patch(
            "backend.routers.statistics.get_white_moth_generation_summary",
            new=AsyncMock(side_effect=RuntimeError("连接失败")),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_white_moth_generation_statistics()

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.detail, "读取美国白蛾世代汇总失败：连接失败")

    async def test_white_moth_locality_router_returns_service_result(self) -> None:
        payload = {
            "year": 2026,
            "generation": None,
            "as_of_date": "2026-06-15",
            "severe_plant_threshold": 10,
            "totals": {
                "damaged_points": 0,
                "damaged_plants": 0,
                "completed_points": 0,
                "completion_rate": 0.0,
                "severe_points": 0,
                "collab_points": 0,
            },
            "localities": [],
        }

        with patch(
            "backend.routers.statistics.get_white_moth_locality_summary",
            new=AsyncMock(return_value=payload),
        ) as service_mock:
            result = await get_white_moth_locality_statistics(
                year=2026,
                generation="第二代",
                as_of_date="2026-06-15",
                severe_plant_threshold=20,
            )

        self.assertEqual(result, payload)
        service_mock.assert_awaited_once_with(
            year=2026,
            generation="第二代",
            as_of_date="2026-06-15",
            severe_plant_threshold=20,
        )

    async def test_white_moth_locality_router_wraps_errors(self) -> None:
        with patch(
            "backend.routers.statistics.get_white_moth_locality_summary",
            new=AsyncMock(side_effect=RuntimeError("连接失败")),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_white_moth_locality_statistics()

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.detail, "读取美国白蛾属地受害汇总失败：连接失败")


if __name__ == "__main__":
    unittest.main()
