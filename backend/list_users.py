import sys
sys.path.insert(0, r"D:\finance ai\backend")
from app.core.database import SessionLocal
from app.models import User
db=SessionLocal()
users=db.query(User).all()
print(f"total users {len(users)}")
for u in users[:10]:
    print(u.email, "| verified", u.is_verified, "| id", u.id[:8])
db.close()
