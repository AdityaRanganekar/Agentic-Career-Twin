import json
import google.generativeai as genai
from typing import Dict, Any
from src.domain.state import CareerTwinState
from src.domain.schemas import JDExtractionResult
from src.llm.client import get_gemini_client
from src.llm.prompts import JD_EXTRACTION_PROMPT
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

NOISE_WORDS = {
    "communication", "teamwork", "leadership", "fast-paced", "problem solving",
    "critical thinking", "collaboration", "self-starter", "passionate", "motivated",
    "bachelor's degree", "master's degree", "phd", "degree", "years of experience"
}

def run_jd_extractor_agent(state: CareerTwinState) -> Dict[str, Any]:
    """
    Extracts core and nice-to-have technical skills from an uploaded target Job Description (JD).
    Converts extracted skills into weighted requirements (1.0 for core, 0.5 for nice-to-have).
    """
    target_jd_text = state.get("target_jd_text")
    if not target_jd_text or not target_jd_text.strip():
        logger.info("No target Job Description provided. Skipping JD Extractor Agent.")
        return {
            "jd_extracted_reqs": None,
            "jd_fit_score": None,
            "jd_missing_skills": None
        }

    logger.info("JD Extractor Agent invoked. Processing target Job Description.")
    prompt = JD_EXTRACTION_PROMPT.format(jd_text=target_jd_text.strip())

    try:
        model = get_gemini_client()
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=JDExtractionResult,
                temperature=0.0
            )
        )

        extraction_data = json.loads(response.text)
        result = JDExtractionResult(**extraction_data)

        # Convert into weighted requirements: 1.0 for core, 0.5 for nice-to-have
        jd_weights: Dict[str, float] = {}
        for skill in result.core_required_skills:
            clean = skill.strip()
            if clean and clean.lower() not in NOISE_WORDS:
                jd_weights[clean] = 1.0

        for skill in result.nice_to_have_skills:
            clean = skill.strip()
            if clean and clean.lower() not in NOISE_WORDS and clean not in jd_weights:
                jd_weights[clean] = 0.5

        logger.info(
            f"JD extraction complete: {len(result.core_required_skills)} core skills, "
            f"{len(result.nice_to_have_skills)} nice-to-have skills."
        )

        return {"jd_extracted_reqs": jd_weights}

    except Exception as e:
        logger.error(f"JD Extractor Agent failed: {str(e)}")
        return {
            "jd_extracted_reqs": None,
            "errors": state.get("errors", []) + [f"JD extraction failed: {str(e)}"]
        }

