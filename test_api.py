import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
gemini_key = os.environ.get("GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:streamGenerateContent?alt=sse&key={gemini_key}"
payload = {
    "contents": [{"role": "user", "parts": [{"text": "hi"}]}]
}
with requests.post(url, json=payload, stream=True) as r:
    print(r.status_code)
    for line in r.iter_lines():
        if line:
            print(line.decode('utf-8'))
