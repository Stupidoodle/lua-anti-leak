import pytest
import redis

from app.core.config import get_settings

settings = get_settings()


@pytest.fixture(autouse=True)
def clear_redis() -> None:
    """Clear Redis before each test"""
    r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
    r.flushall()
    yield
    r.flushall()


@pytest.fixture(autouse=True)
def mock_vault(monkeypatch) -> None:
    """Mock Vault responses"""

    def mock_get_secret(*args, **kwargs) -> str:
        return "test_secret"

    monkeypatch.setattr("app.core.secrets.VaultClient.get_secret", mock_get_secret)
