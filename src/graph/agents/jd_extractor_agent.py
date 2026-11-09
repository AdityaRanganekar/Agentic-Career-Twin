import json
import google.generativeai as genai
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from src.domain.state import CareerTwinState
from src.domain.schemas import JDExtractionResult
from src.engine.competency_clusters import consolidate_target_weights
from src.llm.client import get_gemini_client
from src.llm.prompts import JD_EXTRACTION_PROMPT
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

NOISE_WORDS = {
    "communication", "teamwork", "leadership", "fast-paced", "problem solving",
    "critical thinking", "collaboration", "self-starter", "passionate", "motivated",
    "bachelor's degree", "master's degree", "phd", "degree", "years of experience"
}

def deterministic_extract_jd_weights(target_jd_text: str, db: Optional[Session] = None) -> Dict[str, float]:
    """
    Deterministic regex and taxonomy fallback that extracts weighted requirements directly
    from target Job Description text in < 20ms when Gemini is offline, unreachable, or times out.
    """
    import re
    from src.engine.skill_normalizer import TOOL_CANONICAL_CASING
    from src.engine.competency_clusters import BASELINE_CANONICAL_TAXONOMY, consolidate_target_weights

    jd_weights: Dict[str, float] = {}
    jd_lower = target_jd_text.lower()

    # 1. Match TOOL_CANONICAL_CASING
    for alias, canonical in TOOL_CANONICAL_CASING.items():
        if len(alias) >= 2 and canonical.lower() not in NOISE_WORDS:
            pattern = r'(?<![a-zA-Z0-9_#+.-])' + re.escape(alias) + r'(?![a-zA-Z0-9_#+.-])'
            if re.search(pattern, target_jd_text, re.IGNORECASE):
                jd_weights[canonical] = 1.0

    # 2. Match BASELINE_CANONICAL_TAXONOMY
    for item in BASELINE_CANONICAL_TAXONOMY:
        for alias in item.get("aliases", []):
            if len(alias) >= 2 and alias.lower() not in NOISE_WORDS:
                pattern = r'(?<![a-zA-Z0-9_#+.-])' + re.escape(alias) + r'(?![a-zA-Z0-9_#+.-])'
                if re.search(pattern, target_jd_text, re.IGNORECASE):
                    canonical = TOOL_CANONICAL_CASING.get(alias.lower(), alias.title())
                    if canonical not in jd_weights and canonical.lower() not in NOISE_WORDS:
                        jd_weights[canonical] = 1.0

    # Consolidate sibling alternatives via database taxonomy
    jd_weights = consolidate_target_weights(jd_weights, db=db)

    # Multi-branch engineering degree consolidation
    ENGINEERING_BRANCH_PATTERNS = [
        "mechanical engineering", "electrical engineering", "electronics engineering",
        "electronics & telecommunication engineering", "electronics and telecommunication engineering",
        "electronics & tele comm.", "electronics & tele comm", "electronics and communication engineering",
        "chemical engineering", "civil engineering", "computer engineering", "computer science engineering",
        "ai & ml engineering", "ai ml engineering"
    ]
    matched_branch_keys = []
    for k in list(jd_weights.keys()):
        k_low = k.strip().lower()
        if any(b in k_low for b in ENGINEERING_BRANCH_PATTERNS) or (
            ("mechanical" in k_low or "electrical" in k_low or "electronics" in k_low or "chemical" in k_low)
            and ("engineering" in k_low or "degree" in k_low or "graduate" in k_low)
        ):
            matched_branch_keys.append(k)

    if len(matched_branch_keys) >= 2:
        for mb in matched_branch_keys:
            if mb in jd_weights:
                del jd_weights[mb]
        jd_weights["Engineering Degree Eligibility (CS / AI-ML / Core Engineering)"] = 1.0

    # Functional department safeguard for TPO/Operations apprentice notices
    if "operations" in jd_lower and ("process planning" in jd_lower or "production" in jd_lower or "logistics" in jd_lower):
        if not any("process" in k.lower() or "operations" in k.lower() for k in jd_weights):
            jd_weights["Operations & Process Planning"] = 1.0
        if not any("quality" in k.lower() for k in jd_weights) and "quality" in jd_lower:
            jd_weights["Quality Assurance & Control"] = 1.0
        if not any("logistics" in k.lower() or "production" in k.lower() for k in jd_weights) and ("logistics" in jd_lower or "production" in jd_lower):
            jd_weights["Production & Logistics Systems"] = 1.0
        if not any("agile" in k.lower() for k in jd_weights) and "agile" in jd_lower:
            jd_weights["Agile Methodologies"] = 0.8

    return jd_weights

