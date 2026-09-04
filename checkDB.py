import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-DB6NAB1\\MSSQLSERVER22;"
    "DATABASE=AudiophileDB;"
    "Trusted_Connection=yes;"
)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM Gear")
print(f"[*] Total Gear Items in DB: {cursor.fetchone()[0]}")
conn.close()