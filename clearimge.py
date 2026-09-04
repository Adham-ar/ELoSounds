import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-DB6NAB1\\MSSQLSERVER22;"
    "DATABASE=AudiophileDB;"
    "Trusted_Connection=yes;"
)
cursor = conn.cursor()
cursor.execute("UPDATE Gear SET ImageURL = NULL")
conn.commit()
conn.close()
print("[✔] Reset all broken ImageURL entries to NULL.")