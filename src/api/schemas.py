from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import datetime

class AssessmentCreate(BaseModel):
    student_id: str
    target_role: str
    readiness_score: float
    extracted_skills: List[str]

class AssessmentResponse(BaseModel):
    id: int
    student_id: str
    target_role: str
    readiness_score: float
    extracted_skills: List[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)