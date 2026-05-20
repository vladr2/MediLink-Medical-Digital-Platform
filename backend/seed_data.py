"""
MediLink – script populare date realiste românești
Rulează în containerul backend: python seed_data.py
"""
import uuid, random
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ── DB connection ─────────────────────────────────────────────────────────────
DATABASE_URL = "postgresql://medilink_user:medilink_pass@db:5432/medilink"
engine  = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db      = Session()

def uid(): return uuid.uuid4()
def now(): return datetime.now(timezone.utc)
def days_ago(n, hour=10, minute=0):
    return (now() - timedelta(days=n)).replace(hour=hour, minute=minute, second=0, microsecond=0)
def days_from_now(n, hour=10, minute=0):
    return (now() + timedelta(days=n)).replace(hour=hour, minute=minute, second=0, microsecond=0)

# ── Importuri modele ──────────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, '/app')
os.environ.setdefault('SECRET_KEY', 'seed-secret-key-not-used-in-prod')
os.environ.setdefault('FERNET_KEY', '')

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

# ── Fetch existing users ──────────────────────────────────────────────────────
def get_users_by_role(role):
    return db.query(User).filter(User.role == role, User.is_active == True).all()

doctors_u   = get_users_by_role('doctor')
patients_u  = get_users_by_role('patient')
assistants_u= get_users_by_role('assistant')
admins_u    = get_users_by_role('admin')

print(f"Found: {len(doctors_u)} doctors, {len(patients_u)} patients, {len(assistants_u)} assistants, {len(admins_u)} admins")

# ── 1. Actualizare nume utilizatori existenți ─────────────────────────────────
DOCTOR_NAMES = [
    ("Alexandru", "Ionescu"),
    ("Maria",     "Popescu"),
    ("Radu",      "Constantin"),
    ("Elena",     "Dumitrescu"),
    ("Mihai",     "Georgescu"),
]
PATIENT_NAMES = [
    ("Andrei",    "Marinescu"),
    ("Ioana",     "Popa"),
    ("Cristian",  "Tudose"),
    ("Luminița",  "Niculescu"),
    ("Bogdan",    "Stan"),
    ("Raluca",    "Munteanu"),
]
ASSISTANT_NAMES = [
    ("Daniela",   "Vlad"),
    ("Sorin",     "Negru"),
]

def update_user_name(user, first, last, phone, birth, address):
    user.first_name = first
    user.last_name  = last
    user.phone      = phone
    user.birth_date = birth
    user.address    = address

phones = [f"07{random.randint(10,99)}{random.randint(100000,999999)}" for _ in range(20)]

for i, u in enumerate(doctors_u):
    fn, ln = DOCTOR_NAMES[i % len(DOCTOR_NAMES)]
    # Keep Gigi Becali if already set
    if not u.first_name:
        update_user_name(u, fn, ln, phones[i], f"19{random.randint(60,85)}-0{random.randint(1,9)}-{random.randint(10,28):02d}", "Strada Medicilor nr." + str(random.randint(1,50)) + ", București")

for i, u in enumerate(patients_u):
    fn, ln = PATIENT_NAMES[i % len(PATIENT_NAMES)]
    if not u.first_name:
        update_user_name(u, fn, ln, phones[10+i], f"19{random.randint(70,99)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}", "Strada Florilor nr." + str(random.randint(1,100)) + ", București")

for i, u in enumerate(assistants_u):
    fn, ln = ASSISTANT_NAMES[i % len(ASSISTANT_NAMES)]
    if not u.first_name:
        update_user_name(u, fn, ln, phones[5+i], f"198{random.randint(0,9)}-0{random.randint(1,9)}-{random.randint(10,28):02d}", "Bulevardul Spitalelor nr." + str(random.randint(1,30)) + ", București")

db.flush()
print("✓ Nume utilizatori actualizate")

