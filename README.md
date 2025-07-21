OCR STRUK BELANJA API
======================

Requirement:
------------
- Python 3.11.9
- PostgreSQL 17

Install Dependency:
--------------------
> pip install -r requirements.txt

Masuk ke Folder utama
--------------------
>cd utama

Setup Database:
---------------
1. Pastikan PostgreSQL 17 sudah terinstall & berjalan.
2. Buat database:
> CREATE DATABASE strukAI;


3. Jalankan script berikut **saat pertama kali setup** untuk:
   - Membuat tabel data_pusat jika belum ada.
   - Mengisi data dari file Excel SKUNivea.xlsx ke database.

> python createTable.py


File createTable.py:
--------------------
Script ini otomatis:
- Membuat tabel data_pusat jika belum ada.
- Membaca file SKUNivea.xlsx.
- Mengisi data ke tabel data_pusat.

Pastikan:
- File SKUNivea.xlsx ada di folder project.
- File .env sudah diisi konfigurasi database & API Key Gemini.


Menjalankan API Server:
-----------------------
> python struk.py
atau:
> uvicorn struk:app --reload


Endpoint Utama:
---------------
- Health Check:
http://127.0.0.1:8000/

- Swagger Docs:
http://127.0.0.1:8000/docs

- Endpoint Upload Struk:
POST /struk-batch


Selesai.
