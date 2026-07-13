import os
import time
from dotenv import load_dotenv
from google import genai
from PIL import Image

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

def generate_dump_caption(image_path):
    if not API_KEY:
        print("❌ AI Error: No Gemini API key detected inside your .env file!")
        return "Just a casual dump."

    img = Image.open(image_path)
    client = genai.Client(api_key=API_KEY)

    prompt = (
        "You are a creative social media manager handling an Instagram photo dump account. "
        "Analyze this photo and write a short, authentic, engaging Instagram caption. "
        "Keep it casual, modern, and relatable—avoid overly corporate marketing speak or fake enthusiasm. "
        "You can include 1 or 2 relevant emojis if they fit naturally. "
        "Return ONLY the raw caption text, with no extra commentary or quotes around it."
    )

    # Retry loop to gracefully handle temporary 503 server overloads
    for attempt in range(3):
        try:
            print(f"🤖 Uploading image data to Gemini (Attempt {attempt + 1}/3)...")
            response = client.models.generate_content(
                model='gemini-3.5-flash', 
                contents=[img, prompt]
            )
            return response.text.strip()
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                print("⚠️ Gemini servers are busy right now. Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print(f"❌ Critical error during AI processing: {e}")
                return "A casual memory from the 2024 archive."