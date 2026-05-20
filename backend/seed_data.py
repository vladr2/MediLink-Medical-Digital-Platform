"""
MediLink – script populare date demo realiste
Rulează: docker compose exec backend python seed_data.py
Recreează toți utilizatorii demo și datele asociate.
"""
import uuid, random, sys, os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, '/app')
os.environ.setdefault('SECRET_KEY', 'seed-secret-key-not-used-in-prod')
os.environ.setdefault('FERNET_KEY', '')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

DATABASE_URL = "postgresql://medilink_user:medilink_pass@db:5432/medilink"
engine  = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db      = Session()

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEMO_PASSWORD = pwd_ctx.hash("Parola123!")

from app.models.user        import User
from app.models.doctor      import Doctor
from app.models.patient     import Patient
from app.models.doctor_patient import DoctorPatient
from app.models.appointment import Appointment, AppointmentStatus
from app.models.medical_record import MedicalRecord
from app.models.vital_sign  import VitalSign
from app.models.prescription import Prescription
from app.models.review      import Review
from app.models.message     import Message
from app.models.notification import Notification

def uid():  return uuid.uuid4()
def now():  return datetime.now(timezone.utc)
def ago(n, h=10, m=0):
    return (now() - timedelta(days=n)).replace(hour=h, minute=m, second=0, microsecond=0)
def fwd(n, h=10, m=0):
    return (now() + timedelta(days=n)).replace(hour=h, minute=m, second=0, microsecond=0)

# ─────────────────────────────────────────────────────────────────────────────
# 1. UTILIZATORI DEMO
# ─────────────────────────────────────────────────────────────────────────────
USERS = [
    # (email, first_name, last_name, role, phone, birth_date, address)
    ("admin@medilink.com",       "Alexia",    "Radoi",       "admin",
     "0721000001", "1985-03-15", "Str. Administrației nr. 1, București"),

    ("doctor@medilink.com",      "Mihai",     "Constantin",  "doctor",
     "0721000002", "1978-06-20", "Bd. Eroilor nr. 12, București"),
    ("alexandru.ionescu@gmail.com","Alexandru","Ionescu",    "doctor",
     "0721000003", "1980-11-05", "Str. Medicilor nr. 7, Cluj-Napoca"),
    ("maria.popescu@gmail.com",  "Maria",     "Popescu",     "doctor",
     "0721000004", "1982-04-22", "Calea Victoriei nr. 33, București"),

    ("asistent@medilink.com",    "Daniela",   "Vlad",        "assistant",
     "0721000005", "1990-07-14", "Str. Spitalului nr. 4, București"),
    ("asistent2@medilink.com",   "Ana",       "Florescu",    "assistant",
     "0721000006", "1993-02-28", "Bd. Unirii nr. 22, București"),

    ("pacient@medilink.com",     "Alin",      "Mincu",       "patient",
     "0721000007", "1975-09-10", "Str. Florilor nr. 18, București"),
    ("luminita.niculescu@yahoo.ro","Luminița","Niculescu",   "patient",
     "0721000008", "1968-12-03", "Str. Rozelor nr. 5, Ploiești"),
    ("andrei.marinescu@gmail.com","Andrei",   "Marinescu",   "patient",
     "0721000009", "1990-05-17", "Calea Dorobanților nr. 40, București"),
    ("ioana.popa@gmail.com",     "Ioana",     "Popa",        "patient",
     "0721000010", "1985-08-25", "Str. Libertății nr. 9, Brașov"),
    ("cristian.tudose@gmail.com","Cristian",  "Tudose",      "patient",
     "0721000011", "1972-01-30", "Bd. Republicii nr. 14, Iași"),
    ("raluca.munteanu@gmail.com","Raluca",    "Munteanu",    "patient",
     "0721000012", "1995-11-08", "Str. Primăverii nr. 3, Cluj-Napoca"),
]

print("── 1. Utilizatori ───────────────────────────────────────────")
user_map = {}  # email -> User
for email, fn, ln, role, phone, birth, address in USERS:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            id=uid(), email=email,
            hashed_password=DEMO_PASSWORD,
            role=role, is_active=True,
            first_name=fn, last_name=ln,
            phone=phone, birth_date=birth, address=address,
            email_notifications=True,
        )
        db.add(u)
        db.flush()
        print(f"   + creat {role}: {fn} {ln}")
    else:
        u.first_name=fn; u.last_name=ln; u.phone=phone
        u.birth_date=birth; u.address=address
        if not u.hashed_password:
            u.hashed_password = DEMO_PASSWORD
        db.flush()
        print(f"   ✓ există {role}: {fn} {ln}")
    user_map[email] = u

db.flush()

doctors_u   = [user_map[e] for e in ["doctor@medilink.com","alexandru.ionescu@gmail.com","maria.popescu@gmail.com"]]
patients_u  = [user_map[e] for e in ["pacient@medilink.com","luminita.niculescu@yahoo.ro","andrei.marinescu@gmail.com","ioana.popa@gmail.com","cristian.tudose@gmail.com","raluca.munteanu@gmail.com"]]
assistants_u= [user_map[e] for e in ["asistent@medilink.com","asistent2@medilink.com"]]

# ─────────────────────────────────────────────────────────────────────────────
# 2. PROFILURI DOCTORI
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 2. Profiluri doctori ──────────────────────────────────────")
DOCTOR_PROFILES = [
    {
        "specialization": "cardiologie",
        "license_number": "CMR-2024-001",
        "department": "Cardiologie",
        "bio": "Medic primar cardiolog cu peste 18 ani de experiență clinică. Specializat în ecocardiografie, monitorizare Holter și managementul insuficienței cardiace. Doctorat în științe medicale — Universitatea de Medicină și Farmacie Carol Davila, București.",
        "phone_cabinet": "021-310-2401",
        "schedule": "Luni–Vineri: 09:00–17:00",
    },
    {
        "specialization": "neurologie",
        "license_number": "CMR-2024-002",
        "department": "Neurologie",
        "bio": "Specialist neurolog cu competențe în diagnosticul și tratamentul AVC, epilepsie, migrenă și boli neurodegenerative. Experiență în electroencefalografie și EMG. Formație academică la Cluj-Napoca și stagii internaționale în Germania.",
        "phone_cabinet": "021-310-2402",
        "schedule": "Luni, Miercuri, Vineri: 08:00–16:00",
    },
    {
        "specialization": "medicina interna",
        "license_number": "CMR-2024-003",
        "department": "Medicină Internă",
        "bio": "Medic primar medicină internă, cu focus pe managementul bolilor cronice: diabet zaharat, afecțiuni tiroidiene și dislipidemie. Abordare holistică, orientată pe pacient. Membră a Societății Române de Medicină Internă.",
        "phone_cabinet": "021-310-2403",
        "schedule": "Marți–Sâmbătă: 09:00–15:00",
    },
]

