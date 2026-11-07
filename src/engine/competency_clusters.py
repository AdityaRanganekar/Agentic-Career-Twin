"""
Canonical Competency Concept Engine
Prevents redundant penalties for sibling tools by consolidating requirements into
canonical competency concept buckets and evaluating candidate skills via functional equivalency.
"""
from typing import Dict, Set, List, Tuple, Optional
import re
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

# 1. Canonical Competency Clusters (15 major technical competency domains)
COMPETENCY_CLUSTERS: Dict[str, Set[str]] = {
    "Cloud Infrastructure & Platforms": {
        "aws", "amazon web services", "aws sagemaker", "ec2", "s3", "lambda",
        "gcp", "google cloud", "google cloud platform", "vertex ai",
        "azure", "microsoft azure", "cloud computing", "cloud infrastructure"
    },
    "Relational Databases (SQL)": {
        "sql", "postgresql", "postgres", "mysql", "sqlite", "sql server",
        "ms sql", "oracle", "mariadb", "rdbms", "relational database", "database"
    },
    "NoSQL & Document/Key-Value Databases": {
        "nosql", "mongodb", "dynamodb", "cassandra", "apache cassandra",
        "redis", "couchbase", "elasticsearch", "neo4j", "hbase"
    },
    "Cloud Data Warehouses": {
        "snowflake", "bigquery", "google bigquery", "redshift", "amazon redshift",
        "databricks", "data warehousing", "data warehouse"
    },
    "Deep Learning Frameworks": {
        "pytorch", "tensorflow", "keras", "deep learning", "neural networks",
        "jax", "caffe", "mxnet"
    },
    "Classical ML & Scientific Python": {
        "machine learning", "scikit-learn", "sklearn", "xgboost", "lightgbm",
        "catboost", "scipy", "numpy", "pandas", "statsmodels",
        "random forests", "logistic regression", "linear regression", "predictive modeling"
    },
    "Statistical & Quantitative Modeling": {
        "statistics", "statistical modeling", "statistical analysis", "statistical software",
        "bayesian inference", "time-series analysis", "a/b testing", "hypothesis testing",
        "quantitative analysis", "spss", "stata", "sas", "matlab", "r"
    },
    "GenAI, LLMs & NLP": {
        "nlp", "natural language processing", "llms", "large language models",
        "genai", "generative ai", "langchain", "langgraph", "llamaindex",
        "rag", "huggingface", "transformers", "spacy", "bert",
        "prompt engineering", "vector databases"
    },
    "Big Data & Distributed Compute": {
        "apache spark", "spark", "pyspark", "hadoop", "apache hadoop",
        "hive", "apache hive", "mapreduce", "kafka", "apache kafka",
        "flink", "dask", "big data"
    },
    "Workflow Orchestration & Data Pipelines": {
        "apache airflow", "airflow", "etl", "elt", "data pipelines",
        "data engineering", "dbt", "prefect", "dagster", "informatica", "talend"
    },
    "Containers, Linux & DevOps": {
        "docker", "kubernetes", "k8s", "linux", "unix", "bash", "shell",
        "shell scripting", "git", "github", "gitlab", "ci/cd",
        "jenkins", "github actions", "terraform", "devops", "mlops"
    },
    "BI, Reporting & Data Visualization": {
        "tableau", "powerbi", "power bi", "looker", "qlik",
        "data visualization", "reporting", "matplotlib", "seaborn",
        "plotly", "excel", "microsoft excel", "google analytics"
    },
    "Backend & API Development": {
        "fastapi", "flask", "django", "rest api", "graphql",
        "microservices", "nodejs", "node.js", "spring boot", "express"
    },
    "Frontend & Web Development": {
        "javascript", "typescript", "react", "react.js", "angular",
        "vue", "html", "css", "next.js"
    },
    "Core Programming Languages": {
        "python", "r", "c++", "c", "java", "scala", "go", "golang", "rust", "julia"
    }
}

