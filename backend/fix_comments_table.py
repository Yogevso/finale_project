"""Fix comments table - add missing columns"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'app.db')
print(f"Database path: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("\nTables in database:")
for t in tables:
    print(f"  {t[0]}")

# Check if comments table exists
if ('comments',) not in tables:
    print("\n⚠️ Comments table does not exist! Creating it...")
    # Create the comments table with all columns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            parent_id INTEGER,
            content TEXT NOT NULL,
            is_private BOOLEAN DEFAULT 0 NOT NULL,
            anchor_text TEXT,
            anchor_id VARCHAR(100),
            is_resolved BOOLEAN DEFAULT 0 NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (parent_id) REFERENCES comments(id)
        )
    """)
    print("✅ Comments table created!")
else:
    print("\nComments table exists. Checking columns...")
    cursor.execute("PRAGMA table_info(comments)")
    columns = cursor.fetchall()
    col_names = [c[1] for c in columns]
    print(f"Current columns: {col_names}")
    
    # Add missing columns
    new_columns = [
        ("is_private", "BOOLEAN DEFAULT 0"),
        ("anchor_text", "TEXT"),
        ("anchor_id", "VARCHAR(100)"),
        ("is_resolved", "BOOLEAN DEFAULT 0"),
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in col_names:
            try:
                cursor.execute(f"ALTER TABLE comments ADD COLUMN {col_name} {col_type}")
                print(f"✅ Added column: {col_name}")
            except Exception as e:
                print(f"❌ Error adding {col_name}: {e}")
        else:
            print(f"  Column {col_name} already exists")

conn.commit()
conn.close()
print("\n✅ Done!")