doctor_profiles = {}
for i, u in enumerate(doctors_u):
    d = db.query(Doctor).filter(Doctor.user_id == u.id).first()
    if not d:
        prof = DOCTOR_PROFILES[i]
        d = Doctor(
            id=uid(), user_id=u.id,
            specialization=prof["specialization"],
            license_number=prof["license_number"],
            department=prof["department"],
            bio=prof["bio"],
            phone_cabinet=prof["phone_cabinet"],
            schedule=prof["schedule"],
        )
        db.add(d); db.flush()
        print(f"   + profil doctor: {u.first_name} {u.last_name} ({prof['specialization']})")
    else:
        print(f"   ✓ profil există: {u.first_name} {u.last_name}")
    doctor_profiles[str(u.id)] = d

db.flush()
doctor_list = list(doctor_profiles.values())

# ─────────────────────────────────────────────────────────────────────────────
# 3. PROFILURI PACIENȚI
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 3. Profiluri pacienți ─────────────────────────────────────")
PATIENT_DATA = [
    {"blood_type": "A+",  "allergies": "Penicilină",   "chronic": "Hipertensiune arterială stadiul II, Diabet zaharat tip 2",   "gender": "M", "emergency": ("Cristina Mincu",    "0722100001")},
    {"blood_type": "O-",  "allergies": "Niciuna",       "chronic": "Boală coronariană ischemică, Dislipidemie",                  "gender": "F", "emergency": ("Ion Niculescu",      "0722100002")},
    {"blood_type": "B+",  "allergies": "Ibuprofen",     "chronic": "Astm bronșic moderat persistent",                           "gender": "M", "emergency": ("Ana Marinescu",      "0722100003")},
    {"blood_type": "AB+", "allergies": "Sulfonamide",   "chronic": "Hipotiroidism autoimun (Hashimoto)",                        "gender": "F", "emergency": ("Mihai Popa",         "0722100004")},
    {"blood_type": "A-",  "allergies": "Aspirină",      "chronic": "Diabet zaharat tip 1, Retinopatia diabetică stadiul I",     "gender": "M", "emergency": ("Elena Tudose",       "0722100005")},
    {"blood_type": "O+",  "allergies": "Niciuna",       "chronic": "Spondiloză cervicală, Anxietate generalizată",              "gender": "F", "emergency": ("Vlad Munteanu",      "0722100006")},
]

patient_profiles = {}
for i, u in enumerate(patients_u):
    p = db.query(Patient).filter(Patient.user_id == u.id).first()
    if not p:
        pd = PATIENT_DATA[i]
        p = Patient(
            id=uid(), user_id=u.id,
            blood_type=pd["blood_type"],
            allergies=pd["allergies"],
            chronic_conditions=pd["chronic"],
            gender=pd["gender"],
            emergency_contact=pd["emergency"][0],
            emergency_phone=pd["emergency"][1],
            gdpr_consent_at=ago(random.randint(30, 200)),
        )
        db.add(p); db.flush()
        print(f"   + profil pacient: {u.first_name} {u.last_name}")
    else:
        print(f"   ✓ profil există: {u.first_name} {u.last_name}")
    patient_profiles[str(u.id)] = p

db.flush()
patient_list = list(patient_profiles.values())

# ─────────────────────────────────────────────────────────────────────────────
# 4. ATRIBUIRI DOCTOR–PACIENT
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 4. Atribuiri doctor–pacient ───────────────────────────────")
# Fiecare pacient are un doctor principal + uneori al doilea
ASSIGNMENTS = [
    (0, 0), (1, 0), (2, 1),   # pacientii 0,1 -> doctor 0; pacient 2 -> doctor 1
    (3, 1), (4, 2), (5, 2),   # pacientii 3 -> doctor 1; 4,5 -> doctor 2
    (0, 1), (2, 2),            # pacient 0 are si doctor 1; pacient 2 are si doctor 2
]
for pat_idx, doc_idx in ASSIGNMENTS:
    if pat_idx >= len(patient_list) or doc_idx >= len(doctor_list):
        continue
    pat = patient_list[pat_idx]
    doc = doctor_list[doc_idx]
    ex = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == doc.id,
        DoctorPatient.patient_id == pat.id
    ).first()
    if not ex:
        db.add(DoctorPatient(doctor_id=doc.id, patient_id=pat.id))
db.flush()
print(f"   ✓ atribuiri create/verificate")

def get_primary_doctor(pat):
    dp = db.query(DoctorPatient).filter(DoctorPatient.patient_id == pat.id).first()
    return db.query(Doctor).filter(Doctor.id == dp.doctor_id).first() if dp else None

# ─────────────────────────────────────────────────────────────────────────────
# 5. PROGRAMĂRI
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 5. Programări ─────────────────────────────────────────────")
REASONS = [
    "Consultație cardiologică periodică",
    "Control tensiune arterială și ajustare tratament",
    "Durere toracică — investigații urgente",
    "Consultație pentru diabet zaharat — reevaluare HbA1c",
    "Dureri de cap persistente — evaluare neurologică",
    "Tuse persistentă și dispnee de efort",
    "Oboseală cronică și scădere în greutate",
    "Analize sânge de rutină + profil lipidic",
    "Reînnoire prescripție medicație cronică",
    "Dureri articulare și limitare mobilitate",
    "Consultație medicină internă — simptome digestive",
    "Investigații pentru hipotiroidism — TSH crescut",
    "Control post-externare — monitorizare recuperare",
    "Palpitații și amețeli episodice",
    "Screening preventiv — pacient peste 50 ani",
]
HOURS  = [9, 10, 11, 14, 15, 16]
MINS   = [0, 15, 30, 45]

existing_appts = db.query(Appointment).count()
if existing_appts < 5:
    total_appts = 0
    for pat in patient_list:
        doc = get_primary_doctor(pat)
        if not doc: continue
        doc_user_id = doc.user_id

        # 4-5 programări trecute completate
        for k in range(random.randint(4, 5)):
            db.add(Appointment(
                id=uid(), patient_id=pat.id, doctor_id=doc_user_id,
                datetime=ago(random.randint(5, 180), h=random.choice(HOURS), m=random.choice(MINS)),
                status=AppointmentStatus.completed,
                reason=random.choice(REASONS),
                notes="Consultație efectuată. Pacient cooperant.",
            ))
            total_appts += 1

        # 1-2 programări viitoare confirmate
        for k in range(random.randint(1, 2)):
            db.add(Appointment(
                id=uid(), patient_id=pat.id, doctor_id=doc_user_id,
                datetime=fwd(random.randint(2, 30), h=random.choice(HOURS), m=random.choice(MINS)),
                status=AppointmentStatus.confirmed,
                reason=random.choice(REASONS),
            ))
            total_appts += 1

        # 1 programare pending (pentru coada asistentului)
        db.add(Appointment(
            id=uid(), patient_id=pat.id, doctor_id=doc_user_id,
            datetime=fwd(random.randint(5, 20), h=random.choice(HOURS), m=0),
            status=AppointmentStatus.pending,
            reason=random.choice(REASONS),
        ))
        total_appts += 1

        # 1-2 anulate
        for _ in range(random.randint(1, 2)):
            db.add(Appointment(
                id=uid(), patient_id=pat.id, doctor_id=doc_user_id,
                datetime=ago(random.randint(10, 90), h=random.choice(HOURS), m=0),
                status=AppointmentStatus.cancelled,
                reason=random.choice(REASONS),
                notes="Programare anulată de pacient.",
                cancelled_by_patient=True,
            ))
            total_appts += 1

    db.flush()
    print(f"   ✓ {total_appts} programări create")
