import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# Pastikan load .env dengan path yang benar
dotenv_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

DB_NAME = os.getenv("DB_DB")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

try:
    # Koneksi ke PostgreSQL
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    print("Koneksi ke database berhasil.")

    cur = conn.cursor()

    # Cek nama database yang sedang terkoneksi
    cur.execute("SELECT current_database();")
    current_db = cur.fetchone()[0]
    print(f"Sedang terkoneksi ke database: {current_db}")

    # Cek daftar tabel di schema public
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public';
    """)
    tables = cur.fetchall()
    print("Daftar tabel di schema public:")
    for table in tables:
        print(f"- {table[0]}")

    # Cek isi tabel data_pusat jika ada
    if ('data_pusat',) in tables:
        cur.execute("SELECT * FROM data_pusat LIMIT 5;")
        rows = cur.fetchall()
        print("\nContoh isi tabel data_pusat:")
        for row in rows:
            print(row)
    else:
        print("\nTabel data_pusat tidak ditemukan di database ini.")

    cur.close()
    conn.close()

except Exception as e:
    print("Gagal koneksi atau query:", e)
