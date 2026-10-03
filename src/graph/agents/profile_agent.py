from sqlalchemy.orm import Session
from src.domain.state import CareerTwinState
from src.engine.skill_extractor import process_resume
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def run_profile_agent(state: CareerTwinState, db: Session) -> dict:
    """
    Extracts structured data from the uploaded resume and normalizes skills 
    against the taxonomy database.
    """
    logger.info("Profile Agent invoked. Processing resume PDF.")
    
    try:
        twin_profile = process_resume(state["pdf_bytes"], db)
 
        normalized_skills = [
            skill.skill_name for skill in twin_profile.extracted_skills
        ]
        
        return {
            "student_profile": twin_profile,
            "normalized_student_skills": normalized_skills
        }
        
    except Exception as e:
        logger.error(f"Profile Agent failed: {str(e)}")
        return {"errors": [f"Profile extraction failed: {str(e)}"]}