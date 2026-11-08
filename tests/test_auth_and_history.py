import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.db.models import Base, Student, AnalysisRun
from src.db.crud import (
    hash_password,
    verify_password,
    create_student_user,
    authenticate_user,
    authenticate_or_create_google_user,
    get_student_history,
    create_analysis_run
)
from src.graph.agents.recommendation_agent import (
    clean_skill_for_search,
    build_platform_links,
    generate_deterministic_guidance,
    run_recommendation_agent
)
from src.api.routes import router
from fastapi import FastAPI

from sqlalchemy.pool import StaticPool

# In-memory SQLite session with StaticPool and check_same_thread=False for multi-threaded testing
@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

def test_bcrypt_hashing_and_verification():
    raw_pwd = "SuperSecretPassword123!"
    hashed = hash_password(raw_pwd)

    assert hashed != raw_pwd
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False

def test_student_user_signup_and_login(test_db):
    user = create_student_user(
        db=test_db,
        name="Aditya Ranganekar",
        username="adityar",
        email="aditya@example.com",
        password="ValidPassword2026"
    )

    assert user.id is not None
    assert user.username == "adityar"
    assert user.email == "aditya@example.com"
    assert user.auth_provider == "local"

    # Duplicate email prevention
    with pytest.raises(ValueError, match="already exists"):
        create_student_user(
            db=test_db,
            name="Aditya Copy",
            username="aditya_other",
            email="aditya@example.com",
            password="OtherPassword"
        )

    # Duplicate username prevention
    with pytest.raises(ValueError, match="already taken"):
        create_student_user(
            db=test_db,
            name="Aditya Copy",
            username="adityar",
            email="different@example.com",
            password="OtherPassword"
        )

    # Authenticate via username
    auth_by_user = authenticate_user(test_db, identifier="adityar", password="ValidPassword2026")
    assert auth_by_user is not None
    assert auth_by_user.id == user.id

    # Authenticate via email
    auth_by_email = authenticate_user(test_db, identifier="aditya@example.com", password="ValidPassword2026")
    assert auth_by_email is not None
    assert auth_by_email.id == user.id

    # Reject incorrect password
    failed_auth = authenticate_user(test_db, identifier="adityar", password="WrongPassword")
    assert failed_auth is None

    # Reject nonexistent user
    nonexistent = authenticate_user(test_db, identifier="nobody", password="ValidPassword2026")
    assert nonexistent is None

def test_google_authentication(test_db):
    # First sign in with Google creates account
    g_user = authenticate_or_create_google_user(
        db=test_db,
        email="google.candidate@example.com",
        name="Google Candidate",
        google_id="google_sub_123456"
    )

    assert g_user.id is not None
    assert g_user.email == "google.candidate@example.com"
    assert g_user.auth_provider == "google"
    assert g_user.google_id == "google_sub_123456"

    # Second sign in with same Google account returns existing user
    g_user_2 = authenticate_or_create_google_user(
        db=test_db,
        email="google.candidate@example.com",
        name="Updated Candidate Name",
        google_id="google_sub_123456"
    )

    assert g_user_2.id == g_user.id
    assert g_user_2.google_id == "google_sub_123456"

def test_multi_platform_url_generation():
    # Test query cleaner
    clean_cloud = clean_skill_for_search("Cloud Platforms (AWS / GCP / Azure)")
    assert "AWS" in clean_cloud
    assert "GCP" in clean_cloud
    assert "Azure" in clean_cloud
    assert "(" not in clean_cloud and ")" not in clean_cloud

    clean_rag = clean_skill_for_search("RAG & Vector Databases")
    assert "&" not in clean_rag
    assert "RAG Vector Databases" in clean_rag

    # Test link builder
    links = build_platform_links("RAG & Vector Databases")
    assert len(links) == 5

    platforms = {l["platform"]: l["url"] for l in links}
    assert "Udemy" in platforms
    assert "Coursera" in platforms
    assert "edX" in platforms
    assert "YouTube" in platforms
    assert "Documentation" in platforms

    # Verify query parameters
    assert "https://www.udemy.com/courses/search/?src=ukw&q=" in platforms["Udemy"]
    assert "https://www.coursera.org/search?query=" in platforms["Coursera"]
    assert "https://www.edx.org/search?q=" in platforms["edX"]
    assert "https://www.youtube.com/results?search_query=" in platforms["YouTube"]
    assert "https://www.google.com/search?q=" in platforms["Documentation"]

