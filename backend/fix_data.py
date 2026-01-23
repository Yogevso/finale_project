"""Fix data enum mismatches in the database."""
from app.db import engine
from sqlalchemy import text

conn = engine.connect()

# Fix user roles - SUPER_ADMIN should be SYSTEM_ADMIN
result1 = conn.execute(text("UPDATE users SET role = 'SYSTEM_ADMIN' WHERE role = 'SUPER_ADMIN'"))
print(f"Fixed SUPER_ADMIN -> SYSTEM_ADMIN: {result1.rowcount} rows")

# Fix any lowercase roles
result2 = conn.execute(text("UPDATE users SET role = UPPER(role)"))
print(f"Uppercased roles: {result2.rowcount} rows")

# Fix documents visibility and status
result3 = conn.execute(text("UPDATE documents SET visibility = UPPER(visibility), status = UPPER(status)"))
print(f"Fixed documents: {result3.rowcount} rows")

conn.commit()
print("All data fixed!")
conn.close()
