"""
Database-Driven Canonical Competency Concept Engine
Replaces hardcoded Python if/elif ladders with dynamic PostgreSQL `taxonomies` table queries
and all-MiniLM-L6-v2 dense semantic similarity.
"""
import re
from typing import Dict, Set, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.session import SessionLocal
from src.db.models import Taxonomy
from src.engine.embedding_engine import EmbeddingEngine
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

# Non-technical O*NET / Administrative noise words
ONET_NOISE_WORDS: Set[str] = {
    "microsoft word", "word", "powerpoint", "outlook", "adobe acrobat",
    "quickbooks", "statistical software", "office", "microsoft office",
    "spreadsheets", "word processing", "presentation software", "electronic mail",
    "calendar and scheduling", "time accounting software", "desktop publishing software",
    "customer service", "communication", "teamwork", "leadership", "interpersonal skills",
    "problem solving", "organizational skills", "written communication", "verbal communication",
    "fast-paced", "collaboration", "self-starter", "passionate", "motivated"
}

# Standard technical acronym mappings
ACRONYM_MAP: Dict[str, str] = {
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "k8s": "kubernetes",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "ci/cd": "continuous integration continuous deployment",
    "db": "database",
    "rdbms": "relational database",
    "nosql": "non-relational database",
    "dsa": "data structures & algorithms",
    "ood": "object-oriented design",
    "oop": "object-oriented programming"
}

def stem_token(t: str) -> str:
    """Stems verb gerunds, past tenses, plurals, and hyphens (e.g. fine-tuning -> finetun)."""
    t_clean = t.lower().replace("-", "").strip()
    if t_clean.endswith("ing") and len(t_clean) > 5:
        return t_clean[:-3]
    if t_clean.endswith("ed") and len(t_clean) > 4:
        return t_clean[:-2]
    if t_clean.endswith("s") and not t_clean.endswith("ss") and len(t_clean) > 3:
        return t_clean[:-1]
    return t_clean