# ── 2. Profiluri doctori ──────────────────────────────────────────────────────
DOCTOR_PROFILES = [
    {
        "specialization": "cardiologie",
        "license_number": "CMR-2024-001",
        "department": "Cardiologie",
        "bio": "Specialist în boli cardiovasculare cu peste 15 ani experiență. Competențe în ecocardiografie, monitorizare Holter și intervenții percutane.",
        "phone_cabinet": "021-310-2401",
        "schedule": "Luni-Vineri: 09:00-17:00",
    },
    {
        "specialization": "neurologie",
        "license_number": "CMR-2024-002",
        "department": "Neurologie",
        "bio": "Medic primar neurolog, experiență în diagnosticul și tratamentul AVC, epilepsie și boli neurodegenerative.",
        "phone_cabinet": "021-310-2402",
        "schedule": "Luni, Miercuri, Vineri: 08:00-16:00",
    },
    {
        "specialization": "pediatrie",
        "license_number": "CMR-2024-003",
        "department": "Pediatrie",
        "bio": "Medic primar pediatru cu specializare în boli respiratorii pediatrice și nutriție. Peste 12 ani în practica clinică.",
        "phone_cabinet": "021-310-2403",
        "schedule": "Luni-Joi: 10:00-18:00",
    },
    {
        "specialization": "medicina interna",
        "license_number": "CMR-2024-004",
        "department": "Medicină Internă",
        "bio": "Specialist în medicină internă, management boli cronice, diabet și afecțiuni reumatologice.",
        "phone_cabinet": "021-310-2404",
        "schedule": "Marți-Sâmbătă: 09:00-15:00",
    },
    {
        "specialization": "ortopedie",
        "license_number": "CMR-2024-005",
        "department": "Ortopedie",
        "bio": "Chirurg ortoped, specializat în artroplastie de șold și genunchi, traumatologie sportivă.",
        "phone_cabinet": "021-310-2405",
        "schedule": "Luni, Joi: 08:00-14:00",
    },
]

doctor_profiles = {}  # user_id -> Doctor object
for i, u in enumerate(doctors_u):
    existing = db.query(Doctor).filter(Doctor.user_id == u.id).first()
    if not existing:
        prof_data = DOCTOR_PROFILES[i % len(DOCTOR_PROFILES)]
        # Make license unique based on user index
        lic = prof_data["license_number"].replace("001", f"{i+1:03d}")
        d = Doctor(
            id=uid(),
            user_id=u.id,
            specialization=prof_data["specialization"],
            license_number=lic,
            department=prof_data["department"],
            bio=prof_data["bio"],
            phone_cabinet=prof_data["phone_cabinet"],
            schedule=prof_data["schedule"],
        )
        db.add(d)
        db.flush()
        doctor_profiles[str(u.id)] = d
    else:
        doctor_profiles[str(u.id)] = existing

db.flush()
print("✓ Profiluri doctori create")

# ── 3. Profiluri pacienți ─────────────────────────────────────────────────────
PATIENT_DATA = [
    {"blood_type": "A+",  "allergies": "Penicilină", "chronic": "Hipertensiune arterială, Diabet zaharat tip 2", "gender": "M"},
    {"blood_type": "O-",  "allergies": "Niciuna",    "chronic": "Astm bronșic", "gender": "F"},
    {"blood_type": "B+",  "allergies": "Ibuprofen",  "chronic": "Hipotiroidism", "gender": "M"},
    {"blood_type": "AB+", "allergies": "Niciuna",    "chronic": "Fără afecțiuni cronice cunoscute", "gender": "F"},
    {"blood_type": "A-",  "allergies": "Sulfonamide","chronic": "Boală coronariană, Dislipidemie", "gender": "M"},
    {"blood_type": "O+",  "allergies": "Aspirină",   "chronic": "Spondiloză cervicală", "gender": "F"},
]

