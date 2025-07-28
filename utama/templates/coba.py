import os
import pandas as pd
import psycopg2
from fuzzywuzzy import fuzz
from PIL import Image
import google.generativeai as genai
import json
import re
from pydantic import BaseModel, Field
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Path,Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import nest_asyncio
import uvicorn
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_DB")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def load_data_pusat():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            host=DB_HOST, port=DB_PORT
        )
        df = pd.read_sql_query("SELECT * FROM data_pusat", conn)
        df = df.dropna(subset=["Description", "id", "Harga Jual ke Konsumen yg Disarankan"])
        descriptions = df["Description"].astype(str).str.lower().tolist()
        harga_disarankan = df['Harga Jual ke Konsumen yg Disarankan'].tolist()
        ids = df["id"].tolist()
        return df, descriptions, ids, harga_disarankan
    except Exception as e:
        print(f"Error loading data_pusat: {e}")
        return pd.DataFrame(), [], [], []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_db_conn():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        host=DB_HOST, port=DB_PORT
    )

genai.configure(api_key=GEMINI_API_KEY)
model_gemini = genai.GenerativeModel("gemini-1.5-flash")

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
    Hanya kembalikan JSON-nya saja, tanpa penjelasan atau markdown formatting. buat jadi lowercase
    tambahan: buat jika ada angka di akhir misal "ce180"/"f50ml" jadi "ce 180ml"/"f 50ml", lalu jika tidak ada ml misal "10" maka jadi "10ml".
    """
    response = model_gemini.generate_content([prompt, img])
    text = response.text
    cleaned = re.sub(r'^```json|```$', '', text, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON dari Gemini tidak valid: {e}\nRaw response: {cleaned}")

def load_keywords_db():
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT keyword, normalized_value FROM keywords")
        return {row[0].lower(): row[1].lower() for row in cursor.fetchall()}
    except Exception as e:
        print(f"Error loading keywords: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def normalize_text(text, keyword_map):
    used_keywords = []
    for short, full in keyword_map.items():
        pattern = r'\b' + re.escape(short) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            text = re.sub(pattern, full, text, flags=re.IGNORECASE)
            used_keywords.append(f"{short} → {full}")
    return text, used_keywords

def match_items(items, descriptions, ids, suggested_prices, keyword_map, threshold=58, text_weight=0.7, price_weight=0.3):
    """
    Mencocokkan item dari OCR dengan database menggunakan skor gabungan dari kemiripan teks dan harga.
    """
    result = []
    for item in items:
        # Normalisasi nama item dari OCR
        nama_item, used_keywords = normalize_text(item['nama'].lower(), keyword_map)
        ocr_price = float(item.get('harga_satuan', 0))

        best_combined_score = -1
        best_idx = None
        best_text_score = 0
        best_price_score = 0

        for i, desc in enumerate(descriptions):
            db_price = float(suggested_prices[i])

            # 1. Hitung Skor Kemiripan Teks (0-100)
            text_score = fuzz.token_set_ratio(nama_item, desc)

            # 2. Hitung Skor Kemiripan Harga (0-100)
            price_score = 0
            if db_price > 0:
                # Hitung perbedaan harga sebagai rasio
                price_diff_ratio = abs(ocr_price - db_price) / db_price
                # Skor adalah 100% dikurangi persentase perbedaan. Dibatasi minimal 0.
                price_score = max(0, 1 - price_diff_ratio) * 100
            elif ocr_price == 0:
                price_score = 100 # Jika keduanya 0, anggap cocok sempurna

            # 3. Hitung Skor Gabungan (Weighted Score)
            combined_score = (text_score * text_weight) + (price_score * price_weight)

            # Simpan jika skor gabungan ini yang terbaik sejauh ini
            if combined_score > best_combined_score:
                best_combined_score = combined_score
                best_idx = i
                best_text_score = text_score
                best_price_score = price_score

        # Siapkan output untuk item ini
        matched_info = {
            "ocr_result": {
                "name": item['nama'],
                "quantity": float(item['qty']),
                "price": ocr_price,
                "total": float(item['subtotal']),
                "Final_accuracy": round(best_combined_score / 100, 4),
                "text_accuracy": round(best_text_score / 100, 4),
                "price_accuracy": round(best_price_score / 100, 4),
                "keywords": used_keywords
            }
        }

        # Jika skor gabungan melebihi ambang batas, anggap cocok
        if best_combined_score >= threshold and best_idx is not None:
            matched_info["id"] = int(ids[best_idx])
            matched_info["name"] = descriptions[best_idx]
            matched_info["harga_di_datapusat"] = float(suggested_prices[best_idx])
        else:
            matched_info["id"] = None
            matched_info["name"] = None
            matched_info["harga_di_datapusat"] = None
            
        result.append(matched_info)
        
    return result

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9& ]+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_normalized_value_valid(normalized_value: str) -> bool:
    cleaned_norm = clean_text(normalized_value)
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute('SELECT "Description" FROM data_pusat')
            rows = cur.fetchall()
            for row in rows:
                desc_cleaned = clean_text(str(row[0]))
                if cleaned_norm in desc_cleaned:
                    print(f"[MATCH] '{cleaned_norm}' ditemukan di: {desc_cleaned}")
                    return True
            print(f"[NO MATCH] '{cleaned_norm}' tidak ditemukan di deskripsi manapun.")
            return False
    except Exception as e:
        print(f"Error validating normalized_value: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ---------- Models ----------
class OCRResult(BaseModel):
    name: Optional[str]
    quantity: Optional[float]
    price: Optional[float]
    total: Optional[float]
    Final_accuracy: Optional[float]
    text_accuracy: Optional[float]
    price_accuracy: Optional[float]
    keywords: List[str] = []

class ItemMatched(BaseModel):
    id: Optional[int]
    name: Optional[str]
    harga_di_datapusat: Optional[float]
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

class KeywordRequest(BaseModel):
    id: int
    keyword: str
    normalized_value: str

class KeywordUpdate(BaseModel):
    keyword: str = Field(..., min_length=1)
    normalized_value: str = Field(..., min_length=1)

class ConfirmationRequest(BaseModel):
    is_correct: bool
    feedback: Optional[str] = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

df, descriptions, ids, harga_disarankan = load_data_pusat()
keywords_data = load_keywords_db()

# ---------- Endpoints ----------
@app.post("/struk-batch", response_model=List[FinalOutput])
async def struk_batch(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(await file.read())
            path = tmp.name

        try:
            image = Image.open(path)
            image.load()
            image.close()

            OCRData = OCR_Gemini(path)
            items = OCRData.get('daftar_barang', [])
            
            matched = match_items(items, descriptions, ids, harga_disarankan, keywords_data)
            
            try:
                conn = get_db_conn()
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO ocr_confirmations (receipt_data, matched_data)
                        VALUES (%s, %s)
                    """, (
                        json.dumps(OCRData),
                        json.dumps(matched)
                    ))
                    conn.commit()
            finally:
                if conn:
                    conn.close()

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
            results.append({"error": str(e), "file_name": file.filename})

        finally:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception as e:
                    print(f"Gagal hapus file sementara {path}: {e}")

    return results


