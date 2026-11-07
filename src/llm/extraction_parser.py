import fitz 
import json
import io
import zipfile
import xml.etree.ElementTree as ET
import google.generativeai as genai
from src.domain.schemas import StudentTwinProfile
from src.llm.client import get_gemini_client
from src.llm.prompts import RESUME_EXTRACTION_PROMPT
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

def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    """
    Extracts raw text from uploaded files supporting .pdf, .docx, .txt, and .md formats.
    """
    if not file_bytes:
        return ""
        
    lower_name = (filename or "").lower()
    
    # 1. PDF Documents
    if lower_name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
        
    # 2. DOCX Documents
    elif lower_name.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs if p.text]).strip()
        except ImportError:
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
                    xml_content = docx_zip.read('word/document.xml')
                    tree = ET.fromstring(xml_content)
                    namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    paragraphs = []
                    for p in tree.iterfind('.//w:p', namespaces):
                        texts = [node.text for node in p.iterfind('.//w:t', namespaces) if node.text]
                        if texts:
                            paragraphs.append(''.join(texts))
                    return '\n'.join(paragraphs).strip()
            except Exception as e:
                logger.error(f"Failed extracting text from DOCX archive: {e}")
                raise ValueError(f"Unable to parse DOCX document: {str(e)}")
                
    # 3. Plain Text / Markdown Documents
    else:
        try:
            return file_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="ignore").strip()

def generate_student_twin(resume_text: str) -> StudentTwinProfile:
    """Uses Gemini to parse raw resume text into a structured StudentTwinProfile."""
    logger.info("Sending extracted text to Gemini for structured parsing.")
    model = get_gemini_client()
    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)
    
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
