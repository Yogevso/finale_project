"""Fix notification data with correct enum values"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('c:/Users/PC/Desktop/anti2/v2/backend/data/portal.db')
cursor = conn.cursor()

# Delete existing notifications
cursor.execute('DELETE FROM notifications')
print('Deleted old notifications')

# Get super_admin user id
cursor.execute("SELECT id FROM users WHERE username = 'super_admin'")
user = cursor.fetchone()
if user:
    user_id = user[0]
    now = datetime.now().isoformat()
    # Insert notifications with UPPERCASE enum values (matching the Python enum)
    notifications = [
        (user_id, 'COMMENT_REPLY', 'New reply on your comment', 'Someone replied to your comment on Document #1', '/documents/1', 0, None, now),
        (user_id, 'DOCUMENT_UPDATED', 'Document Updated', 'Safety Protocol v2 was updated', '/documents/2', 0, None, now),
        (user_id, 'COMMENT_ADDED', 'New comment on your document', 'A new comment was added to your document', '/documents/3', 0, None, now),
    ]
    cursor.executemany('''
        INSERT INTO notifications (user_id, type, title, message, link, is_read, read_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', notifications)
    conn.commit()
    print(f'Added 3 test notifications for user_id {user_id}')
else:
    print('super_admin user not found')

conn.close()
print('Done!')
