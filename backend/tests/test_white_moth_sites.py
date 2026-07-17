from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.db.postgres import (
    WhiteMothSiteCodeError,
    WhiteMothSiteDuplicateError,
    create_white_moth_site,
    get_white_moth_site_code_hint,
    resolve_white_moth_site_locality,
    resolve_white_moth_site_prefix,
)
from backend.routers.map import get_white_moth_site_code_hint_endpoint, post_white_moth_site
from backend.schemas import WhiteMothSiteCreateRequest


class WhiteMothSiteCodeTest(unittest.TestCase):
    def test_code_is_normalized_and_locality_is_resolved(self) -> None:
        code, locality = resolve_white_moth_site_locality(" mq001 ")

        self.assertEqual(code, "MQ001")
        self.assertEqual(locality, "马驹桥镇")

    def test_new_locality_prefixes_are_resolved(self) -> None:
        expected_localities = {
            "YS001": "永顺镇",
            "YZ001": "杨庄街道",
            "YQ001": "玉桥街道",
            "LY001": "梨园镇",
            "WJ001": "文景街道",
            "JK001": "九棵树街道",
            "ZC001": "中仓街道",
            "XH001": "新华街道",
            "LYI001": "潞邑街道",
            "LYU001": "潞源街道",
            "BY001": "北苑街道",
            "TY001": "通运街道",
            "LH001": "临河里街道",
        }

        for code, expected_locality in expected_localities.items():
            with self.subTest(code=code):
                self.assertEqual(
                    resolve_white_moth_site_locality(code),
                    (code, expected_locality),
                )

    def test_three_letter_prefix_is_not_confused_with_two_letter(self) -> None:
        self.assertEqual(
            resolve_white_moth_site_locality("LYI001"),
            ("LYI001", "潞邑街道"),
        )
        self.assertEqual(
            resolve_white_moth_site_locality("LYU001"),
            ("LYU001", "潞源街道"),
        )
        self.assertEqual(
            resolve_white_moth_site_locality("LY001"),
            ("LY001", "梨园镇"),
        )

    def test_unknown_prefix_is_rejected(self) -> None:
        with self.assertRaises(WhiteMothSiteCodeError):
            resolve_white_moth_site_locality("AB001")

    def test_digit_count_is_rejected(self) -> None:
        for code in ("MQ01", "MQ0001", "LYI01", "LYI0001"):
            with self.subTest(code=code):
                with self.assertRaises(WhiteMothSiteCodeError):
                    resolve_white_moth_site_locality(code)

    def test_prefix_resolves_locality(self) -> None:
        self.assertEqual(resolve_white_moth_site_prefix("mq"), ("MQ", "马驹桥镇"))
        self.assertEqual(resolve_white_moth_site_prefix("lyi"), ("LYI", "潞邑街道"))

    def test_unknown_prefix_helper_is_rejected(self) -> None:
        with self.assertRaises(WhiteMothSiteCodeError):
            resolve_white_moth_site_prefix("AB")


class WhiteMothSiteCodeHintTest(unittest.IsolatedAsyncioTestCase):
    async def test_hint_returns_next_code_from_max_serial(self) -> None:
        fetchrow_mock = AsyncMock(return_value={"max_serial": 42})

        with patch("backend.db.postgres.fetchrow", new=fetchrow_mock):
            result = await get_white_moth_site_code_hint("mq")

        self.assertEqual(result["prefix"], "MQ")
        self.assertEqual(result["locality"], "马驹桥镇")
        self.assertEqual(result["latest_code"], "MQ042")
        self.assertEqual(result["latest_serial"], 42)
        self.assertEqual(result["suggested_next_code"], "MQ043")

        serial_pattern, code_pattern = fetchrow_mock.await_args.args[1:3]
        self.assertEqual(serial_pattern, r"^MQ([0-9]{3})$")
        self.assertEqual(code_pattern, r"^MQ[0-9]{3}$")

    async def test_hint_returns_first_code_when_empty(self) -> None:
        fetchrow_mock = AsyncMock(return_value={"max_serial": None})

        with patch("backend.db.postgres.fetchrow", new=fetchrow_mock):
            result = await get_white_moth_site_code_hint("LYI")

        self.assertEqual(result["prefix"], "LYI")
        self.assertEqual(result["locality"], "潞邑街道")
        self.assertIsNone(result["latest_code"])
        self.assertIsNone(result["latest_serial"])
        self.assertEqual(result["suggested_next_code"], "LYI001")

    async def test_hint_returns_null_next_when_serial_overflows(self) -> None:
        fetchrow_mock = AsyncMock(return_value={"max_serial": 999})

        with patch("backend.db.postgres.fetchrow", new=fetchrow_mock):
            result = await get_white_moth_site_code_hint("MQ")

        self.assertEqual(result["latest_code"], "MQ999")
        self.assertIsNone(result["suggested_next_code"])

    async def test_router_returns_422_for_unknown_prefix(self) -> None:
        with patch(
            "backend.routers.map.get_white_moth_site_code_hint",
            new=AsyncMock(side_effect=WhiteMothSiteCodeError("未知编号前缀")),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_white_moth_site_code_hint_endpoint(prefix="AB")

        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(context.exception.detail, "未知编号前缀")


class WhiteMothSiteCreateTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_site_uses_normalized_code_and_generated_gid(self) -> None:
        fetchrow_mock = AsyncMock(
            return_value={
                "gid": 14,
                "code": "MQ001",
                "locality": "马驹桥镇",
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
