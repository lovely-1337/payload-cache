import json

import httpx
import pytest
from pydantic import ValidationError
from pydantic_settings import CliApp

from cli.main import read_input, run, write_output
from cli.settings import CliSettings

BODY = {"list_1": ["a"], "list_2": ["b"]}


def make_settings(*args: str) -> CliSettings:
    return CliApp.run(CliSettings, cli_args=list(args))


def mock_client(handler) -> httpx.Client:
    return httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))


# --- разбор аргументов ---

def test_defaults():
    settings = make_settings("-j", "{}")

    assert settings.host == "http://localhost:8000"
    assert settings.repeat == 1
    assert settings.output == "-"


def test_short_flags_are_parsed():
    settings = make_settings("-H", "http://x:1", "-r", "3", "-j", "{}", "-o", "out.txt")

    assert settings.host == "http://x:1"
    assert settings.repeat == 3
    assert settings.output == "out.txt"


def test_input_or_json_is_required():
    with pytest.raises(ValidationError):
        make_settings()


def test_input_and_json_are_mutually_exclusive():
    with pytest.raises(ValidationError):
        make_settings("-i", "file.json", "-j", "{}")


@pytest.mark.parametrize("value", ["0", "-5"])
def test_repeat_must_be_positive(value):
    with pytest.raises(ValidationError):
        make_settings("-j", "{}", "-r", value)


# --- чтение входа и запись результата ---

def test_read_input_from_json_argument():
    assert read_input(make_settings("-j", '{"x": 1}')) == '{"x": 1}'


def test_read_input_from_file(tmp_path):
    path = tmp_path / "in.json"
    path.write_text('{"x": 1}', encoding="utf-8")

    assert read_input(make_settings("-i", str(path))) == '{"x": 1}'


def test_read_input_from_stdin(monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO('{"x": 1}'))

    assert read_input(make_settings("-i", "-")) == '{"x": 1}'


def test_write_output_to_file(tmp_path):
    path = tmp_path / "out.txt"

    write_output(["one", "two"], str(path))

    assert path.read_text(encoding="utf-8") == "one\ntwo\n"


def test_write_output_to_stdout(capsys):
    write_output(["one"], "-")

    assert capsys.readouterr().out == "one\n"


# --- run() с подменённым сервером ---

def test_run_posts_then_gets_and_repeats():
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.method == "POST":
            assert json.loads(request.content) == BODY
            return httpx.Response(201, json={"id": 7, "message": "Payload created"})
        return httpx.Response(200, json={"output": "A, B"})

    settings = make_settings("-j", json.dumps(BODY), "-r", "2")
    outputs = run(settings, mock_client(handler))

    assert outputs == ["A, B", "A, B"]
    assert requests == [
        ("POST", "/payload"), ("GET", "/payload/7"),
        ("POST", "/payload"), ("GET", "/payload/7"),
    ]


def test_run_rejects_invalid_input_before_any_request():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request expected")

    # Разная длина списков: ловим на стороне CLI, до обращения к серверу.
    settings = make_settings("-j", '{"list_1": ["a"], "list_2": []}')

    with pytest.raises(ValidationError):
        run(settings, mock_client(handler))


def test_run_raises_on_server_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    settings = make_settings("-j", json.dumps(BODY))

    with pytest.raises(httpx.HTTPStatusError):
        run(settings, mock_client(handler))


# --- CLI против настоящего приложения ---

def test_run_against_real_app(client):
    # client - фикстура из conftest: приложение с in-memory БД и фейковым transformer.
    # TestClient наследуется от httpx.Client, поэтому подходит для run() напрямую.
    settings = make_settings("-j", json.dumps(BODY), "-r", "2")

    outputs = run(settings, client)

    assert outputs == ["A, B", "A, B"]