from __future__ import annotations

import unittest

from backend.services import view_builder

BASE_WHITELIST = {
    "美国白蛾点位基础表": ["编号", "geom", "gid", "属地", "点位名称"],
    "杨树点位基础表": ["gid", "geom", "fid", "编号", "属地", "村", "面积", "当前点位状态"],
    "监测点位基础表": ["id", "geom", "点位", "虫种", "树种"],
}

RELATED_WHITELIST = {
    "survey.美国白蛾调查表": [
        "编号", "调查日期", "属地", "点位名称", "危害程度", "年份", "世代",
    ],
    "ledger.春尺蠖问题点位台账": [
        "编号", "属地", "点位名称", "年份", "危害程度", "当前状态",
    ],
}


def _build(definition: dict) -> str:
    return view_builder.build_view_sql(
        definition,
        base_columns_by_table=BASE_WHITELIST,
        related_columns_by_table=RELATED_WHITELIST,
    )


class TaskViewNameValidationTest(unittest.TestCase):
    def test_valid_name_accepted(self) -> None:
        sql = _build(
            {
                "name": "task_baie_2025_gen1",
                "display_name": "美国白蛾2025第一代巡查",
                "base_table": "美国白蛾点位基础表",
            }
        )
        self.assertIn('CREATE OR REPLACE VIEW "views"."task_baie_2025_gen1"', sql)

    def test_invalid_names_rejected(self) -> None:
        for name in ["", "美国白蛾任务", "TASK_2025", "task-2025", "baie_2025", "task_" + "a" * 41]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    _build(
                        {
                            "name": name,
                            "display_name": "任务",
                            "base_table": "美国白蛾点位基础表",
                        }
                    )


class TaskViewBaseOnlySqlTest(unittest.TestCase):
    def test_base_only_sql(self) -> None:
        sql = _build(
            {
                "name": "task_sites_only",
                "display_name": "美国白蛾点位",
                "base_table": "美国白蛾点位基础表",
            }
        )
        self.assertIn('FROM "sites"."美国白蛾点位基础表" AS s', sql)
        self.assertIn('WHERE s."geom" IS NOT NULL', sql)
        self.assertIn('AS "编号"', sql)
        self.assertIn('AS "属地"', sql)
        self.assertIn('AS "点位名称"', sql)
        self.assertNotIn("LEFT JOIN", sql)

    def test_site_name_column_mapping(self) -> None:
        sql = _build(
            {
                "name": "task_yangshu",
                "display_name": "杨树点位",
                "base_table": "杨树点位基础表",
            }
        )
        # 杨树点位基础表无点位名称列，自动探测映射为村
        self.assertIn('NULLIF(BTRIM(s."村"::text), \'\') AS "点位名称"', sql)

    def test_unknown_site_name_column_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _build(
                {
                    "name": "task_x",
                    "display_name": "任务",
                    "base_table": "美国白蛾点位基础表",
                    "site_name_column": "不存在的列",
                }
            )

    def test_unknown_base_table_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _build(
                {
                    "name": "task_x",
                    "display_name": "任务",
                    "base_table": 'x" DROP TABLE users; --',
                }
            )


