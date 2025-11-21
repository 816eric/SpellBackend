import sqlite3
import sys

if len(sys.argv) != 2:
    print("Usage: python drop_table.py <table_name>")
    sys.exit(1)

table_name = sys.argv[1]
db_path = 'database/db.sqlite3'  # Adjust path if needed

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
    conn.commit()
    print(f"Dropped table: {table_name}")
except Exception as e:
    print(f"Error dropping table {table_name}: {e}")
finally:
    conn.close()
