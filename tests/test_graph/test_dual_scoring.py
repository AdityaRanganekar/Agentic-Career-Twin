import pytest
from src.domain.schemas import JDExtractionResult, StudentTwinProfile, SkillEvidence
from src.graph.agents.jd_extractor_agent import run_jd_extractor_agent
from src.graph.agents.gap_agent import run_gap_agent
from src.graph.workflow import compile_career_twin_graph, profile_router, market_router

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
    assert result["readiness_score"] is not None
    assert result["readiness_score"] > 0.0
    assert "jd_fit_score" in result
    assert result["jd_fit_score"] is not None
    assert result["jd_fit_score"] > 0.0
    assert "jd_missing_skills" in result
    assert "Docker" in result["jd_missing_skills"]

def test_gap_agent_discipline_only():
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
            )
        ]
    )

    state = {
        "student_profile": profile,
        "market_tf_idf_weights": {"Python": 2.0, "SQL": 1.5},
        "jd_extracted_reqs": None,
        "errors": [],
        "retries": 0
    }

    result = run_gap_agent(state)
    assert result["readiness_score"] is not None
    assert result["readiness_score"] > 0.0
    assert result["missing_skills"] is not None
    assert result["jd_fit_score"] is None
    assert result["jd_missing_skills"] is None
    assert result["jd_radar_dimensions"] is None

def test_gap_agent_jd_only():
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
            )
        ]
    )

    state = {
        "student_profile": profile,
        "market_tf_idf_weights": None,
        "jd_extracted_reqs": {"Python": 1.0, "Kubernetes": 1.0},
        "errors": [],
        "retries": 0
    }

    result = run_gap_agent(state)
    assert result["readiness_score"] is None
    assert result["missing_skills"] is None
    assert result["radar_dimensions"] is None
    assert result["jd_fit_score"] is not None
    assert result["jd_fit_score"] > 0.0
    assert result["jd_missing_skills"] is not None
    assert "Kubernetes" in result["jd_missing_skills"]

def test_workflow_conditional_routers():
    # 1. Target Discipline Mode (Discipline selected, no JD text)
    state_discipline = {
        "target_role": "Machine Learning Engineer",
        "target_jd_text": None
    }
    assert profile_router(state_discipline) == "market_agent"
    assert market_router(state_discipline) == "gap_agent"

    # 2. Target Job Posting Mode (No target role, JD text provided)
    state_jd = {
        "target_role": "",
        "target_jd_text": "We are looking for an SDE with Python and Docker experience."
    }
    assert profile_router(state_jd) == "jd_extractor"

    # 3. Both provided (Dual Mode)
    state_dual = {
        "target_role": "Backend Engineer",
        "target_jd_text": "Requirements: Go, Kubernetes, PostgreSQL"
    }
    assert profile_router(state_dual) == "market_agent"
    assert market_router(state_dual) == "jd_extractor"

    # 4. Neither provided
    state_empty = {
        "target_role": "",
        "target_jd_text": ""
    }
    assert profile_router(state_empty) == "gap_agent"

def test_workflow_graph_compilation(db_session):
    graph = compile_career_twin_graph(db_session)
    assert graph is not None
    assert "JDExtractorAgent" in graph.nodes


