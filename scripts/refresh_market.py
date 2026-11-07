"""
Script to scrape live job postings, update the database, and recalculate Cross-Role TF-IDF weights.
Used by weekly cron jobs and admin endpoints.
"""
import sys
from src.db.session import SessionLocal, init_db
from src.utils.scraper import JobMarketScraper
from src.engine.market_updater import MarketUpdater
from src.db.crud import upsert_job
from src.db.models import Taxonomy, Market
from src.utils.logger import get_custom_logger

logger = get_custom_logger(__name__)

def main():
    logger.info("Starting live job market ingestion and TF-IDF refresh...")
    init_db()
    db = SessionLocal()

    try:
        tax_skills = {t.name for t in db.query(Taxonomy).all()}
        market_skills = {item["skill"] for m in db.query(Market).all() for item in (m.trending_skills or [])}
        known_skills = set(tax_skills | market_skills)
        if not known_skills:
            known_skills = {
                "python", "r", "sql", "pytorch", "tensorflow", "scikit-learn",
                "aws", "gcp", "azure", "docker", "kubernetes", "airflow", "git",
                "machine learning", "deep learning", "nlp", "pandas", "spark", "tableau"
            }

        scraper = JobMarketScraper()
        scraped_by_role = scraper.scrape_all_roles(max_per_role=50)

        total_ingested = 0
        for role, jobs in scraped_by_role.items():
            for job in jobs:
                desc = f"{job.get('title', '')} {job.get('description', '')}"
                extracted_skills = JobMarketScraper.extract_skills_from_text(desc, known_skills)
                upsert_job(
                    db=db,
                    job_hash=job["job_hash"],
                    target_role=role,
                    title=job.get("title"),
                    company=job.get("company"),
                    location=job.get("location"),
                    raw_payload=job.get("raw_payload", {}),
                    skills=extracted_skills
                )
                total_ingested += 1

        logger.info(f"Ingested {total_ingested} total jobs across all roles.")

        updater = MarketUpdater(db=db)
        new_weights = updater.update_market_weights()
        logger.info(f"Successfully updated market weights for {len(new_weights)} roles.")
        print(f"Market refresh complete: {total_ingested} jobs processed.")

    except Exception as e:
        logger.error(f"Error during market refresh: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()

