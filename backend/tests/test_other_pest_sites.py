from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.db.postgres import (
    OtherPestSiteCodeError,
    OtherPestSiteDuplicateError,
    create_other_pest_site,
    get_other_pest_site_code_hint,
    get_other_pest_site_code_rules,
    validate_other_pest_site,
)
from backend.routers.map import post_other_pest_site
from backend.schemas import OtherPestSiteCreateRequest


class OtherPestSiteCodeTest(unittest.TestCase):
    def test_code_is_normalized(self) -> None:
        code, locality = validate_other_pest_site(" qt0007 ", "梨园镇")

        self.assertEqual(code, "QT0007")
        self.assertEqual(locality, "梨园镇")

    def test_invalid_code_patterns_are_rejected(self) -> None:
        for code in ("QT001", "QT00007", "MQ0001", "ABCD1", "qt 0001"):
            with self.subTest(code=code):
                with self.assertRaises(OtherPestSiteCodeError):
                    validate_other_pest_site(code, "梨园镇")

    def test_unknown_locality_is_rejected(self) -> None:
        with self.assertRaises(OtherPestSiteCodeError):
            validate_other_pest_site("QT0007", "不存在的乡镇")

    def test_code_rules_include_pattern_and_localities(self) -> None:
        rules = get_other_pest_site_code_rules()

        self.assertEqual(rules["code_pattern"], r"^QT\d{4}$")
        self.assertEqual(rules["code_example"], "QT0001")
        self.assertEqual(rules["code_prefix"], "QT")
        self.assertIn("梨园镇", rules["localities"])
        self.assertIn("潞邑街道", rules["localities"])
        self.assertEqual(
            len(rules["localities"]), len(set(rules["localities"]))
        )


class OtherPestSiteCodeHintTest(unittest.IsolatedAsyncioTestCase):
    async def test_hint_returns_next_code_from_max_serial(self) -> None:
        fetchrow_mock = AsyncMock(return_value={"max_serial": 6})

        with patch("backend.db.other_pest_sites.fetchrow", new=fetchrow_mock):
            result = await get_other_pest_site_code_hint()

        self.assertEqual(result["prefix"], "QT")
        self.assertEqual(result["latest_code"], "QT0006")
        self.assertEqual(result["latest_serial"], 6)
        self.assertEqual(result["suggested_next_code"], "QT0007")

        serial_pattern, code_pattern = fetchrow_mock.await_args.args[1:3]
        self.assertEqual(serial_pattern, r"^QT([0-9]{4})$")
        self.assertEqual(code_pattern, r"^QT[0-9]{4}$")

    async def test_hint_returns_first_code_when_empty(self) -> None:
        fetchrow_mock = AsyncMock(return_value={"max_serial": None})

        with patch("backend.db.other_pest_sites.fetchrow", new=fetchrow_mock):
            result = await get_other_pest_site_code_hint()

        self.assertIsNone(result["latest_code"])
        self.assertIsNone(result["latest_serial"])
        self.assertEqual(result["suggested_next_code"], "QT0001")

    async def test_hint_returns_null_next_when_serial_overflows(self) -> None:
        fetchrow_mock = AsyncMock(return_value={"max_serial": 9999})

        with patch("backend.db.other_pest_sites.fetchrow", new=fetchrow_mock):
            result = await get_other_pest_site_code_hint()

        self.assertEqual(result["latest_code"], "QT9999")
        self.assertIsNone(result["suggested_next_code"])


class OtherPestSiteCreateTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_site_inserts_normalized_values(self) -> None:
        fetchrow_mock = AsyncMock(
            side_effect=[
                None,
                {
                    "gid": 8,
                    "code": "QT0007",
                    "locality": "梨园镇",
                    "site_name": "示范点",
                    "longitude": 116.5,
                    "latitude": 39.7,
                },
            ]
        )

        with patch("backend.db.other_pest_sites.fetchrow", new=fetchrow_mock):
            result = await create_other_pest_site(
                code="qt0007",
                site_name=" 示范点 ",
                locality="梨园镇",
                longitude=116.5,
                latitude=39.7,
            )

        self.assertEqual(fetchrow_mock.await_count, 2)
        insert_call = fetchrow_mock.await_args_list[1]
        self.assertIn(
            "ST_SetSRID(ST_MakePoint($4, $5), 4326)", insert_call.args[0]
        )
        self.assertEqual(
            insert_call.args[1:], ("QT0007", "梨园镇", "示范点", 116.5, 39.7)
        )
        self.assertEqual(result["gid"], 8)

    async def test_create_site_rejects_duplicate_code(self) -> None:
        fetchrow_mock = AsyncMock(return_value={"?column?": 1})

        with patch("backend.db.other_pest_sites.fetchrow", new=fetchrow_mock):
            with self.assertRaises(OtherPestSiteDuplicateError):
                await create_other_pest_site(
                    code="QT0006",
                    site_name="",
                    locality="梨园镇",
                    longitude=116.5,
                    latitude=39.7,
                )

        self.assertEqual(fetchrow_mock.await_count, 1)

    async def test_router_returns_409_for_duplicate_code(self) -> None:
        with patch(
            "backend.routers.map.create_other_pest_site",
            new=AsyncMock(side_effect=OtherPestSiteDuplicateError("编号已存在：QT0007")),
        ):
            with self.assertRaises(HTTPException) as context:
                await post_other_pest_site(
                    OtherPestSiteCreateRequest(
                        code="QT0007",
                        site_name="",
                        locality="梨园镇",
                        longitude=116.5,
                        latitude=39.7,
                    )
                )

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(context.exception.detail, "编号已存在：QT0007")

    async def test_router_returns_422_for_invalid_code(self) -> None:
        with patch(
            "backend.routers.map.create_other_pest_site",
            new=AsyncMock(side_effect=OtherPestSiteCodeError("编号格式不正确")),
        ):
            with self.assertRaises(HTTPException) as context:
                await post_other_pest_site(
                    OtherPestSiteCreateRequest(
                        code="MQ001",
                        site_name="",
                        locality="梨园镇",
                        longitude=116.5,
                        latitude=39.7,
                    )
                )

        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(context.exception.detail, "编号格式不正确")


if __name__ == "__main__":
    unittest.main()