class TaskViewJoinedSqlTest(unittest.TestCase):
    def test_joined_sql_with_filters(self) -> None:
        sql = _build(
            {
                "name": "task_baie_2025_gen1",
                "display_name": "美国白蛾2025第一代",
                "base_table": "美国白蛾点位基础表",
                "related_table": "survey.美国白蛾调查表",
                "filters": {"年份": "2025", "世代": "第一代"},
            }
        )
        self.assertIn("LEFT JOIN", sql)
        self.assertIn('SELECT DISTINCT ON (BTRIM(r."编号"::text))', sql)
        self.assertIn('FROM "survey"."美国白蛾调查表" AS r', sql)
        self.assertIn("r.\"年份\"::text = '2025'", sql)
        self.assertIn("r.\"世代\"::text = '第一代'", sql)
        self.assertIn('ORDER BY BTRIM(r."编号"::text), r."调查日期" DESC NULLS LAST', sql)
        # 关联表的属地/点位名称与基表输出冲突，应被剔除
        self.assertNotIn('l."属地"', sql)
        self.assertNotIn('l."点位名称"', sql)
        self.assertIn('l."危害程度" AS "危害程度"', sql)

    def test_joined_sql_orders_by_year_when_no_survey_date(self) -> None:
        sql = _build(
            {
                "name": "task_chunchihuo",
                "display_name": "春尺蠖台账",
                "base_table": "杨树点位基础表",
                "related_table": "ledger.春尺蠖问题点位台账",
                "filters": {"年份": "2025"},
            }
        )
        self.assertIn('ORDER BY BTRIM(r."编号"::text), r."年份" DESC NULLS LAST', sql)

    def test_base_without_join_key_cannot_join(self) -> None:
        with self.assertRaises(ValueError):
            _build(
                {
                    "name": "task_x",
                    "display_name": "任务",
                    "base_table": "监测点位基础表",
                    "related_table": "survey.美国白蛾调查表",
                }
            )

    def test_filters_require_related_table(self) -> None:
        with self.assertRaises(ValueError):
            _build(
                {
                    "name": "task_x",
                    "display_name": "任务",
                    "base_table": "美国白蛾点位基础表",
                    "filters": {"年份": "2025"},
                }
            )

    def test_invalid_year_filter_rejected(self) -> None:
        for year in ["202", "2025'; DROP TABLE users; --", "二〇二五"]:
            with self.subTest(year=year):
                with self.assertRaises(ValueError):
                    _build(
                        {
                            "name": "task_x",
                            "display_name": "任务",
                            "base_table": "美国白蛾点位基础表",
                            "related_table": "survey.美国白蛾调查表",
                            "filters": {"年份": year},
                        }
                    )

    def test_invalid_generation_filter_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _build(
                {
                    "name": "task_x",
                    "display_name": "任务",
                    "base_table": "美国白蛾点位基础表",
                    "related_table": "survey.美国白蛾调查表",
                    "filters": {"世代": "第四代'; DROP"},
                }
            )

    def test_generation_filter_requires_column(self) -> None:
        # 春尺蠖台账无世代列
        with self.assertRaises(ValueError):
            _build(
                {
                    "name": "task_x",
                    "display_name": "任务",
                    "base_table": "杨树点位基础表",
                    "related_table": "ledger.春尺蠖问题点位台账",
                    "filters": {"世代": "第一代"},
                }
            )

    def test_unknown_related_table_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _build(
                {
                    "name": "task_x",
                    "display_name": "任务",
                    "base_table": "美国白蛾点位基础表",
                    "related_table": "public.users",
                }
            )


class TaskViewCodeListTest(unittest.TestCase):
    def test_codes_baked_into_base_only_sql(self) -> None:
        sql = _build(
            {
                "name": "task_codes",
                "display_name": "清单图层",
                "base_table": "美国白蛾点位基础表",
                "filters": {"codes": ["YB001", "YB002", "YB001", " YB003 "]},
            }
        )
        # 去重、去空白后烘焙为 IN 字面量
        self.assertIn("BTRIM(s.\"编号\"::text) IN ('YB001', 'YB002', 'YB003')", sql)
        self.assertNotIn("LEFT JOIN", sql)

    def test_codes_combined_with_join_and_filters(self) -> None:
        sql = _build(
            {
                "name": "task_codes_join",
                "display_name": "清单+关联",
                "base_table": "美国白蛾点位基础表",
                "related_table": "survey.美国白蛾调查表",
                "filters": {"年份": "2026", "codes": ["YB001"]},
            }
        )
        # 编号清单在基表侧，年份在关联子查询侧
        self.assertIn("BTRIM(s.\"编号\"::text) IN ('YB001')", sql)
        self.assertIn("r.\"年份\"::text = '2026'", sql)

    def test_codes_require_join_key_in_base(self) -> None:
        with self.assertRaises(ValueError):
            _build(
                {
                    "name": "task_x",
                    "display_name": "任务",
                    "base_table": "监测点位基础表",
                    "filters": {"codes": ["YB001"]},
                }
            )

    def test_illegal_codes_rejected(self) -> None:
        for codes in [
            ["YB001'; DROP TABLE users; --"],
            ['YB001"'],
            ["YB001\\YB002"],
            ["YB 001"],
            ["a" * 65],
        ]:
            with self.subTest(codes=codes):
                with self.assertRaises(ValueError):
                    _build(
                        {
                            "name": "task_x",
                            "display_name": "任务",
                            "base_table": "美国白蛾点位基础表",
                            "filters": {"codes": codes},
                        }
                    )

    def test_too_many_codes_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _build(
                {
                    "name": "task_x",
                    "display_name": "任务",
                    "base_table": "美国白蛾点位基础表",
                    "filters": {"codes": [f"C{i:04d}" for i in range(2001)]},
                }
            )

    def test_codes_must_be_list(self) -> None:
        with self.assertRaises(ValueError):
            _build(
                {
                    "name": "task_x",
                    "display_name": "任务",
                    "base_table": "美国白蛾点位基础表",
                    "filters": {"codes": "YB001"},
                }
            )


class ViewDeleteGuardTest(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_view_name_rejected_before_db(self) -> None:
        for name in ["", "views.美国白蛾点位", "美国白蛾 调查", 'x"; DROP TABLE t', "a" * 64]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    await view_builder.delete_task_view(name)


if __name__ == "__main__":
    unittest.main()
