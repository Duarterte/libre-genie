import lg_db
import requests
import json

try:
    lg_db.init_db()
    with lg_db._pool.connection() as conn:
        with conn.cursor() as cur:
            # Get a valid client and secret
            cur.execute("SELECT client_id, secret FROM clients LIMIT 1;")
            row = cur.fetchone()
            if row:
                client_id, secret = row
                print(f"Using Client: {client_id}, Secret: {secret}")
                
                url = "http://localhost:8000/api/chat"
                payload = {
                    "question": "does it has access to context the assistent need to have the chat history of the conversation",
                    "client_id": client_id,
                    "secret": secret
                }
                
                print("Sending request...")
                response = requests.post(url, json=payload)
                print(f"Status: {response.status_code}")
                # print(f"Response: {response.text}")
            else:
                print("No clients found in DB.")

except Exception as e:
    print(e)
