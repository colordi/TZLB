from __future__ import annotations

import unittest

from backend.services.statistics.host_summary import (
    OTHER_HOST_NAME,
    aggregate_host_summary,
    aggregate_host_summary_by_generation,
    normalize_host_name,
)


class TestNormalizeHostName(unittest.TestCase):
    def test_strips_whitespace(self):
        self.assertEqual(normalize_host_name("  法桐 "), "法桐")

    def test_strips_trailing_shu(self):
        self.assertEqual(normalize_host_name("桑树"), "桑")
        self.assertEqual(normalize_host_name("杨树"), "杨")
        self.assertEqual(normalize_host_name("白蜡树"), "白蜡")

    def test_alias_mapping(self):
        self.assertEqual(normalize_host_name("柿子"), "柿")
        self.assertEqual(normalize_host_name("红叶李"), "紫叶李")
        self.assertEqual(normalize_host_name("君迁"), "君迁子")

    def test_keeps_single_char_and_regular_names(self):
        self.assertEqual(normalize_host_name("桑"), "桑")
        self.assertEqual(normalize_host_name("紫叶李"), "紫叶李")
        # 单字「树」不去尾
        self.assertEqual(normalize_host_name("树"), "树")

    def test_empty_values(self):
        self.assertEqual(normalize_host_name(""), "")
        self.assertEqual(normalize_host_name(None), "")
        self.assertEqual(normalize_host_name("   "), "")


class TestAggregateHostSummary(unittest.TestCase):
    def test_empty_rows(self):
        result = aggregate_host_summary([])
        self.assertEqual(result["hosts"], [])
        self.assertEqual(
            result["totals"],
            {
                "host_species": 0,
                "damaged_plants": 0,
                "damaged_points": 0,
                "top_host": None,
            },
        )

    def test_aggregates_plants_and_dedupes_points(self):
        rows = [
            # 同一点位两种寄主
            {"code": "A001", "host_raw": "杨", "plants": 1, "locality": "宋庄镇"},
            {"code": "A001", "host_raw": "桑树", "plants": 2, "locality": "宋庄镇"},
            # 同一寄主在不同点位
            {"code": "A002", "host_raw": "桑", "plants": 3, "locality": "永顺镇"},
            {"code": "A003", "host_raw": "杨", "plants": 5, "locality": "永顺镇"},
        ]
        result = aggregate_host_summary(rows)

        hosts = {item["host"]: item for item in result["hosts"]}
        # 「桑树」归一为「桑」，点位按编号去重
        self.assertEqual(hosts["桑"]["points"], 2)
        self.assertEqual(hosts["桑"]["plants"], 5)
        self.assertEqual(hosts["杨"]["points"], 2)
        self.assertEqual(hosts["杨"]["plants"], 6)

        # 按受害株数降序
        self.assertEqual([item["host"] for item in result["hosts"]], ["杨", "桑"])

        totals = result["totals"]
        self.assertEqual(totals["host_species"], 2)
        self.assertEqual(totals["damaged_plants"], 11)
        self.assertEqual(totals["damaged_points"], 3)
        self.assertEqual(totals["top_host"]["host"], "杨")
        self.assertAlmostEqual(totals["top_host"]["share"], 6 / 11)

    def test_host_locality_matrix(self):
        rows = [
            {"code": "A001", "host_raw": "桑", "plants": 2, "locality": "宋庄镇"},
            {"code": "A002", "host_raw": "桑", "plants": 3, "locality": "宋庄镇"},
            {"code": "A003", "host_raw": "桑", "plants": 1, "locality": "永顺镇"},
        ]
        result = aggregate_host_summary(rows)
        localities = result["hosts"][0]["localities"]
        self.assertEqual(
            localities,
            [
                {"locality": "宋庄镇", "plants": 5},
                {"locality": "永顺镇", "plants": 1},
            ],
        )

    def test_skips_empty_host_and_bad_plants(self):
        rows = [
            {"code": "A001", "host_raw": "", "plants": 9, "locality": "宋庄镇"},
            {"code": "A001", "host_raw": "桑", "plants": "abc", "locality": "宋庄镇"},
            {"code": "A001", "host_raw": "桑", "plants": -3, "locality": "宋庄镇"},
        ]
        result = aggregate_host_summary(rows)
        self.assertEqual(result["totals"]["host_species"], 1)
        self.assertEqual(result["totals"]["damaged_plants"], 0)
        self.assertEqual(result["hosts"][0]["points"], 1)

    def test_top_limit_merges_rest_into_other(self):
        rows = []
        # 13 个树种：plants 从 13 递减到 1
        for index in range(13):
            rows.append(
                {
                    "code": f"A{index:03d}",
                    "host_raw": f"树种{13 - index}",
                    "plants": 13 - index,
                    "locality": "宋庄镇",
                }
            )
        result = aggregate_host_summary(rows, top_limit=12)

        self.assertEqual(len(result["hosts"]), 13)
        self.assertEqual(result["hosts"][-1]["host"], OTHER_HOST_NAME)
        self.assertEqual(result["hosts"][-1]["plants"], 1)
        self.assertEqual(result["hosts"][-1]["points"], 1)
        self.assertEqual(result["hosts"][-1]["merged_hosts"], 1)
        # 树种总数按归一化后实际种类计，不含「其他」
        self.assertEqual(result["totals"]["host_species"], 13)
        self.assertEqual(result["totals"]["damaged_plants"], 91)

    def test_other_merges_locality_matrix(self):
        rows = [
            {"code": "A001", "host_raw": "甲", "plants": 100, "locality": "宋庄镇"},
            {"code": "A002", "host_raw": "乙", "plants": 1, "locality": "宋庄镇"},
            {"code": "A003", "host_raw": "丙", "plants": 2, "locality": "宋庄镇"},
        ]
        result = aggregate_host_summary(rows, top_limit=1)
        other = result["hosts"][-1]
        self.assertEqual(other["host"], OTHER_HOST_NAME)
        self.assertEqual(other["plants"], 3)
        self.assertEqual(other["points"], 2)
        self.assertEqual(other["localities"], [{"locality": "宋庄镇", "plants": 3}])
        self.assertEqual(other["merged_hosts"], 2)


