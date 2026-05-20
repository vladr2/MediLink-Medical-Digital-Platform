"""
Curăță fișele medicale de test și completează cu date reale pentru toți pacienții.
"""
import sys, os, uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, '/app')
os.environ.setdefault('SECRET_KEY', 'seed-secret')
os.environ.setdefault('FERNET_KEY', '')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.doctor_patient import DoctorPatient
from app.models.medical_record import MedicalRecord
from app.models.prescription import Prescription

DATABASE_URL = 'postgresql://medilink_user:medilink_pass@db:5432/medilink'
engine  = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db      = Session()

def uid(): return uuid.uuid4()
def days_ago(n, hour=10, minute=0):
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=n)).replace(hour=hour, minute=minute, second=0, microsecond=0)

# ── 1. Șterge fișele de test ale lui Alin Mincu ──────────────────────────────
alin = db.query(User).filter(User.email == 'pacient@medilink.com').first()
alin_patient = db.query(Patient).filter(Patient.user_id == alin.id).first()

TEST_TREATMENTS = ['cristi', 'alexia', 'ceva', 'david']
TEST_ANALYSES   = ['test1']

deleted = 0
records = db.query(MedicalRecord).filter(MedicalRecord.patient_id == alin_patient.id).all()
for r in records:
    is_test = False
    # Câmpuri necriptate sau cu date triviale
    if r.treatment and r.treatment.strip() in TEST_TREATMENTS:
        is_test = True
    if r.analysis_result and r.analysis_result.strip() in TEST_ANALYSES:
        is_test = True
    # Diagnostice de test
    if r.diagnosis and r.diagnosis.strip() in ['s', 'b', 'Merge?']:
        is_test = True
    # Tratamente de test (b/c)
    if r.treatment and r.treatment.strip() in ['c', 'b']:
        is_test = True
    # Înregistrări complet goale (fără niciun câmp util)
    has_content = any([
        r.diagnosis and len(r.diagnosis.strip()) > 5,
        r.treatment and len(r.treatment.strip()) > 5,
        r.analysis_result and len(r.analysis_result.strip()) > 5,
        r.notes_encrypted and len(str(r.notes_encrypted).strip()) > 5,
    ])
    if not has_content:
        is_test = True

    if is_test:
        db.delete(r)
        deleted += 1

db.flush()
print(f'✓ Șters {deleted} fișe de test Alin Mincu')

# ── 2. Verifică ce tipuri există deja per pacient ─────────────────────────────
def existing_types(patient_id):
    recs = db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id).all()
    return set(r.record_type for r in recs)

# ── 3. Adaugă fișe logice unde lipsesc ───────────────────────────────────────
RECORDS_TO_ADD = {
    'pacient@medilink.com': [   # Alin Mincu
        {
            'record_type': 'consultatie',
            'diagnosis': 'Diabet zaharat tip 2 cu complicații incipiente',
            'treatment': 'Metformin 1000mg x2/zi, Sitagliptin 100mg/zi, dietă hipoglucidică, activitate fizică 30 min/zi',
            'notes': 'Pacient cunoscut cu diabet zaharat tip 2. HbA1c 7.8% — necesită optimizarea schemei terapeutice. Monitorizare glicemie zilnică.',
            'has_anomaly': True,
            'anomaly_notes': 'HbA1c crescut — control glicemic suboptimal',
            'days_ago': 45,
        },
        {
            'record_type': 'analiza',
            'analysis_result': 'Glicemie à jeun: 142 mg/dL (crescut), HbA1c: 7.8%, Creatinină: 1.1 mg/dL, eRFG: 78 mL/min/1.73m², Microalbuminurie: 35 mg/g (limită)',
            'notes': 'Profil metabolic alterat. Funcție renală la limită — necesită monitorizare. Se recomandă repetare la 3 luni.',
            'has_anomaly': True,
            'anomaly_notes': 'Glicemie crescută și microalbuminurie — risc nefropatie diabetică incipientă',
            'days_ago': 30,
        },
        {
            'record_type': 'tratament',
            'diagnosis': 'Boală coronariană stabilă',
            'treatment': 'Aspirină 100mg/zi, Atorvastatină 40mg seara, Bisoprolol 5mg/zi, Ramipril 5mg/zi',
            'notes': 'Continuarea tratamentului cardioprotector. Tensiunea arterială bine controlată la 130/80 mmHg. Se repetă EKG la 6 luni.',
            'has_anomaly': False,
            'days_ago': 20,
        },
    ],
    'ioana.popa@hotmail.com': [  # Ioana Popa
        {
            'record_type': 'analiza',
            'analysis_result': 'Spirometrie: VEMS/CVF 68% (obstructiv), VEMS 72% din valoarea prezisă. Test bronhodilatator: ameliorare 15%. IgE total: 320 UI/mL (crescut).',
            'notes': 'Astm bronșic alergic moderat persistent. Se optimizează tratamentul inhalator.',
            'has_anomaly': True,
            'anomaly_notes': 'Obstrucție bronșică moderată confirmată spirometric',
            'days_ago': 25,
        },
        {
            'record_type': 'tratament',
            'diagnosis': 'Astm bronșic alergic moderat persistent',
            'treatment': 'Fluticazonă/Salmeterol 250/25mcg x2/zi (inhalator), Montelukast 10mg seara, Salbutamol spray la nevoie',
            'notes': 'Schemă terapeutică ajustată. Pacienta instruită privind tehnica inhalatorie corectă. Evitarea alergenilor cunoscuți.',
            'has_anomaly': False,
            'days_ago': 15,
        },
    ],
}

