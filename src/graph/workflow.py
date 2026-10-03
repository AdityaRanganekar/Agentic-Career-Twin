from langgraph.graph import StateGraph, END
from src.domain.state import CareerTwinState
from src.graph.agents.profile_agent import run_profile_agent
from src.graph.agents.market_agent import run_market_agent
from src.graph.agents.gap_agent import run_gap_agent
from src.graph.agents.recommendation_agent import run_recommendation_agent
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def run_validator(state: CareerTwinState) -> dict:
    """
    Validates the final state. Increments the retry counter if constraints are violated.
    """
    retries = state.get("retries", 0)
    errors = state.get("errors", [])

    missing_skills = state.get("missing_skills", [])
    recommendations = state.get("recommended_resources", [])
    
    if missing_skills and not recommendations and not errors:
        return {
            "errors": state.get("errors", []) + ["LLM returned empty recommendations despite active skill gaps."], 
            "retries": retries + 1
        }
        
    if errors:
        return {"retries": retries + 1}
        
    return {"retries": retries}

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

    workflow = StateGraph(CareerTwinState)

    workflow.add_node("ProfileAgent", profile_node)
    workflow.add_node("MarketAgent", market_node)
    workflow.add_node("GapAgent", run_gap_agent)
    workflow.add_node("RecommendationAgent", recommendation_node)
    workflow.add_node("Validator", run_validator)

    workflow.set_entry_point("ProfileAgent")
    workflow.add_edge("ProfileAgent", "MarketAgent")
    workflow.add_edge("MarketAgent", "GapAgent")
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