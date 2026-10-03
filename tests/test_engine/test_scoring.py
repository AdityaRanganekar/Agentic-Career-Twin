import pytest
from src.engine.readiness_scorer import ReadinessScorer

TARGET_ROLE_JOBS = 100
GLOBAL_JOBS = 500

TARGET_ROLE_SKILLS = {
    "Python": 90,     
    "PyTorch": 60    
}

GLOBAL_SKILL_COUNTS = {
    "Python": 450,    
    "PyTorch": 70    
}

STUDENT_PROFILE = [
    {"name": "Python", "date": "2026-08-01", "strength": 1.0},
    {"name": "PyTorch", "date": "2026-08-01", "strength": 1.0}
]

def test_scoring_sensitivity(capsys):
    scorer = ReadinessScorer(config_path="config.yaml")

    tf_idf_weights = scorer.calculate_tf_idf(
        TARGET_ROLE_SKILLS, TARGET_ROLE_JOBS, GLOBAL_SKILL_COUNTS, GLOBAL_JOBS
    )

    raw_freq_weights = {
        skill: (count / TARGET_ROLE_JOBS) for skill, count in TARGET_ROLE_SKILLS.items()
    }
    

    tfidf_score = scorer.calculate_role_readiness(STUDENT_PROFILE, tf_idf_weights)
    raw_score = scorer.calculate_role_readiness(STUDENT_PROFILE, raw_freq_weights)
    
    old_profile = [
        {"name": "Python", "date": "2026-08-01", "strength": 1.0},
        {"name": "PyTorch", "date": "2023-08-01", "strength": 1.0}
    ]
    decayed_score = scorer.calculate_role_readiness(old_profile, tf_idf_weights)

    with capsys.disabled():
        print(f"\n--- SENSITIVITY ANALYSIS & SCORING BASELINES ---")
        print(f"Generic Skill (Python) TF-IDF Weight: {tf_idf_weights['Python']:.4f}")
        print(f"Discriminative Skill (PyTorch) TF-IDF Weight: {tf_idf_weights['PyTorch']:.4f}")
        print(f"-> Notice how TF-IDF correctly assigns higher weight to PyTorch than Python for this specific role.")
        print(f"\nScore using Raw Frequency (Basic ATS): {raw_score}%")
        print(f"Score using Cross-Role TF-IDF:       {tfidf_score}%")
        print(f"Score with 3-Year Evidence Decay:    {decayed_score}%")
        print(f"------------------------------------------------")

    assert tf_idf_weights["PyTorch"] > tf_idf_weights["Python"], "TF-IDF failed to down-weight the generic skill."
    assert tfidf_score > decayed_score, "Recency decay did not lower the score for old evidence."