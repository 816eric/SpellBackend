#!/usr/bin/env python
"""Migration script to add quiz column to spellingword table"""

import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'database', 'db.sqlite3')

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(spellingword)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'quiz' in columns:
        print("✓ Column 'quiz' already exists in spellingword table")
    else:
        print("Adding 'quiz' column to spellingword table...")
        cursor.execute("ALTER TABLE spellingword ADD COLUMN quiz VARCHAR")
        conn.commit()
        print("✓ Successfully added 'quiz' column")
    
    conn.close()
    print("\n✓ Migration completed successfully!")
    
except sqlite3.Error as e:
    print(f"✗ Database error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
