from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.config import validate_runtime_settings


def build_settings(**overrides):
    payload = {
        "app_env": "development",
        "auth_secret_key": "tzlb-dev-secret-change-me",
        "auth_default_admin_password": "Forestry@2026",
        "auth_cookie_secure": False,
        "auth_bypass_localhost": False,
        "workorder_default_output_format": "doc",
        "workorder_image_max_bytes": 8 * 1024 * 1024,
        "workorder_image_max_total_bytes": 24 * 1024 * 1024,
        "workorder_image_max_dimension": 1600,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class RuntimeSettingsValidationTest(unittest.TestCase):
    def test_development_allows_default_dev_credentials(self) -> None:
        validate_runtime_settings(build_settings())

    def test_production_rejects_all_unsafe_auth_defaults(self) -> None:
        with self.assertRaises(RuntimeError) as context:
            validate_runtime_settings(
                build_settings(
                    app_env="production",
                    auth_bypass_localhost=True,
                )
            )

        message = str(context.exception)
        self.assertIn("AUTH_SECRET_KEY", message)
        self.assertIn("AUTH_DEFAULT_ADMIN_PASSWORD", message)
        self.assertIn("AUTH_COOKIE_SECURE", message)
        self.assertIn("AUTH_BYPASS_LOCALHOST", message)

    def test_production_accepts_hardened_auth_settings(self) -> None:
        validate_runtime_settings(
            build_settings(
                app_env="production",
                auth_secret_key="replace-with-long-random-secret",
                auth_default_admin_password="Changed@2026",
                auth_cookie_secure=True,
            )
        )

    def test_rejects_invalid_workorder_output_format(self) -> None:
        with self.assertRaises(RuntimeError) as context:
            validate_runtime_settings(
                build_settings(workorder_default_output_format="pdf")
            )

        self.assertIn("WORKORDER_DEFAULT_OUTPUT_FORMAT", str(context.exception))


if __name__ == "__main__":
    unittest.main()
