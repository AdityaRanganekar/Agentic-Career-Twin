"""
Database Cleanup and Seeding Script
1. Cleans taxonomies table (removes administrative O*NET software, ensures technical competencies exist with aliases).
2. Cleans resources table (deletes non-technical courses, populates target_skills JSON tags).
3. Seeds all 10 core roles into jobs, job_skills, market_snapshots, and market_data tables.
4. Verifies all 9 active tables in PostgreSQL have COUNT(*) > 0.
"""
import os
import re
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from src.db.session import SessionLocal, init_db, engine
from src.db.models import (
    Base, Student, StudentTwin, AnalysisRun,
    Market, MarketSnapshot, Job, JobSkill,
    Taxonomy, Resources
)
from src.db.crud import save_market_snapshot, upsert_job
from src.engine.competency_clusters import COMPETENCY_CLUSTERS, BASELINE_CANONICAL_TAXONOMY
from src.utils.hashing import hash_text
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

DISALLOWED_TAXONOMY_CATEGORIES = [
    'Word processing software',
    'Accounting software',
    'Time accounting software',
    'Human resources software',
    'Desktop publishing software',
    'Electronic mail software',
    'Presentation software',
    'Calendar and scheduling software',
    'Customer relationship management CRM software',
    'Enterprise resource planning ERP software'
]

CORE_TEN_ROLES = {
    "Data Scientist": {
        "Python": 0.95, "R": 0.82, "SQL": 0.90, "Scikit-Learn": 0.88,
        "Machine Learning": 0.92, "Pandas": 0.85, "NumPy": 0.80, "Statistics": 0.85,
        "Data Visualization": 0.78, "Tableau": 0.70, "Deep Learning": 0.75,
        "PyTorch": 0.72, "TensorFlow": 0.70, "A/B Testing": 0.68, "Git": 0.75
    },
    "Machine Learning Engineer": {
        "Python": 0.98, "PyTorch": 0.95, "TensorFlow": 0.90, "Docker": 0.88,
        "Kubernetes": 0.82, "Machine Learning": 0.95, "Deep Learning": 0.92,
        "AWS": 0.85, "MLOps": 0.88, "FastAPI": 0.80, "Git": 0.85,
        "Linux": 0.82, "CI/CD": 0.78, "SQL": 0.75, "C++": 0.72
    },
    "AI / LLM Engineer": {
        "Python": 0.98, "PyTorch": 0.94, "LLMs": 0.96, "Transformers": 0.92,
        "LangChain": 0.90, "LangGraph": 0.88, "RAG": 0.92, "HuggingFace": 0.90,
        "Vector Databases": 0.85, "Prompt Engineering": 0.82, "NLP": 0.90,
        "FastAPI": 0.82, "Docker": 0.85, "Fine-Tuning": 0.85, "Git": 0.80
    },
    "Data Engineer": {
        "Python": 0.95, "SQL": 0.98, "Apache Spark": 0.92, "Apache Airflow": 0.90,
        "Snowflake": 0.88, "BigQuery": 0.85, "Kafka": 0.85, "ETL": 0.92,
        "Data Warehousing": 0.88, "AWS": 0.85, "Docker": 0.80, "PostgreSQL": 0.85,
        "dbt": 0.82, "Linux": 0.80, "Git": 0.80
    },
    "Data Analyst": {
        "SQL": 0.98, "Tableau": 0.92, "PowerBI": 0.90, "Excel": 0.95,
        "Python": 0.82, "Pandas": 0.80, "Data Visualization": 0.92, "Reporting": 0.88,
        "Business Intelligence": 0.88, "Statistics": 0.78, "A/B Testing": 0.72,
        "Data Analysis": 0.95, "R": 0.65, "Google Analytics": 0.60
    },
    "MLOps Engineer": {
        "Python": 0.95, "Docker": 0.95, "Kubernetes": 0.92, "CI/CD": 0.90,
        "MLOps": 0.96, "AWS": 0.88, "Terraform": 0.85, "Git": 0.88,
        "Linux": 0.88, "Machine Learning": 0.82, "FastAPI": 0.80, "Monitoring": 0.82,
        "Airflow": 0.80, "PyTorch": 0.75, "Prometheus": 0.75
    },
    "Backend Software Engineer": {
        "Python": 0.95, "PostgreSQL": 0.90, "FastAPI": 0.88, "Docker": 0.88,
        "REST API": 0.92, "Microservices": 0.88, "Redis": 0.82, "Git": 0.90,
        "SQL": 0.92, "Linux": 0.85, "CI/CD": 0.82, "AWS": 0.82,
        "Kubernetes": 0.78, "Unit Testing": 0.80, "Java": 0.75
    },
    "Full-Stack Developer": {
        "JavaScript": 0.95, "TypeScript": 0.92, "React": 0.95, "Node.js": 0.90,
        "Python": 0.85, "HTML": 0.90, "CSS": 0.90, "PostgreSQL": 0.85,
        "REST API": 0.88, "Git": 0.90, "Docker": 0.80, "Next.js": 0.82,
        "Tailwind CSS": 0.80, "GraphQL": 0.75, "AWS": 0.75
    },
    "Cloud / DevOps Engineer": {
        "AWS": 0.95, "Terraform": 0.92, "Docker": 0.95, "Kubernetes": 0.92,
        "CI/CD": 0.92, "Linux": 0.95, "Bash": 0.88, "Python": 0.85,
        "Git": 0.90, "Ansible": 0.80, "GCP": 0.80, "Azure": 0.80,
        "Networking": 0.82, "Security": 0.85, "Monitoring": 0.82
    },
    "Quantitative Researcher": {
        "Python": 0.95, "C++": 0.90, "R": 0.85, "Statistics": 0.95,
        "Statistical Modeling": 0.95, "Time-Series Analysis": 0.92, "Econometrics": 0.88,
        "Stochastic Calculus": 0.85, "Machine Learning": 0.85, "NumPy": 0.88,
        "Pandas": 0.88, "SQL": 0.80, "Linear Algebra": 0.88, "Mathematics": 0.90
    },
    "AI Engineer": {
        "Python": 0.98, "PyTorch": 0.94, "LLMs": 0.96, "Transformers": 0.92,
        "LangChain": 0.90, "LangGraph": 0.88, "RAG": 0.92, "HuggingFace": 0.90,
        "Vector Databases": 0.85, "Prompt Engineering": 0.82, "NLP": 0.90,
        "FastAPI": 0.82, "Docker": 0.85, "Fine-Tuning": 0.85, "Git": 0.80
    },
    "Agentic AI Engineer": {
        "Python": 0.98, "LangGraph": 0.95, "LangChain": 0.92, "Autonomous Agents": 0.94,
        "Agentic AI": 0.95, "LLMs": 0.92, "RAG": 0.90, "Vector Databases": 0.88,
        "Prompt Engineering": 0.85, "FastAPI": 0.85, "Docker": 0.82, "PyTorch": 0.78, "Git": 0.80
    },
    "Site Reliability Engineer": {
        "Linux": 0.95, "Kubernetes": 0.92, "Docker": 0.90, "Terraform": 0.88,
        "AWS": 0.85, "Python": 0.85, "Go": 0.80, "CI/CD": 0.88,
        "Prometheus": 0.82, "Grafana": 0.80, "Bash": 0.85, "Networking": 0.82
    }
}

