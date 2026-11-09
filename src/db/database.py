import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from src.db.models import Base, Taxonomy, MarketSnapshot, Market
from src.utils.logger import get_custom_logger
from dotenv import load_dotenv 

load_dotenv()
logger = get_custom_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/career_twin")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

BASELINE_ROLES = {
    "Data Scientist": {
        "Python": 0.95, "R": 0.82, "SQL": 0.90, "Scikit-Learn": 0.88,
        "Machine Learning": 0.92, "Pandas": 0.85, "NumPy": 0.80, "Statistics": 0.85,
        "Data Visualization": 0.78, "Tableau": 0.70, "Deep Learning": 0.75,
        "PyTorch": 0.72, "TensorFlow": 0.70, "A/B Testing": 0.68, "Git": 0.75
    },
    "Machine Learning Engineer": {
        "Python": 0.98, "PyTorch": 0.95, "TensorFlow": 0.90, "Docker": 0.88,
        "Kubernetes": 0.82, "Machine Learning": 0.95, "Deep Learning": 0.92,
        "AWS": 0.85, "MLOps": 0.88, "FastAPI": 0.80, "Git": 0.85,
        "Linux": 0.82, "CI/CD": 0.78, "SQL": 0.75, "C++": 0.72
    },
    "AI / LLM Engineer": {
        "Python": 0.98, "PyTorch": 0.94, "LLMs": 0.96, "Transformers": 0.92,
        "LangChain": 0.90, "LangGraph": 0.88, "RAG": 0.92, "HuggingFace": 0.90,
        "Vector Databases": 0.85, "Prompt Engineering": 0.82, "NLP": 0.90,
        "FastAPI": 0.82, "Docker": 0.85, "Fine-Tuning": 0.85, "Git": 0.80
    },
    "Agentic AI Engineer": {
        "Python": 0.98, "LangGraph": 0.95, "LangChain": 0.92, "Autonomous Agents": 0.94,
        "Agentic AI": 0.95, "LLMs": 0.92, "RAG": 0.90, "Vector Databases": 0.88,
        "Prompt Engineering": 0.85, "FastAPI": 0.85, "Docker": 0.82, "PyTorch": 0.78, "Git": 0.80
    },
    "Data Engineer": {
        "Python": 0.95, "SQL": 0.98, "Apache Spark": 0.92, "Apache Airflow": 0.90,
        "Snowflake": 0.88, "BigQuery": 0.85, "Kafka": 0.85, "ETL": 0.92,
        "Data Warehousing": 0.88, "AWS": 0.85, "Docker": 0.80, "PostgreSQL": 0.85,
        "dbt": 0.82, "Linux": 0.80, "Git": 0.80
    },
    "Data Analyst": {
        "SQL": 0.98, "Tableau": 0.92, "PowerBI": 0.90, "Excel": 0.95,
        "Python": 0.82, "Pandas": 0.80, "Data Visualization": 0.92, "Reporting": 0.88,
        "Business Intelligence": 0.88, "Statistics": 0.78, "A/B Testing": 0.72,
        "Data Analysis": 0.95, "R": 0.65, "Google Analytics": 0.60
    },
    "MLOps Engineer": {
        "Python": 0.95, "Docker": 0.95, "Kubernetes": 0.92, "CI/CD": 0.90,
        "MLOps": 0.96, "AWS": 0.88, "Terraform": 0.85, "Git": 0.88,
        "Linux": 0.88, "Machine Learning": 0.82, "FastAPI": 0.80, "Monitoring": 0.82,
        "Airflow": 0.80, "PyTorch": 0.75, "Prometheus": 0.75
    },
    "Backend Software Engineer": {
        "Python": 0.95, "PostgreSQL": 0.90, "FastAPI": 0.88, "Docker": 0.88,
        "REST API": 0.92, "Microservices": 0.88, "Redis": 0.82, "Git": 0.90,
        "SQL": 0.92, "Linux": 0.85, "CI/CD": 0.82, "AWS": 0.82,
        "Kubernetes": 0.78, "Unit Testing": 0.80, "Java": 0.75
    },
    "Full-Stack Developer": {
        "JavaScript": 0.95, "TypeScript": 0.92, "React": 0.95, "Node.js": 0.90,
        "Python": 0.85, "HTML": 0.90, "CSS": 0.90, "PostgreSQL": 0.85,
        "REST API": 0.88, "Git": 0.90, "Docker": 0.80, "Next.js": 0.82,
        "Tailwind CSS": 0.80, "GraphQL": 0.75, "AWS": 0.75
    },
    "Cloud / DevOps Engineer": {
        "AWS": 0.95, "Terraform": 0.92, "Docker": 0.95, "Kubernetes": 0.92,
        "CI/CD": 0.92, "Linux": 0.95, "Bash": 0.88, "Python": 0.85,
        "Git": 0.90, "Ansible": 0.80, "GCP": 0.80, "Azure": 0.80,
        "Networking": 0.82, "Security": 0.85, "Monitoring": 0.82
    },
    "Site Reliability Engineer": {
        "Linux": 0.95, "Kubernetes": 0.92, "Docker": 0.90, "Terraform": 0.88,
        "AWS": 0.85, "Python": 0.85, "Go": 0.80, "CI/CD": 0.88,
        "Prometheus": 0.82, "Grafana": 0.80, "Bash": 0.85, "Networking": 0.82
    },
    "Quantitative Researcher": {
        "Python": 0.95, "C++": 0.90, "R": 0.85, "Statistics": 0.95,
        "Statistical Modeling": 0.95, "Time-Series Analysis": 0.92, "Econometrics": 0.88,
        "Stochastic Calculus": 0.85, "Machine Learning": 0.85, "NumPy": 0.88,
        "Pandas": 0.88, "SQL": 0.80, "Linear Algebra": 0.88, "Mathematics": 0.90
    }
}

