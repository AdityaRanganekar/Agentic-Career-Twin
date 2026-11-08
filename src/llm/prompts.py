"""
Centralized, version-controlled prompt templates for Gemini agents across all professions and disciplines.
"""

RESUME_EXTRACTION_PROMPT = """
You are an expert domain recruiter and resume evidence extractor across all professional disciplines (including Software/AI Engineering, Core Engineering, Finance & Accounting, Product Management, UI/UX Design, Healthcare & Clinical Research, Marketing, Operations, and Data Science). 
Analyze the following raw resume text and extract the candidate profile strictly into the requested JSON structure.

Rules for dates: 
For 'evidence_date', 'end_date', or 'completion_date', convert dates to YYYY-MM-DD format. 
Use the last day of the month if only month/year is provided. Leave null or 'Unknown' if ongoing or unmentioned.

Rules for skills:
Extract every hard domain competency, professional methodology, software, tool, framework, instrument, industry standard, and certification mentioned in the text.
Create a separate SkillEvidence entry for each one, linking it back to the specific Project, Role/Experience, Education, or Certification where it was actively demonstrated.
Exclude soft skills, personality traits, and generic buzzwords (e.g., "hardworking", "communication", "team player").

RESUME TEXT:
{resume_text}
"""

JD_EXTRACTION_PROMPT = """
You are an expert recruiter and job requirements parser across all professional domains.
Analyze the following Job Description (JD), Assessment Invitation, or Task Brief and extract the professional requirements.

CRITICAL RULES:
1. Extract ONLY hard professional competencies, tools, software, platforms, methodologies, domain standards, and technical/analytical skills required for the role.
2. STRICTLY EXCLUDE all soft skills, personality traits, and HR boilerplate (e.g., "team player", "strong communication", "collaborative", "fast-paced environment", "critical thinker", "self-starter", "bachelor's degree required").
3. UNIVERSAL EXTRACTION PRINCIPLES:
   - Rule A (Universal Interchangeable Option Consolidation): Whenever a Job Description or assessment document lists multiple interchangeable tools, languages, or platforms as alternatives (e.g., 'choose from C, C++, Java, Python, Go...', 'experience with AWS, GCP, or Azure', 'proficiency in AutoCAD, SolidWorks, or Revit', 'QuickBooks, Xero, or SAP'), NEVER extract all options as separate mandatory skills. Consolidate interchangeable alternatives into a single concept requirement (e.g., 'Core Programming (Python / C++ / Java)', 'Cloud Platforms (AWS / GCP / Azure)', 'CAD Modeling Software (AutoCAD / SolidWorks)').
   - Rule B (Universal Assessment / Task Brief Inference): If the uploaded document is an online assessment invitation, case challenge, or practical task brief (in any field) rather than a traditional job posting, infer the underlying core professional competencies tested by the described exercises and categorize them into core_required_skills and nice_to_have_skills.
   - Rule C (Campus Placement / TPO Notices & Eligible Degree Branches): Many campus placement notices, apprenticeship postings, and college TPO documents list multiple eligible engineering branches or degrees (e.g., 'Total positions: 12 (Mechanical=4 | Electronics & Tele comm.=3 | Electrical=3 | Computer Engineering=2)' or 'Graduation in Engineering (Mechanical / Electrical / Electronics / Chemical / CS / AI & ML)'). A candidate only holds ONE degree! NEVER extract 'Mechanical Engineering', 'Electrical Engineering', and 'Electronics Engineering' as separate required skills when they are listed as eligible degree branches! Instead:
     1. Consolidate multi-branch degree eligibility into a single requirement 'Engineering Degree Eligibility (CS / AI-ML / Core Engineering)'.
     2. Extract the actual functional department, technical, and operational competencies mentioned in the notice (for example, if the department is 'Operations: Production, Logistics & Services, Quality, Process Planning' in an 'agile environment', extract 'Operations & Process Planning', 'Quality Assurance & Control', 'Production & Logistics Systems', and 'Agile Methodologies').
     3. Exclude academic percentage cutoffs ('75% in 10th, 12th, B.Tech', 'First class without backlogs') and HR process logistics.
4. Categorize extracted skills into:
   - core_required_skills: Mandatory, essential, must-have requirements for the role/assessment.
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

