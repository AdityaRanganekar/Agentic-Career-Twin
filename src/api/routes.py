from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.db.database import get_db
from src.db.models import UserProfile, CareerAssessment
from src.api.schemas import AssessmentCreate, AssessmentResponse
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)
router = APIRouter()

@router.post("/assessments/", response_model=AssessmentResponse)
def create_assessment(assessment: AssessmentCreate, db: Session = Depends(get_db)):
    logger.info(f"Received assessment creation request for student: {assessment.student_id}")
    
    user = db.query(UserProfile).filter(UserProfile.student_id == assessment.student_id).first()
    if not user:
        logger.info(f"Creating new user profile for student: {assessment.student_id}")
        user = UserProfile(student_id=assessment.student_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    new_assessment = CareerAssessment(
        student_id=assessment.student_id,
        target_role=assessment.target_role,
        readiness_score=assessment.readiness_score,
        extracted_skills=assessment.extracted_skills
    )
    
    try:
        db.add(new_assessment)
        db.commit()
        db.refresh(new_assessment)
        logger.info(f"Successfully saved assessment {new_assessment.id} to database.")
        return new_assessment
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during assessment creation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save assessment to database")

@router.get("/assessments/{student_id}", response_model=List[AssessmentResponse])
def get_student_assessments(student_id: str, db: Session = Depends(get_db)):
    assessments = db.query(CareerAssessment).filter(CareerAssessment.student_id == student_id).all()
    if not assessments:
        raise HTTPException(status_code=404, detail="No assessments found for this student")
    return assessments