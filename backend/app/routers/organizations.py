from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Organization, OrganizationMembership, User
from app.schemas import OrganizationRead

router = APIRouter(prefix="/v1/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationRead])
def list_organizations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrganizationRead]:
    statement = (
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
        .where(OrganizationMembership.user_id == user.id)
        .order_by(Organization.created_at.asc())
    )
    return [
        OrganizationRead(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            role=role,
            created_at=organization.created_at,
        )
        for organization, role in db.execute(statement).all()
    ]