def run_jd_extractor_agent(state: CareerTwinState, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Extracts core and nice-to-have technical and professional competencies from an uploaded target Job Description (JD).
    Converts extracted skills into weighted requirements (1.0 for core, 0.5 for nice-to-have).
    Consolidates sibling alternatives across any domain dynamically via the PostgreSQL taxonomy.
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
            ),
            request_options={"timeout": 10}
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

        # --- POST-PROCESSING: Consolidate sibling alternatives via Database Taxonomy ---
        jd_weights = consolidate_target_weights(jd_weights, db=db)

        # Safeguard: Collapse multi-branch degree eligibility into a single requirement
        ENGINEERING_BRANCH_PATTERNS = [
            "mechanical engineering", "electrical engineering", "electronics engineering",
            "electronics & telecommunication engineering", "electronics and telecommunication engineering",
            "electronics & tele comm.", "electronics & tele comm", "electronics and communication engineering",
            "chemical engineering", "civil engineering", "computer engineering", "computer science engineering",
            "ai & ml engineering", "ai ml engineering"
        ]
        matched_branch_keys = []
        for k in list(jd_weights.keys()):
            k_low = k.strip().lower()
            if any(b in k_low for b in ENGINEERING_BRANCH_PATTERNS) or (
                ("mechanical" in k_low or "electrical" in k_low or "electronics" in k_low or "chemical" in k_low)
                and ("engineering" in k_low or "degree" in k_low or "graduate" in k_low)
            ):
                matched_branch_keys.append(k)

        if len(matched_branch_keys) >= 2:
            logger.info(f"Consolidating {len(matched_branch_keys)} multi-branch degree eligibility requirements into single requirement.")
            for mb in matched_branch_keys:
                del jd_weights[mb]
            jd_weights["Engineering Degree Eligibility (CS / AI-ML / Core Engineering)"] = 1.0

        # Functional department safeguard for TPO/Operations apprentice notices
        jd_lower = target_jd_text.lower()
        if "operations" in jd_lower and ("process planning" in jd_lower or "production" in jd_lower or "logistics" in jd_lower):
            if not any("process" in k.lower() or "operations" in k.lower() for k in jd_weights):
                jd_weights["Operations & Process Planning"] = 1.0
            if not any("quality" in k.lower() for k in jd_weights) and "quality" in jd_lower:
                jd_weights["Quality Assurance & Control"] = 1.0
            if not any("logistics" in k.lower() or "production" in k.lower() for k in jd_weights) and ("logistics" in jd_lower or "production" in jd_lower):
                jd_weights["Production & Logistics Systems"] = 1.0
            if not any("agile" in k.lower() for k in jd_weights) and "agile" in jd_lower:
                jd_weights["Agile Methodologies"] = 0.8

        logger.info(
            f"JD extraction complete: {len(jd_weights)} final weighted technical requirements."
        )

        return {"jd_extracted_reqs": jd_weights}

    except Exception as e:
        logger.warning(f"Gemini JD extraction unavailable ({e}). Engaging deterministic rule-based JD extractor fallback.")
        fallback_weights = deterministic_extract_jd_weights(target_jd_text, db=db)
        if fallback_weights:
            logger.info(f"Deterministic JD fallback extracted {len(fallback_weights)} requirements.")
            return {"jd_extracted_reqs": fallback_weights}
        logger.error(f"JD Extractor Agent failed: {str(e)}")
        return {
            "jd_extracted_reqs": None,
            "errors": state.get("errors", []) + [f"JD extraction failed: {str(e)}"]
        }