def test_deterministic_guidance_generation():
    guidance = generate_deterministic_guidance("Vector Databases", "AI Engineer")
    assert len(guidance["key_topics"]) == 3
    assert "Vector Databases" in guidance["justification"]
    assert "AI Engineer" in guidance["justification"]

def test_analysis_run_history_persistence_and_retrieval(test_db):
    user = create_student_user(
        db=test_db,
        name="History Tester",
        username="history_tester",
        email="history@example.com",
        password="Password123"
    )

    mock_resources = [
        {
            "skill": "LangGraph",
            "course_title": "LangGraph — Multi-Platform Learning Path",
            "url": "https://www.udemy.com/courses/search/?src=ukw&q=LangGraph",
            "platform_links": build_platform_links("LangGraph"),
            "justification": "Core agentic workflow framework",
            "key_topics": ["StateGraph", "Checkpointers", "Multi-agent coordination"]
        }
    ]

    run1 = create_analysis_run(
        db=test_db,
        student_id=user.id,
        target_role="AI Engineer",
        score=82.5,
        gaps=["LangGraph", "Docker"],
        jd_fit_score=85.0,
        target_jd_hash="hash123",
        jd_missing_skills=["Docker"],
        recommended_resources=mock_resources,
        project_quality_score=90.0,
        resume_filename="Aditya_Resume_v1.pdf"
    )

    run2 = create_analysis_run(
        db=test_db,
        student_id=user.id,
        target_role="AI Engineer",
        score=91.0,
        gaps=["Docker"],
        jd_fit_score=94.0,
        target_jd_hash="hash123",
        jd_missing_skills=[],
        recommended_resources=mock_resources,
        project_quality_score=95.0,
        resume_filename="Aditya_Resume_v2.pdf"
    )

    # Retrieve history by student ID
    hist_by_id = get_student_history(test_db, str(user.id))
    assert len(hist_by_id) == 2
    assert hist_by_id[0].id == run2.id  # Chronological descending
    assert hist_by_id[0].readiness_score == 91.0
    assert hist_by_id[0].resume_filename == "Aditya_Resume_v2.pdf"
    assert len(hist_by_id[0].recommended_resources) == 1
    assert hist_by_id[0].recommended_resources[0]["skill"] == "LangGraph"

    # Retrieve history by email
    hist_by_email = get_student_history(test_db, "history@example.com")
    assert len(hist_by_email) == 2

    # Retrieve history by username
    hist_by_username = get_student_history(test_db, "history_tester")
    assert len(hist_by_username) == 2

def test_api_endpoints_auth_and_history(test_db):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    
    # Override get_db generator dependency to yield in-memory test_db
    from src.db.database import get_db
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    # 1. Signup endpoint
    signup_resp = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "API User",
            "username": "apiuser",
            "email": "apiuser@example.com",
            "password": "Password2026!"
        }
    )
    assert signup_resp.status_code == 200
    user_data = signup_resp.json()
    assert user_data["username"] == "apiuser"
    assert user_data["email"] == "apiuser@example.com"
    student_id = user_data["student_id"]

    # 2. Login endpoint with username
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": "apiuser", "password": "Password2026!"}
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["student_id"] == student_id

    # 3. Login endpoint with email
    login_email_resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": "apiuser@example.com", "password": "Password2026!"}
    )
    assert login_email_resp.status_code == 200

    # 4. Failed login
    fail_resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": "apiuser", "password": "BadPassword"}
    )
    assert fail_resp.status_code == 401

    # 5. Google Auth URL endpoint
    url_resp = client.get("/api/v1/auth/google-url")
    assert url_resp.status_code == 200
    assert "configured" in url_resp.json()

    # 6. Google Auth Direct endpoint
    g_resp = client.post(
        "/api/v1/auth/google",
        json={"email": "google.api@example.com", "name": "Google API"}
    )
    assert g_resp.status_code == 200
    assert g_resp.json()["auth_provider"] == "google"

    # 7. History endpoint
    hist_resp = client.get(f"/api/v1/history/{student_id}")
    assert hist_resp.status_code == 200
    assert isinstance(hist_resp.json(), list)
