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

def deterministic_extract_student_twin(raw_text: str) -> StudentTwinProfile:
    """
    Deterministic regex and taxonomy rule-based fallback that parses raw resume text
    directly into a valid StudentTwinProfile in < 50ms without network or LLM dependencies.
    Guarantees the assessment never hangs or crashes when offline or when Gemini is unreachable.
    """
    import re
    from src.domain.schemas import Education, Experience, Project, SkillEvidence
    from src.engine.skill_normalizer import TOOL_CANONICAL_CASING
    from src.engine.competency_clusters import BASELINE_CANONICAL_TAXONOMY

    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    # 1. Candidate Name: First 1-4 word line that is not an email, phone, or section header
    name = "Candidate"
    for l in lines[:8]:
        part = re.split(r'Email:|[|•<:]', l)[0].strip()
        cleaned = re.sub(r'[^a-zA-Z\s.-]', '', part).strip()
        words = cleaned.split()
        if 2 <= len(words) <= 4 and not any(w.lower() in {'resume', 'curriculum', 'vitae', 'profile', 'contact', 'summary', 'experience', 'projects', 'skills', 'education'} for w in words):
            name = ' '.join(words).title()
            break

    # 2. Contact Email: standard email regex
    email_m = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', raw_text)
    contact_email = email_m.group(0).lower() if email_m else "Unknown"

    # 3. Education: search for degree patterns and graduation years
    edu_list = []
    edu_patterns = [
        r'(?:M\.S\.|B\.S\.|B\.Tech|B\.E\.|Master|Bachelor|Ph\.D|PhD)[^,\n]+(?:University|Institute|College|Stanford)?',
        r'(?:Stanford\s+University|University|College|Institute)[^,\n]+(?:M\.S\.|B\.S\.|B\.Tech|B\.E\.|Master|Bachelor)?'
    ]
    for ep in edu_patterns:
        matches = re.findall(ep, raw_text, re.IGNORECASE)
        for m in matches[:2]:
            cleaned_m = m.strip()
            if len(cleaned_m) > 4:
                year_m = re.search(r'\b(20\d\d)\b', cleaned_m)
                year = year_m.group(1) if year_m else "Present"
                edu_list.append(Education(degree=cleaned_m, institution="University", end_date=year))
        if edu_list:
            break
    if not edu_list:
        edu_list.append(Education(degree="Higher Education Degree", institution="University", end_date="Present"))

    # 4. Experience: detect roles, companies, and date spans
    exp_list = []
    exp_matches = re.findall(r'([A-Za-z\s]+(?:Scientist|Engineer|Developer|Analyst|Intern|Manager))[\s,]+([A-Za-z0-9\s]+?)(?:\(([A-Za-z0-9\s-]+)\)|\n)', raw_text)
    for em in exp_matches[:3]:
        role = em[0].strip()
        comp = em[1].strip() or "Company"
        date_str = em[2].strip() if len(em) > 2 and em[2] else "Present"
        if len(role) > 3 and not any(x in role.lower() for x in ['summary', 'skills', 'education', 'certifications']):
            exp_list.append(Experience(role=role, company=comp, end_date=date_str, description=f"{role} at {comp}"))

    # 5. Projects: detect project titles
    proj_list = []
    proj_header_idx = -1
    for h in ["PROJECTS", "ACADEMIC PROJECTS", "PERSONAL PROJECTS"]:
        idx = raw_text.find(h)
        if idx != -1:
            proj_header_idx = idx
            break

    if proj_header_idx != -1:
        proj_text = raw_text[proj_header_idx:proj_header_idx + 1500]
        p_lines = [pl.strip() for pl in proj_text.splitlines() if pl.strip()]
        for pl in p_lines[1:6]:
            if any(term in pl.lower() for term in ["agent", "api", "pipeline", "system", "app", "classifier", "model"]):
                title = pl.split("•")[0].split("  ")[0].strip()
                if 5 <= len(title) <= 60:
                    proj_list.append(Project(title=title, description=pl, completion_date="2024"))

    # 6. Skills extraction against TOOL_CANONICAL_CASING & BASELINE_CANONICAL_TAXONOMY
    skills_map = {}
    for alias, canonical in TOOL_CANONICAL_CASING.items():
        if len(alias) >= 2 and canonical.lower() not in skills_map:
            pattern = r'(?<![a-zA-Z0-9_#+.-])' + re.escape(alias) + r'(?![a-zA-Z0-9_#+.-])'
            if re.search(pattern, raw_text, re.IGNORECASE):
                skills_map[canonical.lower()] = canonical

    for item in BASELINE_CANONICAL_TAXONOMY:
        for alias in item.get("aliases", []):
            if len(alias) >= 2:
                canonical = TOOL_CANONICAL_CASING.get(alias.lower(), alias.title())
                if canonical.lower() not in skills_map:
                    pattern = r'(?<![a-zA-Z0-9_#+.-])' + re.escape(alias) + r'(?![a-zA-Z0-9_#+.-])'
                    if re.search(pattern, raw_text, re.IGNORECASE):
                        skills_map[canonical.lower()] = canonical

    extracted_skills = [
        SkillEvidence(
            skill_name=can,
            source="Resume Verification",
            evidence_type="Project" if proj_list else ("Experience" if exp_list else "Education"),
            evidence_date="Present"
        )
        for can in skills_map.values()
    ]

    return StudentTwinProfile(
        student_name=name,
        contact_email=contact_email,
        education=edu_list,
        experience=exp_list,
        projects=proj_list,
        extracted_skills=extracted_skills
    )

def generate_student_twin(resume_text: str) -> StudentTwinProfile:
    """
    Uses Gemini to parse raw resume text into a structured StudentTwinProfile.
    If Gemini is unreachable, times out, or fails due to network/DNS/quota,
    seamlessly engages the instant deterministic rule-based parser fallback in < 50ms.
    """
    logger.info("Attempting structured extraction with Gemini.")
    try:
        model = get_gemini_client()
        prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=StudentTwinProfile,
                temperature=0.0 
            ),
            request_options={"timeout": 15.0}
        )
   
        twin_data = json.loads(response.text)
        twin_profile = StudentTwinProfile(**twin_data)
        logger.info(f"Successfully extracted {len(twin_profile.extracted_skills)} skills from resume via Gemini.")
        return twin_profile
        
    except Exception as e:
        logger.warning(
            f"Gemini structured extraction unavailable or timed out ({e}). "
            f"Engaging instant deterministic rule-based parser fallback."
        )
        twin_profile = deterministic_extract_student_twin(resume_text)
        logger.info(f"Deterministic parser fallback extracted {len(twin_profile.extracted_skills)} skills for {twin_profile.student_name}.")
        return twin_profile
