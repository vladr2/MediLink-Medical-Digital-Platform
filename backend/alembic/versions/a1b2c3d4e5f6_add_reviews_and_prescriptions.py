"""add reviews and prescriptions tables

Revision ID: a1b2c3d4e5f6
Revises: 9b6f47c15e03
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b2c3d4e5f6'
down_revision = '9b6f47c15e03'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('appointments.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_reviews_patient_id', 'reviews', ['patient_id'])
    op.create_index('ix_reviews_doctor_id',  'reviews', ['doctor_id'])

    op.create_table(
        'prescriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('appointments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('medications', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('issued_at',  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_prescriptions_patient_id', 'prescriptions', ['patient_id'])
    op.create_index('ix_prescriptions_doctor_id',  'prescriptions', ['doctor_id'])


def downgrade() -> None:
    op.drop_table('prescriptions')
    op.drop_table('reviews')
