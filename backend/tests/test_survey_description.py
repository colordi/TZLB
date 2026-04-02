from __future__ import annotations

import unittest

from backend.db.postgres import build_spring_inchworm_description


class BuildSpringInchwormDescriptionTest(unittest.TestCase):
    def test_heavy_damage_uses_location_prefix_without_insect_count(self) -> None:
        description = build_spring_inchworm_description(
            town_or_street="于家务乡",
            location_name="枣林村",
            location_id="YF0005",
            damage_level="重",
        )

        self.assertEqual(
            description,
            "于家务乡枣林村YF0005点位，该点位春尺蠖幼虫危害程度为重，需及时开展防治作业。",
        )

    def test_medium_damage_uses_expected_template(self) -> None:
        description = build_spring_inchworm_description(
            town_or_street="永乐店镇",
            location_name="陈辛庄村",
            location_id="YL0033",
            damage_level="中",
        )

        self.assertEqual(
            description,
            "永乐店镇陈辛庄村YL0033点位，该点位春尺蠖幼虫危害程度为中，建议尽快安排防治。",
        )

    def test_light_damage_uses_expected_template(self) -> None:
        description = build_spring_inchworm_description(
            town_or_street="于家务乡",
            location_name="枣林村",
            location_id="YF0005",
            damage_level="轻",
        )

        self.assertEqual(
            description,
            "于家务乡枣林村YF0005点位，该点位春尺蠖幼虫危害程度为轻，需持续关注并适时防治。",
        )


if __name__ == "__main__":
    unittest.main()
