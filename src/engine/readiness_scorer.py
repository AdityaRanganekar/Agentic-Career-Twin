import math
import yaml
from datetime import datetime, timezone
from typing import Dict, List, Optional
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

class ReadinessScorer:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.decay_lambda = self.config.get('scoring', {}).get('recency_decay_lambda', 0.15)
        self.base_strength = self.config.get('scoring', {}).get('base_strength_default', 1.0)

    def calculate_tf_idf(
        self, 
        target_role_skill_counts: Dict[str, int], 
        target_role_total_jobs: int, 
        global_skill_counts: Dict[str, int], 
        total_global_jobs: int
    ) -> Dict[str, float]:
        """
        Calculates cross-role TF-IDF weighting to penalize generic skills and boost discriminative ones.
        """
        tf_idf_weights = {}
        
        if target_role_total_jobs == 0:
            return tf_idf_weights

        for skill, count_in_role in target_role_skill_counts.items():

            tf = count_in_role / target_role_total_jobs

            df = global_skill_counts.get(skill, 0)
            idf = math.log((total_global_jobs + 1) / (df + 1)) + 1
            
            tf_idf_weights[skill] = tf * idf
            
        return tf_idf_weights

    def apply_recency_decay(self, base_strength: float, completion_date_str: Optional[str]) -> float:
        """
        Applies exponential decay based on the age of the evidence.
        """
        if not completion_date_str:
            return base_strength  
        
        try:

            completion_date = datetime.strptime(completion_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
   
            age_in_days = (datetime.now(timezone.utc) - completion_date).days
            age_in_years = age_in_days / 365.25
            
            if age_in_years <= 0:
                return base_strength  
                
            decayed_strength = base_strength * math.exp(-self.decay_lambda * age_in_years)
            return round(decayed_strength, 4)
            
        except ValueError:
            logger.warning(f"Invalid date format: {completion_date_str}. Skipping decay.")
            return base_strength

    def calculate_role_readiness(
        self, 
        student_skills: List[dict], 
        tf_idf_weights: Dict[str, float]
    ) -> float:
        """
        Calculates the final Market-Weighted Skill Coverage score.
        Expects student_skills as a list of dicts: [{'name': 'Python', 'date': '2023-05-01', 'strength': 1.0}]
        """
        earned_score = 0.0
        total_possible_score = sum(tf_idf_weights.values())
        
        if total_possible_score == 0:
            return 0.0

        processed_student_skills = {}
        for evidence in student_skills:
            skill_name = evidence.get("name")
            if not skill_name:
                continue
                
            strength = evidence.get("strength", self.base_strength)
            date_str = evidence.get("date")
            decayed_strength = self.apply_recency_decay(strength, date_str)
 
            if skill_name not in processed_student_skills or decayed_strength > processed_student_skills[skill_name]:
                processed_student_skills[skill_name] = decayed_strength

        for skill_name, tf_idf_weight in tf_idf_weights.items():
            if skill_name in processed_student_skills:
                earned_score += processed_student_skills[skill_name] * tf_idf_weight
                
        readiness_percentage = (earned_score / total_possible_score) * 100
        return min(round(readiness_percentage, 2), 100.0)