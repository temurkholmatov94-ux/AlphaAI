"""Add organization usage accounts and reservation ledger.

Revision ID: 0004_usage_ledger
Revises: 0003_identity
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_usage_ledger"
down_revision = "0003_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("budget_limit_microusd", sa.BigInteger(), nullable=False),
        sa.Column("reserved_microusd", sa.BigInteger(), nullable=False),
        sa.Column("spent_microusd", sa.BigInteger(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", name="uq_usage_account_organization"),
    )
    op.create_index("ix_usage_accounts_organization_id", "usage_accounts", ["organization_id"])

    op.create_table(
        "usage_reservations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usage_account_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("estimated_microusd", sa.BigInteger(), nullable=False),
        sa.Column("actual_microusd", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usage_account_id"], ["usage_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usage_account_id", "idempotency_key", name="uq_usage_reservation_idempotency"),
    )
    op.create_index("ix_usage_reservations_usage_account_id", "usage_reservations", ["usage_account_id"])
    op.create_index("ix_usage_reservations_status", "usage_reservations", ["status"])
    op.create_index("ix_usage_reservations_account_status", "usage_reservations", ["usage_account_id", "status"])

    op.create_table(
        "usage_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usage_account_id", sa.Integer(), nullable=False),
        sa.Column("reservation_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("input_tokens", sa.BigInteger(), nullable=False),
        sa.Column("output_tokens", sa.BigInteger(), nullable=False),
        sa.Column("cost_microusd", sa.BigInteger(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["usage_account_id"], ["usage_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reservation_id"], ["usage_reservations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id"),
    )
    op.create_index("ix_usage_events_usage_account_id", "usage_events", ["usage_account_id"])


def downgrade() -> None:
    op.drop_index("ix_usage_events_usage_account_id", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_index("ix_usage_reservations_account_status", table_name="usage_reservations")
    op.drop_index("ix_usage_reservations_status", table_name="usage_reservations")
    op.drop_index("ix_usage_reservations_usage_account_id", table_name="usage_reservations")
    op.drop_table("usage_reservations")
    op.drop_index("ix_usage_accounts_organization_id", table_name="usage_accounts")
    op.drop_table("usage_accounts")
