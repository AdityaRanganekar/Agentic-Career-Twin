"""
Sprint 8: Rolling window Cross-Role TF-IDF recalculation engine with small-sample safeguard.
"""
import os
import json
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from src.db.models import Market, MarketSnapshot, Job, JobSkill
from src.db.crud import save_market_snapshot
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

MINIMUM_CORPUS_THRESHOLD = 50
CACHE_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "jobs", "live_market_weights.json"
)

class MarketUpdater:
    """
    Recalculates Cross-Role TF-IDF weights from trailing 90-day live jobs in PostgreSQL,
    with an automatic fallback/blending safeguard against small-sample collapse.
    """
    def __init__(self, db: Session, rolling_days: int = 90, min_jobs_threshold: int = MINIMUM_CORPUS_THRESHOLD):
        self.db = db
        self.rolling_days = rolling_days
        self.min_jobs_threshold = min_jobs_threshold

    def get_live_job_counts(self) -> Dict[str, int]:
        """Counts jobs ingested within the rolling window grouped by target_role."""
        since_date = datetime.now(timezone.utc) - timedelta(days=self.rolling_days)
        jobs = self.db.query(Job).filter(Job.created_at >= since_date).all()
        counts = {}
        for j in jobs:
            counts[j.target_role] = counts.get(j.target_role, 0) + 1
        return counts

    def compute_cross_role_tfidf(
        self,
        role_skill_counts: Dict[str, Dict[str, int]],
        role_job_counts: Dict[str, int]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculates Cross-Role TF-IDF weights:
        TF(s, r) = count(s in r) / total_jobs(r)
        IDF(s) = log((N + 1) / (DF(s) + 1)) + 1
        TF-IDF(s, r) = TF(s, r) * IDF(s)
        """
        total_global_jobs = sum(role_job_counts.values())
        if total_global_jobs == 0:
            return {}

        # Global document frequency: number of jobs across all roles mentioning skill s
        global_df: Dict[str, int] = {}
        for role, skills in role_skill_counts.items():
            for skill, count in skills.items():
                global_df[skill] = global_df.get(skill, 0) + count

        weights: Dict[str, Dict[str, float]] = {}
        for role, skills in role_skill_counts.items():
            role_jobs = role_job_counts.get(role, 0)
            if role_jobs == 0:
                continue
            role_weights = {}
            for skill, count in skills.items():
                tf = count / role_jobs
                df = global_df.get(skill, 0)
                idf = math.log((total_global_jobs + 1) / (df + 1)) + 1
                role_weights[skill] = round(tf * idf, 4)
            weights[role] = role_weights

        return weights

    def update_market_weights(self) -> Dict[str, Dict[str, float]]:
        """
        Calculates new TF-IDF weights across live jobs. If live job count is below threshold,
        blends with the baseline Market records to prevent small-sample collapse.
        """
        since_date = datetime.now(timezone.utc) - timedelta(days=self.rolling_days)
        live_jobs = self.db.query(Job).filter(Job.created_at >= since_date).all()
        
        live_role_counts = {}
        live_skill_counts = {}
        for j in live_jobs:
            live_role_counts[j.target_role] = live_role_counts.get(j.target_role, 0) + 1
            if j.target_role not in live_skill_counts:
                live_skill_counts[j.target_role] = {}
            for js in j.skills:
                live_skill_counts[j.target_role][js.skill_name] = (
                    live_skill_counts[j.target_role].get(js.skill_name, 0) + 1
                )

        # Baseline market records
        baseline_markets = self.db.query(Market).all()
        baseline_role_counts = {m.role_name: int(m.demand_score or 0) for m in baseline_markets}
        baseline_skill_counts = {
            m.role_name: {item["skill"]: item["frequency"] for item in (m.trending_skills or [])}
            for m in baseline_markets
        }

        # Check if blending/fallback is needed
        blended_role_counts = {}
        blended_skill_counts = {}

        all_roles = set(list(baseline_role_counts.keys()) + list(live_role_counts.keys()))
        for role in all_roles:
            live_count = live_role_counts.get(role, 0)
            if live_count < self.min_jobs_threshold:
                # Small-sample safeguard: blend baseline + live
                logger.info(
                    f"Role '{role}' has {live_count} live jobs (< {self.min_jobs_threshold}). "
                    f"Blending with baseline corpus ({baseline_role_counts.get(role, 0)} jobs)."
                )
                blended_role_counts[role] = baseline_role_counts.get(role, 0) + live_count
                combined_skills = dict(baseline_skill_counts.get(role, {}))
                for skill, count in live_skill_counts.get(role, {}).items():
                    combined_skills[skill] = combined_skills.get(skill, 0) + count
                blended_skill_counts[role] = combined_skills
            else:
                blended_role_counts[role] = live_count
                blended_skill_counts[role] = live_skill_counts.get(role, {})

        computed_weights = self.compute_cross_role_tfidf(blended_skill_counts, blended_role_counts)

        # Save to PostgreSQL MarketSnapshot
        for role, weights in computed_weights.items():
            save_market_snapshot(
                db=self.db,
                target_role=role,
                market_corpus_version="2026-Live",
                tfidf_weights=weights
            )

        # Cache to local JSON fallback only if there are substantial weights (>= 10 skills)
        valid_to_cache = {r: w for r, w in computed_weights.items() if len(w) >= 10}
        if valid_to_cache:
            try:
                os.makedirs(os.path.dirname(CACHE_FILE_PATH), exist_ok=True)
                with open(CACHE_FILE_PATH, "w") as f:
                    json.dump(valid_to_cache, f, indent=2)
                logger.info(f"Cached live market weights to {CACHE_FILE_PATH}")
            except Exception as e:
                logger.warning(f"Could not write cache file {CACHE_FILE_PATH}: {str(e)}")

        return computed_weights

