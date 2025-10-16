import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_DB")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def get_db_conn():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        host=DB_HOST, port=DB_PORT
    )

def load_data_pusat():
    conn = None
    try:
        conn = get_db_conn()
        df = pd.read_sql_query("SELECT * FROM data_pusat", conn)
        df = df.dropna(subset=["description", "id", "harga_ppn"])
        return (
            df,
            df["description"].astype(str).str.lower().tolist(),
            df["id"].tolist(),
            df["harga_ppn"].tolist()
        )
    except Exception as e:
        print(f"Error loading data_pusat: {e}")
        return pd.DataFrame(), [], [], []
    finally:
        if conn:
            conn.close()
