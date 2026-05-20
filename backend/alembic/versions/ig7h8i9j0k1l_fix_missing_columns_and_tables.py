"""fix missing columns and tables

Revision ID: ig7h8i9j0k1l
Revises: hf6a7b8c9d0e
Create Date: 2026-05-20 00:00:00.000000

Adds all columns/tables that exist in models but were never created
by any previous migration, causing fresh-DB failures.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'ig7h8i9j0k1l'
down_revision: Union[str, Sequence[str], None] = 'hf6a7b8c9d0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── doctors: add phone_cabinet and schedule ──────────────────────────────
    op.execute("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS phone_cabinet VARCHAR")
    op.execute("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS schedule VARCHAR")

    # ── patients: add emergency_contact and emergency_phone ──────────────────
    op.execute("ALTER TABLE patients ADD COLUMN IF NOT EXISTS emergency_contact VARCHAR")
    op.execute("ALTER TABLE patients ADD COLUMN IF NOT EXISTS emergency_phone VARCHAR")

    # ── audit_logs: create if not exists ────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID,
            user_email VARCHAR,
            action VARCHAR NOT NULL,
            resource VARCHAR,
            details TEXT,
            ip_address VARCHAR,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    # ── doctor_patient: create if not exists ─────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS doctor_patient (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
            patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
            assigned_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_doctor_patient
        ON doctor_patient (doctor_id, patient_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_doctor_patient")
    op.execute("DROP TABLE IF EXISTS doctor_patient")
    op.execute("DROP TABLE IF EXISTS audit_logs")
    op.drop_column('patients', 'emergency_phone')
    op.drop_column('patients', 'emergency_contact')
    op.drop_column('doctors', 'schedule')
    op.drop_column('doctors', 'phone_cabinet')
