from sqlalchemy import create_engine, text

engine = create_engine('postgresql://medilink_user:medilink_pass@db:5432/medilink')

def s(v, maxlen=60):
    """Safe string: handle None and truncate."""
    if v is None:
        return 'None'
    return str(v)[:maxlen]

with engine.connect() as conn:
    print('=== USERS ===')
    r = conn.execute(text('SELECT email, first_name, last_name, role, phone, birth_date FROM users ORDER BY role, email'))
    for row in r:
        fn = row[1] or '???'
        ln = row[2] or '???'
        print(f'  [{row[3]}] {fn} {ln} | {row[0]} | phone={row[4]} | birth={row[5]}')

    print()
    print('=== DOCTOR PROFILES ===')
    r = conn.execute(text('SELECT u.email, d.specialization, d.license_number, d.department, d.schedule, d.bio FROM doctors d JOIN users u ON d.user_id=u.id'))
    for row in r:
        bio = s(row[5], 80)
        print(f'  {row[0]}: spec={row[1]} | lic={row[2]} | dept={row[3]} | {row[4]}')
        print(f'    bio: {bio}')

    print()
    print('=== PATIENT PROFILES ===')
    r = conn.execute(text('SELECT u.email, u.first_name, u.last_name, p.blood_type, p.gender, p.allergies, p.chronic_conditions FROM patients p JOIN users u ON p.user_id=u.id'))
    for row in r:
        fn = row[1] or '???'
        ln = row[2] or '???'
        # allergies & chronic are encrypted — just check if present
        has_alerg = 'DA' if row[5] else 'nu'
        has_cronic = 'DA' if row[6] else 'nu'
        print(f'  {fn} {ln} | {row[0]} | blood={row[3]} | gender={row[4]} | alergii={has_alerg} | cronice={has_cronic}')

    print()
    print('=== DOCTOR-PATIENT ASSIGNMENTS ===')
    r = conn.execute(text('''
        SELECT u_d.first_name, u_d.last_name, u_p.first_name, u_p.last_name
        FROM doctor_patients dp
        JOIN doctors d ON dp.doctor_id=d.id
        JOIN users u_d ON d.user_id=u_d.id
        JOIN patients p ON dp.patient_id=p.id
        JOIN users u_p ON p.user_id=u_p.id
        ORDER BY u_d.last_name, u_p.last_name
    '''))
    for row in r:
        doc = (row[0] or '') + ' ' + (row[1] or '')
        pat = (row[2] or '') + ' ' + (row[3] or '')
        print(f'  Dr. {doc.strip()} -> {pat.strip()}')

    print()
    print('=== APPOINTMENTS ===')
    r = conn.execute(text('SELECT status, COUNT(*) FROM appointments GROUP BY status ORDER BY status'))
    for row in r:
        print(f'  {row[0]}: {row[1]}')

    r = conn.execute(text('''
        SELECT a.status, a.datetime, a.reason, u_d.first_name, u_d.last_name, u_p.first_name, u_p.last_name
        FROM appointments a
        JOIN users u_d ON a.doctor_id=u_d.id
        JOIN patients p ON a.patient_id=p.id
        JOIN users u_p ON p.user_id=u_p.id
        ORDER BY a.datetime DESC LIMIT 12
    '''))
    print('  (sample 12 recent):')
    for row in r:
        doc = (row[3] or '') + ' ' + (row[4] or '')
        pat = (row[5] or '') + ' ' + (row[6] or '')
        reason = s(row[2], 50)
        print(f'    [{row[0]}] {str(row[1])[:16]} | Dr.{doc.strip()} -> {pat.strip()} | {reason}')

    print()
    print('=== MEDICAL RECORDS ===')
    r = conn.execute(text('''
        SELECT mr.record_type, mr.has_anomaly, mr.anomaly_notes, mr.created_at,
               u_p.first_name, u_p.last_name, u_d.first_name, u_d.last_name
        FROM medical_records mr
        JOIN patients p ON mr.patient_id=p.id
        JOIN users u_p ON p.user_id=u_p.id
        JOIN users u_d ON mr.doctor_id=u_d.id
        ORDER BY mr.created_at DESC
    '''))
    for row in r:
        flag = 'ANOMALIE' if row[1] else 'ok'
        pat = (row[4] or '') + ' ' + (row[5] or '')
        doc = (row[6] or '') + ' ' + (row[7] or '')
        note = s(row[2], 50)
        print(f'  [{row[0]}] {flag} | {pat.strip()} <- Dr.{doc.strip()} | {str(row[3])[:10]} | {note}')

    print()
    print('=== PRESCRIPTIONS ===')
    r = conn.execute(text('''
        SELECT u_p.first_name, u_p.last_name, u_d.first_name, u_d.last_name, rx.medications, rx.issued_at
        FROM prescriptions rx
        JOIN patients p ON rx.patient_id=p.id
        JOIN users u_p ON p.user_id=u_p.id
        JOIN doctors d ON rx.doctor_id=d.id
        JOIN users u_d ON d.user_id=u_d.id
        ORDER BY rx.issued_at DESC
    '''))
    for row in r:
        pat = (row[0] or '') + ' ' + (row[1] or '')
        doc = (row[2] or '') + ' ' + (row[3] or '')
        meds = row[4]
        names = [m.get('name', '?') for m in meds] if isinstance(meds, list) else []
        print(f'  {pat.strip()} <- Dr.{doc.strip()} | {str(row[5])[:10]} | {names}')

    print()
    print('=== VITAL SIGNS (per patient per type) ===')
    r = conn.execute(text('''
        SELECT u.first_name, u.last_name, vs.vital_type, COUNT(*) as cnt,
               ROUND(MIN(vs.value)::numeric,1) as mn, ROUND(MAX(vs.value)::numeric,1) as mx
        FROM vital_signs vs
        JOIN patients p ON vs.patient_id=p.id
        JOIN users u ON p.user_id=u.id
        GROUP BY u.first_name, u.last_name, vs.vital_type
        ORDER BY u.last_name, vs.vital_type
    '''))
    for row in r:
        pat = (row[0] or '') + ' ' + (row[1] or '')
        print(f'  {pat.strip()} | {row[2]}: {row[3]} citiri [{row[4]}-{row[5]}]')

    print()
    print('=== REVIEWS ===')
    r = conn.execute(text('''
        SELECT rv.rating, rv.comment, u_p.first_name, u_p.last_name, u_d.first_name, u_d.last_name
        FROM reviews rv
        JOIN patients p ON rv.patient_id=p.id
        JOIN users u_p ON p.user_id=u_p.id
        JOIN doctors d ON rv.doctor_id=d.id
        JOIN users u_d ON d.user_id=u_d.id
    '''))
    rows = list(r)
    if rows:
        for row in rows:
            pat = (row[2] or '') + ' ' + (row[3] or '')
            doc = (row[4] or '') + ' ' + (row[5] or '')
            comment = s(row[1], 70)
            print(f'  {pat.strip()} -> Dr.{doc.strip()}: {row[0]}/5 | {comment}')
    else:
        print('  (nicio recenzie)')

    print()
    print('=== MESSAGES ===')
    r = conn.execute(text('''
        SELECT u_s.first_name, u_s.last_name, u_r.first_name, u_r.last_name, m.content, m.is_read
        FROM messages m
        JOIN users u_s ON m.sender_id=u_s.id
        JOIN users u_r ON m.receiver_id=u_r.id
        ORDER BY m.created_at
    '''))
    for row in r:
        sender = (row[0] or '') + ' ' + (row[1] or '')
        recv   = (row[2] or '') + ' ' + (row[3] or '')
        icon = 'citit' if row[5] else 'NECITIT'
        print(f'  [{icon}] {sender.strip()} -> {recv.strip()}: {s(row[4], 65)}')

    print()
    print('=== COUNTS SUMMARY ===')
    for tbl in ['users','doctors','patients','doctor_patients','appointments','medical_records','vital_signs','prescriptions','reviews','messages']:
        cnt = conn.execute(text(f'SELECT COUNT(*) FROM {tbl}')).scalar()
        print(f'  {tbl}: {cnt}')
