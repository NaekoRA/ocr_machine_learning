from fuzzywuzzy import fuzz
import re

def normalize_text(text, keyword_map):
    text = re.sub(r'(\d+)\s+(ml|gr|pcs)', r'\1\2', text)
    used_keywords = []
    for short, full in keyword_map.items():
        pattern = r'\b' + re.escape(short) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            text = re.sub(pattern, full, text, flags=re.IGNORECASE)
            used_keywords.append(f"{short} → {full}")
    return text, used_keywords

def match_items(items, descriptions, ids, suggested_prices, keyword_map, threshold=58, text_weight=0.7, price_weight=0.3):
    results = []
    for item in items:
        nama_item, used_keywords = normalize_text(item['nama'].lower(), keyword_map)
        ocr_price = float(item.get('harga_satuan', 0))

        best_score, best_idx, text_score, price_score = -1, None, 0, 0
        for i, desc in enumerate(descriptions):
            db_price = float(suggested_prices[i])
            ts = fuzz.token_set_ratio(nama_item, desc)
            ps = max(0, (1 - abs(ocr_price - db_price) / db_price) * 100) if db_price else 100
            score = ts * text_weight + ps * price_weight
            if score > best_score:
                best_score, best_idx, text_score, price_score = score, i, ts, ps

        matched = {
            "ocr_result": {
                "name": item['nama'],
                "quantity": float(item['qty']),
                "price": ocr_price,
                "total": float(item['subtotal']),
                "Final_accuracy": round(best_score / 100, 4),
                "text_accuracy": round(text_score / 100, 4),
                "price_accuracy": round(price_score / 100, 4),
                "keywords": used_keywords
            }
        }
        if best_score >= threshold and best_idx is not None:
            matched["id"] = ids[best_idx]
            matched["name"] = descriptions[best_idx]
            matched["harga_di_datapusat"] = float(suggested_prices[best_idx])
        else:
            matched.update({"id": None, "name": None, "harga_di_datapusat": None})
        results.append(matched)
    return results
