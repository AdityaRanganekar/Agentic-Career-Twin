import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class ReadinessResponse(BaseModel):
    student_id: str
    readiness_score: float
    message: str

@router.post("/process-resume", response_model=ReadinessResponse, tags=["Agentic Core"])
async def process_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        logger.error(f"Invalid file type uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    logger.info(f"Received resume: {file.filename}. Orchestration pending.")
    
    return ReadinessResponse(
        student_id="temp_user_01",
        readiness_score=0.0,
        message="Resume processed. LangGraph orchestration pending."
    )