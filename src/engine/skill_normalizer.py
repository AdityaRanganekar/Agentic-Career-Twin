import numpy as np
from typing import Optional, List, Dict
from sqlalchemy import func
from sqlalchemy.orm import Session
from src.db.models import Taxonomy
from src.engine.embedding_engine import EmbeddingEngine
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

VECTOR_FALLBACK_THRESHOLD = 0.82

class SkillNormalizer:
    # Class-level cache for taxonomy embeddings to avoid re-encoding on every resume
    _taxonomy_names: Optional[List[str]] = None
    _taxonomy_vectors: Optional[np.ndarray] = None
    _engine: Optional[EmbeddingEngine] = None

    def __init__(self, db: Session):
        self.db = db

    def normalize(self, raw_skill: str) -> Optional[str]:
        """
        Executes the deterministic Waterfall normalization pipeline:
        1. Exact Match (case-insensitive)
        2. Alias Dictionary Match
        3. Dense Vector Similarity Fallback (EmbeddingEngine with cosine similarity)
        """
        if not raw_skill or not raw_skill.strip():
            return None

        clean_skill = raw_skill.strip().lower()

        # Step 1: Deterministic Exact Match
        exact_match = self.db.query(Taxonomy).filter(
            func.lower(Taxonomy.name) == clean_skill
        ).first()
        
        if exact_match:
            logger.debug(f"Exact match found: '{raw_skill}' -> '{exact_match.name}'")
            return exact_match.name
        
        # Step 2: Deterministic Alias Match
        all_taxonomies = self.db.query(Taxonomy).all()
        for tax in all_taxonomies:
            aliases = [str(a).strip().lower() for a in tax.aliases] if tax.aliases else []
            if clean_skill in aliases:
                logger.debug(f"Alias match found: '{raw_skill}' -> '{tax.name}'")
                return tax.name

        # Step 3: Vector Similarity Fallback
        logger.debug(f"Skill '{raw_skill}' not found deterministically. Triggering vector fallback.")
        return self._vector_fallback(clean_skill, all_taxonomies)

    def _vector_fallback(self, clean_skill: str, taxonomies: List[Taxonomy]) -> Optional[str]:
        """
        Encodes the raw skill and computes cosine similarity against canonical taxonomy names.
        Returns the canonical name if similarity meets or exceeds VECTOR_FALLBACK_THRESHOLD (0.85).
        """
        if not taxonomies:
            return None

        try:
            if SkillNormalizer._engine is None:
                SkillNormalizer._engine = EmbeddingEngine()

            tax_names = [t.name for t in taxonomies]

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
