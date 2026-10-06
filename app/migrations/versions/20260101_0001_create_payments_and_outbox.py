"""create payments and outbox

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'payments',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('amount', sa.DECIMAL(15, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('idempotency_key', sa.String(255), nullable=False),
        sa.Column('request_hash', sa.String(64), nullable=False),
        sa.Column('webhook_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('idempotency_key', name='uq_payments_idempotency_key'),
    )
    op.create_index('ix_payments_status', 'payments', ['status'])

    op.create_table(
        'outbox',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_outbox_pending',
        'outbox',
        ['created_at'],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index('ix_outbox_pending', table_name='outbox')
    op.drop_table('outbox')
    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_table('payments')
