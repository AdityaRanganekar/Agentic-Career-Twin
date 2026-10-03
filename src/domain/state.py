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