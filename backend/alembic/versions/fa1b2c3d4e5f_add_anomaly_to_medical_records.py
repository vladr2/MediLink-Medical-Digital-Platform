"""add anomaly to medical_records

Revision ID: fa1b2c3d4e5f
Revises: e3f4a5b6c7d8
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa

revision = 'fa1b2c3d4e5f'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('medical_records', sa.Column('has_anomaly', sa.Boolean(), nullable=True))
    op.add_column('medical_records', sa.Column('anomaly_notes', sa.String(500), nullable=True))


def downgrade():
    op.drop_column('medical_records', 'anomaly_notes')
    op.drop_column('medical_records', 'has_anomaly')