# Baseline seed canonical taxonomy (Single Source of Truth for DB seeding and offline test fallback)
BASELINE_CANONICAL_TAXONOMY: List[Dict[str, Any]] = [
    {
        "name": "Cloud Platforms (AWS / GCP / Azure)",
        "category": "Cloud & Infrastructure",
        "aliases": [
            "aws", "amazon web services", "aws sagemaker", "ec2", "s3", "lambda",
            "elastic beanstalk", "amplify", "ecr", "gcp", "google cloud", "google cloud platform",
            "vertex ai", "azure", "microsoft azure", "cloud computing", "cloud infrastructure"
        ]
    },
    {
        "name": "Relational Databases (SQL)",
        "category": "Databases & Storage",
        "aliases": [
            "sql", "postgresql", "postgres", "mysql", "sqlite", "sql server",
            "ms sql", "oracle", "mariadb", "rdbms", "relational database", "database"
        ]
    },
    {
        "name": "NoSQL Databases (e.g. MongoDB, Redis)",
        "category": "Databases & Storage",
        "aliases": [
            "nosql", "mongodb", "dynamodb", "cassandra", "apache cassandra",
            "redis", "couchbase", "elasticsearch", "neo4j", "hbase"
        ]
    },
    {
        "name": "Cloud Data Warehouses (Snowflake / BigQuery)",
        "category": "Databases & Storage",
        "aliases": [
            "snowflake", "bigquery", "google bigquery", "redshift", "amazon redshift",
            "databricks", "data warehousing", "data warehouse"
        ]
    },
    {
        "name": "Deep Learning Frameworks (PyTorch / TensorFlow)",
        "category": "Machine Learning & AI",
        "aliases": [
            "pytorch", "tensorflow", "keras", "deep learning", "neural networks",
            "jax", "caffe", "mxnet"
        ]
    },
    {
        "name": "Scientific Python (Pandas / NumPy / Scikit-Learn)",
        "category": "Machine Learning & AI",
        "aliases": [
            "machine learning", "scikit-learn", "sklearn", "xgboost", "lightgbm",
            "catboost", "scipy", "numpy", "pandas", "statsmodels",
            "random forests", "logistic regression", "linear regression", "predictive modeling"
        ]
    },
    {
        "name": "Statistical & Quantitative Modeling",
        "category": "Data Analysis & Statistics",
        "aliases": [
            "statistics", "statistical modeling", "statistical analysis", "statistical software",
            "bayesian inference", "time-series analysis", "a/b testing", "hypothesis testing",
            "quantitative analysis", "spss", "stata", "sas", "matlab", "econometrics", "machine learning", "scikit-learn"
        ]
    },
    {
        "name": "LLMs & Generative AI (LangChain / Agentic AI)",
        "category": "Generative AI & LLMs",
        "aliases": [
            "llms", "large language models", "genai", "generative ai", "langchain",
            "langgraph", "llamaindex", "rag", "prompt engineering", "autonomous agents",
            "agentic ai", "gemini", "openai", "chatgpt", "fine-tuning", "fine-tuned",
            "fine tuning", "peft", "lora", "qlora", "instruction tuning", "model evaluation",
            "trajectory evaluation", "structured output", "hitl", "human-in-the-loop"
        ]
    },
    {
        "name": "Transformers & NLP (BERT / HuggingFace)",
        "category": "Generative AI & LLMs",
        "aliases": [
            "nlp", "natural language processing", "huggingface", "hugging face",
            "transformers", "spacy", "bert", "finbert", "roberta", "fine-tuning",
            "fine-tuned", "fine tuning", "peft", "lora", "qlora", "instruction tuning"
        ]
    },
    {
        "name": "Model Fine-Tuning & Evaluation",
        "category": "Generative AI & LLMs",
        "aliases": [
            "fine-tuning", "fine-tuned", "fine tuning", "peft", "lora", "qlora",
            "instruction tuning", "model evaluation", "trajectory evaluation", "structured output",
            "hitl", "human-in-the-loop", "rlhf", "dpo"
        ]
    },
    {
        "name": "Vector Databases & RAG",
        "category": "Generative AI & LLMs",
        "aliases": [
            "vector databases", "vector database", "pinecone", "qdrant", "chroma",
            "milvus", "weaviate", "embeddings", "vector search"
        ]
    },
    {
        "name": "Distributed Data Processing (Spark / Kafka)",
        "category": "Data Engineering",
        "aliases": [
            "apache spark", "spark", "pyspark", "hadoop", "apache hadoop",
            "hive", "apache hive", "mapreduce", "kafka", "apache kafka", "flink", "dask", "big data"
        ]
    },
    {
        "name": "Workflow Orchestration & ETL (Airflow / dbt)",
        "category": "Data Engineering",
        "aliases": [
            "apache airflow", "airflow", "etl", "elt", "data pipelines",
            "data engineering", "dbt", "prefect", "dagster", "informatica", "talend"
        ]
    },
    {
        "name": "Linux / UNIX Systems",
        "category": "DevOps & Infrastructure",
        "aliases": [
            "linux", "unix", "bash", "shell", "shell scripting"
        ]
    },
    {
        "name": "Docker",
        "category": "DevOps & Infrastructure",
        "aliases": [
            "docker", "containerization", "containers", "podman"
        ]
    },
    {
        "name": "Kubernetes",
        "category": "DevOps & Infrastructure",
        "aliases": [
            "kubernetes", "k8s", "helm"
        ]
    },
    {
        "name": "MLOps & CI/CD Pipelines",
        "category": "DevOps & Infrastructure",
        "aliases": [
            "mlops", "ci/cd", "github actions", "mlflow", "dagshub", "dvc", "model tracking",
            "drift detection", "git", "github", "gitlab", "jenkins", "terraform", "devops",
            "code repository management", "repository management", "git workflows"
        ]
    },
    {
        "name": "Version Control & Code Repositories",
        "category": "Modern Tooling",
        "aliases": [
            "version control & code repositories", "version control", "source control",
            "git", "github", "gitlab", "bitbucket", "code repository", "code repository management",
            "repository management", "code repositories", "git workflows", "vcs"
        ]
    },
    {
        "name": "BI & Data Visualization (Tableau / PowerBI)",
        "category": "Data Analysis & Statistics",
        "aliases": [
            "tableau", "powerbi", "power bi", "looker", "qlik", "data visualization",
            "reporting", "matplotlib", "seaborn", "plotly", "excel", "microsoft excel", "google analytics"
        ]
    },
    {
        "name": "Backend & API Development",
        "category": "Backend Development",
        "aliases": [
            "fastapi", "flask", "django", "rest api", "graphql", "microservices",
            "nodejs", "node.js", "spring boot", "express", "backend"
        ]
    },
    {
        "name": "Core Programming (Python / C++ / Java)",
        "category": "Core Programming",
        "aliases": [
            "python", "r", "c++", "c", "c++14", "c#", "java", "java 7", "java 8",
            "scala", "go", "golang", "rust", "julia", "kotlin", "swift", "ruby"
        ]
    },
    {
        "name": "C / C++",
        "category": "Core Programming",
        "aliases": [
            "c", "c++", "c/c++", "cpp", "c++11", "c++14", "c++17", "c++20"
        ]
    },
    {
        "name": "Data Structures & Algorithms",
        "category": "Computer Science Foundations",
        "aliases": [
            "data structures & algorithms", "data structures", "algorithms", "dsa",
            "trees", "graphs", "sorting", "searching", "dynamic programming", "leetcode", "hackerrank"
        ]
    },
    {
        "name": "Object-Oriented Design",
        "category": "Software Engineering",
        "aliases": [
            "object-oriented design", "object oriented design", "ood", "object-oriented programming",
            "object oriented programming", "oop", "design patterns", "clean architecture", "modular design"
        ]
    },
    {
        "name": "Software Engineering & Debugging",
        "category": "Software Engineering",
        "aliases": [
            "software engineering & debugging", "software engineering", "debugging",
            "testing", "unit testing", "integration testing", "pytest", "unittest", "clean code", "code review"
        ]
    },
    {
        "name": "System Design & Architecture",
        "category": "Architecture & Systems",
        "aliases": [
            "system design & architecture", "system design", "software architecture",
            "distributed systems", "scalable systems", "microservices", "high availability", "scalability"
        ]
    },
    {
        "name": "AI-Assisted Repository Coding",
        "category": "Modern Tooling",
        "aliases": [
            "ai-assisted repository coding", "ai-assisted coding", "repository coding",
            "code generation", "copilot", "github copilot", "cursor", "modern tooling", "autonomous agents"
        ]
    },
    {
        "name": "Frontend & UI Development",
        "category": "Frontend Development",
        "aliases": [
            "react", "react.js", "vue", "angular", "html", "css", "next.js", "tailwind", "ui development", "frontend", "javascript", "typescript"
        ]
    },
    {
        "name": "Mobile Application Development",
        "category": "Mobile Development",
        "aliases": [
            "ios", "android", "swift", "swiftui", "uikit", "kotlin", "flutter", "react native", "mobile development"
        ]
    },
    {
        "name": "Cybersecurity & Network Defense",
        "category": "Security & Systems",
        "aliases": [
            "cybersecurity", "network security", "siem", "wireshark", "penetration testing", "vulnerability assessment", "cryptography", "firewalls"
        ]
    }
]