else:
    print(f"   ✓ programările există deja ({existing_appts})")

# ─────────────────────────────────────────────────────────────────────────────
# 6. FIȘE MEDICALE (8–10 per pacient, toate tipurile)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 6. Fișe medicale ──────────────────────────────────────────")

# Templates per tip pacient (indexate după patient_list index)
RECORDS_PER_PATIENT = [
    # Pacient 0 — Alin Mincu: HTA + DZ tip 2
    [
        {"record_type":"consultatie","diagnosis":"Hipertensiune arterială stadiul II","treatment":"Amlodipina 5mg/zi, Losartan 50mg/zi, dietă hiposodată","notes":"TA 162/102 mmHg. Se ajustează schema antihipertensivă. Monitorizare la 4 săptămâni.","has_anomaly":True,"anomaly_notes":"TA sistolică >160 mmHg — risc cardiovascular crescut","days":120},
        {"record_type":"analiza","analysis_result":"HbA1c: 8.1% (crescut), Glicemie à jeun: 148 mg/dL, Colesterol LDL: 138 mg/dL, Creatinina: 1.1 mg/dL","notes":"Control glicemic nesatisfăcător. Se intensifică tratamentul antidiabetic.","has_anomaly":True,"anomaly_notes":"HbA1c >8% — diabet dezechilibrat","days":100},
        {"record_type":"tratament","diagnosis":"Diabet zaharat tip 2 — dezechilibrat","treatment":"Metformin 1000mg x2/zi, se adaugă Sitagliptin 100mg/zi, dietă diabetică strictă, activitate fizică 30min/zi","notes":"Pacientul a fost instruit privind dieta și automonitorizarea glicemiei.","days":95},
        {"record_type":"investigatie","diagnosis":"Microalbuminurie — nefropatie diabetică incipientă","analysis_result":"Ecografie renală: rinichi cu contur regulat, dimensiuni normale. Raport albumina/creatinina urinar: 42 mg/g (crescut)","notes":"Nefropatie diabetică stadiul I. Se inițiază monitorizare semestrială.","has_anomaly":True,"anomaly_notes":"Microalbuminurie — nefropatie diabetică incipientă","days":80},
        {"record_type":"consultatie","diagnosis":"HTA + DZ tip 2 — reevaluare la 3 luni","treatment":"Continuare Amlodipina + Losartan. Metformin ajustat la 850mg x3/zi.","notes":"TA 148/92 mmHg — îmbunătățire față de consultația precedentă. Greutate: 84kg (-2kg).","days":60},
        {"record_type":"analiza","analysis_result":"HbA1c: 7.4% (îmbunătățit), Glicemie à jeun: 122 mg/dL, Colesterol LDL: 118 mg/dL, Trigliceride: 162 mg/dL","notes":"Progres bun față de anteriorul control. Se continuă schema actuală.","days":45},
        {"record_type":"reteta","diagnosis":"HTA + DZ tip 2","treatment":"Amlodipina 5mg — 30 comprimate, Losartan 50mg — 30 comprimate, Metformin 850mg — 90 comprimate","notes":"Rețetă compensată 90%. A se respecta dozajul. Control la 6 săptămâni.","days":40},
        {"record_type":"consultatie","diagnosis":"Control periodic — evoluție favorabilă","treatment":"Continuare tratament actual. Se adaugă Atorvastatina 20mg/seara pentru dislipidemie.","notes":"TA 138/86 mmHg. Pacient compliant cu tratamentul. Semne vitale stabile.","days":15},
    ],
    # Pacient 1 — Luminița Niculescu: boală coronariană + dislipidemie
    [
        {"record_type":"consultatie","diagnosis":"Angină pectorală stabilă de efort","treatment":"Bisoprolol 5mg/zi, Aspirina 75mg/zi, Atorvastatina 40mg/seara, Nitroglicerină sublingual la nevoie","notes":"ECG: modificări ischemice de repaus. Indicat test de efort și coronarografie electivă.","has_anomaly":True,"anomaly_notes":"Modificări ischemice ECG — evaluare coronarografică necesară","days":150},
        {"record_type":"investigatie","diagnosis":"Cardiopatie ischemică — stenoze moderate","analysis_result":"Coronarografie: stenoză 60% ADA proximal, 55% CD mediu. FE: 52%. Test de efort pozitiv la 7 METs.","notes":"Revascularizare percutană nerecomandata deocamdată. Tratament medicamentos optimizat.","has_anomaly":True,"anomaly_notes":"Stenoze coronariene moderate bilateral","days":130},
        {"record_type":"analiza","analysis_result":"Colesterol total: 248 mg/dL, LDL: 168 mg/dL (crescut), HDL: 42 mg/dL, Trigliceride: 210 mg/dL, hs-CRP: 3.2 mg/L","notes":"Profil lipidic nefavorabil. Se intensifică terapia cu statine.","has_anomaly":True,"anomaly_notes":"LDL >160 mg/dL — risc cardiovascular foarte înalt","days":120},
        {"record_type":"tratament","diagnosis":"Dislipidemie severă + boală coronariană","treatment":"Rosuvastatina 20mg/seara (înlocuiește Atorvastatina), Ezetimib 10mg/zi se adaugă, target LDL <55 mg/dL","notes":"Pacientă aderentă la tratament. Se repetă lipidograma la 6 săptămâni.","days":90},
        {"record_type":"consultatie","diagnosis":"Control periodic — stabilă clinic","treatment":"Continuare schema actuală. Recomandare cardioreabilitare.","notes":"Fără episoade anginoase în ultimele 3 luni. ECG fără modificări noi.","days":60},
        {"record_type":"analiza","analysis_result":"LDL: 68 mg/dL (target atins), HDL: 48 mg/dL, Trigliceride: 145 mg/dL, Glicemie: 98 mg/dL, Creatinina: 0.9 mg/dL","notes":"Excelent răspuns la terapia dublă lipidică. Se continuă schema.","days":40},
        {"record_type":"reteta","diagnosis":"Boală coronariană + dislipidemie","treatment":"Rosuvastatina 20mg — 30 comprimate, Ezetimib 10mg — 30 comprimate, Bisoprolol 5mg — 30 comprimate, Aspirina 75mg — 30 comprimate","notes":"Rețetă compensată. Obligatoriu tratament continuu fără întrerupere.","days":35},
        {"record_type":"investigatie","analysis_result":"Ecocardiografie de control: FE 55% (îmbunătățit), cinetica parietală normală, fără revărsat pericardic.","notes":"Funcție sistolică ameliorată față de investigația anterioară.","days":20},
    ],
    # Pacient 2 — Andrei Marinescu: astm bronșic
    [
        {"record_type":"consultatie","diagnosis":"Astm bronșic moderat persistent — exacerbare","treatment":"Salbutamol spray 2 pufuri la 4-6h, Budesonid/Formoterol 1 puf x2/zi, Prednison 40mg/zi 5 zile","notes":"Pacient cu wheezing și dispnee. VEMS 62% din valoarea prezisă. Spitalizare evitată.","has_anomaly":True,"anomaly_notes":"Exacerbare astm — VEMS <70% prezis","days":90},
        {"record_type":"investigatie","analysis_result":"Spirometrie: VEMS/CVF 68% (obstrucție moderată), Test bronhodilatator pozitiv (+18% VEMS). Peak flow: 320 L/min.","notes":"Pattern obstructiv reversibil — confirmat astm bronșic.","has_anomaly":True,"anomaly_notes":"Obstrucție bronșică moderată la spirometrie","days":85},
        {"record_type":"analiza","analysis_result":"Eozinofile: 540/mm³ (crescut), IgE total: 285 UI/mL (crescut), FeNO: 38 ppb (crescut), Hemoleucogramă normală","notes":"Inflamație eozinofilică semnificativă. Componenta alergică prezentă.","has_anomaly":True,"anomaly_notes":"Eozinofilie și IgE crescute — astm alergic","days":80},
        {"record_type":"tratament","diagnosis":"Astm bronșic alergic moderat persistent","treatment":"Salmeterol/Fluticazonă 50/250mcg x2/zi (înlocuiește schema anterioară), Montelukast 10mg/seara, evitare triggeri","notes":"Se trece pe LABA+ICS combinat. Pacientul instruit privind tehnica de inhalare.","days":70},
        {"record_type":"consultatie","diagnosis":"Control astm — răspuns bun la tratament","treatment":"Continuare schema LABA+ICS. Reducere treptată Prednison oral.","notes":"Dispneea ameliorată semnificativ. VEMS 78%. Peak flow zilnic 390-420 L/min.","days":50},
        {"record_type":"investigatie","analysis_result":"Spirometrie de control: VEMS/CVF 76% (+8% față de anterior), VEMS 88% din prezis. Ameliorare semnificativă.","notes":"Bun control al astmului sub tratamentul actual.","days":35},
        {"record_type":"reteta","diagnosis":"Astm bronșic","treatment":"Salmeterol/Fluticazonă 50/250mcg — 2 flacoane, Montelukast 10mg — 30 comprimate, Salbutamol 100mcg — 1 flacon (de rezervă)","notes":"A nu întrerupe tratamentul de fond. Salbutamol doar la nevoie.","days":30},
        {"record_type":"consultatie","diagnosis":"Astm controlat — follow-up rutină","treatment":"Continuare schema actuală. Posibilă scădere a dozei ICS peste 3 luni.","notes":"Fără exacerbări în ultimele 6 săptămâni. Calitatea vieții ameliorată.","days":10},
    ],
    # Pacient 3 — Ioana Popa: hipotiroidism Hashimoto
    [
        {"record_type":"analiza","analysis_result":"TSH: 8.4 mUI/L (crescut), FT4: 0.7 ng/dL (scăzut), FT3: 2.1 pg/mL (limită inferioară), Anti-TPO: 420 UI/mL (pozitiv)","notes":"Hipotiroidism autoimun confirmat. Titruri anti-TPO ridicate — tiroidită Hashimoto.","has_anomaly":True,"anomaly_notes":"TSH >8 mUI/L și anti-TPO pozitivi — Hashimoto confirmat","days":110},
        {"record_type":"consultatie","diagnosis":"Tiroidită Hashimoto — hipotiroidism manifest","treatment":"Levotiroxin 50mcg/zi pe stomacul gol cu 30 min înainte de masă. Reevaluare TSH la 6-8 săptămâni.","notes":"Pacientă cu oboseală marcată, creștere în greutate și constipație. Se inițiază tratament substitutiv.","days":105},
        {"record_type":"investigatie","analysis_result":"Ecografie tiroidiană: glandă tiroidiană cu volum redus (6.2 mL), ecogenitate neomogenă cu aspect micronoduler difuz — aspect tipic Hashimoto.","notes":"Aspect ultrasonografic concordant cu diagnosticul de tiroidită Hashimoto.","has_anomaly":True,"anomaly_notes":"Tiroidă atrofică cu aspect heterogen — Hashimoto avansat","days":100},
        {"record_type":"analiza","analysis_result":"TSH: 4.8 mUI/L (în curs de normalizare), FT4: 1.0 ng/dL, Hemoleucogramă: normală, Colesterol: 195 mg/dL","notes":"Răspuns parțial la tratament. Se crește doza de Levotiroxin.","days":65},
        {"record_type":"tratament","diagnosis":"Hipotiroidism Hashimoto — optimizare doză","treatment":"Levotiroxin crescut la 75mcg/zi. Continuare pe termen nedeterminat. Evitare alimente care interferă cu absorbția (soia, fibre în exces).","notes":"Pacientă informată că tratamentul este pe viață.","days":60},
        {"record_type":"analiza","analysis_result":"TSH: 2.1 mUI/L (normal), FT4: 1.2 ng/dL (normal), FT3: 3.0 pg/mL (normal). Colesterol 175 mg/dL.","notes":"Excelent răspuns la doza actuală. Simptomele ameliorate semnificativ.","days":30},
        {"record_type":"reteta","diagnosis":"Hipotiroidism Hashimoto","treatment":"Levotiroxin 75mcg — 60 comprimate (2 luni)","notes":"Administrare strictă dimineața pe stomacul gol. Nu asocia cu suplimente de calciu/fier la interval <4h.","days":25},
        {"record_type":"consultatie","diagnosis":"Hipotiroidism controlat — TSH în limite normale","treatment":"Continuare Levotiroxin 75mcg/zi. Control TSH semestrial.","notes":"Pacienta se simte bine, fără simptome hipotiroidiene. Greutate stabilizată.","days":5},
    ],
    # Pacient 4 — Cristian Tudose: DZ tip 1 + retinopatie
    [
        {"record_type":"consultatie","diagnosis":"Diabet zaharat tip 1 — dezechilibrat metabolic","treatment":"Insulina Glargine 20UI seara, Insulina Aspart 6-8UI preprandial. Schema bazal-bolus intensificată.","notes":"Hipoglicemii nocturne frecvente raportate de pacient. Necesar ajustare schemă insulinică.","has_anomaly":True,"anomaly_notes":"Hipoglicemii recurente — schemă insulinică dezechilibrată","days":130},
        {"record_type":"analiza","analysis_result":"HbA1c: 9.2% (crescut), Glicemie medie sensor CGM: 198 mg/dL, Timp în țintă (TIR): 38%, Creatinina: 1.3 mg/dL, Microalbuminurie: 68 mg/g","notes":"Control glicemic slab. Incipiente semne de complicații microvasculare.","has_anomaly":True,"anomaly_notes":"HbA1c >9% și microalbuminurie — complicații microvasculare","days":120},
        {"record_type":"investigatie","diagnosis":"Retinopatie diabetică neproliferativă stadiul I","analysis_result":"Examen fund de ochi: microanevrisme și exudate dure la nivelul polului posterior bilateral. Edem macular absent.","notes":"Consultație oftalmologică urgentă recomandată. Controlul strict al glicemiei esențial.","has_anomaly":True,"anomaly_notes":"Retinopatie diabetică stadiul I bilateral","days":100},
        {"record_type":"tratament","diagnosis":"DZ tip 1 — optimizare schemă insulinică","treatment":"Insulina Glargine U300 22UI seara, Insulina Lispro ajustată după glicemia preprandială (algoritm de corecție). CGM continuu recomandat.","notes":"Se introduce algoritmul de corecție bazat pe CGM. Educație terapeutică intensivă.","days":85},
        {"record_type":"analiza","analysis_result":"HbA1c: 7.8% (îmbunătățit), TIR: 58%, Glicemie medie: 158 mg/dL, Creatinina: 1.1 mg/dL (stabilă)","notes":"Progres semnificativ față de anterior. Se continuă optimizarea.","days":60},
        {"record_type":"consultatie","diagnosis":"DZ tip 1 — follow-up","treatment":"Continuare schemă actuală. Se adaugă Ramipril 5mg/zi pentru protecție renală.","notes":"Pacient mult mai bine gestionat. TIR >55% atins. Hipoglicemii reduse la <5%.","days":45},
        {"record_type":"reteta","diagnosis":"Diabet zaharat tip 1","treatment":"Insulina Glargine U300 — 3 stilouri x 1.5mL, Insulina Lispro 100UI/mL — 5 stilouri, Ramipril 5mg — 30 comprimate, Ace-K strips — 200 bandelete","notes":"Rețetă compensată 100%. Glucometru și benzi de test asigurate separat.","days":40},
        {"record_type":"investigatie","analysis_result":"Ecografie renală + Doppler renal: fără stenoze arteriale renale. Rinichi cu dimensiuni și ecogenitate normale.","notes":"Fără afectare renală organică semnificativă. Protecție nefrologică continuată.","days":20},
        {"record_type":"analiza","analysis_result":"HbA1c: 7.2% (aproape de target), TIR: 67%, Trigliceride: 142 mg/dL, Colesterol LDL: 95 mg/dL, microalbuminurie 28 mg/g (scăzut față de anterior)","notes":"Control glicemic net ameliorat. Microalbuminurie în regresie.","days":10},
    ],
    # Pacient 5 — Raluca Munteanu: spondiloză cervicală + anxietate
    [
        {"record_type":"consultatie","diagnosis":"Spondiloză cervicală cu radiculopatie C5-C6","treatment":"Diclofenac 75mg x2/zi 10 zile, Tolperizon 150mg x2/zi, Omeprazol 20mg/zi gastroprotecție, fizioterapie 10 ședințe","notes":"Pacientă cu dureri cervicale iradiate în membrul superior drept. IRM cervical indicat.","has_anomaly":True,"anomaly_notes":"Radiculopatie C5-C6 — necesitat IRM coloană cervicală","days":100},
        {"record_type":"investigatie","diagnosis":"Hernie de disc C5-C6 cu compresie radiculară","analysis_result":"IRM coloană cervicală: protruzie discală C5-C6 de 4mm cu amprentare pe sacul dural și contact cu rădăcina C6 dreaptă. Semnal medular normal.","notes":"Hernie de disc moderată. Tratament conservator indicat în primă instanță.","has_anomaly":True,"anomaly_notes":"Hernie disc C5-C6 cu compresie radiculară dreapta","days":90},
        {"record_type":"consultatie","diagnosis":"Reevaluare spondiloză — răspuns parțial la tratament","treatment":"Se trece pe Ketoprofen 100mg la nevoie, Pregabalin 75mg x2/zi pentru durere neuropată, continuare fizioterapie","notes":"Ameliorare parțială a durerii (EVA 4/10 față de 7/10 inițial). Se adaugă neuromodulatoare.","days":70},
        {"record_type":"analiza","analysis_result":"Hemoleucogramă: normală. VSH: 12 mm/h. PCR: 0.4 mg/dL. Factor reumatoid: negativ. Anti-CCP: negativ.","notes":"Markeri inflamatori normali — exclud artropatie inflamatorie sistemică.","days":65},
        {"record_type":"investigatie","analysis_result":"EMG membre superioare: semne de neuropatie C6 dreaptă ușoară — viteză de conducere ușor redusă. Fără denervare activă.","notes":"Neuropatie periferică ușoară concordantă cu hernia de disc.","days":55},
        {"record_type":"tratament","diagnosis":"Anxietate generalizată asociată durerii cronice","treatment":"Sertralina 50mg/zi (titrat progresiv la 100mg), Alprazolam 0.25mg la nevoie (max 10 zile), psihoterapie cognitiv-comportamentală recomandată","notes":"Pacientă cu simptome anxioase semnificative amplificate de durerea cronică. Abordare biopsihosocială.","days":45},
        {"record_type":"reteta","diagnosis":"Spondiloză cervicală + anxietate","treatment":"Pregabalin 75mg — 60 capsule, Sertralina 50mg — 30 comprimate, Omeprazol 20mg — 30 capsule, Ketoprofen 100mg — 20 comprimate (la nevoie)","notes":"Sertralina se ia dimineața cu mâncare. Pregabalin poate da somnolență inițial.","days":40},
        {"record_type":"consultatie","diagnosis":"Control periodic — ameliorare semnificativă","treatment":"Continuare Sertralina 100mg. Reducere treptată Pregabalin. Kinetoterapie de întreținere.","notes":"Durere EVA 2/10. Anxietatea mult redusă. Pacientă funcțională. Evaluare la 3 luni.","days":15},
    ],
]

