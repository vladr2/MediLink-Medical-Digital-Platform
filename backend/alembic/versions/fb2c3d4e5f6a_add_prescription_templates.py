"""add prescription_templates table

Revision ID: fb2c3d4e5f6a
Revises: fa1b2c3d4e5f
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'fb2c3d4e5f6a'
down_revision = 'fa1b2c3d4e5f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'prescription_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('medications', postgresql.JSONB(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_prescription_templates_doctor_id', 'prescription_templates', ['doctor_id'])


def downgrade():
    op.drop_index('ix_prescription_templates_doctor_id', 'prescription_templates')
    op.drop_table('prescription_templates')
