import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# The Supabase connection string from .env
POSTGRES_URL = os.environ.get("DATABASE_URL")
SQLITE_DB = "airfare.db"

def migrate():
    print("Connecting to PostgreSQL...")
    pg_engine = create_engine(POSTGRES_URL)
    
    # 1. Execute schema.sql
    print("Applying schema.sql to PostgreSQL...")
    with open("schema.sql", "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    with pg_engine.begin() as conn:
        try:
            # Drop tables if they exist to restart clean
            conn.execute(text("DROP TABLE IF EXISTS fare_observations, fare_observations_clean, airfare_index, official_cpi CASCADE;"))
            
            # Remove comments and execute whole block
            clean_sql = "\n".join([line for line in schema_sql.split('\n') if not line.strip().startswith('--')])
            for stmt in clean_sql.split(';'):
                if stmt.strip():
                    try:
                        conn.execute(text(stmt.strip()))
                    except Exception as e:
                        if "could not open extension control file" in str(e) or "timescaledb" in str(e):
                            print(f"Skipping TimescaleDB hypertable setup (likely not supported on this host).")
                        else:
                            print(f"Error executing statement: {e}")
                            raise
        except Exception as e:
            print(f"Schema creation failed: {e}")
            return

    # 2. Migrate data
    print("Migrating data from SQLite...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    
    tables = [
        "fare_observations", 
        "fare_observations_clean", 
        "airfare_index", 
        "official_cpi"
    ]
    
    for table in tables:
        try:
            df = pd.read_sql(f"SELECT * FROM {table}", sqlite_conn)
            print(f"Found {len(df)} rows in SQLite table '{table}'.")
            if not df.empty:
                # if the table has an 'id' column, we drop it before inserting to Postgres 
                # so Postgres can auto-generate via BIGSERIAL
                if 'id' in df.columns:
                    df = df.drop(columns=['id'])
                
                # PostgreSQL strict boolean casting from SQLite integers
                for col in ['is_price_band', 'is_duplicate', 'is_outlier']:
                    if col in df.columns:
                        df[col] = df[col].astype(bool)
                
                print(f"Inserting into PostgreSQL table '{table}'...")
                df.to_sql(table, pg_engine, if_exists='append', index=False)
                print(f"Migrated {table} successfully.")
        except Exception as e:
            print(f"Skipped table {table}: {e}")
            
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