existing_records = db.query(MedicalRecord).count()
if existing_records < 10:
    total_rec = 0
    for i, pat in enumerate(patient_list):
        doc = get_primary_doctor(pat)
        if not doc: continue
        templates = RECORDS_PER_PATIENT[i % len(RECORDS_PER_PATIENT)]
        for tmpl in templates:
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
                created_at=ago(tmpl.get("days", random.randint(1,120))),
            )
            db.add(mr)
            total_rec += 1
    db.flush()
    print(f"   ✓ {total_rec} fișe medicale create ({total_rec // max(len(patient_list),1)} per pacient)")
else:
    print(f"   ✓ fișele există deja ({existing_records})")

# ─────────────────────────────────────────────────────────────────────────────
# 7. SEMNE VITALE cu tendințe realiste
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 7. Semne vitale ───────────────────────────────────────────")
existing_vitals = db.query(VitalSign).count()
if existing_vitals < 10:
    VITAL_UNITS = {
        "blood_pressure_sys":"mmHg","blood_pressure_dia":"mmHg",
        "pulse":"bpm","weight":"kg","temperature":"°C","oxygen_sat":"%",
    }
    # Tendințe per pacient: (start_range, end_range) — valorile scad/cresc realist cu tratamentul
    VITAL_TRENDS = [
        # Alin Mincu — HTA: TA scade cu tratamentul, puls stabil
        {"blood_pressure_sys":(162,136),"blood_pressure_dia":(102,84),"pulse":(78,72),"weight":(88,85),"temperature":(36.6,36.5),"oxygen_sat":(97,98)},
        # Luminița Niculescu — boală coronariană: TA și puls controlate
        {"blood_pressure_sys":(145,132),"blood_pressure_dia":(92,80),"pulse":(82,65),"weight":(72,70),"temperature":(36.5,36.6),"oxygen_sat":(96,97)},
        # Andrei Marinescu — astm: saturație O2 îmbunătățită, puls stabil
        {"blood_pressure_sys":(122,118),"blood_pressure_dia":(78,75),"pulse":(88,76),"weight":(78,78),"temperature":(36.7,36.5),"oxygen_sat":(94,98)},
        # Ioana Popa — hipotiroidism: greutate scade cu tratamentul, puls crește
        {"blood_pressure_sys":(118,115),"blood_pressure_dia":(76,73),"pulse":(58,70),"weight":(82,76),"temperature":(36.2,36.6),"oxygen_sat":(98,99)},
        # Cristian Tudose — DZ tip 1: parametri metabolici — TA și puls stabile
        {"blood_pressure_sys":(128,120),"blood_pressure_dia":(82,75),"pulse":(80,74),"weight":(75,74),"temperature":(36.6,36.6),"oxygen_sat":(98,99)},
        # Raluca Munteanu — spondiloză: parametri normali, puls ușor crescut (anxietate)
        {"blood_pressure_sys":(115,112),"blood_pressure_dia":(74,70),"pulse":(92,78),"weight":(62,62),"temperature":(36.5,36.5),"oxygen_sat":(99,99)},
    ]
    total_vitals = 0
    for i, pat in enumerate(patient_list):
        trends = VITAL_TRENDS[i % len(VITAL_TRENDS)]
        readings = list(range(90, 0, -3))  # 30 citiri pe 90 zile
        total_readings = len(readings)
        for step, day_offset in enumerate(readings):
            progress = step / max(total_readings - 1, 1)  # 0 → 1 (trecut → prezent)
            for vtype, unit in VITAL_UNITS.items():
                start_val, end_val = trends[vtype]
                base = start_val + (end_val - start_val) * progress
                noise = random.uniform(-2, 2) if vtype in ("blood_pressure_sys","blood_pressure_dia","pulse") else random.uniform(-0.3, 0.3)
                val = round(base + noise, 1)
                db.add(VitalSign(
                    id=uid(), patient_id=pat.id, vital_type=vtype,
                    value=val, unit=unit,
                    recorded_at=ago(day_offset, h=random.randint(7,20), m=random.randint(0,59)),
                ))
                total_vitals += 1
    db.flush()
    print(f"   ✓ {total_vitals} semne vitale create (tendințe realiste)")
