from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

# API Schemas for Agentic Career Twin
class SignupRequest(BaseModel):
    name: str
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    identifier: str
    password: str

class GoogleAuthRequest(BaseModel):
    code: Optional[str] = None
    id_token: Optional[str] = None
    redirect_uri: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    google_id: Optional[str] = None

class UserResponse(BaseModel):
    student_id: int
    name: Optional[str] = None
    username: Optional[str] = None
    email: str
    auth_provider: str = "local"

    model_config = ConfigDict(from_attributes=True)

class AnalysisRunResponse(BaseModel):
    id: int
    student_id: int
    target_role: str
    readiness_score: float
    jd_fit_score: Optional[float] = None
    missing_skills: List[str]
    timestamp: datetime
    resume_quality_breakdown: Optional[dict] = None
    project_quality_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class HistoricalRunResponse(BaseModel):
    id: int
    student_id: int
    target_role: str
    readiness_score: float
    jd_fit_score: Optional[float] = None
    project_quality_score: Optional[float] = None
    missing_skills: List[str] = []
    jd_missing_skills: List[str] = []
    recommended_resources: List[Dict[str, Any]] = []
    resume_filename: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
