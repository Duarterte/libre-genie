import lg_db
import datetime

try:
    lg_db.init_db()
    
    # We want to move 2024-12-16 to next week from "Now" (2026-02-03)
    # 2024-12-16 to 2026-02-09 (Next Monday)
    # The difference is approx 419 days
    
    with lg_db._pool.connection() as conn:
        with conn.cursor() as cur:
            # Shift everything by 1 year and 2 months roughly (419 days)
            cur.execute("UPDATE calendar_events SET start_time = start_time + interval '420 days', end_time = end_time + interval '420 days';")
            print("Events shifted forward.")
            
            cur.execute("SELECT id, title, start_time FROM calendar_events;")
            rows = cur.fetchall()
            print("New Event Dates:")
            for r in rows:
                print(f"[{r[0]}] {r[1]} : {r[2]}")

except Exception as e:
    print(e)
