from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any

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

    def __init__(
        self,
        student_name: str = "Candidate",
        contact_email: str = "Unknown",
        education: List[Education] = None,
        experience: List[Experience] = None,
        projects: List[Project] = None,
        extracted_skills: List[SkillEvidence] = None,
        **data
    ):
        super().__init__(
            student_name=student_name,
            contact_email=contact_email or "Unknown",
            education=education or [],
            experience=experience or [],
            projects=projects or [],
            extracted_skills=extracted_skills or [],
            **data
        )

    model_config = ConfigDict(extra='allow')

class ResourceMapping(BaseModel):
    gap_skill_name: str = Field(..., description="The exact name of the missing skill.")
    resource_id: int = Field(..., description="The exact database ID of the recommended course.")
    justification: str = Field(..., description="A 1-sentence explanation of why this course closes the gap.")

class RoadmapSynthesis(BaseModel):
    recommendations: List[ResourceMapping] = Field(...)

class JDExtractionResult(BaseModel):
    """Structured extraction schema for target job descriptions."""
    core_required_skills: List[str] = Field(
        default_factory=list,
        description="Essential hard technical skills, tools, frameworks, and methodologies required by the job description. Do NOT include soft skills or HR fluff."
    )
    nice_to_have_skills: List[str] = Field(
        default_factory=list,
        description="Preferred, bonus, or secondary technical skills mentioned. Do NOT include soft skills or HR fluff."
    )

class WeightedSkill(BaseModel):
    skill_name: str = Field(..., description="Canonical single skill or concept name")
    category: str = Field(..., description="Role-specific radar category (one of 5 distinct competency domains for this role)")
    importance_weight: float = Field(..., description="Normalized importance weight between 0.2 and 1.0")
    equivalent_aliases: List[str] = Field(..., description="Equivalent sibling tools, libraries, or acronyms that satisfy this skill")

    def __init__(self, skill_name: str, importance_weight: float, category: str = "General Technical", equivalent_aliases: List[str] = None, **data):
        super().__init__(
            skill_name=skill_name,
            importance_weight=importance_weight,
            category=category,
            equivalent_aliases=equivalent_aliases or [],
            **data
        )

class RoleSkillProfile(BaseModel):
    target_role: str = Field(..., description="The role name analyzed")
    radar_categories: List[str] = Field(..., description="Top 5 distinct competency categories for the radar chart")
    core_skills: List[WeightedSkill] = Field(..., description="Top 12-15 core technical skills required for the role")

    def __init__(self, target_role: str, core_skills: List[WeightedSkill], radar_categories: List[str] = None, **data):
        super().__init__(
            target_role=target_role,
            core_skills=core_skills,
            radar_categories=radar_categories or [],
            **data
        )