import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base, Taxonomy

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def setup_database():
    """Builds the database schema in memory."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(setup_database):
    """Creates a fresh database session and seeds it with controlled taxonomy data."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
   
    test_skills = [
        Taxonomy(category="language", name="Python", aliases=["py", "python 3", "python3"]),
        Taxonomy(category="framework", name="React", aliases=["react.js", "reactjs", "react js"]),
        Taxonomy(category="database", name="PostgreSQL", aliases=["postgres", "psql", "postgre sql"])
    ]
    session.add_all(test_skills)
    session.commit()
    
    yield session

    session.close()
    transaction.rollback()
    connection.close()