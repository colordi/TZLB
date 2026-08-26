from __future__ import annotations

import base64
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from backend.db.postgres import (
    build_guo_huai_inchworm_description,
    build_spring_inchworm_description,
    fetch_survey_candidates,
)
from backend.db.survey_candidates import dispatch_event_types_for_pest


class BuildSpringInchwormDescriptionTest(unittest.TestCase):
    def test_heavy_damage_includes_insect_count_and_urgent_advice(self) -> None:
        description = build_spring_inchworm_description(
            locality="于家务乡",
            location_name="枣林村",
            location_id="YF0005",
            damage_level="重",
            total_insect_count=50,
        )

        self.assertEqual(
            description,
            "于家务乡枣林村YF0005点位，调查发现春尺蠖幼虫危害程度为重，平均每标准枝10头。"
            "建议立即组织防治作业，并优先复核周边相邻点位。",
        )

    def test_medium_damage_includes_insect_count_and_tracking_advice(self) -> None:
        description = build_spring_inchworm_description(
            locality="永乐店镇",
            location_name="陈辛庄村",
            location_id="YL0033",
            damage_level="中",
            total_insect_count=28,
        )

        self.assertEqual(
            description,
            "永乐店镇陈辛庄村YL0033点位，调查发现春尺蠖幼虫危害程度为中，平均每标准枝6头。"
            "建议尽快安排防治，并持续跟踪虫情变化。",
        )

    def test_light_damage_includes_insect_count_and_monitoring_advice(self) -> None:
        description = build_spring_inchworm_description(
            locality="于家务乡",
            location_name="枣林村",
            location_id="YF0005",
            damage_level="轻",
            total_insect_count=6,
        )

        self.assertEqual(
            description,
            "于家务乡枣林村YF0005点位，调查发现春尺蠖幼虫危害程度为轻，平均每标准枝2头。"
            "建议加强巡查，视虫情发展适时处置。",
        )

    def test_missing_insect_count_is_rendered_as_unrecorded(self) -> None:
        description = build_spring_inchworm_description(
            locality="于家务乡",
            location_name="神仙村",
            location_id="YF0069",
            damage_level="重",
            total_insect_count=None,
        )

        self.assertEqual(
            description,
            "于家务乡神仙村YF0069点位，调查发现春尺蠖幼虫危害程度为重，平均每标准枝未记录。"
            "建议立即组织防治作业，并优先复核周边相邻点位。",
        )

    def test_empty_damage_level_uses_pending_judgement_and_fallback_advice(self) -> None:
        description = build_spring_inchworm_description(
            locality="西集镇",
            location_name="林场一区",
            location_id="XJ0001",
            damage_level="",
            total_insect_count=12,
        )

        self.assertEqual(
            description,
            "西集镇林场一区XJ0001点位，调查发现春尺蠖幼虫危害程度为待判定，平均每标准枝3头。"
            "建议复核现场危害情况并及时补录调查结果。",
        )

    def test_unknown_damage_level_preserves_original_level_and_uses_generic_advice(self) -> None:
        description = build_spring_inchworm_description(
            locality="",
            location_name="示范点",
            location_id="SF0008",
            damage_level="偏重",
            total_insect_count=33,
        )

        self.assertEqual(
            description,
            "示范点SF0008点位，调查发现春尺蠖幼虫危害程度为偏重，平均每标准枝7头。"
            "建议结合现场情况制定防治措施并复核虫情。",
        )


class BuildGuoHuaiInchwormDescriptionTest(unittest.TestCase):
    def test_heavy_damage_uses_guo_huai_pest_name(self) -> None:
        description = build_guo_huai_inchworm_description(
            locality="宋庄镇",
            location_name="管头村",
            location_id="1001-1",
            damage_level="重",
            total_insect_count=45,
        )

        self.assertEqual(
            description,
            "宋庄镇管头村1001-1点位，调查发现国槐尺蠖幼虫危害程度为重，平均每标准枝9头。"
            "建议立即组织防治作业，并优先复核周边相邻点位。",
        )

    def test_missing_insect_count_is_rendered_as_unrecorded(self) -> None:
        description = build_guo_huai_inchworm_description(
            locality="潞城镇",
            location_name="卜落垡村",
            location_id="101-1",
            damage_level="轻",
            total_insect_count=None,
        )

        self.assertEqual(
            description,
            "潞城镇卜落垡村101-1点位，调查发现国槐尺蠖幼虫危害程度为轻，平均每标准枝未记录。"
            "建议加强巡查，视虫情发展适时处置。",
        )

    def test_unknown_damage_level_preserves_original_level(self) -> None:
        description = build_guo_huai_inchworm_description(
            locality="",
            location_name="示范点",
            location_id="GH0008",
            damage_level="偏重",
            total_insect_count=31,
        )

        self.assertEqual(
            description,
            "示范点GH0008点位，调查发现国槐尺蠖幼虫危害程度为偏重，平均每标准枝7头。"
            "建议结合现场情况制定防治措施并复核虫情。",
        )


