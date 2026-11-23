import os
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app

# Create a temporary directory for test storage
TEST_STORAGE_DIR = Path(tempfile.mkdtemp(prefix="attendance_gate_test_"))
settings.STORAGE_DIR = TEST_STORAGE_DIR
settings.RAW_STORAGE_DIR = TEST_STORAGE_DIR / "raw"
settings.CLEANED_STORAGE_DIR = TEST_STORAGE_DIR / "cleaned"
settings.init_storage()

# Use an in-memory SQLite database with StaticPool for test isolation
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test database tables and teardown temp storage on finish."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if TEST_STORAGE_DIR.exists():
        shutil.rmtree(TEST_STORAGE_DIR, ignore_errors=True)


@pytest.fixture
def db_session():
    """Yield an isolated database session per test with rollback."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Provide a FastAPI TestClient with the test DB session override."""
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
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).resolve().parent.parent / "fixtures"
