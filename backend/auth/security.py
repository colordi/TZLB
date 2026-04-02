from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


PASSWORD_SCHEME = "scrypt"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
PASSWORD_SALT_BYTES = 16


def _encode_base64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_base64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def hash_password(password: str) -> str:
    """使用 scrypt 生成密码摘要。"""

    normalized_password = password.encode("utf-8")
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.scrypt(
        normalized_password,
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return (
        f"{PASSWORD_SCHEME}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}$"
        f"{_encode_base64url(salt)}${_encode_base64url(digest)}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与摘要是否匹配。"""

    try:
        scheme, n, r, p, salt, expected_digest = password_hash.split("$", 5)
    except ValueError:
        return False

    if scheme != PASSWORD_SCHEME:
        return False

    try:
        derived_digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_decode_base64url(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=SCRYPT_DKLEN,
        )
        expected_bytes = _decode_base64url(expected_digest)
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(derived_digest, expected_bytes)


@dataclass(frozen=True)
class SessionPayload:
    username: str
    expires_at: datetime


def build_session_token(
    username: str,
    secret_key: str,
    lifetime: timedelta,
    *,
    now: datetime | None = None,
) -> tuple[str, datetime]:
    """构造签名会话令牌。"""

    issued_at = now or datetime.now(timezone.utc)
    expires_at = issued_at + lifetime
    payload = {
        "sub": username,
        "exp": int(expires_at.timestamp()),
    }
    payload_segment = _encode_base64url(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = _encode_base64url(
        hmac.new(
            secret_key.encode("utf-8"),
            payload_segment.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    )
    return f"{payload_segment}.{signature}", expires_at


def parse_session_token(
    token: str,
    secret_key: str,
    *,
    now: datetime | None = None,
) -> SessionPayload | None:
    """解析并校验会话令牌。"""

    if not token or "." not in token:
        return None

    payload_segment, signature = token.split(".", 1)
    expected_signature = _encode_base64url(
        hmac.new(
            secret_key.encode("utf-8"),
            payload_segment.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    )

    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        payload = json.loads(_decode_base64url(payload_segment).decode("utf-8"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    username = str(payload.get("sub", "")).strip()
    expires_at_epoch = payload.get("exp")
    if not username or not isinstance(expires_at_epoch, int):
        return None

    expires_at = datetime.fromtimestamp(expires_at_epoch, tz=timezone.utc)
    current_time = now or datetime.now(timezone.utc)
    if expires_at <= current_time:
        return None

    return SessionPayload(username=username, expires_at=expires_at)
