from sqlalchemy import create_engine, text
engine = create_engine('postgresql://medilink_user:medilink_pass@db:5432/medilink')

def s(v, n=40):
    return str(v)[:n] if v else '-'

with engine.connect() as conn:
    print('=== APPOINTMENTS (toate, ordonate descendent) ===')
    r = conn.execute(text('''
        SELECT a.id, a.status, a.datetime, a.reason, a.notes,
               u_d.first_name||' '||u_d.last_name as doc,
               u_p.first_name||' '||u_p.last_name as pat
        FROM appointments a
        JOIN users u_d ON a.doctor_id=u_d.id
        JOIN patients p ON a.patient_id=p.id
        JOIN users u_p ON p.user_id=u_p.id
        ORDER BY a.datetime DESC
    '''))
    for i, row in enumerate(r):
        print(f'  {i+1:2}. [{row[1]}] {s(row[2],16)} | Dr.{row[5]} -> {row[6]} | {s(row[3],40)} | notes:{s(row[4],25)}')

    print()
    print('=== MESSAGES ===')
    r = conn.execute(text('''
        SELECT u_s.first_name||' '||u_s.last_name, u_r.first_name||' '||u_r.last_name, m.content, m.created_at
        FROM messages m
        JOIN users u_s ON m.sender_id=u_s.id
        JOIN users u_r ON m.receiver_id=u_r.id
        ORDER BY m.created_at
    '''))
    for row in r:
        print(f'  {s(row[3],16)} | {row[0]} -> {row[1]}: {s(row[2],70)}')
