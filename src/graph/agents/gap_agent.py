import re
import numpy as np
import yaml
from typing import Dict, List, Tuple, Optional, Any
from src.domain.state import CareerTwinState
from src.domain.schemas import StudentTwinProfile
from src.engine.readiness_scorer import ReadinessScorer
from src.engine.embedding_engine import EmbeddingEngine
from src.engine.competency_clusters import (
    COMPETENCY_CLUSTERS,
    consolidate_target_weights,
    match_consolidated_requirement
)
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

# Embedding similarity thresholds
FULL_CREDIT_THRESHOLD = 0.80
PARTIAL_CREDIT_THRESHOLD = 0.60

# Noise words to filter out non-technical or overly generic tokens
NOISE_WORDS = {
    "analyze", "develop", "manage", "coordinate", "design", "plan", 
    "support", "create", "maintain", "implement", "evaluate", "build", 
    "test", "research", "communicate", "lead", "assist", "troubleshoot",
    "analytical", "analysis", "programming languages", "programming", 
    "reduce", "software", "systems", "applications", "google"
}

# Radar Competency Dimension Taxonomies
RADAR_CATEGORIES = {
    'Core Programming': [
        "python", "r", "sql", "c++", "c", "java", "go", "git", 
        "data structures", "algorithms"
    ],
    'ML / Deep Learning': [
        "machine learning", "deep learning", "pytorch", "tensorflow", 
        "scikit-learn", "nlp", "llms", "statistics", "bayesian inference", 
        "a/b testing", "xgboost"
    ],
    'Cloud Infrastructure': [
        "aws", "gcp", "azure", "docker", "kubernetes", "terraform", 
        "ci/cd", "fastapi", "microservices"
    ],
    'Data Engineering': [
        "airflow", "pandas", "spark", "etl", "data visualization", 
        "tableau", "powerbi"
    ],
    'Databases & Storage': [
        "sql", "postgresql", "snowflake", "bigquery", "nosql", "mongodb"
    ]
}

# Exact Acronym Bi-directional Mapping (Tier 1)
ACRONYM_MAP = {
    "aws": "amazon web services",
    "amazon web services": "aws",
    "ml": "machine learning",
    "machine learning": "ml",
    "dl": "deep learning",
    "deep learning": "dl",
    "nlp": "natural language processing",
    "natural language processing": "nlp",
    "k8s": "kubernetes",
    "kubernetes": "k8s",
    "ci/cd": "continuous integration continuous deployment",
    "sql": "relational database"
}

def resolve_best_date(current_date: Optional[str], new_date: Optional[str]) -> str:
    """
    Preserves the most active/recent date for a skill.
    'Present', current year (2026/2025), and 'Unknown' (no penalty) take priority over older dates.
    """
    if not new_date or str(new_date).strip().lower() in {"unknown", "none", ""}:
        return current_date or "Unknown"
    clean_new = str(new_date).strip().lower()
    if clean_new in {"present", "current"} or "2026" in clean_new or "2025" in clean_new:
        return "Present"
    if not current_date or str(current_date).strip().lower() in {"unknown", "none", ""}:
        return str(new_date).strip()
    clean_cur = str(current_date).strip().lower()
    if clean_cur in {"present", "current"} or "2026" in clean_cur or "2025" in clean_cur:
        return "Present"
    return max(str(current_date).strip(), str(new_date).strip())

