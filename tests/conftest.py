import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db import get_session
from app.main import app
from app.transformer import get_transformer

from app.models import Base


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