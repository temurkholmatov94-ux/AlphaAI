"""Add conservative model identity hints.

Revision ID: 0009_model_identity_hints
Revises: 0008_model_weight_status
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_model_identity_hints"
revises = None
down_revision = "0008_model_weight_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("model_records", sa.Column("publisher_namespace", sa.String(length=255), nullable=True))
    op.add_column("model_records", sa.Column("canonical_name", sa.String(length=255), nullable=True))
    op.add_column("model_records", sa.Column("variant_type", sa.String(length=32), nullable=False, server_default="unknown"))
    op.add_column("model_records", sa.Column("identity_status", sa.String(length=24), nullable=False, server_default="unreviewed"))
    op.create_index("ix_model_records_publisher_namespace", "model_records", ["publisher_namespace"])
    op.create_index("ix_model_records_canonical_name", "model_records", ["canonical_name"])


def downgrade() -> None:
    op.drop_index("ix_model_records_canonical_name", table_name="model_records")
    op.drop_index("ix_model_records_publisher_namespace", table_name="model_records")
    op.drop_column("model_records", "identity_status")
    op.drop_column("model_records", "variant_type")
    op.drop_column("model_records", "canonical_name")
    op.drop_column("model_records", "publisher_namespace")
