import hashlib
import json
from collections.abc import Callable, Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (  # TransformedString уже импортирован, просто допиши Payload
    Payload,
    TransformedString,
)
from app.schemas import PayloadRequest


def compute_input_hash(list_1: list[str], list_2: list[str]) -> str:
    # Хэш служит ключом для переиспользования id. Порядок списков важен:
    # (a, b) и (b, a) дают разный output, поэтому хэшируем пару целиком.
    # Строки не склеиваем через разделитель, иначе ["a,b"] и ["a", "b"] совпали бы.
    # Компактный JSON даёт одинаковые байты для одинакового входа.
    canonical = json.dumps([list_1, list_2], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def interleave(list_1: list[str], list_2: list[str]) -> list[str]:
    # Чередуем элементы: a1, b1, a2, b2, ...
    # Одинаковую длину гарантирует валидация в схеме, поэтому zip ничего не потеряет.
    return [item for pair in zip(list_1, list_2) for item in pair]


def get_transformed(
    session: Session,
    strings: Iterable[str],
    transform: Callable[[str], str],
) -> dict[str, str]:
    # set: одна и та же строка внутри запроса трансформируется один раз.
    unique = set(strings)
    if not unique:
        return {}

    # Один запрос на все строки, а не по запросу на каждую.
    rows = session.execute(
        select(TransformedString).where(TransformedString.source.in_(unique))
    ).scalars()
    result = {row.source: row.result for row in rows}

    # Дорогой вызов только для того, чего нет в кэше.
    for source in unique - result.keys():
        result[source] = transform(source)
        session.add(TransformedString(source=source, result=result[source]))

    session.flush()
    return result


def create_payload(
    session: Session,
    request: PayloadRequest,
    transform: Callable[[str], str],
) -> tuple[Payload, bool]:
    """Возвращает (payload, created). created=False значит, что id переиспользован."""
    input_hash = compute_input_hash(request.list_1, request.list_2)

    # Уровень 2: такой вход уже обрабатывали, transformer не нужен вообще.
    existing = _find_by_hash(session, input_hash)
    if existing is not None:
        return existing, False

    # Уровень 1: трансформируем только то, чего нет в кэше строк.
    transformed = get_transformed(
        session, [*request.list_1, *request.list_2], transform
    )
    left = [transformed[s] for s in request.list_1]
    right = [transformed[s] for s in request.list_2]
    output = ", ".join(interleave(left, right))

    payload = Payload(input_hash=input_hash, output=output)
    session.add(payload)
    try:
        session.flush()
    except IntegrityError:
        # Гонка: параллельный запрос успел вставить такой же хэш раньше нас.
        # Откатываем только нашу вставку и отдаём уже существующую запись.
        session.rollback()
        existing = _find_by_hash(session, input_hash)
        if existing is None:
            raise
        return existing, False
    return payload, True


def get_payload(session: Session, payload_id: int) -> Payload | None:
    return session.get(Payload, payload_id)


def _find_by_hash(session: Session, input_hash: str) -> Payload | None:
    return session.execute(
        select(Payload).where(Payload.input_hash == input_hash)
    ).scalar_one_or_none()
