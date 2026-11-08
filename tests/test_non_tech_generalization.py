import pytest
from src.domain.schemas import StudentTwinProfile, SkillEvidence, Education, Experience, Project
from src.graph.agents.gap_agent import evaluate_skill_coverage, compute_radar_dimensions
from src.engine.embedding_engine import EmbeddingEngine
from src.engine.competency_clusters import TaxonomyConceptEngine

def test_non_tech_financial_analyst_evaluation():
    """
    Verifies that a non-technical profession (Financial Analyst) is evaluated
    without hardcoding and without injecting unrelated tech keywords (like Python or Docker).
    """
    finance_candidate = StudentTwinProfile(
        student_name="Jordan Hayes",
        contact_email="jordan.hayes@example.com",
        education=[
            Education(
                degree="B.S. Finance & Corporate Accounting",
                institution="Wharton School",
                end_date="2022-05-30"
            )
        ],
        experience=[
            Experience(
                role="Senior Financial Analyst",
                company="Deloitte & Touche",
                end_date="Present",
                description="Built 3-statement financial models, performed DCF valuations, and managed corporate budgeting."
            )
        ],
        projects=[
            Project(
                title="M&A Valuation Model",
                description="Discounted Cash Flow (DCF) model and LBO analysis for $50M mid-market acquisition.",
                completion_date="2024-03-15"
            )
        ],
        extracted_skills=[
            SkillEvidence(skill_name=s, source="Experience", evidence_type="Experience", evidence_date="Present")
            for s in [
                "Financial Modeling", "DCF Valuation", "Excel", "QuickBooks",
                "Financial Statement Analysis", "Budgeting", "Variance Analysis", "LBO Modeling"
            ]
        ]
    )

    financial_analyst_market_reqs = {
        "Financial Modeling & Forecasting": 0.95,
        "Valuation & DCF": 0.90,
        "Financial Statement Analysis": 0.88,
        "Corporate Budgeting": 0.82,
        "Variance & Scenario Analysis": 0.80,
        "ERP & Accounting Systems (SAP / QuickBooks)": 0.78,
        "SEC Regulatory Compliance (GAAP)": 0.75,
        "Cost of Capital & WACC Calculation": 0.70
    }

    embedding_engine = EmbeddingEngine()
    score, gaps = evaluate_skill_coverage(
        student_profile=finance_candidate,
        target_weights=financial_analyst_market_reqs,
        embedding_engine=embedding_engine,
        target_role="Financial Analyst",
        max_skills=10,
        filter_noise=True
    )

    # Assertions
    # 1. Candidate must achieve high domain readiness score (>= 70%)
    assert score >= 70.0, f"Expected Jordan Hayes score >= 70%, got {score}%"

    # 2. Tech stack (Python, Docker, PyTorch) must NOT be injected into gaps or requirements
    all_gaps_text = " ".join(gaps).lower()
    for tech_token in ["python", "docker", "pytorch", "kubernetes", "tensorflow"]:
        assert tech_token not in all_gaps_text, f"Unrelated tech skill '{tech_token}' was injected into non-tech role gaps!"

    # 3. Radar chart dimensions must not contain legacy O*NET software labels
    radar_dims = compute_radar_dimensions(
        target_weights=financial_analyst_market_reqs,
        student_profile=finance_candidate,
        embedding_engine=embedding_engine,
        is_jd=False
    )
    assert len(radar_dims) > 0
    for dim_name in radar_dims.keys():
        assert not dim_name.lower().endswith("software"), f"Legacy O*NET label '{dim_name}' appeared in radar dimensions!"
        assert "user interface and query" not in dim_name.lower()
        assert "application server" not in dim_name.lower()
