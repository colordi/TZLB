from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from backend.auth.security import (
    build_session_token,
    hash_password,
    parse_session_token,
    verify_password,
)


class PasswordSecurityTest(unittest.TestCase):
    def test_hash_password_can_be_verified(self) -> None:
        password_hash = hash_password("Forestry@2026")

        self.assertNotEqual(password_hash, "Forestry@2026")
        self.assertTrue(verify_password("Forestry@2026", password_hash))
        self.assertFalse(verify_password("wrong-password", password_hash))

    def test_session_token_roundtrip(self) -> None:
        now = datetime(2026, 4, 2, 8, 0, tzinfo=timezone.utc)
        token, expires_at = build_session_token(
            username="admin",
            secret_key="test-secret",
            lifetime=timedelta(hours=2),
            now=now,
        )

        payload = parse_session_token(token, "test-secret", now=now + timedelta(minutes=30))

        self.assertIsNotNone(payload)
        self.assertEqual(payload.username, "admin")
        self.assertEqual(payload.expires_at, expires_at)

    def test_expired_or_tampered_session_token_is_rejected(self) -> None:
        now = datetime(2026, 4, 2, 8, 0, tzinfo=timezone.utc)
        token, _ = build_session_token(
            username="admin",
            secret_key="test-secret",
            lifetime=timedelta(minutes=10),
            now=now,
        )

        self.assertIsNone(parse_session_token(token, "wrong-secret", now=now))
        self.assertIsNone(
            parse_session_token(token, "test-secret", now=now + timedelta(minutes=11))
        )


if __name__ == "__main__":
    unittest.main()
