"""
Fix script - curăță datele de test și completează ce lipsește
"""
import sys, os, uuid, random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, '/app')
os.environ.setdefault('SECRET_KEY', 'seed-secret')
os.environ.setdefault('FERNET_KEY', '')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.doctor_patient import DoctorPatient
from app.models.appointment import Appointment, AppointmentStatus
from app.models.medical_record import MedicalRecord
from app.models.vital_sign import VitalSign
from app.models.prescription import Prescription
from app.models.review import Review
from app.models.message import Message

DATABASE_URL = 'postgresql://medilink_user:medilink_pass@db:5432/medilink'
engine  = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db      = Session()

def uid(): return uuid.uuid4()
def now(): return datetime.now(timezone.utc)
def days_ago(n, hour=10, minute=0):
    return (now() - timedelta(days=n)).replace(hour=hour, minute=minute, second=0, microsecond=0)
def days_from_now(n, hour=10, minute=0):
    return (now() + timedelta(days=n)).replace(hour=hour, minute=minute, second=0, microsecond=0)

# ── 1. Șterge mesajele de test ────────────────────────────────────────────────
bad_contents = [
    'Hai la control',
    'da mi control bai',
    'nu vreau sa vin ba nene',
]
deleted_msgs = 0
for content in bad_contents:
    rows = db.query(Message).filter(Message.content.ilike(f'%{content}%')).all()
    for r in rows:
        db.delete(r)
        deleted_msgs += 1
db.flush()
print(f'✓ Șters {deleted_msgs} mesaje de test')

# ── 2. Șterge recenzia de test ────────────────────────────────────────────────
bad_reviews = db.query(Review).filter(Review.comment.ilike('%patron%')).all()
# Also delete duplicate reviews (Alin Mincu has 2, keep the realistic one)
alin = db.query(Patient).join(User, Patient.user_id == User.id).filter(User.email == 'pacient@medilink.com').first()
if alin:
    alin_reviews = db.query(Review).filter(Review.patient_id == alin.id).order_by(Review.created_at).all()
    # Keep only the last (seed-generated), delete any test ones
    for rv in alin_reviews:
        if rv.comment and ('patron' in rv.comment.lower() or 'tare' in rv.comment.lower()):
            db.delete(rv)
            print(f'  Șters review test: {rv.comment[:50]}')

db.flush()
print('✓ Recenzii de test șterse')

# ── 3. Șterge prescripțiile de test și adaugă corecte ────────────────────────
bad_rx_keywords = ['Paracetamol', 'Droguri']
for kw in bad_rx_keywords:
    rows = db.query(Prescription).all()
    for rx in rows:
        meds = rx.medications
        if isinstance(meds, list):
            names = [m.get('name', '') for m in meds]
            if any(kw.lower() in n.lower() for n in names):
                db.delete(rx)
                print(f'  Șters prescripție test: {names}')

db.flush()
print('✓ Prescripții de test șterse')

# ── 4. Fix profiluri doctori (bio + schedule lipsă) ──────────────────────────
DOCTOR_UPDATES = {
    'doctor@medilink.com': {
        'bio': 'Medic primar neurolog cu 10 ani experiență clinică. Specializat în diagnosticul și tratamentul AVC, epilepsie și boli neurodegenerative. Colaborare cu centre universitare din București.',
        'schedule': 'Luni, Miercuri, Vineri: 09:00-17:00',
        'phone_cabinet': '021-310-2401',
        'department': 'Neurologie',
    },
    'doctor2@medilink.com': {
        'bio': 'Specialist cardiolog cu 15 ani experiență. Competențe în ecocardiografie, monitorizare Holter și managementul insuficienței cardiace.',
        'schedule': 'Luni-Joi: 08:00-16:00',
        'phone_cabinet': '021-310-2402',
        'department': 'Cardiologie',
    },
    'docto3r@medilink.com': {
        'bio': 'Medic specialist dermatolog. Experiență în dermatologie clinică și estetică, tratamentul psoriazisului, eczemelor și afecțiunilor cutanate complexe.',
        'schedule': 'Marți, Joi: 10:00-18:00',
        'phone_cabinet': '021-310-2403',
        'department': 'Dermatologie',
    },
    'doctor4@medilink.com': {
        'bio': 'Medic primar pediatru, specializată în bolile respiratorii pediatrice și nutriție. Peste 12 ani în practica clinică. Membră a Societății Române de Pediatrie.',
        'schedule': 'Luni-Vineri: 09:00-15:00',
        'phone_cabinet': '021-310-2404',
        'department': 'Pediatrie',
        'specialization': 'pediatrie',
    },
}

