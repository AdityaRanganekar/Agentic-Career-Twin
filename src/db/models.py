from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

Base = declarative_base()

class Student(Base):
    """Stores the persistent identity of a candidate across resume analysis runs."""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    analysis_runs = relationship("AnalysisRun", back_populates="student", cascade="all, delete-orphan")

class AnalysisRun(Base):
    """Tracks historical analysis runs to compute readiness score deltas over time."""
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    target_role = Column(String, nullable=False, index=True)
    target_jd_hash = Column(String, nullable=True, index=True)
    readiness_score = Column(Float, nullable=False)
    jd_fit_score = Column(Float, nullable=True)
    missing_skills = Column(JSON, default=list)
    timestamp = Column(DateTime, default=utc_now, index=True)

    student = relationship("Student", back_populates="analysis_runs")

class StudentTwin(Base):
    """The core digital representation of the user's career state."""
    __tablename__ = "student_twins"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, index=True, nullable=False)
    
    current_skills = Column(JSON, default=list)  
    target_roles = Column(JSON, default=list)    
    experience_level = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class Market(Base):
    """Live job market trends and role requirements gathered by agents."""
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String, index=True, nullable=False)
    
    trending_skills = Column(JSON, default=list) 
    demand_score = Column(Float, nullable=True)  
    
    last_analyzed = Column(DateTime, default=datetime.utcnow)

class Taxonomy(Base):
    """Standardized dictionary mapping unstructured LLM output to clean data."""
    __tablename__ = "taxonomies"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, index=True, nullable=False)
    name = Column(String, unique=True, index=True, nullable=False)

    aliases = Column(JSON, default=list) 

class Resources(Base):
    """Curated learning materials the agent can recommend to close skill gaps."""
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    resource_type = Column(String, nullable=True) 
  
    target_skills = Column(JSON, default=list)
    difficulty_level = Column(String, nullable=True)

# Aliases for specification consistency
LearningResource = Resources
SkillTaxonomy = Taxonomy

class MarketSnapshot(Base):
    """Sprint 8: Snapshot of market demand and cross-role TF-IDF weights."""
    __tablename__ = "market_snapshots"

    snapshot_id = Column(Integer, primary_key=True, index=True)
    target_role = Column(String, nullable=False, index=True)
    market_corpus_version = Column(String, default="2026-Live", index=True)
    tfidf_weights = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=utc_now, index=True)

    jobs = relationship("Job", back_populates="snapshot")

class Job(Base):
    """Sprint 8: Ingested job posting for TF-IDF market calculation and drift tracking."""
    __tablename__ = "jobs"

    job_hash = Column(String, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("market_snapshots.snapshot_id"), nullable=True)
    target_role = Column(String, nullable=False, index=True)
    company = Column(String, nullable=True)
    title = Column(String, nullable=True)
    location = Column(String, nullable=True)
    raw_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now, index=True)

    snapshot = relationship("MarketSnapshot", back_populates="jobs")
    skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")

class JobSkill(Base):
    """Sprint 8: Normalized skills extracted from a job posting."""
    __tablename__ = "job_skills"

    id = Column(Integer, primary_key=True, index=True)
    job_hash = Column(String, ForeignKey("jobs.job_hash"), nullable=False, index=True)
    skill_name = Column(String, nullable=False, index=True)
    required_flag = Column(Boolean, default=True)

    job = relationship("Job", back_populates="skills")
