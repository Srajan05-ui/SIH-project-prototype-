import pandas as pd
import sys

file_path = r"c:\Users\srajan shetty\Downloads\files (1) - Copy\cpi_1661.xlsx"

try:
    xl = pd.ExcelFile(file_path)
    print("Sheet names:", xl.sheet_names)
    
    for sheet in xl.sheet_names:
        print(f"\n--- Sheet: {sheet} ---")
        df = pd.read_excel(file_path, sheet_name=sheet)
        print("Shape:", df.shape)
        print("Columns:", list(df.columns))
        print("First 5 rows:")
        print(df.head(5).to_string())
except Exception as e:
    print(f"Error reading file: {e}")
