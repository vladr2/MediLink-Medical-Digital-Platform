"""add messages table

Revision ID: ge5f6a7b8c9d
Revises: fd4e5f6a7b8c
Create Date: 2025-05-07 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'ge5f6a7b8c9d'
down_revision = 'fd4e5f6a7b8c'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('sender_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('receiver_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_messages_sender_id', 'messages', ['sender_id'])
    op.create_index('ix_messages_receiver_id', 'messages', ['receiver_id'])

def downgrade() -> None:
    op.drop_index('ix_messages_receiver_id', 'messages')
    op.drop_index('ix_messages_sender_id', 'messages')
    op.drop_table('messages')
