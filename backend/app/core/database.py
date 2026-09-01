import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

# Obtain DATABASE_URL from settings
database_url = settings.DATABASE_URL.strip()

# Normalize PostgreSQL scheme for SQLAlchemy 2.0 compatibility
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Ensure postgresql dialect uses psycopg2 driver if no specific driver sub-scheme was provided
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Create engine with driver-specific configurations
if database_url.startswith("sqlite"):
    # SQLite local development configuration
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=False,
    )
else:
    # Production PostgreSQL / Neon connection pool configuration
    # pool_pre_ping validates connection health before handing it out
    # pool_recycle recycles connections periodically to handle Neon serverless idle disconnects
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
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
