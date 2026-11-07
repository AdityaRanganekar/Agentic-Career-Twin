import hashlib
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.db.models import Student, AnalysisRun, MarketSnapshot, Job, JobSkill, StudentTwin
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def normalize_email(email: Optional[str], fallback_name: Optional[str] = None) -> str:
    """
    Normalizes an email address. If email is missing or 'unknown', generates
    a deterministic email alias based on the candidate's normalized name.
    """
    if email and email.strip().lower() not in {"", "unknown", "none", "null"}:
        return email.strip().lower()
        
    normalized_name = (fallback_name or "anonymous_student").strip().lower()
    name_hash = hashlib.sha256(normalized_name.encode("utf-8")).hexdigest()[:12]
    return f"{name_hash}@twin.local"

def get_or_create_student(db: Session, name: Optional[str], email: Optional[str]) -> Student:
    """
    Retrieves an existing student record by normalized email, or creates a new one.
    """
    clean_email = normalize_email(email, fallback_name=name)
    clean_name = name.strip() if name and name.strip() not in {"", "unknown", "none", "null"} else "Anonymous Student"

    student = db.query(Student).filter(Student.email == clean_email).first()
    if student:
        # Update name if previously anonymous but now provided
        if student.name in {"Anonymous Student", None, "Unknown"} and clean_name != "Anonymous Student":
            student.name = clean_name
            db.commit()
            db.refresh(student)
        logger.info(f"Retrieved existing student: ID={student.id}, Email={student.email}")
        return student

    logger.info(f"Creating new student profile: Name='{clean_name}', Email='{clean_email}'")
    student = Student(email=clean_email, name=clean_name)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

def get_latest_analysis_run(db: Session, student_id: int, target_role: str) -> Optional[AnalysisRun]:
    """
    Fetches the most recent analysis run for a specific student and target role, ordered by timestamp descending.
    """
    return (
        db.query(AnalysisRun)
        .filter(AnalysisRun.student_id == student_id, AnalysisRun.target_role == target_role)
        .order_by(AnalysisRun.timestamp.desc())
        .first()
    )

def create_analysis_run(
    db: Session,
    student_id: int,
    target_role: str,
    score: float,
    gaps: List[str],
    jd_fit_score: Optional[float] = None,
    target_jd_hash: Optional[str] = None
) -> AnalysisRun:
    """
    Persists a new analysis run record linked to the student with dual-scoring results.
    """
    new_run = AnalysisRun(
        student_id=student_id,
        target_role=target_role,
        readiness_score=score,
        jd_fit_score=jd_fit_score,
        target_jd_hash=target_jd_hash,
        missing_skills=gaps,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)
    logger.info(f"Persisted AnalysisRun: ID={new_run.id}, StudentID={student_id}, Role='{target_role}', Score={score}%")
    return new_run

def get_latest_market_snapshot(db: Session, target_role: str) -> Optional[MarketSnapshot]:
    """Fetches the most recent MarketSnapshot for a given role."""
    return (
        db.query(MarketSnapshot)
        .filter(MarketSnapshot.target_role == target_role)
        .order_by(MarketSnapshot.timestamp.desc())
        .first()
    )

def save_market_snapshot(
    db: Session,
    target_role: str,
    market_corpus_version: str,
    tfidf_weights: dict
) -> MarketSnapshot:
    """Saves a new MarketSnapshot record with computed TF-IDF weights."""
    snapshot = MarketSnapshot(
        target_role=target_role,
        market_corpus_version=market_corpus_version,
        tfidf_weights=tfidf_weights,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    logger.info(f"Saved MarketSnapshot {snapshot.snapshot_id} for role '{target_role}', version '{market_corpus_version}'")
    return snapshot

def upsert_job(
    db: Session,
    job_hash: str,
    target_role: str,
    title: Optional[str],
    company: Optional[str],
    location: Optional[str],
    raw_payload: dict,
    skills: List[str],
    snapshot_id: Optional[int] = None
) -> Job:
    """Inserts or updates a job posting and its extracted skills."""
    existing_job = db.query(Job).filter(Job.job_hash == job_hash).first()
    if existing_job:
        return existing_job
        
    job = Job(
        job_hash=job_hash,
        snapshot_id=snapshot_id,
        target_role=target_role,
        title=title,
        company=company,
        location=location,
        raw_payload=raw_payload,
        created_at=datetime.now(timezone.utc)
    )
    db.add(job)
    db.flush()
    
    for skill in set(skills):
        if skill and skill.strip():
            db.add(JobSkill(job_hash=job_hash, skill_name=skill.strip(), required_flag=True))
            
    db.commit()
    db.refresh(job)
    return job

def upsert_student_twin(
    db: Session,
    student_email: str,
    current_skills: List[str],
    target_role: str,
    experience_level: Optional[str] = "Entry-to-Mid"
) -> StudentTwin:
    """Inserts or updates the digital twin representation for a student."""
    clean_email = student_email.strip().lower()
    twin = db.query(StudentTwin).filter(StudentTwin.student_id == clean_email).first()
    if twin:
        twin.current_skills = list(dict.fromkeys(current_skills))
        current_roles = list(twin.target_roles or [])
        if target_role and target_role not in current_roles:
            current_roles.append(target_role)
            twin.target_roles = current_roles
        if experience_level:
            twin.experience_level = experience_level
        twin.updated_at = datetime.now(timezone.utc)
    else:
        twin = StudentTwin(
            student_id=clean_email,
            current_skills=list(dict.fromkeys(current_skills)),
            target_roles=[target_role] if target_role else [],
            experience_level=experience_level or "Entry-to-Mid",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(twin)
    db.commit()
    db.refresh(twin)
    logger.info(f"Upserted StudentTwin for '{clean_email}' with {len(current_skills)} skills and target '{target_role}'")
    return twin


