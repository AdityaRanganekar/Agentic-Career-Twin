"""
Deduplication utility for candidate skill evidence and project records.
"""
from typing import List, Dict
from src.domain.schemas import SkillEvidence
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

class SkillDeduplicator:
    @staticmethod
    def _is_priority_one_date(date_str: str) -> bool:
        """Priority 1 (0 decay): Present, Current, Ongoing, 2026/2025, or Unknown."""
        if not date_str:
            return True
        clean = str(date_str).strip().lower()
        if clean in {"present", "current", "ongoing", "unknown", "none", ""}:
            return True
        if "2026" in clean or "2025" in clean:
            return True
        return False

    @classmethod
    def _pick_most_recent(cls, existing: SkillEvidence, new: SkillEvidence) -> SkillEvidence:
        ed = existing.evidence_date
        nd = new.evidence_date

        ex_p1 = cls._is_priority_one_date(ed)
        new_p1 = cls._is_priority_one_date(nd)

        # If existing is Priority 1 (0 decay) and new is older historical date, preserve Priority 1!
        if ex_p1 and not new_p1:
            return existing
        if new_p1 and not ex_p1:
            return new
        if ex_p1 and new_p1:
            if str(nd).strip().lower() in {"present", "current"}:
                return new
            return existing

        # Both are historical ISO dates: newest date wins
        if str(nd) > str(ed):
            return new
        return existing

    @classmethod
    def deduplicate_skills(cls, skills: List[SkillEvidence]) -> List[SkillEvidence]:
        """
        Deduplicates extracted skill evidence entries by canonical skill name.
        When duplicates occur, strictly preserves the entry with the most recent evidence date,
        never overwriting an active/recent (Priority 1) date with an older historical date.
        """
        seen: Dict[str, SkillEvidence] = {}
        for evidence in skills:
            key = evidence.skill_name.strip().lower()
            if key not in seen:
                seen[key] = evidence
            else:
                seen[key] = cls._pick_most_recent(seen[key], evidence)

        deduped = list(seen.values())
        logger.debug(f"Deduplicated {len(skills)} raw evidence items into {len(deduped)} unique skills.")
        return deduped

class JobDeduplicator:
    @staticmethod
    def compute_job_hash(company: str, title: str, location: str = "") -> str:
        """Computes a deterministic hash of company + normalized title + normalized location."""
        import hashlib
        norm = f"{company.strip().lower()}|{title.strip().lower()}|{location.strip().lower()}"
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    @classmethod
    def deduplicate_jobs(cls, jobs: List[dict]) -> List[dict]:
        """Deduplicates a list of raw job dictionaries by computed job hash."""
        seen = {}
        for job in jobs:
            c = job.get("company", "")
            t = job.get("title", "")
            l = job.get("location", "")
            h = job.get("job_hash") or cls.compute_job_hash(c, t, l)
            job["job_hash"] = h
            if h not in seen:
                seen[h] = job
        return list(seen.values())


