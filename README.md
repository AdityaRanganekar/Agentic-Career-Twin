# Agentic Career Twin

## Executive Summary

Agentic Career Twin is a full-stack, evidence-grounded career readiness assessment platform that constructs a persistent digital twin of a candidate's professional profile. It ingests resumes (PDF, DOCX, TXT), extracts structured competency data using Google Gemini, and evaluates the candidate against real-time job market requirements or specific job descriptions using a multi-agent LangGraph orchestration pipeline.

The system solves a concrete problem: objectively quantifying how prepared a candidate is for a target role, identifying precise skill gaps, and generating actionable, multi-platform learning roadmaps -- all grounded in verifiable evidence rather than subjective self-assessment.

The backend employs a six-agent directed acyclic graph (ProfileAgent, MarketAgent, JDExtractorAgent, GapAgent, RecommendationAgent, Validator) with a retry loop, a three-tier hybrid skill matching architecture (exact/token match, database taxonomy lookup, dense semantic vector similarity via all-MiniLM-L6-v2), TF-IDF cross-role market weighting, exponential recency decay scoring, and a project quality evaluation pipeline. The frontend provides a React/TypeScript dashboard with competency radar charts, score gauges, evidence breakdowns, historical assessment tracking, and a multi-platform learning hub.

---

## System Architecture

```mermaid
graph TB
    subgraph "Frontend — React / TypeScript / Vite"
        UI["Single-Page Application"]
        AuthCtx["AuthContext — Session Management"]
        API_SVC["API Service Layer — Axios"]
        Dashboard["DashboardView — Resume Upload and Score Display"]
        Roadmap["RoadmapView — Multi-Platform Learning Hub"]
        History["HistoryView — Assessment Trajectory"]
        Radar["CompetencyRadar — Recharts"]
        Gauge["ScoreGauge — Animated Readiness Dial"]
        Evidence["EvidenceBreakdown — Project Quality Metrics"]
    end

    subgraph "Backend — FastAPI / Python 3.12"
        APIGateway["FastAPI Router — /api/v1"]
        AuthEndpoints["Authentication — Bcrypt and Google OAuth 2.0"]
        ResumeEndpoint["POST /process-resume — Multipart Upload"]
        HistoryEndpoint["GET /history/{id} — Run Archive"]

        subgraph "LangGraph Orchestration Engine"
            ProfileAgent["ProfileAgent — Resume Parsing and Skill Extraction"]
            MarketAgent["MarketAgent — TF-IDF Market Weight Discovery"]
            JDExtractor["JDExtractorAgent — Job Description Requirement Extraction"]
            GapAgent["GapAgent — Hybrid Skill Coverage Evaluation"]
            RecAgent["RecommendationAgent — Multi-Platform Study Guide"]
            Validator["Validator — Retry Loop with 3-Attempt Cap"]
        end

        subgraph "Engine Layer"
            EmbeddingEngine["EmbeddingEngine — all-MiniLM-L6-v2 ONNX"]
            TaxonomyEngine["TaxonomyConceptEngine — PostgreSQL Taxonomy"]
            ReadinessScorer["ReadinessScorer — TF-IDF Weighted Decay Scoring"]
            ProjectEval["ProjectEvaluator — 3-Pillar Evidence Quality"]
            SkillNormalizer["SkillNormalizer — Canonical Casing"]
            Deduplicator["Deduplicator — Semantic Deduplication"]
        end
    end

    subgraph "Data Layer"
        PostgreSQL["PostgreSQL — Neon Serverless"]
        SQLite["SQLite — Local Development Fallback"]
        DVC["DVC — Dataset Version Control"]
    end

    subgraph "External Services"
        Gemini["Google Gemini API — Structured Extraction"]
        GoogleOAuth["Google OAuth 2.0 — Identity Verification"]
        MOOC["MOOC Platforms — Udemy, Coursera, edX, YouTube"]
    end

    UI --> API_SVC
    API_SVC --> APIGateway
    APIGateway --> AuthEndpoints
    APIGateway --> ResumeEndpoint
    APIGateway --> HistoryEndpoint

    ResumeEndpoint --> ProfileAgent
    ProfileAgent --> MarketAgent
    ProfileAgent --> JDExtractor
    MarketAgent --> JDExtractor
    MarketAgent --> GapAgent
    JDExtractor --> GapAgent
    GapAgent --> RecAgent
    RecAgent --> Validator
    Validator -->|"Retry"| RecAgent
    Validator -->|"Pass"| ResumeEndpoint

    ProfileAgent --> Gemini
    JDExtractor --> Gemini
    RecAgent --> Gemini
    MarketAgent --> TaxonomyEngine
    GapAgent --> EmbeddingEngine
    GapAgent --> TaxonomyEngine
    GapAgent --> ReadinessScorer
    GapAgent --> ProjectEval

    AuthEndpoints --> GoogleOAuth
    RecAgent --> MOOC

    TaxonomyEngine --> PostgreSQL
    ReadinessScorer --> PostgreSQL
    MarketAgent --> PostgreSQL
    ProfileAgent --> PostgreSQL
    PostgreSQL -.->|"Fallback"| SQLite
```

