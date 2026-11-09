import numpy as np
from typing import Optional, List, Dict
from sqlalchemy import func
from sqlalchemy.orm import Session
from src.db.models import Taxonomy
from src.engine.embedding_engine import EmbeddingEngine
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

VECTOR_FALLBACK_THRESHOLD = 0.82

TOOL_CANONICAL_CASING: Dict[str, str] = {
    "python": "Python", "py": "Python", "python3": "Python", "python 3": "Python",
    "r": "R", "c++": "C++", "cpp": "C++", "c": "C", "c#": "C#", "csharp": "C#",
    "java": "Java", "go": "Go", "golang": "Go", "rust": "Rust", "scala": "Scala",
    "javascript": "JavaScript", "js": "JavaScript", "typescript": "TypeScript", "ts": "TypeScript",
    "sql": "SQL", "mysql": "MySQL", "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "psql": "PostgreSQL",
    "sqlite": "SQLite", "oracle": "Oracle", "mssql": "MS SQL", "sql server": "SQL Server",
    "mongodb": "MongoDB", "mongo": "MongoDB", "redis": "Redis", "cassandra": "Cassandra",
    "elasticsearch": "Elasticsearch", "dynamodb": "DynamoDB", "neo4j": "Neo4j",
    "snowflake": "Snowflake", "bigquery": "BigQuery", "redshift": "Redshift", "databricks": "Databricks",
    "pytorch": "PyTorch", "torch": "PyTorch", "tensorflow": "TensorFlow", "tf": "TensorFlow",
    "keras": "Keras", "jax": "JAX", "scikit-learn": "Scikit-Learn", "sklearn": "Scikit-Learn",
    "pandas": "Pandas", "numpy": "NumPy", "scipy": "SciPy", "xgboost": "XGBoost", "lightgbm": "LightGBM",
    "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes", "terraform": "Terraform",
    "aws": "AWS", "gcp": "GCP", "azure": "Azure", "linux": "Linux", "unix": "UNIX", "git": "Git", "github": "GitHub",
    "fastapi": "FastAPI", "flask": "Flask", "django": "Django", "nodejs": "Node.js", "node.js": "Node.js", "node": "Node.js",
    "react": "React", "reactjs": "React", "react.js": "React", "angular": "Angular", "vue": "Vue",
    "nextjs": "Next.js", "next.js": "Next.js", "tailwind": "Tailwind CSS", "html": "HTML", "css": "CSS",
    "langchain": "LangChain", "langgraph": "LangGraph", "llamaindex": "LlamaIndex",
    "huggingface": "HuggingFace", "hugging face": "HuggingFace", "transformers": "Transformers", "bert": "BERT",
    "airflow": "Apache Airflow", "apache airflow": "Apache Airflow", "spark": "Apache Spark", "apache spark": "Apache Spark",
    "kafka": "Apache Kafka", "apache kafka": "Apache Kafka", "tableau": "Tableau", "powerbi": "PowerBI", "power bi": "PowerBI",
    "excel": "Excel", "dbt": "dbt", "mlflow": "MLflow", "dvc": "DVC", "dagshub": "DagsHub",
    "rag": "RAG", "pinecone": "Pinecone", "chroma": "ChromaDB", "chromadb": "ChromaDB", "qdrant": "Qdrant",
    "weaviate": "Weaviate", "milvus": "Milvus", "faiss": "FAISS", "pgvector": "pgvector"
}

