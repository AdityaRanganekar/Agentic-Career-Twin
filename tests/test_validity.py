import pytest
from scipy.stats import spearmanr

def test_spearman_correlation(capsys):
    human_scores = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    
    # TODO: Process files 10.pdf down to 1.pdf in Streamlit.
    # Replace these placeholders with the actual TF-IDF % outputs from your UI.
    system_scores = [
        85.56,  
        77.15,  
        79.68,  
        62.9, 
        71.46,  
        74.01,  
        66.88, 
        75.42,  
        62.9,   
        0.0    
    ]
    
    correlation, p_value = spearmanr(human_scores, system_scores)
    
    with capsys.disabled():
        print(f"\n--- SPRINT 5: HUMAN VALIDITY STUDY (SPEARMAN) ---")
        print(f"Target Role: Data Scientist")
        print(f"Spearman Correlation: {correlation:.4f}")
        print(f"P-Value: {p_value:.4e}")
        print(f"-------------------------------------------------")
        
    assert correlation > 0.70, f"System correlation ({correlation:.2f}) fell below the 0.70 threshold."
    assert p_value < 0.05, "Correlation is not statistically significant."