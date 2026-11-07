from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional

from src.db.database import get_db
from src.db.models import Student, AnalysisRun, StudentTwin
from src.db.crud import get_or_create_student, get_latest_analysis_run, create_analysis_run, upsert_student_twin
from src.domain.schemas import StudentTwinProfile
from src.utils.hashing import hash_text
from src.graph.workflow import compile_career_twin_graph
from src.llm.extraction_parser import extract_text_from_upload
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)
router = APIRouter()

@router.post("/process-resume")
@router.post("/analyze")
async def process_resume(
    file: Optional[UploadFile] = File(None),
    jd_file: Optional[UploadFile] = File(None),
    target_role: str = Form(...),
    target_jd_text: Optional[str] = Form(None),
    cached_profile_json: Optional[str] = Form(None),
    force_live_refresh: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Ingests a resume (or pre-cached profile JSON), triggers the LangGraph orchestration,
    and returns the mathematically validated roadmap, market readiness score, historical delta,
    and target JD fit score. Supports PDF, DOCX, and TXT for both resumes and custom JDs.
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
            # 1. Fetch historical run BEFORE creating the new run to compute correct delta
            student = get_or_create_student(db, name=student_name, email=contact_email)
            student_id = student.id
            student_email_val = student.email
            previous_run = get_latest_analysis_run(db, student_id=student.id, target_role=target_role)

            if previous_run:
                score_delta = round(current_score - previous_run.readiness_score, 2)
                previous_timestamp = previous_run.timestamp.isoformat()

            # 2. Persist the current run with dual-scoring results
            jd_fit = final_state.get("jd_fit_score")
            jd_hash = hash_text(target_jd_text) if target_jd_text and target_jd_text.strip() else None

            create_analysis_run(
                db=db,
                student_id=student.id,
                target_role=target_role,
                score=current_score,
                gaps=missing_skills,
                jd_fit_score=jd_fit,
                target_jd_hash=jd_hash
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
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Graph execution critical failure: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred during resume analysis execution: {str(e)}"
        )
