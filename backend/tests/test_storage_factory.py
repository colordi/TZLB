from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from backend.config import BASE_DIR
from backend.services import storage_config
from backend.services.storage import (
    FallbackAssetStorage,
    LocalAssetStorage,
    R2AssetStorage,
    derive_key_prefix,
    get_storage_for_dir,
)


def build_r2_settings(**overrides):
    payload = {
        "asset_storage_backend": "r2",
        "r2_endpoint_url": "https://example.r2.cloudflarestorage.com",
        "r2_access_key_id": "key-id",
        "r2_secret_access_key": "secret",
        "r2_bucket": "tzlb-assets",
        "r2_prefix": "assets/",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class DeriveKeyPrefixTest(unittest.TestCase):
    def test_dir_inside_project_maps_to_relative_path(self) -> None:
        directory = BASE_DIR / "points" / "美国白蛾点位截图"
        self.assertEqual(derive_key_prefix(directory), "points/美国白蛾点位截图")

        images_date_dir = BASE_DIR / "images" / "2026-07-20"
        self.assertEqual(derive_key_prefix(images_date_dir), "images/2026-07-20")

    def test_dir_outside_project_falls_back_to_dir_name(self) -> None:
        with TemporaryDirectory() as tempdir:
            directory = Path(tempdir) / "美国白蛾点位截图"
            self.assertEqual(derive_key_prefix(directory), "美国白蛾点位截图")


class GetStorageForDirTest(unittest.TestCase):
    def setUp(self) -> None:
        storage_config.set_storage_config_override(None)

    def tearDown(self) -> None:
        storage_config.set_storage_config_override(None)

    def test_defaults_to_local_storage(self) -> None:
        with TemporaryDirectory() as tempdir:
            storage = get_storage_for_dir(Path(tempdir), SimpleNamespace())
            self.assertIsInstance(storage, LocalAssetStorage)
            self.assertEqual(storage.directory, Path(tempdir))

    def test_r2_backend_builds_prefixed_r2_storage(self) -> None:
        directory = BASE_DIR / "points" / "美国白蛾点位截图"
        storage = get_storage_for_dir(directory, build_r2_settings())

        self.assertIsInstance(storage, FallbackAssetStorage)
        self.assertIsInstance(storage.primary, R2AssetStorage)
        self.assertIsInstance(storage.fallback, LocalAssetStorage)
        self.assertEqual(storage.primary.bucket, "tzlb-assets")
        self.assertEqual(storage.primary.prefix, "assets/points/美国白蛾点位截图")

    def test_r2_blank_prefix_falls_back_to_default(self) -> None:
        directory = BASE_DIR / "images" / "2026-07-20"
        storage = get_storage_for_dir(directory, build_r2_settings(r2_prefix=""))

        self.assertIsInstance(storage, FallbackAssetStorage)
        self.assertEqual(storage.primary.prefix, "assets/images/2026-07-20")

    def test_database_override_takes_precedence_over_env(self) -> None:
        storage_config.set_storage_config_override(
            storage_config.StorageConfig(
                backend="r2",
                r2_endpoint_url="https://override.r2.cloudflarestorage.com",
                r2_access_key_id="override-key",
                r2_secret_access_key="override-secret",
                r2_bucket="override-bucket",
                r2_prefix="assets/",
            )
        )

        storage = get_storage_for_dir(BASE_DIR / "images" / "2026-07-20", SimpleNamespace())

        self.assertIsInstance(storage, FallbackAssetStorage)
        self.assertEqual(storage.primary.bucket, "override-bucket")

    def test_incomplete_r2_config_raises_configuration_error(self) -> None:
        from backend.exceptions import ConfigurationError

        with self.assertRaisesRegex(ConfigurationError, "Bucket"):
            get_storage_for_dir(
                BASE_DIR / "images" / "2026-07-20",
                build_r2_settings(r2_bucket=""),
            )


if __name__ == "__main__":
    unittest.main()
