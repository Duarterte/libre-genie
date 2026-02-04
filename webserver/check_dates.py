import lg_db
import datetime

try:
    lg_db.init_db()
    with lg_db._pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, start_time FROM calendar_events;")
            rows = cur.fetchall()
            print("Current Events in DB:")
            for r in rows:
                print(f"[{r[0]}] {r[1]} : {r[2]}")

except Exception as e:
    print(e)
