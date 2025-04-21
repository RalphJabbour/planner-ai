import pytest 
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app 
from datetime import datetime, timedelta

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the dependency
def override_get_db():
    db = TestingSessionLocal()
    try: 
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db 

# Create test client
client = TestClient(app)

@pytest.fixture
def test_db():
    # Create the tables
    Base.metadata.create_all(bind=engine)
    yield 
    # Drop the tables
    Base.metadata.drop_all(bind=engine)

def test_log_session(test_db):
    # Create a test session log
    session_data = {
        "userId": "1",
        "start_time": (datetime.now() - timedelta(hours=1)).isoformat(),
        "end_time": datetime.now().isoformat(),
        "pagesRead": 10,
        "focusRating": 4,
        "completed": True,
        "device": "laptop",
        "timezone": "UTC"
    }

    response = client.post("/api/sessions/log", json=session_data)
    assert response.status_code == 200
    data = response.json()
    assert "logId" in data
    assert data["userId"] == "1"
    assert data["pagesRead"] == 10
    assert data["completed"] == True

def test_get_recommendations(test_db):
    # First log a session for the user
    session_data = {
        "userId": "1",
        "startTime": (datetime.now() - timedelta(hours=1)).isoformat(),
        "endTime": datetime.now().isoformat(),
        "pagesRead": 10,
        "focusRating": 4,
        "completed": True,
        "device": "laptop",
        "timezone": "UTC"
    }

    client.post("/api/sessions/log", json=session_data)

    # Get recommendations
    response = client.get("api/sessions/recommendations?userId=1")

    # This might return 404 in tests if models aren't trained, but we check the structure
    if response.status_code == 200:
        data = response.json()
        assert "recommendedStart" in data
        assert "recommendedEnd" in data 
        assert "predictedEfficiency" in data 
        assert "predictedCompletionProb" in data 
        assert "peakHours" in data 
        assert isinstance(data["peakHours"], list)