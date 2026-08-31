import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
gemini_key = os.environ.get("GEMINI_API_KEY")
print(f"Key loaded: {gemini_key is not None}")
try:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Hello")
    print(response.text)
except Exception as e:
    print(f"Exception: {type(e).__name__} - {str(e)}")