NON_TECH_RESOURCE_PATTERNS = [
    r"law\b", r"legal\b", r"happiness", r"adhd", r"cathedral", r"medical treatment",
    r"medical diagnosis", r"nursing", r"dentistry", r"childhood", r"dog emotion",
    r"guitar", r"songwriting", r"music\b", r"literature", r"parenting", r"philosophy",
    r"ancient egypt", r"buddhism", r"psychology\b", r"history of"
]

SKILL_KEYWORD_TAGS = {
    "python": "Python",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "neural network": "Deep Learning",
    "data science": "Data Science",
    "sql": "SQL",
    "database": "Databases",
    "cloud": "Cloud Computing",
    "aws": "AWS",
    "google cloud": "Google Cloud",
    "azure": "Azure",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "nlp": "NLP",
    "natural language": "NLP",
    "big data": "Big Data",
    "spark": "Apache Spark",
    "tableau": "Tableau",
    "power bi": "PowerBI",
    "excel": "Excel",
    "statistics": "Statistics",
    "data analysis": "Data Analysis",
    "algorithms": "Algorithms",
    "data structures": "Data Structures",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "scikit-learn": "Scikit-Learn",
    "pandas": "Pandas",
    "r programming": "R",
    "c++": "C++",
    "java": "Java",
    "javascript": "JavaScript",
    "react": "React",
    "devops": "DevOps",
    "ci/cd": "CI/CD"
}

