"""Add compute worker registry.

Revision ID: 0006_compute_workers
Revises: 0005_model_pricing
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_compute_workers"
down_revision = "0005_model_pricing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compute_workers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("hardware_report", sa.JSON(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compute_workers_worker_id", "compute_workers", ["worker_id"], unique=True)
    op.create_index("ix_compute_workers_token_hash", "compute_workers", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_compute_workers_token_hash", table_name="compute_workers")
    op.drop_index("ix_compute_workers_worker_id", table_name="compute_workers")
    op.drop_table("compute_workers")
