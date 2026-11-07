import pytest
import numpy as np
from src.engine.embedding_engine import EmbeddingEngine, get_embedding_model
from src.graph.agents.gap_agent import run_gap_agent, FULL_CREDIT_THRESHOLD, PARTIAL_CREDIT_THRESHOLD
from src.domain.schemas import StudentTwinProfile, SkillEvidence

def test_singleton_embedding_model():
    model1 = get_embedding_model()
    model2 = get_embedding_model()
    # Verifies singleton behavior: same in-memory object
    assert model1 is model2

def test_acronym_and_short_string_expansion():
    engine = EmbeddingEngine()
    
    # Acronym expansion
    k8s_text = engine.expand_skill_text("k8s")
    assert "kubernetes" in k8s_text.lower()

    # Short string expansion
    r_text = engine.expand_skill_text("R")
    assert "statistical" in r_text.lower() or "programming" in r_text.lower()

def test_semantic_similarity_matrix():
    engine = EmbeddingEngine()
    student_skills = ["PyTorch", "k8s", "Bayesian Inference"]
    market_skills = ["Deep Learning", "Kubernetes", "Machine Learning"]

    matrix = engine.compute_similarity_matrix(student_skills, market_skills)
    assert matrix.shape == (3, 3)

    # PyTorch vs Deep Learning should have strong similarity
    sim_pytorch_dl = matrix[0, 0]
    assert sim_pytorch_dl > 0.60

    # k8s vs Kubernetes should have strong similarity (>0.70)
    sim_k8s_kube = matrix[1, 1]
    assert sim_k8s_kube > 0.70

    # Bayesian Inference vs Machine Learning should yield partial semantic similarity (>0.45)
    sim_bayes_ml = matrix[2, 2]
    assert sim_bayes_ml > 0.45

def test_gap_agent_with_semantic_credit():
    # Scenario: Candidate is a Ph.D. statistician with "Bayesian Inference" and "R", but no "Machine Learning" keyword
    profile = StudentTwinProfile(
        student_name="Sarah Jenkins",
        contact_email="sarah.jenkins@phd.edu",
        education=[],
        experience=[],
        projects=[],
        extracted_skills=[
            SkillEvidence(
                skill_name="Bayesian Inference",
                source="Doctoral Dissertation",
                evidence_type="Project",
                evidence_date="2026-05-01"
            ),
            SkillEvidence(
                skill_name="R",
                source="Statistical Research",
                evidence_type="Experience",
                evidence_date="2026-05-01"
            )
        ]
    )

    market_weights = {
        "Machine Learning": 2.5,
        "Python": 2.0,
        "Deep Learning": 1.8
    }

    state = {
        "student_profile": profile,
        "market_tf_idf_weights": market_weights,
        "errors": [],
        "retries": 0
    }

    result = run_gap_agent(state)
    assert "readiness_score" in result
    assert result["readiness_score"] > 0.0
    # Machine Learning receives partial or full credit from Bayesian Inference
    # Verify that it scored credit
    assert result["readiness_score"] >= 15.0

