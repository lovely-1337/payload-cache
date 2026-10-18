import hashlib
import json
from collections.abc import Callable, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TransformedString

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