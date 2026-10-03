from sqlalchemy import func
from sqlalchemy.orm import Session
from src.db.models import Taxonomy
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

class SkillNormalizer:
    def __init__(self, db: Session):
        self.db = db

    def normalize(self, raw_skill: str) -> str | None:
        """
        Executes the deterministic Waterfall normalization pipeline:
        Exact Match -> Alias Match -> Vector Similarity Fallback
        """
        clean_skill = raw_skill.strip().lower()

        exact_match = self.db.query(Taxonomy).filter(
            func.lower(Taxonomy.name) == clean_skill
        ).first()
        
        if exact_match:
            logger.debug(f"Exact match found: {raw_skill} -> {exact_match.name}")
            return exact_match.name
        
        all_taxonomies = self.db.query(Taxonomy).all()
        for tax in all_taxonomies:
            aliases = [str(a).strip().lower() for a in tax.aliases] if tax.aliases else []
            if clean_skill in aliases:
                logger.debug(f"Alias match found: {raw_skill} -> {tax.name}")
                return tax.name

        logger.warning(f"Skill '{raw_skill}' not found deterministically. Triggering pgvector fallback.")
        return self._vector_fallback(clean_skill)

    def _vector_fallback(self, raw_skill: str) -> str | None:
        """
        TODO: Embed the raw_skill using Gemini and query PostgreSQL 
        using cosine similarity against the Taxonomy vector column.
        """
        return None