patient_profiles = {}  # user_id -> Patient object
for i, u in enumerate(patients_u):
    existing = db.query(Patient).filter(Patient.user_id == u.id).first()
    if not existing:
        pd_data = PATIENT_DATA[i % len(PATIENT_DATA)]
        p = Patient(
            id=uid(),
            user_id=u.id,
            blood_type=pd_data["blood_type"],
            allergies=pd_data["allergies"],
            chronic_conditions=pd_data["chronic"],
            gender=pd_data["gender"],
            emergency_contact=f"{u.first_name or 'Contact'} Urgență",
            emergency_phone=f"07{random.randint(10,99)}{random.randint(100000,999999)}",
            gdpr_consent_at=days_ago(random.randint(30, 365)),
        )
        db.add(p)
        db.flush()
        patient_profiles[str(u.id)] = p
    else:
        patient_profiles[str(u.id)] = existing

db.flush()
print("✓ Profiluri pacienți create")

# ── Collect lists ─────────────────────────────────────────────────────────────
doctor_list  = list(doctor_profiles.values())   # Doctor objects
patient_list = list(patient_profiles.values())  # Patient objects

# ── 4. Atribuire pacienți la doctori ──────────────────────────────────────────
# Each patient gets 1-2 doctors; distribute evenly
assignments = []
for i, pat in enumerate(patient_list):
    primary_doc = doctor_list[i % len(doctor_list)]
    existing = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == primary_doc.id,
        DoctorPatient.patient_id == pat.id
    ).first()
    if not existing:
        dp = DoctorPatient(doctor_id=primary_doc.id, patient_id=pat.id)
        db.add(dp)
        assignments.append((primary_doc, pat))

    # Assign some patients to a second doctor
    if i % 3 == 0 and len(doctor_list) > 1:
        sec_doc = doctor_list[(i + 1) % len(doctor_list)]
        existing2 = db.query(DoctorPatient).filter(
            DoctorPatient.doctor_id == sec_doc.id,
            DoctorPatient.patient_id == pat.id
        ).first()
        if not existing2:
            dp2 = DoctorPatient(doctor_id=sec_doc.id, patient_id=pat.id)
            db.add(dp2)

db.flush()
print(f"✓ {len(assignments)} atribuiri doctor-pacient create")

# ── 5. Programări ─────────────────────────────────────────────────────────────
REASONS = [
    "Consultație cardiologică periodică",
    "Control tensiune arterială",
    "Durere toracică — investigații",
    "Consultație pentru diabet zaharat",
    "Reevaluare tratament hipertensiune",
    "Dureri de cap persistente — neurologie",
    "Control EEG și evaluare epilepsie",
    "Consultație pediatrică — tuse persistentă",
    "Febră recurentă la copil",
    "Dureri articulare — evaluare ortopedie",
    "Reevaluare spondiloză cervicală",
    "Analize sânge și urinare de rutină",
    "Reînnoire prescripție medicație cronică",
    "Consultație medicină internă — oboseală cronică",
    "Investigații pentru hipotiroidism",
]

created_appointments = []
existing_appt_count = db.query(Appointment).count()

