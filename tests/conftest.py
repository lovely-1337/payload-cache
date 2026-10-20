import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import app
from app.models import Base
from app.transformer import get_transformer


class CountingTransformer:
    """Фейковый transformer: ведёт себя как настоящий, но без sleep и со счётчиком."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, value: str) -> str:
        self.calls.append(value)
        return value.upper()


@pytest.fixture
def engine():
    # In-memory SQLite живёт только пока открыто соединение. StaticPool держит
    # одно соединение на всех, иначе каждая сессия увидела бы пустую БД.
    # check_same_thread=False нужен, потому что sync-роуты FastAPI идут в threadpool.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def race_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    engine = create_engine(url)
    Base.metadata.drop_all(engine)    # чистое состояние перед тестом
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def transformer() -> CountingTransformer:
    return CountingTransformer()


@pytest.fixture
def client(engine, transformer):
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_session():
        # Та же логика, что в настоящем get_session: commit при успехе, rollback при ошибке.
        with TestSession() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_transformer] = lambda: transformer

    # Без with TestClient не запускает lifespan: таблицы уже созданы фикстурой engine,
    # и боевая БД (cache.db) в тестах не трогается.
    yield TestClient(app)

    app.dependency_overrides.clear()



@pytest.fixture
def session_factory(race_engine):
    return sessionmaker(bind=race_engine, expire_on_commit=False)