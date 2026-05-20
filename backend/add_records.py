"""
Adaugă fișe medicale realiste pentru toți pacienții — consultații, analize, tratamente, investigații.
"""
import sys, os, uuid, random
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

# ── Date per pacient ──────────────────────────────────────────────────────────
PATIENT_RECORDS = {

    'pacient@medilink.com': {  # Alin Mincu — diabet tip 2, boală coronariană, dislipidemie
        'records': [
            {
                'record_type': 'consultatie', 'days_ago': 120,
                'diagnosis': 'Diabet zaharat tip 2 — debut recent',
                'treatment': 'Metformin 500mg x2/zi, dietă hipoglucidică, automonitorizare glicemie',
                'notes': 'Pacient diagnosticat cu diabet zaharat tip 2. TA 145/90 mmHg. Greutate 88 kg, IMC 30.2. Se inițiează Metformin în doză mică cu titrare progresivă.',
                'has_anomaly': True, 'anomaly_notes': 'Debut diabet zaharat tip 2 — necesită monitorizare intensivă',
            },
            {
                'record_type': 'analiza', 'days_ago': 115,
                'analysis_result': 'Glicemie bazală: 168 mg/dL (crescut), HbA1c: 8.4% (crescut), Insulinemie: 18.2 μUI/mL, Colesterol total: 238 mg/dL, LDL: 158 mg/dL, HDL: 38 mg/dL, Trigliceride: 210 mg/dL',
                'notes': 'Profil glucido-lipidic semnificativ alterat la debut. Se inițiază tratament hipolipemiant.',
                'has_anomaly': True, 'anomaly_notes': 'HbA1c 8.4% și profil lipidic aterogen — risc cardiovascular crescut',
            },
            {
                'record_type': 'tratament', 'days_ago': 110,
                'diagnosis': 'Dislipidemie mixtă, Hipertensiune arterială grad I',
                'treatment': 'Atorvastatină 20mg seara, Ramipril 5mg/zi dimineața, Aspirină 100mg/zi',
                'notes': 'Adăugat tratament cardioprotector. Obiectiv LDL < 70 mg/dL. TA țintă < 130/80 mmHg.',
                'has_anomaly': False,
            },
            {
                'record_type': 'investigatie', 'days_ago': 90,
                'diagnosis': 'Evaluare complicații cardiovasculare diabet',
                'analysis_result': 'EKG: ritm sinusal 78/min, ax normal, fără modificări ischemice acute. Ecografie abdominală: ficat ușor mărit, ecogenitate crescută (steatoză grad I). Ecocardiografie: FE 58%, HVS ușoară.',
                'notes': 'Steatoză hepatică nonalcoolică asociată diabetului. Hipertrofie ventriculară stângă ușoară. Se menține schema terapeutică.',
                'has_anomaly': True, 'anomaly_notes': 'Steatoză hepatică grad I + HVS ușoară — complicații metabolice incipiente',
            },
            {
                'record_type': 'consultatie', 'days_ago': 60,
                'diagnosis': 'Diabet zaharat tip 2 — control periodic',
                'treatment': 'Metformin 1000mg x2/zi (titrare crescută), Sitagliptin 100mg/zi adăugat, Atorvastatină 40mg',
                'notes': 'Control la 2 luni. HbA1c la ultimele analize 8.4% — se intensifică tratamentul. Pacientul respectă dieta. TA 132/82 mmHg, bine controlată.',
                'has_anomaly': False,
            },
            {
                'record_type': 'analiza', 'days_ago': 55,
                'analysis_result': 'Glicemie bazală: 142 mg/dL, HbA1c: 7.8% (ușor îmbunătățit), Creatinină: 1.1 mg/dL, eRFG: 78 mL/min/1.73m², Microalbuminurie: 35 mg/g (limită), LDL: 112 mg/dL, HDL: 42 mg/dL',
                'notes': 'Tendință de ameliorare a controlului glicemic. Funcție renală la limită inferioară — monitorizare la 6 luni.',
                'has_anomaly': True, 'anomaly_notes': 'Microalbuminurie borderline — risc nefropatie diabetică incipientă',
            },
        ],
        'prescriptions': [
            {
                'days_ago': 55,
                'medications': [
                    {"name": "Metformin", "dose": "1000 mg", "frequency": "2x/zi cu masa (dimineața și seara)", "duration": "90 zile", "quantity": "180 comprimate"},
                    {"name": "Sitagliptin", "dose": "100 mg", "frequency": "1x/zi dimineața", "duration": "90 zile", "quantity": "90 comprimate"},
                    {"name": "Atorvastatină", "dose": "40 mg", "frequency": "1x/zi seara", "duration": "90 zile", "quantity": "90 comprimate"},
                    {"name": "Ramipril", "dose": "5 mg", "frequency": "1x/zi dimineața", "duration": "90 zile", "quantity": "90 comprimate"},
                    {"name": "Aspirină", "dose": "100 mg", "frequency": "1x/zi cu masa de prânz", "duration": "90 zile", "quantity": "90 comprimate"},
                ],
                'notes': 'Tratament cronic pentru diabet, hipertensiune și dislipidemie. Monitorizare glicemie zilnică. Control la 3 luni.',
            },
        ],
    },

    'luminita.niculescu@yahoo.ro': {  # Luminița Niculescu — spondiloză cervicală
        'records': [
            {
                'record_type': 'consultatie', 'days_ago': 100,
                'diagnosis': 'Spondiloză cervicală C4-C5, C5-C6 cu sindrom algic',
                'treatment': 'Ketoprofen 100mg 2x/zi (7 zile), Tolperizon 150mg 2x/zi (30 zile), Vitamina B complex, kinetoterapie 10 ședințe',
                'notes': 'Pacientă cu dureri cervicale cu iradiere în membrul superior drept de 3 luni. Parestezii în degetele 1-3 mână dreaptă. IRM cervical recomandat urgent.',
                'has_anomaly': True, 'anomaly_notes': 'Radiculopatie C5-C6 — indicat IRM coloană cervicală',
            },
            {
                'record_type': 'investigatie', 'days_ago': 90,
                'diagnosis': 'Spondiloză cervicală C4-C6',
                'analysis_result': 'IRM coloană cervicală: disc herniat C4-C5 cu indentare durală, disc protrudat C5-C6. Stenoză foraminală dreaptă C5-C6 responsabilă de radiculopatie. Fără semne de compresie medulară.',
                'notes': 'Confirmat IRM: hernie discală C4-C5 și protruzie C5-C6 cu stenoză foraminală. Se continuă tratamentul conservator. Reevaluare neurochirurgicală dacă nu ameliorare în 6 săptămâni.',
                'has_anomaly': True, 'anomaly_notes': 'Hernie disc C4-C5 și stenoză foraminală C5-C6 confirmate IRM',
            },
            {
                'record_type': 'tratament', 'days_ago': 85,
                'diagnosis': 'Sindrom cervicobrahial drept pe fond de spondiloză',
                'treatment': 'Etoricoxib 90mg/zi (14 zile), Pregabalinum 75mg x2/zi (30 zile), Tizanidinum 2mg seara, TENS cervical 10 ședințe',
                'notes': 'Modificat schema — AINS mai potent + pregabalinum pentru durere neuropatică. Pacienta a finalizat kinetoterapia cu ameliorare parțială. Fizioterapie TENS recomandată.',
                'has_anomaly': False,
            },
            {
                'record_type': 'analiza', 'days_ago': 70,
                'analysis_result': 'Hemoleucogramă completă: normală. VSH: 18 mm/h, CRP: 4.2 mg/L (ușor crescut), Factor reumatoid: negativ, Acid uric: 4.8 mg/dL. Calciu seric: 9.1 mg/dL, Vit D3: 28 ng/mL (insuficient).',
                'notes': 'Inflamație ușoară de fond. Vitamina D insuficientă — se adaugă suplimentare. Factor reumatoid negativ exclude patologie autoimună.',
                'has_anomaly': False,
            },
            {
                'record_type': 'consultatie', 'days_ago': 30,
                'diagnosis': 'Spondiloză cervicală — control la 2 luni',
                'treatment': 'Vitamina D3 2000 UI/zi, Calciu 500mg/zi, kinetoterapie de întreținere 2x/săptămână',
                'notes': 'Ameliorare semnificativă a durerilor după tratament. Paresteziile mai rare. Se scoate Pregabalinum, se continuă tratament de fond cu suplimentare calcică și vitamina D.',
                'has_anomaly': False,
            },
        ],
        'prescriptions': [
            {
                'days_ago': 85,
                'medications': [
                    {"name": "Etoricoxib", "dose": "90 mg", "frequency": "1x/zi cu masa", "duration": "14 zile", "quantity": "14 comprimate"},
                    {"name": "Pregabalinum", "dose": "75 mg", "frequency": "2x/zi (dimineața și seara)", "duration": "30 zile", "quantity": "60 capsule"},
                    {"name": "Tizanidinum", "dose": "2 mg", "frequency": "1x/zi seara", "duration": "30 zile", "quantity": "30 comprimate"},
                ],
                'notes': 'Tratament sindrom cervicobrahial. Nu se asociază cu alcool. Se evită conducerea auto în primele zile (Tizanidinum).',
            },
        ],
    },

    'andrei.marinescu@gmail.com': {  # Andrei Marinescu — hipertensiune, diabet tip 2
        'records': [
            {
                'record_type': 'consultatie', 'days_ago': 95,
                'diagnosis': 'Hipertensiune arterială esențială grad II, Diabet zaharat tip 2',
                'treatment': 'Amlodipina 10mg/zi, Losartan 100mg/zi, Metformin 1000mg x2/zi, Aspirină 100mg/zi',
                'notes': 'Pacient cu TA 168/102 mmHg la prezentare. Glicemie 154 mg/dL. Tratament ajustat — doze maxime antihipertensive. Monitorizare la 4 săptămâni.',
                'has_anomaly': True, 'anomaly_notes': 'TA 168/102 mmHg — HTA necontrolată, risc cardiovascular înalt',
            },
            {
                'record_type': 'analiza', 'days_ago': 88,
                'analysis_result': 'Glicemie: 154 mg/dL (crescut), HbA1c: 8.1% (crescut), Creatinină: 1.2 mg/dL, Potasiu: 4.1 mEq/L, Sodiu: 139 mEq/L, Colesterol total: 242 mg/dL, LDL: 168 mg/dL, Trigliceride: 196 mg/dL, Microalbuminurie: 42 mg/g (crescut)',
                'notes': 'Profil cardiometabolic alterat: HTA necontrolată, diabet dezechilibrat, dislipidemie, nefropatie incipientă.',
                'has_anomaly': True, 'anomaly_notes': 'HbA1c 8.1%, microalbuminurie crescută — nefropatie diabetică stadiu incipient',
            },
            {
                'record_type': 'tratament', 'days_ago': 85,
                'diagnosis': 'Nefropatie diabetică stadiu I, Dislipidemie',
                'treatment': 'Rosuvastatină 20mg seara, Ezetimib 10mg seara (asociat), Ramipril 10mg/zi (nefroproteție)',
                'notes': 'Adăugat tratament nefroprotetor și hipolipemiant intensificat. Obiectiv LDL < 55 mg/dL (risc foarte înalt). Restricție sodiu < 5g/zi.',
                'has_anomaly': False,
            },
            {
                'record_type': 'consultatie', 'days_ago': 50,
                'diagnosis': 'HTA + DZ tip 2 — control periodic',
                'treatment': 'Continuare schema actuală, adăugat Bisoprolol 5mg/zi pentru control FC',
                'notes': 'TA la control 142/88 mmHg — ameliorare parțială. FC 92/min. Se adaugă betablocant. Glicemie 138 mg/dL. Pacientul respectă dieta. Activitate fizică moderată 30 min/zi.',
                'has_anomaly': False,
            },
            {
                'record_type': 'analiza', 'days_ago': 25,
                'analysis_result': 'HbA1c: 7.3% (ameliorat față de 8.1%), LDL: 98 mg/dL (ameliorat), Creatinină: 1.15 mg/dL, eRFG: 72 mL/min, Microalbuminurie: 28 mg/g (ameliorată), Potasiu: 4.4 mEq/L.',
                'notes': 'Ameliorare semnificativă a profilului cardiometabolic la 3 luni. Se continuă schema, cu obiectiv LDL < 55 mg/dL.',
                'has_anomaly': False,
            },
            {
                'record_type': 'investigatie', 'days_ago': 15,
                'diagnosis': 'Evaluare fond de ochi — complicații oculare DZ',
                'analysis_result': 'Examen fund de ochi: retinopatie diabetică neproliferativă ușoară bilateral — microanevrisme rare foveal. Cristalin transparent. AV: 10/10 bilateral. Oftalmolog recomandă control anual.',
                'notes': 'Retinopatie diabetică stadiu incipient detectată. Pacientul informat. Control oftalmologic anual obligatoriu.',
                'has_anomaly': True, 'anomaly_notes': 'Retinopatie diabetică neproliferativă ușoară — monitorizare anuală',
            },
        ],
        'prescriptions': [
            {
                'days_ago': 50,
                'medications': [
                    {"name": "Amlodipina", "dose": "10 mg", "frequency": "1x/zi dimineața", "duration": "90 zile", "quantity": "90 comprimate"},
                    {"name": "Losartan", "dose": "100 mg", "frequency": "1x/zi seara", "duration": "90 zile", "quantity": "90 comprimate"},
                    {"name": "Bisoprolol", "dose": "5 mg", "frequency": "1x/zi dimineața", "duration": "90 zile", "quantity": "90 comprimate"},
                    {"name": "Metformin", "dose": "1000 mg", "frequency": "2x/zi cu masa", "duration": "90 zile", "quantity": "180 comprimate"},
                    {"name": "Rosuvastatină", "dose": "20 mg", "frequency": "1x/zi seara", "duration": "90 zile", "quantity": "90 comprimate"},
                ],
                'notes': 'Tratament complex cardiometabolic. Se verifică electroliți la 4 săptămâni (Ramipril + diuretic).',
            },
        ],
    },

    'ioana.popa@hotmail.com': {  # Ioana Popa — astm bronșic, fără cronice altele
        'records': [
            {
                'record_type': 'consultatie', 'days_ago': 110,
                'diagnosis': 'Astm bronșic alergic moderat persistent — exacerbare',
                'treatment': 'Prednisolon 40mg/zi x5 zile (cură scurtă), Salbutamol nebulizare 2.5mg x4/zi, Montelukast 10mg seara',
                'notes': 'Pacientă cu exacerbare astm — 4 zile dispnee progresivă, wheezing, tuse nocturnă. SpO2 94% la prezentare. Se inițiază tratament de atac.',
                'has_anomaly': True, 'anomaly_notes': 'Exacerbare astm bronșic — SpO2 94%, necesită monitorizare',
            },
            {
                'record_type': 'analiza', 'days_ago': 100,
                'analysis_result': 'Spirometrie post-bronhodilatator: VEMS 71% din prezis, VEMS/CVF 69% — obstrucție ușoară-moderată persistentă. Prick test alergen: pozitiv pentru acarieni, polen graminee, păr pisică. IgE specific D. pteronyssinus: 8.4 kUA/L (crescut).',
                'notes': 'Confirmat astm alergic la acarieni și graminee. Se recomandă imunoterapie specifică (desensibilizare) la alergolog.',
                'has_anomaly': True, 'anomaly_notes': 'Sensibilizare multiplă confirmată — candidată imunoterapie specifică',
            },
            {
                'record_type': 'tratament', 'days_ago': 95,
                'diagnosis': 'Astm bronșic alergic — tratament de fond',
                'treatment': 'Fluticazonă/Salmeterol 250/25 mcg x2 pufuri x2/zi, Montelukast 10mg seara, Salbutamol spray la nevoie (max 4x/zi), Loratadină 10mg/zi',
                'notes': 'Schema de fond ajustată. Pacienta instruită tehnica inhalatorie, utilizarea spacer-ului. Evitarea alergenilor: saltele anticarieni, filtru HEPA. Jurnal simptome recomandat.',
                'has_anomaly': False,
            },
            {
                'record_type': 'investigatie', 'days_ago': 60,
                'diagnosis': 'Evaluare control astm bronșic',
                'analysis_result': 'Peak flow: 78% din optim personal (ameliorat față de 65% în exacerbare). Pulsoximetrie: SpO2 98% în repaus. Radiografie torace: hiperinflație ușoară, fără infiltrate.',
                'notes': 'Astm parțial controlat. Peak flow ameliorat. Se menține schema actuală. Reevaluare spirometrie la 6 luni.',
                'has_anomaly': False,
            },
            {
                'record_type': 'consultatie', 'days_ago': 20,
                'diagnosis': 'Astm bronșic — control periodic trimestrial',
                'treatment': 'Schema neschimbată. Adăugat Vitamina D3 1000 UI/zi (nivel seric scăzut).',
                'notes': 'Pacientă stabilă, simptome bine controlate cu terapia curentă. Fără exacerbări în ultimele 2 luni. Se reduce treapta terapeutică la următoarea vizită dacă control menținut.',
                'has_anomaly': False,
            },
        ],
        'prescriptions': [
            {
                'days_ago': 95,
                'medications': [
                    {"name": "Fluticazonă/Salmeterol spray", "dose": "250/25 mcg", "frequency": "2 pufuri de 2x/zi (dimineața și seara)", "duration": "60 zile", "quantity": "2 flacoane"},
                    {"name": "Salbutamol spray", "dose": "100 mcg/puf", "frequency": "2 pufuri la nevoie, max 4x/zi", "duration": "60 zile", "quantity": "2 flacoane"},
                    {"name": "Montelukast", "dose": "10 mg", "frequency": "1x/zi seara", "duration": "90 zile", "quantity": "90 comprimate"},
                    {"name": "Loratadină", "dose": "10 mg", "frequency": "1x/zi dimineața", "duration": "30 zile", "quantity": "30 comprimate"},
                ],
                'notes': 'Tratament astm alergic. A nu se opri corticosteroizii inhalatori fără aviz medical. Tehnica inhalatorie corectă obligatorie.',
            },
        ],
    },
}

