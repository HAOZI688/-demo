"""pytest fixtures — session-level test DB setup.
conftest fixture runs before any test file, avoiding duplication.
test_smoke.py import its own setup_db because conftest is conftest.
"""
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create fresh test DB before any test runs."""
    from app.config import settings
    from app.database import init_db, _seed_defaults
    os.environ["MANJU_DB_PATH"] = "/tmp/manju_test.db"
    settings.DATABASE_URL = "sqlite:////tmp/manju_test.db"
    init_db()
    _seed_defaults()
    yield
    if os.path.exists("/tmp/manju_test.db"):
        os.unlink("/tmp/manju_test.db")
