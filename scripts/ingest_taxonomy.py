import os
import csv
from src.db.database import SessionLocal
from src.db.models import Taxonomy
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def ingest_taxonomy(csv_path: str):
    logger.info(f"Starting taxonomy ingestion from {csv_path}")
    db = SessionLocal()
    
    try:
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            records_added = 0
            seen_names = set()  
            
            for row in reader:
                name = row.get('Workplace Example', '').strip()
                category = row.get('Element Name', '').strip()
  
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                existing = db.query(Taxonomy).filter(Taxonomy.name == name).first()
                if not existing:
                    new_term = Taxonomy(
                        category=category,
                        name=name,
                        aliases=[] 
                    )
                    db.add(new_term)
                    records_added += 1
                    
        db.commit()
        logger.info(f"Taxonomy ingestion completed. Added {records_added} unique records.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to ingest taxonomy: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    target_csv = os.path.join(os.getcwd(), "data", "taxonomy", "hybrid_skills_v1.csv")
    if os.path.exists(target_csv):
        ingest_taxonomy(target_csv)
    else:
        logger.error(f"File not found: {target_csv}")