if existing_appt_count < 5:
    for pat in patient_list:
        # Get doctor for this patient
        dp = db.query(DoctorPatient).filter(DoctorPatient.patient_id == pat.id).first()
        if not dp:
            continue
        doc_user_id = db.query(Doctor).filter(Doctor.id == dp.doctor_id).first().user_id

        # Past completed appointments (2-3 per patient)
        for k in range(random.randint(2, 3)):
            d_ago = random.randint(5, 90)
            appt = Appointment(
                id=uid(),
                patient_id=pat.id,
                doctor_id=doc_user_id,
                datetime=days_ago(d_ago, hour=random.choice([9,10,11,14,15,16]), minute=random.choice([0,15,30,45])),
                status=AppointmentStatus.completed,
                reason=random.choice(REASONS),
                notes="Pacient s-a prezentat la timp. Consultație efectuată.",
            )
            db.add(appt)
            created_appointments.append(appt)

        # Upcoming confirmed
        for k in range(random.randint(1, 2)):
            d_fwd = random.randint(1, 21)
            appt = Appointment(
                id=uid(),
                patient_id=pat.id,
                doctor_id=doc_user_id,
                datetime=days_from_now(d_fwd, hour=random.choice([9,10,11,14,15,16]), minute=random.choice([0,15,30,45])),
                status=AppointmentStatus.confirmed,
                reason=random.choice(REASONS),
            )
            db.add(appt)
            created_appointments.append(appt)

        # Pending (for assistant dashboard queue)
        appt_pend = Appointment(
            id=uid(),
            patient_id=pat.id,
            doctor_id=doc_user_id,
            datetime=days_from_now(random.randint(2, 14), hour=random.choice([9,10,11,14,15,16]), minute=0),
            status=AppointmentStatus.pending,
            reason=random.choice(REASONS),
        )
        db.add(appt_pend)
        created_appointments.append(appt_pend)

        # One cancelled
        appt_canc = Appointment(
            id=uid(),
            patient_id=pat.id,
            doctor_id=doc_user_id,
            datetime=days_ago(random.randint(10, 60), hour=10, minute=0),
            status=AppointmentStatus.cancelled,
            reason="Reevaluare stare generală",
            notes="Programare anulată de pacient.",
        )
        db.add(appt_canc)
        created_appointments.append(appt_canc)

    db.flush()
    print(f"✓ {len(created_appointments)} programări create")
else:
    print(f"✓ Programările există deja ({existing_appt_count}), se sărit")
    # Load existing for later use
    created_appointments = db.query(Appointment).filter(
        Appointment.status == AppointmentStatus.completed
    ).limit(20).all()

# ── 6. Fișe medicale ──────────────────────────────────────────────────────────
existing_records = db.query(MedicalRecord).count()
if existing_records < 5:
    RECORD_TEMPLATES = [
        {
            "record_type": "consultatie",
            "diagnosis": "Hipertensiune arterială stadiul II",
            "treatment": "Amlodipina 5mg/zi, Losartan 50mg/zi, dietă hiposodată",
            "notes": "Pacient prezintă TA 160/100 mmHg. Se ajustează tratamentul antihipertensiv. Monitorizare la 4 săptămâni.",
            "has_anomaly": True,
            "anomaly_notes": "Tensiune arterială crescută — necesită monitorizare intensivă",
        },
        {
            "record_type": "analiza",
            "diagnosis": None,
            "treatment": None,
            "analysis_result": "Hemoglobina: 11.2 g/dL (scăzut), Glicemie à jeun: 128 mg/dL (crescut), Colesterol total: 215 mg/dL, Trigliceride: 180 mg/dL",
            "notes": "Profil lipidic ușor alterat. Glicemie borderline — indicat TTGO.",
            "has_anomaly": True,
            "anomaly_notes": "Anemie ușoară și glicemie crescută",
        },
        {
            "record_type": "tratament",
            "diagnosis": "Diabet zaharat tip 2 — echilibrat",
            "treatment": "Metformin 1000mg x2/zi, Sitagliptin 100mg/zi, dietă diabetică, activitate fizică moderată 30 min/zi",
            "notes": "HbA1c 7.2% — satisfăcător. Se continuă schema actuală.",
            "has_anomaly": False,
        },
        {
            "record_type": "investigatie",
            "diagnosis": "Tahicardie sinusală",
            "treatment": None,
            "analysis_result": "EKG: ritm sinusal, 98/min. Ecografie cord: FE 60%, regurgitare mitrală minimă.",
            "notes": "Ecocardiografie în limite normale. Se repetă EKG la 6 luni.",
            "has_anomaly": False,
        },
        {
            "record_type": "consultatie",
            "diagnosis": "Spondiloză cervicală cu radiculopatie C5-C6",
            "treatment": "Ketoprofen 100mg la nevoie, Tolperizon 150mg x2, kinetoterapie 10 ședințe",
            "notes": "Pacient cu dureri cervicale iradiante în membrul superior drept. IRM cervical recomandat.",
            "has_anomaly": True,
            "anomaly_notes": "Radiculopatie — indicat IRM coloană cervicală",
        },
        {
            "record_type": "analiza",
            "diagnosis": None,
            "treatment": None,
            "analysis_result": "TSH: 5.8 mUI/L (crescut), FT4: 0.9 ng/dL (scăzut), Anticorpi anti-TPO: pozitivi",
            "notes": "Tiroidită autoimună Hashimoto confirmată. Se inițiază tratament substitutiv.",
            "has_anomaly": True,
            "anomaly_notes": "Hipotiroidism autoimun confirmat biologic",
        },
    ]

    for i, pat in enumerate(patient_list):
        dp = db.query(DoctorPatient).filter(DoctorPatient.patient_id == pat.id).first()
        if not dp:
            continue
        doc = db.query(Doctor).filter(Doctor.id == dp.doctor_id).first()
        if not doc:
            continue

        for j in range(random.randint(2, 4)):
            tmpl = RECORD_TEMPLATES[(i + j) % len(RECORD_TEMPLATES)]
            mr = MedicalRecord(
                id=uid(),
                patient_id=pat.id,
                doctor_id=doc.user_id,
                record_type=tmpl["record_type"],
                diagnosis=tmpl.get("diagnosis"),
                treatment=tmpl.get("treatment"),
                analysis_result=tmpl.get("analysis_result"),
                notes_encrypted=tmpl.get("notes"),
                has_anomaly=tmpl.get("has_anomaly", False),
                anomaly_notes=tmpl.get("anomaly_notes"),
                created_at=days_ago(random.randint(1, 120)),
            )
            db.add(mr)

    db.flush()
    print("✓ Fișe medicale create")
