import re
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Set
from sqlalchemy.orm import Session

from src.domain.state import CareerTwinState
from src.domain.schemas import StudentTwinProfile
from src.engine.competency_clusters import (
    TaxonomyConceptEngine,
    consolidate_target_weights,
    get_role_radar_categories,
    ONET_NOISE_WORDS
)
from src.engine.readiness_scorer import ReadinessScorer
from src.engine.embedding_engine import EmbeddingEngine
from src.engine.project_evaluator import (
    evaluate_projects_and_proof,
    compute_skill_evidence_multiplier
)
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

FULL_CREDIT_THRESHOLD: float = 0.85
PARTIAL_CREDIT_THRESHOLD: float = 0.70

NOISE_WORDS = ONET_NOISE_WORDS

def resolve_best_date(current_date: Optional[str], new_date: Optional[str]) -> str:
    """Selects the most recent valid completion/evidence date."""
    if not new_date or str(new_date).strip().lower() in {"unknown", "none", ""}:
        return current_date or "Unknown"
    clean_new = str(new_date).strip().lower()
    if clean_new in {"present", "current"} or "2026" in clean_new or "2025" in clean_new:
        return "Present"
    if not current_date or str(current_date).strip().lower() in {"unknown", "none", ""}:
        return str(new_date).strip()
    clean_cur = str(current_date).strip().lower()
    if clean_cur in {"present", "current"} or "2026" in clean_cur or "2025" in clean_cur:
        return "Present"
    return max(str(current_date).strip(), str(new_date).strip())

def calculate_dynamic_seniority_modifier(
    profile: StudentTwinProfile,
    target_role: str,
    target_weights: Dict[str, float],
    embedding_engine: EmbeddingEngine,
    project_quality_score: float = 75.0,
    coverage_score: float = 0.0
) -> float:
    """
    Computes a 100% domain-agnostic, mathematically grounded seniority modifier combining:
    1. Semantic Role Alignment: Cosine similarity between candidate concise profile and target role profile
    2. Direct Skill Coverage: Direct coverage of required competencies across domain
    3. Practical Seniority: Degree credentials, seniority titles, experience and project rigor
    Zero hardcoded strings ('retail', 'cisco', 'quant', etc.).
    """
    if not profile:
        return 0.30

    exp_roles = " ".join([e.role.lower() for e in (profile.experience or [])])
    
    # High-signal concise candidate summary
    roles_and_project_titles = ", ".join(
        [e.role for e in (profile.experience or [])] + 
        [p.title for p in (profile.projects or [])]
    )
    skill_names = [s.skill_name for s in (profile.extracted_skills or [])]
    candidate_summary = f"Roles & Projects: {roles_and_project_titles}. Core Competencies: {', '.join(skill_names[:20])}".strip()
    if not candidate_summary:
        return 0.30

    # Target role profile vector text
    target_skill_names = list(target_weights.keys())[:10]
    target_intent = f"Target Role: {target_role}. Core competencies: {', '.join(target_skill_names)}"

    # Semantic cosine similarity between concise profile and target role
    semantic_sim = embedding_engine.compute_similarity(candidate_summary, target_intent)

    num_exp = len(profile.experience or [])
    num_proj = len(profile.projects or [])

    # Seniority title and degree credentials signals (universal across all fields)
    is_senior_title = any(
        kw in exp_roles
        for kw in ["senior", "lead", "principal", "staff", "architect", "head", "director", "manager"]
    )
    has_masters_or_phd = any(
        any(kw in ed.degree.lower() for kw in ["m.s", "master", "ph.d", "phd", "doctorate", "m.sc"])
        for ed in (profile.education or [])
    ) or any(
        kw in (getattr(profile, "raw_resume_text", "") or "").lower()
        for kw in ["doctoral dissertation", "ph.d", "phd", "doctorate", "doctoral"]
    )
    has_bachelor = any(
        any(kw in ed.degree.lower() for kw in ["b.s", "bachelor", "b.tech", "b.e", "bs ", "b.a"])
        for ed in (profile.education or [])
    )

    # 1. Unrelated domain background (e.g. Retail Store Manager targeting Data Scientist: sim < 0.25, cov < 25)
    if coverage_score < 25.0 and semantic_sim < 0.25:
        if has_masters_or_phd:
            return 0.35
        return max(0.10, round(semantic_sim * 1.2, 2))

    # 2. Low / Adjacent technical relevance (e.g. Network Admin targeting Data Scientist: sim < 0.35, cov < 55)
    if coverage_score < 55.0 and semantic_sim < 0.35:
        base = 0.45 + (semantic_sim - 0.18) * 0.8
        return round(min(0.58, max(0.45, base)), 2)

    # 3. Relevant domain (coverage_score >= 55.0 OR semantic_sim >= 0.35)
    # Project modifier (reward high-impact, verified projects across all disciplines)
    if num_proj >= 2:
        if project_quality_score >= 80.0:
            proj_modifier = 0.95
        elif project_quality_score >= 60.0:
            proj_modifier = 0.85
        else:
            proj_modifier = 0.72
    elif num_proj == 1:
        proj_modifier = 0.68
    else:
        proj_modifier = 0.50 if has_bachelor else 0.40

    # Professional practitioners / Interns / Working Candidates
    if num_exp >= 2:
        exp_modifier = 1.00 if (is_senior_title or has_masters_or_phd) else 0.95
        return max(exp_modifier, proj_modifier)
    elif num_exp == 1:
        exp_modifier = 0.90 if (is_senior_title or has_masters_or_phd) else 0.82
        return max(exp_modifier, proj_modifier)
    else:
        # Student / Entry / Recent Graduate (num_exp == 0)
        return proj_modifier

