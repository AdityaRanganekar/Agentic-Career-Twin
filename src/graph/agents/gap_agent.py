import re
from src.domain.state import CareerTwinState
from src.engine.readiness_scorer import ReadinessScorer
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

NOISE_WORDS = {
    "analyze", "develop", "manage", "coordinate", "design", "plan", 
    "support", "create", "maintain", "implement", "evaluate", "build", 
    "test", "research", "communicate", "lead", "assist", "troubleshoot",
    "analytical", "analysis", "programming languages", "programming", 
    "reduce", "software", "systems", "applications", "google"
}

EQUIVALENCY_CLUSTERS = [
    # 1. Core Data Science, Analysis & Systems Languages
    {"python", "r", "sas", "julia", "c++", "c", "java", "scala", "matlab", "go", "golang", "rust"},
    
    # 2. Data Manipulation, Ecosystem & Big Data
    {"pandas", "numpy", "polars", "dask", "pyspark", "spark", "apache spark", "hadoop", "sql", "pysqldf"},
    
    # 3. Traditional Machine Learning & Statistical Modeling
    {"scikit-learn", "sklearn", "xgboost", "lightgbm", "catboost", "statsmodels", "machine learning", "predictive modeling"},
    
    # 4. Deep Learning, AI & Advanced NLP
    {"pytorch", "tensorflow", "keras", "jax", "hugging face", "transformers", "deep learning", "nlp", "llms", "neural networks", "genai"},
    
    # 5. Business Intelligence, Dashboarding & Visualization
    {"tableau", "powerbi", "power bi", "looker", "quicksight", "matplotlib", "seaborn", "plotly", "streamlit", "dash"},
    
    # 6. Cloud Infrastructure & Ecosystems
    {"aws", "amazon web services", "gcp", "google cloud", "google cloud platform", "google", "azure", "microsoft azure", "cloud computing", "cloud infrastructure"},
    
    # 7. MLOps, Pipeline Orchestration & CI/CD
    {"mlflow", "kubeflow", "weights & biases", "wandb", "dvc", "apache airflow", "airflow", "prefect", "dagster", "github actions", "ci/cd", "jenkins", "model tracking", "mlops"},
    
    # 8. Containerization, OS & DevOps
    {"docker", "kubernetes", "k8s", "containerization", "terraform", "ansible", "linux", "unix", "bash", "shell scripting"},
    
    # 9. Backend Engineering & APIs
    {"fastapi", "flask", "django", "node.js", "express", "rest", "restful apis", "graphql", "microservices"},
    
    # 10. Databases & Data Warehousing
    {"postgresql", "mysql", "mongodb", "redis", "cassandra", "snowflake", "bigquery", "amazon redshift", "elasticsearch", "databases", "nosql"},
    
    # 11. Version Control & Collaboration
    {"git", "github", "gitlab", "bitbucket", "version control"}
]

def run_gap_agent(state: CareerTwinState) -> dict:
    logger.info("Gap Agent invoked.")
    
    try:
        student_profile = state.get("student_profile")
        raw_market_weights = state.get("market_tf_idf_weights", {})
        
        if not student_profile or not raw_market_weights:
            return {"errors": state.get("errors", []) + ["Missing data for Gap Agent."]}

        clean_market_weights = {
            skill: weight for skill, weight in raw_market_weights.items() 
            if skill.lower() not in NOISE_WORDS
        }

        top_market_reqs = dict(
            sorted(clean_market_weights.items(), key=lambda item: item[1], reverse=True)[:15]
        )

        normalized_student_skill_names = {
            skill.skill_name.lower() for skill in student_profile.extracted_skills
        }

        student_tokens = set()
        for s in normalized_student_skill_names:
            tokens = re.split(r'[\s/|,-]+', s)
            student_tokens.update([t for t in tokens if t])

        effective_student_skills = list(student_profile.extracted_skills)
        missing_skills = []

        for req_skill, weight in top_market_reqs.items():
            req_lower = req_skill.lower()

            if req_lower in normalized_student_skill_names or req_lower in student_tokens:
                continue
                
            has_equivalent = False
            for cluster in EQUIVALENCY_CLUSTERS:
                if req_lower in cluster:
                    
                    for term in cluster:

                        if term in normalized_student_skill_names:
                            has_equivalent = True
                            break

                        if len(term.split()) == 1 and term in student_tokens:
                            has_equivalent = True
                            break

                    if has_equivalent:
                        from src.domain.schemas import SkillEvidence
                        effective_student_skills.append(
                            SkillEvidence(
                                skill_name=req_skill,
                                source="Semantic Equivalency Engine",
                                evidence_type="Equivalent", 
                                evidence_date="Unknown" 
                            )
                        )
                        logger.info(f"Equivalency Match: Granted credit for {req_skill}.")
                        break

            if not has_equivalent:
                missing_skills.append(req_skill)

        student_skills_for_scorer = [
            {
                "name": skill.skill_name,
                "date": skill.evidence_date,
                "strength": 1.0
            }
            for skill in effective_student_skills
        ]
        
        scorer = ReadinessScorer()
        readiness_score = scorer.calculate_role_readiness(student_skills_for_scorer, top_market_reqs)
        top_gaps = missing_skills[:5]
        
        logger.info(f"Calculated Score: {readiness_score}%. True Gaps: {len(top_gaps)}")
        
        return {
            "readiness_score": readiness_score,
            "missing_skills": top_gaps
        }
        
    except Exception as e:
        logger.error(f"Gap Agent failed: {str(e)}")
        return {"errors": state.get("errors", []) + [f"Gap analysis failed: {str(e)}"]}