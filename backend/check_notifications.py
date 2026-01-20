"""Check and fix notifications table"""
import sqlite3

conn = sqlite3.connect('c:/Users/PC/Desktop/anti2/v2/backend/data/portal.db')
cursor = conn.cursor()

# Check if notifications table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
exists = cursor.fetchone()

if exists:
    print("Notifications table exists!")
    cursor.execute("PRAGMA table_info(notifications)")
    rows = cursor.fetchall()
    for r in rows:
        print(f"  {r}")
else:
    print("Notifications table does NOT exist. Creating it...")
    cursor.execute('''
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT,
            link VARCHAR(500),
            is_read BOOLEAN DEFAULT 0 NOT NULL,
            read_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute("CREATE INDEX ix_notifications_user_id ON notifications(user_id)")
    cursor.execute("CREATE INDEX ix_notifications_type ON notifications(type)")
    conn.commit()
    print("Notifications table created successfully!")

conn.close()