else:
    print(f"✓ Fișele medicale există deja ({existing_records}), se sărit")

# ── 7. Semne vitale (serii temporale) ────────────────────────────────────────
existing_vitals = db.query(VitalSign).count()
if existing_vitals < 10:
    VITAL_UNITS = {
        "pulse": "bpm", "weight": "kg", "temperature": "°C",
        "oxygen_sat": "%", "blood_pressure_sys": "mmHg", "blood_pressure_dia": "mmHg",
    }
    VITAL_RANGES = {
        "pulse":              (62, 95),
        "weight":             (60, 95),
        "temperature":        (36.2, 37.4),
        "oxygen_sat":         (95, 99),
        "blood_pressure_sys": (115, 165),
        "blood_pressure_dia": (70, 100),
    }

    for pat in patient_list:
        # 30 readings over 90 days
        for day_offset in range(90, 0, -3):  # every 3 days
            for vtype, unit in VITAL_UNITS.items():
                lo, hi = VITAL_RANGES[vtype]
                val = round(random.uniform(lo, hi), 1)
                vs = VitalSign(
                    id=uid(),
                    patient_id=pat.id,
                    vital_type=vtype,
                    value=val,
                    unit=unit,
                    recorded_at=days_ago(day_offset, hour=random.randint(7,20), minute=random.randint(0,59)),
                    notes=None,
                )
                db.add(vs)

    db.flush()
    print("✓ Semne vitale create")
else:
    print(f"✓ Semnele vitale există deja ({existing_vitals}), se sărit")