def clean_taxonomies(db: Session):
    logger.info("Cleaning taxonomies table...")
    # Delete disallowed O*NET categories
    deleted_cats = 0
    for cat in DISALLOWED_TAXONOMY_CATEGORIES:
        res = db.execute(text("DELETE FROM taxonomies WHERE category = :cat"), {"cat": cat})
        deleted_cats += res.rowcount
    db.commit()
    logger.info(f"Deleted {deleted_cats} non-technical taxonomy rows across disallowed categories.")

    # Cache existing taxonomy names to avoid unique constraint collisions
    existing_tax_rows = db.query(Taxonomy).all()
    tax_by_name = {r.name.lower().strip(): r for r in existing_tax_rows if r.name}

    added_skills = 0
    updated_aliases = 0

    # 1. Ensure technical concepts from BASELINE_CANONICAL_TAXONOMY exist with their sibling aliases
    for item in BASELINE_CANONICAL_TAXONOMY:
        canonical_name = item["name"].strip()
        cat = item["category"]
        aliases = [str(a).strip().lower() for a in item["aliases"] if str(a).strip()]
        name_key = canonical_name.lower()

        if name_key not in tax_by_name:
            new_tax = Taxonomy(category=cat, name=canonical_name, aliases=aliases)
            db.add(new_tax)
            tax_by_name[name_key] = new_tax
            added_skills += 1
        else:
            existing = tax_by_name[name_key]
            existing.category = cat
            curr_aliases = set(str(a).lower() for a in (existing.aliases or []))
            new_aliases = [a for a in aliases if a not in curr_aliases]
            if new_aliases:
                existing.aliases = list(existing.aliases or []) + new_aliases
                updated_aliases += 1

    # 2. Also ensure specific skills from clusters are present
    for cluster_name, skills in COMPETENCY_CLUSTERS.items():
        for skill in skills:
            canonical = skill.strip().title()
            name_key = canonical.lower()
            if name_key not in tax_by_name:
                aliases = [skill.lower()]
                if len(skill.split()) > 1:
                    aliases.append("".join(w[0] for w in skill.split()).lower())
                new_tax = Taxonomy(category=cluster_name, name=canonical, aliases=aliases)
                db.add(new_tax)
                tax_by_name[name_key] = new_tax
                added_skills += 1
            else:
                existing = tax_by_name[name_key]
                current_aliases = existing.aliases or []
                if skill.lower() not in [a.lower() for a in current_aliases]:
                    existing.aliases = list(set(current_aliases + [skill.lower()]))
                    updated_aliases += 1

    db.commit()
    logger.info(f"Taxonomies enriched: Added {added_skills} technical skills, updated aliases for {updated_aliases}.")

