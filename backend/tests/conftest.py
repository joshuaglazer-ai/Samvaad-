import os

# Tests always run in mock mode on an in-memory database, whatever .env says.
os.environ["LLM_MODE"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["SARVAM_API_KEY"] = ""   # tests never call a real provider, whatever backend/.env says
os.environ["GEMINI_API_KEY"] = ""
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ADMIN_PIN"] = "admin-test"
os.environ["COUNSELLOR_PIN"] = "counsellor-test"

import pytest  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import models  # noqa: E402,F401
from app.db import Base  # noqa: E402
from seed.seed import seed  # noqa: E402


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(eng, "connect")
    def _fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def SessionMaker(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db(SessionMaker):
    s = SessionMaker()
    seed(s)
    yield s
    s.close()


@pytest.fixture()
def client(db, SessionMaker):
    """FastAPI TestClient sharing the seeded in-memory database."""
    from fastapi.testclient import TestClient

    from app.db import get_db, get_session_factory
    from app.main import app

    def _get_db():
        s = SessionMaker()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_session_factory] = lambda: SessionMaker
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
