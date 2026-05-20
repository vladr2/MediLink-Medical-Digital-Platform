from sqlalchemy import create_engine, text

engine = create_engine('postgresql://medilink_user:medilink_pass@db:5432/medilink')
with engine.connect() as conn:
    sql = "UPDATE appointments SET status = 'cancelled' WHERE status = 'pending' AND datetime < NOW() RETURNING id, datetime"
    r = conn.execute(text(sql))
    rows = list(r)
    conn.commit()
    print(f'Auto-anulate {len(rows)} programari pending expirate')
    for row in rows:
        print(f'  {str(row[1])[:16]}')

    r2 = conn.execute(text('SELECT status, COUNT(*) FROM appointments GROUP BY status ORDER BY status'))
    print('\nStatus-uri finale:')
    for row in r2:
        print(f'  {row[0]}: {row[1]}')
