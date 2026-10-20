import threading
import time
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.models import Payload
from app.schemas import PayloadRequest
from app.service import create_payload, get_transformed


def slow_transform(value: str) -> str:
    # Задержка растягивает окно между проверкой хэша и вставкой,
    # чтобы потоки гарантированно столкнулись.
    time.sleep(0.3)
    return value.upper()


def test_concurrent_identical_requests(race_engine):
    n = 5
    factory = sessionmaker(bind=race_engine, expire_on_commit=False)
    barrier = threading.Barrier(n)
    request = PayloadRequest(list_1=["a"], list_2=["b"])

    def worker():
        with factory() as session:
            barrier.wait()  # все стартуют одновременно
            payload, created = create_payload(session, request, slow_transform)
            session.commit()
            return payload.id, created

    with ThreadPoolExecutor(n) as pool:
        futures = [pool.submit(worker) for _ in range(n)]
        results = [f.result() for f in futures]  # исключение потока всплывёт здесь

    ids = {payload_id for payload_id, _ in results}
    created_flags = [created for _, created in results]

    assert len(ids) == 1                 # все получили один и тот же id
    assert created_flags.count(True) == 1  # ровно один поток создал запись
    with factory() as session:
        total = session.scalar(select(func.count()).select_from(Payload))
    assert total == 1



def test_transforms_each_unique_string_once(session, transformer):
    result = get_transformed(session, ["a", "b", "a"], transformer)

    assert result == {"a": "A", "b": "B"}
    # "a" встретилась дважды, но вызов был один.
    assert sorted(transformer.calls) == ["a", "b"]


def test_reuses_cached_strings(session, transformer):
    get_transformed(session, ["a", "b"], transformer)
    transformer.calls.clear()

    result = get_transformed(session, ["a", "c"], transformer)

    assert result == {"a": "A", "c": "C"}
    # Из кэша взяли "a", transformer вызван только для новой "c".
    assert transformer.calls == ["c"]


def test_empty_input_does_nothing(session, transformer):
    assert get_transformed(session, [], transformer) == {}
    assert transformer.calls == []