# ── 8. Prescripții ────────────────────────────────────────────────────────────
existing_rx = db.query(Prescription).count()
if existing_rx < 3:
    MEDS_TEMPLATES = [
        [
            {"name": "Amlodipina", "dose": "5 mg", "frequency": "1x/zi dimineața", "duration": "30 zile", "quantity": "30 comprimate"},
            {"name": "Losartan",   "dose": "50 mg", "frequency": "1x/zi seara",     "duration": "30 zile", "quantity": "30 comprimate"},
        ],
        [
            {"name": "Metformin",   "dose": "1000 mg", "frequency": "2x/zi (dimineața și seara cu masa)", "duration": "90 zile", "quantity": "180 comprimate"},
            {"name": "Sitagliptin", "dose": "100 mg",  "frequency": "1x/zi dimineața",                   "duration": "90 zile", "quantity": "90 comprimate"},
        ],
        [
            {"name": "Levotiroxin", "dose": "50 mcg", "frequency": "1x/zi pe stomacul gol", "duration": "60 zile", "quantity": "60 comprimate"},
        ],
        [
            {"name": "Ketoprofen",  "dose": "100 mg", "frequency": "la nevoie, max 2x/zi după masă", "duration": "10 zile", "quantity": "20 comprimate"},
            {"name": "Tolperizon",  "dose": "150 mg", "frequency": "2x/zi (dimineața și seara)",     "duration": "30 zile", "quantity": "60 comprimate"},
            {"name": "Omeprazol",   "dose": "20 mg",  "frequency": "1x/zi dimineața",                "duration": "30 zile", "quantity": "30 capsule"},
        ],
        [
            {"name": "Salbutamol spray", "dose": "100 mcg/puf", "frequency": "2 pufuri la nevoie, max 4x/zi", "duration": "60 zile", "quantity": "2 flacoane"},
            {"name": "Fluticazonă spray","dose": "250 mcg/puf", "frequency": "1 puf 2x/zi (dimineața și seara)","duration": "60 zile", "quantity": "2 flacoane"},
        ],
    ]

    for i, pat in enumerate(patient_list):
        dp = db.query(DoctorPatient).filter(DoctorPatient.patient_id == pat.id).first()
        if not dp:
            continue
        meds = MEDS_TEMPLATES[i % len(MEDS_TEMPLATES)]
        rx = Prescription(
            id=uid(),
            patient_id=pat.id,
            doctor_id=dp.doctor_id,
            medications=meds,
            notes="A se respecta dozajul prescris. Revenire la control după finalizarea tratamentului.",
            issued_at=days_ago(random.randint(1, 30)),
            created_at=days_ago(random.randint(1, 30)),
        )
        db.add(rx)

    db.flush()
    print("✓ Prescripții create")
else:
    print(f"✓ Prescripțiile există deja ({existing_rx}), se sărit")

# ── 9. Recenzii ────────────────────────────────────────────────────────────────
existing_reviews = db.query(Review).count()
if existing_reviews < 3:
    REVIEW_COMMENTS = [
        "Doctor foarte profesionist și empatic. A explicat clar diagnosticul și opțiunile de tratament. Recomand cu caldură!",
        "Consultație excelentă. Doctorul a luat în serios toate simptomele mele și a prescris un tratament eficient.",
        "Am așteptat mai mult decât m-am așteptat, dar consultația a meritat. Doctor competent.",
        "Foarte mulțumit de îngrijire. A răspuns la toate întrebările mele cu răbdare.",
        "Servicii de înaltă calitate. Mă simt în siguranță sub supravegherea acestui medic.",
    ]

    used_appt_ids = set()
    for i, pat in enumerate(patient_list):
        dp = db.query(DoctorPatient).filter(DoctorPatient.patient_id == pat.id).first()
        if not dp:
            continue
        doc = db.query(Doctor).filter(Doctor.id == dp.doctor_id).first()
        if not doc:
            continue
        # Find a completed appointment for this patient+doctor
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
            sentiment="pozitiv" if rating >= 4 else "neutru",
            created_at=appt.datetime + timedelta(hours=random.randint(2, 48)),
        )
        db.add(rev)

    db.flush()
    print("✓ Recenzii create")
else:
    print(f"✓ Recenziile există deja ({existing_reviews}), se sărit")

