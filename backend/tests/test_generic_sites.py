from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from backend.db.generic_sites import (
    GenericSiteDuplicateError,
    GenericSiteError,
    SiteTableProfile,
    match_prefix,
    validate_code_and_locality,
)
from backend.db.layer_metadata import parse_task_view_source_from_viewdef


class GenericSiteValidationTest(unittest.TestCase):
    def test_match_prefix_prefers_longer_prefix(self) -> None:
        self.assertEqual(match_prefix("LYI"), "LYI")
        self.assertEqual(match_prefix("LYI012"), "LYI")
        self.assertEqual(match_prefix("LY012"), "LY")
        self.assertEqual(match_prefix("MQ"), "MQ")
        self.assertEqual(match_prefix("AB"), "")

    def test_prefix_mode_resolves_locality(self) -> None:
        profile = SiteTableProfile(
            table_name="美国白蛾点位基础表",
            locality_mode="prefix",
            serial_width=3,
            name_column="点位名称",
            code_example="MQ001",
        )
        code, locality = validate_code_and_locality(profile, code=" mq043 ", locality=None)
        self.assertEqual(code, "MQ043")
        self.assertEqual(locality, "马驹桥镇")

    def test_manual_mode_requires_locality(self) -> None:
        profile = SiteTableProfile(
            table_name="其他害虫点位基础表",
            locality_mode="manual",
            serial_width=4,
            name_column="点位名称",
            code_example="QT0001",
            fixed_prefix="QT",
        )
        with self.assertRaises(GenericSiteError):
            validate_code_and_locality(profile, code="QT0008", locality="")
        code, locality = validate_code_and_locality(
            profile, code="qt0008", locality="台湖镇"
        )
        self.assertEqual(code, "QT0008")
        self.assertEqual(locality, "台湖镇")

    def test_yangshu_serial_width_4(self) -> None:
        profile = SiteTableProfile(
            table_name="杨树食叶害虫点位基础表",
            locality_mode="prefix",
            serial_width=4,
            name_column="村",
            code_example="MQ0001",
        )
        code, locality = validate_code_and_locality(
            profile, code="MQ0009", locality=None
        )
        self.assertEqual(code, "MQ0009")
        self.assertEqual(locality, "马驹桥镇")
        with self.assertRaises(GenericSiteError):
            validate_code_and_locality(profile, code="MQ009", locality=None)


class ParseViewdefTest(unittest.TestCase):
    def test_parse_base_table_and_codes(self) -> None:
        viewdef = '''
 SELECT s.geom,
    btrim(s."编号"::text) AS "编号"
   FROM sites."美国白蛾点位基础表" s
  WHERE s.geom IS NOT NULL AND BTRIM(s."编号"::text) IN ('MQ001', 'TH002');
'''
        parsed = parse_task_view_source_from_viewdef(viewdef)
        self.assertEqual(parsed["base_table"], "美国白蛾点位基础表")
        self.assertEqual(parsed["codes"], ["MQ001", "TH002"])


class GenericSiteCreateGuardTest(unittest.IsolatedAsyncioTestCase):
    async def test_code_list_filter_blocks_unknown_code(self) -> None:
        from backend.db.generic_sites import create_generic_site

        with patch(
            "backend.db.generic_sites.resolve_site_table_profile",
            new=AsyncMock(
                return_value=SiteTableProfile(
                    table_name="美国白蛾点位基础表",
                    locality_mode="prefix",
                    serial_width=3,
                    name_column="点位名称",
                    code_example="MQ001",
                )
            ),
        ):
            with self.assertRaises(GenericSiteError) as ctx:
                await create_generic_site(
                    base_table="美国白蛾点位基础表",
                    code="MQ999",
                    site_name="",
                    locality=None,
                    longitude=116.5,
                    latitude=39.7,
                    allowed_codes=["MQ001", "MQ002"],
                )
        self.assertIn("编号清单", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
