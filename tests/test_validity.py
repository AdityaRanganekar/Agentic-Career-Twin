import pytest
from scipy.stats import spearmanr
from src.domain.schemas import StudentTwinProfile, SkillEvidence, Education, Experience, Project
from src.graph.agents.gap_agent import evaluate_skill_coverage
from src.engine.embedding_engine import EmbeddingEngine

def test_spearman_correlation(capsys):
    """
    Evaluates the human validity of the algorithmic Role Readiness Score
    against human expert rankings across 10 benchmark candidates.
    Executes real dynamic scoring via evaluate_skill_coverage() with zero hardcoding.
    """
    # 1. Define the 10 real benchmark candidate profiles (10.pdf down to 1.pdf)
    cand_10 = StudentTwinProfile(
        student_name="Alex Mercer",
        contact_email="alex.mercer@gmail.com",
        education=[Education(degree="M.S. Computer Science", institution="Stanford University", end_date="2018-06-01")],
        experience=[
            Experience(role="Senior Data Scientist / Machine Learning Engineer", company="TechCorp", end_date="Present", description="Leading production ML pipelines and neural network models"),
            Experience(role="Machine Learning Engineer", company="StartupAI", end_date="2022-12-31", description="Building end-to-end ML workflows and deep learning models")
        ],
        projects=[Project(title="Deep Learning Framework", description="PyTorch and TensorFlow distributed training", completion_date="2023-01-01")],
        extracted_skills=[
            SkillEvidence(skill_name=s, source="Experience", evidence_type="Experience", evidence_date="Present")
            for s in ["Python", "SQL", "PyTorch", "TensorFlow", "Scikit-Learn", "AWS", "Docker", "Apache Airflow", "XGBoost", "Machine Learning", "Deep Learning", "NLP", "pandas", "NumPy", "Linux", "Data Visualization"]
        ]
    )

    cand_9 = StudentTwinProfile(
        student_name="Priya Sharma",
        contact_email="priya.sharma@gmail.com",
        education=[Education(degree="M.S. Artificial Intelligence", institution="Carnegie Mellon University", end_date="2020-05-15")],
        experience=[
            Experience(role="Lead Machine Learning Engineer", company="AI Solutions", end_date="Present", description="LLM orchestrations, fine-tuning, and production NLP"),
            Experience(role="ML Engineer", company="DataFlow", end_date="2024-01-01", description="Transformer architecture and FastAPI deployment")
        ],
        projects=[Project(title="LLM Orchestrator", description="LangChain and HuggingFace pipelines", completion_date="2024-06-01")],
        extracted_skills=[
            SkillEvidence(skill_name=s, source="Experience", evidence_type="Experience", evidence_date="Present")
            for s in ["Python", "PyTorch", "NLP", "LLMs", "LangChain", "HuggingFace", "FastAPI", "Docker", "Git", "spaCy", "Transformers", "Machine Learning", "pandas", "NumPy", "Linux", "Deep Learning"]
        ]
    )

    cand_8 = StudentTwinProfile(
        student_name="David Chen",
        contact_email="david.chen@gmail.com",
        education=[Education(degree="B.S. Data Science & Statistics", institution="UC Berkeley", end_date="2020-05-01")],
        experience=[
            Experience(role="Mid-level Data Scientist", company="FinTech Global", end_date="Present", description="Predictive modeling, regression analysis, and A/B testing"),
            Experience(role="Data Analyst", company="Retail Analytics", end_date="2023-06-01", description="SQL queries, Pandas analysis, and Tableau dashboards")
        ],
        projects=[],
        extracted_skills=[
            SkillEvidence(skill_name=s, source="Experience", evidence_type="Experience", evidence_date="Present")
            for s in ["Python", "SQL", "Scikit-Learn", "Pandas", "Snowflake", "Tableau", "Statistics", "A/B Testing", "Machine Learning", "NumPy", "Data Visualization"]
        ]
    )

    cand_7 = StudentTwinProfile(
        student_name="Sarah Jenkins",
        contact_email="sarah.jenkins@gmail.com",
        education=[Education(degree="Ph.D. Statistics & Quantitative Methods", institution="Columbia University", end_date="2017-05-01")],
        experience=[
            Experience(role="Principal Quantitative Researcher", company="Capital Fund Management", end_date="Present", description="Statistical modeling, Bayesian inference, time-series forecasting, and stochastic processes")
        ],
        projects=[],
        extracted_skills=[
            SkillEvidence(skill_name=s, source="Experience", evidence_type="Experience", evidence_date="Present")
            for s in ["R", "SAS", "Statistical Modeling", "A/B Testing", "Bayesian Inference", "Time-Series Analysis", "SQL", "MATLAB", "Statistics", "Mathematics"]
        ]
    )

    cand_6 = StudentTwinProfile(
        student_name="Marcus Cole",
        contact_email="marcus.cole@gmail.com",
        education=[Education(degree="B.S. Economics & Business Analytics", institution="NYU Stern", end_date="2021-05-01")],
        experience=[
            Experience(role="Senior Data Analyst", company="Omni Media", end_date="Present", description="BI dashboards, SQL reporting, BigQuery analysis, and regression modeling")
        ],
        projects=[],
        extracted_skills=[
            SkillEvidence(skill_name=s, source="Experience", evidence_type="Experience", evidence_date="Present")
            for s in ["SQL", "PowerBI", "Excel", "BigQuery", "Python", "Pandas", "Linear Regression", "Data Visualization", "Reporting", "Tableau", "Statistics"]
        ]
    )

    cand_5 = StudentTwinProfile(
        student_name="Elena Rodriguez",
        contact_email="elena.rodriguez@gmail.com",
        education=[Education(degree="B.S. Computer Science", institution="University of Michigan", end_date="2025-05-01")],
        experience=[
            Experience(role="Machine Learning Intern", company="HealthTech", end_date="2025-08-30", description="NLP text classification and random forest models")
        ],
        projects=[Project(title="ML Classification Capstone", description="Scikit-Learn and Pandas ML pipeline", completion_date="2025-12-01")],
        extracted_skills=[
            SkillEvidence(skill_name=s, source="Experience", evidence_type="Experience", evidence_date="2025-08-30")
            for s in ["Python", "Java", "SQL", "Scikit-Learn", "Pandas", "Git", "NLP", "Random Forests", "Data Structures", "Algorithms", "C++"]
        ]
    )

    cand_4 = StudentTwinProfile(
        student_name="James Wilson",
        contact_email="james.wilson@gmail.com",
        education=[Education(degree="B.S. Software Engineering", institution="Purdue University", end_date="2019-05-01")],
        experience=[
            Experience(role="Senior Backend Engineer", company="CloudScale Systems", end_date="Present", description="Microservices in Go, Python Django, PostgreSQL, Docker, AWS, Terraform")
        ],
        projects=[],
        extracted_skills=[
            SkillEvidence(skill_name=s, source="Experience", evidence_type="Experience", evidence_date="Present")
            for s in ["Python", "Django", "Go", "AWS", "Docker", "Kubernetes", "PostgreSQL", "Terraform", "CI/CD", "Microservices", "SQL", "Git", "Linux"]
        ]
    )

    cand_3 = StudentTwinProfile(
        student_name="Chloe Bennett",
        contact_email="chloe.bennett@gmail.com",
        education=[Education(degree="12-Week Data Science Bootcamp Certificate", institution="General Assembly", end_date="2025-11-15")],
        experience=[],
        projects=[Project(title="Bootcamp Capstone Project", description="Logistic regression on customer churn", completion_date="2025-11-15")],
        extracted_skills=[
            SkillEvidence(skill_name=s, source="Project", evidence_type="Project", evidence_date="2025-11-15")
            for s in ["Python", "SQL", "Jupyter", "Scikit-Learn", "Pandas", "Logistic Regression", "Machine Learning"]
        ]
    )

    cand_2 = StudentTwinProfile(
        student_name="Robert Fox",
        contact_email="robert.fox@gmail.com",
        education=[Education(degree="A.S. Information Technology", institution="Community College", end_date="2010-05-01")],
        experience=[
            Experience(role="Network Systems Administrator", company="Enterprise IT", end_date="Present", description="Cisco switch configuration, Windows server administration, basic Python script automation")
        ],
        projects=[],
        extracted_skills=[
            SkillEvidence(skill_name=s, source="Experience", evidence_type="Experience", evidence_date="Present")
            for s in ["Networking", "Cisco", "IT Support", "Hardware", "Troubleshooting", "Windows Server", "Python"]
        ]
    )

    cand_1 = StudentTwinProfile(
        student_name="Maria Garcia",
        contact_email="maria.garcia@gmail.com",
        education=[Education(degree="B.A. Hospitality Management", institution="State University", end_date="2015-05-01")],
        experience=[
            Experience(role="Retail Store Manager", company="Fashion Retail", end_date="Present", description="Staff scheduling, team leadership, customer service, sales management")
        ],
        projects=[],
        extracted_skills=[
            SkillEvidence(skill_name=s, source="Experience", evidence_type="Experience", evidence_date="Present")
            for s in ["Leadership", "Customer Service", "Scheduling", "Inventory Management", "Sales", "Team Building", "Communication"]
        ]
    )

    candidates = [cand_10, cand_9, cand_8, cand_7, cand_6, cand_5, cand_4, cand_3, cand_2, cand_1]
    human_rankings = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

    # 2. Real Kaggle Data Scientist Cross-Role TF-IDF Market Weights
    data_scientist_market_weights = {
        'Python': 0.9022,
        'R': 0.8304,
        'C': 0.3630,
        'C++': 0.3617,
        'SAS': 0.3440,
        'TensorFlow': 0.3376,
        'Tableau': 0.3031,
        'Scala': 0.2533,
        'Scikit-learn': 0.2279,
        'pandas': 0.2238,
        'NumPy': 0.2174,
        'Linux': 0.2051,
        'PyTorch': 0.1999,
        'SQL': 0.1950,
        'Machine Learning': 0.1850
    }

    # 3. Dynamic Execution through the Real Scoring Engine (Zero Hardcoded Scores!)
    embedding_engine = EmbeddingEngine()
    computed_scores = []

    with capsys.disabled():
        print("\n" + "=" * 65)
        print("--- DYNAMIC HUMAN VALIDITY STUDY (SPEARMAN RANK CORRELATION) ---")
        print("Target Role: Data Scientist")
        print("Candidate Computed Scores:")

    for idx, cand in enumerate(candidates):
        score, gaps = evaluate_skill_coverage(
            student_profile=cand,
            target_weights=data_scientist_market_weights,
            embedding_engine=embedding_engine,
            max_skills=15,
            filter_noise=True
        )
        computed_scores.append(score)
        with capsys.disabled():
            rank_label = 10 - idx
            print(f"  [Rank {rank_label:2d}] {cand.student_name:<18}: {score:5.2f}% (Gaps: {gaps[:2]})")

    # 4. Compute Spearman Rank Correlation
    corr, p_value = spearmanr(human_rankings, computed_scores)

    with capsys.disabled():
        print("-" * 65)
        print(f"Spearman Rank Correlation: {corr:.4f} (p-value = {p_value:.4e})")
        print("=" * 65 + "\n")

    # 5. Core Assertions
    # Assertion A: Alex Mercer (Cand 10) must score > 85%
    assert computed_scores[0] > 85.0, f"Alex Mercer score ({computed_scores[0]:.2f}%) did not exceed 85.0%"

    # Assertion B: Sarah Jenkins (Cand 7) must score higher than Chloe Bennett (Cand 3)
    sarah_score = computed_scores[3]
    chloe_score = computed_scores[7]
    assert sarah_score > chloe_score, f"Sarah Jenkins ({sarah_score:.2f}%) must score higher than Chloe Bennett ({chloe_score:.2f}%)"

    # Assertion C: Spearman correlation must be >= 0.90 with p < 0.001
    assert corr >= 0.90, f"Spearman correlation ({corr:.4f}) fell below the 0.90 required threshold."
    assert p_value < 0.001, f"Correlation p-value ({p_value:.4e}) is not statistically significant at p < 0.001."
