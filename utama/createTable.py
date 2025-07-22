import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

DB_NAME = os.getenv("DB_DB")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def create_database_if_not_exists():
    # Connect to default postgres DB
    conn = psycopg2.connect(
        dbname="postgres",
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # Cek apakah DB_NAME sudah ada
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    exists = cursor.fetchone()

    if not exists:
        cursor.execute(f'CREATE DATABASE "{DB_NAME}"')
        print(f"Database '{DB_NAME}' berhasil dibuat.")
    else:
        print(f"Database '{DB_NAME}' sudah ada.")

    cursor.close()
    conn.close()

# Step 1: Buat database jika belum ada
create_database_if_not_exists()

# Step 2: Connect ke DB yang dituju
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)
cursor = conn.cursor()

# Buat tabel jika belum ada
cursor.execute("""
CREATE TABLE IF NOT EXISTS data_pusat (
    "id" int PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "Brand" TEXT,
    "Sub Brand AS" TEXT,
    "Brand Group AS" TEXT,
    "Description" TEXT,
    "Barcode (Pieces)" NUMERIC,
    "Harga PTT/Sebelum PPN" BIGINT,
    "Kuantiti per Karton/Dus" BIGINT,
    "Harga PPN" BIGINT,
    "Harga Jual ke Konsumen yg Disarankan" BIGINT
);
""")
conn.commit()
print("Tabel data_pusat siap digunakan.")

# Baca data dari Excel SKUNivea.xlsx
excel_file = 'SKUNivea.xlsx'
df = pd.read_excel(excel_file, usecols=range(9), skiprows=2, sheet_name='All NIVEA PL Mei 2024')
df = df.dropna()

# Insert data ke tabel data_pusat
for index, row in df.iterrows():
    cursor.execute("""
        INSERT INTO data_pusat (
            "Brand",
            "Sub Brand AS",
            "Brand Group AS",
            "Description",
            "Barcode (Pieces)",
            "Harga PTT/Sebelum PPN",
            "Kuantiti per Karton/Dus",
            "Harga PPN",
            "Harga Jual ke Konsumen yg Disarankan"
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        row['Brand'],
        row['Sub Brand AS'],
        row['Brand Group AS'],
        row['Description'],
        row['Barcode (Pieces)'],
        row['Harga PTT/Sebelum PPN'],
        row['Kuantiti per Karton/Dus'],
        row['Harga PPN'],
        row['Harga Jual ke Konsumen yg Disarankan']
    ))

conn.commit()
print(f"Data dari {excel_file} berhasil dimasukkan ke database.")

cursor.close()
conn.close()
