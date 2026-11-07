from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# API Schemas for Agentic Career Twin
class AnalysisRunResponse(BaseModel):
    id: int
    student_id: int
    target_role: str
    readiness_score: float
    jd_fit_score: Optional[float] = None
    missing_skills: List[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
