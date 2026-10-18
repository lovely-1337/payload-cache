import sys
from pathlib import Path

import httpx
from pydantic import ValidationError
from pydantic_settings import CliApp

# Shortcut: схему запроса берём из сервиса, чтобы CLI и API проверяли вход одинаково.
# В реальном проекте её вынесли бы в общий пакет.
from app.schemas import PayloadRequest
from cli.settings import CliSettings


def read_input(settings: CliSettings) -> str:
    if settings.json_data is not None:
        return settings.json_data
    if settings.input == "-":
        return sys.stdin.read()
    return Path(settings.input).read_text(encoding="utf-8")


def write_output(lines: list[str], target: str) -> None:
    text = "\n".join(lines) + "\n"
    if target == "-":
        sys.stdout.write(text)
    else:
        Path(target).write_text(text, encoding="utf-8")


def run(settings: CliSettings, client: httpx.Client) -> list[str]:
    # Валидируем вход до первого запроса: лучше упасть сразу, чем получить 422 от сервера.
    request = PayloadRequest.model_validate_json(read_input(settings))
    body = request.model_dump()

    outputs: list[str] = []
    for i in range(1, settings.repeat + 1):
        created = client.post("/payload", json=body)
        created.raise_for_status()
        payload_id = created.json()["id"]

        response = client.get(f"/payload/{payload_id}")
        response.raise_for_status()
        outputs.append(response.json()["output"])

        # Прогресс идёт в stderr, чтобы stdout содержал только результат
        # и его можно было перенаправить в файл или другую программу.
        message = created.json()["message"]
        print(f"[{i}/{settings.repeat}] id={payload_id}: {message}", file=sys.stderr)
    return outputs


def main() -> None:
    try:
        settings = CliApp.run(CliSettings)
        # Timeout больше стандартных 5 сек: transformer намеренно медленный.
        with httpx.Client(base_url=settings.host, timeout=30) as client:
            outputs = run(settings, client)
        write_output(outputs, settings.output)
    except (ValidationError, OSError) as exc:
        # Понятное сообщение и ненулевой код выхода вместо traceback.
        sys.exit(f"error: {exc}")
    except httpx.HTTPError as exc:
        sys.exit(f"request failed: {exc}")


if __name__ == "__main__":
    main()
