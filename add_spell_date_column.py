#!/usr/bin/env python
"""Migration script to add spell_date column to tag table"""

import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'database', 'db.sqlite3')

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(tag)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'spell_date' in columns:
        print("Column 'spell_date' already exists in tag table")
    else:
        print("Adding 'spell_date' column to tag table...")
        cursor.execute("ALTER TABLE tag ADD COLUMN spell_date VARCHAR")
        conn.commit()
        print("Successfully added 'spell_date' column")

    conn.close()
    print("\nMigration completed successfully!")

except sqlite3.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"Error: {e}")