for email, updates in DOCTOR_UPDATES.items():
    u = db.query(User).filter(User.email == email).first()
    if not u:
        continue
    d = db.query(Doctor).filter(Doctor.user_id == u.id).first()
    if not d:
        continue
    for k, v in updates.items():
        setattr(d, k, v)

db.flush()
print('✓ Profiluri doctori completate (bio + schedule)')

# ── 5. Fix date lipsă utilizatori (Gigi Becali + Alin Mincu) ─────────────────
gigi = db.query(User).filter(User.email == 'doctor@medilink.com').first()
if gigi and not gigi.phone:
    gigi.phone = '0722100200'
    gigi.birth_date = '1966-02-05'
    gigi.address = 'Calea Victoriei nr. 155, București'

alin_u = db.query(User).filter(User.email == 'pacient@medilink.com').first()
if alin_u and not alin_u.phone:
    alin_u.phone = '0744123456'
    alin_u.birth_date = '1988-03-14'
    alin_u.address = 'Strada Florilor nr. 22, București'

admin_u = db.query(User).filter(User.email == 'admin@medilink.com').first()
if admin_u and not admin_u.phone:
    admin_u.phone = '0731000001'
    admin_u.birth_date = '1985-11-20'

db.flush()
print('✓ Date utilizatori completate')

# ── 6. Fix gender inconsistent Alin Mincu ────────────────────────────────────
if alin and alin.gender == 'Masculin':
    alin.gender = 'M'
    print('✓ Gender Alin Mincu corectat (Masculin -> M)')

# ── 7. Fix semne vitale imposibile pentru Alin Mincu ─────────────────────────
if alin:
    # Delete impossible vitals and re-add with sane values
    SANE_RANGES = {
        'pulse':               (58, 88),
        'weight':              (78, 82),
        'temperature':         (36.2, 37.2),
        'oxygen_sat':          (95, 99),
        'blood_pressure_sys':  (125, 155),
        'blood_pressure_dia':  (78, 98),
    }
    UNITS = {
        'pulse': 'bpm', 'weight': 'kg', 'temperature': '°C',
        'oxygen_sat': '%', 'blood_pressure_sys': 'mmHg', 'blood_pressure_dia': 'mmHg',
    }
    # Remove all Alin's vitals (they have garbage values)
    db.query(VitalSign).filter(VitalSign.patient_id == alin.id).delete()
    db.flush()
    # Re-create with sane values
    for day_offset in range(90, 0, -3):
        for vtype, (lo, hi) in SANE_RANGES.items():
            val = round(random.uniform(lo, hi), 1)
            vs = VitalSign(
                id=uid(), patient_id=alin.id, vital_type=vtype,
                value=val, unit=UNITS[vtype],
                recorded_at=days_ago(day_offset, hour=random.randint(7,20), minute=random.randint(0,59)),
            )
            db.add(vs)
    db.flush()
    print('✓ Semne vitale Alin Mincu refăcute cu valori normale')

