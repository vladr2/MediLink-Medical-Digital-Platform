import sys, os, uuid, random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, '/app')
os.environ.setdefault('SECRET_KEY', 'seed-secret')
os.environ.setdefault('FERNET_KEY', '')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor_patient import DoctorPatient
from app.models.doctor import Doctor
from app.models.patient import Patient

engine = create_engine('postgresql://medilink_user:medilink_pass@db:5432/medilink')
db = sessionmaker(bind=engine)()

def uid(): return uuid.uuid4()
def now(): return datetime.now(timezone.utc)
def days_ago(n, hour=10, minute=0):
    return (now() - timedelta(days=n)).replace(hour=hour, minute=minute, second=0, microsecond=0)

REASONS_CANCELLED = [
    'Consultatie cardiologica periodica',
    'Control tensiune arteriala',
    'Reevaluare tratament',
    'Durere toracica — investigatii',
    'Analize sange de rutina',
    'Consultatie pentru diabet zaharat',
    'Dureri de cap persistente',
    'Control periodic',
    'Investigatii suplimentare',
    'Reevaluare spondiloze cervicale',
]

CANCEL_NOTES = [
    'Pacient a anulat din motive personale.',
    'Pacient a anulat — deplasare de serviciu.',
    'Anulat la cererea pacientului.',
    'Pacient indisponibil la data programata.',
    'Anulat — pacient a ales alta clinica.',
    'Anulat din motive medicale neprevazute.',
    None,
    None,
]

patients = db.query(Patient).all()
added = 0

for pat in patients:
    dps = db.query(DoctorPatient).filter(DoctorPatient.patient_id == pat.id).all()
    if not dps:
        continue

    # 2-3 cancelled per patient, spread over last 6 months
    n = random.randint(2, 3)
    for _ in range(n):
        dp = random.choice(dps)
        doc = db.query(Doctor).filter(Doctor.id == dp.doctor_id).first()
        if not doc:
            continue

        a = Appointment(
            id=uid(),
            patient_id=pat.id,
            doctor_id=doc.user_id,
            datetime=days_ago(
                random.randint(7, 180),
                hour=random.choice([9, 10, 11, 14, 15, 16]),
                minute=random.choice([0, 15, 30, 45]),
            ),
            status=AppointmentStatus.cancelled,
            reason=random.choice(REASONS_CANCELLED),
            notes=random.choice(CANCEL_NOTES),
            cancelled_by_patient=random.choice([True, False]),
        )
        db.add(a)
        added += 1

db.flush()
db.commit()
print(f'✓ Adaugate {added} programari anulate din trecut')

from sqlalchemy import text
with engine.connect() as conn:
    r = conn.execute(text('SELECT status, COUNT(*) FROM appointments GROUP BY status ORDER BY status'))
    print('\nProgramari dupa adaugare:')
    total = 0
    for row in r:
        print(f'  {row[0]}: {row[1]}')
        total += row[1]
    print(f'  TOTAL: {total}')
