"""
Self-Caching Web Role Discovery Agent with TTL
Executes the Read-Through Cache + TTL workflow:
Student searches for Role -> Check PostgreSQL (Exact + Vector Similarity) & Check TTL ->
If missing or expired, search Live Internet/APIs + Extract Core Skills via Gemini ->
Save to DB with Timestamp -> Return Role Weights.
"""
import os
import re
import json
import yaml
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.models import Market, MarketSnapshot, Job, JobSkill, Taxonomy
from src.db.crud import save_market_snapshot, upsert_job
from src.engine.embedding_engine import EmbeddingEngine
from src.engine.competency_clusters import COMPETENCY_CLUSTERS, ONET_NOISE_WORDS, TaxonomyConceptEngine
from src.domain.schemas import RoleSkillProfile, WeightedSkill
from src.utils.scraper import JobMarketScraper
from src.llm.client import get_gemini_client
import google.generativeai as genai
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

DEFAULT_TTL_DAYS = 365

def get_configured_ttl_days(config_path: str = "config.yaml") -> int:
    """Reads role_cache_ttl_days from config.yaml, defaulting to 365 days."""
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                cfg = yaml.safe_load(f)
                return int(cfg.get("market", {}).get("role_cache_ttl_days", DEFAULT_TTL_DAYS))
    except Exception as e:
        logger.warning(f"Could not read TTL from {config_path}: {e}")
    return DEFAULT_TTL_DAYS

DOMAIN_ROLE_FALLBACKS: Dict[str, Dict[str, float]] = {
    "ai / llm engineer": {
        "Python": 0.98, "LLMs & Prompt Engineering": 0.95, "LangChain / LangGraph": 0.92,
        "RAG & Vector Databases": 0.90, "PyTorch / Deep Learning": 0.88, "Transformers & HuggingFace": 0.88,
        "FastAPI & REST APIs": 0.85, "Docker & Cloud (AWS/GCP)": 0.82, "SQL / NoSQL Databases": 0.78,
        "MLOps & Evaluation": 0.75, "Fine-Tuning": 0.85, "Git": 0.80
    },
    "ai engineer": {
        "Python": 0.98, "LLMs & Prompt Engineering": 0.95, "LangChain / LangGraph": 0.92,
        "RAG & Vector Databases": 0.90, "PyTorch / Deep Learning": 0.88, "Transformers & HuggingFace": 0.88,
        "FastAPI & REST APIs": 0.85, "Docker & Cloud (AWS/GCP)": 0.82, "SQL / NoSQL Databases": 0.78,
        "MLOps & Evaluation": 0.75, "Fine-Tuning": 0.85, "Git": 0.80
    },
    "agentic ai engineer": {
        "Python": 0.98, "LLMs & Prompt Engineering": 0.95, "LangChain / LangGraph": 0.95,
        "Autonomous Agents": 0.92, "RAG & Vector Databases": 0.90, "FastAPI & REST APIs": 0.88,
        "Docker & Cloud (AWS/GCP)": 0.85, "PyTorch / Deep Learning": 0.85, "Transformers & HuggingFace": 0.85,
        "MLOps & Evaluation": 0.78, "Git": 0.80
    },
    "site reliability engineer": {
        "Linux / UNIX Systems": 0.98, "Kubernetes & Docker": 0.95, "Cloud Platforms (AWS / GCP / Azure)": 0.95,
        "Terraform & IaC": 0.90, "CI/CD & GitHub Actions": 0.88, "Prometheus & Grafana Monitoring": 0.85,
        "Python / Go Scripting": 0.85, "Networking & Security": 0.80, "Bash": 0.82, "Git": 0.80
    },
    "machine learning engineer": {
        "Python": 0.98, "PyTorch": 0.95, "TensorFlow": 0.90, "Scikit-Learn": 0.92,
        "Docker": 0.88, "AWS": 0.85, "MLflow": 0.85, "SQL": 0.85, "CI/CD": 0.80, "Git": 0.80
    }
}

ROLE_SYNONYMS: Dict[str, str] = {
    "ml engineer": "Machine Learning Engineer",
    "mle": "Machine Learning Engineer",
    "machine learning engineer": "Machine Learning Engineer",
    "machine learning": "Machine Learning Engineer",
    "ai engineer": "AI / LLM Engineer",
    "llm engineer": "AI / LLM Engineer",
    "ai / llm engineer": "AI / LLM Engineer",
    "agentic ai engineer": "AI / LLM Engineer",
    "ds": "Data Scientist",
    "data science": "Data Scientist",
    "data scientist": "Data Scientist",
    "swe": "Backend Software Engineer",
    "sde": "Backend Software Engineer",
    "software engineer": "Backend Software Engineer",
    "software development engineer": "Backend Software Engineer",
    "backend engineer": "Backend Software Engineer",
    "backend software engineer": "Backend Software Engineer",
    "sre": "Site Reliability Engineer",
    "site reliability engineer": "Site Reliability Engineer",
}

