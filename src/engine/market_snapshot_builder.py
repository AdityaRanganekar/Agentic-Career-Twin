import os
import pandas as pd
import spacy
from spacy.matcher import PhraseMatcher
from sqlalchemy.orm import Session
from src.db.database import SessionLocal
from src.db.models import Taxonomy, Market
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

class MarketSnapshotBuilder:
    def __init__(self, db: Session):
        self.db = db

        self.nlp = spacy.blank("en")
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self.canonical_map = {}
        self._initialize_matcher()

    def _initialize_matcher(self):
        """Loads the taxonomy from the database and builds spaCy match patterns."""
        taxonomies = self.db.query(Taxonomy).all()
        
        for tax in taxonomies:

            patterns = [self.nlp.make_doc(tax.name)]
            self.canonical_map[tax.name.lower()] = tax.name

            if tax.aliases:
                for alias in tax.aliases:
                    patterns.append(self.nlp.make_doc(str(alias)))
                    self.canonical_map[str(alias).lower()] = tax.name
                    
            self.matcher.add(tax.name, patterns)
        logger.info(f"Initialized PhraseMatcher with {len(taxonomies)} taxonomy rules.")

    def categorize_role(self, title: str) -> str:
        """Deterministically maps raw job titles to the 4 target corpus roles."""
        title_lower = str(title).lower()
        if "machine learning" in title_lower or "ml" in title_lower:
            return "Machine Learning Engineer"
        elif "scientist" in title_lower or "data science" in title_lower:
            return "Data Scientist"
        elif "engineer" in title_lower:
            return "Data Engineer"
        elif "analyst" in title_lower or "analytics" in title_lower:
            return "Data Analyst"
        return "Other"

    def extract_skills(self, text: str) -> set:
        """Runs the PhraseMatcher over a job description to extract canonical skill IDs."""
        doc = self.nlp(str(text))
        matches = self.matcher(doc)
        
        extracted_canonical_skills = set()
        for match_id, start, end in matches:
            rule_id = self.nlp.vocab.strings[match_id]
            extracted_canonical_skills.add(rule_id)
            
        return extracted_canonical_skills

    def build_snapshot(self, csv_path: str):
        """Processes the Kaggle dataset, calculates frequencies, and updates the Market table."""
        logger.info(f"Loading job dataset from {csv_path}")
        df = pd.read_csv(csv_path)

        df['Target Role'] = df['Job Title'].apply(self.categorize_role)
        target_df = df[df['Target Role'] != "Other"].copy()
        
        logger.info(f"Processing {len(target_df)} target roles for skill extraction.")
        
        target_df['Extracted Skills'] = target_df['Job Description'].apply(self.extract_skills)

        role_groups = target_df.groupby('Target Role')
        
        for role_name, group in role_groups:
            skill_counts = {}
            for skills_set in group['Extracted Skills']:
                for skill in skills_set:
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1

            sorted_skills = [{"skill": k, "frequency": v} for k, v in sorted(skill_counts.items(), key=lambda item: item[1], reverse=True)]
        
            existing_market = self.db.query(Market).filter(Market.role_name == role_name).first()
            if existing_market:
                existing_market.trending_skills = sorted_skills
                existing_market.demand_score = len(group) 
            else:
                new_market = Market(
                    role_name=role_name,
                    trending_skills=sorted_skills,
                    demand_score=len(group)
                )
                self.db.add(new_market)
                
        self.db.commit()
        logger.info("Market snapshot successfully built and saved to database.")

if __name__ == "__main__":
    db_session = SessionLocal()
    try:
        builder = MarketSnapshotBuilder(db_session)
        target_csv = os.path.join(os.getcwd(), "data", "jobs", "kaggle_ds_jobs.csv")
        if os.path.exists(target_csv):
            builder.build_snapshot(target_csv)
        else:
            logger.error(f"Dataset not found at {target_csv}")
    finally:
        db_session.close()