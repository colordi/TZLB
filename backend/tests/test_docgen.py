from __future__ import annotations

import base64
import io
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from backend.schemas import WorkOrderGenerateRequest
from backend.services.docgen import (
    convert_docx_bytes_to_doc,
    find_dated_location_images,
    generate_workorder_artifact,
    generate_workorder_batch_artifact,
    get_template_path,
    render_single_document,
    resolve_meiguobaie_image_paths,
    sanitize_existing_image_paths,
    save_base64_images,
)


def create_payload() -> WorkOrderGenerateRequest:
    return WorkOrderGenerateRequest(
        pest_type="春尺蠖",
        task_type="春尺蠖防治",
        task="2026春尺蠖防治",
        records=[
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
    )


def create_image_bytes(image_format: str = "PNG", size: tuple[int, int] = (8, 8)) -> bytes:
    buffer = io.BytesIO()
    mode = "RGBA" if image_format.upper() in {"PNG", "WEBP"} else "RGB"
    color = (255, 0, 0, 128) if mode == "RGBA" else (255, 0, 0)
    Image.new(mode, size, color).save(buffer, format=image_format)
    return buffer.getvalue()


def build_image_settings(temp_dir: Path, **overrides):
    payload = {
        "temp_dir": temp_dir,
        "workorder_image_max_bytes": 8 * 1024 * 1024,
        "workorder_image_max_total_bytes": 24 * 1024 * 1024,
        "workorder_image_max_dimension": 1600,
        "workorder_default_output_format": "doc",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class DocgenTest(unittest.TestCase):
    def test_convert_docx_bytes_to_doc_returns_doc_bytes_and_name(self) -> None:
        with self.subTest("libreoffice convert success"):
            with patch("backend.services.docgen.convert.get_settings") as mocked_settings:
                settings = SimpleNamespace(
                    temp_dir=Path("/tmp/tzlb-tests"),
                    libreoffice_bin="/opt/homebrew/bin/soffice",
                    libreoffice_timeout_seconds=60,
                )
                mocked_settings.return_value = settings

                with patch("backend.services.docgen.convert.tempfile.TemporaryDirectory") as mocked_tempdir:
                    mocked_tempdir.return_value.__enter__.return_value = "/tmp/tzlb-tests/export-job"
                    mocked_tempdir.return_value.__exit__.return_value = False

                    with patch("backend.services.docgen.convert.subprocess.run") as mocked_run:
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

    def test_all_pest_types_use_single_workorder_template(self) -> None:
        expected_name = "林业有害生物防治工作单模板.docx"

        for pest_type in ("春尺蠖", "国槐尺蠖", "美国白蛾", "其他害虫"):
            with self.subTest(pest_type=pest_type):
                self.assertEqual(get_template_path(pest_type).name, expected_name)

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

    def test_generate_workorder_artifact_returns_docx_when_requested(self) -> None:
        payload = create_payload()
        payload.output_format = "docx"

        with (
            patch("backend.services.docgen.get_template_path", return_value=Path("/tmp/template.docx")),
            patch(
                "backend.services.docgen.render_single_document",
                return_value=("测试工作单.docx", b"docx-binary"),
            ),
            patch("backend.services.docgen.convert_docx_bytes_to_doc") as mocked_convert,
        ):
            artifact = generate_workorder_artifact(payload)

        self.assertEqual(artifact.filename, "测试工作单.docx")
        self.assertEqual(
            artifact.media_type,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertEqual(artifact.content, b"docx-binary")
        mocked_convert.assert_not_called()

    def test_save_base64_images_rejects_disguised_image_payload(self) -> None:
        with TemporaryDirectory() as tempdir:
            with patch(
                "backend.services.docgen.images.get_settings",
                return_value=build_image_settings(Path(tempdir)),
            ):
                with self.assertRaises(ValueError) as context:
                    save_base64_images(
                        [
                            "data:image/jpeg;base64,"
                            + base64.b64encode(b"not-an-image").decode("ascii")
                        ],
                        "row_1",
                    )

        self.assertIn("不是有效图片", str(context.exception))

    def test_save_base64_images_rejects_unsupported_real_format(self) -> None:
        gif_bytes = create_image_bytes("GIF")

        with TemporaryDirectory() as tempdir:
            with patch(
                "backend.services.docgen.images.get_settings",
                return_value=build_image_settings(Path(tempdir)),
            ):
                with self.assertRaises(ValueError) as context:
                    save_base64_images(
                        [
                            "data:image/gif;base64,"
                            + base64.b64encode(gif_bytes).decode("ascii")
                        ],
                        "row_1",
                    )

        self.assertIn("格式不支持", str(context.exception))

    def test_save_base64_images_rejects_oversized_image_before_decode(self) -> None:
        with TemporaryDirectory() as tempdir:
            with patch(
                "backend.services.docgen.images.get_settings",
                return_value=build_image_settings(Path(tempdir), workorder_image_max_bytes=4),
            ):
                with self.assertRaises(ValueError) as context:
                    save_base64_images(
                        [
                            "data:image/png;base64,"
                            + base64.b64encode(create_image_bytes("PNG")).decode("ascii")
                        ],
                        "row_1",
                    )

        self.assertIn("超过单图大小限制", str(context.exception))

    def test_save_base64_images_normalizes_supported_image_to_jpeg(self) -> None:
        png_bytes = create_image_bytes("PNG")

        with TemporaryDirectory() as tempdir:
            with patch(
                "backend.services.docgen.images.get_settings",
                return_value=build_image_settings(Path(tempdir)),
            ):
                paths = save_base64_images(
                    [
                        "data:image/png;base64,"
                        + base64.b64encode(png_bytes).decode("ascii")
                    ],
                    "row_1",
                )
                with Image.open(paths[0]) as image:
                    image_format = image.format
                    mode = image.mode

        self.assertEqual(image_format, "JPEG")
        self.assertEqual(mode, "RGB")

    def test_sanitize_existing_image_paths_normalizes_disk_images(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source_path = root / "MQ001.png"
            source_path.write_bytes(create_image_bytes("PNG"))

            with patch(
                "backend.services.docgen.images.get_settings",
                return_value=build_image_settings(root / "tmp"),
            ):
                paths = sanitize_existing_image_paths([source_path], "row_1")
                with Image.open(paths[0]) as image:
                    image_format = image.format

        self.assertEqual(image_format, "JPEG")

    def test_render_single_document_renders_serial_number_from_template(self) -> None:
        payload = create_payload()
        filename, content = render_single_document(
            template_path=Path("templates/林业有害生物防治工作单模板.docx"),
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
        self.assertIn("春尺蠖", document_xml)
        self.assertIn("杨树", document_xml)
        self.assertIn("8米上", document_xml)
        self.assertNotIn("{{serial_number}}", document_xml)

    def test_render_single_document_uses_record_serial_number_when_present(self) -> None:
        payload = create_payload()
        payload.records[0].serial_number = 2

        _, content = render_single_document(
            template_path=Path("templates/林业有害生物防治工作单模板.docx"),
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
                    "locality": "潞城镇",
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
            template_path=Path("templates/林业有害生物防治工作单模板.docx"),
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

    def test_render_single_document_renders_meiguobaie_template_fields(self) -> None:
        payload = WorkOrderGenerateRequest(
            pest_type="美国白蛾",
            task_type="美国白蛾防治",
            task="2026美国白蛾第一代防治",
            generation="第一代",
            records=[
                {
                    "survey_date": "2026-05-26",
                    "locality": "梨园镇",
                    "location_id": "MQ001",
                    "location_name": "玉桥东路",
                    "green_space_type": "道路绿化",
                    "pest_hosts": "白蜡",
                    "damaged_plant_count": 3,
                    "web_nest_count": 5,
                    "description": "发现美国白蛾网幕，已安排剪网处置。",
                    "note": "需复查",
                    "images": [],
                }
            ],
        )

        _, content = render_single_document(
            template_path=Path("templates/林业有害生物防治工作单模板.docx"),
            record=payload.records[0],
            pest_type=payload.pest_type,
            task_type=payload.task_type,
            task_name=payload.task,
            index=0,
            temp_images=[],
        )

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")

        self.assertIn("白蜡", document_xml)
        self.assertIn("道路绿化", document_xml)
        self.assertIn("3", document_xml)
        self.assertIn("5", document_xml)
        self.assertIn("发现美国白蛾网幕，已安排剪网处置。", document_xml)

    def test_resolve_meiguobaie_images_prefers_point_then_dated_images(self) -> None:
        payload = WorkOrderGenerateRequest(
            pest_type="美国白蛾",
            task_type="美国白蛾防治",
            task="2026美国白蛾第一代防治",
            generation="第一代",
            records=[
                {
                    "survey_date": "2026-05-26",
                    "locality": "梨园镇",
                    "location_id": "MQ001",
                    "location_name": "玉桥东路",
                    "green_space_type": "道路绿化",
                    "pest_hosts": "白蜡",
                    "damaged_plant_count": 3,
                    "web_nest_count": 5,
                    "description": "发现美国白蛾网幕，已安排剪网处置。",
                    "note": "",
                    "images": ["data:image/jpeg;base64,ignored"],
                }
            ],
        )

        with TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            points_dir = root / "points"
            dated_images_dir = root / "images" / "2026-05-26"
            points_dir.mkdir()
            dated_images_dir.mkdir(parents=True)

            for path in [
                points_dir / "MQ001.jpg",
                dated_images_dir / "MQ001-3.jpg",
                dated_images_dir / "MQ001现场.jpg",
                dated_images_dir / "MQ001-1.jpg",
                dated_images_dir / "MQ001_2.jpg",
                dated_images_dir / "MQ001-2.jpg",
                dated_images_dir / "MQ001-4.jpg",
                dated_images_dir / "MQ002-1.jpg",
                dated_images_dir / "AMQ001-1.jpg",
                dated_images_dir / "MQ001-说明.txt",
            ]:
                path.write_bytes(b"fake-image")

            with patch(
                "backend.services.docgen.images.get_settings",
                return_value=SimpleNamespace(
                    meiguobaie_point_screenshot_dir=points_dir,
                    images_dir=root / "images",
                ),
            ):
                image_paths = resolve_meiguobaie_image_paths(payload.records[0])
                dated_image_names = [
                    path.name
                    for path in find_dated_location_images(
                        root / "images",
                        "2026-05-26",
                        "MQ001",
                    )
                ]

        self.assertEqual(
            [path.name for path in image_paths],
            ["MQ001.jpg", "MQ001-1.jpg", "MQ001-2.jpg", "MQ001-3.jpg"],
        )
        self.assertIn("MQ001现场.jpg", dated_image_names)
        self.assertIn("MQ001_2.jpg", dated_image_names)
        self.assertNotIn("AMQ001-1.jpg", dated_image_names)

    def test_generate_workorder_batch_artifact_packs_successful_records(self) -> None:
        payload = WorkOrderGenerateRequest(
            pest_type="春尺蠖",
            task_type="春尺蠖防治",
            task="2026春尺蠖防治",
            records=[
                {
                    "survey_date": "2026-04-01",
                    "locality": "于家务乡",
                    "location_id": "YF0069",
                    "location_name": "神仙村",
                    "description": "点位描述1",
                    "note": "",
                    "images": [],
                },
                {
                    "survey_date": "2026-04-02",
                    "locality": "于家务乡",
                    "location_id": "YF0070",
                    "location_name": "中心林地",
                    "description": "点位描述2",
                    "note": "",
                    "images": [],
                },
            ],
        )

        with (
            patch("backend.services.docgen.get_template_path", return_value=Path("/tmp/template.docx")),
            patch(
                "backend.services.docgen.render_single_document",
                side_effect=[
                    ("工作单1.docx", b"docx-1"),
                    ("工作单2.docx", b"docx-2"),
                ],
            ),
            patch(
                "backend.services.docgen.convert_docx_bytes_to_doc",
                side_effect=[
                    ("工作单1.doc", b"doc-1"),
                    ("工作单2.doc", b"doc-2"),
                ],
            ) as mocked_convert,
        ):
            artifact = generate_workorder_batch_artifact(payload)

        self.assertEqual(artifact.media_type, "application/zip")
        self.assertTrue(artifact.filename.endswith("_2份.zip"))
        self.assertEqual(mocked_convert.call_count, 2)

        with zipfile.ZipFile(io.BytesIO(artifact.content)) as archive:
            names = archive.namelist()
            self.assertIn("工作单/工作单1.doc", names)
            self.assertIn("工作单/工作单2.doc", names)
            self.assertNotIn("失败记录.json", names)
            self.assertEqual(archive.read("工作单/工作单1.doc"), b"doc-1")
            self.assertEqual(archive.read("工作单/工作单2.doc"), b"doc-2")

    def test_generate_workorder_batch_artifact_includes_failure_report(self) -> None:
        payload = WorkOrderGenerateRequest(
            pest_type="春尺蠖",
            task_type="春尺蠖防治",
            task="2026春尺蠖防治",
            records=[
                {
                    "survey_date": "2026-04-01",
                    "locality": "于家务乡",
                    "location_id": "YF0069",
                    "location_name": "神仙村",
                    "description": "点位描述1",
                    "note": "",
                    "images": [],
                },
                {
                    "survey_date": "2026-04-02",
                    "locality": "于家务乡",
                    "location_id": "YF0070",
                    "location_name": "中心林地",
                    "description": "点位描述2",
                    "note": "",
                    "images": [],
                },
            ],
        )

        with (
            patch("backend.services.docgen.get_template_path", return_value=Path("/tmp/template.docx")),
            patch(
                "backend.services.docgen.render_single_document",
                side_effect=[
                    ("工作单1.docx", b"docx-1"),
                    ValueError("模板渲染失败"),
                ],
            ),
            patch(
                "backend.services.docgen.convert_docx_bytes_to_doc",
                return_value=("工作单1.doc", b"doc-1"),
            ),
        ):
            artifact = generate_workorder_batch_artifact(payload)

        self.assertTrue(artifact.filename.endswith("_1份.zip"))

        with zipfile.ZipFile(io.BytesIO(artifact.content)) as archive:
            names = archive.namelist()
            self.assertIn("工作单/工作单1.doc", names)
            self.assertIn("失败记录.json", names)
            failure_report = archive.read("失败记录.json").decode("utf-8")
            self.assertIn("中心林地", failure_report)
            self.assertIn("模板渲染失败", failure_report)

    def test_generate_workorder_batch_artifact_raises_when_all_fail(self) -> None:
        payload = WorkOrderGenerateRequest(
            pest_type="春尺蠖",
            task_type="春尺蠖防治",
            task="2026春尺蠖防治",
            records=[
                {
                    "survey_date": "2026-04-01",
                    "locality": "于家务乡",
                    "location_id": "YF0069",
                    "location_name": "神仙村",
                    "description": "点位描述1",
                    "note": "",
                    "images": [],
                },
            ],
        )

        with (
            patch("backend.services.docgen.get_template_path", return_value=Path("/tmp/template.docx")),
            patch(
                "backend.services.docgen.render_single_document",
                side_effect=ValueError("模板渲染失败"),
            ),
        ):
            with self.assertRaises(ValueError) as context:
                generate_workorder_batch_artifact(payload)

        self.assertIn("批量导出全部失败", str(context.exception))
        self.assertIn("神仙村", str(context.exception))


if __name__ == "__main__":
    unittest.main()
