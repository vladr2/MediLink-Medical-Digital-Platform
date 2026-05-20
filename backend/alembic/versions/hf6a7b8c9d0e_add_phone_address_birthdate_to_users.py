"""add phone address birthdate to users

Revision ID: hf6a7b8c9d0e
Revises: c7d8e9f0a1b2
Create Date: 2026-05-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'hf6a7b8c9d0e'
down_revision: Union[str, Sequence[str], None] = 'ge5f6a7b8c9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS address VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date VARCHAR")


def downgrade() -> None:
    op.drop_column('users', 'phone')
    op.drop_column('users', 'address')
    op.drop_column('users', 'birth_date')
