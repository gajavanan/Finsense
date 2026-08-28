from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Handle both postgresql+psycopg and sqlite for local dev
database_url = settings.DATABASE_URL
# Neon recommends postgresql+psycopg with sslmode=require; also support psycopg2
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # SQLite uses SingletonThreadPool by default - do not set pool_size/max_overflow
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
        echo=False,
    )
else:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args=connect_args,
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