The architecture separates concerns into four layers:

- **Frontend**: A statically deployed React SPA (Vercel) that communicates with the backend exclusively through REST API calls. Handles authentication state, result visualization, and navigation.
- **Backend API**: A FastAPI application exposing authentication, resume analysis, and history endpoints. On each analysis request, it compiles and invokes the LangGraph state machine, then persists results to the database.
- **LangGraph Orchestration**: A six-node directed acyclic graph with conditional routing. The ProfileAgent extracts structured data; the MarketAgent retrieves or computes TF-IDF market weights; the JDExtractorAgent parses custom job descriptions; the GapAgent performs hybrid skill matching and readiness scoring; the RecommendationAgent generates multi-platform study guides; and the Validator enforces a retry loop (capped at 3 attempts) to ensure recommendation completeness.
- **Data Layer**: PostgreSQL (Neon Serverless in production) stores students, analysis runs, digital twin state, market snapshots, job postings, skill taxonomies, and learning resources. Automatic fallback to local SQLite ensures the system remains operational without a PostgreSQL connection.

---

## Core Features

- **Structured Resume Parsing**: Extracts candidate name, contact, education, experience, projects, and granular skill evidence (with dates and sources) from PDF, DOCX, and TXT files using Google Gemini structured output.
- **Dual-Scoring Architecture**: Independently evaluates candidates against (a) broad market discipline requirements via TF-IDF weighting and (b) specific uploaded job descriptions, producing separate readiness and fit scores.
- **Three-Tier Hybrid Skill Matching**: Combines exact token matching, database-driven canonical taxonomy alias resolution (27+ concept clusters with 300+ aliases), and dense semantic vector similarity (all-MiniLM-L6-v2, 384-dimensional embeddings) to accurately map candidate skills to requirements.
- **Exponential Recency Decay**: Applies configurable time-decay (lambda = 0.15 by default) to skill evidence, penalizing stale competencies and rewarding recent, active usage.
- **Dynamic Competency Radar**: Generates Top-5 role-specific competency categories with per-category coverage scores, rendered as interactive radar charts on the frontend.
- **3-Pillar Project Quality Evaluation**: Assesses resume evidence across quantitative metrics, production deployment proof, and role alignment scoring dimensions.
- **Domain-Agnostic Seniority Modifier**: Computes a semantic role alignment score via cosine similarity between the candidate profile summary and the target role profile, combined with degree credentials and experience signals. No hardcoded domain strings.
- **Read-Through Market Cache with TTL**: Caches role market snapshots in PostgreSQL with configurable TTL (365 days). Cache misses trigger live web role discovery and persist results for subsequent requests at zero token cost.
- **Multi-Platform Learning Roadmaps**: For each identified skill gap, generates deterministic search URLs across Udemy, Coursera, edX, YouTube, and official documentation, enriched with LLM-synthesized study justifications and sub-topic curricula.
- **Persistent Digital Twin**: Maintains a living `student_twins` record per candidate, tracking current skills, target roles, and experience level across sessions.
- **Historical Assessment Tracking**: Stores every analysis run with score deltas, enabling candidates to track readiness improvement over time.
- **Authentication**: Supports local account registration (bcrypt password hashing) and Google OAuth 2.0 server-side code exchange.
- **Resilient LLM Client**: Wraps the Gemini API with strict 22-second deadlines, automatic fallback to gemini-1.5-flash on rate limits, and fast-failure on DNS/network errors.