class FetchSurveyCandidatesTest(unittest.IsolatedAsyncioTestCase):
    async def test_matching_point_screenshot_is_encoded_as_first_image(self) -> None:
        image_bytes = b"fake-jpeg-bytes"

        with TemporaryDirectory() as tempdir:
            image_path = Path(tempdir) / "YF0069.jpg"
            image_path.write_bytes(image_bytes)

            with (
                patch(
                    "backend.db.survey_candidates.fetch",
                    new=AsyncMock(
                        return_value=[
                            {
                                "location_id": "YF0069",
                                "survey_date": "2026-04-01",
                                "event_type": "幼虫调查下派",
                                "event_detail": "",
                                "total_insect_count": 50,
                                "damage_level": "重",
                                "note": "树冠北侧虫口集中",
                                "locality": "于家务乡",
                                "location_name": "神仙村",
                            }
                        ]
                    ),
                ),
                patch(
                    "backend.db.survey_candidates.get_settings",
                    return_value=SimpleNamespace(point_screenshot_dir=Path(tempdir)),
                ),
            ):
                candidates = await fetch_survey_candidates("2026-04-01")

        expected_image = (
            "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
        )
        self.assertEqual(candidates[0]["images"], [expected_image])

    async def test_guo_huai_matching_point_screenshot_is_encoded_as_first_image(
        self,
    ) -> None:
        image_bytes = b"fake-guo-huai-jpeg-bytes"

        with TemporaryDirectory() as tempdir:
            image_path = Path(tempdir) / "1001-1.jpg"
            image_path.write_bytes(image_bytes)

            with (
                patch(
                    "backend.db.survey_candidates.fetch",
                    new=AsyncMock(
                        return_value=[
                            {
                                "location_id": "1001-1",
                                "survey_date": "2026-05-02",
                                "event_type": "幼虫调查下派",
                                "event_detail": "",
                                "total_insect_count": 45,
                                "damage_level": "重",
                                "note": "树冠中上部虫口集中",
                                "locality": "宋庄镇",
                                "location_name": "管头村",
                            }
                        ]
                    ),
                ),
                patch(
                    "backend.db.survey_candidates.get_settings",
                    return_value=SimpleNamespace(
                        sophora_point_screenshot_dir=Path(tempdir)
                    ),
                ),
            ):
                candidates = await fetch_survey_candidates(
                    "2026-05-02",
                    pest_type="国槐尺蠖",
                )

        expected_image = (
            "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
        )
        self.assertEqual(candidates[0]["images"], [expected_image])

    async def test_note_is_preserved_but_not_merged_into_description(self) -> None:
        mocked_fetch = AsyncMock(
            return_value=[
                {
                    "location_id": "YF0069",
                    "survey_date": "2026-04-01",
                    "event_type": "幼虫调查下派",
                    "event_detail": "",
                    "total_insect_count": 50,
                    "damage_level": "重",
                    "note": "树冠北侧虫口集中",
                    "locality": "于家务乡",
                    "location_name": "神仙村",
                }
            ]
        )

        with TemporaryDirectory() as tempdir, patch(
            "backend.db.survey_candidates.fetch",
            new=mocked_fetch,
        ), patch(
            "backend.db.survey_candidates.get_settings",
            return_value=SimpleNamespace(point_screenshot_dir=Path(tempdir)),
        ):
            candidates = await fetch_survey_candidates("2026-04-01")

        self.assertEqual(candidates[0]["note"], "树冠北侧虫口集中")
        self.assertEqual(candidates[0]["event_type"], "幼虫调查下派")
        self.assertEqual(candidates[0]["images"], [])
        self.assertEqual(
            candidates[0]["description"],
            "于家务乡神仙村YF0069点位，幼虫调查下派，危害程度为重，平均虫口50头。",
        )
        self.assertNotIn("树冠北侧虫口集中", candidates[0]["description"])

        query = mocked_fetch.call_args.args[0]
        self.assertIn('ledger"."春尺蠖问题点位事件流水表', query)
        self.assertIn('(e."事件时间")::date = $1', query)
        self.assertIn('e."年份" = $3', query)
        self.assertNotIn("survey.", query)
        args = mocked_fetch.call_args.args
        self.assertIn("幼虫调查下派", args[2])
        self.assertIn("成虫调查下派", args[2])
        self.assertIn("历史预警下派", args[2])
        self.assertIn("复查异常", args[2])
        self.assertEqual(args[3], 2026)

    async def test_other_pest_candidates_include_template_required_fields(self) -> None:
        mocked_fetch = AsyncMock(
            return_value=[
                {
                    "event_id": 11,
                    "location_id": "QT0001",
                    "survey_date": "2026-04-17",
                    "event_type": "调查下派",
                    "pest_name": "蚜虫",
                    "survey_result": "发现问题",
                    "description": "潞城镇畅和东路，北京学校西侧，发现行道树栾树上蚜虫危害严重。",
                    "note": "",
                    "locality": "潞城镇",
                    "location_name": "畅和东路北京学校西侧",
                    "host_plant": "栾树",
                    "plot_type": "道路绿化",
                }
            ]
        )

        with TemporaryDirectory() as tempdir, patch(
            "backend.db.survey_candidates.fetch",
            new=mocked_fetch,
        ), patch(
            "backend.db.survey_candidates.get_settings",
            return_value=SimpleNamespace(other_pest_point_screenshot_dir=Path(tempdir)),
        ):
            candidates = await fetch_survey_candidates("2026-04-17", pest_type="其他害虫")

        self.assertEqual(
            candidates,
            [
                {
                    "id": 11,
                    "survey_date": "2026-04-17",
                    "event_type": "调查下派",
                    "locality": "潞城镇",
                    "location_id": "QT0001",
                    "location_name": "畅和东路北京学校西侧",
                    "pest_name": "蚜虫",
                    "host_plant": "栾树",
                    "plot_type": "道路绿化",
                    "survey_result": "发现问题",
                    "description": "潞城镇畅和东路，北京学校西侧，发现行道树栾树上蚜虫危害严重。",
                    "note": "",
                    "images": [],
                }
            ],
        )

        query = mocked_fetch.call_args.args[0]
        self.assertIn('ledger"."其他害虫问题点位事件流水表', query)
        self.assertIn('LEFT JOIN "sites"."其他害虫点位基础表"', query)
        self.assertIn('e."年份" = $3', query)
        self.assertNotIn("发现问题", query)
        self.assertIn("复查异常", mocked_fetch.call_args.args[2])
        self.assertIn("调查下派", mocked_fetch.call_args.args[2])

    async def test_guo_huai_candidates_include_template_required_fields(self) -> None:
        mocked_fetch = AsyncMock(
            return_value=[
                {
                    "event_id": 7,
                    "location_id": "1001-1",
                    "survey_date": "2026-05-02",
                    "event_type": "幼虫调查下派",
                    "event_detail": "",
                    "total_insect_count": 45,
                    "damage_level": "重",
                    "note": "树冠中上部虫口集中",
                    "locality": "宋庄镇",
                    "location_name": "管头村",
                }
            ]
        )

        with TemporaryDirectory() as tempdir, patch(
            "backend.db.survey_candidates.fetch",
            new=mocked_fetch,
        ), patch(
            "backend.db.survey_candidates.get_settings",
            return_value=SimpleNamespace(sophora_point_screenshot_dir=Path(tempdir)),
        ):
            candidates = await fetch_survey_candidates(
                "2026-05-02",
                pest_type="国槐尺蠖",
            )

        self.assertEqual(
            candidates,
            [
                {
                    "id": 7,
                    "survey_date": "2026-05-02",
                    "event_type": "幼虫调查下派",
                    "locality": "宋庄镇",
                    "location_id": "1001-1",
                    "location_name": "管头村",
                    "total_insect_count": 45,
                    "damage_level": "重",
                    "note": "树冠中上部虫口集中",
                    "images": [],
                    "description": "宋庄镇管头村1001-1点位，幼虫调查下派，危害程度为重，平均虫口45头。",
                }
            ],
        )

        query = mocked_fetch.call_args.args[0]
        self.assertIn('ledger"."国槐尺蠖问题点位事件流水表', query)
        self.assertIn('e."年份" = $3', query)
        self.assertNotIn("survey.", query)
        self.assertNotIn("无需防治", query)
        args = mocked_fetch.call_args.args
        self.assertIn("幼虫调查下派", args[2])
        self.assertIn("历史预警下派", args[2])
        self.assertIn("复查异常", args[2])
        self.assertNotIn("成虫调查下派", args[2])
        self.assertEqual(args[3], 2026)

    async def test_meiguobaie_candidates_include_template_required_fields(self) -> None:
        image_bytes = b"fake-meiguobaie-jpeg-bytes"
        mocked_fetch = AsyncMock(
            return_value=[
                {
                    "event_id": 23,
                    "location_id": "MQ001",
                    "survey_date": "2026-05-26",
                    "event_type": "调查下派",
                    "region": "城区",
                    "locality": "梨园镇",
                    "location_name": "玉桥东路",
                    "occurrence_position": "道路东侧",
                    "green_space_type": "道路绿化",
                    "pest_hosts": "白蜡",
                    "damaged_plant_count": 3,
                    "web_nest_count": 5,
                    "description": "发现美国白蛾网幕，已安排剪网处置。",
                    "note": "需复查",
                }
            ]
        )

        with TemporaryDirectory() as tempdir:
            image_path = Path(tempdir) / "MQ001.jpg"
            image_path.write_bytes(image_bytes)

            with patch(
                "backend.db.survey_candidates.fetch",
                new=mocked_fetch,
            ), patch(
                "backend.db.survey_candidates.get_settings",
                return_value=SimpleNamespace(meiguobaie_point_screenshot_dir=Path(tempdir)),
            ):
                candidates = await fetch_survey_candidates(
                    "2026-05-26",
                    pest_type="美国白蛾",
                )

        expected_image = (
            "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
        )
        self.assertEqual(
            candidates,
            [
                {
                    "id": 23,
                    "survey_date": "2026-05-26",
                    "event_type": "调查下派",
                    "region": "城区",
                    "locality": "梨园镇",
                    "location_id": "MQ001",
                    "location_name": "玉桥东路",
                    "occurrence_position": "道路东侧",
                    "green_space_type": "道路绿化",
                    "pest_hosts": "白蜡",
                    "damaged_plant_count": 3,
                    "web_nest_count": 5,
                    "description": "发现美国白蛾网幕，已安排剪网处置。",
                    "note": "需复查",
                    "images": [expected_image],
                }
            ],
        )

        query = mocked_fetch.call_args.args[0]
        self.assertIn('ledger"."美国白蛾问题点位事件流水表', query)
        self.assertIn('e."年份" = $3', query)
        self.assertIn('e."本次详细情况"', query)
        self.assertNotIn("survey.", query)
        self.assertNotIn("详细描述", query)
        args = mocked_fetch.call_args.args
        self.assertIn("调查下派", args[2])
        self.assertIn("复查异常", args[2])
        self.assertEqual(args[3], 2026)

    async def test_ledger_event_detail_is_used_as_description(self) -> None:
        mocked_fetch = AsyncMock(
            return_value=[
                {
                    "location_id": "YF0069",
                    "survey_date": "2026-04-01",
                    "event_type": "复查异常",
                    "event_detail": "复查仍见大量幼虫，需再次下派防治。",
                    "total_insect_count": 40,
                    "damage_level": "重",
                    "note": "",
                    "locality": "于家务乡",
                    "location_name": "神仙村",
                }
            ]
        )

        with TemporaryDirectory() as tempdir, patch(
            "backend.db.survey_candidates.fetch",
            new=mocked_fetch,
        ), patch(
            "backend.db.survey_candidates.get_settings",
            return_value=SimpleNamespace(point_screenshot_dir=Path(tempdir)),
        ):
            candidates = await fetch_survey_candidates("2026-04-01", year=2026)

        self.assertEqual(
            candidates[0]["description"],
            "复查仍见大量幼虫，需再次下派防治。",
        )
        self.assertEqual(candidates[0]["event_type"], "复查异常")

    async def test_guo_huai_filters_generation_when_provided(self) -> None:
        mocked_fetch = AsyncMock(return_value=[])

        with TemporaryDirectory() as tempdir, patch(
            "backend.db.survey_candidates.fetch",
            new=mocked_fetch,
        ), patch(
            "backend.db.survey_candidates.get_settings",
            return_value=SimpleNamespace(sophora_point_screenshot_dir=Path(tempdir)),
        ):
            await fetch_survey_candidates(
                "2026-05-02",
                pest_type="国槐尺蠖",
                year=2026,
                generation="第二代",
            )

        query = mocked_fetch.call_args.args[0]
        self.assertIn('e."世代" = $4', query)
        self.assertEqual(mocked_fetch.call_args.args[4], "第二代")

    def test_dispatch_event_types_are_symmetric_for_chi_huo_except_adult(self) -> None:
        spring_types = set(dispatch_event_types_for_pest("春尺蠖"))
        guo_huai_types = set(dispatch_event_types_for_pest("国槐尺蠖"))
        self.assertEqual(
            spring_types - {"成虫调查下派"},
            guo_huai_types,
        )
        self.assertIn("复查异常", spring_types)
        self.assertIn("复查异常", set(dispatch_event_types_for_pest("美国白蛾")))
        self.assertEqual(
            set(dispatch_event_types_for_pest("其他害虫")),
            set(dispatch_event_types_for_pest("杨树食叶害虫")),
        )


if __name__ == "__main__":
    unittest.main()