def create_resilient_engine():
    """
    Attempts to connect to the configured DATABASE_URL (e.g. Neon PostgreSQL or local PostgreSQL).
    If DATABASE_URL is a placeholder or fails to connect, automatically tries local PostgreSQL
    instances (localhost:5432/career_twin) before ever falling back to SQLite.
    Logs a clear, informative startup banner with the active engine and student count.
    """
    global DATABASE_URL
    raw_env_url = (os.getenv("DATABASE_URL") or "").strip()
    if raw_env_url.startswith("postgres://"):
        raw_env_url = raw_env_url.replace("postgres://", "postgresql://", 1)

    is_placeholder = (
        not raw_env_url
        or any(p in raw_env_url for p in ["ep-sample-pooler", "user:password", "<password>", "your_neon", "placeholder"])
    )

    candidate_urls = []
    if not is_placeholder and not raw_env_url.startswith("sqlite"):
        candidate_urls.append(raw_env_url)

    # Local PostgreSQL candidate fallbacks before SQLite
    candidate_urls.extend([
        "postgresql://postgres:admin123@localhost:5432/career_twin",
        "postgresql://postgres:postgres@localhost:5432/career_twin",
        "postgresql://postgres:@localhost:5432/career_twin",
        "postgresql://localhost:5432/career_twin"
    ])

    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
        "connect_args": {"connect_timeout": 10}
    }

    # 1. Attempt PostgreSQL connection across candidate URLs
    for cand in candidate_urls:
        try:
            eng = create_engine(cand, **engine_kwargs)
            with eng.connect() as conn:
                # Check student count if table exists
                student_count = 0
                try:
                    res = conn.execute(text("SELECT count(*) FROM students;"))
                    student_count = res.scalar() or 0
                except Exception:
                    pass

                # Mask password for secure logging
                safe_url = cand
                if "@" in cand and ":" in cand.split("@")[0]:
                    prefix, rest = cand.split("@", 1)
                    proto_user = prefix.split(":")[0] + ":" + prefix.split(":")[1]
                    safe_url = f"{proto_user}:***@{rest}"

                banner = (
                    "\n" + "=" * 80 + "\n"
                    f" [DATABASE] Connected to PostgreSQL: {safe_url}\n"
                    f" [DATABASE] Active students registered in database: {student_count}\n"
                    + "=" * 80 + "\n"
                )
                logger.info(banner)
                print(banner, flush=True)
                DATABASE_URL = cand
                return eng
        except Exception as cand_err:
            logger.debug(f"PostgreSQL connection candidate ({cand.split('@')[-1] if '@' in cand else cand}) unavailable: {cand_err}")

    # 2. Graceful fallback to local SQLite if all PostgreSQL options fail
    fallback_url = "sqlite:///career_twin.db"
    warning_banner = (
        "\n" + "!" * 80 + "\n"
        " [DATABASE WARNING] Could not connect to any PostgreSQL database!\n"
        f" [DATABASE WARNING] Falling back to local SQLite: {fallback_url}\n"
        " [DATABASE WARNING] To see PostgreSQL users, ensure PostgreSQL is running on port 5432.\n"
        + "!" * 80 + "\n"
    )
    logger.warning(warning_banner)
    print(warning_banner, flush=True)
    DATABASE_URL = fallback_url
    return create_engine(fallback_url, connect_args={"check_same_thread": False})

engine = create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def auto_seed_baseline_data():
    """Seeds baseline canonical taxonomies and 12 core disciplines on fresh/empty database."""
    db = SessionLocal()
    try:
        tax_count = db.query(Taxonomy).count()
        if tax_count == 0:
            logger.info("Empty database detected: Auto-seeding canonical taxonomy concepts...")
            from src.engine.competency_clusters import BASELINE_CANONICAL_TAXONOMY
            for item in BASELINE_CANONICAL_TAXONOMY:
                db.add(Taxonomy(
                    category=item["category"],
                    name=item["name"],
                    aliases=list(dict.fromkeys(item.get("aliases", [])))
                ))
            db.commit()
            logger.info(f"Auto-seeded {len(BASELINE_CANONICAL_TAXONOMY)} taxonomy concepts.")

        snap_count = db.query(MarketSnapshot).count()
        if snap_count == 0:
            logger.info("Empty database detected: Auto-seeding 12 baseline career disciplines...")
            now = datetime.now(timezone.utc)
            for role_name, weights in BASELINE_ROLES.items():
                db.add(MarketSnapshot(
                    target_role=role_name,
                    market_corpus_version="2026-Live",
                    tfidf_weights=weights,
                    timestamp=now
                ))
                trending = [{"skill": k, "frequency": int(v * 100)} for k, v in weights.items()]
                db.add(Market(
                    role_name=role_name,
                    trending_skills=trending,
                    demand_score=float(len(weights) * 15),
                    last_analyzed=now
                ))
            db.commit()
            logger.info(f"Auto-seeded {len(BASELINE_ROLES)} baseline discipline market snapshots.")
    except Exception as e:
        logger.warning(f"Auto-seeding note in init_db: {e}")
        db.rollback()
    finally:
        db.close()

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

    # 3. Auto-seed canonical data if DB is empty (fresh cloud deploy)
    auto_seed_baseline_data()
    try:
        with SessionLocal() as s:
            from src.db.models import Student
            cnt = s.query(Student).count()
            logger.info(f"Verified database operational: {cnt} registered students ready for login.")
    except Exception:
        pass
    logger.info("Database tables initialized successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
