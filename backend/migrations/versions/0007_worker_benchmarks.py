"""Add worker benchmark results.

Revision ID: 0007_worker_benchmarks
Revises: 0006_compute_workers
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_worker_benchmarks"
down_revision = "0006_compute_workers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worker_benchmarks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("worker_id", sa.Integer(), nullable=False),
        sa.Column("benchmark_name", sa.String(length=80), nullable=False),
        sa.Column("benchmark_version", sa.String(length=40), nullable=False),
        sa.Column("device_name", sa.String(length=120), nullable=False),
        sa.Column("device_vram_bytes", sa.BigInteger(), nullable=False),
        sa.Column("matrix_size", sa.Integer(), nullable=False),
        sa.Column("repetitions", sa.Integer(), nullable=False),
        sa.Column("average_latency_ms", sa.Float(), nullable=False),
        sa.Column("estimated_fp32_tflops", sa.Float(), nullable=False),
        sa.Column("measurement_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["worker_id"], ["compute_workers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worker_benchmarks_worker_id", "worker_benchmarks", ["worker_id"])
    op.create_index("ix_worker_benchmarks_worker_created", "worker_benchmarks", ["worker_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_worker_benchmarks_worker_created", table_name="worker_benchmarks")
    op.drop_index("ix_worker_benchmarks_worker_id", table_name="worker_benchmarks")
    op.drop_table("worker_benchmarks")