else:
    print(f"   ✓ semnele vitale există deja ({existing_vitals})")

# ─────────────────────────────────────────────────────────────────────────────
# 8. PRESCRIPȚII (2-3 per pacient)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 8. Prescripții ────────────────────────────────────────────")
existing_rx = db.query(Prescription).count()
if existing_rx < 3:
    PRESCRIPTIONS = [
        # Alin Mincu
        [
            {"meds":[{"name":"Amlodipina","dose":"5 mg","frequency":"1x/zi dimineața","duration":"30 zile","quantity":"30 compr."},{"name":"Losartan","dose":"50 mg","frequency":"1x/zi seara","duration":"30 zile","quantity":"30 compr."}],"notes":"A nu omite doze. Monitorizare TA zilnic.","days":40},
            {"meds":[{"name":"Metformin","dose":"850 mg","frequency":"3x/zi cu mesele","duration":"90 zile","quantity":"270 compr."},{"name":"Sitagliptin","dose":"100 mg","frequency":"1x/zi dimineața","duration":"90 zile","quantity":"90 compr."},{"name":"Atorvastatina","dose":"20 mg","frequency":"1x/zi seara","duration":"30 zile","quantity":"30 compr."}],"notes":"Control glicemie zilnic. HbA1c la 3 luni.","days":15},
        ],
        # Luminița Niculescu
        [
            {"meds":[{"name":"Rosuvastatina","dose":"20 mg","frequency":"1x/zi seara","duration":"30 zile","quantity":"30 compr."},{"name":"Ezetimib","dose":"10 mg","frequency":"1x/zi","duration":"30 zile","quantity":"30 compr."},{"name":"Bisoprolol","dose":"5 mg","frequency":"1x/zi dimineața","duration":"30 zile","quantity":"30 compr."},{"name":"Aspirina","dose":"75 mg","frequency":"1x/zi cu masă","duration":"30 zile","quantity":"30 compr."}],"notes":"Nu întrerupe Aspirina fără indicație medicală.","days":35},
        ],
        # Andrei Marinescu
        [
            {"meds":[{"name":"Salmeterol/Fluticazonă","dose":"50/250mcg","frequency":"1 puf x2/zi","duration":"60 zile","quantity":"2 flacoane"},{"name":"Montelukast","dose":"10 mg","frequency":"1x/zi seara","duration":"30 zile","quantity":"30 compr."}],"notes":"Tehnica de inhalare corectă este esențială. Clătire gură după inhalator cu corticoid.","days":30},
        ],
        # Ioana Popa
        [
            {"meds":[{"name":"Levotiroxin","dose":"75 mcg","frequency":"1x/zi dimineața pe stomacul gol","duration":"60 zile","quantity":"60 compr."}],"notes":"Interval minim 30 min față de micul dejun. Nu asocia cu calciu/fier.","days":25},
        ],
        # Cristian Tudose
        [
            {"meds":[{"name":"Insulina Glargine U300","dose":"22 UI","frequency":"1x/zi seara","duration":"30 zile","quantity":"3 stilouri"},{"name":"Insulina Lispro","dose":"variabil","frequency":"preprandial (algoritm corecție)","duration":"30 zile","quantity":"5 stilouri"},{"name":"Ramipril","dose":"5 mg","frequency":"1x/zi dimineața","duration":"30 zile","quantity":"30 compr."}],"notes":"CGM continuu. Tintă TIR >65%. Ramipril nefroprotector obligatoriu.","days":40},
            {"meds":[{"name":"Vitamina D3","dose":"4000 UI","frequency":"1x/zi","duration":"90 zile","quantity":"90 capsule"},{"name":"Acid alfa-lipoic","dose":"600 mg","frequency":"1x/zi","duration":"60 zile","quantity":"60 compr."}],"notes":"Suplimentare pentru neuroprotecție.","days":20},
        ],
        # Raluca Munteanu
        [
            {"meds":[{"name":"Sertralina","dose":"100 mg","frequency":"1x/zi dimineața cu mâncare","duration":"90 zile","quantity":"90 compr."},{"name":"Pregabalin","dose":"75 mg","frequency":"2x/zi (dimineața și seara)","duration":"30 zile","quantity":"60 capsule"}],"notes":"Sertralina: efect deplin la 4-6 săptămâni. Nu opri brusc.","days":40},
            {"meds":[{"name":"Ketoprofen","dose":"100 mg","frequency":"la nevoie, max 2x/zi după masă","duration":"10 zile","quantity":"20 compr."},{"name":"Omeprazol","dose":"20 mg","frequency":"1x/zi dimineața","duration":"10 zile","quantity":"10 capsule"}],"notes":"Ketoprofen doar în perioadele de acutizare. Obligatoriu gastroprotecție.","days":15},
        ],
    ]

    total_rx = 0
    for i, pat in enumerate(patient_list):
        doc = get_primary_doctor(pat)
        if not doc: continue
        for rx_tmpl in PRESCRIPTIONS[i % len(PRESCRIPTIONS)]:
            db.add(Prescription(
                id=uid(), patient_id=pat.id, doctor_id=doc.id,
                medications=rx_tmpl["meds"],
                notes=rx_tmpl["notes"],
                issued_at=ago(rx_tmpl["days"]),
                created_at=ago(rx_tmpl["days"]),
            ))
            total_rx += 1
    db.flush()
    print(f"   ✓ {total_rx} prescripții create")
