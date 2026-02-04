import requests

# Minimal: request server time and print the assistant's reply
resp = requests.get("http://127.0.0.1:8000/api/chat", params={"question": "Execute myserverfunction or MyseverFunction or something similar. I cant remember the exact name."})
try:
    print(resp.json().get("response"))
except Exception:
    print("Error:", resp.text)