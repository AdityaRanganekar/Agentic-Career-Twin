"""
Domain-Agnostic Human Resume & Project Evaluator
Evaluates engineering resumes across Skills, Projects, and Proof-of-Work.
Quantifies real metrics, verifiable links, structural engineering depth, and project-backed skill evidence
without hardcoding any role-specific or resume-specific keywords.
"""
import re
from typing import Dict, List, Any, Optional, Set
from src.domain.schemas import StudentTwinProfile
from src.engine.competency_clusters import TaxonomyConceptEngine, stem_token
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

# Universal technical action verbs across all engineering disciplines
TECHNICAL_ACTION_VERBS: Set[str] = {
    "designed", "built", "implemented", "deployed", "evaluated", "developed",
    "trained", "engineered", "architected", "optimized", "tested", "automated",
    "created", "integrated", "managed", "led", "refactored", "benchmarked",
    "scaled", "analyzed", "modeled", "configured", "maintained", "migrated"
}

# Universal proof & publication markers (Strictly verifiable URLs, repositories, and certifications)
UNIVERSAL_PROOF_PATTERNS = [
    r'https?://\S+',
    r'\b(?:github|gitlab|bitbucket|linkedin)\.com/\S+',
    r'\b(?:github|gitlab|dagshub|live url|video walkthrough|live demo|arxiv|pypi|dockerhub)\b',
    r'\b(?:certified|certification|hackerrank|oracle cloud|aws certified|coursera|udemy)\b'
]

def get_combined_project_and_exp_text(profile: StudentTwinProfile) -> str:
    """Concatenates all text from projects, experience, certifications, and experience/project-evidenced skills."""
    chunks = []
    if getattr(profile, "raw_resume_text", None):
        chunks.append(profile.raw_resume_text)
    if profile.projects:
        for p in profile.projects:
            chunks.append(f"{p.title} {p.description}")
    if profile.experience:
        for e in profile.experience:
            chunks.append(f"{e.role} {e.company} {e.description}")
    if profile.education:
        for ed in profile.education:
            chunks.append(f"{ed.degree} {ed.institution}")
    if profile.extracted_skills:
        for sk in profile.extracted_skills:
            if sk.evidence_type in {"Experience", "Project"} or (sk.source and "skills" not in sk.source.lower()):
                chunks.append(sk.skill_name)
    return " ".join(chunks)

def compute_skill_evidence_multiplier(skill_name: str, profile: StudentTwinProfile) -> float:
    """
    Checks if skill_name (or its synonyms/equivalents from the database taxonomy)
    is actively demonstrated inside a Project or Experience.
    Returns 1.00 if evidenced in projects/experience, 0.75 if only listed in skills section.
    """
    if not profile:
        return 0.75

    clean_skill = skill_name.strip().lower()

    # 1. If extracted with evidence_type 'Experience' or 'Project'
    for sk in (profile.extracted_skills or []):
        if sk.skill_name.strip().lower() == clean_skill:
            if sk.evidence_type in {"Experience", "Project"}:
                return 1.00
            if "skills" not in sk.source.lower() and sk.source.strip():
                return 1.00

    combined_text = get_combined_project_and_exp_text(profile).lower()
    if not combined_text.strip():
        return 0.75

    # 2. Exact match in project/experience descriptions
    if clean_skill in combined_text:
        return 1.00

    # 3. Token match for multi-word skills (e.g. 'apache airflow' -> 'airflow')
    tokens = [t for t in re.split(r'[\s/|,-]+', clean_skill) if len(t) > 2]
    if tokens and any(t in combined_text for t in tokens):
        return 1.00

    # 4. Database Taxonomy concept and sibling alias match
    engine = TaxonomyConceptEngine.get_instance()
    canonical, category, aliases = engine.get_canonical_concept(clean_skill)
    if any(alias in combined_text for alias in aliases):
        return 1.00

    # 5. Compound skill sub-parts match
    if any(sep in clean_skill for sep in ["/", "&", "(", "+"]):
        sub_parts = [
            p.strip().lower()
            for p in re.split(r'[/,&()+]+', clean_skill)
            if len(p.strip()) > 1 and p.strip().lower() not in {'and', 'or', 'in', 'of', 'with', 'the'}
        ]
        for part in sub_parts:
            if part in combined_text:
                return 1.00
            _, _, part_aliases = engine.get_canonical_concept(part)
            if any(alias in combined_text for alias in part_aliases):
                return 1.00

    # 6. Morphological / Stemming equivalents (e.g. fine-tuning <-> fine-tuned, modeling <-> modeled)
    stemmed_tokens = [stem_token(t) for t in re.split(r'[\s/|,-]+', clean_skill) if len(t) > 2]
    if stemmed_tokens:
        for st in stemmed_tokens:
            if len(st) > 3 and st in combined_text:
                return 1.00

    for alias in aliases:
        for al_t in re.split(r'[\s/|,-]+', alias):
            st = stem_token(al_t)
            if len(st) > 3 and st in combined_text:
                return 1.00

    return 0.75

