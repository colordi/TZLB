from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.routers.admin import (
    get_storage_config,
    post_storage_config_test,
    put_storage_config,
)
from backend.schemas import StorageConfigPayload
from backend.services import storage_config
from backend.services.storage_config import StorageConfig


class StorageConfigEndpointTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        storage_config.set_storage_config_override(None)

    def tearDown(self) -> None:
        storage_config.set_storage_config_override(None)


def build_payload(**overrides) -> StorageConfigPayload:
    values = {
        "backend": "r2",
        "r2_endpoint_url": "https://example.r2.cloudflarestorage.com",
        "r2_access_key_id": "key-id",
        "r2_secret_access_key": "secret",
        "r2_bucket": "tzlb-assets",
        "r2_prefix": "assets/",
    }
    values.update(overrides)
    return StorageConfigPayload(**values)


class GetStorageConfigTest(StorageConfigEndpointTestCase):
    async def test_returns_env_source_when_no_override(self) -> None:
        response = await get_storage_config()

        self.assertEqual(response.source, "env")
        self.assertEqual(response.backend, "local")
        self.assertFalse(response.r2_secret_configured)

    async def test_returns_database_source_with_masked_secret(self) -> None:
        storage_config.set_storage_config_override(
            StorageConfig(
                backend="r2",
                r2_endpoint_url="https://example.r2.dev",
                r2_access_key_id="key-id",
                r2_secret_access_key="super-secret",
                r2_bucket="bucket",
            )
        )

        with patch(
            "backend.routers.admin.app_settings_db.load_app_settings_meta",
            new=AsyncMock(
                return_value={
                    "asset_storage_backend": {
                        "updated_by": "admin",
                        "updated_at": "2026-08-12T10:00:00+00:00",
                    }
                }
            ),
        ):
            response = await get_storage_config()

        self.assertEqual(response.source, "database")
        self.assertEqual(response.backend, "r2")
        self.assertEqual(response.r2_access_key_id, "key-id")
        self.assertTrue(response.r2_secret_configured)
        self.assertEqual(response.updated_by, "admin")
        # 密钥本身永不下发
        self.assertNotIn("super-secret", response.model_dump_json())


class PutStorageConfigTest(StorageConfigEndpointTestCase):
    def patch_db(self, saved: dict):
        return patch(
            "backend.routers.admin.app_settings_db.save_app_settings",
            new=AsyncMock(side_effect=lambda values, *, updated_by: saved.update(values)),
        )

    async def test_saves_config_and_refreshes_override(self) -> None:
        saved: dict = {}

        def fake_refresh():
            storage_config.set_storage_config_override(
                storage_config.build_config_from_payload(build_payload())
            )

        with (
            self.patch_db(saved),
            patch(
                "backend.routers.admin.storage_config_service.refresh_storage_config_override",
                new=AsyncMock(side_effect=fake_refresh),
            ),
            patch(
                "backend.routers.admin.app_settings_db.load_app_settings_meta",
                new=AsyncMock(return_value={}),
            ),
        ):
            response = await put_storage_config(build_payload(), {"username": "admin"})

        self.assertEqual(saved["asset_storage_backend"], "r2")
        self.assertEqual(saved["r2_bucket"], "tzlb-assets")
        self.assertEqual(saved["r2_secret_access_key"], "secret")
        self.assertEqual(response.backend, "r2")
        self.assertEqual(response.source, "database")

    async def test_empty_secret_keeps_existing_value(self) -> None:
        storage_config.set_storage_config_override(
            StorageConfig(backend="r2", r2_secret_access_key="saved-secret")
        )
        saved: dict = {}

        with (
            self.patch_db(saved),
            patch(
                "backend.routers.admin.storage_config_service.refresh_storage_config_override",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "backend.routers.admin.app_settings_db.load_app_settings_meta",
                new=AsyncMock(return_value={}),
            ),
        ):
            await put_storage_config(
                build_payload(r2_secret_access_key=""),
                {"username": "admin"},
            )

        self.assertEqual(saved["r2_secret_access_key"], "saved-secret")

    async def test_incomplete_r2_config_returns_422(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await put_storage_config(build_payload(r2_bucket=""), {"username": "admin"})

        self.assertEqual(context.exception.status_code, 422)
        self.assertIn("Bucket", context.exception.detail)

    async def test_local_backend_saves_without_r2_fields(self) -> None:
        saved: dict = {}

        with (
            self.patch_db(saved),
            patch(
                "backend.routers.admin.storage_config_service.refresh_storage_config_override",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "backend.routers.admin.app_settings_db.load_app_settings_meta",
                new=AsyncMock(return_value={}),
            ),
        ):
            response = await put_storage_config(
                build_payload(
                    backend="local",
                    r2_endpoint_url="",
                    r2_access_key_id="",
                    r2_secret_access_key="",
                    r2_bucket="",
                    r2_prefix="assets/",
                ),
                {"username": "admin"},
            )

        self.assertEqual(saved["asset_storage_backend"], "local")
        self.assertEqual(response.backend, "local")


class TestStorageConnectionTest(StorageConfigEndpointTestCase):
    async def test_rejects_local_backend(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await post_storage_config_test(build_payload(backend="local"))

        self.assertEqual(context.exception.status_code, 422)

    async def test_success_returns_ok(self) -> None:
        with patch(
            "backend.routers.admin.test_r2_connection",
            new=AsyncMock(return_value=None),
        ):
            response = await post_storage_config_test(build_payload())

        self.assertTrue(response.ok)

    async def test_connection_failure_returns_422(self) -> None:
        with patch(
            "backend.routers.admin.test_r2_connection",
            new=AsyncMock(side_effect=ValueError("连接 R2 失败：Bucket 不存在或无访问权限")),
        ):
            with self.assertRaises(HTTPException) as context:
                await post_storage_config_test(build_payload())

        self.assertEqual(context.exception.status_code, 422)
        self.assertIn("Bucket", context.exception.detail)

    async def test_empty_secret_falls_back_to_saved_value(self) -> None:
        storage_config.set_storage_config_override(
            StorageConfig(backend="r2", r2_secret_access_key="saved-secret")
        )
        captured: list[StorageConfig] = []

        async def fake_test(config):
            captured.append(config)

        with patch(
            "backend.routers.admin.test_r2_connection",
            new=AsyncMock(side_effect=fake_test),
        ):
            await post_storage_config_test(build_payload(r2_secret_access_key=""))

        self.assertEqual(captured[0].r2_secret_access_key, "saved-secret")


if __name__ == "__main__":
    unittest.main()
