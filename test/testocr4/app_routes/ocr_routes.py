from fastapi import APIRouter, UploadFile, File, HTTPException, Query
import tempfile, os
from typing import List, Optional
from PIL import Image
from fuzzywuzzy import fuzz

from services.ocr_service import OCR_Gemini
from services.match_service import match_items
from services.keyword_service import load_keywords_db, clean_text, is_normalized_value_valid
from database import get_db_conn, load_data_pusat
from models import FinalOutput, KeywordUpdate

router = APIRouter()

# Cache global data
df, descriptions, ids, harga_data_pusat = load_data_pusat()
keywords_data = load_keywords_db()

# ================== OCR /struk-batch ==================
@router.post("/struk-batch", response_model=List[FinalOutput])
async def struk_batch(files: List[UploadFile] = File(...)):
    results = []
    global df, descriptions, ids, harga_data_pusat, keywords_data

    for file in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(await file.read())
            path = tmp.name
        try:
            Image.open(path).close()
            OCRData = OCR_Gemini(path)
            matched = match_items(OCRData.get("daftar_barang", []), descriptions, ids, harga_data_pusat, keywords_data)

            conn = get_db_conn()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ocr_items (invoice_number, nama_toko, alamat, phone, email, tanggal, total_belanja)
                    VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (
                    OCRData.get('invoice_number'), OCRData.get('nama_toko'), OCRData.get('alamat'),
                    OCRData.get('phone'), OCRData.get('email'), OCRData.get('tanggal'), OCRData.get('total_belanja')
                ))
                receipt_id = cur.fetchone()[0]

                for item in matched:
                    ocr = item["ocr_result"]
                    cur.execute("""
                        INSERT INTO ocr_results (
                            receipt_id, ocr_name, ocr_quantity, ocr_price, ocr_total,
                            matched_item_id, matched_name, matched_price,
                            text_accuracy, price_accuracy, final_score, keywords, is_correct
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL)
                    """, (
                        receipt_id,
                        ocr["name"], ocr["quantity"], ocr["price"], ocr["total"],
                        item.get("id"), item.get("name"), item.get("harga_di_datapusat"),
                        ocr["text_accuracy"], ocr["price_accuracy"], ocr["Final_accuracy"],
                        ocr["keywords"]
                    ))
                conn.commit()

            results.append({
                "invoice_number": OCRData.get("invoice_number"),
                "tanggal": OCRData.get("tanggal"),
                "merchant": {
                    "name": OCRData.get("nama_toko"),
                    "address": OCRData.get("alamat"),
                    "phone": OCRData.get("phone"),
                    "email": OCRData.get("email")
                },
                "items": matched,
                "grand_total": float(OCRData.get("total_belanja")) if OCRData.get("total_belanja") else None
            })
        except Exception as e:
            results.append({"error": str(e), "file_name": file.filename})
        finally:
            os.unlink(path)
            if 'conn' in locals(): conn.close()
    return results


# ================== OCR Confirm ==================
@router.patch("/ocr-results/{item_id}/confirm")
async def confirm_ocr_item(
    item_id: int,
    is_correct: bool = Query(..., description="Status benar/salah hasil match"),
    selected_id: Optional[int] = Query(None, description="ID produk yang dipilih jika ingin mengganti match"),
    feedback: Optional[str] = Query(None, description="Feedback tambahan")
):
    global keywords_data, df, descriptions, ids, harga_data_pusat
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT ocr_name, matched_name FROM ocr_results WHERE id=%s", (item_id,))
            item_info = cur.fetchone()
            if not item_info:
                raise HTTPException(status_code=404, detail="Item OCR tidak ditemukan.")
            ocr_name, matched_name = item_info

            if is_correct:
                cur.execute("""UPDATE ocr_results SET is_correct=TRUE, feedback=%s, confirmed_at=NOW() WHERE id=%s""",
                            (feedback, item_id))
                conn.commit()
                keywords_data = load_keywords_db()
                return {"message": "Item benar, keyword dipelajari."}

            if not is_correct and selected_id:
                cur.execute('SELECT description FROM data_pusat WHERE id=%s', (selected_id,))
                product_row = cur.fetchone()
                if not product_row:
                    raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
                selected_name = product_row[0]

                cur.execute("""
                    UPDATE ocr_results
                    SET matched_item_id=%s, matched_name=%s, is_correct=TRUE, feedback=%s, confirmed_at=NOW(), updated_at=NOW()
                    WHERE id=%s
                """, (selected_id, selected_name, feedback, item_id))
                conn.commit()
                keywords_data = load_keywords_db()
                return {"message": "Alternatif dipilih, match diperbarui.", "selected_id": selected_id, "selected_name": selected_name}

            if df.empty:
                df, descriptions, ids, harga_data_pusat = load_data_pusat()
            scored = [
                {"id": ids[i], "name": desc, "score": round(fuzz.token_set_ratio(clean_text(ocr_name), clean_text(desc)) / 100, 4)}
                for i, desc in enumerate(descriptions)
            ]
            return {"message": "Item salah, pilih salah satu alternatif.", "alternatives": sorted(scored, key=lambda x: x["score"], reverse=True)[:5]}
    finally:
        conn.close()


# ================== Keyword Normalisasi ==================
@router.post("/normalisasi")
def add_keywords(data: List[KeywordUpdate]):
    added, failed, skipped = [], [], []
    global keywords_data
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            for item in data:
                k, v = item.keyword.lower(), item.normalized_value.lower()
                if not is_normalized_value_valid(v):
                    failed.append({"keyword": k, "reason": "normalized_value tidak valid"})
                    continue
                cur.execute("SELECT normalized_value FROM keywords WHERE keyword=%s", (k,))
                existing = cur.fetchone()
                if existing and existing[0] == v:
                    skipped.append(k)
                    continue
                cur.execute("""
                    INSERT INTO keywords (keyword, normalized_value)
                    VALUES (%s, %s)
                    ON CONFLICT (keyword) DO UPDATE SET normalized_value=EXCLUDED.normalized_value, updated_at=NOW()
                """, (k, v))
                added.append(f"{k} → {v}")
            conn.commit()
        keywords_data = load_keywords_db()
        return {"added_or_updated": added, "skipped_duplicates": skipped, "failed": failed}
    finally:
        conn.close()
