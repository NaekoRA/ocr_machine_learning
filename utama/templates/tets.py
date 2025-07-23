import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def insert_keywords_from_file(file_path='normalisasi.txt'):
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
            with open(file_path, 'r', encoding='utf-8') as f:
                count = 0
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        keyword = key.strip().lower()
                        normalized_value = value.strip().lower()
                        cur.execute("""
                            INSERT INTO keywords (keyword, normalized_value)
                            VALUES (%s, %s)
                            ON CONFLICT (keyword) DO NOTHING;
                        """, (keyword, normalized_value))
                        count += 1
                conn.commit()
                print(f"{count} keyword berhasil dimasukkan.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

insert_keywords_from_file()