---

## Tech Stack

### Backend

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web Framework | FastAPI 0.110+ with Uvicorn ASGI |
| Agentic Orchestration | LangGraph 0.0.26+, LangChain Core 0.1.30+ |
| LLM Provider | Google Gemini API (gemini-3.5-flash-lite default, gemini-1.5-flash fallback) |
| Embedding Model | all-MiniLM-L6-v2 via FastEmbed ONNX (384-dimensional, CPU-optimized) |
| Database ORM | SQLAlchemy 2.0+ |
| Database | PostgreSQL (Neon Serverless) with SQLite fallback |
| NLP / Parsing | PyMuPDF (PDF extraction), spaCy 3.7+ |
| Data Processing | Pandas, NumPy, SciPy, scikit-learn |
| Authentication | bcrypt, Google OAuth 2.0 (server-side code exchange) |
| Configuration | Pydantic Settings, python-dotenv, PyYAML |
| Data Versioning | DVC |
| Testing | pytest, pytest-asyncio |

### Frontend

| Layer | Technology |
|---|---|
| Language | TypeScript 5.7 |
| UI Framework | React 18.3 |
| Build Tool | Vite 5.4 |
| Styling | Tailwind CSS 3.4 |
| Charts | Recharts 2.15 (radar, gauges) |
| Animation | Framer Motion 11.18 |
| Icons | Lucide React |
| HTTP Client | Axios 1.7 |

### Infrastructure

| Component | Technology |
|---|---|
| Backend Hosting | Render (Docker), Hugging Face Spaces |
| Frontend Hosting | Vercel |
| CI/CD | GitHub Actions (3-job pipeline: pytest, Vite build, deploy) |
| Containerization | Docker (Python 3.12-slim, pre-baked ONNX model) |

---

## Data Flow / Workflow

```mermaid
sequenceDiagram
    actor User
    participant Frontend as React SPA
    participant API as FastAPI Backend
    participant Profile as ProfileAgent
    participant Market as MarketAgent
    participant JD as JDExtractorAgent
    participant Gap as GapAgent
    participant Rec as RecommendationAgent
    participant Val as Validator
    participant Gemini as Google Gemini API
    participant DB as PostgreSQL
    participant Embed as EmbeddingEngine

    User->>Frontend: Upload Resume PDF + Select Target Role
    Frontend->>API: POST /api/v1/process-resume (multipart/form-data)
    API->>API: Extract text from PDF/DOCX/TXT
    API->>Profile: Invoke LangGraph State Machine

    Profile->>Gemini: Structured extraction (StudentTwinProfile schema)
    Gemini-->>Profile: Name, education, experience, projects, skills with dates
    Profile->>DB: Normalize skills against taxonomies table

    alt Target Role Provided
        Profile->>Market: Route to MarketAgent
        Market->>DB: Check MarketSnapshot cache (TTL lookup)
        alt Cache Hit
            DB-->>Market: Return cached TF-IDF weights
        else Cache Miss
            Market->>Market: Live Web Role Discovery
            Market->>DB: Persist new MarketSnapshot
        end
    end

    alt Job Description Provided
        Market->>JD: Route to JDExtractorAgent
        JD->>Gemini: Extract core and nice-to-have skills (JDExtractionResult)
        Gemini-->>JD: Weighted skill requirements
        JD->>DB: Consolidate via taxonomy aliases
    end

    JD->>Gap: Forward extracted requirements
    Market->>Gap: Forward TF-IDF market weights

    Gap->>Embed: Compute semantic similarity matrix (all-MiniLM-L6-v2)
    Gap->>DB: Query taxonomy aliases for concept matching
    Gap->>Gap: Three-tier hybrid matching (exact, taxonomy, semantic)
    Gap->>Gap: Apply recency decay + seniority modifier
    Gap->>Gap: Evaluate 3-pillar project quality
    Gap->>Gap: Compute readiness score + radar dimensions

    Gap->>Rec: Pass missing skills list
    Rec->>Gemini: Generate study justifications (MultiSkillStudyGuide)
    Rec->>Rec: Build multi-platform search URLs (Udemy, Coursera, edX, YouTube, Docs)

    Rec->>Val: Forward recommendations
    Val->>Val: Validate completeness

    alt Validation Failed and Retries < 3
        Val->>Rec: Retry recommendation generation
    end

    Val-->>API: Return final state
    API->>DB: Persist AnalysisRun + upsert StudentTwin
    API->>DB: Compute score delta vs. previous run
    API-->>Frontend: JSON response (scores, gaps, radar, recommendations)
    Frontend->>User: Render dashboard with radar chart, score gauge, roadmap
```