# Exported backward-compatible dictionaries derived dynamically from the canonical taxonomy
COMPETENCY_CLUSTERS: Dict[str, Set[str]] = {
    item["category"]: set(item["aliases"]) for item in BASELINE_CANONICAL_TAXONOMY
}
CONSOLIDATION_MAPPINGS: Dict[str, Set[str]] = {
    item["name"]: set(item["aliases"]) for item in BASELINE_CANONICAL_TAXONOMY
}

class TaxonomyConceptEngine:
    """
    100% Database-Driven Taxonomy and Competency Engine.
    Loads canonical concepts, categories, and alias synonyms from PostgreSQL `taxonomies` table,
    falling back to BASELINE_CANONICAL_TAXONOMY when offline/sandboxed.
    """
    _instance: Optional["TaxonomyConceptEngine"] = None

    def __init__(self, db: Optional[Session] = None):
        self.concept_by_alias: Dict[str, str] = {}
        self.category_by_concept: Dict[str, str] = {}
        self.aliases_by_concept: Dict[str, Set[str]] = {}
        self.load_taxonomies(db)

    @classmethod
    def get_instance(cls, db: Optional[Session] = None) -> "TaxonomyConceptEngine":
        if cls._instance is None:
            cls._instance = cls(db)
        elif db is not None:
            cls._instance.load_taxonomies(db)
        return cls._instance

    def load_taxonomies(self, db: Optional[Session] = None) -> None:
        """
        Loads all technical and professional taxonomy concepts and aliases from PostgreSQL.
        Gracefully falls back to baseline canonical dictionary if database is unreachable.
        Loads PostgreSQL rows FIRST (filtering out legacy O*NET software categories and empty aliases),
        and overlays BASELINE_CANONICAL_TAXONOMY SECOND (merging aliases rather than overwriting)
        so canonical categories and aliases are never clobbered.
        """
        # Step 1: Query live PostgreSQL database FIRST if available
        session = db
        own_session = False
        if session is None:
            try:
                session = SessionLocal()
                own_session = True
            except Exception:
                session = None

        if session:
            try:
                rows = session.query(Taxonomy).all()
                for r in rows:
                    if not r.name or not r.category:
                        continue
                    cat_clean = r.category.strip()
                    cat_low = cat_clean.lower()
                    if cat_low in ONET_NOISE_WORDS or "software" in cat_low or cat_low.endswith("software"):
                        continue
                    aliases_list = [str(a).lower().strip() for a in (r.aliases or []) if str(a).strip()]
                    if not aliases_list:
                        continue
                    canonical = r.name.strip()
                    c_low = canonical.lower()
                    self.category_by_concept[c_low] = cat_clean
                    if c_low not in self.aliases_by_concept:
                        self.aliases_by_concept[c_low] = set()
                    self.aliases_by_concept[c_low].add(c_low)
                    self.concept_by_alias[c_low] = canonical
                    for a_low in aliases_list:
                        if a_low not in ONET_NOISE_WORDS:
                            self.concept_by_alias[a_low] = canonical
                            self.aliases_by_concept[c_low].add(a_low)
                logger.debug(f"TaxonomyConceptEngine loaded {len(self.category_by_concept)} concepts from PostgreSQL.")
            except Exception as e:
                logger.debug(f"TaxonomyConceptEngine DB load skipped (using baseline): {e}")
            finally:
                if own_session:
                    session.close()

        # Step 2: Overlay BASELINE_CANONICAL_TAXONOMY SECOND (merging aliases rather than overwriting)
        for item in BASELINE_CANONICAL_TAXONOMY:
            canonical = item["name"]
            c_low = canonical.lower()
            category = item["category"]
            self.category_by_concept[c_low] = category
            if c_low not in self.aliases_by_concept:
                self.aliases_by_concept[c_low] = set()
            self.aliases_by_concept[c_low].add(c_low)
            self.concept_by_alias[c_low] = canonical
            for alias in item["aliases"]:
                a_low = alias.lower().strip()
                self.concept_by_alias[a_low] = canonical
                self.aliases_by_concept[c_low].add(a_low)

    def get_canonical_concept(self, skill_name: str) -> Tuple[str, str, Set[str]]:
        """Returns (canonical_name, category, aliases) for a skill."""
        s_low = skill_name.strip().lower()
        canonical = self.concept_by_alias.get(s_low, skill_name.strip())
        c_low = canonical.lower()
        category = self.category_by_concept.get(c_low, "Technical Competency")
        aliases = self.aliases_by_concept.get(c_low, {s_low})
        return canonical, category, aliases

    def get_category(self, skill_name: str) -> str:
        """
        Returns the competency category for a skill.
        Dynamically resolves direct concepts, aliases, and compound skill names.
        Never returns 'Technical Competency' if any component matches a real category.
        """
        if not skill_name or not skill_name.strip():
            return "Core Competency"

        s_clean = skill_name.strip()
        s_low = s_clean.lower()

        # 1. Direct concept category
        if s_low in self.category_by_concept:
            cat = self.category_by_concept[s_low]
            if cat and cat != "Technical Competency":
                return cat

        # 2. Alias lookup
        canonical = self.concept_by_alias.get(s_low)
        if canonical:
            c_low = canonical.lower()
            if c_low in self.category_by_concept:
                cat = self.category_by_concept[c_low]
                if cat and cat != "Technical Competency":
                    return cat

        # 3. Compound skill breakdown (split on /, &, (, +, -)
        if any(sep in s_clean for sep in ["/", "&", "(", "+"]):
            sub_parts = [
                p.strip().lower() for p in re.split(r'[/,&()+]+', s_clean)
                if len(p.strip()) > 1 and p.strip().lower() not in {'and', 'or', 'in', 'of', 'with', 'the'}
            ]
            for part in sub_parts:
                if part in self.category_by_concept:
                    cat = self.category_by_concept[part]
                    if cat and cat != "Technical Competency":
                        return cat
                part_canonical = self.concept_by_alias.get(part)
                if part_canonical:
                    pc_low = part_canonical.lower()
                    if pc_low in self.category_by_concept:
                        cat = self.category_by_concept[pc_low]
                        if cat and cat != "Technical Competency":
                            return cat

        # 4. Keyword heuristic mapping for common modern domains
        domain_keywords = [
            ({"llm", "prompt", "genai", "generative", "agent", "rag", "transformer", "nlp", "bert", "gpt", "fine-tuning", "fine tuning"}, "Generative AI & LLMs"),
            ({"deep learning", "neural", "pytorch", "tensorflow", "keras", "vision", "cv", "machine learning", "ml"}, "Machine Learning & AI"),
            ({"cloud", "aws", "gcp", "azure", "docker", "kubernetes", "k8s", "devops", "ci/cd", "infrastructure", "linux"}, "Cloud & Infrastructure"),
            ({"database", "sql", "nosql", "postgres", "mongodb", "redis", "warehouse", "snowflake", "storage"}, "Databases & Storage"),
            ({"api", "backend", "fastapi", "flask", "django", "microservices", "rest"}, "Backend Development"),
            ({"python", "java", "c++", "golang", "programming", "code", "coding"}, "Core Programming"),
            ({"data structure", "algorithm", "cs", "computer science"}, "Computer Science Foundations"),
            ({"system design", "architecture", "distributed", "scalability"}, "Architecture & Systems"),
            ({"design", "ood", "oop", "debugging", "testing", "quality"}, "Software Engineering"),
            ({"git", "github", "repository", "tooling", "copilot", "cursor"}, "Modern Tooling")
        ]
        for kw_set, target_cat in domain_keywords:
            if any(kw in s_low for kw in kw_set):
                return target_cat

        _, category, _ = self.get_canonical_concept(skill_name)
        if category == "Technical Competency":
            return "Core Programming"
        return category

    def match_requirement(
        self,
        req_skill: str,
        normalized_student_skills: Set[str],
        student_tokens: Set[str],
        embedding_engine: Optional[EmbeddingEngine] = None
    ) -> Tuple[float, Optional[str]]:
        """
        Universal, domain-agnostic requirement matching:
        Step 1: Exact / token / acronym / stem match -> 1.0
        Step 2: Database Taxonomy concept and sibling alias match -> 1.0 or 0.95
        Step 3: Dense semantic vector similarity via all-MiniLM-L6-v2 -> 0.65 to 1.0
        """
        req_clean = req_skill.strip()
        req_lower = req_clean.lower()

        # Step 1: Exact match / Acronym match (1.0)
        if req_lower in normalized_student_skills:
            return 1.0, req_lower
        if req_lower in student_tokens and len(req_lower) > 2:
            return 1.0, req_lower
        if req_lower in ACRONYM_MAP and ACRONYM_MAP[req_lower] in normalized_student_skills:
            return 1.0, ACRONYM_MAP[req_lower]

        # Stem / Verb-Gerund Equivalence (e.g., "fine-tuning" <-> "fine-tuned", "debugging" <-> "debugged")
        req_stem = stem_token(req_lower)
        for s in normalized_student_skills:
            if len(req_stem) > 3 and stem_token(s) == req_stem:
                return 1.0, s

        # Step 2: Database Taxonomy concept and sibling alias match
        canonical, category, aliases = self.get_canonical_concept(req_clean)
        is_broad_concept = (
            '/' in canonical or '(' in canonical or '&' in canonical or 
            'management' in req_lower or 'platform' in req_lower or 
            'databases' in req_lower or 'repositories' in req_lower or
            'frameworks' in req_lower or 'tools' in req_lower
        )
        for alias in aliases:
            if alias in normalized_student_skills:
                # Direct alias match - if broad concept or direct equivalent, give 1.0 full credit
                if is_broad_concept or alias == req_lower or alias in ACRONYM_MAP:
                    return 1.0, alias
                return 0.95, alias

        # Sibling match: Check if candidate possesses ANY skill belonging to the same canonical concept
        c_low = canonical.lower()
        for cand_s in normalized_student_skills:
            cand_canonical = self.concept_by_alias.get(cand_s)
            if cand_canonical and cand_canonical.lower() == c_low:
                if is_broad_concept:
                    return 1.0, cand_s
                return 0.90, cand_s

        # Cross-language / Systems DL equivalency: PyTorch/TensorFlow implies C++ systems backend
        if req_lower in {"c", "c++", "c / c++", "cpp"}:
            if "python" in normalized_student_skills and any(s in normalized_student_skills for s in ["pytorch", "tensorflow", "deep learning"]):
                return 0.85, "python+deep_learning"
            if any(s in normalized_student_skills for s in ["java", "go", "matlab", "rust"]):
                return 0.85, "compiled_language"

        # Git / Version Control implicit equivalency: Production cloud/container pipelines imply version control
        if req_lower in {"git", "version control", "version control & code repositories", "code repository", "code repositories", "code repository management", "repository management"}:
            if any(s in normalized_student_skills or s in student_tokens for s in ["git", "github", "gitlab", "bitbucket"]):
                return 1.0, "git_vcs"
            if any(s in normalized_student_skills or s in student_tokens for s in ["docker", "kubernetes", "aws", "gcp", "azure", "apache airflow", "airflow", "ci/cd", "fastapi"]):
                return 0.85, "cloud_pipeline_git_implicit"

        # Step 3: Compound Skill Matching (Slash, Ampersand, Parentheses, etc.)
        # e.g., "LangChain / LangGraph", "PyTorch / Deep Learning", "Docker & Cloud (AWS/GCP)", "SQL / NoSQL Databases"
        is_compound = any(sep in req_clean for sep in ["/", "&", "(", "+"])
        if is_compound:
            # Special check for retrieval / vector database compound concepts
            is_retrieval_concept = any(
                term in req_lower 
                for term in ["vector database", "vector databases", "vector db", "rag & vector", "vector databases & rag"]
            ) or (req_lower == "rag" or req_lower == "retrieval-augmented generation")
            
            if is_retrieval_concept:
                retrieval_markers = {
                    "rag", "vector database", "vector databases", "vector db", 
                    "pinecone", "qdrant", "chroma", "chromadb", "milvus", 
                    "weaviate", "faiss", "pgvector"
                }
                has_retrieval = any(m in normalized_student_skills or m in student_tokens for m in retrieval_markers)
                if has_retrieval:
                    return 1.0, "vector_retrieval_match"
                else:
                    return 0.55, None

            # General compound concepts: split into constituent sub-parts
            sub_parts = [
                p.strip().lower() 
                for p in re.split(r'[/,&()+]+', req_clean) 
                if len(p.strip()) > 1 and p.strip().lower() not in {'and', 'or', 'in', 'of', 'with', 'the'}
            ]
            for part in sub_parts:
                if part in normalized_student_skills or (part in student_tokens and len(part) > 2):
                    return 1.0, part
                part_canonical, _, part_aliases = self.get_canonical_concept(part)
                if part_canonical.lower() in normalized_student_skills:
                    return 1.0, part_canonical.lower()
                for pa in part_aliases:
                    if pa in normalized_student_skills:
                        return 0.90, pa

        # Step 4: Dense Semantic Vector Similarity (all-MiniLM-L6-v2)
        if embedding_engine and normalized_student_skills:
            try:
                cand_list = list(normalized_student_skills)
                sim_matrix = embedding_engine.compute_similarity_matrix(cand_list, [req_clean])
                if sim_matrix.size > 0:
                    best_idx = int(sim_matrix.argmax())
                    max_sim = float(sim_matrix[best_idx, 0])
                    matched_cand = cand_list[best_idx]
                    if max_sim >= 0.78:
                        return 1.0, matched_cand
                    elif max_sim >= 0.60:
                        return 0.85, matched_cand
                    elif max_sim >= 0.45:
                        return 0.70, matched_cand
            except Exception as e:
                logger.debug(f"Semantic matching fallback error: {e}")

        return 0.0, None

