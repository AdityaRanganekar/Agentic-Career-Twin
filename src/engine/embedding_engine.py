import os
import numpy as np

# Ensure HuggingFace uses cached local files without network delay
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from functools import lru_cache
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

# Acronym expansions for domain-specific terminology that compact embedding models struggle with
ACRONYM_EXPANSIONS: Dict[str, str] = {
    "k8s": "kubernetes container orchestration",
    "gcp": "google cloud platform",
    "aws": "amazon web services cloud",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "ci/cd": "continuous integration continuous deployment",
    "db": "database",
    "rdbms": "relational database management system",
    "nosql": "non-relational database",
    "bi": "business intelligence reporting",
    "tf": "tensorflow deep learning framework",
    "genai": "generative artificial intelligence llm",
    "llm": "large language model",
    "llms": "large language models",
    "eda": "exploratory data analysis",
    "etl": "extract transform load data pipeline",
    "elt": "extract load transform data pipeline",
    "git": "git version control github"
}

# Rich domain expansions for data science, ML, data engineering, and cloud skills
DOMAIN_EXPANSIONS: Dict[str, str] = {
    "python": "Python programming language for data science, machine learning, and backend software engineering",
    "r": "R programming language for statistical computing, data analysis, and statistical modeling",
    "scala": "Scala functional programming language for data engineering, Apache Spark, and distributed systems",
    "julia": "Julia high performance scientific computing and machine learning programming language",
    "sql": "SQL structured query language for relational database querying, PostgreSQL, Snowflake, BigQuery",
    "machine learning": "Machine learning algorithms, predictive modeling, statistical learning, scikit-learn",
    "deep learning": "Deep learning neural networks, PyTorch, TensorFlow, computer vision, NLP",
    "statistical modeling": "Statistical modeling, probability distributions, regression, Bayesian inference, statistics",
    "bayesian inference": "Bayesian inference, Bayesian statistics, probability theory, statistical modeling, MCMC",
    "a/b testing": "A/B testing, randomized controlled experiments, hypothesis testing, statistical analysis",
    "time-series analysis": "Time-series analysis, forecasting, ARIMA, temporal data modeling, statistics",
    "statistics": "Statistics, probability theory, inferential statistics, hypothesis testing, statistical modeling",
    "scikit-learn": "Scikit-Learn machine learning library in Python for predictive modeling and data analysis",
    "pytorch": "PyTorch deep learning framework for neural network training and AI model development",
    "tensorflow": "TensorFlow deep learning library for neural network training and AI engineering",
    "xgboost": "XGBoost gradient boosted decision trees for machine learning tabular predictive models",
    "nlp": "Natural language processing, computational linguistics, text mining, language models",
    "aws": "Amazon Web Services AWS cloud infrastructure, EC2, S3, cloud computing",
    "gcp": "Google Cloud Platform GCP cloud computing, BigQuery, cloud infrastructure",
    "azure": "Microsoft Azure cloud platform, cloud computing, enterprise cloud infrastructure",
    "docker": "Docker containerization platform for application packaging and isolated deployments",
    "kubernetes": "Kubernetes container orchestration, k8s cluster scaling and container management",
    "airflow": "Apache Airflow workflow orchestration, DAG scheduler, ETL data pipeline automation",
    "git": "Git version control system, GitHub, source code management, branching workflows",
    "ci/cd": "Continuous integration continuous deployment CI/CD automated software testing and delivery",
    "pandas": "Pandas Python data manipulation, DataFrame analysis, and data engineering",
    "spark": "Apache Spark big data distributed processing and cluster data engineering",
    "tableau": "Tableau business intelligence reporting, data visualization, and executive dashboards",
    "powerbi": "PowerBI business intelligence, data modeling, reporting, and visualization dashboards",
    "snowflake": "Snowflake cloud data warehouse, SQL analytics, and data engineering",
    "bigquery": "Google BigQuery cloud data warehouse, SQL analytics, and large scale data processing",
    "c++": "C++ systems programming language, high performance computing, backend engine for PyTorch and TensorFlow",
    "c": "C low level systems programming language and performance critical software engineering",
    "java": "Java enterprise backend programming language and big data JVM ecosystems",
    "go": "Golang concurrent backend programming language for cloud services and microservices",
    "sas": "SAS statistical analytics system for enterprise statistical modeling and quantitative data analysis",
    "matlab": "MATLAB numerical computing, matrix mathematics, and algorithmic modeling environment"
}

@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Singleton loader for the 384-dimensional SentenceTransformer model.
    Cached in RAM to prevent disk I/O latency on repeated API requests.
    Uses local cached weights to avoid network timeout delays.
    """
    model_name = "all-MiniLM-L6-v2"
    logger.info(f"Loading SentenceTransformer singleton model: {model_name}")
    try:
        return SentenceTransformer(model_name, local_files_only=True)
    except Exception:
        return SentenceTransformer(model_name)

class EmbeddingEngine:
    """
    Computes dense semantic similarity matrices between candidate skills and market requirements.
    """
    def __init__(self):
        self.model = get_embedding_model()

    @staticmethod
    def expand_skill_text(raw_skill: str) -> str:
        """
        Normalizes acronyms and injects rich domain context to ensure dense vector embeddings
        accurately capture functional semantic overlap.
        """
        clean = raw_skill.strip().lower()

        if clean in DOMAIN_EXPANSIONS:
            return DOMAIN_EXPANSIONS[clean]
            
        if clean in ACRONYM_EXPANSIONS:
            return f"Technical skill: {ACRONYM_EXPANSIONS[clean]}"
            
        return f"Technical skill: {raw_skill.strip()}"

    def compute_similarity_matrix(
        self,
        student_skills: List[str],
        market_skills: List[str]
    ) -> np.ndarray:
        """
        Encodes student skills and market requirements into 384-dimensional vectors
        and computes the pairwise cosine similarity matrix.

        Returns:
            np.ndarray: Matrix of shape (len(student_skills), len(market_skills))
        """
        if not student_skills or not market_skills:
            return np.zeros((len(student_skills), len(market_skills)))

        expanded_student = [self.expand_skill_text(s) for s in student_skills]
        expanded_market = [self.expand_skill_text(m) for m in market_skills]

        student_vectors = self.model.encode(
            expanded_student,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        market_vectors = self.model.encode(
            expanded_market,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        similarity_matrix = cosine_similarity(student_vectors, market_vectors)
        return similarity_matrix