# ── Ștergere fișe existente și adăugare date noi ──────────────────────────────
total_added_records = 0
total_added_rx = 0

for email, data in PATIENT_RECORDS.items():
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f'  USER NOT FOUND: {email}')
        continue
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        print(f'  PATIENT NOT FOUND: {email}')
        continue
    dp = db.query(DoctorPatient).filter(DoctorPatient.patient_id == patient.id).first()
    if not dp:
        print(f'  NO DOCTOR for {email}')
        continue
    doc = db.query(Doctor).filter(Doctor.id == dp.doctor_id).first()
    doc_user_id = doc.user_id

    # Șterge toate fișele existente pentru pacientul curent
    existing = db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient.id).all()
    for r in existing:
        db.delete(r)

    # Șterge toate prescripțiile existente
    existing_rx = db.query(Prescription).filter(Prescription.patient_id == patient.id).all()
    for r in existing_rx:
        db.delete(r)

    db.flush()

    # Adaugă fișele noi
    for rec in data.get('records', []):
        mr = MedicalRecord(
            id=uid(),
            patient_id=patient.id,
            doctor_id=doc_user_id,
            record_type=rec['record_type'],
            diagnosis=rec.get('diagnosis'),
            treatment=rec.get('treatment'),
            analysis_result=rec.get('analysis_result'),
            notes_encrypted=rec.get('notes'),
            has_anomaly=rec.get('has_anomaly', False),
            anomaly_notes=rec.get('anomaly_notes'),
            created_at=days_ago(rec['days_ago'], hour=random.choice([9,10,11,14,15,16])),
        )
        db.add(mr)
        total_added_records += 1

    # Adaugă prescripțiile noi
    for rx_data in data.get('prescriptions', []):
        rx = Prescription(
            id=uid(),
            patient_id=patient.id,
            doctor_id=dp.doctor_id,
            medications=rx_data['medications'],
            notes=rx_data['notes'],
            issued_at=days_ago(rx_data['days_ago']),
            created_at=days_ago(rx_data['days_ago']),
        )
        db.add(rx)
        total_added_rx += 1

    db.flush()
    print(f'✓ {user.first_name} {user.last_name}: {len(data["records"])} fișe + {len(data.get("prescriptions", []))} prescripții')

db.commit()
print(f'\n✅ Total: {total_added_records} fișe medicale + {total_added_rx} prescripții adăugate')

# Sumar
from sqlalchemy import text as sqlt
rows = db.execute(sqlt('''
    SELECT u.first_name, u.last_name, mr.record_type, COUNT(*) as cnt
    FROM medical_records mr
    JOIN patients p ON mr.patient_id = p.id
    JOIN users u ON p.user_id = u.id
    GROUP BY u.first_name, u.last_name, mr.record_type
    ORDER BY u.last_name, mr.record_type
''')).fetchall()
print('\n📊 Sumar final:')
for r in rows:
    print(f'  {r[0]} {r[1]}: [{r[2]}] x{r[3]}')
