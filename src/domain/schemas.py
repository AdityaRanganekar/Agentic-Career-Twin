from pydantic import BaseModel, Field
from typing import List, Optional

class SkillEvidence(BaseModel):
    """Tracks individual skills and when they were last used for recency decay."""
    skill_name: str = Field(..., description="The exact name of the skill, tool, or technology.")
    source: str = Field(..., description="Where this skill was found (e.g., 'Experience at Google', 'Project Alpha').")
    evidence_type: str = Field(..., description="Category of evidence: 'Experience', 'Project', 'Education', or 'Certification'.")
    evidence_date: Optional[str] = Field(None, description="ISO format date (YYYY-MM-DD) representing when the skill was most recently used or acquired. Estimate if only month/year is provided.")

class Experience(BaseModel):
    role: str
    company: str
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format. Null if currently employed.")
    description: str

class Project(BaseModel):
    title: str
    description: str
    completion_date: Optional[str] = Field(None, description="Completion date in YYYY-MM-DD format.")

class Education(BaseModel):
    degree: str
    institution: str
    end_date: Optional[str] = Field(None, description="Graduation date in YYYY-MM-DD format.")

class StudentTwinProfile(BaseModel):
    """The root schema passed to Gemini for structured extraction."""
    student_name: str
    contact_email: Optional[str] = None
    education: List[Education] = []
    experience: List[Experience] = []
    projects: List[Project] = []
    extracted_skills: List[SkillEvidence] = []

class ResourceMapping(BaseModel):
    gap_skill_name: str = Field(..., description="The exact name of the missing skill.")
    resource_id: int = Field(..., description="The exact database ID of the recommended course.")
    justification: str = Field(..., description="A 1-sentence explanation of why this course closes the gap.")

class RoadmapSynthesis(BaseModel):
    recommendations: List[ResourceMapping]