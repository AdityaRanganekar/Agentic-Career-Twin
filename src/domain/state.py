from typing import TypedDict, List, Dict, Any, Optional
from src.domain.schemas import StudentTwinProfile

class CareerTwinState(TypedDict):
    """The shared memory structure routed between LangGraph agents."""

    pdf_bytes: bytes
    target_role: str

    student_profile: Optional[StudentTwinProfile]
    normalized_student_skills: List[str]

    market_tf_idf_weights: Dict[str, float]

    missing_skills: List[str]
    readiness_score: float

    recommended_resources: List[Dict[str, Any]]
    retries: int
    errors: List[str]

    # Sprint 7: Dual-Scoring Job Description (JD) Fields
    target_jd_text: Optional[str]
    jd_extracted_reqs: Optional[Dict[str, float]]
    jd_fit_score: Optional[float]
    jd_missing_skills: Optional[List[str]]

    # Radar dimensions
    radar_dimensions: Optional[Dict[str, float]]
    jd_radar_dimensions: Optional[Dict[str, float]]
    jd_benchmark_dimensions: Optional[Dict[str, float]]
    market_corpus_version: Optional[str]
    force_live_refresh: Optional[bool]

    # Project Quality & Evidence Breakdown
    resume_quality_breakdown: Optional[Dict[str, Any]]
    project_quality_score: Optional[float]
    jd_quality_breakdown: Optional[Dict[str, Any]]
    jd_project_quality_score: Optional[float]