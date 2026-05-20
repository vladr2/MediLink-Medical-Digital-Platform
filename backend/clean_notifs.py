from sqlalchemy import create_engine, text
engine = create_engine('postgresql://medilink_user:medilink_pass@db:5432/medilink')
with engine.connect() as conn:
    # Sterge notificarile cu temperatura critica invalida (45 grade)
    r = conn.execute(text("""
        DELETE FROM notifications
        WHERE message LIKE '%45.0%' OR message LIKE '%Hai la control%' OR message LIKE '%da mi control%'
        RETURNING id, title, message
    """))
    rows = list(r)
    conn.commit()
    print(f'Sterse {len(rows)} notificari invalide:')
    for row in rows:
        print(f'  [{row[1]}] {str(row[2])[:60]}')

    # Marcheaza toate ca citite (pentru un start curat)
    r2 = conn.execute(text("SELECT COUNT(*) FROM notifications WHERE read = false"))
    unread = r2.scalar()
    print(f'\nNotificari necitite ramase: {unread}')

    r3 = conn.execute(text("SELECT COUNT(*) FROM notifications"))
    print(f'Total notificari: {r3.scalar()}')
