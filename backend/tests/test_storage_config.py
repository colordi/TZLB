from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from backend.services import storage_config
from backend.services.storage_config import StorageConfig


class StorageConfigTestCase(unittest.TestCase):
    def setUp(self) -> None:
        storage_config.set_storage_config_override(None)

    def tearDown(self) -> None:
        storage_config.set_storage_config_override(None)


class FromSettingsTest(StorageConfigTestCase):
    def test_defaults_to_local_with_default_prefix(self) -> None:
        config = storage_config.storage_config_from_settings(SimpleNamespace())

        self.assertEqual(config.backend, "local")
        self.assertEqual(config.r2_prefix, "assets/")

    def test_reads_r2_fields(self) -> None:
        settings = SimpleNamespace(
            asset_storage_backend=" R2 ",
            r2_endpoint_url=" https://example.r2.dev ",
            r2_access_key_id="key",
            r2_secret_access_key="secret",
            r2_bucket="bucket",
            r2_prefix="",
        )

        config = storage_config.storage_config_from_settings(settings)

        self.assertEqual(config.backend, "r2")
        self.assertEqual(config.r2_endpoint_url, "https://example.r2.dev")
        self.assertEqual(config.r2_prefix, "assets/")


class ResolveStorageConfigTest(StorageConfigTestCase):
    def test_override_takes_precedence(self) -> None:
        storage_config.set_storage_config_override(StorageConfig(backend="r2", r2_bucket="b"))

        config = storage_config.resolve_storage_config(
            SimpleNamespace(asset_storage_backend="local")
        )

        self.assertEqual(config.backend, "r2")
        self.assertEqual(config.r2_bucket, "b")

    def test_falls_back_to_settings_without_override(self) -> None:
        config = storage_config.resolve_storage_config(
            SimpleNamespace(asset_storage_backend="local")
        )
        self.assertEqual(config.backend, "local")


class RefreshOverrideTest(unittest.IsolatedAsyncioTestCase):
    def tearDown(self) -> None:
        storage_config.set_storage_config_override(None)

    async def test_refresh_loads_override_from_database(self) -> None:
        rows = {
            "asset_storage_backend": "r2",
            "r2_endpoint_url": "https://example.r2.dev",
            "r2_access_key_id": "key",
            "r2_secret_access_key": "secret",
            "r2_bucket": "bucket",
            "r2_prefix": "assets/",
        }

        with patch(
            "backend.services.storage_config.app_settings_db.load_app_settings",
            new=AsyncMock(return_value=rows),
        ):
            await storage_config.refresh_storage_config_override()

        override = storage_config.get_storage_config_override()
        self.assertIsNotNone(override)
        self.assertEqual(override.backend, "r2")
        self.assertEqual(override.r2_bucket, "bucket")

    async def test_refresh_clears_override_when_table_empty(self) -> None:
        storage_config.set_storage_config_override(StorageConfig(backend="r2"))

        with patch(
            "backend.services.storage_config.app_settings_db.load_app_settings",
            new=AsyncMock(return_value={}),
        ):
            await storage_config.refresh_storage_config_override()

        self.assertIsNone(storage_config.get_storage_config_override())


class ValidateStorageConfigTest(StorageConfigTestCase):
    def test_local_backend_always_valid(self) -> None:
        storage_config.validate_storage_config(StorageConfig(backend="local"))

    def test_rejects_unknown_backend(self) -> None:
        with self.assertRaisesRegex(ValueError, "local 或 r2"):
            storage_config.validate_storage_config(StorageConfig(backend="oss"))

    def test_r2_requires_each_field(self) -> None:
        cases = [
            ({"r2_endpoint_url": ""}, "Endpoint"),
            ({"r2_access_key_id": ""}, "Access Key ID"),
            ({"r2_secret_access_key": ""}, "Secret Access Key"),
            ({"r2_bucket": ""}, "Bucket"),
        ]
        complete = {
            "r2_endpoint_url": "https://example.r2.dev",
            "r2_access_key_id": "key",
            "r2_secret_access_key": "secret",
            "r2_bucket": "bucket",
        }
        for missing_override, message in cases:
            fields = {**complete, **missing_override}
            with self.assertRaisesRegex(ValueError, message):
                storage_config.validate_storage_config(StorageConfig(backend="r2", **fields))

    def test_r2_complete_config_valid(self) -> None:
        storage_config.validate_storage_config(
            StorageConfig(
                backend="r2",
                r2_endpoint_url="https://example.r2.dev",
                r2_access_key_id="key",
                r2_secret_access_key="secret",
                r2_bucket="bucket",
            )
        )


class BuildConfigFromPayloadTest(StorageConfigTestCase):
    def test_empty_secret_falls_back_to_existing(self) -> None:
        payload = SimpleNamespace(
            backend="r2",
            r2_endpoint_url="https://example.r2.dev",
            r2_access_key_id="key",
            r2_secret_access_key="",
            r2_bucket="bucket",
            r2_prefix="assets/",
        )

        config = storage_config.build_config_from_payload(
            payload, fallback_secret="saved-secret"
        )

        self.assertEqual(config.r2_secret_access_key, "saved-secret")

    def test_new_secret_overrides(self) -> None:
        payload = SimpleNamespace(
            backend="r2",
            r2_endpoint_url="",
            r2_access_key_id="",
            r2_secret_access_key="new-secret",
            r2_bucket="",
            r2_prefix="",
        )

        config = storage_config.build_config_from_payload(
            payload, fallback_secret="saved-secret"
        )

        self.assertEqual(config.r2_secret_access_key, "new-secret")
        self.assertEqual(config.r2_prefix, "assets/")


class ConfigToSettingsDictTest(StorageConfigTestCase):
    def test_roundtrip_keys(self) -> None:
        config = StorageConfig(backend="r2", r2_bucket="bucket")
        values = storage_config.config_to_settings_dict(config)

        self.assertEqual(set(values), set(storage_config.STORAGE_CONFIG_KEYS))
        self.assertEqual(values["r2_bucket"], "bucket")


if __name__ == "__main__":
    unittest.main()