def normalize_role_name(role: str) -> str:
    cleaned = (role or "").strip().lower()
    return ROLE_SYNONYMS.get(cleaned, (role or "").strip())

class RoleResearchAgent:
    """
    Manages self-caching market role discovery with semantic cache lookup and TTL expiration.
    """
    @staticmethod
    def find_cached_role_snapshot(
        db: Session,
        target_role: str,
        ttl_days: Optional[int] = None,
        force_refresh: bool = False
    ) -> Optional[Tuple[Dict[str, float], str]]:
        """
        Step A: Checks PostgreSQL for an exact or semantic match within the active TTL window.
        Returns (weights, market_corpus_version) on cache hit, or None on cache miss/expired TTL.
        """
        target_role = normalize_role_name(target_role)

        if force_refresh:
            logger.info(f"Force refresh requested for '{target_role}'; bypassing DB cache.")
            return None

        if ttl_days is None:
            ttl_days = get_configured_ttl_days()

        now_utc = datetime.now(timezone.utc)
        clean_role = target_role.strip().lower()

        # 1. Exact match in MarketSnapshot
        snapshots = db.query(MarketSnapshot).filter(
            func.lower(MarketSnapshot.target_role) == clean_role
        ).order_by(MarketSnapshot.timestamp.desc()).all()

        for snap in snapshots:
            if snap.tfidf_weights and len(snap.tfidf_weights) >= 8:
                snap_time = snap.timestamp
                if snap_time.tzinfo is None:
                    snap_time = snap_time.replace(tzinfo=timezone.utc)
                age_days = (now_utc - snap_time).days
                if age_days <= ttl_days:
                    version = f"DB-Cached ({snap.target_role}, {age_days}d old, TTL={ttl_days}d)"
                    logger.info(f"Cache HIT (Exact Snapshot): {version}")
                    return snap.tfidf_weights, version
                else:
                    logger.info(f"Cache EXPIRED for '{target_role}': Snapshot is {age_days}d old (TTL={ttl_days}d).")
                    return None

        # 2. Exact match in Market (market_data table)
        market_entry = db.query(Market).filter(
            func.lower(Market.role_name) == clean_role
        ).first()

        if market_entry and market_entry.trending_skills and len(market_entry.trending_skills) >= 8:
            m_time = market_entry.last_analyzed or now_utc
            if m_time.tzinfo is None:
                m_time = m_time.replace(tzinfo=timezone.utc)
            age_days = (now_utc - m_time).days
            if age_days <= ttl_days:
                # Convert trending_skills list to normalized weights
                max_freq = max(item.get("frequency", 1) for item in market_entry.trending_skills) or 1
                weights = {
                    item["skill"]: round(item.get("frequency", 1) / max_freq, 4)
                    for item in market_entry.trending_skills
                }
                version = f"DB-Cached ({market_entry.role_name}, {age_days}d old, TTL={ttl_days}d)"
                logger.info(f"Cache HIT (Exact Market): {version}")
                return weights, version

        # 3. Semantic similarity lookup across existing cached roles (cos_sim >= 0.88)
        all_snapshots = db.query(MarketSnapshot).all()
        all_markets = db.query(Market).all()
        available_roles = list({s.target_role for s in all_snapshots if s.target_role} | {m.role_name for m in all_markets if m.role_name})

        if available_roles:
            try:
                engine = EmbeddingEngine()
                target_vec = engine.model.encode([target_role], normalize_embeddings=True)
                cand_vecs = engine.model.encode(available_roles, normalize_embeddings=True)
                import numpy as np
                sims = np.dot(cand_vecs, target_vec.T).flatten()
                best_idx = int(np.argmax(sims))
                best_sim = float(sims[best_idx])
                best_role = available_roles[best_idx]

                if best_sim >= 0.88:
                    logger.info(f"Semantic Cache HIT: '{target_role}' matched '{best_role}' (cosine_sim={best_sim:.3f} >= 0.88)")
                    # Recursively fetch best_role without infinite loop
                    return RoleResearchAgent.find_cached_role_snapshot(
                        db=db,
                        target_role=best_role,
                        ttl_days=ttl_days,
                        force_refresh=False
                    )
            except Exception as sim_err:
                logger.warning(f"Semantic role lookup skipped: {sim_err}")

        logger.info(f"Cache MISS for role '{target_role}'. Triggering Live Internet Discovery.")
        return None

    @staticmethod
    def research_role_live(
        target_role: str,
        db: Session,
        max_jobs: int = 20
    ) -> Tuple[Dict[str, float], str]:
        """
        Step B: Scrapes live job listings and web snippets, extracts top core technical skills
        via Gemini, and persists the new profile to PostgreSQL with current timestamp.
        """
        target_role = normalize_role_name(target_role)
        logger.info(f"Executing Live Web Discovery for target role: '{target_role}'...")
        scraper = JobMarketScraper()
        jobs = scraper.scrape_role(target_role, max_jobs=max_jobs)

        # 1. Ingest scraped jobs into PostgreSQL jobs and job_skills tables
        known_tech_skills = set()
        for cluster_skills in COMPETENCY_CLUSTERS.values():
            known_tech_skills.update(cluster_skills)

        job_summaries = []
        for j in jobs:
            extracted_skills = scraper.extract_skills_from_text(j.get("description", ""), known_tech_skills)
            try:
                upsert_job(
                    db=db,
                    job_hash=j.get("job_hash", ""),
                    target_role=target_role,
                    title=j.get("title"),
                    company=j.get("company"),
                    location=j.get("location"),
                    raw_payload=j.get("raw_payload", {}),
                    skills=extracted_skills
                )
            except Exception as db_err:
                db.rollback()
                logger.warning(f"Could not persist job record: {db_err}")

            desc_snip = (j.get("description", "") or "")[:400]
            if desc_snip:
                job_summaries.append(f"Title: {j.get('title')} | Company: {j.get('company')}\nRequirements: {desc_snip}")

        # 2. Synthesize Top 12-15 Core Technical Skills via Gemini
        aggregated_context = "\n---\n".join(job_summaries[:15]) if job_summaries else f"Role: {target_role}"
        weights: Dict[str, float] = {}

        try:
            model = get_gemini_client()
            prompt = (
                f"You are an Expert Industry Recruiter and Labor Market Analyst across all professional domains and industries. "
                f"Analyze the following live job postings, market requirements, and industry standards for the role '{target_role}':\n\n"
                f"{aggregated_context}\n\n"
                f"Extract the TOP 10 to 15 MOST CRITICAL hard professional competencies, domain tools, software, platforms, methodologies, or qualifications required for '{target_role}'.\n"
                f"Rules:\n"
                f"1. Only include hard domain competencies, technical/professional tools, methodologies, and standards. Exclude generic soft skills, administrative fluff (e.g., 'communication', 'leadership', 'teamwork'), and generic buzzwords.\n"
                f"2. Group the skills into the TOP 5 distinct, clean, human-readable Competency Categories tailored specifically to this role (to serve as the 5 Radar Chart axes, e.g. for AI Engineer: 'Generative AI & LLMs', 'Machine Learning & AI', 'Cloud & MLOps', 'Backend & APIs', 'Databases & Storage'; for Financial Analyst: 'Financial Modeling & Valuation', 'Accounting & ERP Systems', 'Data & BI Analytics', 'Risk & Forecasting', 'Regulatory Compliance'; for Civil Engineer: 'Structural Analysis & Design', 'CAD & BIM Modeling', 'Geotechnical & Materials', 'Project Management & Estimation', 'Codes & Standards').\n"
                f"3. For each skill, specify 'category' (one of the 5 categories), 'importance_weight' (0.20 to 1.00 based on criticality and frequency), and 'equivalent_aliases' (a list of sibling tools, libraries, or frameworks that satisfy this competency in that industry).\n"
                f"4. Assign importance weight between 0.20 and 1.00.\n"
                f"5. Return the exact JSON schema."
            )
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=RoleSkillProfile,
                    temperature=0.1
                )
            )
            data = json.loads(response.text)
            profile = RoleSkillProfile(**data)
            for skill in profile.core_skills:
                name = skill.skill_name.strip()
                if name.lower() not in ONET_NOISE_WORDS and len(name) > 1:
                    weights[name] = round(float(skill.importance_weight), 4)

                    # Persist discovered skill, category, and aliases to PostgreSQL taxonomies table
                    try:
                        existing_tax = db.query(Taxonomy).filter(func.lower(Taxonomy.name) == name.lower()).first()
                        aliases = [str(a).strip() for a in (skill.equivalent_aliases or []) if str(a).strip()]
                        if existing_tax:
                            curr_aliases = set(str(a).lower() for a in (existing_tax.aliases or []))
                            new_aliases = [a for a in aliases if a.lower() not in curr_aliases]
                            if new_aliases:
                                existing_tax.aliases = list(existing_tax.aliases or []) + new_aliases
                        else:
                            db.add(Taxonomy(
                                name=name,
                                category=skill.category or "General Technical",
                                aliases=aliases
                            ))
                    except Exception as tax_err:
                        logger.warning(f"Could not persist taxonomy for '{name}': {tax_err}")

            try:
                db.commit()
                # Instantly refresh in-memory taxonomy engine
                TaxonomyConceptEngine.get_instance().load_taxonomies(db)
            except Exception as commit_tax_err:
                db.rollback()
                logger.warning(f"Could not commit taxonomy additions: {commit_tax_err}")

            logger.info(f"Gemini successfully synthesized {len(weights)} core skills for '{target_role}' and synced taxonomies.")
        except Exception as llm_err:
            logger.warning(f"Gemini live role synthesis fallback triggered: {llm_err}")

        # Fallback if Gemini or API unavailable: Domain-intelligent fallback or clean frequency count
        if len(weights) < 8:
            clean_role_lower = target_role.strip().lower()
            if clean_role_lower in DOMAIN_ROLE_FALLBACKS:
                logger.info(f"Using domain-intelligent curated fallback for role '{target_role}'.")
                weights = dict(DOMAIN_ROLE_FALLBACKS[clean_role_lower])
            else:
                for role_key, role_weights in DOMAIN_ROLE_FALLBACKS.items():
                    if role_key in clean_role_lower or clean_role_lower in role_key:
                        logger.info(f"Matched role '{target_role}' to domain fallback '{role_key}'.")
                        weights = dict(role_weights)
                        break

            if len(weights) < 8:
                logger.info("Using frequency aggregation fallback for live role weights.")
                counts: Dict[str, int] = {}
                for j in jobs:
                    for s in scraper.extract_skills_from_text(j.get("description", ""), known_tech_skills):
                        if s.lower() not in ONET_NOISE_WORDS and len(s) > 1:
                            counts[s] = counts.get(s, 0) + 1
                if counts:
                    max_c = max(counts.values()) or 1
                    for s, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:15]:
                        weights[s] = round(c / max_c, 4)

        # Final safety net for rare completely offline cases (Domain-agnostic dynamic generation)
        if len(weights) < 5:
            role_words = [w.capitalize() for w in re.findall(r'[a-zA-Z]+', target_role) if len(w) > 2 and w.lower() not in {'and', 'the', 'for', 'senior', 'junior', 'lead', 'staff'}]
            core_name = " ".join(role_words) if role_words else target_role.title()
            weights = {f"{core_name} Methodologies": 1.0}
            for w in role_words[:3]:
                weights[f"{w} Analysis & Execution"] = 0.85
                weights[f"{w} Tools & Standards"] = 0.80
            weights["Industry Quality & Standards"] = 0.75
            weights["Domain Reporting & Evaluation"] = 0.70

        # 3. Persist newly discovered role to BOTH MarketSnapshot and Market (market_data) tables
        now_utc = datetime.now(timezone.utc)
        corpus_version = "2026-Live-Web-Acquired (Saved to DB, TTL=365d)"
        try:
            save_market_snapshot(
                db=db,
                target_role=target_role,
                market_corpus_version=corpus_version,
                tfidf_weights=weights
            )

            trending = [{"skill": k, "frequency": int(v * 100)} for k, v in weights.items()]
            existing_market = db.query(Market).filter(
                func.lower(Market.role_name) == target_role.strip().lower()
            ).first()

            if existing_market:
                existing_market.trending_skills = trending
                existing_market.demand_score = float(len(jobs))
                existing_market.last_analyzed = now_utc
            else:
                new_m = Market(
                    role_name=target_role,
                    trending_skills=trending,
                    demand_score=float(len(jobs)),
                    last_analyzed=now_utc
                )
                db.add(new_m)
            db.commit()
            logger.info(f"Persisted live discovered role '{target_role}' to PostgreSQL MarketSnapshot and Market tables.")
        except Exception as persist_err:
            db.rollback()
            logger.error(f"Failed persisting live role to DB: {persist_err}")

        return weights, corpus_version

