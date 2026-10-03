import fitz 
import json
import google.generativeai as genai
from src.domain.schemas import StudentTwinProfile
from src.llm.client import get_gemini_client
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts and cleans raw text from a PDF byte stream."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_pages = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_pages.append(page.get_text("text"))
            
        doc.close()

        cleaned_text = "\n".join(text_pages).strip()
        logger.info(f"Successfully extracted {len(cleaned_text)} characters from PDF.")
        
        return cleaned_text
        
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        raise ValueError(f"Unable to process PDF document: {str(e)}")

def generate_student_twin(resume_text: str) -> StudentTwinProfile:
    """Uses Gemini to parse raw resume text into a structured StudentTwinProfile."""
    logger.info("Sending extracted text to Gemini for structured parsing.")
    model = get_gemini_client()
    
    prompt = f"""
    You are an expert technical recruiter and data extractor. 
    Analyze the following raw resume text and extract the information strictly into the requested JSON structure.
    
    Rules for dates: 
    For 'evidence_date', 'end_date', or 'completion_date', convert dates to YYYY-MM-DD format. 
    Use the last day of the month if only month/year is provided. Leave null if ongoing or unmentioned.
    
    Rules for skills:
    Extract every technical skill, programming language, framework, and tool mentioned in the text. 
    Create a separate SkillEvidence entry for each one, linking it back to the specific project or role where it was used.
    
    RESUME TEXT:
    {resume_text}
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=StudentTwinProfile,
                temperature=0.0 
            )
        )
   
        twin_data = json.loads(response.text)
        twin_profile = StudentTwinProfile(**twin_data)
        
        logger.info(f"Successfully extracted {len(twin_profile.extracted_skills)} skills from resume.")
        return twin_profile
        
    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}")
        raise