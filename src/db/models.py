from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()



class UserProfile(Base):
    """Stores the core user identity for the Agentic Career Twin."""
    __tablename__ = "user_profiles"

    student_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    assessments = relationship("CareerAssessment", back_populates="user")

class CareerAssessment(Base):
    """Tracks individual resume uploads and their deterministic readiness scores."""
    __tablename__ = "career_assessments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("user_profiles.student_id"), nullable=False)
    target_role = Column(String, nullable=False)  
    
    readiness_score = Column(Float, nullable=False)
    extracted_skills = Column(JSON, nullable=False)  
    
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserProfile", back_populates="assessments")


class StudentTwin(Base):
    """The core digital representation of the user's career state."""
    __tablename__ = "student_twins"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, index=True, nullable=False)
    
    current_skills = Column(JSON, default=list)  
    target_roles = Column(JSON, default=list)    
    experience_level = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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