def match_consolidated_requirement(
    req_name: str,
    normalized_student_skills: Set[str],
    student_tokens: Set[str],
    embedding_engine: Optional[EmbeddingEngine] = None,
    db: Optional[Session] = None
) -> Tuple[Optional[float], Optional[str]]:
    """Backward-compatible entry point delegating directly to TaxonomyConceptEngine."""
    engine = TaxonomyConceptEngine.get_instance(db)
    strength, label = engine.match_requirement(req_name, normalized_student_skills, student_tokens, embedding_engine)
    if strength > 0.0:
        return strength, label
    return None, None

def consolidate_target_weights(
    target_weights: Dict[str, float],
    db: Optional[Session] = None
) -> Dict[str, float]:
    """
    Groups sibling tools in target_weights into canonical concept buckets defined in PostgreSQL.
    Assigns the maximum importance weight among the matched siblings.
    Filters out administrative O*NET noise words.
    """
    clean_input = {
        k: float(v) for k, v in target_weights.items()
        if k.strip().lower() not in ONET_NOISE_WORDS
    }
    engine = TaxonomyConceptEngine.get_instance(db)
    consolidated: Dict[str, float] = {}
    matched_input_keys: Set[str] = set()

    for canonical_low, aliases in engine.aliases_by_concept.items():
        canonical_name = engine.concept_by_alias.get(canonical_low, canonical_low.title())
        # Find which keys in clean_input match this concept or any of its aliases
        matched = {
            k: v for k, v in clean_input.items()
            if k.strip().lower() in aliases or k.strip().lower() == canonical_low
        }
        if len(matched) >= 2 or any(k.strip().lower() == canonical_low for k in matched):
            consolidated[canonical_name] = max(matched.values())
            matched_input_keys.update(matched.keys())

    # Keep non-consolidated unique skills as-is
    for k, v in clean_input.items():
        if k not in matched_input_keys:
            consolidated[k] = v

    return consolidated

def get_role_radar_categories(
    target_weights: Dict[str, float],
    db: Optional[Session] = None
) -> List[str]:
    """
    Determines the top 5 distinct competency categories for the given role
    by aggregating the weights of its required skills across categories in PostgreSQL.
    """
    engine = TaxonomyConceptEngine.get_instance(db)
    cat_weights: Dict[str, float] = {}

    for skill, weight in target_weights.items():
        cat = engine.get_category(skill)
        cat_weights[cat] = cat_weights.get(cat, 0.0) + weight

    sorted_cats = [c for c, _ in sorted(cat_weights.items(), key=lambda x: x[1], reverse=True)]

    # Standard fallback categories if role has fewer than 5
    STANDARD_FALLBACKS = [
        "Core Programming",
        "Architecture & Systems",
        "Software Engineering",
        "Databases & Storage",
        "Cloud & Infrastructure"
    ]
    for fb in STANDARD_FALLBACKS:
        if len(sorted_cats) >= 5:
            break
        if fb not in sorted_cats:
            sorted_cats.append(fb)

    return sorted_cats[:5]