else:
    print(f"   ✓ prescripțiile există deja ({existing_rx})")

# ─────────────────────────────────────────────────────────────────────────────
# 9. RECENZII
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 9. Recenzii ───────────────────────────────────────────────")
existing_reviews = db.query(Review).count()
if existing_reviews < 3:
    REVIEWS = [
        (5, "Domnul doctor Constantin este excepțional — empatic, răbdător și extrem de competent. A explicat în detaliu diagnosticul și fiecare opțiune de tratament. Mă simt în siguranță sub îngrijirea sa.", "pozitiv"),
        (5, "O experiență medicală cu adevărat profesionistă. Doctorul a identificat rapid problema și a propus un plan clar de tratament. Recomand cu toată căldura!", "pozitiv"),
        (4, "Consultație bună, dr. Ionescu a fost atent și thorough. Singurul minus a fost timpul de așteptare, dar serviciile medicale au compensat.", "pozitiv"),
        (5, "Dr. Popescu este un medic cu vocație reală. A luat în serios toate simptomele mele și mi-a explicat pe înțelesul meu. Mulțumesc din suflet!", "pozitiv"),
        (3, "Competent, dar consultația a fost scurtă. Mi-aș fi dorit mai mult timp pentru întrebări. Tratamentul prescris a funcționat.", "neutru"),
        (5, "Cel mai bun medic pe care l-am întâlnit. Abordare holistică, verifică tot, nu se grăbește. Merită fiecare minut din timp.", "pozitiv"),
    ]

    used_appts = set()
    total_rev = 0
    for i, pat in enumerate(patient_list):
        doc = get_primary_doctor(pat)
        if not doc: continue
        appt = db.query(Appointment).filter(
            Appointment.patient_id == pat.id,
            Appointment.doctor_id == doc.user_id,
            Appointment.status == 'completed',
            ~Appointment.id.in_(used_appts),
        ).first()
        if not appt: continue
        used_appts.add(appt.id)
        rating, comment, sentiment = REVIEWS[i % len(REVIEWS)]
        db.add(Review(
            id=uid(), patient_id=pat.id, doctor_id=doc.id,
            appointment_id=appt.id, rating=rating,
            comment=comment, sentiment=sentiment,
            created_at=appt.datetime + timedelta(hours=random.randint(3, 72)),
        ))
        total_rev += 1
    db.flush()
    print(f"   ✓ {total_rev} recenzii create")