# ── 8. Adaugă fișe medicale pentru pacienții fără ────────────────────────────
RECORD_TEMPLATES = [
    {
        'record_type': 'consultatie',
        'diagnosis': 'Hipertensiune arteriala stadiul II',
        'treatment': 'Amlodipina 5mg/zi, Losartan 50mg/zi, dieta hiposadata, miscare 30 min/zi',
        'notes': 'Pacient prezinta TA 160/100 mmHg. Se ajusteaza tratamentul antihipertensiv. Monitorizare la 4 saptamani.',
        'has_anomaly': True,
        'anomaly_notes': 'Tensiune arteriala crescuta — necesita monitorizare intensiva',
    },
    {
        'record_type': 'analiza',
        'diagnosis': None,
        'treatment': None,
        'analysis_result': 'Hemoglobina: 11.2 g/dL (scazut), Glicemie a jeun: 128 mg/dL (crescut), Colesterol total: 215 mg/dL, Trigliceride: 180 mg/dL',
        'notes': 'Profil lipidic usor alterat. Glicemie borderline — indicat TTGO.',
        'has_anomaly': True,
        'anomaly_notes': 'Anemie usoara si glicemie crescuta',
    },
    {
        'record_type': 'tratament',
        'diagnosis': 'Diabet zaharat tip 2 — echilibrat',
        'treatment': 'Metformin 1000mg x2/zi, Sitagliptin 100mg/zi, dieta diabetica, activitate fizica moderata',
        'notes': 'HbA1c 7.2% — satisfacator. Se continua schema actuala.',
        'has_anomaly': False,
    },
    {
        'record_type': 'investigatie',
        'diagnosis': 'Tahicardie sinusala',
        'treatment': None,
        'analysis_result': 'EKG: ritm sinusal, 98/min. Ecografie cord: FE 60%, regurgitare mitrala minima.',
        'notes': 'Ecocardiografie in limite normale. Se repeta EKG la 6 luni.',
        'has_anomaly': False,
    },
    {
        'record_type': 'consultatie',
        'diagnosis': 'Spondiloza cervicala cu radiculopatie C5-C6',
        'treatment': 'Ketoprofen 100mg la nevoie, Tolperizon 150mg x2, kinetoterapie 10 sedinte',
        'notes': 'Pacient cu dureri cervicale iradiante in membrul superior drept. IRM cervical recomandat.',
        'has_anomaly': True,
        'anomaly_notes': 'Radiculopatie — indicat IRM coloana cervicala',
    },
    {
        'record_type': 'analiza',
        'diagnosis': None,
        'treatment': None,
        'analysis_result': 'TSH: 5.8 mUI/L (crescut), FT4: 0.9 ng/dL (scazut), Anticorpi anti-TPO: pozitivi',
        'notes': 'Tiroidita autoimuna Hashimoto confirmata. Se initiaza tratament substitutiv.',
        'has_anomaly': True,
        'anomaly_notes': 'Hipotiroidism autoimun confirmat biologic',
    },
    {
        'record_type': 'reteta',
        'diagnosis': 'Astm bronsic persistent moderat',
        'treatment': 'Salbutamol spray 100mcg la nevoie, Fluticazona spray 250mcg x2/zi',
        'notes': 'Control astm — bun. Se continua terapia de intretinere. Spirometrie la 3 luni.',
        'has_anomaly': False,
    },
    {
        'record_type': 'consultatie',
        'diagnosis': 'Dislipidemie mixta',
        'treatment': 'Rosuvastatina 10mg/zi, dieta saraca in grasimi saturate, activitate fizica regulata',
        'notes': 'Colesterol LDL crescut. Se initiaza statina. Retestare lipidograma la 3 luni.',
        'has_anomaly': True,
        'anomaly_notes': 'LDL crescut — risc cardiovascular moderat',
    },
]

# Get patients without medical records
patients_without_records = []
all_patients = db.query(Patient).all()
for p in all_patients:
    cnt = db.query(MedicalRecord).filter(MedicalRecord.patient_id == p.id).count()
    if cnt == 0:
        patients_without_records.append(p)

print(f'  Pacienți fără fișe medicale: {len(patients_without_records)}')
for i, pat in enumerate(patients_without_records):
    dp = db.query(DoctorPatient).filter(DoctorPatient.patient_id == pat.id).first()
    if not dp:
        print(f'  SKIP: {pat.id} - nu are doctor asignat')
        continue
    doc = db.query(Doctor).filter(Doctor.id == dp.doctor_id).first()
    if not doc:
        continue

    for j in range(random.randint(2, 4)):
        tmpl = RECORD_TEMPLATES[(i * 3 + j) % len(RECORD_TEMPLATES)]
        mr = MedicalRecord(
            id=uid(),
            patient_id=pat.id,
            doctor_id=doc.user_id,
            record_type=tmpl['record_type'],
            diagnosis=tmpl.get('diagnosis'),
            treatment=tmpl.get('treatment'),
            analysis_result=tmpl.get('analysis_result'),
            notes_encrypted=tmpl.get('notes'),
            has_anomaly=tmpl.get('has_anomaly', False),
            anomaly_notes=tmpl.get('anomaly_notes'),
            created_at=days_ago(random.randint(1, 120)),
        )
        db.add(mr)

db.flush()
print('✓ Fișe medicale adăugate pentru pacienții lipsă')

