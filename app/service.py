import hashlib
import json


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