---

## Prerequisites

| Tool | Minimum Version | Purpose |
|---|---|---|
| Python | 3.12+ | Backend runtime |
| Node.js | 20+ | Frontend build toolchain |
| npm | 10+ | Frontend dependency management |
| PostgreSQL | 14+ | Production database (optional; SQLite fallback available) |
| Git | 2.30+ | Source control |
| Docker | 24+ | Containerized deployment (optional) |

A Google Gemini API key is required for LLM-powered extraction and recommendation synthesis. The system includes deterministic fallbacks for offline/sandboxed operation, but core functionality depends on API access.

---

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/Agentic-Career-Twin.git
cd Agentic-Career-Twin
```

### 2. Backend Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Pre-cache the ONNX embedding model (one-time download, approximately 80 MB):

```bash
python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2')"
```

### 3. Frontend Setup

```bash
cd frontend
npm ci
cd ..
```

### 4. Environment Configuration

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Edit both `.env` files with your credentials (see Environment Variables section below).

### 5. Database Initialization

The database schema is automatically created and seeded with baseline taxonomy and market data on first application startup via `init_db()`. No manual migration commands are required.

For PostgreSQL, ensure the database exists:

```bash
createdb career_twin
```

If no PostgreSQL instance is available, the application automatically falls back to a local SQLite database (`career_twin.db`).

---

## Environment Variables

### Backend (.env)

| Variable | Purpose | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string. Append `?sslmode=require` for Neon. | `postgresql://user:pass@host/career_twin?sslmode=require` |
| `GEMINI_API_KEY` | Google Gemini API key for LLM extraction and synthesis. | `AIzaSy...` |
| `GEMINI_MODEL` | Gemini model identifier. Defaults to `gemini-3.5-flash-lite`. | `gemini-3.5-flash-lite` |
| `FRONTEND_URL` | Frontend origin for CORS whitelist configuration. | `http://localhost:5173` |
| `GOOGLE_CLIENT_ID` | Google OAuth 2.0 Web Client ID (optional). | `123456.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 2.0 Client Secret (optional). | `GOCSPX-...` |
| `GOOGLE_REDIRECT_URI` | OAuth redirect URI. Must match Google Cloud Console configuration. | `http://localhost:5173` |
| `PORT` | Server port. Defaults to `8000` locally, `7860` on Hugging Face Spaces. | `8000` |

### Frontend (frontend/.env)

| Variable | Purpose | Example |
|---|---|---|
| `VITE_API_BASE_URL` | Backend API base URL including `/api/v1` path. | `http://localhost:8000/api/v1` |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth 2.0 Web Client ID for frontend Sign-In button (optional). | `123456.apps.googleusercontent.com` |

---

## Running the Application

### Development Mode

Start the backend and frontend in separate terminals:

```bash
# Terminal 1: Backend API server (auto-reload enabled)
source venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# Terminal 2: Frontend development server
cd frontend
npm run dev
```

The backend API will be available at `http://localhost:8000` and the frontend at `http://localhost:5173`.

### Production Mode (Docker)

```bash
docker build -t career-twin-api .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e GEMINI_API_KEY="..." \
  -e FRONTEND_URL="https://your-frontend.vercel.app" \
  career-twin-api
```

```bash
# Frontend production build (deploy dist/ to Vercel or any static host)
cd frontend
npm run build
npm run preview  # Local preview of production build
```

### Running Tests

```bash
source venv/bin/activate
export PYTHONPATH=.
pytest -v --tb=short
```

The test suite includes mathematical validity checks, scoring ablation tests, hallucination baselines, embedding engine verification, dual-scoring integration tests, authentication and history persistence tests, and non-technical domain generalization tests.

---

## Usage / API Overview

### Health Check

```
GET /health
```

```json
{
  "status": "online",
  "service": "Agentic Career Twin API",
  "version": "2.0.0"
}
```

### Authentication

