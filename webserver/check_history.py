import lg_db
import json

try:
    lg_db.init_db()
    with lg_db._pool.connection() as conn:
        with conn.cursor() as cur:
            # mimic exactly what server does
            cur.execute("SELECT client_id, role, content FROM chat_history ORDER BY timestamp ASC;")
            rows = cur.fetchall()
            print(f"Total rows: {len(rows)}")
            for i, r in enumerate(rows):
                print(f"[{i}] Role: {r[1]}")
                print(f"    Type: {type(r[2])}")
                print(f"    Content Start: {str(r[2])[:50]}...")
                
                if isinstance(r[2], (list, dict, tuple)):
                    print("    WARNING: IT IS A SEQUENCE/OBJECT!")

except Exception as e:
    print(e)
