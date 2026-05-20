"""add reminder flags to appointments

Revision ID: fd4e5f6a7b8c
Revises: fc3d4e5f6a7b
Create Date: 2025-05-07 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'fd4e5f6a7b8c'
down_revision = 'fc3d4e5f6a7b'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('appointments', sa.Column('reminder_24h_sent', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('appointments', sa.Column('reminder_1h_sent', sa.Boolean(), server_default='false', nullable=True))

def downgrade() -> None:
    op.drop_column('appointments', 'reminder_1h_sent')
    op.drop_column('appointments', 'reminder_24h_sent')
