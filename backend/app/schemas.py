from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class RegisterResponse(BaseModel):
    user_id: int
    email: EmailStr
    status: str
    verification_required: bool
    development_verification_token: str | None = None


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    email_verified: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    user: UserRead


class OrganizationRead(BaseModel):
    id: int
    name: str
    slug: str
    role: str
    created_at: datetime


ALLOWED_API_SCOPES = {"models:read", "inference:run", "usage:read"}


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    scopes: list[str] = Field(min_length=1, max_length=10)
    expires_in_days: int | None = Field(default=90, ge=1, le=365)

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, scopes: list[str]) -> list[str]:
        normalized = sorted(set(scopes))
        unknown = set(normalized) - ALLOWED_API_SCOPES
        if unknown:
            raise ValueError(f"Unsupported scopes: {', '.join(sorted(unknown))}")
        if not normalized:
            raise ValueError("At least one scope is required")
        return normalized


class APIKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    key_prefix: str
    scopes: list[str]
    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class APIKeyCreated(APIKeyRead):
    api_key: str


class ModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_id: str
    display_name: str
    provider: str
    publisher: str | None
    source_url: str | None
    description: str | None
    license_id: str | None
    license_status: str
    access_method: str
    availability_status: str
    tasks: list[str]
    modalities: list[str]
    context_window: int | None
    weights_available: bool
    downloads: int | None
    likes: int | None
    gated: bool | None
    library_name: str | None
    upstream_revision: str | None
    upstream_last_modified: datetime | None
    last_verified_at: datetime | None


class ModelListResponse(BaseModel):
    items: list[ModelRead]
    total: int
    limit: int
    offset: int


class ModelCreate(BaseModel):
    model_id: str = Field(min_length=2, max_length=255, pattern=r"^[A-Za-z0-9._:/-]+$")
    display_name: str = Field(min_length=1, max_length=255)
    provider: str = Field(min_length=1, max_length=100)
    source_url: HttpUrl | None = None
    description: str | None = Field(default=None, max_length=10000)
    license_id: str | None = Field(default=None, max_length=100)
    license_status: str = "unknown"
    access_method: str = "unknown"
    availability_status: str = "discovered"
    tasks: list[str] = Field(default_factory=list, max_length=40)
    modalities: list[str] = Field(default_factory=list, max_length=20)
    context_window: int | None = Field(default=None, ge=1, le=10_000_000)
    weights_available: bool = False


class ModelFilter(BaseModel):
    q: str | None = Field(default=None, max_length=120)
