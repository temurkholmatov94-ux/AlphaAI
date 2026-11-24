"""One-time interactive bootstrap for the first platform administrator.

Run inside the deployed API environment:
    python -m app.bootstrap_admin

The administrator email must already be present in ALPHAAI_ADMIN_EMAILS.
The password is entered with terminal echo disabled and is never printed.
"""
from __future__ import annotations

import getpass
import re
import sys
from uuid import uuid4

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import AuditEvent, Organization, OrganizationMembership, UsageAccount, User
from app.security import hash_password


def main() -> int:
    settings = get_settings()
    allowed = {address.strip().lower() for address in settings.alphaai_admin_emails if address.strip()}
    if not allowed:
        print("ERROR: ALPHAAI_ADMIN_EMAILS is empty. Configure it as a JSON array in Render first.")
        return 2

    email = input("Administrator email: ").strip().lower()
    if email not in allowed:
        print("ERROR: This email is not in ALPHAAI_ADMIN_EMAILS. No account was created.")
        return 2
    if not re.fullmatch(r"[^@\\s]+@[^@\\s]+\\.[^@\\s]+", email):
        print("ERROR: Enter a valid email address.")
        return 2

    password = getpass.getpass("New administrator password (12+ characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if len(password) < 12 or len(password) > 128:
        print("ERROR: Password must contain 12–128 characters.")
        return 2
    if password != confirm:
        print("ERROR: Passwords do not match.")
        return 2

    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            print("ERROR: An account with this email already exists. No changes were made.")
            return 3

        user = User(
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        db.flush()

        organization = Organization(
            name=f"{email.split('@', 1)[0]}'s workspace",
            slug=f"workspace-{uuid4().hex[:12]}",
            created_by_user_id=user.id,
        )
        db.add(organization)
        db.flush()
        db.add(OrganizationMembership(user_id=user.id, organization_id=organization.id, role="owner"))
        db.add(UsageAccount(organization_id=organization.id, budget_limit_microusd=0, enabled=False))
        db.add(
            AuditEvent(
                actor_user_id=user.id,
                action="identity.admin_bootstrapped",
                resource_type="user",
                resource_id=str(user.id),
                details={"organization_id": organization.id, "email_verified": True},
            )
        )
        db.commit()

    password = ""
    confirm = ""
    print(f"SUCCESS: Administrator account created and verified for {email}.")
    print("You can now sign in at /admin. Your password was not displayed or stored in plaintext.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