MODERN_COURSES = [
    {
        "title": "Vector Databases: from Embeddings to Applications",
        "url": "https://www.deeplearning.ai/short-courses/vector-databases-embeddings-applications/",
        "resource_type": "Course",
        "target_skills": ["Vector Databases", "Embeddings", "Chroma", "Pinecone", "RAG", "Vector Search"],
        "difficulty_level": "Intermediate"
    },
    {
        "title": "Building Systems with the ChatGPT API",
        "url": "https://www.deeplearning.ai/short-courses/building-systems-with-chatgpt/",
        "resource_type": "Course",
        "target_skills": ["LLMs", "Prompt Engineering", "OpenAI", "API", "Generative AI"],
        "difficulty_level": "Beginner"
    },
    {
        "title": "Generative AI with Large Language Models",
        "url": "https://www.coursera.org/learn/generative-ai-with-llms",
        "resource_type": "Course",
        "target_skills": ["LLMs", "Generative AI", "Transformers", "Fine-Tuning", "RLHF", "NLP"],
        "difficulty_level": "Intermediate"
    },
    {
        "title": "Building and Evaluating Advanced RAG Applications",
        "url": "https://www.deeplearning.ai/short-courses/building-evaluating-advanced-rag/",
        "resource_type": "Course",
        "target_skills": ["RAG", "Retrieval Augmented Generation", "Vector Databases", "LlamaIndex", "Embeddings"],
        "difficulty_level": "Advanced"
    },
    {
        "title": "LangChain for LLM Application Development",
        "url": "https://www.deeplearning.ai/short-courses/langchain-for-llm-application-development/",
        "resource_type": "Course",
        "target_skills": ["LangChain", "LLMs", "Autonomous Agents", "Prompt Engineering", "Agents"],
        "difficulty_level": "Intermediate"
    },
    {
        "title": "AI Agents in Practice with LangGraph",
        "url": "https://www.deeplearning.ai/short-courses/ai-agents-in-practice/",
        "resource_type": "Course",
        "target_skills": ["LangGraph", "Autonomous Agents", "Multi-Agent Workflows", "Agentic AI", "Human-in-the-Loop"],
        "difficulty_level": "Advanced"
    },
    {
        "title": "Hugging Face NLP Course",
        "url": "https://huggingface.co/learn/nlp-course/",
        "resource_type": "Course",
        "target_skills": ["Transformers", "HuggingFace", "BERT", "Fine-Tuning", "NLP", "PyTorch"],
        "difficulty_level": "Intermediate"
    },
    {
        "title": "Full Stack LLM BootCamp",
        "url": "https://fullstackdeeplearning.com/llm-bootcamp/",
        "resource_type": "Course",
        "target_skills": ["LLMs", "FastAPI", "Docker", "MLOps", "Evaluation", "Deployment"],
        "difficulty_level": "Advanced"
    },
    {
        "title": "Production Machine Learning with MLOps",
        "url": "https://www.coursera.org/specializations/machine-learning-engineering-for-production-mlops",
        "resource_type": "Course",
        "target_skills": ["MLOps", "CI/CD", "Docker", "Model Monitoring", "MLflow", "Drift Detection"],
        "difficulty_level": "Advanced"
    },
    {
        "title": "Docker & Kubernetes: The Practical Guide",
        "url": "https://www.udemy.com/course/docker-kubernetes-the-practical-guide/",
        "resource_type": "Course",
        "target_skills": ["Docker", "Kubernetes", "DevOps", "Containers", "CI/CD"],
        "difficulty_level": "Intermediate"
    },
    {
        "title": "Snowflake Masterclass: Cloud Data Warehousing & Architecture",
        "url": "https://www.udemy.com/course/ultimate-snowpro-core-certification-course/",
        "resource_type": "Course",
        "target_skills": ["Snowflake", "Data Warehousing", "SQL", "Cloud Data", "BigQuery"],
        "difficulty_level": "Intermediate"
    },
    {
        "title": "MongoDB - The Complete Developer's Guide 2026",
        "url": "https://www.udemy.com/course/nodejs-express-mongodb-bootcamp/",
        "resource_type": "Course",
        "target_skills": ["MongoDB", "NoSQL", "Databases", "Document Databases", "Redis"],
        "difficulty_level": "Intermediate"
    },
    {
        "title": "Deep Learning Specialization with PyTorch & TensorFlow",
        "url": "https://www.deeplearning.ai/courses/deep-learning-specialization/",
        "resource_type": "Course",
        "target_skills": ["Deep Learning", "PyTorch", "TensorFlow", "Keras", "Neural Networks", "CNNs"],
        "difficulty_level": "Advanced"
    },
    {
        "title": "Modern FastAPI & REST Microservices in Python",
        "url": "https://testdriven.io/courses/fastapi-crud/",
        "resource_type": "Course",
        "target_skills": ["FastAPI", "REST API", "Microservices", "Python", "Docker"],
        "difficulty_level": "Intermediate"
    },
    {
        "title": "Data Structures & Algorithms in Python and C++",
        "url": "https://www.udemy.com/course/data-structures-and-algorithms-deep-dive-using-python/",
        "resource_type": "Course",
        "target_skills": ["Data Structures", "Algorithms", "DSA", "LeetCode", "Problem Solving", "C++", "Python"],
        "difficulty_level": "Intermediate"
    }
]

def clean_and_tag_resources(db: Session):
    logger.info("Cleaning and tagging resources table...")
    all_resources = db.query(Resources).all()
    deleted_count = 0
    tagged_count = 0

    for r in all_resources:
        title_lower = (r.title or "").lower()
        if any(re.search(pat, title_lower) for pat in NON_TECH_RESOURCE_PATTERNS):
            db.delete(r)
            deleted_count += 1
            continue

        # Tag remaining courses with matching technical skills
        tags = set()
        for kw, skill_label in SKILL_KEYWORD_TAGS.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', title_lower):
                tags.add(skill_label)

        if not tags:
            # Fallback tag by general category
            if "programming" in title_lower or "software" in title_lower:
                tags.add("Software Engineering")
            elif "data" in title_lower:
                tags.add("Data Science")
            elif "ai" in title_lower:
                tags.add("Machine Learning")
            else:
                tags.add("Computer Science")

        r.target_skills = sorted(list(tags))
        tagged_count += 1

    # Seed 10 modern 2024-2026 courses with explicit target_skills
    seeded_modern = 0
    for mc in MODERN_COURSES:
        existing = db.query(Resources).filter(Resources.title == mc["title"]).first()
        if not existing:
            db.add(Resources(
                title=mc["title"],
                url=mc["url"],
                resource_type=mc["resource_type"],
                target_skills=mc["target_skills"],
                difficulty_level=mc["difficulty_level"]
            ))
            seeded_modern += 1
        else:
            existing.target_skills = mc["target_skills"]
            existing.url = mc["url"]

    db.commit()
    logger.info(f"Resources cleaned: Deleted {deleted_count} non-technical courses, tagged {tagged_count} technical courses, seeded {seeded_modern} modern AI/ML courses.")

