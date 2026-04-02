from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Response

from backend.routers.auth import login, logout
from backend.schemas import LoginRequest


class AuthRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_login_success_sets_cookie(self) -> None:
        response = Response()
        settings = SimpleNamespace(
            auth_remember_ttl_days=30,
            auth_session_ttl_hours=12,
            auth_secret_key="test-secret",
            auth_cookie_name="tzlb_session",
            auth_cookie_secure=False,
        )
        user_payload = {
            "id": 1,
            "username": "admin",
            "display_name": "系统管理员",
            "is_active": True,
            "last_login_at": None,
        }

        with (
            patch("backend.routers.auth.get_settings", return_value=settings),
            patch(
                "backend.routers.auth.authenticate_user",
                new=AsyncMock(return_value=user_payload),
            ),
        ):
            result = await login(
                LoginRequest(username="admin", password="Forestry@2026", remember_me=True),
                response,
            )

        self.assertEqual(result.user.username, "admin")
        self.assertIn("tzlb_session=", response.headers.get("set-cookie", ""))
        self.assertIn("Max-Age=2592000", response.headers.get("set-cookie", ""))

    async def test_login_failure_returns_401(self) -> None:
        response = Response()

        with patch(
            "backend.routers.auth.authenticate_user",
            new=AsyncMock(return_value=None),
        ):
            with self.assertRaises(HTTPException) as context:
                await login(
                    LoginRequest(username="admin", password="bad-password", remember_me=False),
                    response,
                )

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "用户名或密码错误")

    async def test_logout_clears_cookie(self) -> None:
        response = Response()
        settings = SimpleNamespace(
            auth_cookie_name="tzlb_session",
            auth_cookie_secure=False,
        )

        with patch("backend.routers.auth.get_settings", return_value=settings):
            result = await logout(response)

        self.assertEqual(result.status_code, 204)
        self.assertIn("tzlb_session=", result.headers.get("set-cookie", ""))
        self.assertIn("Max-Age=0", result.headers.get("set-cookie", ""))


if __name__ == "__main__":
    unittest.main()
