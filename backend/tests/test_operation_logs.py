from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.db.admin import list_operation_logs
from backend.routers.admin import get_operation_logs


class ListOperationLogsTest(unittest.IsolatedAsyncioTestCase):
    async def test_serializes_occurred_at_isoformat(self) -> None:
        occurred = datetime(2026, 7, 9, 10, 30, tzinfo=timezone.utc)
        count_row = {"total": 5}

        async def fake_fetch(query, *args):
            if "COUNT(*)" in query:
                return [count_row]
            return [
                {
                    "id": 1,
                    "occurred_at": occurred,
                    "action": "删除美国白蛾点位",
                    "operator_id": 7,
                    "operator_username": "investigator1",
                    "operator_display_name": "张调查",
                    "operator_role": "investigator",
                    "site_code": "MQ001",
                    "site_name": "示范点",
                    "locality": "马驹桥镇",
                    "longitude": 116.5,
                    "latitude": 39.7,
                    "survey_record_count": 2,
                }
            ]

        with patch(
            "backend.db.admin.ensure_operation_log_storage",
            new=AsyncMock(return_value=None),
        ), patch("backend.db.admin.fetchrow", new=AsyncMock(return_value=count_row)), patch(
            "backend.db.admin.fetch", new=fake_fetch
        ):
            items, total = await list_operation_logs(limit=100, offset=0)

        self.assertEqual(total, 5)
        self.assertEqual(items[0]["occurred_at"], occurred.isoformat())
        self.assertEqual(items[0]["site_code"], "MQ001")
        self.assertEqual(items[0]["survey_record_count"], 2)


class OperationLogsEndpointTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_items_and_total(self) -> None:
        item = {
            "id": 1,
            "occurred_at": "2026-07-09T10:30:00+00:00",
            "action": "删除美国白蛾点位",
            "operator_id": 7,
            "operator_username": "investigator1",
            "operator_display_name": "张调查",
            "operator_role": "investigator",
            "site_code": "MQ001",
            "site_name": "示范点",
            "locality": "马驹桥镇",
            "longitude": 116.5,
            "latitude": 39.7,
            "survey_record_count": 2,
        }
        with patch(
            "backend.routers.admin.list_operation_logs",
            new=AsyncMock(return_value=([item], 1)),
        ):
            response = await get_operation_logs(limit=100, offset=0)

        self.assertEqual(response.total, 1)
        self.assertEqual(response.items[0].site_code, "MQ001")
        self.assertEqual(response.items[0].survey_record_count, 2)

    async def test_rejects_limit_above_max(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await get_operation_logs(limit=501, offset=0)
        self.assertEqual(context.exception.status_code, 400)

    async def test_rejects_limit_below_min(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await get_operation_logs(limit=0, offset=0)
        self.assertEqual(context.exception.status_code, 400)

    async def test_rejects_negative_offset(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await get_operation_logs(limit=100, offset=-1)
        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
