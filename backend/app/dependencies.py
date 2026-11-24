from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import APIKey, User
from app.security import decode_access_token, digest_secret

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    user: User
    scopes: frozenset[str]
    method: str
    api_key_id: int | None = None


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid authentication is required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    raw_token = credentials.credentials
    if raw_token.startswith("aai_live_"):
        try:
            key_digest = digest_secret(raw_token)
        except RuntimeError:
            raise HTTPException(status_code=503, detail="Authentication is not configured")
        api_key = db.scalar(select(APIKey).where(APIKey.key_hash == key_digest))
        now = datetime.now(timezone.utc)
        if api_key is None or api_key.revoked_at is not None:
            raise unauthorized
        expires_at = api_key.expires_at
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= now:
                raise unauthorized
        user = db.get(User, api_key.user_id)
        if user is None or not user.is_active or not user.email_verified:
            raise unauthorized
        api_key.last_used_at = now
        db.commit()
        return AuthContext(
            user=user,
            scopes=frozenset(api_key.scopes or []),
            method="api_key",
            api_key_id=api_key.id,
        )

    try:
        payload = decode_access_token(raw_token)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError, RuntimeError):
        raise unauthorized

    user = db.get(User, user_id)
    if user is None or not user.is_active or not user.email_verified:
        raise unauthorized
    return AuthContext(user=user, scopes=frozenset({"*"}), method="session")


def get_current_user(context: AuthContext = Depends(get_auth_context)) -> User:
    return context.user


def require_scopes(*required_scopes: str) -> Callable:
    def dependency(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if "*" in context.scopes:
            return context
        missing = set(required_scopes) - set(context.scopes)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": "Insufficient API key permissions", "required": sorted(missing)},
            )
        return context

    return dependency
