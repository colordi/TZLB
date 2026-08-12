from __future__ import annotations

import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from backend.services.point_date_image_service import (
    delete_point_date_image,
    list_date_images,
    list_point_date_images,
    read_point_date_image,
    save_point_date_images,
)


def make_jpeg_bytes(color: str = "red") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color).save(buffer, format="JPEG")
    return buffer.getvalue()


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.content = content

    async def read(self) -> bytes:
        return self.content


def patch_images_dir(images_dir: Path):
    return patch(
        "backend.services.point_date_image_service.get_settings",
        return_value=SimpleNamespace(images_dir=images_dir),
    )


class SavePointDateImagesTest(unittest.IsolatedAsyncioTestCase):
    async def test_save_renames_files_with_point_code_and_sequence(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            files = [
                FakeUploadFile("现场照片A.jpg", make_jpeg_bytes("red")),
                FakeUploadFile("现场照片B.png", make_jpeg_bytes("blue")),
            ]

            with patch_images_dir(images_dir):
                result = await save_point_date_images(
                    survey_date="2026-05-26",
                    point_code="MQ001",
                    files=files,
                )

            self.assertEqual(result["saved_count"], 2)
            self.assertEqual(result["rejected"], [])
            saved_names = [item["file_name"] for item in result["saved"]]
            self.assertEqual(saved_names, ["MQ001-1.jpg", "MQ001-2.jpg"])
            date_dir = images_dir / "2026-05-26"
            self.assertTrue((date_dir / "MQ001-1.jpg").is_file())
            self.assertTrue((date_dir / "MQ001-2.jpg").is_file())
            self.assertTrue((date_dir / "MQ001-1.thumb.jpg").is_file())
            self.assertTrue((date_dir / "MQ001-2.thumb.jpg").is_file())

    async def test_save_continues_sequence_from_existing_files(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            date_dir = images_dir / "2026-05-26"
            date_dir.mkdir(parents=True)
            (date_dir / "MQ001-1.jpg").write_bytes(make_jpeg_bytes())
            (date_dir / "MQ001-2.jpg").write_bytes(make_jpeg_bytes())
            legacy = date_dir / "MQ001现场.jpg"
            legacy.write_bytes(make_jpeg_bytes("green"))

            with patch_images_dir(images_dir):
                result = await save_point_date_images(
                    survey_date="2026-05-26",
                    point_code="MQ001",
                    files=[FakeUploadFile("新照片.jpg", make_jpeg_bytes("yellow"))],
                )

            self.assertEqual(result["saved_count"], 1)
            self.assertEqual(result["saved"][0]["file_name"], "MQ001-3.jpg")
            self.assertTrue((date_dir / "MQ001-3.jpg").is_file())
            self.assertEqual(legacy.read_bytes(), make_jpeg_bytes("green"))

    async def test_save_rejects_non_image_content_but_keeps_valid_files(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            files = [
                FakeUploadFile("说明.txt", b"not an image"),
                FakeUploadFile("正常.jpg", make_jpeg_bytes()),
            ]

            with patch_images_dir(images_dir):
                result = await save_point_date_images(
                    survey_date="2026-05-26",
                    point_code="MQ001",
                    files=files,
                )

            self.assertEqual(result["saved_count"], 1)
            self.assertEqual(len(result["rejected"]), 1)
            self.assertEqual(result["rejected"][0]["file_name"], "说明.txt")

    async def test_save_rejects_invalid_date_and_point_code(self) -> None:
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            await save_point_date_images(
                survey_date="20260526",
                point_code="MQ001",
                files=[FakeUploadFile("a.jpg", make_jpeg_bytes())],
            )

        with self.assertRaisesRegex(ValueError, "点位编号"):
            await save_point_date_images(
                survey_date="2026-05-26",
                point_code="MQ/001",
                files=[FakeUploadFile("a.jpg", make_jpeg_bytes())],
            )

    async def test_save_rejects_empty_file_list(self) -> None:
        with self.assertRaisesRegex(ValueError, "请选择要上传的图片"):
            await save_point_date_images(
                survey_date="2026-05-26",
                point_code="MQ001",
                files=[],
            )


class ListPointDateImagesTest(unittest.TestCase):
    def test_list_only_returns_images_with_matching_prefix(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            date_dir = images_dir / "2026-05-26"
            date_dir.mkdir(parents=True)
            (date_dir / "MQ001-1.jpg").write_bytes(make_jpeg_bytes())
            (date_dir / "MQ001现场.jpg").write_bytes(make_jpeg_bytes())
            (date_dir / "MQ002-1.jpg").write_bytes(make_jpeg_bytes())
            (date_dir / "AMQ001-1.jpg").write_bytes(make_jpeg_bytes())
            (date_dir / "MQ001-说明.txt").write_text("text", encoding="utf-8")

            with patch_images_dir(images_dir):
                images = list_point_date_images(
                    survey_date="2026-05-26",
                    point_code="MQ001",
                )

            self.assertEqual(
                [item["file_name"] for item in images],
                ["MQ001-1.jpg", "MQ001现场.jpg"],
            )

    def test_list_returns_empty_when_directory_missing(self) -> None:
        with TemporaryDirectory() as tempdir:
            with patch_images_dir(Path(tempdir) / "images"):
                images = list_point_date_images(
                    survey_date="2026-05-26",
                    point_code="MQ001",
                )
            self.assertEqual(images, [])

    def test_list_date_images_excludes_thumbnail_sidecars(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            date_dir = images_dir / "2026-05-26"
            date_dir.mkdir(parents=True)
            (date_dir / "MQ001-1.jpg").write_bytes(make_jpeg_bytes())
            (date_dir / "MQ001-1.thumb.jpg").write_bytes(make_jpeg_bytes("blue"))

            with patch_images_dir(images_dir):
                images = list_date_images(survey_date="2026-05-26")

            self.assertEqual([item["file_name"] for item in images], ["MQ001-1.jpg"])

    def test_list_date_images_returns_all_images_sorted(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            date_dir = images_dir / "2026-05-26"
            date_dir.mkdir(parents=True)
            (date_dir / "MQ001-2.jpg").write_bytes(make_jpeg_bytes())
            (date_dir / "MQ001-10.jpg").write_bytes(make_jpeg_bytes())
            (date_dir / "GH01-1.jpg").write_bytes(make_jpeg_bytes())
            (date_dir / "说明.txt").write_text("text", encoding="utf-8")

            with patch_images_dir(images_dir):
                images = list_date_images(survey_date="2026-05-26")

            self.assertEqual(
                [item["file_name"] for item in images],
                ["GH01-1.jpg", "MQ001-2.jpg", "MQ001-10.jpg"],
            )


class ReadPointDateImageTest(unittest.TestCase):
    def test_read_rejects_path_traversal_and_non_image(self) -> None:
        with TemporaryDirectory() as tempdir:
            with patch_images_dir(Path(tempdir) / "images"):
                with self.assertRaisesRegex(ValueError, "文件名不合法"):
                    read_point_date_image(
                        survey_date="2026-05-26",
                        file_name="../MQ001-1.jpg",
                    )
                with self.assertRaisesRegex(ValueError, "图片文件"):
                    read_point_date_image(
                        survey_date="2026-05-26",
                        file_name="MQ001-说明.txt",
                    )

    def test_read_returns_none_when_missing(self) -> None:
        with TemporaryDirectory() as tempdir:
            with patch_images_dir(Path(tempdir) / "images"):
                result = read_point_date_image(
                    survey_date="2026-05-26",
                    file_name="MQ001-1.jpg",
                )
            self.assertIsNone(result)

    def test_read_returns_content_and_media_type(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            date_dir = images_dir / "2026-05-26"
            date_dir.mkdir(parents=True)
            content = make_jpeg_bytes()
            (date_dir / "MQ001-1.jpg").write_bytes(content)

            with patch_images_dir(images_dir):
                result = read_point_date_image(
                    survey_date="2026-05-26",
                    file_name="MQ001-1.jpg",
                )

            self.assertIsNotNone(result)
            read_content, media_type = result
            self.assertEqual(read_content, content)
            self.assertEqual(media_type, "image/jpeg")

    def test_read_thumb_returns_downscaled_jpeg(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            date_dir = images_dir / "2026-05-26"
            date_dir.mkdir(parents=True)
            buffer = io.BytesIO()
            Image.new("RGB", (800, 600), color=(45, 120, 80)).save(buffer, format="JPEG")
            content = buffer.getvalue()
            (date_dir / "MQ001-1.jpg").write_bytes(content)

            with patch_images_dir(images_dir):
                result = read_point_date_image(
                    survey_date="2026-05-26",
                    file_name="MQ001-1.jpg",
                    size="thumb",
                )
                cached = read_point_date_image(
                    survey_date="2026-05-26",
                    file_name="MQ001-1.jpg",
                    size="thumb",
                )

            self.assertIsNotNone(result)
            thumb_content, media_type = result
            self.assertEqual(media_type, "image/jpeg")
            self.assertLess(len(thumb_content), len(content))
            self.assertTrue((date_dir / "MQ001-1.thumb.jpg").is_file())
            self.assertEqual(cached[0], thumb_content)
            with Image.open(io.BytesIO(thumb_content)) as thumb:
                self.assertEqual(thumb.format, "JPEG")
                self.assertLessEqual(max(thumb.size), 360)

    def test_read_rejects_invalid_size(self) -> None:
        with TemporaryDirectory() as tempdir:
            with patch_images_dir(Path(tempdir) / "images"):
                with self.assertRaisesRegex(ValueError, "预览尺寸"):
                    read_point_date_image(
                        survey_date="2026-05-26",
                        file_name="MQ001-1.jpg",
                        size="medium",
                    )


class DeletePointDateImageTest(unittest.TestCase):
    def test_delete_removes_matching_image(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            date_dir = images_dir / "2026-05-26"
            date_dir.mkdir(parents=True)
            target = date_dir / "MQ001-1.jpg"
            target.write_bytes(make_jpeg_bytes())

            with patch_images_dir(images_dir):
                delete_point_date_image(
                    survey_date="2026-05-26",
                    point_code="MQ001",
                    file_name="MQ001-1.jpg",
                )

            self.assertFalse(target.exists())

    def test_delete_rejects_image_of_other_point(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            date_dir = images_dir / "2026-05-26"
            date_dir.mkdir(parents=True)
            (date_dir / "MQ002-1.jpg").write_bytes(make_jpeg_bytes())

            with patch_images_dir(images_dir):
                with self.assertRaisesRegex(ValueError, "点位编号"):
                    delete_point_date_image(
                        survey_date="2026-05-26",
                        point_code="MQ001",
                        file_name="MQ002-1.jpg",
                    )

            self.assertTrue((date_dir / "MQ002-1.jpg").exists())

    def test_delete_missing_image_raises_not_found(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            (images_dir / "2026-05-26").mkdir(parents=True)

            with patch_images_dir(images_dir):
                with self.assertRaises(FileNotFoundError):
                    delete_point_date_image(
                        survey_date="2026-05-26",
                        point_code="MQ001",
                        file_name="MQ001-9.jpg",
                    )


if __name__ == "__main__":
    unittest.main()
