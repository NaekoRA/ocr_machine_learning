import google.generativeai as genai
from PIL import Image
import json, re, os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model_gemini = genai.GenerativeModel("gemini-2.5-flash")

def OCR_Gemini(image_path: str):
    img = Image.open(image_path)
    prompt = """
    Ini adalah struk belanja. Tolong ekstrak informasinya dalam format JSON dengan field:
    - invoice_number, phone, alamat, email, nama_toko, tanggal (DD/MM/YYYY),
    - daftar_barang [{nama, qty, harga_satuan, subtotal}],
    - total_belanja
    Jika tidak jelas → null.
    Hanya JSON, lowercase semua.
    """
    response = model_gemini.generate_content([prompt, img])
    text = response.text
    cleaned = re.sub(r'^```json|```$', '', text, flags=re.MULTILINE).strip()
    return json.loads(cleaned)
