from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from backend.db.postgres import build_spring_inchworm_description, fetch_survey_candidates


class BuildSpringInchwormDescriptionTest(unittest.TestCase):
    def test_heavy_damage_includes_insect_count_and_urgent_advice(self) -> None:
        description = build_spring_inchworm_description(
            town_or_street="于家务乡",
            location_name="枣林村",
            location_id="YF0005",
            damage_level="重",
            total_insect_count=50,
        )

        self.assertEqual(
            description,
            "于家务乡枣林村YF0005点位，调查发现春尺蠖幼虫危害程度为重，总虫口数50头。"
            "建议立即组织防治作业，并优先复核周边相邻点位。",
        )

    def test_medium_damage_includes_insect_count_and_tracking_advice(self) -> None:
        description = build_spring_inchworm_description(
            town_or_street="永乐店镇",
            location_name="陈辛庄村",
            location_id="YL0033",
            damage_level="中",
            total_insect_count=28,
        )

        self.assertEqual(
            description,
            "永乐店镇陈辛庄村YL0033点位，调查发现春尺蠖幼虫危害程度为中，总虫口数28头。"
            "建议尽快安排防治，并持续跟踪虫情变化。",
        )

    def test_light_damage_includes_insect_count_and_monitoring_advice(self) -> None:
        description = build_spring_inchworm_description(
            town_or_street="于家务乡",
            location_name="枣林村",
            location_id="YF0005",
            damage_level="轻",
            total_insect_count=6,
        )

        self.assertEqual(
            description,
            "于家务乡枣林村YF0005点位，调查发现春尺蠖幼虫危害程度为轻，总虫口数6头。"
            "建议加强巡查，视虫情发展适时处置。",
        )

    def test_missing_insect_count_is_rendered_as_unrecorded(self) -> None:
        description = build_spring_inchworm_description(
            town_or_street="于家务乡",
            location_name="神仙村",
            location_id="YF0069",
            damage_level="重",
            total_insect_count=None,
        )

        self.assertEqual(
            description,
            "于家务乡神仙村YF0069点位，调查发现春尺蠖幼虫危害程度为重，总虫口数未记录。"
            "建议立即组织防治作业，并优先复核周边相邻点位。",
        )

    def test_empty_damage_level_uses_pending_judgement_and_fallback_advice(self) -> None:
        description = build_spring_inchworm_description(
            town_or_street="西集镇",
            location_name="林场一区",
            location_id="XJ0001",
            damage_level="",
            total_insect_count=12,
        )

        self.assertEqual(
            description,
            "西集镇林场一区XJ0001点位，调查发现春尺蠖幼虫危害程度为待判定，总虫口数12头。"
            "建议复核现场危害情况并及时补录调查结果。",
        )

    def test_unknown_damage_level_preserves_original_level_and_uses_generic_advice(self) -> None:
        description = build_spring_inchworm_description(
            town_or_street="",
            location_name="示范点",
            location_id="SF0008",
            damage_level="偏重",
            total_insect_count=33,
        )

        self.assertEqual(
            description,
            "示范点SF0008点位，调查发现春尺蠖幼虫危害程度为偏重，总虫口数33头。"
            "建议结合现场情况制定防治措施并复核虫情。",
        )


class FetchSurveyCandidatesTest(unittest.IsolatedAsyncioTestCase):
    async def test_note_is_preserved_but_not_merged_into_description(self) -> None:
        with patch(
            "backend.db.postgres.fetch",
            new=AsyncMock(
                return_value=[
                    {
                        "location_id": "YF0069",
                        "survey_date": "2026-04-01",
                        "total_insect_count": 50,
                        "damage_level": "重",
                        "note": "树冠北侧虫口集中",
                        "town_or_street": "于家务乡",
                        "location_name": "神仙村",
                    }
                ]
            ),
        ):
            candidates = await fetch_survey_candidates("2026-04-01")

        self.assertEqual(candidates[0]["note"], "树冠北侧虫口集中")
        self.assertEqual(
            candidates[0]["description"],
            "于家务乡神仙村YF0069点位，调查发现春尺蠖幼虫危害程度为重，总虫口数50头。"
            "建议立即组织防治作业，并优先复核周边相邻点位。",
        )
        self.assertNotIn("树冠北侧虫口集中", candidates[0]["description"])


if __name__ == "__main__":
    unittest.main()
