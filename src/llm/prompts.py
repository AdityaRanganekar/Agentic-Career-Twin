"""
Centralized, version-controlled prompt templates for Gemini agents.
"""

RESUME_EXTRACTION_PROMPT = """
You are an expert technical recruiter and data extractor. 
Analyze the following raw resume text and extract the information strictly into the requested JSON structure.

Rules for dates: 
For 'evidence_date', 'end_date', or 'completion_date', convert dates to YYYY-MM-DD format. 
Use the last day of the month if only month/year is provided. Leave null or 'Unknown' if ongoing or unmentioned.

Rules for skills:
Extract every technical skill, programming language, framework, and tool mentioned in the text. 
Create a separate SkillEvidence entry for each one, linking it back to the specific project or role where it was used.

RESUME TEXT:
{resume_text}
"""

JD_EXTRACTION_PROMPT = """
You are an expert technical recruiter and job requirements parser.
Analyze the following Job Description (JD) and extract the technical requirements.

CRITICAL RULES:
1. Extract ONLY hard technical skills, programming languages, frameworks, developer tools, cloud infrastructure, databases, and mathematical/statistical methodologies.
2. STRICTLY EXCLUDE all soft skills, personality traits, and HR boilerplate (e.g., "team player", "communication", "collaborative", "fast-paced environment", "critical thinker", "self-starter", "bachelor's degree").
3. Categorize extracted skills into:
   - core_required_skills: Mandatory, essential, must-have requirements.
   - nice_to_have_skills: Preferred, bonus, optional, or plus qualifications.

JOB DESCRIPTION:
{jd_text}
"""

ROADMAP_SYNTHESIS_PROMPT = """
You are a career advisor. The user is missing the following high-priority skills: {missing_skills}.

Below is a list of VERIFIED courses from our database. 
You must map each missing skill to the most appropriate course from this list.
NEVER invent a course or an ID. Only use the IDs provided below.

DATABASE COURSES:
{db_context}
"""

