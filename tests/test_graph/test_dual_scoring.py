import pytest
from src.domain.schemas import JDExtractionResult, StudentTwinProfile, SkillEvidence
from src.graph.agents.jd_extractor_agent import run_jd_extractor_agent
from src.graph.agents.gap_agent import run_gap_agent
from src.graph.workflow import compile_career_twin_graph

def test_jd_extraction_result_schema():
    data = {
        "core_required_skills": ["Python", "PyTorch", "Docker"],
        "nice_to_have_skills": ["Kubernetes", "AWS"]
    }
    result = JDExtractionResult(**data)
    assert len(result.core_required_skills) == 3
    assert len(result.nice_to_have_skills) == 2

def test_jd_extractor_agent_empty_input():
    state = {
        "target_jd_text": None,
        "errors": []
    }
    output = run_jd_extractor_agent(state)
    assert output["jd_extracted_reqs"] is None
    assert output["jd_fit_score"] is None

def test_gap_agent_dual_scoring():
    profile = StudentTwinProfile(
        student_name="Alex River",
        contact_email="alex.river@example.com",
        education=[],
        experience=[],
        projects=[],
        extracted_skills=[
            SkillEvidence(
                skill_name="Python",
                source="Project A",
                evidence_type="Project",
                evidence_date="2026-06-01"
            ),
            SkillEvidence(
                skill_name="PyTorch",
                source="Thesis",
                evidence_type="Education",
                evidence_date="2026-06-01"
            )
        ]
    )

    market_weights = {
        "Python": 2.0,
        "PyTorch": 2.5,
        "SQL": 1.5,
        "Docker": 1.2
    }

    jd_weights = {
        "PyTorch": 1.0,
        "Docker": 1.0,
        "Kubernetes": 0.5
    }

    state = {
        "student_profile": profile,
        "market_tf_idf_weights": market_weights,
        "jd_extracted_reqs": jd_weights,
        "errors": [],
        "retries": 0
    }

    result = run_gap_agent(state)
    assert "readiness_score" in result
    assert result["readiness_score"] > 0.0
    assert "jd_fit_score" in result
    assert result["jd_fit_score"] is not None
    assert result["jd_fit_score"] > 0.0
    assert "jd_missing_skills" in result
    assert "Docker" in result["jd_missing_skills"]

def test_workflow_graph_compilation(db_session):
    graph = compile_career_twin_graph(db_session)
    assert graph is not None
    assert "JDExtractorAgent" in graph.nodes

