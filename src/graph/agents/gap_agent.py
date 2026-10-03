from src.domain.state import CareerTwinState
from src.engine.readiness_scorer import ReadinessScorer
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def run_gap_agent(state: CareerTwinState) -> dict:
    """
    Calculates the Role Readiness Score and identifies top skill gaps based on TF-IDF weight.
    """
    logger.info("Gap Agent invoked.")
    
    try:
        student_profile = state.get("student_profile")
        market_weights = state.get("market_tf_idf_weights", {})
        
        if not student_profile or not market_weights:
            return {"errors": state.get("errors", []) + ["Missing profile or market data for Gap Agent."]}

        student_skills_for_scorer = [
            {
                "name": skill.skill_name,
                "date": skill.evidence_date,
                "strength": 1.0  
            }
            for skill in student_profile.extracted_skills
        ]
        
        scorer = ReadinessScorer()
        readiness_score = scorer.calculate_role_readiness(student_skills_for_scorer, market_weights)
 
        normalized_student_skill_names = set(state.get("normalized_student_skills", []))
        missing_skills = []

        sorted_market_reqs = sorted(market_weights.items(), key=lambda item: item[1], reverse=True)
        
        for skill_name, weight in sorted_market_reqs:
            if skill_name not in normalized_student_skill_names:
                missing_skills.append(skill_name)

        top_gaps = missing_skills[:5]
        logger.info(f"Calculated Score: {readiness_score}%. Identified {len(top_gaps)} critical gaps.")
        
        return {
            "readiness_score": readiness_score,
            "missing_skills": top_gaps
        }
        
    except Exception as e:
        logger.error(f"Gap Agent failed: {str(e)}")
        return {"errors": state.get("errors", []) + [f"Gap analysis failed: {str(e)}"]}