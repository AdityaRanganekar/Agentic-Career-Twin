import os
import numpy as np
from functools import lru_cache
from typing import List, Dict, Union
from sklearn.metrics.pairwise import cosine_similarity
from src.utils.logger import get_custom_logger

try:
    from fastembed import TextEmbedding
    HAS_FASTEMBED = True
except ImportError:
    HAS_FASTEMBED = False

logger = get_custom_logger(__name__)

class FastEmbedModelAdapter:
    """
    Adapter around fastembed.TextEmbedding providing 100% API compatibility with SentenceTransformer.
    Specifically implements .encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    returning normalized numpy arrays of shape (len(texts), 384) or (384,) for single strings.
    """
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def encode(
        self,
        sentences: Union[str, List[str]],
        batch_size: int = 32,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
        convert_to_tensor: bool = False,
        device: str = None,
        normalize_embeddings: bool = True,
        **kwargs
    ) -> np.ndarray:
        is_single = isinstance(sentences, str)
        text_list = [sentences] if is_single else list(sentences)

        if not text_list:
            return np.empty((0, 384), dtype=np.float32)

        embeddings_gen = self._model.embed(text_list, batch_size=batch_size)
        embeddings = np.array(list(embeddings_gen), dtype=np.float32)

        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            embeddings = embeddings / norms

        return embeddings[0] if is_single else embeddings

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
def get_embedding_model():
    """
    Singleton loader for the 384-dimensional embedding model.
    Prioritizes ONNX FastEmbed (TextEmbedding) for lean, high-performance CPU inference (<160 MB RAM).
    Cached in RAM to prevent redundant re-initialization and latency on repeated requests.
    Gracefully falls back to SentenceTransformer if fastembed is not installed.
    """
    if HAS_FASTEMBED:
        logger.info("Loading FastEmbed ONNX singleton model: sentence-transformers/all-MiniLM-L6-v2")
        return FastEmbedModelAdapter(model_name="sentence-transformers/all-MiniLM-L6-v2")

    try:
        from sentence_transformers import SentenceTransformer
        model_name = "all-MiniLM-L6-v2"
        logger.info(f"Loading SentenceTransformer singleton model: {model_name}")
        try:
            return SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            return SentenceTransformer(model_name)
    except ImportError:
        raise ImportError("Neither 'fastembed' nor 'sentence-transformers' is installed.")

@lru_cache(maxsize=2048)
def _encode_text_cached(expanded_text: str) -> tuple:
    """Encodes a single expanded text string into a normalized embedding tuple (hashable for lru_cache)."""
    model = get_embedding_model()
    vec = model.encode(expanded_text, convert_to_numpy=True, normalize_embeddings=True)
    return tuple(vec)

class EmbeddingEngine:
    """
    Computes dense semantic similarity matrices between candidate skills and market requirements.
    Uses in-memory LRU vector caching to avoid repeated neural network forward passes.
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
            return ACRONYM_EXPANSIONS[clean]
            
        return raw_skill.strip()

    @lru_cache(maxsize=2048)
    def _encode_single(self, text: str) -> np.ndarray:
        """
        LRU-cached single string encoding.
        Converts hashable tuple from internal cache to numpy ndarray in O(1).
        """
        expanded = self.expand_skill_text(text)
        cached_tuple = _encode_text_cached(expanded)
        return np.array(cached_tuple, dtype=np.float32)

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

        student_vectors = np.vstack([self._encode_single(s) for s in student_skills])
        market_vectors = np.vstack([self._encode_single(m) for m in market_skills])

        similarity_matrix = cosine_similarity(student_vectors, market_vectors)
        return similarity_matrix

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """
        Computes cosine similarity between two arbitrary texts (e.g. for semantic role alignment).
        """
        if not text_a or not text_b:
            return 0.0
        vec_a = self._encode_single(text_a)
        vec_b = self._encode_single(text_b)
        return float(np.dot(vec_a, vec_b))
