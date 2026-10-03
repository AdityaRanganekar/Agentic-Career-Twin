from sqlalchemy.orm import Session
from src.domain.state import CareerTwinState
from src.db.models import Market
from src.engine.readiness_scorer import ReadinessScorer
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def run_market_agent(state: CareerTwinState, db: Session) -> dict:
    """
    Retrieves the global TF-IDF weights for the selected target role.
    """
    target_role = state.get("target_role")
    logger.info(f"Market Agent invoked for role: {target_role}")
    
    try:
        market_data = db.query(Market).filter(Market.role_name == target_role).first()
        
        if not market_data:
            return {"errors": [f"Market data for '{target_role}' not found in database."]}

        target_role_skills = {item["skill"]: item["frequency"] for item in market_data.trending_skills}

        all_markets = db.query(Market).all()
        global_skill_counts = {}
        total_global_jobs = sum(m.demand_score for m in all_markets)
        
        for m in all_markets:
            for item in m.trending_skills:
                skill = item["skill"]
                global_skill_counts[skill] = global_skill_counts.get(skill, 0) + item["frequency"]

        scorer = ReadinessScorer()
        tf_idf_weights = scorer.calculate_tf_idf(
            target_role_skill_counts=target_role_skills,
            target_role_total_jobs=market_data.demand_score,
            global_skill_counts=global_skill_counts,
            total_global_jobs=total_global_jobs
        )
        
        return {"market_tf_idf_weights": tf_idf_weights}
        
    except Exception as e:
        logger.error(f"Market Agent failed: {str(e)}")
        return {"errors": [f"Market analysis failed: {str(e)}"]}