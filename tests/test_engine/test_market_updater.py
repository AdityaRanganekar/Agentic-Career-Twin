import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from src.utils.scraper import JobMarketScraper
from src.engine.deduplicator import JobDeduplicator
from src.engine.market_updater import MarketUpdater
from src.db.models import Market, MarketSnapshot, Job, JobSkill
from src.graph.agents.role_research_agent import RoleResearchAgent
from src.domain.schemas import RoleSkillProfile, WeightedSkill

def test_job_deduplicator():
    job1 = {"company": "Google", "title": "Machine Learning Engineer", "location": "Remote"}
    job2 = {"company": " Google ", "title": "machine learning engineer", "location": "remote"}
    job3 = {"company": "Meta", "title": "Data Scientist", "location": "Menlo Park"}

    h1 = JobDeduplicator.compute_job_hash(job1["company"], job1["title"], job1["location"])
    h2 = JobDeduplicator.compute_job_hash(job2["company"], job2["title"], job2["location"])
    h3 = JobDeduplicator.compute_job_hash(job3["company"], job3["title"], job3["location"])

    assert h1 == h2, "Equivalent job postings with whitespace/case differences must yield identical hash"
    assert h1 != h3, "Different companies and titles must yield distinct hashes"

    deduped = JobDeduplicator.deduplicate_jobs([job1, job2, job3])
    assert len(deduped) == 2, "Duplicate postings must be collapsed into one"

def test_scraper_missing_credentials_graceful():
    scraper = JobMarketScraper()
    scraper.adzuna_app_id = None
    scraper.adzuna_app_key = None
    scraper.serpapi_key = None

    with patch.object(scraper, 'fetch_remotive_jobs', return_value=[]), \
         patch.object(scraper, 'fetch_arbeitnow_jobs', return_value=[]), \
         patch.object(scraper, 'fetch_web_job_snippets', return_value=[]):
        jobs = scraper.scrape_role("Data Scientist", max_jobs=10)
        assert jobs == [], "Scraper must return empty list without crashing when API credentials are unset"

def test_scraper_skill_extraction():
    text = "We are seeking a candidate experienced in Python, PyTorch, Docker, and Kubernetes for building ML pipelines."
    candidate_skills = {"python", "pytorch", "docker", "kubernetes", "golang", "react"}
    extracted = JobMarketScraper.extract_skills_from_text(text, candidate_skills)
    
    assert "python" in extracted
    assert "pytorch" in extracted
    assert "docker" in extracted
    assert "kubernetes" in extracted
    assert "golang" not in extracted
    assert "react" not in extracted

def test_market_updater_cross_role_tfidf_math():
    mock_db = MagicMock()
    updater = MarketUpdater(db=mock_db, min_jobs_threshold=50)

    # Synthetic corpus with 2 roles: Role A (ML) and Role B (Analyst)
    # Python is generic (in both roles), PyTorch is discriminative (only in ML)
    role_skill_counts = {
        "Machine Learning Engineer": {"Python": 100, "PyTorch": 80},
        "Data Analyst": {"Python": 100, "Excel": 90}
    }
    role_job_counts = {
        "Machine Learning Engineer": 100,
        "Data Analyst": 100
    }

    weights = updater.compute_cross_role_tfidf(role_skill_counts, role_job_counts)

    assert "Machine Learning Engineer" in weights
    assert "Data Analyst" in weights

    ml_weights = weights["Machine Learning Engineer"]
    # PyTorch appears in only 1 role's jobs (DF=80), while Python appears in both (DF=200)
    # IDF for PyTorch should be higher than Python, giving PyTorch a higher TF-IDF weight
    assert ml_weights["PyTorch"] > ml_weights["Python"], "Discriminative skill PyTorch must have higher weight than generic Python"

def test_market_updater_small_sample_safeguard():
    mock_db = MagicMock()
    # Mock live jobs: only 5 jobs in live table for Data Scientist (below threshold of 50)
    mock_db.query.return_value.filter.return_value.all.return_value = []
    
    baseline_market = Market(
        role_name="Data Scientist",
        demand_score=1000,
        trending_skills=[{"skill": "Python", "frequency": 800}, {"skill": "SQL", "frequency": 700}]
    )
    mock_db.query.return_value.all.return_value = [baseline_market]

    updater = MarketUpdater(db=mock_db, min_jobs_threshold=50)
    weights = updater.update_market_weights()

    assert "Data Scientist" in weights
    assert "Python" in weights["Data Scientist"]
    assert weights["Data Scientist"]["Python"] > 0, "Fallback/blended TF-IDF weights must be preserved"

