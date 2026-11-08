import os
import re
import json
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from src.llm.extraction_parser import extract_text_from_pdf, generate_student_twin
from src.engine.skill_normalizer import SkillNormalizer, TOOL_CANONICAL_CASING
from src.engine.competency_clusters import BASELINE_CANONICAL_TAXONOMY
from src.engine.deduplicator import SkillDeduplicator
from src.domain.schemas import StudentTwinProfile, SkillEvidence
from src.graph.agents.gap_agent import NOISE_WORDS
from src.utils.hashing import hash_bytes
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

CACHE_DIR = "logs"
CACHE_FILE = os.path.join(CACHE_DIR, "pdf_profile_cache.json")
_PDF_PROFILE_CACHE: Dict[str, str] = {}

def _load_cache():
    global _PDF_PROFILE_CACHE
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _PDF_PROFILE_CACHE = json.load(f)
            logger.info(f"Loaded {len(_PDF_PROFILE_CACHE)} cached resume profiles from {CACHE_FILE}")
        except Exception as e:
            logger.warning(f"Could not load PDF profile cache from {CACHE_FILE}: {e}")
            _PDF_PROFILE_CACHE = {}

def _save_cache():
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_PDF_PROFILE_CACHE, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save PDF profile cache to {CACHE_FILE}: {e}")

# Initialize in-memory cache from disk
_load_cache()

def process_resume(pdf_bytes: bytes, db: Session) -> StudentTwinProfile:
    """
    End-to-end pipeline: PDF -> SHA-256 Cache Check -> Clean Text -> LLM Extraction
    -> Deterministic Regex/Taxonomy Augmentation -> Deduplication & Normalization.
    Guarantees 100% deterministic results (0.00% variance) across identical resume uploads.
    """
    pdf_hash = hash_bytes(pdf_bytes)

    # 1. Check persistent cache for zero variance and instant evaluation
    if pdf_hash in _PDF_PROFILE_CACHE:
        try:
            cached_json = _PDF_PROFILE_CACHE[pdf_hash]
            profile = StudentTwinProfile.model_validate_json(cached_json)
            logger.info(f"Deterministic Cache HIT for resume SHA-256: {pdf_hash[:12]} ({profile.student_name})")
            return profile
        except Exception as cache_err:
            logger.warning(f"Failed parsing cached profile for {pdf_hash[:12]}: {cache_err}. Re-extracting.")

    # 2. Extract raw text from uploaded PDF
    raw_text = extract_text_from_pdf(pdf_bytes)

    # 3. LLM structured profile extraction
    twin_profile = generate_student_twin(raw_text)
    twin_profile.raw_resume_text = raw_text

    # 4. Deterministic Regex/Taxonomy Skill Augmentation:
    # Guarantees that canonical tools present in the resume text are never missed due to LLM variance.
    existing_skills_lower = {
        s.skill_name.strip().lower()
        for s in (twin_profile.extracted_skills or [])
        if s.skill_name
    }

    # A. Match known canonical tools in TOOL_CANONICAL_CASING
    for alias, canonical in TOOL_CANONICAL_CASING.items():
        if len(alias) >= 2 and canonical.lower() not in existing_skills_lower:
            pattern = r'(?<![a-zA-Z0-9_#+.-])' + re.escape(alias) + r'(?![a-zA-Z0-9_#+.-])'
            if re.search(pattern, raw_text, re.IGNORECASE):
                twin_profile.extracted_skills.append(
                    SkillEvidence(
                        skill_name=canonical,
                        source="Resume Text Verification",
                        evidence_type="Project",
                        evidence_date="Present"
                    )
                )
                existing_skills_lower.add(canonical.lower())

    # B. Match aliases from BASELINE_CANONICAL_TAXONOMY
    for item in BASELINE_CANONICAL_TAXONOMY:
        for alias in item.get("aliases", []):
            if len(alias) >= 2:
                canonical = TOOL_CANONICAL_CASING.get(alias.lower(), alias.title())
                if canonical.lower() not in existing_skills_lower:
                    pattern = r'(?<![a-zA-Z0-9_#+.-])' + re.escape(alias) + r'(?![a-zA-Z0-9_#+.-])'
                    if re.search(pattern, raw_text, re.IGNORECASE):
                        twin_profile.extracted_skills.append(
                            SkillEvidence(
                                skill_name=canonical,
                                source="Resume Text Verification",
                                evidence_type="Project",
                                evidence_date="Present"
                            )
                        )
                        existing_skills_lower.add(canonical.lower())

    # 5. Normalization against PostgreSQL taxonomies
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
            skill_evidence.skill_name = raw_name
            normalized_skills.append(skill_evidence)

    # 6. Deduplicate repeated skill mentions while keeping most recent evidence dates
    twin_profile.extracted_skills = SkillDeduplicator.deduplicate_skills(normalized_skills)

    # 7. Persist to deterministic SHA-256 cache
    try:
        _PDF_PROFILE_CACHE[pdf_hash] = twin_profile.model_dump_json()
        _save_cache()
        logger.info(f"Persisted resume profile to SHA-256 cache for hash {pdf_hash[:12]}")
    except Exception as save_err:
        logger.warning(f"Could not persist profile to cache: {save_err}")

    logger.info(f"Resume processing complete. Kept {len(twin_profile.extracted_skills)} validated, deduplicated skills.")
    return twin_profile
