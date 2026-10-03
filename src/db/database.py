import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base
from src.utils.logger import get_custom_logger
from dotenv import load_dotenv 

load_dotenv()

logger = get_custom_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/career_twin")

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Successfully configured PostgreSQL database engine.")
except Exception as e:
    logger.error(f"Failed to initialize database engine: {e}")
    raise

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()