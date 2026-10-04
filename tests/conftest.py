import os
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.trustdesk.models.db_models import Base
from src.trustdesk.storage.database import get_db, seed_initial_data
from src.trustdesk.storage.repository import Repository
from src.trustdesk.api.app import app
from src.trustdesk.ai.mock_adapter import MockAIAdapter

TEST_DB_PATH = Path("test_trustdesk.db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

@pytest.fixture(scope="session")
def engine():
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    eng = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=eng)

    SessionClass = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    with SessionClass() as s:
        seed_initial_data(session=s)

    yield eng

    eng.dispose()
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

@pytest.fixture
def test_db(engine):
    SessionClass = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionClass()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def repo(test_db):
    return Repository(test_db)

@pytest.fixture
def mock_ai():
    return MockAIAdapter()

@pytest.fixture
def client(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
