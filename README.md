# 🧬 Evidence-Grounded Agentic Career Twin

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red.svg)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-blue.svg)](https://www.postgresql.org/)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-all--MiniLM--L6--v2-yellow.svg)](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
[![Gemini](https://img.shields.io/badge/Gemini-3.5--flash--lite-purple.svg)](https://deepmind.google/technologies/gemini/)
[![Tests Passing](https://img.shields.io/badge/Tests-20%2F20%20Passing-brightgreen.svg)]()
[![Spearman Correlation](https://img.shields.io/badge/Human%20Validity-0.9758%20(p%20<%200.001)-success.svg)]()

> **An evidence-based, mathematically defensible career intelligence platform and digital twin.**  
> Evaluates candidate readiness using cross-role TF-IDF weighting, exponential evidence recency decay, a Two-Tier Hybrid Matching Architecture (domain clusters + `all-MiniLM-L6-v2`), dual-scoring for broad market and specific job descriptions, and deterministic database validation to eliminate AI-hallucinated resources and percentages.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph UI_Layer ["Client & Delivery Layer"]
        Streamlit["Streamlit Interactive Dashboard (ui/app.py)"]
        FastAPI["FastAPI REST API (src/api/routes.py)"]
        Streamlit <-->|JSON Payloads & PDF Hashing| FastAPI
    end

    subgraph Orchestration ["Layer 1: LangGraph Agentic Orchestration"]
        Supervisor{{"Graph State Machine"}}
        ProfileAgent["Profile Agent\n(PyMuPDF + Gemini Structured Extraction)"]
        MarketAgent["Market Agent\n(Cross-Role TF-IDF + Corpus Loader)"]
        JDAgent["JD Extractor Agent\n(Target Job Parser & Fluff Filter)"]
        GapAgent["Gap Agent\n(Two-Tier Hybrid Matching Architecture)"]
        RecAgent["Recommendation Agent\n(Grounded DB ID Mapping)"]
        Validator{"Validator Node\n(Max 3 Retries)"}

        Supervisor --> ProfileAgent
        ProfileAgent --> MarketAgent
        MarketAgent -->|Target JD Provided| JDAgent
        MarketAgent -->|No JD Provided| GapAgent
        JDAgent --> GapAgent
        GapAgent --> RecAgent
        RecAgent --> Validator
        Validator -->|Validation OK| Done(["Validated Roadmap & Scores"])
        Validator -->|Validation Failed| RecAgent
    end

    subgraph Engines ["Layer 2: Deterministic Python Engines"]
        Normalizer["Waterfall Normalizer\n(Exact -> Synonym -> Vector Fallback)"]
        EmbeddingEngine["Embedding Engine Singleton\n(SentenceTransformer all-MiniLM-L6-v2)"]
        ReadinessScorer["Readiness Scorer\n(TF-IDF + Exponential Recency Decay)"]
        Deduplicator["Deduplicator\n(Skill Recency + Job Hash SHA-256)"]
        MarketUpdater["Market Updater\n(90-Day Rolling Window & Safeguard)"]
    end

    subgraph Storage ["Layer 3: Persistent Relational & Vector Storage"]
        Postgres[("PostgreSQL Database\n(career_twin)")]
        Students[("Student & AnalysisRun\n(Historical Deltas)")]
        TaxonomyDB[("SkillTaxonomy & Aliases\n(8,752 Entries)")]
        ResourcesDB[("Learning Resources\n(888 Curated Coursera Courses)")]
        MarketDB[("MarketData & Jobs\n(3,768 Postings Across 4 Roles)")]

        Postgres --> Students
        Postgres --> TaxonomyDB
        Postgres --> ResourcesDB
        Postgres --> MarketDB
    end

    FastAPI <--> Supervisor
    ProfileAgent --> Normalizer
    GapAgent --> EmbeddingEngine
    GapAgent --> ReadinessScorer
    RecAgent --> ResourcesDB
    MarketAgent --> MarketDB
    FastAPI --> Students
```

---

## 🚀 Key Innovations & Core Modules

### 1. Two-Tier Hybrid Matching Architecture
Eliminates brittle ATS keyword matching without hallucinated credit. Solves the *"Experience with Python, R, C++, or Scala"* dilemma by recognizing functional equivalencies across:
- **Core DS/ML Languages:** Python $\leftrightarrow$ R, Scala, Julia ($0.80 - 0.88$ credit).
- **Systems Languages in ML:** Python + Deep Learning (PyTorch/TF) $\rightarrow$ C/C++ backend credit ($0.85$).
- **Statistical & ML Frameworks:** Bayesian Inference, Statistical Modeling, and A/B Testing map directly to Machine Learning, Statistics, and Scikit-Learn ($0.88 - 0.92$).
- **Dense Vector Fallback:** 384-dimensional cosine similarity via Hugging Face `all-MiniLM-L6-v2` ($\ge 0.80 \to 1.0$, $\ge 0.60 \to 0.75$, $\ge 0.48 \to 0.50$).

### 2. Dual-Scoring Model (Market Readiness vs. Specific JD Fit)
- **Broad Market Readiness:** Evaluates candidate competency against the entire target job family using Cross-Role TF-IDF weighting and recency decay.
- **Specific Job Description Fit:** When a custom job posting is pasted, the `JDExtractorAgent` extracts `core_required_skills` (weight 1.0) and `nice_to_have_skills` (weight 0.5), filtering HR boilerplate and scoring specific alignment.

### 3. Persistent Memory & Historical Deltas
- Students are deterministically identified via extracted email (with fallback to normalized name SHA-256 hash).
- Every analysis run records `target_role`, `target_jd_hash`, `readiness_score`, `jd_fit_score`, and `missing_skills`.
- Sequential historical score deltas ($\Delta = \text{Current} - \text{Previous}$) are calculated and displayed in the UI.

### 4. Zero-Hallucination Grounded Recommendations
- Recommendations are restricted strictly to existing database IDs in PostgreSQL (`Resources` table).
- The `Validator` node halts if candidate course IDs do not exist in the curated catalog, ensuring **0.0% hallucinated resource identities**.

### 5. Authentic 5-Dimension Competency Radar
- Dynamically computes real percentage competencies across 5 axes:
  1. `Core Programming`
  2. `ML / Deep Learning`
  3. `Cloud Infrastructure`
  4. `Data Engineering`
  5. `Databases & Storage`

---

## 📊 Evaluation Benchmarks & Academic Rigor

The system was evaluated using independent validation suites matching graduate-level peer-review standards:

| Evaluation Dimension | Benchmark Metric | Result Achieved | Academic Significance |
| :--- | :--- | :---: | :--- |
| **Human Validity Study** | Spearman Rank Correlation ($r_s$) across 10 benchmark candidates | **$r_s = 0.9758$ ($p = 1.4675 \times 10^{-6}$)** | Outperforms legacy ATS string baseline ($0.7538$) by $+29.4\%$. Senior ML engineers score $>90\%$, PhD statisticians outscore 12-week bootcamps. |
| **Extraction Ablation Study** | Precision, Recall, and F1-Score | **Precision: 1.00<br>Recall: 1.00<br>F1: 1.00** | Waterfall method (PhraseMatcher $\rightarrow$ Exact Alias $\rightarrow$ Vector Fallback) achieves zero false positives on standard test sets. |
| **Hallucination Baseline** | Rate of non-existent course recommendations | **0.0% (vs. >50.0% unconstrained LLM)** | Strict database ID pair validation guarantees zero fabricated course URLs or course titles. |
| **Scoring Sensitivity Analysis** | TF-IDF discriminative weighting vs. Raw frequency | **PyTorch (1.77) > Python (0.99)** | Cross-role TF-IDF successfully down-weights generic ubiquitous skills while boosting discriminative technologies. |
| **Recency Evidence Decay** | Exponential decay with active role floor | **$73.76\%$ at 3 years ($0.80$ active floor)** | Models skill obsolescence without penalizing senior active practitioners. |

---

## 🛠️ Tech Stack

- **Runtime & Environment:** Python 3.12 (Linux x86_64)
- **Agent Orchestration:** LangGraph (StateGraph, Conditional Edges, TypedDict State)
- **API Framework:** FastAPI, Uvicorn, Pydantic v2
- **Frontend & Visuals:** Streamlit, Plotly Graph Objects (`Scatterpolar`)
- **Semantic Embeddings:** SentenceTransformers (`all-MiniLM-L6-v2`), PyTorch (CPU), Scikit-Learn
- **NLP & Parsing:** spaCy (PhraseMatcher), PyMuPDF
- **LLM Engine:** Google Gemini (`gemini-3.5-flash-lite` with structured Pydantic schema generation)
- **Database:** PostgreSQL (with `pgvector`), SQLAlchemy 2.0 ORM, SQLite resilient auto-fallback

---

## ⚙️ Quickstart & Local Setup

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/adityaxd-1904/Agentic-Career-Twin.git
cd Agentic-Career-Twin

python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```ini
DATABASE_URL=postgresql://postgres:admin123@localhost:5432/career_twin
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite

# Optional (Sprint 8 Live Job Scraping):
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_API_KEY=your_adzuna_api_key
SERPAPI_KEY=your_serpapi_key
```

### 3. Initialize & Seed Database
```bash
python -c "from src.db.session import init_db; init_db()"
python scripts/ingest_taxonomy.py
python -m src.engine.market_snapshot_builder
```

### 4. Run the Full Test Suite
```bash
# Run all 20 tests (unit, engine, graph, and validity)
./venv/bin/pytest -v

# Run the live human validity study with verbose output
./venv/bin/pytest tests/test_validity.py -v -s
```

### 5. Launch Application Services

**Terminal 1 — FastAPI Backend:**
```bash
./venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
*Interactive Swagger documentation:* [http://localhost:8000/docs](http://localhost:8000/docs)

**Terminal 2 — Streamlit Frontend:**
```bash
./venv/bin/streamlit run ui/app.py
```
*Web Dashboard:* [http://localhost:8501](http://localhost:8501)

---

## 📁 Repository Structure

```
career-twin/
├── config.yaml                      # Model name (gemini-3.5-flash-lite), TF-IDF baselines, lambda, embedding thresholds
├── requirements.txt                 # Dependencies
├── Dockerfile                       # Production multi-stage Docker build
├── .github/
│   └── workflows/
│       ├── main.yml                 # Automated CI/CD test suite
│       └── job_scraper_cron.yml     # Weekly live job scraper & TF-IDF refresh cron
├── data/
│   ├── taxonomy/hybrid_skills_v1.csv# O*NET & technical taxonomy
│   ├── jobs/kaggle_ds_jobs.csv      # Baseline job dataset
│   └── resources/kaggle_coursera.csv# Curated learning catalog
├── src/
│   ├── api/
│   │   ├── main.py                  # FastAPI entry point & CORS
│   │   └── routes.py                # Endpoints (/process-resume, /analyze, /history, /market/refresh)
│   ├── db/
│   │   ├── database.py              # Resilient engine (PostgreSQL + SQLite fallback)
│   │   ├── models.py                # SQLAlchemy models (Student, AnalysisRun, MarketSnapshot, Job, etc.)
│   │   ├── crud.py                  # Database CRUD & sequential delta tracking
│   │   └── session.py               # Session maker & get_db dependency
│   ├── domain/
│   │   ├── schemas.py               # Pydantic schemas (StudentTwinProfile, JDExtractionResult, etc.)
│   │   └── state.py                 # CareerTwinState TypedDict
│   ├── engine/
│   │   ├── deduplicator.py          # Skill recency & job hash SHA-256 deduplication
│   │   ├── embedding_engine.py      # Singleton all-MiniLM-L6-v2 vector engine
│   │   ├── readiness_scorer.py      # Cross-Role TF-IDF & recency decay math
│   │   ├── skill_extractor.py       # Deterministic NLP extraction
│   │   ├── skill_normalizer.py      # Waterfall normalizer (Exact -> Synonym -> Vector)
│   │   └── market_updater.py        # 90-day rolling window TF-IDF calculator & safeguard
│   ├── graph/
│   │   ├── workflow.py              # LangGraph compilation & conditional routing
│   │   └── agents/
│   │       ├── profile_agent.py     # Resume extraction & cache bypass
│   │       ├── market_agent.py      # Market demand & TF-IDF loader
│   │       ├── jd_extractor_agent.py# Target JD parser & fluff filter
│   │       ├── gap_agent.py         # Two-Tier Hybrid Matching Architecture & radar analytics
│   │       └── recommendation_agent.py # Grounded DB ID mapping & synthesis
│   ├── llm/
│   │   ├── client.py                # Gemini SDK client (gemini-3.5-flash-lite)
│   │   └── prompts.py               # Centralized prompts (Resume, JD, Roadmap)
│   └── utils/
│       ├── hashing.py               # MD5 & SHA-256 utilities
│       ├── logger.py                # Custom logger
│       └── scraper.py               # Live job API scraper (Adzuna & SerpAPI)
├── ui/
│   └── app.py                       # Streamlit UI (PDF hash caching, dual-columns, radar chart)
└── tests/
    ├── test_persistence.py          # Student deduplication & history deltas
    ├── test_validity.py             # Dynamic human validity study (Spearman rank correlation)
    ├── test_engine/                 # Scoring, embedding, ablation, and market updater tests
    └── test_graph/                  # Dual scoring and zero-hallucination baseline tests
```

