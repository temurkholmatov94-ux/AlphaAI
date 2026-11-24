"""Add versioned model pricing table.

Revision ID: 0005_model_pricing
Revises: 0004_usage_ledger
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_model_pricing"
down_revision = "0004_usage_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_pricing",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("input_microusd_per_million_tokens", sa.BigInteger(), nullable=False),
        sa.Column("output_microusd_per_million_tokens", sa.BigInteger(), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "model_id", "effective_from", name="uq_model_pricing_version"),
    )
    op.create_index(
        "ix_model_pricing_provider_model_active",
        "model_pricing",
        ["provider", "model_id", "active"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_pricing_provider_model_active", table_name="model_pricing")
    op.drop_table("model_pricing")
