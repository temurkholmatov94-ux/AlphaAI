"""Track evidence for model weight availability.

Revision ID: 0008_model_weight_status
Revises: 0007_worker_benchmarks
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_model_weight_status"
down_revision = "0007_worker_benchmarks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_records",
        sa.Column("weights_status", sa.String(length=24), nullable=False, server_default="unknown"),
    )


def downgrade() -> None:
    op.drop_column("model_records", "weights_status")
