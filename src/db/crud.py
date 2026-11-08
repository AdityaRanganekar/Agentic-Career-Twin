import hashlib
import bcrypt
from typing import Optional, List, Dict, Any
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

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt directly (Python 3.12 compatible)."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a bcrypt hash."""
    if not hashed_password or not plain_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_student_user(
    db: Session,
    name: str,
    username: str,
    email: str,
    password: str
) -> Student:
    """Creates a new registered user with bcrypt hashed password."""
    clean_email = email.strip().lower()
    clean_username = username.strip().lower()
    clean_name = name.strip() if name and name.strip() else clean_username

    if db.query(Student).filter(Student.email == clean_email).first():
        raise ValueError(f"An account with email '{clean_email}' already exists.")

    if db.query(Student).filter(Student.username == clean_username).first():
        raise ValueError(f"The username '{clean_username}' is already taken.")

    pwd_hash = hash_password(password)
    student = Student(
        name=clean_name,
        username=clean_username,
        email=clean_email,
        password_hash=pwd_hash,
        auth_provider="local"
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    logger.info(f"Created registered student: ID={student.id}, Username='{student.username}', Email='{student.email}'")
    return student

def authenticate_user(
    db: Session,
    identifier: str,
    password: str
) -> Optional[Student]:
    """Authenticates a user via either username OR email with bcrypt verification."""
    clean_id = identifier.strip().lower()
    student = db.query(Student).filter(
        (Student.email == clean_id) | (Student.username == clean_id)
    ).first()

    if not student or not student.password_hash:
        return None

    if verify_password(password, student.password_hash):
        logger.info(f"User authenticated successfully: ID={student.id}, Email='{student.email}'")
        return student

    logger.warning(f"Failed login attempt for identifier: '{clean_id}'")
    return None

def authenticate_or_create_google_user(
    db: Session,
    email: str,
    name: Optional[str] = None,
    google_id: Optional[str] = None
) -> Student:
    """Upserts a student with auth_provider='google'."""
    clean_email = email.strip().lower()
    student = None
    if google_id:
        student = db.query(Student).filter(Student.google_id == google_id).first()
    if not student:
        student = db.query(Student).filter(Student.email == clean_email).first()

    if student:
        if google_id and not student.google_id:
            student.google_id = google_id
        student.auth_provider = "google"
        if name and (student.name in {None, "", "Anonymous Student"}):
            student.name = name
        db.commit()
        db.refresh(student)
        return student

    clean_name = name.strip() if name and name.strip() else clean_email.split("@")[0]
    base_username = clean_email.split("@")[0].lower()
    username_candidate = base_username
    counter = 1
    while db.query(Student).filter(Student.username == username_candidate).first():
        username_candidate = f"{base_username}_{counter}"
        counter += 1

    student = Student(
        email=clean_email,
        name=clean_name,
        username=username_candidate,
        auth_provider="google",
        google_id=google_id
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    logger.info(f"Created Google authenticated student: ID={student.id}, Email='{student.email}'")
    return student

def get_student_by_identifier(db: Session, identifier: str) -> Optional[Student]:
    """Retrieves student by student_id (int), email, or username."""
    clean_id = str(identifier).strip()
    if clean_id.isdigit():
        student = db.query(Student).filter(Student.id == int(clean_id)).first()
        if student:
            return student
    clean_lower = clean_id.lower()
    return db.query(Student).filter(
        (Student.email == clean_lower) | (Student.username == clean_lower)
    ).first()

def get_student_history(db: Session, student_identifier: str) -> List[AnalysisRun]:
    """Fetches chronological analysis run history for a student."""
    student = get_student_by_identifier(db, student_identifier)
    if not student:
        return []
    return (
        db.query(AnalysisRun)
        .filter(AnalysisRun.student_id == student.id)
        .order_by(AnalysisRun.timestamp.desc())
        .all()
    )

def get_or_create_student(db: Session, name: Optional[str], email: Optional[str]) -> Student:
    """
    Retrieves an existing student record by normalized email, or creates a new one.
    """
    clean_email = normalize_email(email, fallback_name=name)
    clean_name = name.strip() if name and name.strip() not in {"", "unknown", "none", "null"} else "Anonymous Student"

    student = db.query(Student).filter(Student.email == clean_email).first()
    if student:
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
    target_jd_hash: Optional[str] = None,
    jd_missing_skills: Optional[List[str]] = None,
    recommended_resources: Optional[List[dict]] = None,
    project_quality_score: Optional[float] = None,
    resume_filename: Optional[str] = None
) -> AnalysisRun:
    """
    Persists a new analysis run record linked to the student with dual-scoring results,
    missing skill lists, study recommendations, and project rigor quality scores.
    """
    new_run = AnalysisRun(
        student_id=student_id,
        target_role=target_role,
        readiness_score=score,
        jd_fit_score=jd_fit_score,
        target_jd_hash=target_jd_hash,
        missing_skills=gaps or [],
        jd_missing_skills=jd_missing_skills or [],
        recommended_resources=recommended_resources or [],
        project_quality_score=project_quality_score,
        resume_filename=resume_filename,
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


