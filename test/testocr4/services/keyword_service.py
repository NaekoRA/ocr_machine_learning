import re
from fuzzywuzzy import fuzz
from database import get_db_conn

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9& ]+', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def load_keywords_db():
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT keyword, normalized_value FROM keywords")
            return {row[0].lower(): row[1].lower() for row in cur.fetchall()}
    finally:
        conn.close()

def is_normalized_value_valid(normalized_value: str) -> bool:
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT "description" FROM data_pusat')
            return any(clean_text(normalized_value) in clean_text(str(r[0])) for r in cur.fetchall())
    finally:
        conn.close()
