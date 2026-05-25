from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from backend.auth.dependencies import get_current_user, require_user_role


def build_request(
    headers: dict[str, str] | None = None,
    client: tuple[str, int] = ("127.0.0.1", 52341),
) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/auth/me",
        "raw_path": b"/api/auth/me",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in (headers or {}).items()
        ],
        "client": client,
        "server": ("127.0.0.1", 8000),
    }
    return Request(scope)


class AuthDependenciesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.settings = SimpleNamespace(
            auth_cookie_name="tzlb_session",
            auth_secret_key="test-secret",
            auth_bypass_localhost=True,
            auth_default_admin_username="admin",
            auth_default_admin_display_name="系统管理员",
        )

    async def test_local_bypass_accepts_loopback_referer(self) -> None:
        request = build_request(
            {
                "x-tzlb-local-auth-bypass": "1",
                "referer": "http://127.0.0.1:5173/map",
            }
        )

        with patch("backend.auth.dependencies.get_settings", return_value=self.settings):
            user = await get_current_user(request)

        self.assertEqual(user["id"], 0)
        self.assertEqual(user["username"], "admin")
        self.assertEqual(user["display_name"], "系统管理员")
        self.assertEqual(user["role"], "admin")

    async def test_local_bypass_rejects_non_loopback_referer(self) -> None:
        request = build_request(
            {
                "x-tzlb-local-auth-bypass": "1",
                "referer": "http://192.168.1.20:5173/map",
            }
        )

        with patch("backend.auth.dependencies.get_settings", return_value=self.settings):
            with self.assertRaises(HTTPException) as context:
                await get_current_user(request)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "未登录或登录状态已失效")

    async def test_local_bypass_accepts_direct_loopback_api_request(self) -> None:
        request = build_request(
            {
                "x-tzlb-local-auth-bypass": "1",
                "host": "127.0.0.1:8000",
            }
        )

        with patch("backend.auth.dependencies.get_settings", return_value=self.settings):
            user = await get_current_user(request)

        self.assertEqual(user["username"], "admin")
        self.assertTrue(user["is_active"])

    async def test_role_dependency_accepts_allowed_role(self) -> None:
        dependency = require_user_role("admin")

        user = await dependency(
            {
                "id": 1,
                "username": "admin",
                "display_name": "系统管理员",
                "role": "admin",
                "is_active": True,
            }
        )

        self.assertEqual(user["username"], "admin")

    async def test_role_dependency_rejects_disallowed_role(self) -> None:
        dependency = require_user_role("admin")

        with self.assertRaises(HTTPException) as context:
            await dependency(
                {
                    "id": 2,
                    "username": "dc01",
                    "display_name": "调查员 dc01",
                    "role": "investigator",
                    "is_active": True,
                }
            )

        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(context.exception.detail, "当前账号无权访问该功能")


if __name__ == "__main__":
    unittest.main()
