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
       # Mapping kolom Excel -> kolom Database
    column_mapping = {
        "Brand": "brand",
        "Sub Brand AS": "sub_brand",
        "Brand Group AS": "brand_group",
        "Description": "description",
        "Barcode (Pieces)": "barcode",
        "Harga PTT/Sebelum PPN": "harga_ptt",
        "Kuantiti per Karton/Dus": "kuantiti_per_karton",
        "Harga PPN": "harga_ppn",
        "Harga Jual ke Konsumen yg Disarankan": "harga_jual"
    }
    
    # --- Membuat Tabel data_pusat ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_pusat (
        "id" int PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        "brand" TEXT,
        "sub_brand" TEXT,
        "brand_group" TEXT,
        "description" TEXT,
        "barcode" NUMERIC,
        "harga_ptt" BIGINT,
        "kuantiti_per_karton" BIGINT,
        "harga_ppn" BIGINT,
        "harga_jual" BIGINT
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

    # --- Membuat Tabel ocr_items ---
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

    # --- Membuat Tabel ocr_results ---
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

    # --- Fungsi dan Trigger untuk otomatisasi konfirmasi struk ---
    cursor.execute("""
    -- Membuat Fungsi untuk Cek Konfirmasi
    CREATE OR REPLACE FUNCTION update_ocr_item_confirmation()
    RETURNS TRIGGER AS $$
    DECLARE
        all_confirmed BOOLEAN;
    BEGIN
        -- Memeriksa apakah semua item untuk receipt_id ini sudah dikonfirmasi (is_correct IS NOT NULL)
        SELECT BOOL_AND(is_correct IS NOT NULL)
        INTO all_confirmed
        FROM ocr_results
        WHERE receipt_id = NEW.receipt_id;

        -- Jika semua item sudah dikonfirmasi, perbarui is_confirmed di ocr_items menjadi TRUE
        IF all_confirmed THEN
            UPDATE ocr_items
            SET is_confirmed = TRUE,
                confirmed_at = NOW()
            WHERE id = NEW.receipt_id;
        END IF;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- Membuat Trigger yang akan berjalan setelah setiap INSERT atau UPDATE di ocr_results
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'check_all_items_confirmed') THEN
            CREATE TRIGGER check_all_items_confirmed
            AFTER INSERT OR UPDATE ON ocr_results
            FOR EACH ROW
            EXECUTE FUNCTION update_ocr_item_confirmation();
        END IF;
    END
    $$;
    """)
    conn.commit()
    print("Fungsi dan Trigger untuk konfirmasi ocr_items siap digunakan.")


    excel_file = 'SKU.xlsx'
    try:
        df = pd.read_excel(excel_file, usecols=range(9), skiprows=2, sheet_name='All NIVEA PL Mei 2024')
        df = df.dropna()

        # Insert data ke tabel data_pusat
        # Periksa apakah tabel kosong sebelum memasukkan data untuk menghindari duplikasi
        cursor.execute("SELECT COUNT(*) FROM data_pusat")
        count = cursor.fetchone()[0]

        if count == 0:

            cols_excel = list(column_mapping.keys())   # Kolom dari Excel
            cols_db = [column_mapping[col] for col in cols_excel]  # Kolom di DB
        
            for index, row in df.iterrows():
                placeholders = ', '.join(['%s'] * len(cols_db))
                cols_str = ', '.join(f'"{col}"' for col in cols_db)  # Nama kolom di DB
        
                cursor.execute(f"""
                    INSERT INTO data_pusat ({cols_str})
                    VALUES ({placeholders})
                """, tuple(row[col] for col in cols_excel))
        
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
