import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.domain.state import CareerTwinState
from src.db.models import Resources
from src.domain.schemas import RoadmapSynthesis
from src.llm.client import get_gemini_client
from src.llm.prompts import ROADMAP_SYNTHESIS_PROMPT
import google.generativeai as genai
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

SKILL_TO_BROAD_KEYWORDS = {
    "keras": ["deep learning", "neural network", "tensorflow", "machine learning"],
    "pytorch": ["deep learning", "neural network", "machine learning", "pytorch"],
    "tensorflow": ["deep learning", "neural network", "tensorflow", "machine learning"],
    "deep learning": ["deep learning", "neural network", "tensorflow", "machine learning"],
    "scipy": ["data science", "python", "machine learning", "applied data"],
    "numpy": ["data science", "python", "machine learning", "applied data"],
    "pandas": ["data science", "python", "data analysis", "applied data"],
    "scikit-learn": ["data science", "machine learning", "python", "applied data"],
    "nosql": ["database", "sql", "data engineering", "big data", "nosql"],
    "mongodb": ["database", "sql", "data engineering", "big data", "nosql"],
    "postgresql": ["database", "sql", "data engineering", "postgresql"],
    "snowflake": ["database", "sql", "data engineering", "data warehouse"],
    "bigquery": ["database", "sql", "data engineering", "data warehouse", "google cloud"],
    "sql": ["database", "sql", "data engineering", "big data"],
    "c++": ["programming", "computer science", "software", "data structures"],
    "c": ["programming", "computer science", "software", "data structures"],
    "scala": ["programming", "computer science", "software", "big data", "spark"],
    "java": ["programming", "computer science", "software", "data structures"],
    "go": ["programming", "computer science", "software", "backend"],
    "aws": ["cloud", "aws", "devops", "data engineering", "mlops"],
    "gcp": ["cloud", "google cloud", "devops", "data engineering"],
    "azure": ["cloud", "azure", "devops", "data engineering"],
    "docker": ["cloud", "docker", "devops", "containers"],
    "kubernetes": ["cloud", "kubernetes", "devops", "containers"],
    "airflow": ["cloud", "airflow", "devops", "data engineering", "workflow"],
    "git": ["devops", "git", "software engineering", "programming"],
    "tableau": ["visualization", "tableau", "analytics", "business intelligence"],
    "powerbi": ["visualization", "power bi", "analytics", "business intelligence"],
    "excel": ["visualization", "excel", "analytics", "data analysis"],
}

def run_recommendation_agent(state: CareerTwinState, db: Session) -> dict:
    """
    Fetches real database resources for missing skills and uses Gemini to synthesize the roadmap
    with deterministic fallback to guarantee grounded recommendations without hallucination.
    """
    logger.info("Recommendation Agent invoked.")
    
    market_gaps = state.get("missing_skills", [])
    jd_gaps = state.get("jd_missing_skills") or []
    missing_skills = list(dict.fromkeys(market_gaps + jd_gaps))
    if not missing_skills:
        return {"recommended_resources": []}
        
    try:
        # Collect search keywords: both exact skill name and broad mapped keywords
        search_terms = set()
        for skill in missing_skills:
            s_clean = skill.strip().lower()
            search_terms.add(skill.strip())
            if s_clean in SKILL_TO_BROAD_KEYWORDS:
                for kw in SKILL_TO_BROAD_KEYWORDS[s_clean]:
                    search_terms.add(kw)
            else:
                for k, kws in SKILL_TO_BROAD_KEYWORDS.items():
                    if k in s_clean or s_clean in k:
                        for kw in kws:
                            search_terms.add(kw)

        filters = [Resources.title.ilike(f"%{term}%") for term in search_terms if term]
        candidate_resources = []
        if filters:
            candidate_resources = db.query(Resources).filter(or_(*filters)).limit(25).all()

        if len(candidate_resources) < 5:
            existing_ids = {r.id for r in candidate_resources}
            fallback_courses = db.query(Resources).limit(15).all()
            for fb in fallback_courses:
                if fb.id not in existing_ids:
                    candidate_resources.append(fb)
                    existing_ids.add(fb.id)

        if not candidate_resources:
            logger.warning("No matching resources found in database.")
            return {"recommended_resources": []}
 
        db_context = "\n".join([
            f"ID: {r.id} | Title: {r.title} | Type: {getattr(r, 'resource_type', 'Course')}" 
            for r in candidate_resources
        ])

        synthesis = None
        try:
            model = get_gemini_client()
            prompt = ROADMAP_SYNTHESIS_PROMPT.format(
                missing_skills=', '.join(missing_skills),
                db_context=db_context
            )
            
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=RoadmapSynthesis,
                    temperature=0.1
                )
            )
            
            synthesis_data = json.loads(response.text)
            synthesis = RoadmapSynthesis(**synthesis_data)
        except Exception as gemini_err:
            logger.warning(f"LLM roadmap synthesis skipped or failed: {str(gemini_err)}")

        final_recommendations = []
        covered_skills = set()
        used_resource_ids = set()

        # 1. Process LLM generated recommendations (strictly database-validated)
        if synthesis and synthesis.recommendations:
            for rec in synthesis.recommendations:
                db_record = next((r for r in candidate_resources if r.id == rec.resource_id), None)
                if db_record:
                    final_recommendations.append({
                        "skill": rec.gap_skill_name,
                        "course_title": db_record.title,
                        "url": db_record.url,
                        "justification": rec.justification,
                        "resource_id": db_record.id
                    })
                    covered_skills.add(rec.gap_skill_name.strip().lower())
                    used_resource_ids.add(db_record.id)

        # 2. Deterministic Gap-to-Course Fallback for any unmapped gap in missing_skills[:5]
        for skill in missing_skills[:5]:
            s_clean = skill.strip().lower()
            if s_clean in covered_skills:
                continue

            matched_course = None
            skill_kws = [s_clean] + SKILL_TO_BROAD_KEYWORDS.get(s_clean, [])
            for cr in candidate_resources:
                c_title = (cr.title or "").lower()
                if any(kw in c_title for kw in skill_kws):
                    matched_course = cr
                    break

            if not matched_course:
                for cr in candidate_resources:
                    if cr.id not in used_resource_ids:
                        matched_course = cr
                        break
                if not matched_course and candidate_resources:
                    matched_course = candidate_resources[0]

            if matched_course:
                final_recommendations.append({
                    "skill": skill,
                    "course_title": matched_course.title,
                    "url": matched_course.url,
                    "justification": f"Covers core foundational concepts required to bridge the {skill} competency gap.",
                    "resource_id": matched_course.id
                })
                covered_skills.add(s_clean)
                used_resource_ids.add(matched_course.id)
                    
        return {"recommended_resources": final_recommendations}
        
    except Exception as e:
        logger.error(f"Recommendation Agent failed: {str(e)}")
        return {"errors": state.get("errors", []) + [f"Recommendation failed: {str(e)}"]}
