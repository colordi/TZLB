from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.routers.workorder import generate_workorder
from backend.schemas import WorkOrderGenerateRequest
from backend.services.docgen import GeneratedArtifact


def create_payload(records: list[dict] | None = None) -> dict:
    return {
        "pest_type": "春尺蠖",
        "task_type": "春尺蠖防治",
        "task": "2026春尺蠖防治",
        "records": records
        or [
            {
                "survey_date": "2026-04-01",
                "town_or_street": "于家务乡",
                "location_id": "YF0069",
                "location_name": "神仙村",
                "description": "点位描述",
                "note": "",
                "images": [],
            }
        ],
    }


class WorkorderRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_generate_single_record_returns_doc_response(self) -> None:
        with patch(
            "backend.routers.workorder.generate_workorder_artifact",
            return_value=GeneratedArtifact(
                filename="测试工作单.doc",
                media_type="application/msword",
                content=b"doc-bytes",
            ),
        ):
            response = await generate_workorder(WorkOrderGenerateRequest(**create_payload()))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, b"doc-bytes")
        self.assertIn("application/msword", response.headers["content-type"])
        self.assertIn("attachment;", response.headers["content-disposition"])
        self.assertIn(
            "%E6%B5%8B%E8%AF%95%E5%B7%A5%E4%BD%9C%E5%8D%95.doc",
            response.headers["content-disposition"],
        )

    async def test_generate_multiple_records_returns_400(self) -> None:
        payload = WorkOrderGenerateRequest(
            **create_payload(
                records=[
                    {
                        "survey_date": "2026-04-01",
                        "town_or_street": "于家务乡",
                        "location_id": "YF0069",
                        "location_name": "神仙村",
                        "description": "点位描述",
                        "note": "",
                        "images": [],
                    },
                    {
                        "survey_date": "2026-04-01",
                        "town_or_street": "于家务乡",
                        "location_id": "YF0070",
                        "location_name": "中心林地",
                        "description": "第二条点位描述",
                        "note": "",
                        "images": [],
                    },
                ]
        )
        )

        with patch(
            "backend.routers.workorder.generate_workorder_artifact",
            return_value=GeneratedArtifact(
                filename="不应被调用.docx",
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                content=b"unused",
            ),
        ) as mocked_generate:
            with self.assertRaises(HTTPException) as context:
                await generate_workorder(payload)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(
            context.exception.detail,
            "批量压缩导出已取消，请改为逐条导出工作单。",
        )
        mocked_generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
