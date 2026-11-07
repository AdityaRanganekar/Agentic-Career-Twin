import pytest
from sqlalchemy import func
from src.db.models import Taxonomy
from src.engine.skill_normalizer import SkillNormalizer

BENCHMARK_EXTRACTION_DATASET = [
    # Exact Matches (Stage A, B, C)
    {"raw": "Python", "ground_truth": "Python"},
    {"raw": "React", "ground_truth": "React"},
    {"raw": "PostgreSQL", "ground_truth": "PostgreSQL"},
    {"raw": "Docker", "ground_truth": "Docker"},
    
    # Alias / Acronym Matches (Stage B, C)
    {"raw": "py", "ground_truth": "Python"},
    {"raw": "reactjs", "ground_truth": "React"},
    {"raw": "postgres", "ground_truth": "PostgreSQL"},
    {"raw": "torch", "ground_truth": "PyTorch"},
    
    # Dense Vector Similarity Fallback Matches (Stage C)
    {"raw": "react frontend", "ground_truth": "React"},
    {"raw": "postgresql database", "ground_truth": "PostgreSQL"},
    
    # Out-of-Domain / Negative Controls (Rejected by all stages)
    {"raw": "Django", "ground_truth": None},
    {"raw": "Kubernetes", "ground_truth": None},
    {"raw": "Project Management", "ground_truth": None},
    {"raw": "Cooking Recipes", "ground_truth": None}
]

def calculate_f1(tp: int, fp: int, fn: int):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

def evaluate_predictions(dataset, predictions):
    tp, fp, fn = 0, 0, 0
    for item, pred in zip(dataset, predictions):
        expected = item["ground_truth"]
        if expected is not None:
            if pred == expected:
                tp += 1
            else:
                fn += 1
        else:
            if pred is not None:
                fp += 1
    return calculate_f1(tp, fp, fn)

def test_waterfall_ablation_metrics(db_session, capsys):
    """
    Ablation study evaluating the 3 stages of the Waterfall Normalizer:
    - Stage A: Deterministic Exact Match Only
    - Stage B: Deterministic Exact Match + Alias Match
    - Stage C: Full Waterfall Architecture (Exact + Alias + Dense Vector Fallback)
    """
    # Seed additional taxonomies required for benchmark dataset
    additional_taxonomies = [
        Taxonomy(category="tool", name="Docker", aliases=["docker engine", "docker ce"]),
        Taxonomy(category="framework", name="PyTorch", aliases=["torch", "pytorch dl"]),
        Taxonomy(category="concept", name="Machine Learning", aliases=["ml"]),
    ]
    db_session.add_all(additional_taxonomies)
    db_session.commit()

    normalizer = SkillNormalizer(db_session)
    
    # --- STAGE A: Exact Match Only ---
    def stage_a_exact(raw_skill: str):
        clean = raw_skill.strip().lower()
        match = db_session.query(Taxonomy).filter(func.lower(Taxonomy.name) == clean).first()
        return match.name if match else None

    # --- STAGE B: Exact Match + Alias Match ---
    def stage_b_exact_alias(raw_skill: str):
        exact = stage_a_exact(raw_skill)
        if exact:
            return exact
        clean = raw_skill.strip().lower()
        for tax in db_session.query(Taxonomy).all():
            if tax.aliases and clean in [str(a).strip().lower() for a in tax.aliases]:
                return tax.name
        return None

    # --- STAGE C: Full Waterfall with Vector Fallback ---
    def stage_c_full(raw_skill: str):
        return normalizer.normalize(raw_skill)

    preds_a = [stage_a_exact(d["raw"]) for d in BENCHMARK_EXTRACTION_DATASET]
    prec_a, rec_a, f1_a = evaluate_predictions(BENCHMARK_EXTRACTION_DATASET, preds_a)

    preds_b = [stage_b_exact_alias(d["raw"]) for d in BENCHMARK_EXTRACTION_DATASET]
    prec_b, rec_b, f1_b = evaluate_predictions(BENCHMARK_EXTRACTION_DATASET, preds_b)

    preds_c = [stage_c_full(d["raw"]) for d in BENCHMARK_EXTRACTION_DATASET]
    prec_c, rec_c, f1_c = evaluate_predictions(BENCHMARK_EXTRACTION_DATASET, preds_c)

    with capsys.disabled():
        print(f"\n=======================================================")
        print(f"--- WATERFALL NORMALIZER 3-STAGE ABLATION RESULTS ---")
        print(f"Stage A (Exact Only):            Precision: {prec_a:.2f} | Recall: {rec_a:.2f} | F1: {f1_a:.2f}")
        print(f"Stage B (Exact + Alias):         Precision: {prec_b:.2f} | Recall: {rec_b:.2f} | F1: {f1_b:.2f}")
        print(f"Stage C (Full Waterfall+Vector): Precision: {prec_c:.2f} | Recall: {rec_c:.2f} | F1: {f1_c:.2f}")
        print(f"=======================================================")

    # Verification assertions
    assert prec_a == 1.0, "Exact match should have 100% precision on true positives"
    assert rec_b > rec_a, "Adding alias matching must strictly increase recall over exact matching"
    assert rec_c >= rec_b, "Full waterfall with vector fallback must maintain or improve recall"
    assert prec_c >= 0.80, "Stage C Precision must be >= 0.80"
    assert rec_c >= 0.80, "Stage C Recall must be >= 0.80"
    assert f1_c >= 0.80, "Stage C F1 score must be >= 0.80"
