import os
import pandas as pd
import psycopg2
from fuzzywuzzy import fuzz
from PIL import Image
import google.generativeai as genai
import json
import re
from pydantic import BaseModel
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import nest_asyncio
import uvicorn
from dotenv import load_dotenv
from uuid import uuid4
load_dotenv()

# Konfigurasi Database dari .env
DB_NAME = os.getenv("DB_DB")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def load_data_pusat():
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        df = pd.read_sql_query("SELECT * FROM data_pusat", conn)
        df = df.dropna()
        descriptions = df["Description"].astype(str).str.lower().tolist()
        ids = df["id"].tolist()
        prices = df["Harga Jual ke Konsumen yg Disarankan"].tolist()
        return df, descriptions, ids, prices
    except Exception as e:
        print(f"Error loading data_pusat: {e}")
        # Return empty lists/dataframe if there's an error to prevent further issues
        return pd.DataFrame(), [], [], []
    finally:
        if conn:
            conn.close()

def get_db_conn():
    return psycopg2.connect(
        dbname=os.getenv("DB_DB"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
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

# --- Fungsi baru untuk memuat keywords dari database ---
def load_keywords_from_db():
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        with conn.cursor() as cur:
            cur.execute("SELECT keyword FROM keywords")
            keywords_list = [row[0].lower() for row in cur.fetchall()]
        return keywords_list
    except Exception as e:
        print(f"Error loading keywords from database: {e}")
        return []
    finally:
        if conn:
            conn.close()

def normalize_text(text):
    text = text.lower()
    for k, v in normalisasi.items():
        pattern = r'\b' + re.escape(k) + r'\b'
        text = re.sub(pattern, v, text)
    return text

# --- Fungsi match_items yang diperbarui untuk menyertakan keywords ---
def match_items(items, descriptions, ids, prices, keywords_data, threshold=58):
    result = []
    for item in items:
        nama_item = normalize_text(item['nama'].lower())
        best_score = 0
        best_idx = None
        identified_keywords = []

        # Identifikasi keywords dalam nama item OCR
        for keyword in keywords_data:
            if keyword in nama_item:
                identified_keywords.append(keyword)

        for i, desc in enumerate(descriptions):
            score = fuzz.token_set_ratio(nama_item, desc)
            if score > best_score:
                best_score = score
                best_idx = i

        matched_info = {
            "ocr_result": {
                "name": item['nama'],
                "quantity": float(item['qty']),
                "price": float(item['harga_satuan']),
                "total": float(item['subtotal']),
                "accuration": round(best_score / 100, 4),
                "keywords": identified_keywords # Tambahkan keywords ke hasil OCR
            }
        }

        if best_score >= threshold:
            matched_info["id"] = int(ids[best_idx])
            matched_info["name"] = descriptions[best_idx]
        else:
            matched_info["id"] = None
            matched_info["name"] = None
        result.append(matched_info)
    return result

# Pydantic Models for FastAPI response validation
class OCRResult(BaseModel):
    name: Optional[str]
    quantity: Optional[float]
    price: Optional[float]
    total: Optional[float]
    accuration: Optional[float]
    keywords: List[str] = [] # Tambahkan keywords ke model

class ItemMatched(BaseModel):
    id: Optional[int]
    name: Optional[str]
    ocr_result: OCRResult

class Merchant(BaseModel):
    name: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    email: Optional[str]

class FinalOutput(BaseModel):
    invoice_number: Optional[str]
    tanggal: Optional[str]
    merchant: Merchant
    items: List[ItemMatched]
    grand_total: Optional[float]

class KeywordModel(BaseModel):
    keyword: str
    normalized_value: str


# --- Pydantic Models baru untuk konfirmasi dan pengelolaan keywords ---
class ConfirmationRequest(BaseModel):
    receipt_data: dict # Data JSON dari hasil OCR asli
    matched_data: List[ItemMatched] # Data JSON dari hasil pencocokan
    is_correct: bool # True jika benar, False jika salah
    feedback: Optional[str] = None # Umpan balik opsional

class KeywordRequest(BaseModel):
    keyword: str
    normalized_value: str
class KeywordUpdate(BaseModel):
    old_keyword: str
    new_keyword: str

class ConfirmationRequest(BaseModel):
    receipt_id: str  # <--- tambahkan ini
    is_correct: bool
    feedback: Optional[str] = None


app = FastAPI()

# Konfigurasi CORS Middleware
origins = [
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:8000",
    "http://localhost:8000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data pusat dan keywords saat aplikasi dimulai
df, descriptions, ids, prices = load_data_pusat()
keywords_data = load_keywords_from_db() # Muat keywords dari database

@app.post("/struk-batch", response_model=List[FinalOutput])
async def struk_batch(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(await file.read())
            path = tmp.name

        try:
            OCRData = OCR_Gemini(path)
            items = OCRData['daftar_barang']
            # Panggil match_items dengan keywords_data
            matched = match_items(items, descriptions, ids, prices, keywords_data)

            receipt_id = str(uuid4())

            # simpan ke ocr_confirmations
            try:
                conn = get_db_conn()
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO ocr_confirmations (receipt_id, receipt_data, matched_data)
                        VALUES (%s, %s, %s)
                    """, (
                        receipt_id,
                        json.dumps(OCRData),
                        json.dumps(matched)
                    ))
                    conn.commit()
            except Exception as e:
                print(f"Error inserting batch OCR to db: {e}")
            finally:
                if conn:
                    conn.close()

            result = {
                "receipt_id": receipt_id,  # ini penting untuk frontend
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
            results.append({"error": str(e), "file_name": file.filename})
        finally:
            if os.path.exists(path):
                os.unlink(path)
    return results

# --- Endpoint baru untuk konfirmasi OCR ---
@app.post("/confirm-ocr")
async def confirm_ocr_result(request: ConfirmationRequest):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ocr_confirmations
                SET is_confirmed = TRUE,
                    is_correct = %s,
                    feedback = %s,
                    confirmed_at = NOW()
                WHERE receipt_id = %s
                """,
                (
                    request.is_correct,
                    request.feedback,
                    request.receipt_id
                )
            )
            
            conn.commit()
        return JSONResponse(content={"message": "Konfirmasi berhasil disimpan!"}, status_code=200)
    except Exception as e:
        print(f"Error saving confirmation: {e}")
        return JSONResponse(content={"error": f"Gagal menyimpan konfirmasi: {e}"}, status_code=500)
    finally:
        if conn:
            conn.close()

# --- Endpoint baru untuk pengelolaan keywords ---
@app.get("/keywords")
async def get_all_keywords():
    conn = None
    try:
        conn = conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT keyword FROM keywords ORDER BY keyword")
            keywords = [row[0] for row in cur.fetchall()]
        return JSONResponse(content=keywords, status_code=200)
    except Exception as e:
        print(f"Error fetching keywords: {e}")
        return JSONResponse(content={"error": f"Gagal mengambil keywords: {e}"}, status_code=500)
    finally:
        if conn:
            conn.close()

@app.post("/keywords")
def add_keyword(data: KeywordRequest):
    keyword = data.keyword.strip().lower()
    normalized = data.normalized_value.strip().lower()

    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO keywords (keyword, normalized_value)
            VALUES (%s, %s)
            ON CONFLICT (keyword) DO UPDATE
            SET normalized_value = EXCLUDED.normalized_value,
                updated_at = NOW()
        """, (keyword, normalized))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Keyword berhasil ditambahkan atau diperbarui."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error menambahkan keyword: {e}")
@app.get("/ocr/unconfirmed")
def get_unconfirmed_ocr():
    try:
        conn = conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT receipt_id, receipt_data, matched_data
                FROM ocr_confirmations
                WHERE is_confirmed = FALSE
            """)
            rows = cur.fetchall()
            results = []
            for row in rows:
                results.append({
                    "receipt_id": row[0],
                    "receipt_data": row[1],
                    "matched_data": row[2]
                })
            return results
    except Exception as e:
        print(f"Error fetching unconfirmed: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        if conn:
            conn.close()

@app.put("/keywords")
async def update_keyword(kw_update: KeywordUpdate):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("UPDATE keywords SET keyword = %s WHERE keyword = %s", (kw_update.new_keyword.lower(), kw_update.old_keyword.lower()))
            conn.commit()
            if cur.rowcount == 0:
                return JSONResponse(content={"message": "Keyword lama tidak ditemukan."}, status_code=404)
            global keywords_data
            keywords_data = load_keywords_from_db() # Reload keywords setelah perubahan
        return JSONResponse(content={"message": f"Keyword '{kw_update.old_keyword}' berhasil diupdate menjadi '{kw_update.new_keyword}'."}, status_code=200)
    except Exception as e:
        print(f"Error updating keyword: {e}")
        return JSONResponse(content={"error": f"Gagal memperbarui keyword: {e}"}, status_code=500)
    finally:
        if conn:
            conn.close()

@app.delete("/keywords/{keyword}")
async def delete_keyword(keyword: str):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM keywords WHERE keyword = %s", (keyword.lower(),))
            conn.commit()
            if cur.rowcount == 0:
                return JSONResponse(content={"message": "Keyword tidak ditemukan."}, status_code=404)
            global keywords_data
            keywords_data = load_keywords_from_db() # Reload keywords setelah perubahan
        return JSONResponse(content={"message": f"Keyword '{keyword}' berhasil dihapus."}, status_code=200)
    except Exception as e:
        print(f"Error deleting keyword: {e}")
        return JSONResponse(content={"error": f"Gagal menghapus keyword: {e}"}, status_code=500)
    finally:
        if conn:
            conn.close()

@app.get("/")
def health_check():
    return {"status": "running", "message": "FastAPI service is operational."}

if __name__ == "__main__":
    nest_asyncio.apply()
    uvicorn.run("coba:app", host="127.0.0.1", port=8000, reload=True)