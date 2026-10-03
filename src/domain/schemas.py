from pydantic import BaseModel, Field
from typing import List

class SkillEvidence(BaseModel):
    """Tracks individual skills and when they were last used for recency decay."""
    skill_name: str = Field(..., description="The EXACT single name of the skill (e.g., 'Pandas'). You MUST break apart space-separated or pipe-separated lists into individual skill records.")
    source: str = Field(..., description="Where this skill was found (e.g., 'Experience at Google', 'Project Alpha').")
    evidence_type: str = Field(..., description="Category of evidence: 'Experience', 'Project', 'Education', or 'Certification'.")
    evidence_date: str = Field(..., description="ISO format date (YYYY-MM-DD). If missing or unknown, return 'Unknown'.")

class Experience(BaseModel):
    role: str = Field(...)
    company: str = Field(...)
    end_date: str = Field(..., description="End date in YYYY-MM-DD format. Return 'Present' if currently employed.")
    description: str = Field(...)

class Project(BaseModel):
    title: str = Field(...)
    description: str = Field(...)
    completion_date: str = Field(..., description="Completion date in YYYY-MM-DD format. Return 'Unknown' if missing.")

class Education(BaseModel):
    degree: str = Field(...)
    institution: str = Field(...)
    end_date: str = Field(..., description="Graduation date in YYYY-MM-DD format. Return 'Unknown' if missing.")

class StudentTwinProfile(BaseModel):
    """The root schema passed to Gemini for structured extraction."""
    student_name: str = Field(...)
    contact_email: str = Field(..., description="Contact email. Return 'Unknown' if missing.")
    education: List[Education] = Field(..., description="Must be a list. Return an empty list [] if no education is found.")
    experience: List[Experience] = Field(..., description="Must be a list. Return an empty list [] if no formal work experience is found (e.g., student resumes).")
    projects: List[Project] = Field(..., description="Must be a list. Return an empty list [] if no projects are found.")
    extracted_skills: List[SkillEvidence] = Field(..., description="Must be a list. Return an empty list [] if none.")

class ResourceMapping(BaseModel):
    gap_skill_name: str = Field(..., description="The exact name of the missing skill.")
    resource_id: int = Field(..., description="The exact database ID of the recommended course.")
    justification: str = Field(..., description="A 1-sentence explanation of why this course closes the gap.")

class RoadmapSynthesis(BaseModel):
    recommendations: List[ResourceMapping] = Field(...)