# ── 9. Adaugă prescripții lipsă ──────────────────────────────────────────────
MEDS_MAP = {
    'pacient@medilink.com': [
        {'name': 'Amlodipina',  'dose': '5 mg',    'frequency': '1x/zi dimineata', 'duration': '30 zile', 'quantity': '30 comprimate'},
        {'name': 'Losartan',    'dose': '50 mg',    'frequency': '1x/zi seara',     'duration': '30 zile', 'quantity': '30 comprimate'},
    ],
    'pacient2@medilink.com': [
        {'name': 'Ketoprofen',  'dose': '100 mg',   'frequency': 'la nevoie, max 2x/zi dupa masa', 'duration': '10 zile', 'quantity': '20 comprimate'},
        {'name': 'Tolperizon',  'dose': '150 mg',   'frequency': '2x/zi',            'duration': '30 zile', 'quantity': '60 comprimate'},
        {'name': 'Omeprazol',   'dose': '20 mg',    'frequency': '1x/zi dimineata',  'duration': '30 zile', 'quantity': '30 capsule'},
    ],
    'pacient3@medilink.com': [
        {'name': 'Metformin',   'dose': '1000 mg',  'frequency': '2x/zi cu masa',    'duration': '90 zile', 'quantity': '180 comprimate'},
        {'name': 'Sitagliptin', 'dose': '100 mg',   'frequency': '1x/zi dimineata',  'duration': '90 zile', 'quantity': '90 comprimate'},
    ],
    'pacient4@medilink.com': [
        {'name': 'Levotiroxin', 'dose': '50 mcg',   'frequency': '1x/zi pe stomacul gol', 'duration': '60 zile', 'quantity': '60 comprimate'},
    ],
}

for email, meds in MEDS_MAP.items():
    u = db.query(User).filter(User.email == email).first()
    if not u:
        continue
    pat = db.query(Patient).filter(Patient.user_id == u.id).first()
    if not pat:
        continue
    # Check if already has a valid prescription (not the test ones we deleted)
    existing = db.query(Prescription).filter(Prescription.patient_id == pat.id).count()
    if existing > 0:
        continue
    dp = db.query(DoctorPatient).filter(DoctorPatient.patient_id == pat.id).first()
    if not dp:
        continue
    rx = Prescription(
        id=uid(),
        patient_id=pat.id,
        doctor_id=dp.doctor_id,
        medications=meds,
        notes='A se respecta dozajul prescris. Revenire la control dupa finalizarea tratamentului.',
        issued_at=days_ago(random.randint(1, 20)),
        created_at=days_ago(random.randint(1, 20)),
    )
    db.add(rx)

db.flush()
print('✓ Prescripții corecte adăugate')

# ── 10. Adaugă recenzii realiste pentru toți pacienții ───────────────────────
REVIEW_COMMENTS = [
    'Doctor foarte profesionist si empatic. A explicat clar diagnosticul si optiunile de tratament. Recomand cu caldura!',
    'Consultatie excelenta. Doctorul a luat in serios toate simptomele mele si a prescris un tratament eficient.',
    'Foarte multumit de ingrijire. A raspuns la toate intrebarile mele cu rabdare si profesionalism.',
    'Servicii de inalta calitate. Ma simt in siguranta sub supravegherea acestui medic.',
    'Medic dedicat si atent. Consultatie completa, explicatii clare. Va recomanda tuturor.',
]

used_appt_ids = set(
    r[0] for r in db.query(Review.appointment_id).all()
)

added_reviews = 0
for i, pat in enumerate(all_patients):
    dp = db.query(DoctorPatient).filter(DoctorPatient.patient_id == pat.id).first()
    if not dp:
        continue
    doc = db.query(Doctor).filter(Doctor.id == dp.doctor_id).first()
    if not doc:
        continue
    # Check if already has a valid review
    existing_rv = db.query(Review).filter(Review.patient_id == pat.id).count()
    if existing_rv > 0:
        continue
    # Find a completed appointment not yet reviewed
    appt = db.query(Appointment).filter(
        Appointment.patient_id == pat.id,
        Appointment.doctor_id == doc.user_id,
        Appointment.status == 'completed',
        ~Appointment.id.in_(used_appt_ids),
    ).first()
    if not appt:
        continue
    used_appt_ids.add(appt.id)
    rating = random.randint(4, 5)
    rev = Review(
        id=uid(),
        patient_id=pat.id,
        doctor_id=dp.doctor_id,
        appointment_id=appt.id,
        rating=rating,
        comment=REVIEW_COMMENTS[i % len(REVIEW_COMMENTS)],
        sentiment='pozitiv',
        created_at=appt.datetime + timedelta(hours=random.randint(2, 48)),
    )
    db.add(rev)
    added_reviews += 1

db.flush()
print(f'✓ {added_reviews} recenzii adăugate')

# ── Commit ────────────────────────────────────────────────────────────────────
db.commit()
print('\n✅ Fix complet!')

# ── Summary ───────────────────────────────────────────────────────────────────
print('\n📊 Rezumat final:')
for tbl in ['users','doctors','patients','doctor_patients','appointments','medical_records','vital_signs','prescriptions','reviews','messages']:
    cnt = db.execute(text(f'SELECT COUNT(*) FROM {tbl}')).scalar()
    print(f'   {tbl}: {cnt}')
