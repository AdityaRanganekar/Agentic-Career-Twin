"""
Live job market API scraper supporting Adzuna, SerpAPI, Remotive, Arbeitnow, and DuckDuckGo web search
with deduplication and error handling.
"""
import os
import re
import html
import urllib.parse
import httpx
from typing import List, Dict, Optional, Set
from dotenv import load_dotenv
from src.utils.logger import get_custom_logger
from src.engine.deduplicator import JobDeduplicator

load_dotenv()
logger = get_custom_logger(__name__)

DEFAULT_ROLES = [
    "Data Scientist",
    "Machine Learning Engineer",
    "AI / LLM Engineer",
    "Data Engineer",
    "Data Analyst",
    "MLOps Engineer",
    "Backend Software Engineer",
    "Full-Stack Developer",
    "Cloud / DevOps Engineer",
    "Quantitative Researcher"
]

class JobMarketScraper:
    """
    Scrapes live job postings from zero-key open APIs (Remotive, Arbeitnow, DuckDuckGo)
    as well as Adzuna and SerpAPI when credentials are provided.
    """
    def __init__(self):
        self.adzuna_app_id = os.getenv("ADZUNA_APP_ID")
        self.adzuna_app_key = os.getenv("ADZUNA_API_KEY")
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.timeout = 7.0

    def fetch_adzuna_jobs(self, role: str, country: str = "us", results_per_page: int = 20) -> List[Dict]:
        """Fetches job postings from the Adzuna REST API if credentials exist."""
        if not self.adzuna_app_id or not self.adzuna_app_key:
            return []

        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": self.adzuna_app_id,
            "app_key": self.adzuna_app_key,
            "results_per_page": results_per_page,
            "what": role,
            "content-type": "application/json"
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    jobs = []
                    for item in results:
                        title = item.get("title", "")
                        company = item.get("company", {}).get("display_name", "")
                        loc = item.get("location", {}).get("display_name", "")
                        description = item.get("description", "")
                        job_hash = JobDeduplicator.compute_job_hash(company, title, loc)
                        jobs.append({
                            "job_hash": job_hash,
                            "target_role": role,
                            "title": title,
                            "company": company,
                            "location": loc,
                            "description": description,
                            "url": item.get("redirect_url", ""),
                            "source": "adzuna",
                            "raw_payload": item
                        })
                    logger.info(f"Fetched {len(jobs)} jobs for role '{role}' from Adzuna.")
                    return jobs
        except Exception as e:
            logger.warning(f"Adzuna API fetch failed: {str(e)}")
        return []

    def fetch_serpapi_jobs(self, role: str, num: int = 20) -> List[Dict]:
        """Fetches Google Jobs listings via SerpAPI if credentials exist."""
        if not self.serpapi_key:
            return []

        url = "https://serpapi.com/search"
        params = {"engine": "google_jobs", "q": role, "api_key": self.serpapi_key, "hl": "en"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    jobs_results = resp.json().get("jobs_results", [])
                    jobs = []
                    for item in jobs_results[:num]:
                        title = item.get("title", "")
                        company = item.get("company_name", "")
                        loc = item.get("location", "")
                        description = item.get("description", "")
                        job_hash = JobDeduplicator.compute_job_hash(company, title, loc)
                        jobs.append({
                            "job_hash": job_hash,
                            "target_role": role,
                            "title": title,
                            "company": company,
                            "location": loc,
                            "description": description,
                            "url": item.get("related_links", [{}])[0].get("link", "") if item.get("related_links") else "",
                            "source": "serpapi",
                            "raw_payload": item
                        })
                    logger.info(f"Fetched {len(jobs)} jobs for role '{role}' from SerpAPI.")
                    return jobs
        except Exception as e:
            logger.warning(f"SerpAPI fetch failed: {str(e)}")
        return []

    def fetch_remotive_jobs(self, role: str, limit: int = 15) -> List[Dict]:
        """Free, zero-key remote tech jobs API from Remotive."""
        url = f"https://remotive.com/api/remote-jobs?search={urllib.parse.quote(role)}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    raw_jobs = resp.json().get("jobs", [])
                    jobs = []
                    for item in raw_jobs[:limit]:
                        title = item.get("title", "")
                        company = item.get("company_name", "")
                        loc = item.get("candidate_required_location", "Remote")
                        raw_desc = item.get("description", "")
                        description = re.sub(r'<[^>]+>', ' ', raw_desc).strip()
                        job_hash = JobDeduplicator.compute_job_hash(company, title, loc)
                        jobs.append({
                            "job_hash": job_hash,
                            "target_role": role,
                            "title": title,
                            "company": company,
                            "location": loc,
                            "description": description,
                            "url": item.get("url", ""),
                            "source": "remotive",
                            "raw_payload": item
                        })
                    logger.info(f"Fetched {len(jobs)} jobs for role '{role}' from Remotive.")
                    return jobs
        except Exception as e:
            logger.warning(f"Remotive API fetch skipped or failed: {str(e)}")
        return []

    def fetch_arbeitnow_jobs(self, role: str, limit: int = 15) -> List[Dict]:
        """Free, zero-key public tech jobs board API from Arbeitnow."""
        url = "https://www.arbeitnow.com/api/job-board-api"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    raw_data = resp.json().get("data", [])
                    role_tokens = set(re.findall(r'\w+', role.lower()))
                    jobs = []
                    for item in raw_data:
                        title = item.get("title", "")
                        tags = [t.lower() for t in item.get("tags", [])]
                        title_lower = title.lower()
                        # Filter by role relevance
                        if any(token in title_lower or token in tags for token in role_tokens):
                            company = item.get("company_name", "")
                            loc = item.get("location", "Remote")
                            raw_desc = item.get("description", "")
                            description = re.sub(r'<[^>]+>', ' ', raw_desc).strip()
                            job_hash = JobDeduplicator.compute_job_hash(company, title, loc)
                            jobs.append({
                                "job_hash": job_hash,
                                "target_role": role,
                                "title": title,
                                "company": company,
                                "location": loc,
                                "description": description,
                                "url": item.get("url", ""),
                                "source": "arbeitnow",
                                "raw_payload": item
                            })
                            if len(jobs) >= limit:
                                break
                    logger.info(f"Fetched {len(jobs)} jobs for role '{role}' from Arbeitnow.")
                    return jobs
        except Exception as e:
            logger.warning(f"Arbeitnow API fetch skipped or failed: {str(e)}")
        return []

    def fetch_web_job_snippets(self, role: str, limit: int = 10) -> List[Dict]:
        """Keyless DuckDuckGo live web search extracting technical skill requirements snippets."""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        query = urllib.parse.quote(f"{role} job description required technical skills qualifications")
        url = f"https://html.duckduckgo.com/html/?q={query}"
        try:
            with httpx.Client(timeout=self.timeout, headers=headers) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    raw_snippets = re.findall(r"class=[\"\']result__snippet[\"\'][^>]*>(.*?)</a>", resp.text, re.DOTALL)
                    jobs = []
                    for idx, s in enumerate(raw_snippets[:limit]):
                        clean_text = re.sub(r"<[^>]+>", "", html.unescape(s)).strip()
                        if clean_text:
                            job_hash = JobDeduplicator.compute_job_hash("Web Intelligence", f"{role} Snippet {idx}", "Online")
                            jobs.append({
                                "job_hash": job_hash,
                                "target_role": role,
                                "title": f"{role} Live Web Posting Snippet",
                                "company": "Web Search Index",
                                "location": "Online",
                                "description": clean_text,
                                "url": "https://duckduckgo.com",
                                "source": "duckduckgo",
                                "raw_payload": {"snippet": clean_text}
                            })
                    logger.info(f"Fetched {len(jobs)} live web snippets for role '{role}'.")
                    return jobs
        except Exception as e:
            logger.warning(f"Web snippets search skipped or failed: {str(e)}")
        return []

    def scrape_role(self, role: str, max_jobs: int = 50) -> List[Dict]:
        """
        Aggregates and deduplicates jobs for a single role across all available APIs and search sources.
        """
        jobs = []
        # 1. Zero-key open tech APIs
        jobs.extend(self.fetch_remotive_jobs(role, limit=min(max_jobs, 15)))
        jobs.extend(self.fetch_arbeitnow_jobs(role, limit=min(max_jobs, 15)))
        jobs.extend(self.fetch_web_job_snippets(role, limit=10))

        # 2. Keyed APIs if configured
        if self.adzuna_app_id and self.adzuna_app_key:
            jobs.extend(self.fetch_adzuna_jobs(role, results_per_page=min(max_jobs, 20)))
        if self.serpapi_key:
            jobs.extend(self.fetch_serpapi_jobs(role, num=15))
            
        deduped = JobDeduplicator.deduplicate_jobs(jobs)
        logger.info(f"Total deduplicated jobs acquired for role '{role}': {len(deduped)}")
        return deduped[:max_jobs]

    def scrape_all_roles(self, roles: Optional[List[str]] = None, max_per_role: int = 50) -> Dict[str, List[Dict]]:
        """Scrapes job postings for all specified roles."""
        target_roles = roles or DEFAULT_ROLES
        results = {}
        for role in target_roles:
            results[role] = self.scrape_role(role, max_jobs=max_per_role)
        return results

    @staticmethod
    def extract_skills_from_text(text: str, candidate_skills: Set[str]) -> List[str]:
        """Extracts matched skills from a raw job description using case-insensitive boundary search."""
        found = set()
        clean_text = text.lower()
        for skill in candidate_skills:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, clean_text):
                found.add(skill)
        return sorted(list(found))
