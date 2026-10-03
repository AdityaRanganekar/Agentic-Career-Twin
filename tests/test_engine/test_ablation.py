import pytest
from src.engine.skill_normalizer import SkillNormalizer

MOCK_EXTRACTION_DATASET = [

    {"raw": "PostgreSQL", "ground_truth": "PostgreSQL"}, 
    {"raw": "postgres", "ground_truth": "PostgreSQL"},   
    {"raw": "React.js", "ground_truth": "React"},        
    {"raw": "python 3", "ground_truth": "Python"},       
    {"raw": "Django", "ground_truth": None},             
    {"raw": "K8s", "ground_truth": None}                 
]

def calculate_f1(tp: int, fp: int, fn: int):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

def test_waterfall_ablation_metrics(db_session, capsys):
    normalizer = SkillNormalizer(db_session)
    
    tp, fp, fn = 0, 0, 0
    
    for item in MOCK_EXTRACTION_DATASET:
        raw_skill = item["raw"]
        expected = item["ground_truth"]
        
        predicted = normalizer.normalize(raw_skill)
        
        if expected is not None:
            if predicted == expected:
                tp += 1  
            else:
                fn += 1  
        else:
            if predicted is not None:
                fp += 1  

    precision, recall, f1 = calculate_f1(tp, fp, fn)

    with capsys.disabled():
        print(f"\n--- ABLATION STUDY RESULTS ---")
        print(f"True Positives: {tp} | False Positives: {fp} | False Negatives: {fn}")
        print(f"Precision: {precision:.2f}")
        print(f"Recall:    {recall:.2f}")
        print(f"F1 Score:  {f1:.2f}")
        print(f"------------------------------")

    assert precision > 0.80, "Precision fell below 80% baseline."
    assert recall > 0.80, "Recall fell below 80% baseline."