# ── 10. Mesaje ────────────────────────────────────────────────────────────────
existing_msgs = db.query(Message).count()
if existing_msgs < 5:
    CONV_TEMPLATES = [
        [
            ("doctor", "patient", "Bună ziua! Ați primit rezultatele analizelor de sânge pe email. Glicemia este ușor crescută — vă rog să reduceți consumul de carbohidrați."),
            ("patient", "doctor", "Bună ziua, doctor! Mulțumesc pentru mesaj. Voi respecta indicațiile. Ar trebui să vin la control mai devreme?"),
            ("doctor", "patient", "Da, aș recomanda un control în 2-3 săptămâni. Vă voi programa miercuri sau joi la alegere."),
            ("patient", "doctor", "Joi ar fi perfect, mulțumesc mult!"),
        ],
        [
            ("doctor", "patient", "Stimate pacient, tensiunea diastolică din ultima măsurătoare este îngrijorătoare. Ați luat medicamentele prescrise regulat?"),
            ("patient", "doctor", "Am uitat câteva zile să iau Losartan. Vă cer scuze, voi fi mai atent."),
            ("doctor", "patient", "Vă rog să nu întrerupeți tratamentul. Neregularitatea poate provoca variații periculoase ale tensiunii."),
        ],
        [
            ("assistant", "doctor", "Bună ziua, dr.! Avem 3 programări pending pentru mâine care necesită confirmare din partea dvs."),
            ("doctor", "assistant", "Mulțumesc, Daniela. Le confirm pe toate trei. Vă rog să-i anunțați pe pacienți."),
            ("assistant", "doctor", "Cu plăcere! Am trimis notificările de confirmare."),
        ],
    ]

    for c_idx, conv in enumerate(CONV_TEMPLATES):
        if c_idx < len(patient_list) and c_idx < len(doctor_list):
            pat_user_id = patients_u[c_idx].id if c_idx < len(patients_u) else None
            doc_user = doctors_u[c_idx % len(doctors_u)]

            role_map = {
                "doctor": doc_user.id,
                "patient": pat_user_id,
                "assistant": assistants_u[0].id if assistants_u else None,
            }

            base_time = days_ago(random.randint(2, 14), hour=9)
            for m_idx, (sender_role, receiver_role, content) in enumerate(conv):
                sender_id   = role_map.get(sender_role)
                receiver_id = role_map.get(receiver_role)
                if not sender_id or not receiver_id:
                    continue
                msg = Message(
                    id=uid(),
                    sender_id=sender_id,
                    receiver_id=receiver_id,
                    content=content,
                    is_read=m_idx < len(conv) - 1,  # last message unread
                    created_at=base_time + timedelta(minutes=m_idx * random.randint(2, 30)),
                )
                db.add(msg)

    db.flush()
    print("✓ Mesaje create")
else:
    print(f"✓ Mesajele există deja ({existing_msgs}), se sărit")

# ── Commit ────────────────────────────────────────────────────────────────────
db.commit()
print("\n✅ Seed complet! Baza de date a fost populată cu succes.")

# ── Summary ────────────────────────────────────────────────────────────────────
from sqlalchemy import func as sqlfunc
print("\n📊 Rezumat bază de date:")
print(f"   Utilizatori: {db.query(User).count()}")
print(f"   Doctori (profil): {db.query(Doctor).count()}")
print(f"   Pacienți (profil): {db.query(Patient).count()}")
print(f"   Atribuiri doctor-pacient: {db.query(DoctorPatient).count()}")
print(f"   Programări: {db.query(Appointment).count()}")
print(f"   Fișe medicale: {db.query(MedicalRecord).count()}")
print(f"   Semne vitale: {db.query(VitalSign).count()}")
print(f"   Prescripții: {db.query(Prescription).count()}")
print(f"   Recenzii: {db.query(Review).count()}")
print(f"   Mesaje: {db.query(Message).count()}")