# 2. Consolidation mappings for pre-scoring requirement merging
CONSOLIDATION_MAPPINGS: Dict[str, Set[str]] = {
    "NoSQL Databases (e.g. MongoDB, Redis)": {
        "nosql", "mongodb", "cassandra", "dynamodb", "redis", "hbase"
    },
    "SQL / Relational Databases": {
        "sql", "mysql", "postgresql", "postgres", "oracle", "sql server", "sqlite", "rdbms"
    },
    "Cloud Platforms (AWS / GCP / Azure)": {
        "aws", "gcp", "google cloud", "azure", "cloud computing", "cloud infrastructure"
    },
    "Deep Learning Frameworks (PyTorch / TensorFlow)": {
        "pytorch", "tensorflow", "keras"
    },
    "Scientific Python (Pandas / NumPy / Scikit-Learn)": {
        "scikit-learn", "scipy", "numpy", "pandas"
    },
    "Distributed Data Processing (Spark / Kafka)": {
        "apache spark", "spark", "pyspark", "hadoop", "hive", "mapreduce", "kafka"
    },
    "Linux / UNIX Systems": {
        "linux", "unix", "bash", "shell"
    },
    "BI & Data Visualization (Tableau / PowerBI)": {
        "tableau", "powerbi", "looker", "data visualization"
    },
    "C / C++": {
        "c", "c++"
    }
}

# 3. Non-technical O*NET / HR / Administrative noise words
ONET_NOISE_WORDS: Set[str] = {
    "microsoft word", "word", "powerpoint", "outlook", "adobe acrobat",
    "quickbooks", "statistical software", "office", "microsoft office",
    "spreadsheets", "word processing", "presentation software", "electronic mail",
    "calendar and scheduling", "time accounting software", "desktop publishing software",
    "customer service", "communication", "teamwork", "leadership", "interpersonal skills",
    "problem solving", "organizational skills", "written communication", "verbal communication"
}

def consolidate_target_weights(target_weights: Dict[str, float]) -> Dict[str, float]:
    """
    Consolidates sibling tools in target_weights into single technical concept requirement keys.
    Filters out administrative O*NET noise words and assigns maximum weight among matched siblings.
    """
    clean_input = {
        k: float(v) for k, v in target_weights.items()
        if k.strip().lower() not in ONET_NOISE_WORDS
    }
    
    consolidated: Dict[str, float] = {}
    matched_keys: Set[str] = set()

    for bucket_name, members in CONSOLIDATION_MAPPINGS.items():
        matched = {k: v for k, v in clean_input.items() if k.strip().lower() in members}
        if matched:
            consolidated[bucket_name] = max(matched.values())
            matched_keys.update(matched.keys())

    for k, v in clean_input.items():
        if k not in matched_keys:
            consolidated[k] = v

    return consolidated

