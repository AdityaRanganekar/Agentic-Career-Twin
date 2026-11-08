from langgraph.graph import StateGraph, END
from src.domain.state import CareerTwinState
from src.graph.agents.profile_agent import run_profile_agent
from src.graph.agents.market_agent import run_market_agent
from src.graph.agents.jd_extractor_agent import run_jd_extractor_agent
from src.graph.agents.gap_agent import run_gap_agent
from src.graph.agents.recommendation_agent import run_recommendation_agent
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def run_validator(state: CareerTwinState) -> dict:
    """
    Validates the final state. Increments the retry counter if constraints are violated.
    Clears empty recommendation errors when recommendations are successfully synthesized.
    """
    retries = state.get("retries", 0)
    errors = list(state.get("errors", []))

    missing_skills = state.get("missing_skills", []) or state.get("jd_missing_skills", [])
    recommendations = state.get("recommended_resources", [])
    
    empty_rec_msg = "LLM returned empty recommendations despite active skill gaps."
    if recommendations and empty_rec_msg in errors:
        errors = [e for e in errors if e != empty_rec_msg]
        
    if missing_skills and not recommendations:
        if empty_rec_msg not in errors:
            errors.append(empty_rec_msg)
        return {
            "errors": errors, 
            "retries": retries + 1
        }
        
    if errors:
        return {"errors": errors, "retries": retries + 1}
        
    return {"errors": errors, "retries": retries}

def validation_router(state: CareerTwinState) -> str:
    """
    Routes the execution graph based on validation status. 
    Halts after 3 retries to prevent infinite LLM loops and burning rate limits.
    """
    errors = state.get("errors", [])
    retries = state.get("retries", 0)
    
    if not errors:
        logger.info("Validation passed. Routing to END.")
        return "end"
        
    if retries >= 3:
        logger.warning(f"Max retries (3) reached. Halting with unresolved errors: {errors}")
        return "end"
        
    logger.info(f"Validation failed. Retrying Recommendation Agent (Attempt {retries}/3).")
    return "retry"

def compile_career_twin_graph(db_session):
    """Builds and compiles the LangGraph state machine."""

    def profile_node(state: CareerTwinState):
        return run_profile_agent(state, db_session)
        
    def market_node(state: CareerTwinState):
        return run_market_agent(state, db_session)
        
    def recommendation_node(state: CareerTwinState):
        return run_recommendation_agent(state, db_session)

    def jd_router(state: CareerTwinState) -> str:
        """Routes to JDExtractorAgent only when target_jd_text is provided."""
        target_jd = state.get("target_jd_text")
        if target_jd and str(target_jd).strip():
            return "jd_extractor"
        return "gap_agent"

    def jd_node(state: CareerTwinState):
        return run_jd_extractor_agent(state, db_session)

    def gap_node(state: CareerTwinState):
        return run_gap_agent(state, db_session)

    workflow = StateGraph(CareerTwinState)

    workflow.add_node("ProfileAgent", profile_node)
    workflow.add_node("MarketAgent", market_node)
    workflow.add_node("JDExtractorAgent", jd_node)
    workflow.add_node("GapAgent", gap_node)
    workflow.add_node("RecommendationAgent", recommendation_node)
    workflow.add_node("Validator", run_validator)

    workflow.set_entry_point("ProfileAgent")
    workflow.add_edge("ProfileAgent", "MarketAgent")
    workflow.add_conditional_edges(
        "MarketAgent",
        jd_router,
        {
            "jd_extractor": "JDExtractorAgent",
            "gap_agent": "GapAgent"
        }
    )
    workflow.add_edge("JDExtractorAgent", "GapAgent")
    workflow.add_edge("GapAgent", "RecommendationAgent")
    workflow.add_edge("RecommendationAgent", "Validator")

    workflow.add_conditional_edges(
        "Validator",
        validation_router,
        {
            "retry": "RecommendationAgent", 
            "end": END
        }
    )

    return workflow.compile()