# Payload cache

FastAPI microservice that builds payloads from two lists of strings and caches
the results of a slow "transformer" function, so repeated work is never redone.

## How it works

- `POST /payload` takes `list_1` and `list_2` (same length), transforms every
  string, interleaves the results and returns the payload id.
- `GET /payload/{id}` returns `{"output": "..."}` or 404.

Two cache levels, both in the database:

1. **Strings cache** (`transformed_strings`): the transformer runs only for
   strings never seen before, and once per unique string within a request.
2. **Payload cache** (`payloads`): the input is hashed (sha256 of canonical
   JSON). The same input returns the same id (HTTP 200 instead of 201)
   without calling the transformer at all.

## Run with Docker

```bash
docker compose up --build
```

The API is on http://localhost:8000 (Swagger at `/docs`), data is stored in
Postgres and survives restarts (`pgdata` volume).

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app
```

Without `DATABASE_URL` it uses SQLite (`cache.db`).

Settings (env variables): `DATABASE_URL`, `TRANSFORMER_DELAY` (seconds).

## CLI

```bash
cache-cli -i example.json -r 3
cache-cli -j '{"list_1": ["a"], "list_2": ["b"]}'
cat example.json | cache-cli -i - -o result.txt
```

| Flag | Meaning |
|---|---|
| `-H`, `--host` | server URL (default `http://localhost:8000`) |
| `-r`, `--repeat` | number of iterations (default 1, min 1) |
| `-i`, `--input` | input file, `-` for stdin |
| `-j`, `--json` | input as a JSON string |
| `-o`, `--output` | output file, `-` for stdout (default) |
| `-h`, `--help` | help |

Exactly one of `--input` / `--json` is required. Progress goes to stderr, the
result to stdout.

## Tests

```bash
python -m pytest
```

Unit tests (helpers, strings cache), integration tests through `TestClient`
(in-memory SQLite, transformer replaced by a call counter) and CLI tests
(`httpx.MockTransport`).

## Shortcuts & decisions

- **`-H` for host.** The task assigns `-h` to both `--host` and `--help`.
  `-h` stays as help, host uses `-H`.
- **Empty lists are allowed** and produce an empty output.
- **Tables via `create_all` on startup** instead of Alembic migrations.
  Production would need migrations.
- **Sync endpoints and sync SQLAlchemy.** The transformer blocks, so plain
  `def` routes run in FastAPI's threadpool and do not block the event loop.
- **Race conditions.** A duplicate payload hash is handled (`IntegrityError`,
  then re-read). Two concurrent requests with the same new string may both call
  the transformer, and the second insert into the strings cache can fail with
  a unique violation, so the request would return 500 and succeed on retry.
  Fixing it needs `INSERT ... ON CONFLICT DO NOTHING` or a per-key lock; not
  done to keep the code simple.
- **Rollback on a hash race** also discards the strings cached by that request;
  they are recomputed next time. Correct, just not optimal.
- **`IN` query limit.** Very large inputs can exceed the database's parameter
  limit. Chunking would be needed for that.
- **CLI reuses `PayloadRequest`** from the service instead of a shared package.
- **Dependencies are listed twice**: `requirements.txt` (Docker layer cache)
  and `pyproject.toml` (package and `cache-cli` entry point).
- **Credentials in `docker-compose.yml`** are for demo only; use secrets in
  production.