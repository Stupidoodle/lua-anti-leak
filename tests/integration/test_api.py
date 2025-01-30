import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings

settings = get_settings()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_rate_limiting(client) -> None:
    """Test rate limiting functionality"""
    assert hasattr(app.state, "redis")

    for _ in range(settings.RATE_LIMIT):
        response = client.post(
            f"{settings.API_V1_STR}/auth/auth",
            json={"user_id": 1, "username": "test_user"},
        )
        assert response.status_code != 429

    response = client.post(
        f"{settings.API_V1_STR}/auth/auth",
        json={"user_id": 1, "username": "test_user"},
    )
    assert response.status_code == 429
    assert "retry_after" in response.json()["detail"]


def test_request_validation() -> None:
    """Test request validation"""
    # Test payload size limit
    large_data = "x" * (settings.MAX_REQUEST_SIZE + 1)
    response = client.post("/api/v1/auth/auth", json={"data": large_data})
    assert response.status_code == 413

    # Test JSON depth limit
    deep_json = {}
    current = deep_json
    for _ in range(settings.MAX_JSON_DEPTH + 1):
        current["nested"] = {}
        current = current["nested"]

    response = client.post("/api/v1/auth/auth", json=deep_json)
    assert response.status_code == 400


def test_health_check() -> None:
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert all(
        service in data["services"] for service in ["database", "redis", "vault"]
    )


def test_authentication_flow() -> None:
    """Test complete authentication flow"""
    # Create test user
    # Note: This would require setting up test database

    # Attempt authentication
    response = client.post(
        "/api/v1/auth/auth", json={"user_id": 1, "username": "test_user"}
    )
    assert response.status_code == 200
    assert "session_token" in response.json()

    # Use token for subsequent request
    token = response.json()["session_token"]
    response = client.get("/api/v1/script/script_chunk/0", params={"token": token})
    assert response.status_code == 200
