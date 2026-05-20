"""add vital_signs table

Revision ID: fc3d4e5f6a7b
Revises: fb2c3d4e5f6a
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'fc3d4e5f6a7b'
down_revision = 'fb2c3d4e5f6a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'vital_signs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vital_type', sa.String(50), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.create_index('ix_vital_signs_patient_id', 'vital_signs', ['patient_id'])


def downgrade():
    op.drop_index('ix_vital_signs_patient_id', 'vital_signs')
    op.drop_table('vital_signs')
