from __future__ import annotations

import io
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.schemas import WorkOrderGenerateRequest
from backend.services.docgen import (
    convert_docx_bytes_to_doc,
    generate_workorder_artifact,
    render_single_document,
)


def create_payload() -> WorkOrderGenerateRequest:
    return WorkOrderGenerateRequest(
        pest_type="春尺蠖",
        task_type="春尺蠖防治",
        task="2026春尺蠖防治",
        records=[
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
    )


class DocgenTest(unittest.TestCase):
    def test_convert_docx_bytes_to_doc_returns_doc_bytes_and_name(self) -> None:
        with self.subTest("libreoffice convert success"):
            with patch("backend.services.docgen.get_settings") as mocked_settings:
                settings = SimpleNamespace(
                    temp_dir=Path("/tmp/tzlb-tests"),
                    libreoffice_bin="/opt/homebrew/bin/soffice",
                    libreoffice_timeout_seconds=60,
                )
                mocked_settings.return_value = settings

                with patch("backend.services.docgen.tempfile.TemporaryDirectory") as mocked_tempdir:
                    mocked_tempdir.return_value.__enter__.return_value = "/tmp/tzlb-tests/export-job"
                    mocked_tempdir.return_value.__exit__.return_value = False

                    with patch("backend.services.docgen.subprocess.run") as mocked_run:
                        with (
                            patch("pathlib.Path.write_bytes", return_value=11),
                            patch("pathlib.Path.exists", return_value=True),
                            patch("pathlib.Path.read_bytes", return_value=b"doc-binary") as mocked_read,
                        ):
                            filename, content = convert_docx_bytes_to_doc(
                                "测试工作单.docx",
                                b"docx-binary",
                            )

        self.assertEqual(filename, "测试工作单.doc")
        self.assertEqual(content, b"doc-binary")
        mocked_run.assert_called_once()
        mocked_read.assert_called_once()

    def test_generate_workorder_artifact_returns_doc_by_default(self) -> None:
        payload = create_payload()

        with (
            patch("backend.services.docgen.get_template_path", return_value=Path("/tmp/template.docx")),
            patch(
                "backend.services.docgen.render_single_document",
                return_value=("测试工作单.docx", b"docx-binary"),
            ),
            patch(
                "backend.services.docgen.convert_docx_bytes_to_doc",
                return_value=("测试工作单.doc", b"doc-binary"),
            ) as mocked_convert,
        ):
            artifact = generate_workorder_artifact(payload)

        self.assertEqual(artifact.filename, "测试工作单.doc")
        self.assertEqual(artifact.media_type, "application/msword")
        self.assertEqual(artifact.content, b"doc-binary")
        mocked_convert.assert_called_once_with("测试工作单.docx", b"docx-binary")

    def test_generate_workorder_artifact_raises_clear_error_when_convert_fails(self) -> None:
        payload = create_payload()

        with (
            patch("backend.services.docgen.get_template_path", return_value=Path("/tmp/template.docx")),
            patch(
                "backend.services.docgen.render_single_document",
                return_value=("测试工作单.docx", b"docx-binary"),
            ),
            patch(
                "backend.services.docgen.convert_docx_bytes_to_doc",
                side_effect=RuntimeError("LibreOffice 转换失败：filter not found"),
            ),
        ):
            with self.assertRaises(RuntimeError) as context:
                generate_workorder_artifact(payload)

        self.assertEqual(str(context.exception), "LibreOffice 转换失败：filter not found")

    def test_render_single_document_renders_serial_number_from_template(self) -> None:
        payload = create_payload()
        filename, content = render_single_document(
            template_path=Path("templates/春尺蠖工作单模板.docx"),
            record=payload.records[0],
            pest_type=payload.pest_type,
            task_type=payload.task_type,
            task_name=payload.task,
            index=0,
            temp_images=[],
        )

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")

        self.assertEqual(
            filename,
            "2026林业有害生物防治工作单（于家务乡）-神仙村-2026-04-01-YF0069.docx",
        )
        self.assertIn("编号：2026-04-01-001", document_xml)
        self.assertNotIn("{{serial_number}}", document_xml)

    def test_render_single_document_uses_record_serial_number_when_present(self) -> None:
        payload = create_payload()
        payload.records[0].serial_number = 2

        _, content = render_single_document(
            template_path=Path("templates/春尺蠖工作单模板.docx"),
            record=payload.records[0],
            pest_type=payload.pest_type,
            task_type=payload.task_type,
            task_name=payload.task,
            index=0,
            temp_images=[],
        )

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")

        self.assertIn("编号：2026-04-01-002", document_xml)
        self.assertNotIn("编号：2026-04-01-001", document_xml)

    def test_render_single_document_renders_other_pest_template_fields(self) -> None:
        payload = WorkOrderGenerateRequest(
            pest_type="其他害虫",
            task_type="其他害虫防治",
            task="2026其他害虫防治",
            records=[
                {
                    "survey_date": "2026-04-17",
                    "town_or_street": "潞城镇",
                    "location_id": "QT0001",
                    "location_name": "畅和东路北京学校西侧",
                    "pest_name": "蚜虫",
                    "host_plant": "栾树",
                    "plot_type": "道路绿化",
                    "description": "潞城镇畅和东路，北京学校西侧，发现行道树栾树上蚜虫危害严重。",
                    "note": "",
                    "images": [],
                }
            ],
        )

        _, content = render_single_document(
            template_path=Path("templates/其他害虫工作单模板.docx"),
            record=payload.records[0],
            pest_type=payload.pest_type,
            task_type=payload.task_type,
            task_name=payload.task,
            index=0,
            temp_images=[],
        )

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")

        self.assertIn("蚜虫", document_xml)
        self.assertIn("栾树", document_xml)
        self.assertIn("道路绿化", document_xml)
        self.assertIn("潞城镇畅和东路，北京学校西侧，发现行道树栾树上蚜虫危害严重。", document_xml)


if __name__ == "__main__":
    unittest.main()
