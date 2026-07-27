from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.db.postgres import (
    check_white_moth_site_deletion,
    delete_white_moth_site,
)
from backend.routers.map import (
    delete_white_moth_site_endpoint,
    get_white_moth_site_delete_check,
)


class FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakePool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return FakeAcquire(self.connection)


class FakeConnection:
    def __init__(self, delete_row, survey_count=0):
        self.delete_row = delete_row
        self.survey_count = survey_count
        self.transaction_calls = 0
        self.execute_calls: list[tuple] = []
        self._fetchrow_sequence = 0

    def transaction(self):
        self.transaction_calls += 1
        return FakeTransaction()

    async def fetchrow(self, query, *args):
        if self.delete_row is None:
            return None
        if self._fetchrow_sequence == 0:
            self._fetchrow_sequence += 1
            return self.delete_row
        self._fetchrow_sequence += 1
        return {"survey_record_count": self.survey_count}

    async def execute(self, query, *args):
        self.execute_calls.append(args)


OPERATOR = {
    "id": 7,
    "username": "investigator1",
    "display_name": "张调查",
    "role": "investigator",
}


class CheckWhiteMothSiteDeletionTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_site_info_and_survey_count(self) -> None:
        row = {
            "code": "MQ001",
            "locality": "马驹桥镇",
            "site_name": "示范点",
            "longitude": 116.5,
            "latitude": 39.7,
            "survey_record_count": 3,
        }
        with patch("backend.db.white_moth_sites.fetchrow", new=AsyncMock(return_value=row)):
            result = await check_white_moth_site_deletion("MQ001")

        self.assertEqual(result["code"], "MQ001")
        self.assertEqual(result["survey_record_count"], 3)
        self.assertEqual(result["locality"], "马驹桥镇")

    async def test_returns_none_when_site_missing(self) -> None:
        with patch("backend.db.white_moth_sites.fetchrow", new=AsyncMock(return_value=None)):
            result = await check_white_moth_site_deletion("MQ001")
        self.assertIsNone(result)


class DeleteWhiteMothSiteTest(unittest.IsolatedAsyncioTestCase):
    async def test_delete_writes_log_in_same_transaction(self) -> None:
        delete_row = {
            "gid": 14,
            "code": "MQ001",
            "locality": "马驹桥镇",
            "site_name": "示范点",
            "longitude": 116.5,
            "latitude": 39.7,
        }
        connection = FakeConnection(delete_row=delete_row, survey_count=2)
        pool = FakePool(connection)

        with patch(
            "backend.db.admin.ensure_operation_log_storage",
            new=AsyncMock(return_value=None),
        ), patch("backend.db.white_moth_sites.ensure_pool", new=AsyncMock(return_value=pool)):
            result = await delete_white_moth_site(code="MQ001", operator=OPERATOR)

        self.assertEqual(connection.transaction_calls, 1)
        self.assertEqual(len(connection.execute_calls), 1)
        log_args = connection.execute_calls[0]
        self.assertEqual(log_args[0], "删除美国白蛾点位")
        self.assertEqual(log_args[1], OPERATOR["id"])
        self.assertEqual(log_args[2], OPERATOR["username"])
        self.assertEqual(log_args[5], "MQ001")
        self.assertEqual(log_args[10], 2)
        self.assertEqual(result["code"], "MQ001")
        self.assertEqual(result["survey_record_count"], 2)

    async def test_delete_returns_none_when_site_missing(self) -> None:
        connection = FakeConnection(delete_row=None)
        pool = FakePool(connection)

        with patch(
            "backend.db.admin.ensure_operation_log_storage",
            new=AsyncMock(return_value=None),
        ), patch("backend.db.white_moth_sites.ensure_pool", new=AsyncMock(return_value=pool)):
            result = await delete_white_moth_site(code="MQ001", operator=OPERATOR)

        self.assertIsNone(result)
        self.assertEqual(len(connection.execute_calls), 0)


class DeleteWhiteMothSiteRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_router_returns_404_when_missing(self) -> None:
        with patch(
            "backend.routers.map.delete_white_moth_site",
            new=AsyncMock(return_value=None),
        ):
            with self.assertRaises(HTTPException) as context:
                await delete_white_moth_site_endpoint(
                    "mq001",
                    current_user=OPERATOR,
                )

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("MQ001", context.exception.detail)

    async def test_router_returns_deleted_info(self) -> None:
        deleted = {
            "code": "MQ001",
            "site_name": "示范点",
            "locality": "马驹桥镇",
            "longitude": 116.5,
            "latitude": 39.7,
            "survey_record_count": 2,
        }
        with patch(
            "backend.routers.map.delete_white_moth_site",
            new=AsyncMock(return_value=deleted),
        ):
            response = await delete_white_moth_site_endpoint(
                "mq001",
                current_user=OPERATOR,
            )

        self.assertEqual(response.code, "MQ001")
        self.assertEqual(response.survey_record_count, 2)

    async def test_delete_check_router_returns_exists_false_when_missing(self) -> None:
        with patch(
            "backend.routers.map.check_white_moth_site_deletion",
            new=AsyncMock(return_value=None),
        ):
            response = await get_white_moth_site_delete_check("mq001")

        self.assertEqual(response.code, "MQ001")
        self.assertFalse(response.exists)

    async def test_delete_check_router_returns_site_info(self) -> None:
        check_result = {
            "code": "MQ001",
            "locality": "马驹桥镇",
            "site_name": "示范点",
            "longitude": 116.5,
            "latitude": 39.7,
            "survey_record_count": 3,
        }
        with patch(
            "backend.routers.map.check_white_moth_site_deletion",
            new=AsyncMock(return_value=check_result),
        ):
            response = await get_white_moth_site_delete_check("mq001")

        self.assertTrue(response.exists)
        self.assertEqual(response.survey_record_count, 3)


if __name__ == "__main__":
    unittest.main()