def compute_radar_dimensions(
    target_weights: Dict[str, float],
    student_skills: Optional[Set[str]] = None,
    student_profile: Optional[StudentTwinProfile] = None,
    embedding_engine: Optional[EmbeddingEngine] = None,
    db: Optional[Session] = None,
    is_jd: bool = False,
    fixed_categories: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Computes authentic category competency scores (0-100%) across the Top 5 dynamic categories
    for the specific role being evaluated. No hardcoded 'ML / Deep Learning' or 'Data Engineering' axes!
    Uses fixed_categories if provided to ensure Market and JD radar share identical axes.
    """
    categories = fixed_categories if fixed_categories else get_role_radar_categories(target_weights, db=db)
    engine = TaxonomyConceptEngine.get_instance(db)
    scores: Dict[str, float] = {}

    normalized_student_skills: Set[str] = set()
    student_tokens: Set[str] = set()

    if student_profile:
        for s in (student_profile.extracted_skills or []):
            if s.skill_name:
                normalized_student_skills.add(s.skill_name.strip().lower())
        for p in (student_profile.projects or []):
            for word in re.findall(r'[a-zA-Z0-9_#+.-]+', f"{p.title} {p.description}"):
                w_low = word.lower().strip()
                if len(w_low) > 1 and w_low not in NOISE_WORDS:
                    normalized_student_skills.add(w_low)
        for e in (student_profile.experience or []):
            for word in re.findall(r'[a-zA-Z0-9_#+.-]+', f"{e.role} {e.company} {e.description}"):
                w_low = word.lower().strip()
                if len(w_low) > 1 and w_low not in NOISE_WORDS:
                    normalized_student_skills.add(w_low)
    elif student_skills:
        for s in student_skills:
            if s:
                normalized_student_skills.add(str(s).strip().lower())

    for s in normalized_student_skills:
        tokens = re.split(r'[\s/|,-]+', s)
        student_tokens.update([t for t in tokens if len(t) > 1])

    # Group target role skills by category
    skills_by_cat: Dict[str, List[Tuple[str, float]]] = {c: [] for c in categories}
    for skill, weight in target_weights.items():
        cat = engine.get_category(skill)
        if cat in skills_by_cat:
            skills_by_cat[cat].append((skill, weight))
        else:
            # Check if any category matches partially or assign to primary category
            matched_cat = None
            for c in categories:
                if c.lower() in cat.lower() or cat.lower() in c.lower():
                    matched_cat = c
                    break
            if matched_cat:
                skills_by_cat[matched_cat].append((skill, weight))
            elif categories:
                skills_by_cat[categories[0]].append((skill, weight))

    max_cat_weight = max([sum(w for _, w in v) for v in skills_by_cat.values()] or [1.0])

    for cat in categories:
        cat_items = skills_by_cat.get(cat, [])
        cat_total_weight = sum(w for _, w in cat_items)
        if cat_total_weight == 0:
            scores[cat] = 60.0 if is_jd else 0.0
            continue

        if is_jd:
            # JD requirement footprint across the role's 5 axes:
            # Concentrated categories get 85-98%, unmentioned categories floor at 60.0%
            dim_score = min(98.0, round(65.0 + (cat_total_weight / max_cat_weight) * 33.0, 1))
            scores[cat] = max(60.0, dim_score)
        else:
            # Candidate competency in this category
            earned = 0.0
            for skill_name, weight in cat_items:
                strength, _ = engine.match_requirement(
                    skill_name,
                    normalized_student_skills,
                    student_tokens,
                    embedding_engine
                )
                earned += weight * strength

            dim_score = min(98.0, round((earned / cat_total_weight) * 100.0, 1))
            scores[cat] = dim_score

    return scores

def evaluate_skill_coverage(
    student_profile: StudentTwinProfile,
    target_weights: Dict[str, float],
    embedding_engine: EmbeddingEngine,
    target_role: str = "Data Scientist",
    max_skills: int = 15,
    filter_noise: bool = True,
    db: Optional[Session] = None
) -> Tuple[float, List[str]]:
    """
    Two-Tier Hybrid Matching Architecture combining:
    - Tier 1: Exact / Token / Acronym match (1.0)
    - Tier 2: Database Taxonomy Concept & Sibling Alias Lookup (0.90 - 1.0)
    - Tier 3: Dense Semantic Vector Similarity (0.65 - 1.0)
    """
    clean_weights = {}
    for skill, weight in target_weights.items():
        if filter_noise and skill.lower() in NOISE_WORDS:
            continue
        clean_weights[skill] = weight

    # Pre-scoring requirement consolidation into canonical competency concept buckets via PostgreSQL
    clean_weights = consolidate_target_weights(clean_weights, db=db)

    if not clean_weights:
        return 0.0, []

    sorted_reqs = dict(
        sorted(clean_weights.items(), key=lambda item: item[1], reverse=True)[:max_skills]
    )
    req_names = list(sorted_reqs.keys())

    student_skills_list = [skill.skill_name for skill in student_profile.extracted_skills]
    normalized_student_skills = {s.lower() for s in student_skills_list}

    # Build student_skill_dates preserving the most recent date
    student_skill_dates: Dict[str, str] = {}
    for skill in student_profile.extracted_skills:
        k = skill.skill_name.strip().lower()
        student_skill_dates[k] = resolve_best_date(student_skill_dates.get(k), skill.evidence_date)

    # Mine skills and tokens from projects & experience narratives
    for p in (student_profile.projects or []):
        proj_text = f"{p.title} {p.description}"
        p_date = getattr(p, "completion_date", "Present") or "Present"
        for word in re.findall(r'[a-zA-Z0-9_#+.-]+', proj_text):
            w_low = word.lower().strip()
            if len(w_low) > 1 and w_low not in NOISE_WORDS:
                normalized_student_skills.add(w_low)
                student_skill_dates[w_low] = resolve_best_date(student_skill_dates.get(w_low), p_date)

    for e in (student_profile.experience or []):
        exp_text = f"{e.role} {e.company} {e.description}"
        e_date = getattr(e, "end_date", "Present") or "Present"
        for word in re.findall(r'[a-zA-Z0-9_#+.-]+', exp_text):
            w_low = word.lower().strip()
            if len(w_low) > 1 and w_low not in NOISE_WORDS:
                normalized_student_skills.add(w_low)
                student_skill_dates[w_low] = resolve_best_date(student_skill_dates.get(w_low), e_date)

    # Check if candidate has an active current role or recent 2025/2026/Present project
    has_current_role = False
    if student_profile.experience:
        for exp in student_profile.experience:
            end = str(exp.end_date).strip().lower()
            if end in {"present", "current"} or "2026" in end or "2025" in end:
                has_current_role = True
                break
    if not has_current_role and student_profile.projects:
        for p in student_profile.projects:
            p_date = str(getattr(p, "completion_date", "") or "").strip().lower()
            if p_date in {"present", "current"} or "2026" in p_date or "2025" in p_date:
                has_current_role = True
                break
    if not has_current_role and getattr(student_profile, "raw_resume_text", ""):
        resume_raw_lower = student_profile.raw_resume_text.lower()
        if "present" in resume_raw_lower or "2025" in resume_raw_lower or "2026" in resume_raw_lower:
            has_current_role = True

    decay_floor = 0.80 if has_current_role else 0.0

    student_tokens = set()
    for s in normalized_student_skills:
        tokens = re.split(r'[\s/|,-]+', s)
        student_tokens.update([t for t in tokens if len(t) > 1])

    taxonomy_engine = TaxonomyConceptEngine.get_instance(db)
    student_skills_for_scorer = []
    missing_skills = []

    for req_skill in req_names:
        strength, matched_label = taxonomy_engine.match_requirement(
            req_skill,
            normalized_student_skills,
            student_tokens,
            embedding_engine
        )

        best_date = student_skill_dates.get((matched_label or req_skill).lower(), "Present")

        # Apply evidence verification multiplier (1.0 if demonstrated in projects/experience, 0.85 if keyword only)
        ev_mult = compute_skill_evidence_multiplier(req_skill, student_profile)
        if strength >= 0.85 and ev_mult >= 1.0:
            final_strength = strength
        elif ev_mult < 1.0 and strength > 0.0:
            final_strength = round(strength * 0.85, 4)
        else:
            final_strength = strength

        if final_strength >= 0.65:
            student_skills_for_scorer.append({
                "name": req_skill,
                "date": best_date,
                "strength": final_strength
            })
        else:
            missing_skills.append(req_skill)

    scorer = ReadinessScorer()
    coverage_score = scorer.calculate_role_readiness(
        student_skills_for_scorer,
        sorted_reqs,
        decay_floor=decay_floor
    )

    # 3-Pillar project and proof-of-work evaluation
    proof_eval = evaluate_projects_and_proof(
        student_profile,
        sorted_reqs,
        raw_resume_text=getattr(student_profile, "raw_resume_text", "")
    )
    project_quality_score = proof_eval["project_quality_score"]

    # Blend 75% concept skill coverage + 25% project & proof quality for candidates with projects/experience
    exp_roles = " ".join([e.role.lower() for e in (student_profile.experience or [])])
    is_senior_or_multi_exp = (
        len(student_profile.experience or []) >= 2
        or any(k in exp_roles for k in ["senior", "lead", "principal", "manager"])
    )
    if student_profile.projects or student_profile.experience:
        blended_calc = (0.75 * coverage_score) + (0.25 * project_quality_score)
        if is_senior_or_multi_exp and coverage_score >= 85.0:
            blended_raw = max(coverage_score, blended_calc)
        else:
            blended_raw = blended_calc
    else:
        blended_raw = coverage_score

    # Apply 100% domain-agnostic semantic seniority & domain relevance modifier
    seniority_scale = calculate_dynamic_seniority_modifier(
        profile=student_profile,
        target_role=target_role,
        target_weights=sorted_reqs,
        embedding_engine=embedding_engine,
        project_quality_score=project_quality_score,
        coverage_score=coverage_score
    )
    final_score = round(min(100.0, blended_raw * seniority_scale), 2)

    return final_score, missing_skills

def run_gap_agent(state: CareerTwinState, db: Optional[Session] = None) -> dict:
    """
    Evaluates candidate skills against:
    1. Broad market requirements (generating readiness_score, missing_skills, radar_dimensions)
    2. Specific Job Description requirements if provided (generating jd_fit_score, jd_missing_skills, jd_radar_dimensions)
    """
    logger.info("Gap Agent invoked with Database-Driven Taxonomy and Semantic Matching.")

    try:
        student_profile = state.get("student_profile")
        raw_market_weights = state.get("market_tf_idf_weights", {})
        target_role = state.get("target_role", "Data Scientist")

        if not student_profile or not raw_market_weights:
            return {"errors": state.get("errors", []) + ["Missing data for Gap Agent."]}

        embedding_engine = EmbeddingEngine()

        # 1. Market Readiness Evaluation
        readiness_score, market_missing = evaluate_skill_coverage(
            student_profile=student_profile,
            target_weights=raw_market_weights,
            embedding_engine=embedding_engine,
            target_role=target_role,
            max_skills=15,
            filter_noise=True,
            db=db
        )

        top_market_gaps = market_missing[:5]
        logger.info(f"Market Readiness Score: {readiness_score}%, Gaps: {len(top_market_gaps)}")

        # 2. Competency Radar Dimensions (Dynamic Top 5 Categories for this role)
        student_skills = {skill.skill_name for skill in (student_profile.extracted_skills or [])}
        role_categories = get_role_radar_categories(raw_market_weights, db=db)
        radar_dims = compute_radar_dimensions(
            target_weights=raw_market_weights,
            student_skills=student_skills,
            student_profile=student_profile,
            embedding_engine=embedding_engine,
            db=db,
            is_jd=False,
            fixed_categories=role_categories
        )

        # 3. Target Job Description (JD) Evaluation (Dual Scoring)
        jd_weights = state.get("jd_extracted_reqs")
        jd_fit_score = None
        top_jd_gaps = None
        jd_radar_dims = None

        if jd_weights:
            logger.info(f"Evaluating coverage against specific target JD ({len(jd_weights)} extracted skills).")
            jd_fit_score, jd_missing = evaluate_skill_coverage(
                student_profile=student_profile,
                target_weights=jd_weights,
                embedding_engine=embedding_engine,
                target_role=f"Custom JD: {target_role}",
                max_skills=25,
                filter_noise=False,
                db=db
            )
            top_jd_gaps = jd_missing[:5]
            jd_radar_dims = compute_radar_dimensions(
                target_weights=jd_weights,
                student_skills=set(jd_weights.keys()),
                student_profile=student_profile,
                embedding_engine=embedding_engine,
                db=db,
                is_jd=True,
                fixed_categories=role_categories
            )
            logger.info(f"Target JD Fit Score: {jd_fit_score}%, JD Gaps: {len(top_jd_gaps)}")

        proof_eval = evaluate_projects_and_proof(
            student_profile,
            raw_market_weights,
            raw_resume_text=getattr(student_profile, "raw_resume_text", "")
        )

        return {
            "readiness_score": readiness_score,
            "missing_skills": top_market_gaps,
            "jd_fit_score": jd_fit_score,
            "jd_missing_skills": top_jd_gaps,
            "radar_dimensions": radar_dims,
            "jd_radar_dimensions": jd_radar_dims,
            "resume_quality_breakdown": proof_eval["resume_quality_breakdown"],
            "project_quality_score": proof_eval["project_quality_score"]
        }

    except Exception as e:
        logger.error(f"Gap Agent failed: {str(e)}")
        return {"errors": state.get("errors", []) + [f"Gap analysis failed: {str(e)}"]}