def evaluate_projects_and_proof(
    profile: StudentTwinProfile,
    target_weights: Dict[str, float],
    raw_resume_text: str = ""
) -> Dict[str, Any]:
    """
    Evaluates candidate projects and experience on 3 domain-agnostic dimensions:
    A. Quantitative Impact & Metrics Score (0–100)
    B. Engineering Depth & Verifiable Proof Score (0–100)
    C. Target Role Alignment Score (0–100)

    Returns project_quality_score (0.0 to 100.0) and resume_quality_breakdown.
    """
    combined_text = get_combined_project_and_exp_text(profile)
    if raw_resume_text:
        combined_text += " " + raw_resume_text
    lower_text = combined_text.lower()

    num_projects = len(profile.projects) if profile.projects else 0
    num_experience = len(profile.experience) if profile.experience else 0

    if num_projects == 0 and num_experience == 0 and not raw_resume_text:
        return {
            "project_quality_score": 30.0,
            "resume_quality_breakdown": {
                "quantitative_metrics_score": 30.0,
                "production_proof_score": 30.0,
                "role_alignment_score": 30.0,
                "detected_metrics": [],
                "detected_proof_links": [],
                "detected_production_stack": []
            }
        }

    # ----------------------------------------------------
    # A. Quantitative Impact & Metrics Score (Universal)
    # ----------------------------------------------------
    detected_metrics = []

    # 1. Percentages (e.g. 87.8%, 15%)
    percentages = re.findall(r'\b\d+(?:\.\d+)?%', combined_text)
    for p in percentages:
        detected_metrics.append(p)

    # 2. Multipliers (e.g. 10x, 3.5x)
    multipliers = re.findall(r'\b\d+(?:\.\d+)?x\b', combined_text, re.IGNORECASE)
    for m in multipliers:
        detected_metrics.append(m)

    # 3. Universal measurements & engineering benchmarks
    benchmark_patterns = [
        r'\b(?:reduced|increased|improved|achieved|optimized|scaled|accelerated|lowered|decreased|cut|boosted|saved)\s+(?:by\s+)?[\d.]+%?',
        r'\b\d+(?:\.\d+)?\s*(?:ms|seconds|minutes|hours|k|m|b|gb|tb|fps|qps|tps|db|f1|auc|accuracy|recall|precision|cgpa|gpa|psnr|ssim|users|requests|queries|rps|events|samples|records|parameters|params)\b',
        r'\b(?:batch[ -]?size|learning[ -]?rate|epochs?|c\s*=|lr\s*=|f1|recall|precision|accuracy)\s*(?:=|:|\s)?\s*[\de.-]+',
        r'\b\d+[- ](?:statement|tier|party|way|step|phase|stage)\b'
    ]
    for pat in benchmark_patterns:
        matches = re.findall(pat, combined_text, re.IGNORECASE)
        for m in matches:
            detected_metrics.append(m.strip())

    unique_metrics = list(dict.fromkeys(detected_metrics))
    num_metrics = len(unique_metrics)

    if num_metrics >= 5:
        metrics_score = 98.0
    elif num_metrics >= 3:
        metrics_score = 88.0
    elif num_metrics == 2:
        metrics_score = 72.0
    elif num_metrics == 1:
        metrics_score = 52.0
    else:
        metrics_score = 25.0

    # ----------------------------------------------------
    # B. Engineering Depth & Verifiable Proof Score (Universal)
    # ----------------------------------------------------
    detected_proof_signals = []
    for pat in UNIVERSAL_PROOF_PATTERNS:
        matches = re.findall(pat, combined_text, re.IGNORECASE)
        for m in matches:
            detected_proof_signals.append(m.strip().title())

    unique_proof_signals = list(dict.fromkeys(detected_proof_signals))
    num_proof_signals = len(unique_proof_signals)

    # Narrative depth & action-architecture structure
    words = lower_text.split()
    desc_word_count = len(words)
    num_projects = len(profile.projects or [])

    if num_projects >= 3 and desc_word_count >= 120:
        narrative_depth = 96.0
    elif num_projects >= 2 and desc_word_count >= 80:
        narrative_depth = 85.0
    elif num_projects == 0 and desc_word_count < 80:
        narrative_depth = 42.0
    else:
        narrative_depth = 62.0

    if num_proof_signals >= 3:
        proof_signals_score = 98.0
    elif num_proof_signals == 2:
        proof_signals_score = 82.0
    elif num_proof_signals == 1:
        proof_signals_score = 60.0
    else:
        proof_signals_score = 20.0

    # Skill evidence ratio: fraction of claimed skills demonstrated in narrative
    claimed_skills = profile.extracted_skills or []
    if claimed_skills:
        evidenced_count = sum(
            1 for s in claimed_skills
            if compute_skill_evidence_multiplier(s.skill_name, profile) >= 1.0
        )
        evidence_ratio = evidenced_count / max(len(claimed_skills), 1)
    else:
        evidence_ratio = 0.5

    proof_score = min(98.0, round(
        0.40 * narrative_depth + 0.40 * proof_signals_score + 0.20 * (evidence_ratio * 100),
        1
    ))

    # ----------------------------------------------------
    # C. Target Role Alignment Score (Domain-Agnostic)
    # ----------------------------------------------------
    matched_target_skills = []
    engine = TaxonomyConceptEngine.get_instance()
    if target_weights:
        for skill_name in target_weights.keys():
            s_low = skill_name.strip().lower()
            if s_low in lower_text:
                matched_target_skills.append(skill_name)
            else:
                _, _, aliases = engine.get_canonical_concept(skill_name)
                if any(alias in lower_text for alias in aliases):
                    matched_target_skills.append(skill_name)
                elif any(sep in s_low for sep in ["/", "&", "(", "+"]):
                    sub_parts = [
                        p.strip() for p in re.split(r'[/,&()+]+', s_low)
                        if len(p.strip()) > 1 and p.strip() not in {'and', 'or', 'in', 'of', 'with', 'the'}
                    ]
                    if any(part in lower_text for part in sub_parts):
                        matched_target_skills.append(skill_name)

        total_reqs = max(len(target_weights), 1)
        unique_matches = len(set(matched_target_skills))
        coverage_ratio = min(1.0, unique_matches / total_reqs)
        alignment_score = min(100.0, round(coverage_ratio * 115.0, 1))
    else:
        alignment_score = 75.0

    # ----------------------------------------------------
    # Combined Overall Project Quality Score
    # ----------------------------------------------------
    project_quality_score = round(
        (0.35 * metrics_score) + (0.35 * proof_score) + (0.30 * alignment_score),
        1
    )

    # Extract candidate skills demonstrated in projects or experience
    project_verified_skills = [
        s.skill_name for s in claimed_skills
        if compute_skill_evidence_multiplier(s.skill_name, profile) >= 1.0
    ]

    return {
        "project_quality_score": project_quality_score,
        "resume_quality_breakdown": {
            "quantitative_metrics_score": metrics_score,
            "production_proof_score": proof_score,
            "role_alignment_score": alignment_score,
            "detected_metrics": unique_metrics[:8],
            "detected_proof_links": unique_proof_signals[:8],
            "detected_production_stack": list(dict.fromkeys(project_verified_skills))[:12]
        }
    }
