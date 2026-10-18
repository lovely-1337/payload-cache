import time
from collections.abc import Callable

from app.config import settings

# Тип "функция, принимающая строку и возвращающая строку".
# Нужен, чтобы в сервисе и тестах можно было подставить любую замену.
Transformer = Callable[[str], str]


def transform(value: str) -> str:
    # Имитация медленного внешнего сервиса: задержка делает выигрыш от кэша заметным.
    time.sleep(settings.transformer_delay)
    return value.upper()


def get_transformer() -> Transformer:
    # Отдельная функция для Depends: в тестах её подменяют на мок со счётчиком вызовов.
    return transform
