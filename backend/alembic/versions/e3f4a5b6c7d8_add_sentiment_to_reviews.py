"""add sentiment to reviews

Revision ID: e3f4a5b6c7d8
Revises: d1e2f3a4b5c6
Create Date: 2026-05-02

Feature 14 — Analiză sentiment recenzii:
- Adaugă câmpul sentiment (pozitiv/negativ/neutru) la tabelul reviews
- Câmpul este nullable; se populează la crearea unei noi recenzii via Groq
"""

from alembic import op
import sqlalchemy as sa

revision = 'e3f4a5b6c7d8'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('reviews', sa.Column('sentiment', sa.String(20), nullable=True))


def downgrade():
    op.drop_column('reviews', 'sentiment')
