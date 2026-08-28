# Nexus

A small auth API built with the layered project structure commonly used for
production FastAPI services: a versioned API layer, a service layer for business
rules, a repository layer for storage, and Pydantic schemas at the boundary.

## Project structure

```
app/
├── main.py                 # create_app() factory, middleware, lifespan
├── api/
│   ├── deps.py             # shared dependencies (DI)
│   └── v1/
│       ├── router.py       # aggregates every v1 endpoint module
│       └── endpoints/
│           ├── auth.py     # /auth/signup, /auth/login, /auth/admin/login, /auth/me
│           └── health.py   # /health
├── core/
│   ├── config.py           # Settings loaded from environment / .env
│   ├── error_handlers.py   # 422/4xx/5xx JSON responses
│   ├── exceptions.py       # AppError hierarchy raised by services
│   ├── logging.py          # logging configuration
│   └── security.py         # password hashing helpers (for SQLAlchemy later)
├── models/                 # domain models (become ORM entities later)
├── repositories/           # empty for now; add SQLAlchemy repositories here
├── schemas/                # request/response validation models
└── services/               # business rules, framework independent
tests/                      # pytest suite driven through the HTTP layer
```

Endpoints call services. Services will call repositories once SQLAlchemy is wired.
Endpoints never contain business rules, and services never touch HTTP objects.

## Requirements

- Python 3.10+

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

Docs and the OpenAPI schema are disabled automatically when `ENVIRONMENT` is
`production`.

## Tests

```bash
pytest
```

## Endpoints

All routes are served under `API_V1_PREFIX` (default `/api/v1`).

| Method | Path                       | Description                |
| ------ | -------------------------- | -------------------------- |
| GET    | `/api/v1/health`           | Liveness probe             |
| POST   | `/api/v1/auth/signup`      | Register a user (201)      |
| POST   | `/api/v1/auth/login`       | Authenticate a user        |
| POST   | `/api/v1/auth/admin/login` | Authenticate an admin      |
| GET    | `/api/v1/auth/me`          | Current user (placeholder) |

## Configuration

Settings come from environment variables or `.env`; see `.env.example`.

## Validation errors

Request validation failures return HTTP 422 with plain-language messages, for
example `"email is required"` or `"password must be at least 8 characters"`.
Business-rule failures raise `AppError` subclasses that map to 400/401/403/404/409.

## Known limitations

- Auth endpoints validate input and return stub responses. Nothing is persisted yet.
- Add SQLAlchemy under `app/repositories/` (and wire it in `AuthService`) when you
  are ready to save users in a database.
- JWT / real `/auth/me` auth comes after the database layer.
