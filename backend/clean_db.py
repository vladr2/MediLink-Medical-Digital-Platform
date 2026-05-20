"""
Curăță programările de test și lasă doar unele corecte.
"""
import sys, os
sys.path.insert(0, '/app')
os.environ.setdefault('SECRET_KEY', 'seed-secret')
os.environ.setdefault('FERNET_KEY', '')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.appointment import Appointment

engine  = create_engine('postgresql://medilink_user:medilink_pass@db:5432/medilink')
db = sessionmaker(bind=engine)()

# ── Identifică programările de șters ──────────────────────────────────────────
# Criterii de test/gunoi:
#  1. notes sunt "a", "1", "code", "ada", "test", "cat mai repede" etc.
#  2. Fără reason ȘI notes ciudate
#  3. Doctor este admin (Alexia Radoi) - admin nu poate fi doctor
#  4. Datetime în viitor ÎNDEPĂRTAT (dec 2026) dar cancelled fără reason

BAD_NOTES = {'a', '1', 'code', 'ada', 'test', 'cat mai repede', 'dureri de cap'}

# Găsim user_id al adminului
admin_id = db.execute(text("SELECT id FROM users WHERE email='admin@medilink.com'")).scalar()

deleted = 0
all_appts = db.query(Appointment).all()
for a in all_appts:
    should_delete = False
    reason = a.reason

    # Fără reason și notes suspect
    notes_lower = (a.notes or '').strip().lower()
    if not reason and notes_lower in BAD_NOTES:
        should_delete = True

    # Fără reason și notes "Consultatie initiala" dar doctor e admin
    if str(a.doctor_id) == str(admin_id):
        should_delete = True

    # Cancelled în dec 2026 fără reason
    if a.status.value == 'cancelled' and not reason and a.datetime.year == 2026 and a.datetime.month == 12:
        should_delete = True

    if should_delete:
        print(f'  DELETE: [{a.status}] {str(a.datetime)[:16]} | reason={reason} | notes={a.notes}')
        db.delete(a)
        deleted += 1

db.flush()
print(f'\n✓ Șters {deleted} programări de test')

db.commit()

# Summar final
from sqlalchemy import text as t2
with engine.connect() as conn:
    r = conn.execute(t2('SELECT status, COUNT(*) FROM appointments GROUP BY status ORDER BY status'))
    print('\nProgramări rămase:')
    total = 0
    for row in r:
        print(f'  {row[0]}: {row[1]}')
        total += row[1]
    print(f'  TOTAL: {total}')