else:
    print(f"   ✓ recenziile există deja ({existing_reviews})")

# ─────────────────────────────────────────────────────────────────────────────
# 10. MESAJE
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 10. Mesaje ────────────────────────────────────────────────")
existing_msgs = db.query(Message).count()
if existing_msgs < 5:
    CONVERSATIONS = [
        # Doctor 0 (Mihai Constantin) <-> Pacient 0 (Alin Mincu)
        (0, 0, [
            ("doc","pac","Bună ziua, domnule Mincu! Am analizat rezultatele analizelor dumneavoastră. Glicemia și HbA1c sunt îmbunătățite față de controlul anterior — progres bun!"),
            ("pac","doc","Bună ziua, doctor! Mă bucur să aud asta. Am respectat cu strictețe dieta și medicamentele. Tensiunea mai are momente în care e ridicată dimineața."),
            ("doc","pac","Normal pentru faza de ajustare. Luați Losartan-ul seara, înainte de culcare — aceasta îmbunătățește controlul matinal al tensiunii."),
            ("pac","doc","Înțeles, voi face asta. Mulțumesc mult pentru explicație!"),
            ("doc","pac","Cu plăcere. Ne vedem la control peste 4 săptămâni. Dacă apar valori >170/105, sunați imediat."),
        ]),
        # Doctor 1 (Alexandru Ionescu) <-> Pacient 2 (Andrei Marinescu)
        (1, 2, [
            ("pac","doc","Bună ziua dr. Ionescu, am avut azi o criză de astm după ce am jucat fotbal. Am folosit salbutamolul și a trecut, dar am fost speriat."),
            ("doc","pac","Bună ziua! Bine că salbutamolul a funcționat. Activitatea fizică intensă poate declanșa bronhospasm — vă recomand să folosiți 2 pufuri de salbutamol preventiv, cu 15 minute înainte de sport."),
            ("pac","doc","Nu știam asta! Mă poate ajuta și tehnica de respirație?"),
            ("doc","pac","Absolut — respirația diafragmatică și tehnica pursed-lip breathing sunt utile. Vă voi arăta la consultația de joi."),
            ("pac","doc","Perfect, vă mulțumesc! Joi la 10:00 sunt acolo."),
        ]),
        # Doctor 2 (Maria Popescu) <-> Pacient 3 (Ioana Popa)
        (2, 3, [
            ("doc","pac","Bună ziua, doamnă Popa! Rezultatele TSH-ului au venit — 2.1 mUI/L, perfect în limite normale. Levotiroxin-ul 75mcg funcționează bine."),
            ("pac","doc","Doamne, ce veste bună! Chiar mă simțeam mult mai bine în ultimele săptămâni — mai multă energie, am pierdut și 3kg."),
            ("doc","pac","Excelent! Exact cum trebuie. Continuați tratamentul fără întrerupere, chiar și când vă simțiți bine — hipotiroidismul necesită tratament pe termen lung."),
            ("pac","doc","Am înțeles. Pot să fac sport mai intens acum?"),
            ("doc","pac","Da, cu siguranță! Exercițiile moderate-intense sunt recomandate. Revenire la control în 6 luni pentru TSH de rutină."),
        ]),
        # Asistent (Daniela Vlad) <-> Doctor 0 (Mihai Constantin)
        (None, 0, [
            ("asist","doc","Bună dimineața, dr. Constantin! Am 4 programări pending pentru această săptămână care necesită confirmarea dvs.: Mincu luni 10:00, Niculescu marți 14:00, două altele joi."),
            ("doc","asist","Bună, Daniela! Le confirm pe toate. Vă rog să trimiteți notificările de confirmare pacienților și să adăugați în calendar."),
            ("asist","doc","Trimis! De asemenea, pacientul Bogdan Stan a sunat — dorește o programare de urgență, acuză dureri toracice."),
            ("doc","asist","Programați-l azi dacă e posibil, în intervalul 15:00-16:00. Durerea toracică necesită evaluare promptă."),
            ("asist","doc","L-am contactat, vine la 15:30. Am pregătit și fișa medicală pentru consultație."),
            ("doc","asist","Mulțumesc mult, Daniela! Profesionalism exemplar."),
        ]),
    ]

    total_msgs = 0
    for conv in CONVERSATIONS:
        doc_idx, pac_idx, messages = conv
        doc_user = doctors_u[doc_idx] if doc_idx is not None else None
        pac_user = patients_u[pac_idx] if pac_idx < len(patients_u) else None
        asist_user = assistants_u[0] if assistants_u else None

        def resolve(role):
            if role == "doc":    return doc_user
            if role == "pac":    return pac_user
            if role == "asist":  return asist_user
            return None

        base_time = ago(random.randint(2, 14), h=9)
        for idx, (sender_role, receiver_role, content) in enumerate(messages):
            s = resolve(sender_role); r = resolve(receiver_role)
            if not s or not r: continue
            db.add(Message(
                id=uid(), sender_id=s.id, receiver_id=r.id,
                content=content,
                is_read=(idx < len(messages) - 1),
                created_at=base_time + timedelta(minutes=idx * random.randint(3, 45)),
            ))
            total_msgs += 1
    db.flush()
    print(f"   ✓ {total_msgs} mesaje create")