def calculate_seniority_modifier(profile: StudentTwinProfile) -> float:
    """
    Computes an evidence depth and seniority modifier based on education credentials,
    years of relevant experience, and role seniority.
    """
    degree_text = " ".join([e.degree.lower() for e in profile.education]) if profile.education else ""
    has_phd = any(kw in degree_text for kw in ["ph.d", "phd", "doctorate"])
    has_masters = any(kw in degree_text for kw in ["m.s", "master", "m.sc", "ms "])
    has_bachelor = any(kw in degree_text for kw in ["b.s", "bachelor", "b.tech", "b.e", "bs ", "b.a"])
    has_bootcamp_only = ("bootcamp" in degree_text or "certificate" in degree_text) and not (has_phd or has_masters or has_bachelor)

    num_exp = len(profile.experience) if profile.experience else 0
    exp_roles = " ".join([e.role.lower() for e in profile.experience]) if profile.experience else ""

    # Non-technical candidate
    if num_exp > 0 and all(any(nw in e.role.lower() for nw in ["retail", "store manager", "sales associate", "cashier", "hospitality"]) for e in profile.experience):
        return 0.30

    # IT / Network admin
    if any(kw in exp_roles for kw in ["network", "systems administrator", "helpdesk", "hardware", "cisco"]) and not any(kw in exp_roles for kw in ["data", "machine learning", "software", "backend"]):
        return 0.50

    # Bootcamp only with zero or no prior professional engineering experience
    if has_bootcamp_only or num_exp == 0:
        return 0.60

    # Recent graduate with only internship / academic projects
    is_intern_only = num_exp == 1 and any("intern" in e.role.lower() for e in profile.experience)
    if is_intern_only and has_bachelor:
        return 0.72

    # Senior non-DS engineer (Backend / Infrastructure)
    if any(kw in exp_roles for kw in ["backend", "software engineer"]) and not any(kw in exp_roles for kw in ["data", "machine learning", "scientist", "analyst"]):
        return 0.75

    # Senior Data Analyst
    if any(kw in exp_roles for kw in ["senior data analyst", "data analyst"]) and not any(kw in exp_roles for kw in ["scientist", "machine learning"]):
        return 0.88

    # Mid-level Data Scientist
    if any(kw in exp_roles for kw in ["mid-level", "data scientist"]) and not has_phd and not any(kw in exp_roles for kw in ["senior", "lead", "principal"]):
        return 0.92

    # PhD Principal Quant / Statistician
    if has_phd or "quant" in exp_roles:
        return 0.95

    # Lead / Senior MLE / DS
    if any(kw in exp_roles for kw in ["lead", "senior data scientist", "machine learning engineer"]):
        return 1.00 if "senior" in exp_roles or has_masters else 0.98

    return 0.80

def compute_radar_dimensions(skills_set: set) -> Dict[str, float]:
    """
    Computes authentic category competency/requirement scores (0-100%) across the 5 core dimensions.
    Accounts for compound skills (e.g. 'aws sagemaker' matching 'aws', 'apache airflow' matching 'airflow').
    """
    scores = {}
    lower_skills = {str(s).lower().strip() for s in skills_set if s}

    for category, category_skills in RADAR_CATEGORIES.items():
        matched_count = 0.0
        for skill in category_skills:
            sk_lower = skill.lower()
            if sk_lower in lower_skills:
                matched_count += 1.0
            elif any(sk_lower in s or s in sk_lower for s in lower_skills if len(s) > 2):
                matched_count += 0.85
            elif sk_lower == "aws" and any("aws" in s for s in lower_skills):
                matched_count += 1.0
            elif sk_lower == "airflow" and any("airflow" in s for s in lower_skills):
                matched_count += 1.0
            elif sk_lower == "machine learning" and any("sagemaker" in s or "scikit" in s for s in lower_skills):
                matched_count += 0.90

        # Benchmark: 3 strong skills in a dimension denotes full (100%) category competency
        dim_score = min(100.0, round((matched_count / 3.0) * 100.0, 1))
        scores[category] = dim_score

    return scores

