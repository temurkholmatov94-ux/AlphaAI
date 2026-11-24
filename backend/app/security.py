from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.config import get_settings

_password_hash = PasswordHash.recommended()
_DUMMY_HASH = _password_hash.hash("alphaai-invalid-user-password")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    candidate = password_hash or _DUMMY_HASH
    valid = _password_hash.verify(password, candidate)
    return bool(password_hash) and valid


def _secret() -> bytes:
    value = get_settings().alphaai_secret_key
    if not value or len(value) < 32:
        raise RuntimeError("ALPHAAI_SECRET_KEY must contain at least 32 characters")
    return value.encode("utf-8")


def create_access_token(user_id: int) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=get_settings().access_token_minutes)
    payload = {
        "sub": str(user_id),
        "iss": "alphaai",
        "aud": "alphaai-api",
        "iat": now,
        "exp": expires_at,
        "type": "access",
    }
    token = jwt.encode(payload, _secret(), algorithm="HS256")
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        _secret(),
        algorithms=["HS256"],
        issuer="alphaai",
        audience="alphaai-api",
        options={"require": ["sub", "exp", "iat", "iss", "aud"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    return payload


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def digest_secret(value: str) -> str:
    return hmac.new(_secret(), value.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    raw = f"aai_live_{secrets.token_urlsafe(36)}"
    return raw, raw[:18], digest_secret(raw)
