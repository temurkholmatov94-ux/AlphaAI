"""Add upstream provenance and discovery metrics.

Revision ID: 0002_hub_metadata
Revises: 0001_model_registry
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_hub_metadata"
down_revision = "0001_model_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("model_records", sa.Column("publisher", sa.String(length=255), nullable=True))
    op.add_column("model_records", sa.Column("downloads", sa.BigInteger(), nullable=True))
    op.add_column("model_records", sa.Column("likes", sa.Integer(), nullable=True))
    op.add_column("model_records", sa.Column("gated", sa.Boolean(), nullable=True))
    op.add_column("model_records", sa.Column("library_name", sa.String(length=100), nullable=True))
    op.add_column("model_records", sa.Column("upstream_revision", sa.String(length=64), nullable=True))
    op.add_column(
        "model_records",
        sa.Column("upstream_last_modified", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("model_records", "upstream_last_modified")
    op.drop_column("model_records", "upstream_revision")
    op.drop_column("model_records", "library_name")
    op.drop_column("model_records", "gated")
    op.drop_column("model_records", "likes")
    op.drop_column("model_records", "downloads")
    op.drop_column("model_records", "publisher")
