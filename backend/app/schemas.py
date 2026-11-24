from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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