**Register a new account:**

```
POST /api/v1/auth/signup
Content-Type: application/json

{
  "name": "Jane Doe",
  "username": "janedoe",
  "email": "jane@example.com",
  "password": "securepassword"
}
```

**Login with credentials:**

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "identifier": "janedoe",
  "password": "securepassword"
}
```

**Google OAuth 2.0 (server-side code exchange):**

```
GET  /api/v1/auth/google-url         # Returns OAuth authorization URL
POST /api/v1/auth/google              # Exchanges authorization code for identity
```

### Resume Analysis

```
POST /api/v1/process-resume
Content-Type: multipart/form-data

file:            <resume.pdf>
target_role:     "Data Scientist"
service_mode:    "discipline"          # "discipline" or "jd"
jd_file:         <job_description.pdf> # Optional: target JD for dual scoring
target_jd_text:  "..."                 # Optional: pasted JD text alternative
authenticated_student_id: 1            # Optional: link to authenticated user
```

**Response (abbreviated):**

```json
{
  "student_id": 1,
  "student_name": "Jane Doe",
  "readiness_score": 72.45,
  "score_delta": 4.2,
  "previous_timestamp": "2026-11-01T10:30:00",
  "missing_skills": ["Apache Spark", "MLOps", "Kubernetes"],
  "jd_fit_score": 68.3,
  "jd_missing_skills": ["Terraform", "Monitoring"],
  "radar_dimensions": {
    "Machine Learning & AI": 85.2,
    "Core Programming": 92.0,
    "Cloud & DevOps": 45.8,
    "Data Engineering": 38.5,
    "Generative AI & LLMs": 71.0
  },
  "project_quality_score": 78.5,
  "recommendations": [
    {
      "skill": "Apache Spark",
      "gap_type": "Role Gap",
      "course_title": "Apache Spark -- Multi-Platform Learning Path",
      "url": "https://www.udemy.com/courses/search/?src=ukw&q=Apache+Spark",
      "platform_links": [
        {"platform": "Udemy", "url": "..."},
        {"platform": "Coursera", "url": "..."},
        {"platform": "edX", "url": "..."},
        {"platform": "YouTube", "url": "..."},
        {"platform": "Documentation", "url": "..."}
      ],
      "justification": "Mastering Apache Spark is essential for Data Scientist roles...",
      "key_topics": ["Core architecture...", "Practical implementation...", "Production deployment..."]
    }
  ],
  "market_corpus_version": "2026-Live"
}
```

### Historical Assessment Runs

```
GET /api/v1/history/{student_id_or_email_or_username}
```

Returns a chronologically ordered array of all previous analysis runs for the specified candidate, including scores, gaps, recommended resources, and timestamps.

---

## Project Structure

```
Agentic-Career-Twin/
├── src/
│   ├── api/                    # FastAPI application, routes, and request/response schemas
│   ├── db/                     # SQLAlchemy models, CRUD operations, database initialization
│   ├── domain/                 # Pydantic domain schemas and LangGraph state definition
│   ├── engine/                 # Embedding engine, readiness scorer, taxonomy, project evaluator
│   ├── graph/
│   │   ├── agents/             # Six LangGraph agent implementations
│   │   └── workflow.py         # State machine compilation and conditional routing
│   ├── llm/                    # Gemini client wrapper, prompt templates, extraction parser
│   └── utils/                  # Logger, hashing, web scraper utilities
├── frontend/
│   └── src/
│       ├── components/         # Radar chart, score gauge, evidence breakdown, sidebar, header
│       ├── context/            # Authentication and theme context providers
│       ├── services/           # Axios API client layer
│       ├── types/              # TypeScript interface definitions
│       └── views/              # Dashboard, roadmap, and history view components
├── scripts/                    # Database seeding, taxonomy ingestion, market refresh scripts
├── tests/                      # Pytest suite: validity, scoring, embedding, auth, generalization
├── data/                       # DVC-tracked datasets (jobs, resources, taxonomy)
├── config.yaml                 # LLM model, scoring parameters, embedding thresholds
├── Dockerfile                  # Production Docker image (Python 3.12-slim + ONNX model)
├── render.yaml                 # Render deployment configuration
└── .github/workflows/          # CI/CD: pytest, Vite build, Render/HF deploy
```
