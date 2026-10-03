import json
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.domain.state import CareerTwinState
from src.db.models import Resources
from src.domain.schemas import RoadmapSynthesis
from src.llm.client import get_gemini_client
import google.generativeai as genai
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def run_recommendation_agent(state: CareerTwinState, db: Session) -> dict:
    """
    Fetches real database resources for missing skills and uses Gemini to synthesize the roadmap.
    """
    logger.info("Recommendation Agent invoked.")
    
    missing_skills = state.get("missing_skills", [])
    if not missing_skills:
        return {"recommended_resources": []}
        
    try:
        filters = [Resources.title.ilike(f"%{skill}%") for skill in missing_skills]
        candidate_resources = db.query(Resources).filter(or_(*filters)).limit(20).all()
        
        if not candidate_resources:
            logger.warning("No matching resources found in database.")
            return {"recommended_resources": []}
 
        db_context = "\n".join([
            f"ID: {r.id} | Title: {r.title} | Type: {r.resource_type}" 
            for r in candidate_resources
        ])

        model = get_gemini_client()
        prompt = f"""
        You are a career advisor. The user is missing the following high-priority skills: {', '.join(missing_skills)}.
        
        Below is a list of VERIFIED courses from our database. 
        You must map each missing skill to the most appropriate course from this list.
        NEVER invent a course or an ID. Only use the IDs provided below.
        
        DATABASE COURSES:
        {db_context}
        """
        
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

        final_recommendations = []
        for rec in synthesis.recommendations:
            db_record = next((r for r in candidate_resources if r.id == rec.resource_id), None)
            if db_record:
                final_recommendations.append({
                    "skill": rec.gap_skill_name,
                    "course_title": db_record.title,
                    "url": db_record.url,
                    "justification": rec.justification
                })
                
        return {"recommended_resources": final_recommendations}
        
    except Exception as e:
        logger.error(f"Recommendation Agent failed: {str(e)}")
        return {"errors": state.get("errors", []) + [f"Recommendation failed: {str(e)}"]}