class SkillNormalizer:
    # Class-level cache for taxonomy embeddings to avoid re-encoding on every resume
    _taxonomy_names: Optional[List[str]] = None
    _taxonomy_vectors: Optional[np.ndarray] = None
    _engine: Optional[EmbeddingEngine] = None

    def __init__(self, db: Session):
        self.db = db
        self._taxonomies: Optional[List[Taxonomy]] = None
        self._exact_map: Optional[Dict[str, Taxonomy]] = None
        self._alias_map: Optional[Dict[str, Taxonomy]] = None

    def _ensure_taxonomy_cache(self):
        if self._taxonomies is None:
            try:
                self._taxonomies = self.db.query(Taxonomy).all()
            except Exception as e:
                logger.warning(f"Failed to query taxonomies from DB: {e}")
                self._taxonomies = []
            self._exact_map = {t.name.strip().lower(): t for t in self._taxonomies if t.name}
            self._alias_map = {}
            for tax in self._taxonomies:
                if tax.aliases:
                    for a in tax.aliases:
                        a_clean = str(a).strip().lower()
                        if a_clean and a_clean not in self._alias_map:
                            self._alias_map[a_clean] = tax

    def _get_taxonomies(self) -> List[Taxonomy]:
        self._ensure_taxonomy_cache()
        return self._taxonomies

    def normalize(self, raw_skill: str) -> Optional[str]:
        """
        Executes the deterministic Waterfall normalization pipeline:
        1. Exact Match (O(1) in-memory lookup) against taxonomy
        2. Alias Dictionary Match (O(1) in-memory lookup) preserving tool identity
        3. Dense Vector Similarity Fallback (EmbeddingEngine with cosine similarity)
        """
        if not raw_skill or not raw_skill.strip():
            return None

        clean_skill = raw_skill.strip().lower()
        self._ensure_taxonomy_cache()

        # Step 1: Deterministic Exact Match (O(1) memory lookup)
        exact_match = self._exact_map.get(clean_skill)
        if exact_match:
            # If matched row is an umbrella bucket, do NOT replace raw_skill with umbrella name
            if '/' in exact_match.name or '(' in exact_match.name or '&' in exact_match.name:
                return TOOL_CANONICAL_CASING.get(clean_skill, raw_skill.strip())
            logger.debug(f"Exact match found: '{raw_skill}' -> '{exact_match.name}'")
            return exact_match.name
        
        # Step 2: Deterministic Alias Match (O(1) memory lookup)
        alias_match = self._alias_map.get(clean_skill)
        if alias_match:
            # If matched row is an umbrella bucket, return specific tool name, not umbrella name
            if '/' in alias_match.name or '(' in alias_match.name or '&' in alias_match.name:
                return TOOL_CANONICAL_CASING.get(clean_skill, raw_skill.strip())
            logger.debug(f"Alias match found: '{raw_skill}' -> '{alias_match.name}'")
            return alias_match.name

        # Step 3: Vector Similarity Fallback
        logger.debug(f"Skill '{raw_skill}' not found deterministically. Triggering vector fallback.")
        return self._vector_fallback(clean_skill, self._taxonomies)

    def _vector_fallback(self, clean_skill: str, taxonomies: List[Taxonomy]) -> Optional[str]:
        """
        Encodes the raw skill and computes cosine similarity against canonical taxonomy names.
        Filters out multi-tool umbrella buckets to avoid overwriting candidate skills.
        Returns the canonical name if similarity meets or exceeds VECTOR_FALLBACK_THRESHOLD (0.82).
        """
        # Restrict vector fallback targets to single-tool entities
        target_taxonomies = [
            t for t in taxonomies 
            if '/' not in t.name and '(' not in t.name and '&' not in t.name
        ]
        if not target_taxonomies:
            return None

        try:
            if SkillNormalizer._engine is None:
                SkillNormalizer._engine = EmbeddingEngine()

            tax_names = [t.name for t in target_taxonomies]

            # Re-encode only if taxonomy list in memory changed or not yet initialized
            if SkillNormalizer._taxonomy_names != tax_names:
                SkillNormalizer._taxonomy_names = tax_names
                expanded_tax = [SkillNormalizer._engine.expand_skill_text(name) for name in tax_names]
                SkillNormalizer._taxonomy_vectors = SkillNormalizer._engine.model.encode(
                    expanded_tax,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )

            # Encode query skill
            query_expanded = SkillNormalizer._engine.expand_skill_text(clean_skill)
            query_vector = SkillNormalizer._engine.model.encode(
                [query_expanded],
                convert_to_numpy=True,
                normalize_embeddings=True
            )

            # Cosine similarity is dot product of normalized vectors
            sims = np.dot(SkillNormalizer._taxonomy_vectors, query_vector.T).flatten()
            best_idx = int(np.argmax(sims))
            max_sim = float(sims[best_idx])

            if max_sim >= VECTOR_FALLBACK_THRESHOLD:
                canonical = tax_names[best_idx]
                logger.info(f"Vector Normalization Match: '{clean_skill}' -> '{canonical}' (sim={max_sim:.3f})")
                return canonical

            logger.debug(f"Vector fallback below threshold ({max_sim:.3f} < {VECTOR_FALLBACK_THRESHOLD}) for '{clean_skill}'")
            return None

        except Exception as e:
            logger.error(f"Vector fallback failed for skill '{clean_skill}': {e}")
            return None