def match_consolidated_requirement(
    req_name: str,
    normalized_student_skills: Set[str],
    student_tokens: Set[str]
) -> Tuple[Optional[float], Optional[str]]:
    """
    Implements the Canonical Equivalence Matching Rules:
    Returns (match_strength, matched_skill_label) if candidate possesses ANY tool
    belonging to that consolidated bucket or an implied higher-level competency.
    """
    req_lower = req_name.strip().lower()

    # Rule 1: Cloud Platforms (AWS / GCP / Azure)
    if req_name == "Cloud Platforms (AWS / GCP / Azure)" or req_lower in {"aws", "gcp", "azure", "cloud computing"}:
        cloud_tools = COMPETENCY_CLUSTERS["Cloud Infrastructure & Platforms"]
        for s in normalized_student_skills:
            if s in cloud_tools or any(ct in s for ct in ["aws", "sagemaker", "gcp", "google cloud", "azure"]):
                return 1.0, s

    # Rule 2: SQL / Relational Databases
    if req_name == "SQL / Relational Databases" or req_lower in {"sql", "postgresql", "postgres", "mysql", "sqlite", "oracle"}:
        sql_tools = COMPETENCY_CLUSTERS["Relational Databases (SQL)"]
        for s in normalized_student_skills:
            if s in sql_tools or any(st in s for st in ["sql", "postgres", "mysql", "sqlite"]):
                return 1.0, s

    # Rule 3: Deep Learning Frameworks (PyTorch / TensorFlow)
    if req_name == "Deep Learning Frameworks (PyTorch / TensorFlow)" or req_lower in {"pytorch", "tensorflow", "keras", "deep learning"}:
        dl_tools = COMPETENCY_CLUSTERS["Deep Learning Frameworks"]
        for s in normalized_student_skills:
            if s in dl_tools or any(dt in s for dt in ["pytorch", "tensorflow", "keras", "deep learning", "neural network"]):
                return 1.0, s

    # Rule 4: Scientific Python (Pandas / NumPy / Scikit-Learn)
    if req_name == "Scientific Python (Pandas / NumPy / Scikit-Learn)" or req_lower in {"pandas", "numpy", "scikit-learn", "scipy", "sklearn"}:
        sci_tools = {"scikit-learn", "sklearn", "pandas", "numpy", "scipy", "xgboost", "lightgbm"}
        for s in normalized_student_skills:
            if s in sci_tools:
                return 1.0, s

    # Rule 5: Linux / UNIX Systems
    if req_name == "Linux / UNIX Systems" or req_lower in {"linux", "unix", "bash", "shell"}:
        if any(s in normalized_student_skills for s in {"linux", "unix", "bash", "shell"}):
            return 1.0, "linux"
        if any(s in normalized_student_skills for s in {"docker", "aws", "apache airflow", "airflow"}):
            return 0.90, "docker/cloud"

    # Rule 6: Git & Version Control
    if req_lower == "git":
        if any(s in normalized_student_skills for s in {"git", "github", "gitlab"}):
            return 1.0, "git"
        if any(s in normalized_student_skills for s in {"docker", "aws", "apache airflow", "airflow"}):
            return 0.90, "docker/cloud"

    # Rule 7: Distributed Data Processing (Spark / Kafka)
    if req_name == "Distributed Data Processing (Spark / Kafka)" or req_lower in {"spark", "pyspark", "kafka", "hadoop"}:
        dist_tools = {"apache spark", "spark", "pyspark", "hadoop", "hive", "mapreduce", "kafka", "apache kafka"}
        for s in normalized_student_skills:
            if s in dist_tools or any(dt in s for dt in ["spark", "pyspark", "kafka"]):
                return 1.0, s
        if ("apache airflow" in normalized_student_skills or "airflow" in normalized_student_skills):
            if "python" in normalized_student_skills and any(s in normalized_student_skills for s in ["sql", "postgresql", "mysql"]):
                return 0.82, "airflow+python+sql"

    # Rule 8: BI & Data Visualization (Tableau / PowerBI)
    if req_name == "BI & Data Visualization (Tableau / PowerBI)" or req_lower in {"tableau", "powerbi", "power bi", "looker"}:
        bi_tools = {"tableau", "powerbi", "power bi", "looker", "data visualization", "matplotlib", "seaborn", "plotly"}
        for s in normalized_student_skills:
            if s in bi_tools:
                return 1.0, s

    # Rule 9: C / C++
    if req_name == "C / C++" or req_lower in {"c", "c++"}:
        if "c" in normalized_student_skills or "c++" in normalized_student_skills:
            return 1.0, "c++"
        has_deep_learning = any(s in normalized_student_skills for s in ["pytorch", "tensorflow", "deep learning"])
        if "python" in normalized_student_skills and has_deep_learning:
            return 0.85, "python+deep_learning"
        if any(s in normalized_student_skills for s in ["java", "go", "matlab", "rust"]):
            return 0.85, "compiled_language"

    # Rule 10: NoSQL Databases (e.g. MongoDB, Redis)
    if req_name == "NoSQL Databases (e.g. MongoDB, Redis)" or req_lower in {"nosql", "mongodb", "cassandra", "dynamodb", "redis"}:
        nosql_tools = {"nosql", "mongodb", "cassandra", "dynamodb", "redis", "hbase", "elasticsearch"}
        for s in normalized_student_skills:
            if s in nosql_tools:
                return 1.0, s
        if "sql" in normalized_student_skills and any(s in normalized_student_skills for s in ["aws", "gcp", "azure"]):
            return 0.50, "sql+cloud"

    # Rule 11: Machine Learning & Quantitative Analytics
    if req_lower in {"machine learning", "statistics"}:
        if any(s in normalized_student_skills for s in ["statistical modeling", "bayesian inference", "time-series analysis"]):
            return 0.85, "advanced_statistics"

    return None, None