@app.get("/ocr/confirmed")
def get_confirmed_ocr(status: Optional[bool] = Query(None, description="True = benar, False = salah, kosong = semua")):
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            if status is None:
                cur.execute("""
                    SELECT receipt_id, receipt_data, matched_data, is_correct, feedback, confirmed_at
                    FROM ocr_confirmations
                    WHERE is_confirmed = TRUE
                    ORDER BY confirmed_at DESC
                """)
            else:
                cur.execute("""
                    SELECT receipt_id, receipt_data, matched_data, is_correct, feedback, confirmed_at
                    FROM ocr_confirmations
                    WHERE is_confirmed = TRUE AND is_correct = %s
                    ORDER BY confirmed_at DESC
                """, (status,))
            rows = cur.fetchall()

        return [
            {
                "receipt_id": row[0],
                "receipt_data": row[1],
                "matched_data": row[2],
                "is_correct": row[3],
                "feedback": row[4],
                "confirmed_at": row[5]
            } for row in rows
        ]
    except Exception as e:
        return JSONResponse(content={"error": f"Gagal mengambil data konfirmasi: {e}"}, status_code=500)
    finally:
        if conn:
            conn.close()

@app.get("/ocr/unconfirmed")
def get_unconfirmed_ocr():
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT receipt_id, receipt_data, matched_data
                FROM ocr_confirmations
                WHERE is_confirmed = FALSE
            """)
            rows = cur.fetchall()
            return [{
                "receipt_id": row[0],
                "receipt_data": row[1],
                "matched_data": row[2]
            } for row in rows]
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        if conn:
            conn.close()

@app.post("/confirm-ocr/{receipt_id}")
async def confirm_ocr_result(receipt_id: str, request: ConfirmationRequest):
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE ocr_confirmations
                SET is_confirmed = TRUE,
                    is_correct = %s,
                    feedback = %s,
                    confirmed_at = NOW()
                WHERE receipt_id = %s
            """, (request.is_correct, request.feedback, receipt_id))
            conn.commit()
        return {"message": "Konfirmasi berhasil disimpan!"}
    except Exception as e:
        return JSONResponse(content={"error": f"Gagal menyimpan konfirmasi: {e}"}, status_code=500)
    finally:
        if conn:
            conn.close()

