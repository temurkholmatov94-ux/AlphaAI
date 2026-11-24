"""Create initial model registry table.

Revision ID: 0001_model_registry
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_model_registry"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("license_id", sa.String(length=100), nullable=True),
        sa.Column("license_status", sa.String(length=32), nullable=False),
        sa.Column("access_method", sa.String(length=32), nullable=False),
        sa.Column("availability_status", sa.String(length=32), nullable=False),
        sa.Column("tasks", sa.JSON(), nullable=False),
        sa.Column("modalities", sa.JSON(), nullable=False),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("weights_available", sa.Boolean(), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_records_model_id", "model_records", ["model_id"], unique=True)
    op.create_index("ix_model_records_display_name", "model_records", ["display_name"])
    op.create_index("ix_model_records_provider", "model_records", ["provider"])
    op.create_index("ix_model_records_license_status", "model_records", ["license_status"])
    op.create_index("ix_model_records_availability_status", "model_records", ["availability_status"])


def downgrade() -> None:
    op.drop_index("ix_model_records_availability_status", table_name="model_records")
    op.drop_index("ix_model_records_license_status", table_name="model_records")
    op.drop_index("ix_model_records_provider", table_name="model_records")
    op.drop_index("ix_model_records_display_name", table_name="model_records")
    op.drop_index("ix_model_records_model_id", table_name="model_records")
    op.drop_table("model_records")
