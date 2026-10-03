import os
import csv
import urllib.parse
from src.db.database import SessionLocal
from src.db.models import Resources
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def seed_coursera_resources(csv_path: str):
    logger.info(f"Starting resource seeding from {csv_path}")
    db = SessionLocal()
    
    try:
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            records_added = 0
            seen_titles = set()  
            
            for row in reader:
                title = row.get('course_title', '').strip()

                if not title or title in seen_titles:
                    continue
                    
                seen_titles.add(title)

                existing = db.query(Resources).filter(Resources.title == title).first()
                if not existing:
                    url_encoded_title = urllib.parse.quote_plus(title)
                    generated_url = f"https://www.coursera.org/search?query={url_encoded_title}"
                    
                    new_resource = Resources(
                        title=title,
                        url=generated_url,
                        resource_type=row.get('course_Certificate_type', 'COURSE').strip(),
                        difficulty_level=row.get('course_difficulty', 'Mixed').strip(),
                        target_skills=[] 
                    )
                    db.add(new_resource)
                    records_added += 1
                    
        db.commit()
        logger.info(f"Resource seeding completed. Added {records_added} unique courses.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed resources: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    target_csv = os.path.join(os.getcwd(), "data", "resources", "kaggle_coursera.csv")
    if os.path.exists(target_csv):
        seed_coursera_resources(target_csv)
    else:
        logger.error(f"File not found: {target_csv}")