@app.get("/keywords", response_model=List[KeywordRequest])
async def get_all_keywords():
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id, keyword, normalized_value FROM keywords ORDER BY keyword ASC")
            return [{"id": row[0], "keyword": row[1], "normalized_value": row[2]} for row in cur.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching keywords: {e}")
    finally:
        if conn:
            conn.close()
            
@app.get("/suggestions/descriptions", response_model=List[str])
async def get_description_suggestions():
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute('SELECT "Description" FROM data_pusat')
            rows = cur.fetchall()

        word_set = set()
        for row in rows:
            if row[0]:
                cleaned = clean_text(str(row[0]))
                tokens = cleaned.split()
                word_set.update(tokens)

        return sorted(word_set)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching suggestions: {e}")
    finally:
        if conn:
            conn.close()

@app.post("/keywords")
def add_keyword(data: KeywordUpdate):
    if not is_normalized_value_valid(data.normalized_value):
        raise HTTPException(
            status_code=400,
            detail="normalized_value tidak ditemukan dalam deskripsi produk pusat."
        )

    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO keywords (keyword, normalized_value)
                VALUES (%s, %s)
                ON CONFLICT (keyword) DO UPDATE
                SET normalized_value = EXCLUDED.normalized_value,
                    updated_at = NOW()
            """, (data.keyword.lower(), data.normalized_value.lower()))
            conn.commit()

        global keywords_data
        keywords_data = load_keywords_db()
        return {"message": "Keyword berhasil ditambahkan atau diperbarui."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error menambahkan keyword: {e}")
    finally:
        if conn:
            conn.close()

@app.put("/keyword/{id}")
async def update_keyword(id: int, kw_update: KeywordUpdate):
    if not is_normalized_value_valid(kw_update.normalized_value):
        raise HTTPException(
            status_code=400,
            detail="normalized_value tidak ditemukan dalam deskripsi produk pusat."
        )

    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT keyword, normalized_value FROM keywords WHERE id = %s", (id,))
            old_data = cur.fetchone()
            if not old_data:
                return JSONResponse(content={"message": "Keyword tidak ditemukan"}, status_code=404)

            cur.execute("""
                UPDATE keywords
                SET keyword = %s, normalized_value = %s
                WHERE id = %s
            """, (kw_update.keyword.lower(), kw_update.normalized_value.lower(), id))
            conn.commit()

        global keywords_data
        keywords_data = load_keywords_db()

        return {
            "message": f"Keyword ID {id} berhasil diperbarui.",
            "old_data": {"keyword": old_data[0], "normalized_value": old_data[1]},
            "new_data": {
                "keyword": kw_update.keyword.lower(),
                "normalized_value": kw_update.normalized_value.lower()
            }
        }
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        if conn:
            conn.close()

@app.delete("/keywords/{id}")
async def delete_keyword(id: int):
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT keyword, normalized_value FROM keywords WHERE id = %s", (id,))
            data = cur.fetchone()
            if not data:
                return JSONResponse(content={"message": "Keyword tidak ditemukan"}, status_code=404)

            cur.execute("DELETE FROM keywords WHERE id = %s", (id,))
            conn.commit()

        global keywords_data
        keywords_data = load_keywords_db()

        return {
            "message": f"Keyword ID {id} berhasil dihapus.",
            "deleted_data": {"keyword": data[0], "normalized_value": data[1]}
        }
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        if conn:
            conn.close()

@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    nest_asyncio.apply()
    uvicorn.run("coba:app", host="127.0.0.1", port=8000, reload=True)