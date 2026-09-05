import pandas as pd

file_path = r"c:\Users\srajan shetty\Downloads\files (1) - Copy\cpi_1661.xlsx"
df = pd.read_excel(file_path, sheet_name='CPI Data')

print("Total rows:", len(df))
print("Distinct States:", df['state'].unique())
print("Distinct Sectors:", df['sector'].unique())
print("Distinct Items:", df['item'].unique())
print("Distinct Series:", df['series'].unique())
print("Distinct Base Years:", df['base_year'].unique())
