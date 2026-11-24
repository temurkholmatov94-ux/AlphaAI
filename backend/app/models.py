from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModelRecord(Base):
    __tablename__ = "model_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), index=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    license_status: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    access_method: Mapped[str] = mapped_column(String(32), default="unknown")
    availability_status: Mapped[str] = mapped_column(String(32), default="discovered", index=True)
    tasks: Mapped[list] = mapped_column(JSON, default=list)
    modalities: Mapped[list] = mapped_column(JSON, default=list)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weights_available: Mapped[bool] = mapped_column(Boolean, default=False)
    downloads: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    likes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    library_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    upstream_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    upstream_last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
