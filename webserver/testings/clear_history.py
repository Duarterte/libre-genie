import lg_db

try:
    lg_db.init_db()
    with lg_db._pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chat_history;")
            # cur.execute("DELETE FROM client_chat_history;") # Just in case
            print("Chat history cleared.")
except Exception as e:
    print(e)
