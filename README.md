# Church City Kids

Child ministry management for Church City.

## Backend (Milestone 1)

Domain model and unit tests only. No API, database, or frontend yet.

Python 3.11 or newer is required.

Development dependencies and the local environment are managed with `uv`.

```bash
cd backend
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy .
```
