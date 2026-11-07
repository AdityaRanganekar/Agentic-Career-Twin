"""
Self-Caching Web Role Discovery Agent with TTL
Executes the Read-Through Cache + TTL workflow:
Student searches for Role -> Check PostgreSQL (Exact + Vector Similarity) & Check TTL ->
If missing or expired, search Live Internet/APIs + Extract Core Skills via Gemini ->
Save to DB with Timestamp -> Return Role Weights.
"""
import os
import json
import yaml
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.models import Market, MarketSnapshot, Job, JobSkill
from src.db.crud import save_market_snapshot, upsert_job
from src.engine.embedding_engine import EmbeddingEngine
from src.engine.competency_clusters import COMPETENCY_CLUSTERS, ONET_NOISE_WORDS
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
                f"You are a Senior Technical Recruiter and Job Market Analyst. Analyze the following live job postings and requirements for the role '{target_role}':\n\n"
                f"{aggregated_context}\n\n"
                f"Extract the TOP 12 to 15 MOST CRITICAL hard technical skills, programming languages, databases, cloud platforms, and frameworks required for '{target_role}'.\n"
                f"Rules:\n"
                f"1. Only include hard technical skills. Exclude soft skills, administrative fluff (e.g., 'communication', 'leadership', 'teamwork'), and office tools.\n"
                f"2. Assign an importance weight between 0.20 and 1.00 based on market frequency and criticality.\n"
                f"3. Return the exact JSON schema."
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

            logger.info(f"Gemini successfully synthesized {len(weights)} core skills for '{target_role}'.")
        except Exception as llm_err:
            logger.warning(f"Gemini live role synthesis fallback triggered: {llm_err}")

        # Fallback if Gemini or API unavailable: Frequency count from scraped jobs or generic technical core
        if len(weights) < 8:
            logger.info("Using frequency aggregation fallback for live role weights.")
            counts: Dict[str, int] = {}
            for j in jobs:
                for s in scraper.extract_skills_from_text(j.get("description", ""), known_tech_skills):
                    counts[s] = counts.get(s, 0) + 1
            if counts:
                max_c = max(counts.values()) or 1
                for s, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:15]:
                    weights[s] = round(c / max_c, 4)

        # Final safety net for rare completely offline cases
        if len(weights) < 8:
            weights = {
                "Python": 1.0, "SQL": 0.85, "Git": 0.75, "Docker": 0.70,
                "Linux": 0.70, "Cloud Platforms (AWS / GCP / Azure)": 0.80,
                "Data Analysis": 0.65, "REST APIs": 0.60
            }

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

