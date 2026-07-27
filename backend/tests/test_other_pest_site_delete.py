from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.db.postgres import (
    check_other_pest_site_deletion,
    delete_other_pest_site,
)
from backend.routers.map import (
    delete_other_pest_site_endpoint,
    get_other_pest_site_delete_check,
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
    def __init__(self, deleted_rows, survey_count=0):
        self.deleted_rows = deleted_rows
        self.survey_count = survey_count
        self.transaction_calls = 0
        self.execute_calls: list[tuple] = []

    def transaction(self):
        self.transaction_calls += 1
        return FakeTransaction()

    async def fetch(self, query, *args):
        return self.deleted_rows

    async def fetchrow(self, query, *args):
        return {"survey_record_count": self.survey_count}

    async def execute(self, query, *args):
        self.execute_calls.append(args)


OPERATOR = {
    "id": 7,
    "username": "investigator1",
    "display_name": "张调查",
    "role": "investigator",
}

DELETED_ROW = {
    "code": "QT0007",
    "locality": "梨园镇",
    "site_name": "示范点",
    "longitude": 116.5,
    "latitude": 39.7,
}


class CheckOtherPestSiteDeletionTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_site_info_and_survey_count(self) -> None:
        fetchrow_mock = AsyncMock(
            side_effect=[
                {
                    "code": "QT0007",
                    "locality": "梨园镇",
                    "site_name": "示范点",
                    "longitude": 116.5,
                    "latitude": 39.7,
                },
                {"survey_record_count": 3},
            ]
        )

        with patch("backend.db.postgres.fetchrow", new=fetchrow_mock):
            result = await check_other_pest_site_deletion("QT0007")

        self.assertEqual(result["code"], "QT0007")
        self.assertEqual(result["survey_record_count"], 3)
        self.assertEqual(result["locality"], "梨园镇")
        # 点位查询优先带坐标的记录
        site_query = fetchrow_mock.await_args_list[0].args[0]
        self.assertIn("ORDER BY (s.geom IS NOT NULL) DESC", site_query)

    async def test_returns_none_when_site_missing(self) -> None:
        with patch("backend.db.postgres.fetchrow", new=AsyncMock(return_value=None)):
            result = await check_other_pest_site_deletion("QT9999")
        self.assertIsNone(result)


class DeleteOtherPestSiteTest(unittest.IsolatedAsyncioTestCase):
    async def test_delete_writes_log_in_same_transaction(self) -> None:
        connection = FakeConnection(deleted_rows=[DELETED_ROW], survey_count=2)
        pool = FakePool(connection)

        with patch(
            "backend.db.admin.ensure_operation_log_storage",
            new=AsyncMock(return_value=None),
        ), patch("backend.db.postgres.ensure_pool", new=AsyncMock(return_value=pool)):
            result = await delete_other_pest_site(code="QT0007", operator=OPERATOR)

        self.assertEqual(connection.transaction_calls, 1)
        self.assertEqual(len(connection.execute_calls), 1)
        log_args = connection.execute_calls[0]
        self.assertEqual(log_args[0], "删除其他害虫点位")
        self.assertEqual(log_args[1], OPERATOR["id"])
        self.assertEqual(log_args[2], OPERATOR["username"])
        self.assertEqual(log_args[5], "QT0007")
        self.assertEqual(log_args[10], 2)
        self.assertEqual(result["code"], "QT0007")
        self.assertEqual(result["survey_record_count"], 2)

    async def test_delete_duplicate_code_prefers_row_with_geometry(self) -> None:
        geomless_row = {**DELETED_ROW, "longitude": None, "latitude": None}
        connection = FakeConnection(deleted_rows=[geomless_row, DELETED_ROW])
        pool = FakePool(connection)

        with patch(
            "backend.db.admin.ensure_operation_log_storage",
            new=AsyncMock(return_value=None),
        ), patch("backend.db.postgres.ensure_pool", new=AsyncMock(return_value=pool)):
            result = await delete_other_pest_site(code="QT0007", operator=OPERATOR)

        self.assertEqual(result["longitude"], 116.5)
        self.assertEqual(result["latitude"], 39.7)

    async def test_delete_returns_none_when_site_missing(self) -> None:
        connection = FakeConnection(deleted_rows=[])
        pool = FakePool(connection)

        with patch(
            "backend.db.admin.ensure_operation_log_storage",
            new=AsyncMock(return_value=None),
        ), patch("backend.db.postgres.ensure_pool", new=AsyncMock(return_value=pool)):
            result = await delete_other_pest_site(code="QT9999", operator=OPERATOR)

        self.assertIsNone(result)
        self.assertEqual(len(connection.execute_calls), 0)


class DeleteOtherPestSiteRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_router_returns_404_when_missing(self) -> None:
        with patch(
            "backend.routers.map.delete_other_pest_site",
            new=AsyncMock(return_value=None),
        ):
            with self.assertRaises(HTTPException) as context:
                await delete_other_pest_site_endpoint(
                    "qt9999",
                    current_user=OPERATOR,
                )

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("QT9999", context.exception.detail)

    async def test_router_returns_deleted_info(self) -> None:
        deleted = {
            "code": "QT0007",
            "site_name": "示范点",
            "locality": "梨园镇",
            "longitude": 116.5,
            "latitude": 39.7,
            "survey_record_count": 2,
        }
        with patch(
            "backend.routers.map.delete_other_pest_site",
            new=AsyncMock(return_value=deleted),
        ):
            response = await delete_other_pest_site_endpoint(
                "qt0007",
                current_user=OPERATOR,
            )

        self.assertEqual(response.code, "QT0007")
        self.assertEqual(response.survey_record_count, 2)

    async def test_delete_check_router_returns_exists_false_when_missing(self) -> None:
        with patch(
            "backend.routers.map.check_other_pest_site_deletion",
            new=AsyncMock(return_value=None),
        ):
            response = await get_other_pest_site_delete_check("qt9999")

        self.assertEqual(response.code, "QT9999")
        self.assertFalse(response.exists)

    async def test_delete_check_router_returns_site_info(self) -> None:
        check_result = {
            "code": "QT0007",
            "locality": "梨园镇",
            "site_name": "示范点",
            "longitude": 116.5,
            "latitude": 39.7,
            "survey_record_count": 3,
        }
        with patch(
            "backend.routers.map.check_other_pest_site_deletion",
            new=AsyncMock(return_value=check_result),
        ):
            response = await get_other_pest_site_delete_check("qt0007")

        self.assertTrue(response.exists)
        self.assertEqual(response.survey_record_count, 3)


if __name__ == "__main__":
    unittest.main()
