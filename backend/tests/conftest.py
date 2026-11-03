"""Pytest configuration and common fixtures."""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.database import Base, get_db
import app.models  # Register all models on Base.metadata
from app.main import app
from app.core.security import (
    create_access_token,
    ROLE_SENIOR_UNDERWRITER,
    ROLE_ADMIN,
    ROLE_CREDIT_UNDERWRITER,
    ROLE_RISK_COMMITTEE_MEMBER,
)

# In-memory SQLite database for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables in memory once for the test session and seed initial demo cases."""
    from app.core.config import settings
    settings.RATE_LIMIT_ENABLED = False
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    from app.core.seed import seed_demonstration_cases
    seed_demonstration_cases(session)
    session.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Yield a transactional in-memory database session."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def auth_headers():
    """Header with valid JWT for SENIOR_UNDERWRITER."""
    token = create_access_token({
        "sub": "v.sundaram",
        "name": "V. Sundaram",
        "role": ROLE_SENIOR_UNDERWRITER,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    """Header with valid JWT for ADMIN."""
    token = create_access_token({
        "sub": "admin",
        "name": "System Administrator",
        "role": ROLE_ADMIN,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def underwriter_headers():
    """Header with valid JWT for CREDIT_UNDERWRITER."""
    token = create_access_token({
        "sub": "underwriter",
        "name": "Credit Underwriter",
        "role": ROLE_CREDIT_UNDERWRITER,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def unauthenticated_client(db_session):
    """Provide a TestClient without default Authorization header."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client(db_session, auth_headers):
    """Provide a TestClient with database session override and authenticated default header."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, headers=auth_headers) as test_client:
        yield test_client
    app.dependency_overrides.clear()

