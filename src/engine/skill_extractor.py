from sqlalchemy.orm import Session
from src.llm.extraction_parser import extract_text_from_pdf, generate_student_twin
from src.engine.skill_normalizer import SkillNormalizer
from src.engine.deduplicator import SkillDeduplicator
from src.domain.schemas import StudentTwinProfile
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

from src.graph.agents.gap_agent import NOISE_WORDS

def process_resume(pdf_bytes: bytes, db: Session) -> StudentTwinProfile:
    """
    End-to-end pipeline: PDF -> Clean Text -> LLM Extraction -> Deterministic Normalization
    Retains canonical taxonomy names where matched, while preserving non-taxonomy technical
    skills for downstream Two-Tier Hybrid matching.
    """
    raw_text = extract_text_from_pdf(pdf_bytes)

    twin_profile = generate_student_twin(raw_text)
 
    normalizer = SkillNormalizer(db)
    normalized_skills = []
    
    for skill_evidence in twin_profile.extracted_skills:
        raw_name = skill_evidence.skill_name.strip()
        if not raw_name or raw_name.lower() in NOISE_WORDS:
            logger.info(f"Filtering non-technical noise word: {raw_name}")
            continue

        canonical_name = normalizer.normalize(raw_name)
        if canonical_name:
            skill_evidence.skill_name = canonical_name
            normalized_skills.append(skill_evidence)
        else:
            # Retain non-taxonomy technical skills for downstream hybrid matching
            skill_evidence.skill_name = raw_name
            normalized_skills.append(skill_evidence)
            logger.debug(f"Retained non-taxonomy technical skill for hybrid matching: {raw_name}")
            
    # Deduplicate repeated skill mentions while keeping most recent evidence dates
    twin_profile.extracted_skills = SkillDeduplicator.deduplicate_skills(normalized_skills)
    
    logger.info(f"Resume processing complete. Kept {len(twin_profile.extracted_skills)} validated, deduplicated skills.")
    return twin_profile