added = 0
for email, rec_list in RECORDS_TO_ADD.items():
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f'  USER NOT FOUND: {email}')
        continue
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        print(f'  PATIENT NOT FOUND for {email}')
        continue

    dp = db.query(DoctorPatient).filter(DoctorPatient.patient_id == patient.id).first()
    if not dp:
        print(f'  NO DOCTOR ASSIGNED for {email}')
        continue
    doc = db.query(Doctor).filter(Doctor.id == dp.doctor_id).first()
    doc_user_id = doc.user_id

    ex = existing_types(patient.id)
    for rec_data in rec_list:
        # Nu duplica dacă există deja tipul (cu excepție: mai multe tratamente/consultații sunt OK)
        mr = MedicalRecord(
            id=uid(),
            patient_id=patient.id,
            doctor_id=doc_user_id,
            record_type=rec_data['record_type'],
            diagnosis=rec_data.get('diagnosis'),
            treatment=rec_data.get('treatment'),
            analysis_result=rec_data.get('analysis_result'),
            notes_encrypted=rec_data.get('notes'),
            has_anomaly=rec_data.get('has_anomaly', False),
            anomaly_notes=rec_data.get('anomaly_notes'),
            created_at=days_ago(rec_data['days_ago'], hour=14),
        )
        db.add(mr)
        added += 1

db.flush()
print(f'✓ Adăugate {added} fișe medicale noi')

# ── 4. Fix prescripție Alin Mincu — asigură că există ─────────────────────────
existing_rx = db.query(Prescription).filter(Prescription.patient_id == alin_patient.id).count()
if existing_rx == 0:
    dp = db.query(DoctorPatient).filter(DoctorPatient.patient_id == alin_patient.id).first()
    if dp:
        meds = [
            {"name": "Metformin", "dose": "1000 mg", "frequency": "2x/zi cu masa", "duration": "90 zile", "quantity": "180 comprimate"},
            {"name": "Sitagliptin", "dose": "100 mg", "frequency": "1x/zi dimineața", "duration": "90 zile", "quantity": "90 comprimate"},
            {"name": "Atorvastatină", "dose": "40 mg", "frequency": "1x/zi seara", "duration": "90 zile", "quantity": "90 comprimate"},
        ]
        rx = Prescription(
            id=uid(),
            patient_id=alin_patient.id,
            doctor_id=dp.doctor_id,
            medications=meds,
            notes="Tratament cronic. Monitorizare glicemie și profil lipidic la 3 luni.",
            issued_at=days_ago(20),
            created_at=days_ago(20),
        )
        db.add(rx)
        print('✓ Adăugată prescripție Alin Mincu')

db.commit()

# ── Sumar final ────────────────────────────────────────────────────────────────
print('\n📊 Fișe medicale per pacient:')
from sqlalchemy import func as sqlfunc
rows = db.execute(text('''
    SELECT u.first_name, u.last_name, mr.record_type, COUNT(*) as cnt
    FROM medical_records mr
    JOIN patients p ON mr.patient_id = p.id
    JOIN users u ON p.user_id = u.id
    GROUP BY u.first_name, u.last_name, mr.record_type
    ORDER BY u.last_name, mr.record_type
''')).fetchall()
for r in rows:
    print(f'  {r[0]} {r[1]}: [{r[2]}] x{r[3]}')