else:
    print(f"   ✓ mesajele există deja ({existing_msgs})")

# ─────────────────────────────────────────────────────────────────────────────
# 11. NOTIFICĂRI
# ─────────────────────────────────────────────────────────────────────────────
print("\n── 11. Notificări ────────────────────────────────────────────")
existing_notifs = db.query(Notification).count()
if existing_notifs < 5:
    NOTIFICATIONS = [
        # Pentru pacienți
        (0, "appointment", "Programare confirmată", "Programarea dvs. de luni la 10:00 cu Dr. Mihai Constantin a fost confirmată.", False, 1),
        (0, "warning",     "Semne vitale — alertă", "Tensiunea arterială înregistrată ieri (168/104 mmHg) depășește limitele normale. Contactați medicul.", False, 3),
        (0, "info",        "Rețetă disponibilă", "Dr. Constantin a eliberat o nouă rețetă pentru dvs. O puteți vizualiza în secțiunea Rețete.", True, 5),
        (1, "appointment", "Programare confirmată", "Consultația de marți la 14:00 cu Dr. Alexandru Ionescu a fost confirmată.", False, 1),
        (1, "info",        "Rezultate analize disponibile", "Rezultatele analizelor de sânge din 15 mai sunt acum disponibile în fișa dvs. medicală.", False, 2),
        (2, "warning",     "Control periodic recomandat", "Nu ați mai avut o consultație în ultimele 60 de zile. Programați un control de rutină.", False, 4),
        (3, "appointment", "Reamintire programare", "Mâine la 11:00 aveți consultație cu Dr. Maria Popescu. Vă rugăm să veniți cu 10 min mai devreme.", False, 0),
        (3, "info",        "Tratament actualizat", "Schema dvs. de tratament a fost actualizată. Consultați secțiunea Tratamente pentru detalii.", True, 7),
        # Pentru doctori
        (None, "appointment", "Programare nouă", "Pacientul Bogdan Stan a solicitat o programare de urgență pentru astăzi.", False, 0, "doc0"),
        (None, "info",        "Recenzie nouă primită", "Ați primit o recenzie de 5 stele de la pacientul Alin Mincu.", True, 2, "doc0"),
    ]

    total_notifs = 0
    for notif_data in NOTIFICATIONS:
        if len(notif_data) == 6:
            pac_idx, ntype, title, message, read, days_a = notif_data
            if pac_idx < len(patients_u):
                user = patients_u[pac_idx]
            else:
                continue
        else:
            _, ntype, title, message, read, days_a, target = notif_data
            user = doctors_u[0]

        db.add(Notification(
            id=uid(), user_id=user.id,
            notification_type=ntype, title=title,
            message=message, read=read,
            created_at=ago(days_a, h=random.randint(8,18)),
        ))
        total_notifs += 1
    db.flush()
    print(f"   ✓ {total_notifs} notificări create")
else:
    print(f"   ✓ notificările există deja ({existing_notifs})")

# ─────────────────────────────────────────────────────────────────────────────
# COMMIT
# ─────────────────────────────────────────────────────────────────────────────
db.commit()

print("\n" + "="*60)
print("✅  Seed complet! Baza de date populată cu succes.")
print("="*60)
print("\n📊 Rezumat:")
print(f"   Utilizatori:            {db.query(User).count()}")
print(f"   Doctori (profil):       {db.query(Doctor).count()}")
print(f"   Pacienți (profil):      {db.query(Patient).count()}")
print(f"   Atribuiri doc-pacient:  {db.query(DoctorPatient).count()}")
print(f"   Programări:             {db.query(Appointment).count()}")
print(f"   Fișe medicale:          {db.query(MedicalRecord).count()}")
print(f"   Semne vitale:           {db.query(VitalSign).count()}")
print(f"   Prescripții:            {db.query(Prescription).count()}")
print(f"   Recenzii:               {db.query(Review).count()}")
print(f"   Mesaje:                 {db.query(Message).count()}")
print(f"   Notificări:             {db.query(Notification).count()}")
print("\n🔑 Conturi demo (parola: Parola123!):")
print("   admin@medilink.com        — Admin")
print("   doctor@medilink.com       — Dr. Mihai Constantin (cardiologie)")
print("   alexandru.ionescu@gmail.com — Dr. Alexandru Ionescu (neurologie)")
print("   maria.popescu@gmail.com   — Dr. Maria Popescu (medicină internă)")
print("   asistent@medilink.com     — Daniela Vlad")
print("   pacient@medilink.com      — Alin Mincu")