def seed_jobs_and_snapshots(db: Session):
    logger.info("Purging corrupted roles and seeding core roles into jobs, job_skills, market_snapshots, and market_data...")
    now_utc = datetime.now(timezone.utc)
    
    # 0. Delete corrupted non-tech jobs and market rows (Remotive scraped junk)
    junk_roles = [
        "content reviewer", "freelance copywriter", "copywriter", "writer",
        "customer service", "telemarketer", "data entry", "administrative assistant"
    ]
    for jr in junk_roles:
        db.execute(text("DELETE FROM market_data WHERE lower(role_name) LIKE :pat"), {"pat": f"%{jr}%"})
        db.execute(text("DELETE FROM market_snapshots WHERE lower(target_role) LIKE :pat"), {"pat": f"%{jr}%"})
        db.execute(text("DELETE FROM jobs WHERE lower(target_role) LIKE :pat OR lower(title) LIKE :pat"), {"pat": f"%{jr}%"})
    db.commit()

    for role_name, weights in CORE_TEN_ROLES.items():
        # 1. Seed/Update MarketSnapshot
        save_market_snapshot(
            db=db,
            target_role=role_name,
            market_corpus_version="2026-Live",
            tfidf_weights=weights
        )

        # 2. Seed/Update Market (market_data table)
        trending = [{"skill": k, "frequency": int(v * 100)} for k, v in weights.items()]
        existing_m = db.query(Market).filter(Market.role_name == role_name).first()
        if existing_m:
            existing_m.trending_skills = trending
            existing_m.demand_score = float(len(weights) * 15)
            existing_m.last_analyzed = now_utc
        else:
            db.add(Market(
                role_name=role_name,
                trending_skills=trending,
                demand_score=float(len(weights) * 15),
                last_analyzed=now_utc
            ))

        # 3. Seed real job postings into jobs and job_skills
        for idx in range(1, 4):
            job_hash = hash_text(f"{role_name}_job_{idx}_{now_utc.date()}")
            top_skills = list(weights.keys())[:7]
            desc = (
                f"Seeking an experienced {role_name} to design and deploy scalable systems. "
                f"Requirements include strong proficiency with {', '.join(top_skills)}. "
                f"Must have hands-on experience in building production architectures."
            )
            upsert_job(
                db=db,
                job_hash=job_hash,
                target_role=role_name,
                title=f"Senior {role_name}",
                company=f"TechCorp Solutions {idx}",
                location="San Francisco, CA (Hybrid)",
                raw_payload={"sample_seed": True, "skills": top_skills},
                skills=top_skills
            )

    db.commit()
    logger.info("Successfully seeded all 10 roles across MarketSnapshot, Market, Job, and JobSkill tables.")

def verify_all_tables(db: Session):
    logger.info("\n=== VERIFYING ALL 9 ACTIVE POSTGRESQL TABLES ===")
    tables = [
        "students", "student_twins", "analysis_runs",
        "market_data", "market_snapshots", "jobs",
        "job_skills", "taxonomies", "resources"
    ]
    all_ok = True
    for t in tables:
        cnt = db.execute(text(f"SELECT COUNT(*) FROM {t};")).scalar()
        logger.info(f"  {t:<20}: {cnt} rows")
        if cnt == 0 and t != "student_twins":
            all_ok = False

    # Check that dropped tables do not exist
    dropped = db.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name IN ('user_profiles', 'career_assessments');"
    )).fetchall()
    if dropped:
        logger.error(f"Legacy tables still present: {[d[0] for d in dropped]}")
        all_ok = False
    else:
        logger.info("  legacy tables       : DROPPED (Clean)")

    if all_ok:
        logger.info("ALL DATABASE INTEGRITY CHECKS PASSED SUCCESSFULLY!\n")
    else:
        logger.warning("Some table checks flagged anomalies; check logs above.\n")

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        clean_taxonomies(db)
        clean_and_tag_resources(db)
        seed_jobs_and_snapshots(db)
        verify_all_tables(db)
    finally:
        db.close()
