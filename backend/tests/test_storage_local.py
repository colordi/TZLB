from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.services.storage import LocalAssetStorage


class LocalAssetStorageTest(unittest.TestCase):
    def test_write_read_exists_delete_roundtrip(self) -> None:
        with TemporaryDirectory() as tempdir:
            storage = LocalAssetStorage(Path(tempdir) / "images" / "2026-05-26")

            self.assertFalse(storage.exists("MQ001-1.jpg"))
            storage.write("MQ001-1.jpg", b"image-bytes")

            self.assertTrue(storage.exists("MQ001-1.jpg"))
            self.assertEqual(storage.read("MQ001-1.jpg"), b"image-bytes")
            self.assertTrue(
                (Path(tempdir) / "images" / "2026-05-26" / "MQ001-1.jpg").is_file()
            )

            storage.delete("MQ001-1.jpg")
            self.assertFalse(storage.exists("MQ001-1.jpg"))

    def test_read_missing_raises_not_found(self) -> None:
        with TemporaryDirectory() as tempdir:
            storage = LocalAssetStorage(Path(tempdir))
            with self.assertRaises(FileNotFoundError):
                storage.read("missing.jpg")

    def test_delete_missing_is_silent(self) -> None:
        with TemporaryDirectory() as tempdir:
            LocalAssetStorage(Path(tempdir)).delete("missing.jpg")

    def test_list_returns_files_with_sizes_and_skips_subdirs(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "a.jpg").write_bytes(b"1234")
            (root / "b.png").write_bytes(b"12")
            (root / "nested").mkdir()
            (root / "nested" / "c.jpg").write_bytes(b"x")

            objects = LocalAssetStorage(root).list()

            self.assertEqual(
                {(obj.name, obj.size_bytes) for obj in objects},
                {("a.jpg", 4), ("b.png", 2)},
            )

    def test_list_skips_symlink_pointing_outside(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            storage_dir = root / "screenshots"
            storage_dir.mkdir()
            outside = root / "outside.jpg"
            outside.write_bytes(b"x")
            (storage_dir / "YB001.jpg").symlink_to(outside)

            self.assertEqual(LocalAssetStorage(storage_dir).list(), [])

    def test_list_missing_directory_returns_empty(self) -> None:
        with TemporaryDirectory() as tempdir:
            storage = LocalAssetStorage(Path(tempdir) / "not-exists")
            self.assertEqual(storage.list(), [])

    def test_rejects_path_traversal_names(self) -> None:
        with TemporaryDirectory() as tempdir:
            storage = LocalAssetStorage(Path(tempdir))
            with self.assertRaisesRegex(ValueError, "文件名不合法"):
                storage.read("../secret.jpg")
            with self.assertRaisesRegex(ValueError, "文件名不合法"):
                storage.write("a/b.jpg", b"x")
            with self.assertRaisesRegex(ValueError, "文件名不合法"):
                storage.exists("..\\secret.jpg")


if __name__ == "__main__":
    unittest.main()
