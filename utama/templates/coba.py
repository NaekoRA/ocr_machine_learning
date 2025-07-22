import os
import pandas as pd
import psycopg2
from fuzzywuzzy import fuzz
from PIL import Image
import google.generativeai as genai
import json
import re
from pydantic import BaseModel
from typing import List
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware # Import CORSMiddleware
import tempfile
import nest_asyncio
import uvicorn
from dotenv import load_dotenv

load_dotenv()

# Konfigurasi Database dari .env
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def load_data_pusat():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    df = pd.read_sql_query("SELECT * FROM data_pusat", conn)
    conn.close()

    df = df.dropna()
    descriptions = df["Description"].astype(str).str.lower().tolist()
    ids = df["id"].tolist()
    prices = df["Harga Jual ke Konsumen yg Disarankan"].tolist()

    return df, descriptions, ids, prices

genai.configure(api_key=GEMINI_API_KEY)
model_gemini = genai.GenerativeModel("gemini-2.5-flash")

def OCR_Gemini(image_path):
    img = Image.open(image_path)
    prompt = """
    Ini adalah struk belanja. Tolong ekstrak informasinya dalam format JSON dengan field:
    - invoice_number (string)
    - phone (string)
    - alamat (string)
    - email (string)
    - nama_toko (string)
    - tanggal (string, format DD/MM/YYYY)
    - daftar_barang (array of objects: nama, qty, harga_satuan, subtotal)
    - total_belanja (number)
    Jika ada informasi yang tidak jelas, isi dengan null.
    Hanya kembalikan JSON-nya saja, tanpa penjelasan atau markdown formatting.buat jadi lowercase
    tambahan: buat jika ada angka di akhir misal "ce180" /"f50ml" jadi "ce 180ml"/ "f 50ml" agar nama barang tidak menyatu dengan volume, lalu jika tidakk ada ml misal "10" maka buat agar adamlnya "10ml" pastikan volume menyatu dengan angka misal "50ml".
    """
    response = model_gemini.generate_content([prompt, img])
    text = response.text
    cleaned = re.sub(r'^```json|```$', '', text, flags=re.MULTILINE).strip()
    return json.loads(cleaned)

def load_normalisasi_from_file(filepath='normalisasi.txt'):
    normalisasi_map = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    normalisasi_map[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"Warning: normalisasi file not found at {filepath}. Normalization will not be applied.")
    return normalisasi_map

normalisasi = load_normalisasi_from_file()

def normalize_text(text):
    text = text.lower()
    for k, v in normalisasi.items():
        pattern = r'\b' + re.escape(k) + r'\b'
        text = re.sub(pattern, v, text)
    return text

def match_items(items, descriptions, ids, prices, threshold=58):
    result = []
    for item in items:
        nama_item = normalize_text(item['nama'].lower())
        best_score = 0
        best_idx = None

        for i, desc in enumerate(descriptions):
            score = fuzz.token_set_ratio(nama_item, desc)
            if score > best_score:
                best_score = score
                best_idx = i

        if best_score >= threshold:
            result.append({
                "id": int(ids[best_idx]),
                "name": descriptions[best_idx],
                "ocr_result": {
                    "name": item['nama'],
                    "quantity": float(item['qty']),
                    "price": float(item['harga_satuan']),
                    "total": float(item['subtotal']),
                    "accuration": round(best_score / 100, 4)
                }
            })
        else:
            result.append({
                "id": None,
                "name": None,
                "ocr_result": {
                    "name": item['nama'],
                    "quantity": float(item['qty']),
                    "price": float(item['harga_satuan']),
                    "total": float(item['subtotal']),
                    "accuration": round(best_score / 100, 4)
                }
            })
    return result

# Pydantic Models for FastAPI response validation
class OCRResult(BaseModel):
    name: str | None
    quantity: float | None
    price: float | None
    total: float | None
    accuration: float | None

class ItemMatched(BaseModel):
    id: int | None
    name: str | None
    ocr_result: OCRResult

class Merchant(BaseModel):
    name: str | None
    address: str | None
    phone: str | None
    email: str | None

class FinalOutput(BaseModel):
    invoice_number: str | None
    tanggal: str | None
    merchant: Merchant
    items: List[ItemMatched]
    grand_total: float | None

app = FastAPI()

# Konfigurasi CORS Middleware
origins = [
    "http://localhost:3001",  # Explicitly allow your Nuxt app's exact origin
    "http://127.0.0.1:3001",  # Also allow 127.0.0.1 for the Nuxt app just in case of slight variations
    "http://127.0.0.1:8000",  # Your backend's own origin
    "http://localhost:8000"   # Your backend's localhost origin
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Memungkinkan semua metode (GET, POST, dll.)
    allow_headers=["*"], # Memungkinkan semua header
)

# Load data pusat saat aplikasi dimulai
df, descriptions, ids, prices = load_data_pusat()

@app.post("/struk-batch", response_model=List[FinalOutput])
async def struk_batch(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        # Gunakan tempfile untuk menyimpan sementara file yang diunggah
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(await file.read())
            path = tmp.name # Dapatkan path ke file sementara

        try:
            OCRData = OCR_Gemini(path)
            items = OCRData['daftar_barang']
            matched = match_items(items, descriptions, ids, prices)

            result = {
                "invoice_number": OCRData.get('invoice_number'),
                "tanggal": OCRData.get('tanggal'),
                "merchant": {
                    "name": OCRData.get('nama_toko'),
                    "address": OCRData.get('alamat'),
                    "phone": OCRData.get('phone'),
                    "email": OCRData.get('email')
                },
                "items": matched,
                "grand_total": float(OCRData.get('total_belanja')) if OCRData.get('total_belanja') is not None else None
            }
            results.append(result)
        except Exception as e:
            # Jika ada error pada satu file, tambahkan error ke hasil
            results.append({"error": str(e)})
        finally:
            # Pastikan file sementara dihapus setelah diproses
            if os.path.exists(path):
                os.unlink(path)

    return results

@app.get("/")
def health_check():
    return {"status": "running", "message": "FastAPI service is operational."}

if __name__ == "__main__":
    # Ini memastikan uvicorn dapat dijalankan di lingkungan async
    nest_asyncio.apply()
    # Pastikan host dan port sesuai dengan yang diakses oleh frontend
    uvicorn.run("coba:app", host="127.0.0.1", port=8000, reload=True)