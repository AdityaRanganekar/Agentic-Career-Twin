import os
import json
from sqlalchemy.orm import Session
from src.domain.state import CareerTwinState
from src.db.models import Market, MarketSnapshot
from src.graph.agents.role_research_agent import RoleResearchAgent
from src.engine.readiness_scorer import ReadinessScorer
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def run_market_agent(state: CareerTwinState, db: Session) -> dict:
    """
    Market Agent: Executes the Read-Through Role Cache + TTL architecture.
    1. Checks PostgreSQL for exact or semantic role cache hit within active TTL window (0 tokens).
    2. If missing or expired (or force_live_refresh=True), triggers Live Web Role Discovery,
       persists results to DB, and returns market weights.
    3. Seamlessly falls back to baseline Market table if live network is unreachable.
    """
    target_role = state.get("target_role")
    force_refresh = bool(state.get("force_live_refresh", False))
    logger.info(f"Market Agent invoked for role: '{target_role}' (Force refresh: {force_refresh})")
    
    if not target_role or not str(target_role).strip():
        return {"errors": state.get("errors", []) + ["Target role must be provided to Market Agent."]}

    try:
        # Step 1: Check Database Cache & Semantic Role Lookup + TTL
        cached_result = RoleResearchAgent.find_cached_role_snapshot(
            db=db,
            target_role=target_role,
            force_refresh=force_refresh
        )
        if cached_result:
            weights, version = cached_result
            return {
                "market_tf_idf_weights": weights,
                "market_corpus_version": version
            }

        # Step 2: Live Internet Research & DB Persistence
        try:
            live_weights, live_version = RoleResearchAgent.research_role_live(
                target_role=target_role,
                db=db
            )
            return {
                "market_tf_idf_weights": live_weights,
                "market_corpus_version": live_version
            }
        except Exception as live_err:
            logger.warning(f"Live role research encountered error: {live_err}. Checking baseline fallback...")

        # Step 3: Fallback to baseline Market table if available
        market_data = db.query(Market).filter(Market.role_name == target_role).first()
        if market_data and market_data.trending_skills:
            target_role_skills = {item["skill"]: item["frequency"] for item in market_data.trending_skills}
            all_markets = db.query(Market).all()
            global_skill_counts = {}
            total_global_jobs = sum(m.demand_score for m in all_markets) or 1
            
            for m in all_markets:
                for item in m.trending_skills:
                    skill = item["skill"]
                    global_skill_counts[skill] = global_skill_counts.get(skill, 0) + item["frequency"]

            scorer = ReadinessScorer()
            tf_idf_weights = scorer.calculate_tf_idf(
                target_role_skill_counts=target_role_skills,
                target_role_total_jobs=int(market_data.demand_score or 1),
                global_skill_counts=global_skill_counts,
                total_global_jobs=int(total_global_jobs)
            )
            return {
                "market_tf_idf_weights": tf_idf_weights,
                "market_corpus_version": "2017-Kaggle-Baseline"
            }

        return {"errors": state.get("errors", []) + [f"Market data for '{target_role}' could not be discovered or retrieved."]}
        
    except Exception as e:
        logger.error(f"Market Agent critical failure: {str(e)}")
        return {"errors": state.get("errors", []) + [f"Market Agent failed: {str(e)}"]}
