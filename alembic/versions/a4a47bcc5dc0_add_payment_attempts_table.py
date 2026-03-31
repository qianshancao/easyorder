"""add_payment_attempts_table

Revision ID: a4a47bcc5dc0
Revises: 94bcc6bc46cd
Create Date: 2026-03-31 15:46:13.953128

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4a47bcc5dc0'
down_revision: Union[str, Sequence[str], None] = '94bcc6bc46cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'payment_attempts',
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('channel_transaction_id', sa.String(length=255), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_attempts_channel'), 'payment_attempts', ['channel'])
    op.create_index(op.f('ix_payment_attempts_order_id'), 'payment_attempts', ['order_id'])
    op.create_index(op.f('ix_payment_attempts_status'), 'payment_attempts', ['status'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_payment_attempts_status'), table_name='payment_attempts')
    op.drop_index(op.f('ix_payment_attempts_order_id'), table_name='payment_attempts')
    op.drop_index(op.f('ix_payment_attempts_channel'), table_name='payment_attempts')
    op.drop_table('payment_attempts')