class TestAggregateHostSummaryByGeneration(unittest.TestCase):
    def test_groups_rows_by_generation(self):
        rows = [
            {"code": "A001", "host_raw": "桑", "plants": 2, "locality": "宋庄镇", "generation": "第一代"},
            {"code": "A001", "host_raw": "桑", "plants": 2, "locality": "宋庄镇", "generation": "第一代"},
            {"code": "A001", "host_raw": "杨", "plants": 5, "locality": "宋庄镇", "generation": "第二代"},
            {"code": "A002", "host_raw": "杨", "plants": 3, "locality": "宋庄镇", "generation": "第二代"},
        ]
        result = aggregate_host_summary_by_generation(rows)

        self.assertEqual([item["generation"] for item in result], ["第一代", "第二代"])
        first, second = result
        # 组内独立聚合、点位去重
        self.assertEqual(first["totals"]["damaged_plants"], 4)
        self.assertEqual(first["totals"]["damaged_points"], 1)
        self.assertEqual(second["totals"]["damaged_plants"], 8)
        self.assertEqual(second["totals"]["damaged_points"], 2)
        self.assertEqual(second["totals"]["top_host"]["host"], "杨")

    def test_fixed_generation_order_and_unknown_last(self):
        rows = [
            {"code": "A001", "host_raw": "桑", "plants": 1, "locality": "宋庄镇", "generation": "越冬代"},
            {"code": "A002", "host_raw": "桑", "plants": 1, "locality": "宋庄镇", "generation": "第二代"},
            {"code": "A003", "host_raw": "桑", "plants": 1, "locality": "宋庄镇", "generation": "第一代"},
        ]
        result = aggregate_host_summary_by_generation(rows)
        self.assertEqual(
            [item["generation"] for item in result],
            ["第一代", "第二代", "越冬代"],
        )

    def test_skips_empty_generation_and_empty_rows(self):
        self.assertEqual(aggregate_host_summary_by_generation([]), [])
        rows = [
            {"code": "A001", "host_raw": "桑", "plants": 1, "locality": "宋庄镇", "generation": ""},
        ]
        self.assertEqual(aggregate_host_summary_by_generation(rows), [])

    def test_single_generation_still_returns(self):
        rows = [
            {"code": "A001", "host_raw": "桑", "plants": 1, "locality": "宋庄镇", "generation": "第一代"},
        ]
        result = aggregate_host_summary_by_generation(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["generation"], "第一代")


if __name__ == "__main__":
    unittest.main()
