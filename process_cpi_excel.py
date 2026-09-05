import pandas as pd
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

EXCEL_FILE = r"c:\Users\srajan shetty\Downloads\files (1) - Copy\cpi_1661.xlsx"
DB_FILE = r"c:\Users\srajan shetty\Downloads\files (1) - Copy\sih26056-collector\airfare.db"

def process_cpi_data():
    try:
        logger.info(f"Reading {EXCEL_FILE}...")
        df = pd.read_excel(EXCEL_FILE, sheet_name='CPI Data')
        
        # Keep only the relevant columns
        columns_to_keep = ['year', 'month', 'state', 'sector', 'item', 'index', 'inflation']
        df_clean = df[columns_to_keep].copy()
        
        # We can rename index to cpi_index to avoid SQL keyword conflicts, but 'index' is fine if quoted. Let's rename for safety.
        df_clean = df_clean.rename(columns={'index': 'cpi_index'})
        
        logger.info(f"Cleaned data shape: {df_clean.shape}")
        
        # Save to SQLite
        conn = sqlite3.connect(DB_FILE)
        
        logger.info(f"Writing to official_cpi table in {DB_FILE}...")
        df_clean.to_sql('official_cpi', conn, if_exists='replace', index=False)
        
        conn.close()
        logger.info("Successfully processed and saved official CPI data.")
        
    except Exception as e:
        logger.error(f"Error processing CPI data: {e}")

if __name__ == "__main__":
    process_cpi_data()
