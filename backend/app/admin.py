from fastapi import Depends, HTTPException, status

from app.config import get_settings
from app.dependencies import get_current_user
from app.models import User


def require_platform_admin(user: User = Depends(get_current_user)) -> User:
    """Bootstrap platform admin using an explicit server-side email allowlist."""
    configured = {
        address.strip().lower()
        for address in get_settings().alphaai_admin_emails
        if address.strip()
    }
    if not configured or user.email.strip().lower() not in configured:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access is required",
        )
    return user