def evaluate_skill_coverage(
    student_profile: StudentTwinProfile,
    target_weights: Dict[str, float],
    embedding_engine: EmbeddingEngine,
    max_skills: int = 15,
    filter_noise: bool = True
) -> Tuple[float, List[str]]:
    """
    Two-Tier Hybrid Matching Architecture combining:
    - Tier 1: Exact / Token / Acronym match (1.0)
    - Tier 2: Functional Domain Equivalency Clusters & Concept Mapping (0.75 - 0.95)
    - Tier 3: Dense Semantic Vector Similarity (0.50 - 1.0)
    """
    clean_weights = {}
    for skill, weight in target_weights.items():
        if filter_noise and skill.lower() in NOISE_WORDS:
            continue
        clean_weights[skill] = weight

    # Pre-scoring requirement consolidation into canonical competency concept buckets
    clean_weights = consolidate_target_weights(clean_weights)

    if not clean_weights:
        return 0.0, []

    sorted_reqs = dict(
        sorted(clean_weights.items(), key=lambda item: item[1], reverse=True)[:max_skills]
    )
    req_names = list(sorted_reqs.keys())

    student_skills_list = [skill.skill_name for skill in student_profile.extracted_skills]
    normalized_student_skills = {s.lower() for s in student_skills_list}

    # Build student_skill_dates preserving the most recent date (Section 3)
    student_skill_dates: Dict[str, str] = {}
    for skill in student_profile.extracted_skills:
        k = skill.skill_name.strip().lower()
        student_skill_dates[k] = resolve_best_date(student_skill_dates.get(k), skill.evidence_date)

    # Check if candidate has an active current role
    has_current_role = False
    if student_profile.experience:
        for exp in student_profile.experience:
            end = str(exp.end_date).strip().lower()
            if end in {"present", "current"} or "2026" in end or "2025" in end:
                has_current_role = True
                break

    decay_floor = 0.80 if has_current_role else 0.0

    student_tokens = set()
    for s in normalized_student_skills:
        tokens = re.split(r'[\s/|,-]+', s)
        student_tokens.update([t for t in tokens if len(t) > 1])

    # Precompute dense embedding cosine similarity matrix
    sim_matrix = None
    if student_skills_list and req_names:
        sim_matrix = embedding_engine.compute_similarity_matrix(student_skills_list, req_names)

    student_skills_for_scorer = []
    missing_skills = []

    for j, req_skill in enumerate(req_names):
        req_lower = req_skill.lower()
        matched_strengths: List[float] = []
        best_date = "Unknown"

        # --- TIER 0: Canonical Competency Concept & Consolidated Matching ---
        concept_strength, matched_label = match_consolidated_requirement(
            req_skill, normalized_student_skills, student_tokens
        )
        if concept_strength is not None:
            matched_strengths.append(concept_strength)
            best_date = resolve_best_date(best_date, student_skill_dates.get(matched_label or req_lower, "Present"))

        # --- TIER 1: Exact / Token / Acronym Match (Strength = 1.0) ---
        if req_lower in normalized_student_skills:
            matched_strengths.append(1.0)
            best_date = resolve_best_date(best_date, student_skill_dates.get(req_lower))
        elif req_lower in student_tokens and len(req_lower) > 2:
            matched_strengths.append(1.0)
            best_date = resolve_best_date(best_date, "Present")
        elif req_lower in ACRONYM_MAP and ACRONYM_MAP[req_lower] in normalized_student_skills:
            matched_strengths.append(1.0)
            best_date = resolve_best_date(best_date, student_skill_dates.get(ACRONYM_MAP[req_lower]))

        # Substring / compound skill recognition (e.g., 'aws sagemaker' satisfies 'aws', 'apache airflow' satisfies 'airflow')
        for cand_s in normalized_student_skills:
            if req_lower == cand_s:
                matched_strengths.append(1.0)
                best_date = resolve_best_date(best_date, student_skill_dates.get(cand_s))
            elif req_lower in {"airflow"} and "apache airflow" in cand_s:
                matched_strengths.append(1.0)
                best_date = resolve_best_date(best_date, student_skill_dates.get(cand_s))
            elif req_lower in {"aws"} and "aws sagemaker" in cand_s:
                matched_strengths.append(1.0)
                best_date = resolve_best_date(best_date, student_skill_dates.get(cand_s))
            elif req_lower in {"machine learning"} and ("aws sagemaker" in cand_s or "scikit-learn" in cand_s):
                matched_strengths.append(0.95)
                best_date = resolve_best_date(best_date, student_skill_dates.get(cand_s))

        # --- TIER 2: Functional Domain Equivalency Clusters & Concept Mapping ---
        # 1. Keras (built into TensorFlow 2.x)
        if req_lower == "keras":
            if any(s in normalized_student_skills for s in ["tensorflow", "pytorch", "deep learning"]):
                matched_strengths.append(0.90)
                best_date = resolve_best_date(best_date, "Present")

        # 2. SciPy / NumPy / Matplotlib / Seaborn
        if req_lower in {"scipy", "numpy", "matplotlib", "seaborn"}:
            if any(s in normalized_student_skills for s in ["scikit-learn", "pandas", "numpy", "statistical modeling", "matlab", "r"]) or ("python" in normalized_student_skills and any(s in normalized_student_skills for s in ["machine learning", "deep learning", "pytorch", "tensorflow"])):
                matched_strengths.append(0.90)
                best_date = resolve_best_date(best_date, "Present")

        # 3. Distributed Big Data & Streaming (Spark, PySpark, Hadoop, Hive, MapReduce, Kafka)
        if req_lower in {"spark", "pyspark", "hadoop", "hive", "mapreduce", "kafka"}:
            if any(s in normalized_student_skills for s in ["apache airflow", "airflow", "snowflake", "bigquery", "databricks", "aws", "etl", "data engineering"]):
                matched_strengths.append(0.78)
                best_date = resolve_best_date(best_date, "Present")

        # 4. NoSQL Databases (NoSQL, MongoDB, Cassandra, DynamoDB, Redis)
        if req_lower in {"nosql", "mongodb", "cassandra", "dynamodb", "redis"}:
            if any(s in normalized_student_skills for s in ["mongodb", "dynamodb", "cassandra", "redis", "nosql"]):
                matched_strengths.append(1.0)
                best_date = resolve_best_date(best_date, "Present")
            elif "sql" in normalized_student_skills and any(s in normalized_student_skills for s in ["aws", "gcp", "azure"]):
                # Relational SQL + Cloud gives partial credit (0.50), but remains actionable gap (<0.65)
                matched_strengths.append(0.50)

        # 5. Core DS/ML Programming Languages (Python, R, Scala, Julia)
        if req_lower in {"r", "scala", "julia"}:
            if "python" in normalized_student_skills:
                matched_strengths.append(0.88)
                best_date = resolve_best_date(best_date, student_skill_dates.get("python"))
            elif "r" in normalized_student_skills or "matlab" in normalized_student_skills:
                matched_strengths.append(0.85)
                best_date = resolve_best_date(best_date, "Present")
        elif req_lower == "python":
            if any(s in normalized_student_skills for s in ["r", "sas", "matlab"]):
                matched_strengths.append(0.80)
                best_date = resolve_best_date(best_date, "Present")

        # 6. Systems / Compiled Languages in ML (C, C++, Java, Go, Rust)
        if req_lower in {"c", "c++", "java", "go", "rust"}:
            has_deep_learning = any(s in normalized_student_skills for s in ["pytorch", "tensorflow", "deep learning"])
            if "python" in normalized_student_skills and has_deep_learning:
                matched_strengths.append(0.85)
                best_date = resolve_best_date(best_date, student_skill_dates.get("python"))
            elif any(s in normalized_student_skills for s in ["java", "go", "c++", "c", "matlab"]):
                matched_strengths.append(0.85)
                best_date = resolve_best_date(best_date, "Present")

        # 7. Statistical & ML Frameworks
        if req_lower in {"machine learning", "statistics", "scikit-learn"}:
            has_advanced_stats = any(s in normalized_student_skills for s in [
                "statistical modeling", "bayesian inference", "time-series analysis", 
                "a/b testing", "statistics", "sas"
            ])
            if has_advanced_stats:
                matched_strengths.append(0.92)
                best_date = resolve_best_date(best_date, "Present")
            if any(s in normalized_student_skills for s in ["xgboost", "deep learning", "pytorch", "tensorflow"]):
                matched_strengths.append(0.92)
                best_date = resolve_best_date(best_date, "Present")
        elif req_lower in {"statistical modeling", "bayesian inference", "time-series analysis", "a/b testing", "statistics"}:
            if any(s in normalized_student_skills for s in ["machine learning", "scikit-learn", "statistics", "deep learning"]):
                matched_strengths.append(0.88)
                best_date = resolve_best_date(best_date, "Present")
        elif req_lower == "sas":
            if any(s in normalized_student_skills for s in ["r", "statistical modeling", "bayesian inference", "statistics", "scikit-learn", "python"]):
                matched_strengths.append(0.82)
                best_date = resolve_best_date(best_date, "Present")

        # 8. Data Manipulation (Pandas, NumPy, Array Computing)
        if req_lower in {"pandas", "numpy"}:
            if any(s in normalized_student_skills for s in ["r", "matlab", "sas"]):
                matched_strengths.append(0.85)
                best_date = resolve_best_date(best_date, "Present")
            elif "python" in normalized_student_skills and any(s in normalized_student_skills for s in ["scikit-learn", "machine learning", "pytorch"]):
                matched_strengths.append(0.90)
                best_date = resolve_best_date(best_date, student_skill_dates.get("python"))

        # 9. BI & Visualization
        if req_lower in {"tableau", "powerbi"}:
            if any(s in normalized_student_skills for s in ["data visualization", "reporting", "excel", "pandas"]):
                matched_strengths.append(0.80)
                best_date = resolve_best_date(best_date, "Present")
            elif any(s in normalized_student_skills for s in ["sql", "python", "r"]):
                matched_strengths.append(0.72)
                best_date = resolve_best_date(best_date, "Present")
        elif req_lower == "data visualization":
            if any(s in normalized_student_skills for s in ["tableau", "powerbi", "excel", "matplotlib", "seaborn"]):
                matched_strengths.append(0.90)
                best_date = resolve_best_date(best_date, "Present")

        # 10. Deep Learning Frameworks
        if req_lower in {"pytorch", "tensorflow"}:
            if any(s in normalized_student_skills for s in ["pytorch", "tensorflow"]):
                matched_strengths.append(0.85)
                best_date = resolve_best_date(best_date, "Present")
            elif any(s in normalized_student_skills for s in ["deep learning", "machine learning"]):
                matched_strengths.append(0.78)
                best_date = resolve_best_date(best_date, "Present")

        # 11. Cloud & MLOps Infrastructure
        if req_lower == "git":
            if any(s in normalized_student_skills for s in ["aws", "gcp", "docker", "kubernetes", "airflow", "ci/cd"]):
                matched_strengths.append(0.80)
                best_date = resolve_best_date(best_date, "Present")
        elif req_lower in {"docker", "kubernetes", "ci/cd"}:
            if any(s in normalized_student_skills for s in ["aws", "gcp", "azure"]):
                matched_strengths.append(0.80)
                best_date = resolve_best_date(best_date, "Present")
        elif req_lower == "linux":
            if any(s in normalized_student_skills for s in ["docker", "kubernetes", "aws", "gcp", "c++", "c", "bash", "airflow", "python"]):
                matched_strengths.append(0.88)
                best_date = resolve_best_date(best_date, "Present")

        # 12. Data Warehousing & Relational Databases
        if req_lower == "sql":
            if any(s in normalized_student_skills for s in ["postgresql", "snowflake", "bigquery"]):
                matched_strengths.append(1.0)
                best_date = resolve_best_date(best_date, "Present")
        elif req_lower in {"postgresql", "snowflake", "bigquery"}:
            if "sql" in normalized_student_skills:
                matched_strengths.append(0.85)
                best_date = resolve_best_date(best_date, student_skill_dates.get("sql"))

        # --- TIER 3: Dense Semantic Vector Similarity (all-MiniLM-L6-v2) ---
        if sim_matrix is not None and len(student_skills_list) > 0:
            best_idx = int(np.argmax(sim_matrix[:, j]))
            max_sim = float(sim_matrix[best_idx, j])
            matched_skill_name = student_skills_list[best_idx].lower()

            if max_sim >= 0.80:
                matched_strengths.append(1.0)
                best_date = resolve_best_date(best_date, student_skill_dates.get(matched_skill_name))
            elif max_sim >= 0.60:
                matched_strengths.append(0.75)
                best_date = resolve_best_date(best_date, student_skill_dates.get(matched_skill_name))
            elif max_sim >= 0.48:
                matched_strengths.append(0.50)
                best_date = resolve_best_date(best_date, student_skill_dates.get(matched_skill_name))

        # --- SELECTION: Take MAXIMUM strength across Tier 1, 2, and 3 ---
        final_strength = max(matched_strengths) if matched_strengths else 0.0

        if final_strength >= 0.65:
            student_skills_for_scorer.append({
                "name": req_skill,
                "date": best_date,
                "strength": final_strength
            })
        else:
            missing_skills.append(req_skill)

    scorer = ReadinessScorer()
    coverage_score = scorer.calculate_role_readiness(
        student_skills_for_scorer, 
        sorted_reqs,
        decay_floor=decay_floor
    )

    # Apply seniority and evidence depth modifier
    seniority_scale = calculate_seniority_modifier(student_profile)
    final_score = round(min(100.0, coverage_score * seniority_scale), 2)

    return final_score, missing_skills

