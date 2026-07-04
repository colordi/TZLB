from __future__ import annotations

import unittest
from unittest.mock import patch

from pydantic import ValidationError

from backend.exceptions import BusinessError
from backend.routers.workorder import generate_workorder, generate_workorder_batch
from backend.schemas import WorkOrderBatchGenerateRequest, WorkOrderGenerateRequest
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
                "locality": "于家务乡",
                "location_id": "YF0069",
                "location_name": "神仙村",
                "description": "点位描述",
                "note": "",
                "images": [],
            }
        ],
    }


class WorkorderRouterTest(unittest.IsolatedAsyncioTestCase):
    def test_payload_rejects_unknown_pest_type(self) -> None:
        payload = create_payload()
        payload["pest_type"] = "未知害虫"

        with self.assertRaises(ValidationError) as context:
            WorkOrderGenerateRequest(**payload)

        self.assertIn("不支持的害虫类型：未知害虫", str(context.exception))

    def test_payload_rejects_task_type_not_registered_for_pest(self) -> None:
        payload = create_payload()
        payload["task_type"] = "其他害虫防治"

        with self.assertRaises(ValidationError) as context:
            WorkOrderGenerateRequest(**payload)

        self.assertIn("春尺蠖 不支持统防统治类型：其他害虫防治", str(context.exception))

    def test_payload_accepts_valid_survey_date(self) -> None:
        payload = create_payload()
        request = WorkOrderGenerateRequest(**payload)
        self.assertEqual(request.records[0].survey_date, "2026-04-01")

    def test_payload_rejects_invalid_survey_date(self) -> None:
        payload = create_payload()
        payload["records"][0]["survey_date"] = "2026-02-30"

        with self.assertRaises(ValidationError) as context:
            WorkOrderGenerateRequest(**payload)

        self.assertIn("调查日期必须是 YYYY-MM-DD 格式", str(context.exception))

    def test_payload_rejects_empty_survey_date(self) -> None:
        payload = create_payload()
        payload["records"][0]["survey_date"] = ""

        with self.assertRaises(ValidationError) as context:
            WorkOrderGenerateRequest(**payload)

        self.assertIn("调查日期不能为空", str(context.exception))

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
                        "locality": "于家务乡",
                        "location_id": "YF0069",
                        "location_name": "神仙村",
                        "description": "点位描述",
                        "note": "",
                        "images": [],
                    },
                    {
                        "survey_date": "2026-04-01",
                        "locality": "于家务乡",
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
            with self.assertRaises(BusinessError) as context:
                await generate_workorder(payload)

        self.assertEqual(
            str(context.exception),
            "批量压缩导出已取消，请改为逐条导出工作单。",
        )
        mocked_generate.assert_not_called()

    async def test_generate_batch_returns_zip_response(self) -> None:
        payload = WorkOrderBatchGenerateRequest(
            **create_payload(
                records=[
                    {
                        "survey_date": "2026-04-01",
                        "locality": "于家务乡",
                        "location_id": "YF0069",
                        "location_name": "神仙村",
                        "description": "点位描述",
                        "note": "",
                        "images": [],
                    },
                    {
                        "survey_date": "2026-04-02",
                        "locality": "于家务乡",
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
            "backend.routers.workorder.generate_workorder_batch_artifact",
            return_value=GeneratedArtifact(
                filename="批量导出_2份.zip",
                media_type="application/zip",
                content=b"zip-bytes",
            ),
        ) as mocked_batch:
            response = await generate_workorder_batch(payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, b"zip-bytes")
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertIn("attachment;", response.headers["content-disposition"])
        self.assertIn("%E6%89%B9%E9%87%8F%E5%AF%BC%E5%87%BA_2%E4%BB%BD.zip", response.headers["content-disposition"])
        mocked_batch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