def test_read_through_role_cache_and_ttl(db_session):
    """
    Verifies the Read-Through Role Cache + TTL architecture:
    1. First search for a new role (e.g. 'Computer Vision Engineer') misses cache,
       triggers live research, and persists the snapshot to the database.
    2. Second search for the same role hits the database cache immediately ('DB-Cached')
       without triggering live discovery or LLM calls.
    3. Simulating an expired timestamp (> 365 days TTL) triggers a fresh live research
       update and resets the timestamp.
    """
    role = "Computer Vision Engineer"

    # Step 1: Initial search - Cache MISS
    miss = RoleResearchAgent.find_cached_role_snapshot(db_session, role, ttl_days=365)
    assert miss is None, "New role must result in a cache miss"

    sample_skills = [
        WeightedSkill(skill_name="Python", importance_weight=0.95),
        WeightedSkill(skill_name="PyTorch", importance_weight=0.95),
        WeightedSkill(skill_name="OpenCV", importance_weight=0.90),
        WeightedSkill(skill_name="CUDA", importance_weight=0.85),
        WeightedSkill(skill_name="TensorFlow", importance_weight=0.80),
        WeightedSkill(skill_name="CNN", importance_weight=0.85),
        WeightedSkill(skill_name="YOLO", importance_weight=0.80),
        WeightedSkill(skill_name="C++", importance_weight=0.80),
        WeightedSkill(skill_name="Docker", importance_weight=0.75),
        WeightedSkill(skill_name="Git", importance_weight=0.70)
    ]
    mock_profile = RoleSkillProfile(target_role=role, core_skills=sample_skills)

    with patch("src.graph.agents.role_research_agent.JobMarketScraper") as mock_scraper_cls, \
         patch("src.graph.agents.role_research_agent.get_gemini_client") as mock_get_client:

        mock_scraper = MagicMock()
        mock_scraper_cls.return_value = mock_scraper
        mock_scraper.scrape_role.return_value = [
            {"job_hash": "cv1", "title": "CV Engineer", "company": "Vision AI", "location": "Remote", "description": "PyTorch, OpenCV, CUDA"}
        ]
        mock_scraper.extract_skills_from_text.return_value = ["Python", "PyTorch", "OpenCV"]

        mock_model = MagicMock()
        mock_get_client.return_value = mock_model
        mock_model.generate_content.return_value.text = mock_profile.model_dump_json()

        weights, version = RoleResearchAgent.research_role_live(role, db_session)

        assert "Live-Web-Acquired" in version
        assert len(weights) >= 8
        assert "PyTorch" in weights
        assert "OpenCV" in weights

    # Step 2: Second search - Cache HIT (0 LLM tokens)
    cached = RoleResearchAgent.find_cached_role_snapshot(db_session, role, ttl_days=365)
    assert cached is not None, "Subsequent search must return a database cache hit"
    cached_weights, cached_version = cached
    assert "DB-Cached" in cached_version
    assert "Computer Vision Engineer" in cached_version
    assert cached_weights["PyTorch"] == 0.95

    # Step 3: Expired TTL (> 365 days) -> Cache EXPIRED and Refresh
    snap = db_session.query(MarketSnapshot).filter(MarketSnapshot.target_role == role).order_by(MarketSnapshot.timestamp.desc()).first()
    assert snap is not None
    # Set timestamp to 400 days ago
    snap.timestamp = datetime.now(timezone.utc) - timedelta(days=400)
    m = db_session.query(Market).filter(Market.role_name == role).first()
    if m:
        m.last_analyzed = datetime.now(timezone.utc) - timedelta(days=400)
    db_session.commit()

    expired = RoleResearchAgent.find_cached_role_snapshot(db_session, role, ttl_days=365)
    assert expired is None, "Snapshot older than 365 days must be treated as expired"

    # Refresh live update resets timestamp
    with patch("src.graph.agents.role_research_agent.JobMarketScraper") as mock_scraper_cls, \
         patch("src.graph.agents.role_research_agent.get_gemini_client") as mock_get_client:
        mock_scraper = MagicMock()
        mock_scraper_cls.return_value = mock_scraper
        mock_scraper.scrape_role.return_value = []
        mock_scraper.extract_skills_from_text.return_value = []

        mock_model = MagicMock()
        mock_get_client.return_value = mock_model
        mock_model.generate_content.return_value.text = mock_profile.model_dump_json()

        refreshed_weights, refreshed_version = RoleResearchAgent.research_role_live(role, db_session)
        assert "Live-Web-Acquired" in refreshed_version

    new_snap = db_session.query(MarketSnapshot).filter(MarketSnapshot.target_role == role).order_by(MarketSnapshot.timestamp.desc()).first()
    now_utc = datetime.now(timezone.utc)
    t = new_snap.timestamp
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    assert (now_utc - t).days == 0, "Refreshed snapshot must have a current timestamp"


