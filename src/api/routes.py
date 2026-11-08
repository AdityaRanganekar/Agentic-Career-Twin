import os
import requests
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional

from src.db.database import get_db
from src.db.models import Student, AnalysisRun, StudentTwin
from src.db.crud import (
    get_or_create_student,
    get_latest_analysis_run,
    create_analysis_run,
    upsert_student_twin,
    create_student_user,
    authenticate_user,
    authenticate_or_create_google_user,
    get_student_history
)
from src.api.schemas import (
    SignupRequest,
    LoginRequest,
    GoogleAuthRequest,
    UserResponse,
    HistoricalRunResponse
)
from src.domain.schemas import StudentTwinProfile
from src.utils.hashing import hash_text
from src.graph.workflow import compile_career_twin_graph
from src.llm.extraction_parser import extract_text_from_upload
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)
router = APIRouter()

# -------------------------------------------------------------
# Authentication Endpoints (Bcrypt & Google OAuth)
# -------------------------------------------------------------
@router.post("/auth/signup", response_model=UserResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    """Registers a new user account with bcrypt password hashing."""
    try:
        student = create_student_user(
            db=db,
            name=req.name,
            username=req.username,
            email=req.email,
            password=req.password
        )
        return UserResponse(
            student_id=student.id,
            name=student.name,
            username=student.username,
            email=student.email,
            auth_provider=student.auth_provider
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/auth/login", response_model=UserResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates a user via either username or email with bcrypt verification."""
    student = authenticate_user(db, identifier=req.identifier, password=req.password)
    if not student:
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")
    return UserResponse(
        student_id=student.id,
        name=student.name,
        username=student.username,
        email=student.email,
        auth_provider=student.auth_provider
    )

@router.get("/auth/google-url")
def get_google_auth_url():
    """Returns Google OAuth authorization URL if credentials are configured in environment."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")
    if client_id and client_secret:
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={urllib.parse.quote(client_id)}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
            f"access_type=offline"
        )
        return {"configured": True, "auth_url": auth_url}
    return {"configured": False, "auth_url": None}

@router.post("/auth/google", response_model=UserResponse)
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Authenticates via Google: exchanges OAuth code if configured,
    or accepts verified Google profile payload for local/demo sign-in.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")

    email = req.email
    name = req.name
    google_id = req.google_id

    # If OAuth authorization code is provided, exchange for user profile
    if req.code and client_id and client_secret:
        try:
            token_resp = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": req.code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                },
                timeout=10
            )
            if token_resp.status_code == 200:
                tokens = token_resp.json()
                access_token = tokens.get("access_token")
                userinfo_resp = requests.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                if userinfo_resp.status_code == 200:
                    info = userinfo_resp.json()
                    email = info.get("email")
                    name = info.get("name")
                    google_id = info.get("sub")
        except Exception as oauth_err:
            logger.warning(f"Google OAuth code exchange note: {oauth_err}")

    if not email:
        raise HTTPException(status_code=400, detail="Google authentication requires email address or valid OAuth code.")

    student = authenticate_or_create_google_user(
        db=db,
        email=email,
        name=name,
        google_id=google_id
    )
    return UserResponse(
        student_id=student.id,
        name=student.name,
        username=student.username,
        email=student.email,
        auth_provider=student.auth_provider
    )

# -------------------------------------------------------------
# Historical Runs & Study Archive
# -------------------------------------------------------------
@router.get("/history/{student_identifier}", response_model=List[HistoricalRunResponse])
def get_history(student_identifier: str, db: Session = Depends(get_db)):
    """Fetches complete chronological analysis run history for a student by ID, email, or username."""
    runs = get_student_history(db, student_identifier)
    return [
        HistoricalRunResponse(
            id=r.id,
            student_id=r.student_id,
            target_role=r.target_role,
            readiness_score=r.readiness_score,
            jd_fit_score=r.jd_fit_score,
            project_quality_score=r.project_quality_score,
            missing_skills=r.missing_skills or [],
            jd_missing_skills=r.jd_missing_skills or [],
            recommended_resources=r.recommended_resources or [],
            resume_filename=r.resume_filename,
            timestamp=r.timestamp
        )
        for r in runs
    ]

# -------------------------------------------------------------
# Resume Processing & Agentic Orchestration
# -------------------------------------------------------------
@router.post("/process-resume")
@router.post("/analyze")
async def process_resume(
    file: Optional[UploadFile] = File(None),
    jd_file: Optional[UploadFile] = File(None),
    target_role: str = Form(...),
    target_jd_text: Optional[str] = Form(None),
    cached_profile_json: Optional[str] = Form(None),
    force_live_refresh: bool = Form(False),
    authenticated_student_id: Optional[int] = Form(None),
    authenticated_email: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Ingests a resume (or pre-cached profile JSON), triggers the LangGraph orchestration,
    and returns the mathematically validated roadmap, market readiness score, historical delta,
    and target JD fit score. Supports PDF, DOCX, and TXT for both resumes and custom JDs.
    Links the run directly to authenticated user accounts when logged in.
    """
    logger.info(f"Processing resume/profile for role: '{target_role}' (Custom JD provided: {bool(target_jd_text or jd_file)}, Force refresh: {force_live_refresh})")

    pdf_bytes = b""
    pre_cached_profile = None

    # Handle JD file upload if provided
    if jd_file is not None and jd_file.filename:
        try:
            jd_bytes = await jd_file.read()
            extracted_jd = extract_text_from_upload(jd_bytes, jd_file.filename)
            if extracted_jd and extracted_jd.strip():
                target_jd_text = extracted_jd.strip()
                logger.info(f"Successfully extracted {len(target_jd_text)} chars from uploaded JD file: {jd_file.filename}")
        except Exception as jd_err:
            logger.warning(f"Failed extracting text from uploaded JD file ({jd_file.filename}): {str(jd_err)}")

    if cached_profile_json and cached_profile_json.strip():
        try:
            pre_cached_profile = StudentTwinProfile.model_validate_json(cached_profile_json)
            logger.info(f"Using cached StudentTwinProfile for candidate: {pre_cached_profile.student_name}")
        except Exception as e:
            logger.warning(f"Could not parse cached_profile_json: {str(e)}")

    if not pre_cached_profile:
        if file is None:
            raise HTTPException(status_code=400, detail="Either a resume PDF file or cached_profile_json must be provided.")
        pdf_bytes = await file.read()

    initial_state = {
        "pdf_bytes": pdf_bytes,
        "target_role": target_role,
        "target_jd_text": target_jd_text,
        "student_profile": pre_cached_profile,
        "force_live_refresh": force_live_refresh,
        "errors": [],
        "retries": 0
    }
    
    try:
        graph = compile_career_twin_graph(db)
        final_state = graph.invoke(initial_state)
        
        if final_state.get("errors"):
            logger.warning(f"Graph completed with recoverable errors: {final_state['errors']}")

        current_score = final_state.get("readiness_score", 0.0)
        missing_skills = final_state.get("missing_skills", [])
        recommendations = final_state.get("recommended_resources", [])
        errors = final_state.get("errors", [])
        market_corpus_version = final_state.get("market_corpus_version", "2017-Kaggle-Baseline")

        # Extract student identity from profile
        student_profile = final_state.get("student_profile")
        student_name = getattr(student_profile, "student_name", "Anonymous Student") if student_profile else "Anonymous Student"
        contact_email = getattr(student_profile, "contact_email", None) if student_profile else None

        score_delta = None
        previous_timestamp = None
        student_id = None
        student_email_val = contact_email

        # Persistent Digital Twin History (Wrapped safely in try...except)
        try:
            # 1. Prioritize authenticated user session if logged in
            student = None
            if authenticated_student_id:
                student = db.query(Student).filter(Student.id == authenticated_student_id).first()
            elif authenticated_email:
                student = db.query(Student).filter(Student.email == authenticated_email.strip().lower()).first()

            if not student:
                student = get_or_create_student(db, name=student_name, email=contact_email)

            student_id = student.id
            student_email_val = student.email
            previous_run = get_latest_analysis_run(db, student_id=student.id, target_role=target_role)

            if previous_run:
                score_delta = round(current_score - previous_run.readiness_score, 2)
                previous_timestamp = previous_run.timestamp.isoformat()

            # 2. Persist the current run with dual-scoring results, study resources, and file name
            jd_fit = final_state.get("jd_fit_score")
            jd_hash = hash_text(target_jd_text) if target_jd_text and target_jd_text.strip() else None
            resume_name = (
                file.filename if file and file.filename 
                else ("Cached Resume" if cached_profile_json else "Direct Assessment")
            )

            create_analysis_run(
                db=db,
                student_id=student.id,
                target_role=target_role,
                score=current_score,
                gaps=missing_skills,
                jd_fit_score=jd_fit,
                target_jd_hash=jd_hash,
                jd_missing_skills=final_state.get("jd_missing_skills") or [],
                recommended_resources=recommendations or [],
                project_quality_score=final_state.get("project_quality_score"),
                resume_filename=resume_name
            )

            # 3. Actively populate and synchronize the student_twins table
            extracted_skill_names = [s.skill_name for s in student_profile.extracted_skills] if student_profile else []
            upsert_student_twin(
                db=db,
                student_email=student.email,
                current_skills=extracted_skill_names,
                target_role=target_role,
                experience_level="Professional" if student_profile and student_profile.experience else "Student/Entry"
            )
        except Exception as db_err:
            db.rollback()
            logger.error(f"Failed to persist analysis history to database: {str(db_err)}")

        return {
            "student_id": student_id,
            "student_name": student_name,
            "student_email": student_email_val,
            "readiness_score": current_score,
            "score_delta": score_delta,
            "previous_timestamp": previous_timestamp,
            "missing_skills": missing_skills,
            "jd_fit_score": final_state.get("jd_fit_score"),
            "jd_missing_skills": final_state.get("jd_missing_skills"),
            "radar_dimensions": final_state.get("radar_dimensions"),
            "jd_radar_dimensions": final_state.get("jd_radar_dimensions"),
            "market_corpus_version": market_corpus_version,
            "recommendations": recommendations,
            "student_profile_json": student_profile.model_dump_json() if student_profile else None,
            "resume_quality_breakdown": final_state.get("resume_quality_breakdown"),
            "project_quality_score": final_state.get("project_quality_score"),
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Graph execution critical failure: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred during resume analysis execution: {str(e)}"
        )
