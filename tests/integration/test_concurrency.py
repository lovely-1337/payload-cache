import threading
import time
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.models import Payload
from app.schemas import PayloadRequest
from app.service import create_payload


def slow_transform(value: str) -> str:
    # Задержка растягивает окно между проверкой хэша и вставкой,
    # чтобы потоки гарантированно столкнулись.
    time.sleep(0.3)
    return value.upper()


def test_concurrent_identical_requests(race_engine):
    n = 5
    factory = sessionmaker(bind=race_engine, expire_on_commit=False)
    # timeout: если один поток не дойдёт до барьера, тест упадёт, а не зависнет.
    barrier = threading.Barrier(n, timeout=10)
    request = PayloadRequest(list_1=["a"], list_2=["b"])

    def worker():
        with factory() as session:
            barrier.wait()
            payload, created = create_payload(session, request, slow_transform)
            session.commit()
            return payload.id, created

    with ThreadPoolExecutor(n) as pool:
        futures = [pool.submit(worker) for _ in range(n)]
        results = [f.result(timeout=30) for f in futures]

    ids = {payload_id for payload_id, _ in results}
    created_flags = [created for _, created in results]

    assert len(ids) == 1
    assert created_flags.count(True) == 1

    with factory() as session:
        total = session.scalar(select(func.count()).select_from(Payload))
    assert total == 1