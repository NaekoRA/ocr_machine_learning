import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Pastikan nama variabel di .env sesuai dengan ini
DB_NAME = os.getenv("DB_DB") 
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def create_database_if_not_exists():
    """
    Membuat database PostgreSQL jika belum ada.
    """
    # Sambungkan ke database 'postgres' default untuk membuat database baru
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True # Diperlukan untuk perintah CREATE DATABASE
        cursor = conn.cursor()

        # Cek apakah DB_NAME sudah ada
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"Database '{DB_NAME}' berhasil dibuat.")
        else:
            print(f"Database '{DB_NAME}' sudah ada.")

    except Exception as e:
        print(f"Error saat membuat database: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Step 1: Buat database jika belum ada
create_database_if_not_exists()

# Step 2: Sambungkan ke DB yang dituju
conn = None
cursor = None
try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()

    # --- Membuat Tabel data_pusat ---
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

    # --- Membuat Tabel keywords (untuk normalisasi dan keyword identifikasi) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keywords (
        id SERIAL PRIMARY KEY,
        keyword TEXT NOT NULL UNIQUE,          
        normalized_value TEXT NOT NULL,      
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    print("Tabel keywords siap digunakan.")

    # --- Membuat Fungsi dan Trigger untuk updated_at pada tabel keywords ---
    cursor.execute("""
    CREATE OR REPLACE FUNCTION update_timestamp()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_keywords_timestamp') THEN
            CREATE TRIGGER update_keywords_timestamp
            BEFORE UPDATE ON keywords
            FOR EACH ROW
            EXECUTE FUNCTION update_timestamp();
        END IF;
    END
    $$;
    """)
    conn.commit()
    print("Trigger 'update_keywords_timestamp' untuk tabel keywords siap digunakan.")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ocr_items(
        id SERIAL PRIMARY KEY,
        invoice_number TEXT,
        tanggal DATE,
        nama_toko TEXT,
        alamat TEXT,
        phone TEXT,
        email TEXT,
        total_belanja BIGINT,
        is_confirmed BOOLEAN DEFAULT FALSE,
        feedback TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        confirmed_at TIMESTAMP
    );
    """)
    conn.commit()
    print("Tabel ocr_items siap digunakan.")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS ocr_results (
    id SERIAL PRIMARY KEY,
    receipt_id INTEGER REFERENCES ocr_items(id) ON DELETE CASCADE,
    
    -- Hasil OCR mentah
    ocr_name TEXT,
    ocr_quantity NUMERIC,
    ocr_price BIGINT,
    ocr_total BIGINT,

    -- Akurasi dan pencocokan
    text_accuracy NUMERIC,
    price_accuracy NUMERIC,
    final_score NUMERIC,

    -- Data hasil pencocokan
    matched_item_id INTEGER REFERENCES data_pusat(id),
    matched_price NUMERIC,
    matched_name TEXT,

    -- Keyword hasil normalisasi
    keywords TEXT[],

    -- Konfirmasi dan feedback user
    is_correct BOOLEAN,
    feedback TEXT,
    confirmed_at TIMESTAMP,

    -- Timestamp standar
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

    """)
    conn.commit()
    print("Tabel ocr_results siap digunakan.")

    excel_file = 'SKU.xlsx'
    try:
        df = pd.read_excel(excel_file, usecols=range(9), skiprows=2, sheet_name='All NIVEA PL Mei 2024')
        df = df.dropna()

        # Insert data ke tabel data_pusat
        # Periksa apakah tabel kosong sebelum memasukkan data untuk menghindari duplikasi
        cursor.execute("SELECT COUNT(*) FROM data_pusat")
        count = cursor.fetchone()[0]

        if count == 0:
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
        else:
            print(f"Tabel data_pusat sudah berisi data. Melewatkan penyisipan dari {excel_file}.")

    except FileNotFoundError:
        print(f"Error: File Excel '{excel_file}' tidak ditemukan. Pastikan file berada di direktori yang sama.")
    except Exception as e:
        print(f"Error saat membaca atau memasukkan data dari Excel: {e}")
    # --- Menambahkan data dari normalisasi.txt ke tabel keywords ---
    normalisasi_file = 'normalisasi.txt'
    try:
        if os.path.exists(normalisasi_file):
            with open(normalisasi_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                inserted = 0
                for line in lines:
                    line = line.strip()
                    if not line or '=' not in line:
                        continue  # skip baris kosong atau format salah
                    keyword, normalized = line.split('=', 1)
                    keyword = keyword.strip().lower()
                    normalized = normalized.strip().lower()
                    try:
                        cursor.execute("""
                            INSERT INTO keywords (keyword, normalized_value)
                            VALUES (%s, %s)
                            ON CONFLICT (keyword) DO NOTHING;
                        """, (keyword, normalized))
                        inserted += 1
                    except Exception as inner_e:
                        print(f"Gagal insert keyword '{keyword}': {inner_e}")
                conn.commit()
                print(f"{inserted} keyword dari {normalisasi_file} berhasil dimasukkan ke tabel keywords.")
        else:
            print(f"File '{normalisasi_file}' tidak ditemukan. Lewatkan input keywords.")
    except Exception as e:
        print(f"Error saat membaca atau memasukkan data dari normalisasi.txt: {e}")

except Exception as e:
    print(f"Error koneksi atau operasi database utama: {e}")
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()

print("Skrip inisialisasi database selesai.")
