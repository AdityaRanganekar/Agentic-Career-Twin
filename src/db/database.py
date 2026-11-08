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
            try:
                conn.execute(text("DROP TABLE IF EXISTS career_assessments CASCADE;"))
                conn.execute(text("DROP TABLE IF EXISTS user_profiles CASCADE;"))
            except Exception:
                pass

            # 2. Safe schema migrations for students and analysis_runs columns
            col_migrations = [
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS username VARCHAR;",
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS password_hash VARCHAR;",
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS auth_provider VARCHAR DEFAULT 'local';",
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS google_id VARCHAR;",
                "ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS target_jd_hash VARCHAR;",
                "ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS jd_fit_score FLOAT;",
                "ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS project_quality_score FLOAT;",
                "ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS jd_missing_skills JSON;",
                "ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS recommended_resources JSON;",
                "ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS resume_filename VARCHAR;"
            ]
            for stmt in col_migrations:
                try:
                    conn.execute(text(stmt))
                except Exception as col_err:
                    logger.debug(f"Column migration step note: {col_err}")
            conn.commit()
            logger.info("Database migration: dropped legacy tables and updated students / analysis_runs columns.")
    except Exception as e:
        logger.warning(f"Schema migration note in init_db: {e}")
    logger.info("Database tables initialized successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
