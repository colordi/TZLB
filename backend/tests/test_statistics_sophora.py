from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from backend.services.statistics.service import (
    get_sophora_generation_summary,
    get_sophora_locality_summary,
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
        self.fetch_calls: list[tuple] = []

    async def fetch(self, query: str, *args):
        self.fetch_calls.append((query, args))
        return self.results.pop(0)


class FakeRow(dict):
    def __getitem__(self, key):
        return super().__getitem__(key)


class SophoraStatisticsServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_generation_summary_serializes_kpis(self) -> None:
        connection = SequentialFakeConnection(
            [
                [
                    FakeRow(
                        {
                            "世代": "第一代",
                            "sort_order": 1,
                            "year": 2026,
                            "as_of_date": date(2026, 8, 12),
                            "surveyed_points": 100,
                            "damaged_points": 20,
                            "light_points": 10,
                            "medium_points": 5,
                            "severe_points": 5,
                            "avg_insect_count": 8.25,
                            "start_date": date(2026, 5, 9),
                            "end_date": date(2026, 5, 24),
                            "ledger_points": 60,
                            "pending_treatment": 4,
                            "pending_recheck": 45,
                            "recheck_abnormal": 10,
                            "closed_points": 1,
                        }
                    ),
                    FakeRow(
                        {
                            "世代": "第二代",
                            "sort_order": 2,
                            "year": 2026,
                            "as_of_date": date(2026, 8, 12),
                            "surveyed_points": 0,
                            "damaged_points": 0,
                            "light_points": 0,
                            "medium_points": 0,
                            "severe_points": 0,
                            "avg_insect_count": None,
                            "start_date": None,
                            "end_date": None,
                            "ledger_points": 0,
                            "pending_treatment": 0,
                            "pending_recheck": 0,
                            "recheck_abnormal": 0,
                            "closed_points": 0,
                        }
                    ),
                    FakeRow(
                        {
                            "世代": "第三代",
                            "sort_order": 3,
                            "year": 2026,
                            "as_of_date": date(2026, 8, 12),
                            "surveyed_points": 50,
                            "damaged_points": 0,
                            "light_points": 0,
                            "medium_points": 0,
                            "severe_points": 0,
                            "avg_insect_count": None,
                            "start_date": date(2026, 8, 10),
                            "end_date": date(2026, 8, 11),
                            "ledger_points": 0,
                            "pending_treatment": 0,
                            "pending_recheck": 0,
                            "recheck_abnormal": 0,
                            "closed_points": 0,
                        }
                    ),
                ]
            ]
        )

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_sophora_generation_summary(year=2026)

        self.assertEqual(result["year"], 2026)
        self.assertEqual(len(result["generations"]), 3)
        first = result["generations"][0]
        self.assertEqual(first["generation"], "第一代")
        self.assertEqual(first["surveyed_points"], 100)
        self.assertEqual(first["damaged_points"], 20)
        self.assertEqual(first["damage_rate"], 20.0)
        self.assertEqual(first["avg_insect_count"], 8.2)
        self.assertEqual(first["closure_rate"], 1.7)
        self.assertEqual(first["start_date"], "2026-05-09")

        second = result["generations"][1]
        self.assertIsNone(second["damage_rate"])
        self.assertIsNone(second["closure_rate"])
        self.assertIsNone(second["start_date"])

    async def test_locality_summary_merges_severe_sites_and_totals(self) -> None:
        locality_rows = [
            FakeRow(
                {
                    "locality": "永乐店镇",
                    "monitor_points": 239,
                    "surveyed_points": 57,
                    "damaged_points": 30,
                    "light_points": 10,
                    "medium_points": 12,
                    "severe_points": 8,
                    "avg_insect_count": 9.5,
                    "ledger_points": 30,
                    "pending_treatment": 2,
                    "pending_recheck": 20,
                    "recheck_abnormal": 7,
                    "closed_points": 1,
                }
            ),
            FakeRow(
                {
                    "locality": "宋庄镇",
                    "monitor_points": 303,
                    "surveyed_points": 118,
                    "damaged_points": 21,
                    "light_points": 9,
                    "medium_points": 1,
                    "severe_points": 11,
                    "avg_insect_count": 12.0,
                    "ledger_points": 11,
                    "pending_treatment": 0,
                    "pending_recheck": 10,
                    "recheck_abnormal": 1,
                    "closed_points": 0,
                }
            ),
        ]
        severe_rows = [
            FakeRow(
                {
                    "locality": "永乐店镇",
                    "code": "YL001",
                    "name": "某村",
                    "avg_insect_count": 15,
                    "survey_date": date(2026, 5, 12),
                    "ledger_status": "待复查",
                }
            ),
            FakeRow(
                {
                    "locality": "宋庄镇",
                    "code": "SZ001",
                    "name": "--",
                    "avg_insect_count": 20,
                    "survey_date": date(2026, 5, 15),
                    "ledger_status": None,
                }
            ),
        ]
        connection = SequentialFakeConnection([locality_rows, severe_rows])

        with patch(
            "backend.services.statistics.service.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            result = await get_sophora_locality_summary(year=2026, generation="第一代")

        self.assertEqual(result["year"], 2026)
        self.assertEqual(result["generation"], "第一代")
        self.assertEqual(result["totals"]["surveyed_points"], 175)
        self.assertEqual(result["totals"]["damaged_points"], 51)
        self.assertEqual(result["totals"]["severe_points"], 2)
        self.assertEqual(result["totals"]["closure_rate"], 2.4)

        yongle = next(item for item in result["localities"] if item["locality"] == "永乐店镇")
        self.assertEqual(yongle["severe_points"], 1)
        self.assertEqual(yongle["severe_sites"][0]["code"], "YL001")
        self.assertEqual(yongle["severe_sites"][0]["survey_date"], "2026-05-12")
        self.assertEqual(yongle["coverage_rate"], 23.8)

        args = connection.fetch_calls[0][1]
        self.assertEqual(args, (2026, "第一代"))
