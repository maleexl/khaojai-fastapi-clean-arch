# Khaojai FastAPI Clean Architecture

![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![Docker](https://img.shields.io/badge/Docker-ready-blue)
![Tests](https://img.shields.io/badge/tests-48%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-90%25-green)

A **Python 3.11 + FastAPI** reimplementation inspired by
[max38/golang-clean-code-architecture](https://github.com/max38/golang-clean-code-architecture),
preserving its **Clean Architecture** layering with an async-first stack.

---

## Highlights

- **Strict Clean Architecture** — Domain, Usecases, Interface, Infrastructure
- **Dependency Inversion in action** — use cases depend on repository interfaces, not implementations
- **AST-enforced boundaries** — domain/usecases cannot import framework code
- **Dual-token JWT** — short-lived access + long-lived refresh with jti-based blacklist
- **47 unit/API tests + 1 Playwright E2E** — in-memory fakes prove the DI boundary
- **Async I/O end-to-end** — FastAPI → SQLAlchemy 2.x → asyncpg → PostgreSQL
- **Full-stack bonus** — React 19 + Vite + TypeScript frontend, Playwright E2E

---

## Golang → Python Mapping

| Go (`src/`) | Python (`app/`) | Notes |
|-------------|-----------------|-------|
| `domain/entities/user/` | `domain/entities/user.py` | Pure dataclass |
| `domain/entities/crud/` | *(omitted)* | Generic CRUD not ported |
| `domain/repositories/user.go` | `domain/repositories/user_repository.py` | ABC interface |
| `usecases/user/userUsecase.go` | `usecases/user_usecase.py` | register / login / logout / refresh / get_by_id |
| `interface/handlers/gofiber/modules/user/` | `interface/api/v1/routers/user_router.py` | HTTP + manual DI |
| `interface/handlers/gofiber/modules/monitor/` | `interface/api/v1/routers/health_router.py` | Health check |
| `interface/repositories/postgres/user/` | `interface/repositories/user_repository_impl.py` | SQLAlchemy impl |
| `infrastructure/database/postgres/` | `infrastructure/database/session.py` | Async engine + session |
| `shared/authentication/JWTAuthentication.go` | `shared/security.py` | bcrypt + JWT helpers |
| `config/config.go` | `config/settings.py` | Pydantic Settings |

### Intentional Differences from the Reference

- **Generic CRUD endpoints** — omitted. The reference ships a generic CRUD
  system over any entity; this port focuses on the user auth domain.
- **MongoDB connector** — omitted. PostgreSQL only.
- **`domain/models/` + `domain/entities/`** — merged into `domain/entities/`.
  The reference mixed GORM structs with pure entities; this port keeps the
  domain framework-free and moves ORM concerns to `infrastructure/database/models.py`.
- **`config/crudModels.go`** — omitted (tied to generic CRUD).
- **TokenBlacklist entity** — added. jti-based revocation (reference has no logout).
- **AST architecture tests** — added. Enforced by code, not convention.
- **React frontend + Playwright E2E** — added as a bonus.

---

## Quick Start

### With Docker (recommended)

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec app alembic upgrade head
curl http://localhost:8000/health   # {"status":"ok","database":"connected"}
```

Open <http://localhost:8000/docs> for interactive API.

> **Port note:** host maps PostgreSQL to **5433** (container uses 5432).

### Local (WSL / venv)

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
docker compose up -d db
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

---

## Frontend (Bonus)

A minimal **React 19 + Vite + TypeScript + Tailwind** SPA that exercises
the three user flows end-to-end.

**Pages:** `/register` · `/login` · `/profile` (protected)

**Run locally:**

```bash
cd frontend
npm install
cp .env.example .env       # VITE_API_URL=http://localhost:8000
npm run dev                # http://localhost:5173
```

Backend must be running (`docker compose up -d`). CORS is preconfigured
via the `CORS_ORIGINS` setting (default `http://localhost:5173`).

**E2E coverage:** `tests/e2e/test_frontend_flow.py` drives a real Chromium
browser through register → login → profile → logout:

```bash
pytest tests/e2e/test_frontend_flow.py -v
```

---

## Architecture & Dependency Flow

```
  Domain  ◄──  Use Cases  ◄──  Interface/Adapters  ◄──  Infrastructure
  (pure)       (logic)         (FastAPI · Pydantic)     (SQLAlchemy · cfg)

  imports point inward only ──►
```

Request path (concrete):

```
HTTP request
  → Router             (app/interface/api/v1/routers/user_router.py)
  → UserUsecase        (app/usecases/user_usecase.py)       ← domain only
  → UserRepository     (app/domain/repositories/)           ← ABC
  → UserRepositoryImpl (app/interface/repositories/)        ← SQLAlchemy lives here
  → AsyncSession       (app/infrastructure/database/session.py)
```

### Why manual DI (no framework)

Wiring lives in `_get_usecase(session)` and is ~10 lines:

| Reason | What it buys you |
|--------|------------------|
| **Testability** | Use cases are constructed with fakes directly — no DB, no web context, no container. |
| **Explicitness** | Every dependency is a visible constructor argument. |
| **No magic** | Debugging is reading Python — no framework lifecycle to learn. |

**Trade-off accepted:** wiring grows linearly with the app. If it becomes
painful, the fix is a small factory module — still manual, still framework-free.

---

## Design Decisions

| Decision | Why | Trade-off |
|----------|-----|-----------|
| **Domain entity ≠ ORM model** | Domain stays framework-free; ORM schema changes don't ripple into business rules | One extra mapping step |
| **Manual DI** | Explicitness, testability, no framework lifecycle | Wiring grows linearly |
| **Dual JWT (access + refresh)** | Short-lived access limits damage; refresh enables long sessions | Requires blacklist for logout |
| **jti-based blacklist** | Stateless JWT + server-side revocation | DB write per logout; needs cleanup |
| **Custom exceptions → HTTP** | Usecase raises `ConflictError`; router maps to 409 | Two translation points |
| **AST architecture tests** | Docs rot; a failing test doesn't | Negligible overhead |

---

## API Endpoints

Base prefix: `/api/v1`

| Method | Path | Auth | Success | Errors |
|--------|------|------|---------|--------|
| GET | `/health` | — | 200 | 503 |
| POST | `/api/v1/users/register` | — | 201 | 400, 409, 422 |
| POST | `/api/v1/users/login` | — | 200 | 401, 422 |
| GET | `/api/v1/users/me` | Bearer (access) | 200 | 401 |
| POST | `/api/v1/users/refresh-token` | — (body) | 200 | 401 |
| POST | `/api/v1/users/logout` | Bearer (refresh) | 200 | 401 |

### Example — register

Request:

```json
{
  "email": "alice@example.com",
  "username": "alice",
  "password": "supersecret123"
}
```

Response (201):

```json
{
  "id": "77ea9b2d-9cc8-474b-bb83-028062be7fb9",
  "email": "alice@example.com",
  "username": "alice",
  "is_active": true,
  "created_at": "2026-10-09T14:47:00.043903Z",
  "updated_at": "2026-10-09T14:47:00.043903Z"
}
```

### Example — login

Response (200):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Error responses

Full details at `/docs`. Two examples:

- `409 Conflict` — `{ "detail": "Email already registered" }`
- `401 Unauthorized` — `{ "detail": "Could not validate credentials" }`

---

## Testing Strategy

### How to run

```bash
# Core suite (no DB / Docker / network required)
pytest tests/unit tests/api -v
pytest tests/unit tests/api --cov=app --cov-report=term-missing
```

### Real results

- **47 unit/API tests passing** in ~6s
- **90% coverage**
- **+1 Playwright E2E test** (requires frontend + backend running)

### Coverage by layer

| Layer | Coverage | Notes |
|-------|----------|-------|
| Domain | 100% | Entities + repository ABCs |
| Usecases | 100% | All 5 operations |
| Shared | 100% | Security + exceptions |
| Interface (schemas, health) | 100% | |
| Interface (user_router) | 93% | Error paths covered |
| Main | 91% | Wiring |
| Infrastructure (session) | 54% | Integration territory |
| Interface (repo impls) | 46-55% | Integration territory |
| **TOTAL** | **90%** | |

### Example — duplicate email guard

```python
async def test_register_duplicate_email_raises(usecase, existing_user):
    """register() rejects an already-used email with ConflictError."""
    with pytest.raises(ConflictError, match="Email"):
        await usecase.register(
            email="alice@example.com",
            username="different-name",
            password="password123",
        )
```

### Architecture tests (AST-enforced)

Clean Architecture boundaries are enforced at test time using Python's `ast` module:

- `domain/` must not import `fastapi`, `sqlalchemy`, `pydantic`, `jose`, `bcrypt`
- `usecases/` must not import `interface/` or `infrastructure/`
- Violation → test fails with filename + offending import

### Why not 100%?

Domain, Use Cases, and Shared code are at 100%. The remaining gap is in
adapter implementations (`*_repository_impl.py`, `session.py`) which require
a real database. We treat these as **integration territory** — covered by the
`docker compose up` smoke test, not by mocked unit tests. Mocking a database
to test the database defeats the purpose.

### Browser E2E (Playwright)

`tests/e2e/test_frontend_flow.py` drives a real Chromium browser through
the complete user journey: register → login → profile → logout. Uses a
unique email per run (idempotent).

```bash
# Requires: docker compose up -d AND cd frontend && npm run dev
pytest tests/e2e/test_frontend_flow.py -v
```

### Backend end-to-end verification

Sequence run against a live `docker compose up` stack:

```
GET  /health                       → 200 {"status":"ok","database":"connected"}
POST /api/v1/users/register        → 201
POST /api/v1/users/login           → 200 (access + refresh)
GET  /api/v1/users/me (Bearer)     → 200
POST /api/v1/users/refresh-token   → 200 (new access)
POST /api/v1/users/logout          → 200 {"message":"Logged out successfully"}
POST /api/v1/users/refresh-token   → 401 {"detail":"Token has been revoked"}
```

---

## Project Structure

```
khaojai-fastapi-clean-arch/
├── app/
│   ├── main.py                              # FastAPI factory + exception handlers
│   ├── config/settings.py                   # Pydantic Settings
│   ├── domain/                              # ← pure business core (no framework)
│   │   ├── entities/user.py
│   │   ├── entities/token_blacklist.py
│   │   ├── repositories/user_repository.py
│   │   └── repositories/token_blacklist_repository.py
│   ├── usecases/user_usecase.py             # register / login / logout / refresh / get_by_id
│   ├── interface/
│   │   ├── api/v1/routers/user_router.py
│   │   ├── api/v1/routers/health_router.py
│   │   ├── api/v1/schemas/user_schema.py
│   │   ├── api/v1/schemas/token_schema.py
│   │   ├── repositories/user_repository_impl.py
│   │   └── repositories/token_blacklist_repository_impl.py
│   ├── infrastructure/database/
│   │   ├── models.py                        # SQLAlchemy ORM
│   │   └── session.py                       # async engine + get_session
│   └── shared/
│       ├── exceptions.py
│       └── security.py
├── frontend/                                # ← React 19 + Vite + TS + Tailwind
│   ├── src/
│   │   ├── api/client.ts
│   │   ├── contexts/AuthContext.tsx
│   │   ├── components/{Layout,ProtectedRoute}.tsx
│   │   └── pages/{Register,Login,Profile}.tsx
│   ├── package.json
│   └── vite.config.ts
├── alembic/
│   ├── env.py                               # async migrations
│   └── versions/                            # users + token_blacklist migrations
├── tests/
│   ├── unit/                                # 32 tests
│   ├── api/                                 # 15 tests
│   └── e2e/                                 # 1 Playwright test
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── pytest.ini
└── LICENSE                                  # Apache 2.0
```

### Database schema

See `app/infrastructure/database/models.py`. Two tables:

- **`users`** — `id` (UUID PK), `email` (unique, indexed), `username` (unique, indexed), `hashed_password`, `is_active`, `created_at`, `updated_at`
- **`token_blacklist`** — `jti` (String PK), `expires_at` (indexed), `created_at`

---

## Database Migrations

```bash
# Generate a new migration (reads DATABASE_URL from settings)
alembic revision --autogenerate -m "add something"

# Apply all pending migrations
alembic upgrade head

# Rollback one
alembic downgrade -1
```

Alembic is configured to import `Base.metadata` from
`app.infrastructure.database.models` so autogenerate sees every ORM model.

---

## Verifications

### Layer purity (grep audit)

```bash
grep -rE --include='*.py' "fastapi|sqlalchemy|pydantic|jose|bcrypt" app/domain/ \
  && echo LEAK || echo "domain clean"

grep -rE --include='*.py' "fastapi|sqlalchemy|pydantic|jose|bcrypt" app/usecases/ \
  && echo LEAK || echo "usecase clean"
```

Both checks pass. The same rules are additionally enforced by
`tests/unit/test_architecture.py`.

---

## License & Acknowledgments

This project is licensed under the **Apache License 2.0** (see [LICENSE](LICENSE)).

The architecture is a Python reimplementation inspired by
[max38/golang-clean-code-architecture](https://github.com/max38/golang-clean-code-architecture),
which is also licensed under Apache 2.0. No Go source code was copied —
the reference was used to understand the layer structure and API surface.
EOF