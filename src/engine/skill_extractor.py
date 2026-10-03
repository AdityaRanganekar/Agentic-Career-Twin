from sqlalchemy.orm import Session
from src.llm.extraction_parser import extract_text_from_pdf, generate_student_twin
from src.engine.skill_normalizer import SkillNormalizer
from src.domain.schemas import StudentTwinProfile
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def process_resume(pdf_bytes: bytes, db: Session) -> StudentTwinProfile:
    """
    End-to-end pipeline: PDF -> Clean Text -> LLM Extraction -> Deterministic Normalization
    """
    raw_text = extract_text_from_pdf(pdf_bytes)

    twin_profile = generate_student_twin(raw_text)
 
    normalizer = SkillNormalizer(db)
    normalized_skills = []
    
    for skill_evidence in twin_profile.extracted_skills:
        canonical_name = normalizer.normalize(skill_evidence.skill_name)
        
        if canonical_name:
            skill_evidence.skill_name = canonical_name
            normalized_skills.append(skill_evidence)
        else:
            logger.info(f"Dropped unrecognized skill: {skill_evidence.skill_name}")
            
    twin_profile.extracted_skills = normalized_skills
    
    logger.info(f"Resume processing complete. Kept {len(normalized_skills)} validated skills.")
    return twin_profile