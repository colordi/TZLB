from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.services.storage import FallbackAssetStorage, LocalAssetStorage


class FallbackAssetStorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self._primary_dir = TemporaryDirectory()
        self._fallback_dir = TemporaryDirectory()
        self.addCleanup(self._primary_dir.cleanup)
        self.addCleanup(self._fallback_dir.cleanup)
        self.primary = LocalAssetStorage(Path(self._primary_dir.name))
        self.fallback = LocalAssetStorage(Path(self._fallback_dir.name))
        self.storage = FallbackAssetStorage(self.primary, self.fallback)

    def test_read_prefers_primary_then_fallback(self) -> None:
        self.fallback.write("old.jpg", b"local-bytes")
        self.primary.write("new.jpg", b"r2-bytes")

        self.assertEqual(self.storage.read("old.jpg"), b"local-bytes")
        self.assertEqual(self.storage.read("new.jpg"), b"r2-bytes")

    def test_read_primary_wins_on_name_conflict(self) -> None:
        self.fallback.write("same.jpg", b"local")
        self.primary.write("same.jpg", b"r2")

        self.assertEqual(self.storage.read("same.jpg"), b"r2")

    def test_read_missing_raises_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.storage.read("missing.jpg")

    def test_list_merges_with_primary_winning(self) -> None:
        self.fallback.write("old.jpg", b"1234")
        self.fallback.write("same.jpg", b"local!")
        self.primary.write("same.jpg", b"r2")

        objects = {obj.name: obj.size_bytes for obj in self.storage.list()}

        self.assertEqual(objects, {"old.jpg": 4, "same.jpg": 2})

    def test_write_only_goes_to_primary(self) -> None:
        self.storage.write("new.jpg", b"r2-bytes")

        self.assertTrue(self.primary.exists("new.jpg"))
        self.assertFalse(self.fallback.exists("new.jpg"))

    def test_delete_clears_both_layers(self) -> None:
        self.fallback.write("same.jpg", b"local")
        self.primary.write("same.jpg", b"r2")

        self.storage.delete("same.jpg")

        self.assertFalse(self.primary.exists("same.jpg"))
        self.assertFalse(self.fallback.exists("same.jpg"))

    def test_exists_checks_both_layers(self) -> None:
        self.fallback.write("old.jpg", b"x")

        self.assertTrue(self.storage.exists("old.jpg"))
        self.assertFalse(self.storage.exists("missing.jpg"))


if __name__ == "__main__":
    unittest.main()
