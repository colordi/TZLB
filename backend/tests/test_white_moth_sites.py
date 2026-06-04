from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.db.postgres import (
    WhiteMothSiteCodeError,
    WhiteMothSiteDuplicateError,
    create_white_moth_site,
    resolve_white_moth_site_township,
)
from backend.routers.map import post_white_moth_site
from backend.schemas import WhiteMothSiteCreateRequest


class WhiteMothSiteCodeTest(unittest.TestCase):
    def test_code_is_normalized_and_township_is_resolved(self) -> None:
        code, township = resolve_white_moth_site_township(" mq001 ")

        self.assertEqual(code, "MQ001")
        self.assertEqual(township, "马驹桥镇")

    def test_new_township_prefixes_are_resolved(self) -> None:
        expected_townships = {
            "YS001": "永顺镇",
            "LY001": "梨园镇",
            "WJ001": "文景街道",
        }

        for code, expected_township in expected_townships.items():
            with self.subTest(code=code):
                self.assertEqual(
                    resolve_white_moth_site_township(code),
                    (code, expected_township),
                )

    def test_unknown_prefix_is_rejected(self) -> None:
        with self.assertRaises(WhiteMothSiteCodeError):
            resolve_white_moth_site_township("AB001")

    def test_digit_count_is_rejected(self) -> None:
        for code in ("MQ01", "MQ0001"):
            with self.subTest(code=code):
                with self.assertRaises(WhiteMothSiteCodeError):
                    resolve_white_moth_site_township(code)


class WhiteMothSiteCreateTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_site_uses_normalized_code_and_generated_gid(self) -> None:
        fetchrow_mock = AsyncMock(
            return_value={
                "gid": 14,
                "code": "MQ001",
                "township": "马驹桥镇",
                "site_name": "示范点",
                "longitude": 116.5,
                "latitude": 39.7,
            }
        )

        with patch("backend.db.postgres.fetchrow", new=fetchrow_mock):
            result = await create_white_moth_site(
                code="mq001",
                site_name=" 示范点 ",
                longitude=116.5,
                latitude=39.7,
            )

        query = fetchrow_mock.await_args.args[0]
        args = fetchrow_mock.await_args.args[1:]

        self.assertIn("ST_SetSRID(ST_MakePoint($4, $5), 4326)", query)
        self.assertNotIn("gid", query.split("VALUES", maxsplit=1)[0])
        self.assertEqual(args, ("MQ001", "马驹桥镇", "示范点", 116.5, 39.7))
        self.assertEqual(result["gid"], 14)

    async def test_router_returns_409_for_duplicate_code(self) -> None:
        with patch(
            "backend.routers.map.create_white_moth_site",
            new=AsyncMock(side_effect=WhiteMothSiteDuplicateError("编号已存在：MQ001")),
        ):
            with self.assertRaises(HTTPException) as context:
                await post_white_moth_site(
                    WhiteMothSiteCreateRequest(
                        code="MQ001",
                        site_name="",
                        longitude=116.5,
                        latitude=39.7,
                    )
                )

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(context.exception.detail, "编号已存在：MQ001")

    async def test_router_returns_422_for_invalid_code(self) -> None:
        with patch(
            "backend.routers.map.create_white_moth_site",
            new=AsyncMock(side_effect=WhiteMothSiteCodeError("编号格式不正确")),
        ):
            with self.assertRaises(HTTPException) as context:
                await post_white_moth_site(
                    WhiteMothSiteCreateRequest(
                        code="AB001",
                        site_name="",
                        longitude=116.5,
                        latitude=39.7,
                    )
                )

        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(context.exception.detail, "编号格式不正确")


if __name__ == "__main__":
    unittest.main()
