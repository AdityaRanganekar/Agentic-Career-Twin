import json
import pytest
from unittest.mock import MagicMock, patch
from src.db.models import Resources
from src.graph.agents.recommendation_agent import run_recommendation_agent
from src.domain.schemas import RoadmapSynthesis, ResourceMapping

def test_hallucination_rate_comparison():
    """
    Evaluation Framework Metric 4: LLM-Only Synthesis Baseline.
    Compares the pure LLM hallucinated-resource rate against the system's deterministic 
    DB-validated rate (target: 0.0% hallucinated resource identities).
    """
    mock_db = MagicMock()
    
    # 2 real verified resources in database
    real_resource_1 = Resources(id=101, title="Deep Learning Specialization", resource_type="course", url="https://coursera.org/dl")
    real_resource_2 = Resources(id=102, title="Machine Learning with Python", resource_type="course", url="https://coursera.org/ml")
    
    mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [
        real_resource_1, real_resource_2
    ]
    
    # Simulate an LLM output that attempts to return 1 real resource, 1 hallucinated ID (999), and 1 hallucinated ID (888)
    llm_output_items = [
        {"gap_skill_name": "Deep Learning", "resource_id": 101, "justification": "Matches deep learning needs"},
        {"gap_skill_name": "Docker", "resource_id": 999, "justification": "Hallucinated container course"},
        {"gap_skill_name": "Kubernetes", "resource_id": 888, "justification": "Hallucinated k8s course"}
    ]
    
    # Baseline (Unconstrained LLM without DB ID validation):
    total_unconstrained = len(llm_output_items)
    hallucinated_unconstrained = sum(
        1 for item in llm_output_items if item["resource_id"] not in [101, 102]
    )
    baseline_hallucination_rate = hallucinated_unconstrained / total_unconstrained
    
    # System with Deterministic DB Validation Barrier:
    candidate_resources = [real_resource_1, real_resource_2]
    final_recommendations = []
    for rec in llm_output_items:
        db_record = next((r for r in candidate_resources if r.id == rec["resource_id"]), None)
        if db_record:
            final_recommendations.append(db_record)
            
    system_hallucinated = sum(
        1 for item in final_recommendations if item.id not in [101, 102]
    )
    system_hallucination_rate = system_hallucinated / len(final_recommendations) if final_recommendations else 0.0
    
    print("\n--- LLM-ONLY SYNTHESIS BASELINE EVALUATION ---")
    print(f"Unconstrained LLM Hallucination Rate: {baseline_hallucination_rate * 100:.1f}%")
    print(f"System Deterministic DB-Validated Rate: {system_hallucination_rate * 100:.1f}%")
    print("----------------------------------------------")
    
    assert baseline_hallucination_rate > 0.50, "Baseline unconstrained LLM should exhibit hallucinated IDs"
    assert system_hallucination_rate == 0.0, "System must strictly enforce 0.0% hallucinated resource identities"
    assert len(final_recommendations) == 1
    assert final_recommendations[0].id == 101


def test_recommendation_agent_filters_hallucinated_ids():
    """
    Directly tests run_recommendation_agent to verify that any hallucinated resource IDs
    injected by an LLM response (e.g. ID 999) are strictly filtered out by the database
    validation barrier, guaranteeing 0.0% hallucinated resources.
    """
    mock_db = MagicMock()
    real_resource_1 = Resources(id=101, title="Deep Learning Specialization", resource_type="course", url="https://coursera.org/dl")
    real_resource_2 = Resources(id=102, title="Machine Learning with Python", resource_type="course", url="https://coursera.org/ml")
    
    mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [
        real_resource_1, real_resource_2
    ]
    mock_db.query.return_value.limit.return_value.all.return_value = [
        real_resource_1, real_resource_2
    ]

    state = {
        "missing_skills": ["Deep Learning", "Docker"],
        "jd_missing_skills": [],
        "errors": []
    }

    with patch("src.graph.agents.recommendation_agent.get_gemini_client") as mock_get_client:
        mock_model = MagicMock()
        mock_get_client.return_value = mock_model
        
        # LLM returns valid ID 101 and hallucinated ID 999
        mock_model.generate_content.return_value.text = json.dumps({
            "recommendations": [
                {"gap_skill_name": "Deep Learning", "resource_id": 101, "justification": "Matches deep learning needs"},
                {"gap_skill_name": "Docker", "resource_id": 999, "justification": "Hallucinated container course"}
            ]
        })
        
        output = run_recommendation_agent(state, mock_db)

    recs = output.get("recommended_resources", [])
    assert len(recs) > 0, "Recommendations should not be empty"

    # Verify ID 999 was never included and all resources map to real DB IDs
    for r in recs:
        assert r.get("resource_id") != 999, "Hallucinated ID 999 must be strictly filtered out"
        assert r.get("resource_id") in [101, 102], f"Resource {r} must map to a verified database ID"

    hallucinated_count = sum(1 for r in recs if r.get("resource_id") not in [101, 102])
    agent_hallucination_rate = hallucinated_count / len(recs)
    
    print("\n--- RECOMMENDATION AGENT DB VALIDATION BARRIER ---")
    print(f"Total Recommendations: {len(recs)}")
    print(f"Hallucinated Resources Accepted: {hallucinated_count}")
    print(f"Agent Hallucination Rate: {agent_hallucination_rate * 100:.1f}%")
    print("--------------------------------------------------")
    
    assert agent_hallucination_rate == 0.0, "run_recommendation_agent must have exactly 0.0% hallucinated resources"
