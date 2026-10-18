import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

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