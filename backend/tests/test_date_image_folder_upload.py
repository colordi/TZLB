from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.services.date_image_folder_upload import upload_date_image_folder


class FakeUploadFile:
    def __init__(self, content: bytes) -> None:
        self.content = content

    async def read(self) -> bytes:
        return self.content


class DateImageFolderUploadTest(unittest.IsolatedAsyncioTestCase):
    async def test_upload_saves_images_and_skips_existing_non_image_and_nested_files(self) -> None:
        with TemporaryDirectory() as tempdir:
            images_dir = Path(tempdir) / "images"
            existing_dir = images_dir / "2026-05-26"
            existing_dir.mkdir(parents=True)
            (existing_dir / "MQ001.jpg").write_bytes(b"old")

            files = [
                FakeUploadFile(b"existing"),
                FakeUploadFile(b"new"),
                FakeUploadFile(b"text"),
                FakeUploadFile(b"nested"),
            ]
            relative_paths = [
                "2026-05-26/MQ001.jpg",
                "2026-05-26/MQ002.png",
                "2026-05-26/说明.txt",
                "2026-05-26/子目录/MQ003.jpg",
            ]

            with patch(
                "backend.services.date_image_folder_upload.get_settings",
                return_value=SimpleNamespace(images_dir=images_dir),
            ):
                result = await upload_date_image_folder(
                    folder_name="2026-05-26",
                    files=files,
                    relative_paths=relative_paths,
                )

            self.assertEqual(result["folder_name"], "2026-05-26")
            self.assertEqual(result["saved_count"], 1)
            self.assertEqual(result["skipped_existing_count"], 1)
            self.assertEqual(result["skipped_non_image_count"], 1)
            self.assertEqual(result["skipped_nested_count"], 1)
            self.assertEqual((existing_dir / "MQ001.jpg").read_bytes(), b"old")
            self.assertEqual((existing_dir / "MQ002.png").read_bytes(), b"new")

    async def test_invalid_folder_name_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            await upload_date_image_folder(
                folder_name="20260526",
                files=[FakeUploadFile(b"image")],
                relative_paths=["20260526/MQ001.jpg"],
            )

        with self.assertRaisesRegex(ValueError, "有效日期"):
            await upload_date_image_folder(
                folder_name="2026-02-31",
                files=[FakeUploadFile(b"image")],
                relative_paths=["2026-02-31/MQ001.jpg"],
            )

    async def test_mismatched_folder_is_rejected(self) -> None:
        with TemporaryDirectory() as tempdir:
            with patch(
                "backend.services.date_image_folder_upload.get_settings",
                return_value=SimpleNamespace(images_dir=Path(tempdir) / "images"),
            ):
                with self.assertRaisesRegex(ValueError, "同一个日期文件夹"):
                    await upload_date_image_folder(
                        folder_name="2026-05-26",
                        files=[FakeUploadFile(b"image")],
                        relative_paths=["2026-05-27/MQ001.jpg"],
                    )


if __name__ == "__main__":
    unittest.main()
