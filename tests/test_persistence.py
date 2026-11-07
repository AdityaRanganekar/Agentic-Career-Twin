import pytest
from src.db.crud import (
    get_or_create_student,
    get_latest_analysis_run,
    create_analysis_run,
    upsert_student_twin
)
from src.db.models import StudentTwin

def test_student_get_or_create(db_session):
    # Create student on first call
    student1 = get_or_create_student(db_session, name="Jane Doe", email="Jane.Doe@Example.com")
    assert student1.id is not None
    assert student1.email == "jane.doe@example.com"
    assert student1.name == "Jane Doe"

    # Same email with different casing/spacing returns identical student record
    student2 = get_or_create_student(db_session, name="Jane Doe", email="  jane.doe@example.com  ")
    assert student2.id == student1.id

def test_student_fallback_email_for_unknown(db_session):
    student = get_or_create_student(db_session, name="John Smith", email="Unknown")
    assert student.id is not None
    assert student.email.endswith("@twin.local")

    # Re-uploading with same name generates matching identifier
    student_same = get_or_create_student(db_session, name="John Smith", email="")
    assert student_same.id == student.id

def test_analysis_run_history_and_delta(db_session):
    student = get_or_create_student(db_session, name="Alex Vance", email="alex@vance.com")
    role = "Machine Learning Engineer"

    # Initially, no prior runs exist
    initial_prior = get_latest_analysis_run(db_session, student_id=student.id, target_role=role)
    assert initial_prior is None

    # First run (Initial Baseline)
    run1 = create_analysis_run(
        db=db_session,
        student_id=student.id,
        target_role=role,
        score=65.0,
        gaps=["PyTorch", "Docker"]
    )
    assert run1.id is not None
    assert run1.readiness_score == 65.0

    # Query latest run
    latest = get_latest_analysis_run(db_session, student_id=student.id, target_role=role)
    assert latest.id == run1.id

    # Second run after candidate completes PyTorch course (+15% score)
    current_score = 80.0
    delta = round(current_score - latest.readiness_score, 2)
    assert delta == 15.0

    run2 = create_analysis_run(
        db=db_session,
        student_id=student.id,
        target_role=role,
        score=current_score,
        gaps=["Docker"],
        jd_fit_score=75.0,
        target_jd_hash="hash_ml_engineer_jd"
    )

    # Latest should now be run2
    latest_after_run2 = get_latest_analysis_run(db_session, student_id=student.id, target_role=role)
    assert latest_after_run2.id == run2.id
    assert latest_after_run2.readiness_score == 80.0
    assert latest_after_run2.jd_fit_score == 75.0
    assert latest_after_run2.target_jd_hash == "hash_ml_engineer_jd"

def test_student_twin_persistence(db_session):
    email = "alex.mercer@gmail.com"
    skills = ["Python", "PyTorch", "SQL"]
    role = "Machine Learning Engineer"

    twin = upsert_student_twin(
        db=db_session,
        student_email=email,
        current_skills=skills,
        target_role=role,
        experience_level="Senior"
    )
    assert twin.id is not None
    assert twin.student_id == email
    assert "Python" in twin.current_skills
    assert role in twin.target_roles

    # Subsequent update adds new skills and roles without duplicating
    twin2 = upsert_student_twin(
        db=db_session,
        student_email=email,
        current_skills=["Python", "PyTorch", "SQL", "Docker", "AWS"],
        target_role="AI / LLM Engineer",
        experience_level="Principal"
    )
    assert twin2.id == twin.id
    assert len(twin2.current_skills) == 5
    assert "AI / LLM Engineer" in twin2.target_roles
    assert "Machine Learning Engineer" in twin2.target_roles


