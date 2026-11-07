import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.db.models import Base
from src.utils.logger import get_custom_logger
from dotenv import load_dotenv 

load_dotenv()
logger = get_custom_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/career_twin")

def create_resilient_engine():
    """
    Attempts to connect to the configured DATABASE_URL (e.g. PostgreSQL).
    If unavailable, gracefully falls back to a local SQLite database (career_twin.db)
    to enable instant local evaluation and testing without external service blockers.
    """
    connect_args = {}
    if "sqlite" in DATABASE_URL:
        connect_args["check_same_thread"] = False
        
    try:
        eng = create_engine(DATABASE_URL, connect_args=connect_args)
        # Test active connection
        with eng.connect() as conn:
            pass
        logger.info(f"Database engine successfully connected to primary URL.")
        return eng
    except Exception as e:
        fallback_url = "sqlite:///career_twin.db"
        logger.warning(
            f"Primary database connection failed ({e}). "
            f"Falling back to local SQLite: {fallback_url}"
        )
        return create_engine(fallback_url, connect_args={"check_same_thread": False})

engine = create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            # 1. Drop dead legacy tables permanently
            conn.execute(text("DROP TABLE IF EXISTS career_assessments CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS user_profiles CASCADE;"))
            # 2. Fix PostgreSQL schema migrations for analysis_runs
            conn.execute(text("ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS target_jd_hash VARCHAR;"))
            conn.execute(text("ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS jd_fit_score FLOAT;"))
            conn.commit()
            logger.info("Database migration: dropped legacy tables and updated analysis_runs columns.")
    except Exception as e:
        logger.warning(f"Schema migration note in init_db: {e}")
    logger.info("Database tables initialized successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