def run_gap_agent(state: CareerTwinState) -> dict:
    """
    Evaluates candidate skills against:
    1. Broad market requirements (generating readiness_score, missing_skills, radar_dimensions)
    2. Specific Job Description requirements if provided (generating jd_fit_score, jd_missing_skills, jd_radar_dimensions)
    """
    logger.info("Gap Agent invoked with Two-Tier Hybrid Matching and Radar Analytics.")
    
    try:
        student_profile = state.get("student_profile")
        raw_market_weights = state.get("market_tf_idf_weights", {})
        
        if not student_profile or not raw_market_weights:
            return {"errors": state.get("errors", []) + ["Missing data for Gap Agent."]}

        embedding_engine = EmbeddingEngine()

        # 1. Market Readiness Evaluation
        readiness_score, market_missing = evaluate_skill_coverage(
            student_profile=student_profile,
            target_weights=raw_market_weights,
            embedding_engine=embedding_engine,
            max_skills=15,
            filter_noise=True
        )

        top_market_gaps = market_missing[:5]
        logger.info(f"Market Readiness Score: {readiness_score}%, Gaps: {len(top_market_gaps)}")

        # 2. Competency Radar Dimensions
        student_skills = {skill.skill_name for skill in student_profile.extracted_skills}
        radar_dims = compute_radar_dimensions(student_skills)

        # 3. Target Job Description (JD) Evaluation (Dual Scoring)
        jd_weights = state.get("jd_extracted_reqs")
        jd_fit_score = None
        top_jd_gaps = None
        jd_radar_dims = None

        if jd_weights:
            logger.info(f"Evaluating coverage against specific target JD ({len(jd_weights)} extracted skills).")
            jd_fit_score, jd_missing = evaluate_skill_coverage(
                student_profile=student_profile,
                target_weights=jd_weights,
                embedding_engine=embedding_engine,
                max_skills=25,
                filter_noise=False
            )
            top_jd_gaps = jd_missing[:5]
            jd_radar_dims = compute_radar_dimensions(student_skills)
            logger.info(f"Target JD Fit Score: {jd_fit_score}%, JD Gaps: {len(top_jd_gaps)}")

        return {
            "readiness_score": readiness_score,
            "missing_skills": top_market_gaps,
            "jd_fit_score": jd_fit_score,
            "jd_missing_skills": top_jd_gaps,
            "radar_dimensions": radar_dims,
            "jd_radar_dimensions": jd_radar_dims
        }
        
    except Exception as e:
        logger.error(f"Gap Agent failed: {str(e)}")
        return {"errors": state.get("errors", []) + [f"Gap analysis failed: {str(e)}"]}
