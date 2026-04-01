# LedgerLens — Rebuild Architecture Plan

> Exhaustive blueprint for re-implementing LedgerLens from scratch with a cleaner,
> modern architecture while preserving **100 % of existing functionality**.
> The new system runs in a **single Docker container only**.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current System Analysis](#2-current-system-analysis)
3. [Design Principles](#3-design-principles)
4. [New Project Structure](#4-new-project-structure)
5. [Technology Choices](#5-technology-choices)
6. [Data Model](#6-data-model)
7. [Backend Architecture](#7-backend-architecture)
8. [Frontend Architecture](#8-frontend-architecture)
9. [Single-Container Docker Design](#9-single-container-docker-design)
10. [API Contract](#10-api-contract)
11. [Background Processing](#11-background-processing)
12. [OCR & LLM Pipeline](#12-ocr--llm-pipeline)
13. [Authentication & Authorization](#13-authentication--authorization)
14. [Real-Time Communication](#14-real-time-communication)
15. [File Storage](#15-file-storage)
16. [Database Migrations](#16-database-migrations)
17. [Testing Strategy](#17-testing-strategy)
18. [CI/CD](#18-cicd)
19. [Configuration & Environment](#19-configuration--environment)
20. [Implementation Order](#20-implementation-order)

---

## 1. Executive Summary

LedgerLens is a self-hosted, privacy-first receipt-tracking PWA. Users upload receipt
images or PDFs, which pass through an OCR → LLM extraction pipeline. The system
normalises line items into canonical products, offers fuzzy-match suggestions, tracks
prices over time, and provides spending dashboards — all shareable within a household.

### What stays the same

- Every user-facing feature and API endpoint.
- SQLite-by-default with optional PostgreSQL.
- Tesseract OCR + OpenAI-compatible LLM extraction.
- Celery + embedded Redis for background processing.
- Session-cookie authentication.
- PWA with offline API caching.

### What changes

| Dimension | Current | New |
|---|---|---|
| Docker deployment | Three Dockerfiles + Compose with multi-container AND all-in-one profile | **Single Dockerfile** producing one all-in-one image; no Compose file shipped |
| Backend layout | Flat `app/` package; services mix DB queries and business logic | Layered architecture: **routers → services → repositories**; clear separation |
| Migration state | Three incremental Alembic revisions | Single consolidated initial migration |
| `_utc_now()` helper | Duplicated in every model file | One shared `app.core.time` module |
| Model base class | `Base` defined in `database.py` | `Base` with common `id`, `created_at`, `updated_at` mixin |
| Error handling | Ad-hoc `HTTPException` raises scattered in routers | Centralised domain exceptions + FastAPI exception handlers |
| Frontend state | Mixed Zustand (auth, filters, upload) + TanStack Query | Keep TanStack Query for server state; consolidate Zustand stores into a single `appStore` |
| Frontend routing | Lazy imports + inline `createBrowserRouter` | Same pattern, cleaned up into a dedicated `routes/` directory |
| WebSocket | Minimal ping/pong; no server-push for job updates | Server actively pushes `ProcessingJob` state changes to the owning user |
| Tests | Smoke + sparse unit/integration | Structured `tests/` mirroring `app/`; fixtures for every model; >80 % service coverage target |
| CI | Builds two separate GHCR images | Builds **one** all-in-one image |

---

## 2. Current System Analysis

### 2.1 Repository Inventory

```
ledgerlens/
├── backend/                 # Python 3.11 + FastAPI
│   ├── alembic/             # 3 migration revisions
│   ├── app/
│   │   ├── middleware/       # AuthMiddleware, SecurityMiddleware
│   │   ├── models/           # 10 SQLAlchemy ORM models
│   │   ├── routers/          # 11 FastAPI routers (+ WebSocket)
│   │   ├── schemas/          # 9 Pydantic schema modules
│   │   ├── services/         # 12 service modules
│   │   ├── tasks/            # Celery task (receipt_processing)
│   │   ├── config.py         # pydantic-settings
│   │   ├── database.py       # engine + session factory + Base
│   │   ├── main.py           # FastAPI app, lifespan, router registration
│   │   └── worker.py         # Celery app + worker process init
│   ├── tests/                # conftest, smoke, 3 unit, 4 integration
│   ├── pyproject.toml        # uv-managed deps; ruff, mypy config
│   └── Dockerfile            # Standalone backend image
├── frontend/                # React 19 + TypeScript 5.9 + Vite 8
│   ├── src/
│   │   ├── components/       # layout (2), product (3), receipt (5), ui (3)
│   │   ├── hooks/            # 8 TanStack Query hooks
│   │   ├── lib/              # types.ts, utils.ts, money.ts
│   │   ├── pages/            # 15 page components
│   │   ├── services/         # api.ts, websocket.ts
│   │   ├── stores/           # 3 Zustand stores
│   │   ├── router.tsx
│   │   ├── App.tsx / main.tsx / index.css
│   │   └── test-setup.ts
│   ├── Dockerfile            # Standalone frontend image
│   └── nginx.conf
├── specs/                   # 5 feature spec folders (001–005)
├── Dockerfile               # All-in-one image (the one we keep)
├── docker-compose.yml       # Multi-service + AIO profile
├── supervisord.conf         # Redis → Backend → Worker → Nginx
├── nginx-unified.conf       # Reverse proxy config
├── entrypoint.sh            # Migration + supervisord launch
└── .env.example
```

### 2.2 Data Model (10 Tables)

| Model | Purpose | Key Relationships |
|---|---|---|
| `User` | Account with email/password/role | → Household (optional), → Receipt[] |
| `UserSession` | Server-side session rows | → User |
| `Household` | Multi-user grouping | owner → User, → User[] (members) |
| `Receipt` | Core receipt record (totals, dates, status, file paths) | → User, → Store?, → LineItem[], → ProcessingJob[] |
| `LineItem` | Individual line on a receipt | → Receipt, → CanonicalItem?, → MatchSuggestion[] |
| `CanonicalItem` | Normalised product identity (name, aliases, category, image) | → MatchSuggestion[] |
| `MatchSuggestion` | Fuzzy-match proposal linking LineItem ↔ CanonicalItem | → LineItem, → CanonicalItem |
| `Store` | Merchant (name, address, chain, geo) | → Receipt[] |
| `ProcessingJob` | Tracks async OCR/LLM pipeline runs | → Receipt, → ModelConfig? |
| `ModelConfig` | Admin-managed LLM endpoint configuration | — |

### 2.3 API Surface (all under `/api/v1`)

| Group | Endpoints |
|---|---|
| **Auth** | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| **Receipts** | `POST /receipts` (upload), `POST /receipts/manual`, `GET /receipts`, `GET /receipts/:id`, `PATCH /receipts/:id`, `DELETE /receipts/:id`, `PATCH /receipts/:id/items/:id`, `POST /receipts/:id/reprocess` |
| **Items** | `GET /items`, `GET /items/:id`, `GET /items/:id/prices`, `PATCH /items/:id`, `DELETE /items/:id`, `POST /items/:id/image`, `DELETE /items/:id/image`, `POST /items/:id/fetch-image` |
| **Stores** | `GET /stores`, `GET /stores/:id`, `PATCH /stores/:id` |
| **Dashboard** | `GET /dashboard/summary`, `GET /dashboard/spending-by-store`, `GET /dashboard/spending-by-month`, `GET /dashboard/spending-by-category` |
| **Household** | `POST /household`, `GET /household`, `PATCH /household`, `POST /household/invite`, `POST /household/join/:token`, `DELETE /household/members/:id` |
| **Jobs** | `GET /jobs`, `GET /jobs/:id` |
| **Line Items** | `PATCH /line-items/:id` |
| **Suggestions** | `GET /suggestions`, `GET /items/:id/suggestions`, `POST /suggestions/:id/accept`, `POST /suggestions/:id/reject` |
| **Admin** | `GET /admin/models`, `POST /admin/models`, `PATCH /admin/models/:id`, `DELETE /admin/models/:id`, `POST /admin/models/:id/test` |
| **WebSocket** | `WS /ws/jobs?session_id=<token>` |

### 2.4 Processing Pipeline

```
Upload/Camera → save file → create Receipt(status=pending)
                          → create ProcessingJob(status=queued)
                          → Celery task dispatched
                                ↓
                          OCR (Tesseract)
                                ↓
                          LLM extraction (OpenAI-compatible)
                           │ fails? → heuristic regex fallback
                                ↓
                          Normalise store name
                          Find/create CanonicalItem per line item
                           (exact → alias → fuzzy auto-link → suggestion → new)
                                ↓
                          Receipt(status=processed)
                          ProcessingJob(status=completed)
```

### 2.5 Frontend Pages

| Route | Page | Key Data |
|---|---|---|
| `/dashboard` | Dashboard | Summary cards, spending-by-store chart, spending-by-month chart, spending-by-category chart |
| `/receipts` | Receipts | Paginated list, status/store/date filters |
| `/receipts/add` | AddReceipt | Camera capture, file upload |
| `/receipts/manual` | ManualEntry | Form: store, date, line items, totals |
| `/receipts/:id` | ReceiptDetail | Receipt editor, line item table, reprocess, delete |
| `/items` | Items | Paginated product list, search, delete |
| `/items/:id` | ProductDetail | Edit name/category/URL, aliases, image upload/fetch, match suggestions |
| `/price-tracker` | PriceTracker | Item search, price history chart + table |
| `/stores` | Stores | Paginated store cards |
| `/settings` | Settings | Profile info, links to household/admin |
| `/settings/household` | HouseholdSettings | Create/edit household, invite link, member management |
| `/admin/models` | AdminModels | LLM model config CRUD, connection test |
| `/login` | Login | Email + password |
| `/register` | Register | Email + display name + password |
| `/join/:token` | JoinHousehold | Accept invite |

---

## 3. Design Principles

1. **Layered backend**: Router → Service → Repository. Routers handle HTTP concerns only; services contain business logic; repositories encapsulate all database queries.
2. **Domain exceptions**: No `HTTPException` below the router layer. Services raise domain-specific exceptions (e.g. `ReceiptNotFoundError`); routers translate them.
3. **Single responsibility models**: Each ORM model in its own file, inheriting a `BaseMixin` that provides `id`, `created_at`, `updated_at`.
4. **Strict typing**: mypy strict mode (backend), TypeScript strict mode (frontend). No `Any` escapes without justification.
5. **Testability**: Every service accepts its DB session as a parameter (no global imports for testing). Repositories are easily mockable.
6. **Single container**: One Dockerfile, one image, four supervised processes (Redis, FastAPI, Celery worker, Nginx). No docker-compose shipped.

---

## 4. New Project Structure

```
ledgerlens/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app factory, lifespan, CORS, middleware
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # pydantic-settings Settings class
│   │   │   ├── database.py            # engine, session factory, Base, get_db
│   │   │   ├── exceptions.py          # Domain exception hierarchy
│   │   │   ├── security.py            # password hashing, token serialiser
│   │   │   └── time.py                # utc_now() — single source of truth
│   │   ├── models/
│   │   │   ├── __init__.py            # re-exports all models
│   │   │   ├── base.py                # BaseMixin (id, created_at, updated_at)
│   │   │   ├── user.py
│   │   │   ├── user_session.py
│   │   │   ├── household.py
│   │   │   ├── receipt.py
│   │   │   ├── line_item.py
│   │   │   ├── canonical_item.py
│   │   │   ├── match_suggestion.py
│   │   │   ├── store.py
│   │   │   ├── processing_job.py
│   │   │   └── model_config.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── receipt.py
│   │   │   ├── item.py
│   │   │   ├── store.py
│   │   │   ├── dashboard.py
│   │   │   ├── household.py
│   │   │   ├── admin.py
│   │   │   ├── job.py
│   │   │   ├── suggestion.py
│   │   │   └── pagination.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── user.py                # UserRepository
│   │   │   ├── session.py             # SessionRepository
│   │   │   ├── household.py           # HouseholdRepository
│   │   │   ├── receipt.py             # ReceiptRepository
│   │   │   ├── line_item.py           # LineItemRepository
│   │   │   ├── canonical_item.py      # CanonicalItemRepository
│   │   │   ├── match_suggestion.py    # MatchSuggestionRepository
│   │   │   ├── store.py               # StoreRepository
│   │   │   ├── processing_job.py      # ProcessingJobRepository
│   │   │   └── model_config.py        # ModelConfigRepository
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                # login, register, session lifecycle
│   │   │   ├── receipt.py             # upload, manual create, update, delete, list
│   │   │   ├── extraction.py          # orchestrate OCR → LLM/heuristic → persist
│   │   │   ├── ocr.py                 # Tesseract wrapper + PDF handler
│   │   │   ├── llm.py                 # OpenAI-compatible chat extraction
│   │   │   ├── heuristic.py           # Regex-based receipt parser
│   │   │   ├── normalization.py       # Store name / item name normalisation
│   │   │   ├── matching.py            # Fuzzy match engine (rapidfuzz)
│   │   │   ├── item.py                # Canonical item CRUD + price history
│   │   │   ├── store.py               # Store CRUD + stats
│   │   │   ├── dashboard.py           # Aggregation queries
│   │   │   ├── household.py           # Household CRUD, invites, join
│   │   │   ├── admin.py               # ModelConfig CRUD, health test
│   │   │   ├── processing.py          # Enqueue receipt, orphan recovery
│   │   │   ├── image_fetcher.py       # Google CSE image search
│   │   │   ├── storage.py             # File save/delete, path validation
│   │   │   ├── scope.py               # Household-aware visibility filters
│   │   │   └── retroactive_matching.py # Background scan loop
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── receipts.py
│   │   │   ├── items.py
│   │   │   ├── stores.py
│   │   │   ├── dashboard.py
│   │   │   ├── household.py
│   │   │   ├── admin.py
│   │   │   ├── jobs.py
│   │   │   ├── line_items.py
│   │   │   ├── suggestions.py
│   │   │   └── ws.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                # Session cookie gate
│   │   │   └── security.py            # CSP + security headers
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   └── receipt_processing.py
│   │   └── worker.py                  # Celery app definition
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial_schema.py # Single consolidated migration
│   ├── tests/
│   │   ├── conftest.py                # Fixtures: async engine, session, test client, factories
│   │   ├── factories.py               # Model factories for test data
│   │   ├── unit/
│   │   │   ├── services/              # One test file per service
│   │   │   └── repositories/          # One test file per repository
│   │   └── integration/
│   │       ├── test_auth_flow.py
│   │       ├── test_receipt_flow.py
│   │       ├── test_item_management.py
│   │       ├── test_dashboard.py
│   │       ├── test_household.py
│   │       └── test_processing_pipeline.py
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons/                     # PWA icons (192, 512, maskable)
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css                  # @import "tailwindcss";
│   │   ├── router.tsx
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppShell.tsx
│   │   │   │   └── ProtectedRoute.tsx
│   │   │   ├── receipt/
│   │   │   │   ├── CameraCapture.tsx
│   │   │   │   ├── FileUpload.tsx
│   │   │   │   ├── LineItemTable.tsx
│   │   │   │   ├── ProcessingStatus.tsx
│   │   │   │   └── ReceiptCard.tsx
│   │   │   ├── product/
│   │   │   │   ├── AliasManager.tsx
│   │   │   │   ├── MatchSuggestionCard.tsx
│   │   │   │   └── ProductImageUpload.tsx
│   │   │   └── ui/
│   │   │       ├── Badge.tsx
│   │   │       ├── Pagination.tsx
│   │   │       └── Spinner.tsx
│   │   ├── hooks/
│   │   │   ├── useAdmin.ts
│   │   │   ├── useDashboard.ts
│   │   │   ├── useHousehold.ts
│   │   │   ├── useItems.ts
│   │   │   ├── useMatchSuggestions.ts
│   │   │   ├── useProcessingJobs.ts
│   │   │   ├── useReceipts.ts
│   │   │   └── useStores.ts
│   │   ├── lib/
│   │   │   ├── types.ts
│   │   │   ├── utils.ts
│   │   │   └── money.ts
│   │   ├── pages/
│   │   │   ├── AddReceipt.tsx
│   │   │   ├── AdminModels.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── HouseholdSettings.tsx
│   │   │   ├── Items.tsx
│   │   │   ├── JoinHousehold.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── ManualEntry.tsx
│   │   │   ├── PriceTracker.tsx
│   │   │   ├── ProductDetail.tsx
│   │   │   ├── ReceiptDetail.tsx
│   │   │   ├── Receipts.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── Stores.tsx
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   └── websocket.ts
│   │   └── stores/
│   │       └── appStore.ts            # Consolidated Zustand store
│   ├── index.html
│   ├── vite.config.ts
│   ├── vitest.config.ts
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   ├── eslint.config.js
│   └── package.json
├── infra/
│   ├── nginx.conf                     # Unified reverse proxy
│   ├── supervisord.conf               # Process supervisor config
│   └── entrypoint.sh                  # Migration + supervisord
├── Dockerfile                         # The single all-in-one image
├── .dockerignore
├── .env.example
├── .gitignore
└── .github/
    └── workflows/
        └── build.yml                  # Single image CI
```

---

## 5. Technology Choices

### 5.1 Backend

| Component | Technology | Version | Rationale |
|---|---|---|---|
| Language | Python | 3.11 | Async support, type hints, broad library ecosystem |
| Framework | FastAPI | ≥ 0.115 | Async-native, OpenAPI generation, Pydantic v2 integration |
| ORM | SQLAlchemy | 2.0+ (async) | Mature, typed mapped columns, async session support |
| Migrations | Alembic | ≥ 1.14 | Standard SQLAlchemy migration tool |
| Default DB | SQLite | via `aiosqlite` | Zero-config, single-file; WAL mode for concurrency |
| Optional DB | PostgreSQL | via `asyncpg` | Production scale-out path |
| OCR | Tesseract | via `pytesseract` | Open-source, no cloud dependency |
| PDF | PyMuPDF (`fitz`) | ≥ 1.25 | Fast page-to-image rasterisation |
| Image processing | Pillow | ≥ 11.0 | Preprocessing for OCR, product image resize |
| LLM client | OpenAI Python SDK | ≥ 1.60 | Works with any OpenAI-compatible endpoint (Ollama, vLLM, etc.) |
| Fuzzy matching | rapidfuzz | ≥ 3.14 | Token sort ratio + partial ratio for OCR name matching |
| Task queue | Celery | ≥ 5.4 (redis extra) | Proven distributed task execution |
| Broker | Redis | 7 (embedded in container) | Lightweight, no external dep required |
| Auth tokens | itsdangerous | ≥ 2.2 | Signed session cookies, invite tokens |
| Password hash | bcrypt | ≥ 4.2 | Industry standard |
| HTTP client | httpx | ≥ 0.28 | Async HTTP for LLM health checks, image fetch |
| Settings | pydantic-settings | ≥ 2.7 | Typed, `.env`-aware configuration |
| Package manager | uv | latest | Fast, lockfile-based Python package management |

### 5.2 Frontend

| Component | Technology | Version | Rationale |
|---|---|---|---|
| Language | TypeScript | 5.9 | Strict mode, latest features |
| UI framework | React | 19 | Current stable, concurrent features |
| Build tool | Vite | 8 | Fast HMR, ESM-native |
| CSS | Tailwind CSS | v4 | Utility-first, v4 with `@tailwindcss/vite` plugin |
| Server state | TanStack Query | 5 | Cache, refetch, pagination, mutations |
| Client state | Zustand | 5 | Minimal, hook-based global state |
| Routing | React Router | 7 | Nested routes, lazy loading, data loaders |
| Charts | Recharts | 3 | Declarative React charting |
| Icons | Lucide React | latest | Clean, tree-shakeable icon set |
| Date formatting | date-fns | 4 | Lightweight, tree-shakeable date utilities |
| PWA | vite-plugin-pwa | latest | Service worker + manifest generation |
| Package manager | Bun | 1 | Fast installs, native lockfile |

### 5.3 Infrastructure (In-Container)

| Component | Role |
|---|---|
| **Nginx** | Port 80, serves SPA static files, reverse-proxies `/api/*`, `/ws/*`, `/files/*` to Uvicorn on 127.0.0.1:8000 |
| **Uvicorn** | ASGI server for FastAPI on 127.0.0.1:8000 |
| **Celery worker** | prefork pool, concurrency=1, processes receipt jobs |
| **Redis** | In-memory broker on 127.0.0.1:6379, no persistence |
| **Supervisor** | Manages all four processes, restarts on failure |

---

## 6. Data Model

### 6.1 Base Mixin

Every model inherits `BaseMixin` providing:

```python
class BaseMixin:
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
```

### 6.2 Entity Definitions

#### `users`

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK, UUID |
| `email` | `String(255)` | UNIQUE, NOT NULL, indexed |
| `display_name` | `String(100)` | NOT NULL, default `""` |
| `password_hash` | `String(255)` | NOT NULL |
| `role` | `String(20)` | NOT NULL, default `"member"` — values: `admin`, `member` |
| `household_id` | `String(36)` | FK → `households.id` ON DELETE SET NULL, nullable |
| `is_active` | `Boolean` | NOT NULL, default `True` |
| `created_at` | `DateTime(tz)` | NOT NULL |
| `updated_at` | `DateTime(tz)` | NOT NULL |

Relationships: `household` (Household, back_populates=`users`), `receipts` (Receipt[], back_populates=`user`).

#### `user_sessions`

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK (signed token payload, not auto-UUID) |
| `user_id` | `String(36)` | FK → `users.id` ON DELETE CASCADE, indexed |
| `expires_at` | `DateTime(tz)` | NOT NULL |
| `ip_address` | `String(45)` | nullable |
| `user_agent` | `String(500)` | nullable |
| `created_at` | `DateTime(tz)` | NOT NULL |

No `updated_at` — sessions are immutable.

#### `households`

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK, UUID |
| `name` | `String(100)` | NOT NULL |
| `owner_id` | `String(36)` | FK → `users.id` ON DELETE RESTRICT |
| `sharing_mode` | `String(20)` | NOT NULL, default `"shared"` — values: `shared`, `private` |
| `created_at` | `DateTime(tz)` | NOT NULL |
| `updated_at` | `DateTime(tz)` | NOT NULL |

Relationships: `users` (User[], foreign_keys=`User.household_id`), `owner` (User, foreign_keys=`[owner_id]`).

#### `receipts`

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK, UUID |
| `user_id` | `String(36)` | FK → `users.id` ON DELETE CASCADE |
| `household_id` | `String(36)` | FK → `households.id` ON DELETE SET NULL, nullable |
| `store_id` | `String(36)` | FK → `stores.id` ON DELETE SET NULL, nullable |
| `transaction_date` | `Date` | nullable |
| `currency` | `String(3)` | NOT NULL, default `"CAD"` |
| `subtotal` | `Integer` | nullable (cents) |
| `tax` | `Integer` | nullable (cents) |
| `total` | `Integer` | nullable (cents) |
| `source` | `String(20)` | NOT NULL — values: `camera`, `upload`, `manual` |
| `status` | `String(20)` | NOT NULL, default `"pending"` — values: `pending`, `processing`, `processed`, `reviewed`, `failed`, `deleted` |
| `file_path` | `String(500)` | nullable (relative to DATA_DIR) |
| `thumbnail_path` | `String(500)` | nullable |
| `page_count` | `Integer` | NOT NULL, default `1` |
| `ocr_confidence` | `Float` | nullable (0.0–1.0) |
| `extraction_source` | `String(20)` | nullable — values: `llm`, `heuristic` |
| `raw_ocr_text` | `Text` | nullable |
| `duplicate_of` | `String(36)` | FK → `receipts.id` ON DELETE SET NULL, nullable |
| `notes` | `Text` | nullable |
| `created_at` | `DateTime(tz)` | NOT NULL |
| `updated_at` | `DateTime(tz)` | NOT NULL |

Indexes: `(user_id, transaction_date)`, `(household_id, transaction_date)`, `(store_id)`, `(status)`.

Relationships: `user`, `household`, `store`, `line_items` (cascade delete), `processing_jobs` (cascade delete), `duplicate_parent` (self-referential).

#### `line_items`

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK, UUID |
| `receipt_id` | `String(36)` | FK → `receipts.id` ON DELETE CASCADE |
| `canonical_item_id` | `String(36)` | FK → `canonical_items.id` ON DELETE SET NULL, nullable |
| `name` | `String(500)` | NOT NULL (raw OCR / user-entered name) |
| `quantity` | `Float` | NOT NULL, default `1.0` |
| `unit_price` | `Integer` | nullable (cents) |
| `total_price` | `Integer` | nullable (cents) |
| `confidence` | `Float` | nullable (0.0–1.0) |
| `position` | `Integer` | NOT NULL, default `0` |
| `is_corrected` | `Boolean` | NOT NULL, default `False` |
| `created_at` | `DateTime(tz)` | NOT NULL |

No `updated_at` — corrections set `is_corrected=True` as the change signal.

Indexes: `(receipt_id, position)`, `(canonical_item_id)`.

#### `canonical_items`

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK, UUID |
| `name` | `String(255)` | UNIQUE, NOT NULL, indexed |
| `category` | `String(100)` | nullable |
| `aliases` | `JSON` | NOT NULL, default `[]` |
| `product_url` | `Text` | nullable |
| `image_path` | `String(500)` | nullable |
| `image_source` | `String(20)` | nullable — values: `user`, `auto` |
| `image_fetch_status` | `String(20)` | nullable — values: `pending`, `fetching`, `found`, `not_found`, `failed` |
| `created_at` | `DateTime(tz)` | NOT NULL |
| `updated_at` | `DateTime(tz)` | NOT NULL |

#### `match_suggestions`

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK, UUID |
| `line_item_id` | `String(36)` | FK → `line_items.id` ON DELETE CASCADE |
| `canonical_item_id` | `String(36)` | FK → `canonical_items.id` ON DELETE CASCADE |
| `confidence` | `Float` | NOT NULL (0–100 scale) |
| `status` | `String(20)` | NOT NULL, default `"pending"` — values: `pending`, `accepted`, `rejected` |
| `created_at` | `DateTime(tz)` | NOT NULL |
| `resolved_at` | `DateTime(tz)` | nullable |

Indexes: `(line_item_id)`, `(status)`.
Unique constraint: `(line_item_id, canonical_item_id)`.

#### `stores`

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK, UUID |
| `name` | `String(255)` | NOT NULL, indexed |
| `address` | `String(500)` | nullable |
| `chain` | `String(100)` | nullable |
| `latitude` | `Float` | nullable |
| `longitude` | `Float` | nullable |
| `created_by` | `String(36)` | FK → `users.id` ON DELETE RESTRICT |
| `is_verified` | `Boolean` | NOT NULL, default `False` |
| `created_at` | `DateTime(tz)` | NOT NULL |
| `updated_at` | `DateTime(tz)` | NOT NULL |

#### `processing_jobs`

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK, UUID |
| `receipt_id` | `String(36)` | FK → `receipts.id` ON DELETE CASCADE |
| `status` | `String(20)` | NOT NULL — values: `queued`, `running`, `completed`, `failed` |
| `stage` | `String(30)` | nullable — values: `ocr`, `extraction`, `done` |
| `model_config_id` | `String(36)` | FK → `model_configs.id` ON DELETE SET NULL, nullable |
| `error_message` | `Text` | nullable |
| `celery_task_id` | `String(255)` | nullable |
| `started_at` | `DateTime(tz)` | nullable |
| `completed_at` | `DateTime(tz)` | nullable |
| `created_at` | `DateTime(tz)` | NOT NULL |

No `updated_at` — status/stage transitions serve as the audit trail.

#### `model_configs`

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK, UUID |
| `name` | `String(100)` | NOT NULL |
| `provider_type` | `String(20)` | NOT NULL |
| `base_url` | `String(500)` | NOT NULL |
| `model_name` | `String(100)` | NOT NULL |
| `api_key_encrypted` | `String(500)` | nullable |
| `is_active` | `Boolean` | NOT NULL, default `False` |
| `is_default` | `Boolean` | NOT NULL, default `False` |
| `timeout_seconds` | `Integer` | NOT NULL, default `30` |
| `max_retries` | `Integer` | NOT NULL, default `1` |
| `last_health_check` | `DateTime(tz)` | nullable |
| `health_status` | `String(20)` | nullable |
| `created_at` | `DateTime(tz)` | NOT NULL |
| `updated_at` | `DateTime(tz)` | NOT NULL |

### 6.3 Money Representation

All monetary values are stored as **integers in minor units (cents)**. The frontend
formats them via a shared `formatMoney(cents, currency)` helper. The currency is
always a 3-letter ISO code (default `CAD`).

---

## 7. Backend Architecture

### 7.1 Application Factory (`app/main.py`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    retroactive_task = asyncio.create_task(
        start_retroactive_loop(session_factory)
    )
    yield
    retroactive_task.cancel()
    with suppress(asyncio.CancelledError):
        await retroactive_task
    await engine.dispose()

app = FastAPI(title="LedgerLens API", lifespan=lifespan)

# Middleware (outermost first)
app.add_middleware(AuthMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(CORSMiddleware, ...)

# Routers
for router_module in [auth, receipts, items, stores, dashboard, household, admin, jobs, line_items, suggestions]:
    app.include_router(router_module.router, prefix="/api/v1")
app.include_router(ws.router)  # WebSocket at /ws/jobs (no API prefix)

# Static files
app.mount("/files", StaticFiles(directory=settings.DATA_DIR), name="files")
```

### 7.2 Core Module (`app/core/`)

#### `exceptions.py` — Domain Exception Hierarchy

```python
class AppError(Exception):
    """Base for all domain errors."""
    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code

class NotFoundError(AppError): ...      # → 404
class ConflictError(AppError): ...      # → 409
class ForbiddenError(AppError): ...     # → 403
class ValidationError(AppError): ...    # → 400 (domain, not Pydantic)
class AuthenticationError(AppError): ...# → 401

# Specific errors
class ReceiptNotFoundError(NotFoundError): ...
class ItemNotFoundError(NotFoundError): ...
class StoreNotFoundError(NotFoundError): ...
class JobNotFoundError(NotFoundError): ...
class HouseholdNotFoundError(NotFoundError): ...
class DuplicateEmailError(ConflictError): ...
class ActiveJobExistsError(ConflictError): ...
class InvalidCredentialsError(AuthenticationError): ...
class OCRProcessingError(AppError): ...
```

A global exception handler in `main.py` maps these to HTTP responses:

```python
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    status_map = {
        NotFoundError: 404,
        ConflictError: 409,
        ForbiddenError: 403,
        ValidationError: 400,
        AuthenticationError: 401,
    }
    status_code = 500
    for cls, code in status_map.items():
        if isinstance(exc, cls):
            status_code = code
            break
    return JSONResponse(status_code=status_code, content={"detail": exc.message})
```

#### `security.py`

Consolidates `hash_password`, `verify_password`, the `URLSafeTimedSerializer` for
session tokens and household invite tokens.

#### `time.py`

```python
from datetime import UTC, datetime

def utc_now() -> datetime:
    return datetime.now(UTC)
```

Used by every model and service. No more per-file `_utc_now()`.

### 7.3 Repository Layer (`app/repositories/`)

Each repository encapsulates all SQLAlchemy queries for a single model. Example:

```python
class ReceiptRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, receipt_id: str) -> Receipt | None: ...

    async def get_for_user(
        self, receipt_id: str, visibility: ColumnElement[bool]
    ) -> Receipt | None: ...

    async def list_paginated(
        self, visibility: ColumnElement[bool],
        filters: ReceiptFilters, page: int, per_page: int,
        sort_by: str, sort_dir: str,
    ) -> tuple[list[Receipt], int]: ...

    async def create(self, receipt: Receipt) -> Receipt: ...

    async def update(self, receipt: Receipt) -> None: ...

    async def soft_delete(self, receipt: Receipt) -> None: ...
```

**Key rule**: Repositories never import from `routers/` or raise HTTP exceptions.
They return `None` when entities are not found; the service layer raises domain errors.

### 7.4 Service Layer (`app/services/`)

Services contain business logic and orchestrate repositories. They accept `AsyncSession`
as a parameter (injected by the router via `Depends(get_db)`).

Example — `services/receipt.py`:

```python
class ReceiptService:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.repo = ReceiptRepository(db)
        self.store_repo = StoreRepository(db)

    async def upload(self, file: UploadFile, source: str) -> Receipt:
        receipt = Receipt(user_id=self.user.id, household_id=self.user.household_id, source=source, status="pending")
        await self.repo.create(receipt)
        file_path, thumb, pages = await storage.save_receipt_file(file, self.user.id, receipt.id)
        receipt.file_path = file_path
        receipt.thumbnail_path = thumb
        receipt.page_count = pages
        await self.db.commit()
        await processing.enqueue_receipt(receipt.id, self.db)
        return receipt

    async def get_detail(self, receipt_id: str) -> Receipt:
        vis = await scope.receipt_visibility_clause(self.db, self.user)
        receipt = await self.repo.get_for_user(receipt_id, vis)
        if receipt is None:
            raise ReceiptNotFoundError(f"Receipt {receipt_id} not found")
        return receipt
    ...
```

### 7.5 Router Layer (`app/routers/`)

Routers are thin — they parse HTTP inputs, construct services, call service methods,
and serialise responses. Example:

```python
@router.post("", response_model=ReceiptListItem, status_code=201)
async def upload_receipt(
    file: UploadFile = File(...),
    source: Literal["camera", "upload"] = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReceiptListItem:
    svc = ReceiptService(db, user)
    receipt = await svc.upload(file, source)
    return to_receipt_list_item(receipt)
```

### 7.6 Middleware

#### `AuthMiddleware`

Checks for `session_id` cookie on all `/api/*` paths except `/api/v1/auth/*`,
`/docs`, and `/openapi.json`. Returns `401` JSON if missing.

#### `SecurityMiddleware`

Adds security headers to every response:
- `Content-Security-Policy`: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' ws: wss:; font-src 'self'`
- `X-Content-Type-Options`: `nosniff`
- `X-Frame-Options`: `DENY`

---

## 8. Frontend Architecture

### 8.1 Entry Point

`main.tsx` creates a `QueryClient` (staleTime: 30s) and renders `<App />` inside
`<QueryClientProvider>` and `<StrictMode>`.

### 8.2 Routing (`router.tsx`)

```
/                  → redirect to /dashboard
/login             → Login (public)
/register          → Register (public)
<ProtectedRoute>   → fetches /auth/me, redirects to /login if unauthenticated
  <AppShell>       → sidebar + mobile tab bar + <Suspense> outlet
    /dashboard
    /receipts
    /receipts/add
    /receipts/manual
    /receipts/:id
    /items
    /items/:id
    /price-tracker
    /stores
    /settings
    /settings/household
    /admin/models
    /join/:token
```

All page components are lazy-loaded via `React.lazy`.

### 8.3 State Management

| Store | Contents |
|---|---|
| **`appStore`** (Zustand) | `user: User \| null`, `loading`, login/register/logout/fetchMe actions, dashboard filter state (dateFrom, dateTo, storeId, category), upload pending count |
| **TanStack Query** | All server data: receipts, items, stores, dashboard aggregates, jobs, suggestions, household, admin models |

### 8.4 API Client (`services/api.ts`)

A `fetch`-based wrapper that:
- Prepends `/api/v1` to relative paths.
- Sets `credentials: "include"` for cookies.
- Auto-sets `Content-Type: application/json` for non-FormData bodies.
- On 401 (non-auth paths), redirects to `/login`.
- Reads error `detail` from JSON response body.
- Exposes `api.get`, `api.post`, `api.patch`, `api.delete`, `api.upload`.

### 8.5 WebSocket (`services/websocket.ts`)

`WSService` singleton:
- Connects to `ws(s)://<host>/ws/jobs?session_id=<token>`.
- Exponential backoff reconnection (1s → 30s max).
- Parses incoming messages as `ProcessingJob` updates.
- Exposes `subscribe(handler)` → unsubscribe function.
- `useProcessingJobs` hook subscribes and invalidates TanStack Query cache on updates.

### 8.6 Hooks Pattern

Each hook module maps 1:1 to an API resource group. Example pattern:

```typescript
export function useReceipts(filters: ReceiptFilters) {
  return useQuery({
    queryKey: ["receipts", filters],
    queryFn: () => api.get<PaginatedResponse<Receipt>>("/receipts", filters),
  });
}

export function useUploadReceipt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => api.upload<Receipt>("/receipts", formData),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["receipts"] }),
  });
}
```

### 8.7 Component Hierarchy

```
AppShell
├── Sidebar (desktop) / TabBar (mobile)
└── <Suspense fallback={<Spinner />}>
    └── <Outlet /> → page component
        ├── Dashboard
        │   ├── SummaryCards
        │   ├── SpendingByStoreChart (Recharts BarChart)
        │   ├── SpendingByMonthChart (Recharts LineChart)
        │   └── SpendingByCategoryChart (Recharts PieChart)
        ├── Receipts
        │   ├── FilterBar
        │   ├── ReceiptCard[] (grid)
        │   └── Pagination
        ├── ReceiptDetail
        │   ├── ReceiptHeader (store, date, totals, status)
        │   ├── LineItemTable (editable)
        │   ├── ProcessingStatus
        │   └── Actions (reprocess, delete)
        ├── AddReceipt
        │   ├── CameraCapture
        │   └── FileUpload
        ├── Items
        │   ├── SearchBar
        │   ├── ItemCard[] (grid)
        │   └── Pagination
        ├── ProductDetail
        │   ├── ProductForm (name, category, URL)
        │   ├── AliasManager
        │   ├── ProductImageUpload
        │   └── MatchSuggestionCard[]
        └── ... (other pages follow similar patterns)
```

---

## 9. Single-Container Docker Design

### 9.1 Dockerfile

```dockerfile
# ── Stage 1: Build frontend ─────────────────────────────────
FROM oven/bun:1 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/bun.lock* ./
RUN bun install --frozen-lockfile
COPY frontend/ .
RUN bun run build

# ── Stage 2: Final all-in-one image ─────────────────────────
FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    nginx \
    redis-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY backend/ .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked

ENV PATH="/app/backend/.venv/bin:$PATH" PYTHONUNBUFFERED=1

COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

COPY infra/nginx.conf /etc/nginx/conf.d/default.conf
COPY infra/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY infra/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && rm -f /etc/nginx/sites-enabled/default

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
```

### 9.2 `infra/supervisord.conf`

```ini
[supervisord]
nodaemon=true
user=root
logfile=/dev/null
logfile_maxbytes=0
pidfile=/var/run/supervisord.pid

[unix_http_server]
file=/var/run/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[program:redis]
command=redis-server --save "" --appendonly no --bind 127.0.0.1
priority=10
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:backend]
command=uvicorn app.main:app --host 127.0.0.1 --port 8000
directory=/app/backend
environment=PATH="/app/backend/.venv/bin:%(ENV_PATH)s"
priority=20
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:worker]
command=celery -A app.worker worker --pool=prefork --concurrency=1 --loglevel=info
directory=/app/backend
environment=PATH="/app/backend/.venv/bin:%(ENV_PATH)s"
priority=20
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:nginx]
command=nginx -g "daemon off;"
priority=30
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

### 9.3 `infra/nginx.conf`

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /files/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### 9.4 `infra/entrypoint.sh`

```bash
#!/bin/sh
set -e
DATA_DIR="${DATA_DIR:-/app/data}"
mkdir -p "$DATA_DIR"
cd /app/backend
echo "Running database migrations..."
alembic upgrade head
echo "Starting supervisord..."
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
```

### 9.5 Running the Container

```bash
docker build -t ledgerlens .
docker run -d \
  -p 3000:80 \
  -v ./data:/app/data \
  -e SECRET_KEY=your-secret-here \
  -e LLM_BASE_URL=http://host.docker.internal:11434/v1 \
  -e LLM_MODEL=llama3.2 \
  --name ledgerlens \
  ledgerlens
```

---

## 10. API Contract

All endpoints live under `/api/v1`. Responses use JSON. Authentication is via
`session_id` cookie (httpOnly, sameSite=lax, 30-day max-age).

### 10.1 Pagination

Standard paginated responses use this envelope:

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

Query parameters: `page` (default 1), `per_page` (default 20, max 100).

### 10.2 Error Responses

```json
{
  "detail": "Human-readable error message"
}
```

Pydantic validation errors return an array of objects in `detail`.

### 10.3 Endpoint Specifications

(All endpoints preserve the exact same request/response shapes as the current system.
Refer to §2.3 for the full endpoint listing. Key contracts below.)

#### `POST /auth/register`

- **Body**: `{ email, display_name, password }`
- **Response** (201): `UserResponse` + `Set-Cookie: session_id`
- **Error**: 409 if email taken

#### `POST /auth/login`

- **Body**: `{ email, password }`
- **Response** (200): `UserResponse` + `Set-Cookie: session_id`
- **Error**: 401 if invalid credentials

#### `POST /receipts`

- **Body**: `multipart/form-data` with `file` (image/PDF) + `source` (`camera`|`upload`)
- **Response** (201): `ReceiptListItem`
- **Side effect**: Saves file, creates ProcessingJob, dispatches Celery task

#### `POST /receipts/manual`

- **Body**: `ManualReceiptCreate` JSON (store_name, date, line_items, totals)
- **Response** (201): `ReceiptDetail`

#### `GET /items/:id/prices`

- **Query**: `store_ids` (comma-separated), `date_from`, `date_to`
- **Response**: `{ item: CanonicalItemResponse, data_points: PricePoint[] }`

#### `POST /suggestions/:id/accept`

- **Response**: `MatchSuggestionDetail`
- **Side effect**: Links line_item to canonical_item, adds name as alias

#### `WS /ws/jobs?session_id=<token>`

- Server sends `ProcessingJob` JSON on status/stage changes.
- Client can send `{ type: "ping" }` → server responds `{ type: "pong" }`.

---

## 11. Background Processing

### 11.1 Celery Configuration

```python
celery_app = Celery("ledgerlens", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=settings.TASK_SOFT_TIME_LIMIT,   # default 300s
    task_time_limit=settings.TASK_HARD_TIME_LIMIT,         # default 360s
)
```

### 11.2 Worker Initialisation

On `worker_process_init`: create a dedicated async engine + session factory
(with NullPool + SQLite WAL pragmas if applicable).

On `worker_ready`: verify Tesseract binary is on PATH; recover orphaned jobs
(mark stale running → failed; redispatch stale queued).

### 11.3 Task: `process_receipt`

1. Load ProcessingJob by ID; set `status=running`, `stage=ocr`, record `celery_task_id`.
2. Load Receipt; resolve file path.
3. **OCR stage**: Call `ocr.extract_text` (image) or `ocr.extract_text_from_pdf` (PDF).
   - Preprocessing: grayscale → upscale if width < 1500px → binarize threshold.
   - Tesseract with `--oem 3 --psm 6 --dpi 300`, configurable via settings.
   - Store `raw_ocr_text` and `ocr_confidence` on Receipt.
4. **Extraction stage**: Call `llm.extract_receipt_data(raw_text, model_config)`.
   - System prompt instructs JSON output with cents, ISO dates, line items.
   - If LLM result has no usable `total_cents`, fall back to `heuristic.extract_receipt_data`.
5. **Normalisation**: Find or create Store (by normalised name). Delete existing LineItems.
   For each extracted line item, run `normalization.find_or_create_canonical_item`:
   - Exact name match → link.
   - Exact alias match → link.
   - Fuzzy match (rapidfuzz) ≥ 85 → auto-link + add as alias.
   - Fuzzy match ≥ 60 → create MatchSuggestion.
   - No match → create new CanonicalItem.
6. Set Receipt `status=processed`. Set ProcessingJob `status=completed`, `stage=done`.
7. On any exception: set Receipt `status=failed`, ProcessingJob `status=failed` + error_message.
8. On `SoftTimeLimitExceeded`: record timeout message, re-raise.

### 11.4 Retroactive Matching

An async background loop runs on the FastAPI process (via `asyncio.create_task` in
`lifespan`). Every `RETROACTIVE_INTERVAL_SECONDS` (default 300), it scans LineItems
where `canonical_item_id IS NULL`, runs fuzzy matching, and auto-links or creates
suggestions. Batch size configurable via `RETROACTIVE_BATCH_SIZE` (default 200).

### 11.5 Orphan Recovery

On worker startup, `recover_orphaned_jobs`:
- Jobs stuck in `running` longer than `TASK_HARD_TIME_LIMIT` → mark `failed`.
- Jobs stuck in `queued` longer than 60s → redispatch via `process_receipt_task.delay`.

---

## 12. OCR & LLM Pipeline

### 12.1 OCR Service (`services/ocr.py`)

#### Image Processing

```
Input image → Pillow open → Convert to grayscale (L mode)
            → Upscale if width < 1500px (LANCZOS)
            → Binarize (threshold 150)
            → Save temp PNG
            → pytesseract.image_to_data (Dict output)
            → Group words by line_num → join into lines
            → Average confidence (0.0–1.0)
            → Clean up temp file
```

#### PDF Processing

```
Input PDF → PyMuPDF open → For each page:
          → Rasterize at 300 DPI → temp PNG
          → Run image OCR pipeline above
          → Concatenate all page texts with double newline
          → Average confidence across pages
          → Clean up temp files
```

Both run via `asyncio.to_thread` to avoid blocking the event loop.

#### Health Check

`verify_tesseract()`: checks `shutil.which("tesseract")` — raises `RuntimeError`
if missing. Called on Celery worker startup.

### 12.2 LLM Service (`services/llm.py`)

#### System Prompt

```
You extract structured data from raw receipt OCR text.
Respond with a single JSON object only (no markdown fences, no commentary).
All monetary amounts MUST be integers in minor units (cents).
Use null for unknown numeric fields.
currency is a 3-letter ISO code when inferable, else null.
transaction_date must be YYYY-MM-DD or null.
line_items is an array of objects: {"name", "quantity", "unit_price_cents", "total_price_cents"}.
```

#### Expected Output Schema

```json
{
  "store_name": "string | null",
  "store_address": "string | null",
  "transaction_date": "YYYY-MM-DD | null",
  "currency": "CAD | USD | ... | null",
  "subtotal_cents": "int | null",
  "tax_cents": "int | null",
  "total_cents": "int | null",
  "line_items": [
    {
      "name": "string",
      "quantity": 1.0,
      "unit_price_cents": "int | null",
      "total_price_cents": "int | null"
    }
  ]
}
```

#### Client Construction

If a ProcessingJob has a `model_config_id`, use that ModelConfig's `base_url`,
`model_name`, `api_key_encrypted`, `timeout_seconds`, `max_retries`.
Otherwise fall back to env vars (`LLM_BASE_URL`, `LLM_MODEL`, etc.).

First attempt uses `response_format={"type": "json_object"}`. If that raises an
`APIError` (model doesn't support JSON mode), retry without it.

Strip markdown code fences from response before `json.loads`.

On failure (timeout, rate limit, parse error), return `{}` — caller falls back to
heuristic.

### 12.3 Heuristic Service (`services/heuristic.py`)

Regex-based extraction used when the LLM fails or returns unusable results:

- **Total**: Regex for `TOTAL`, `AMOUNT DUE`, `BALANCE`, `GRAND TOTAL` lines.
- **Tax**: Regex for `TAX`, `HST`, `GST`, `PST`, `VAT` lines.
- **Date**: `YYYY-MM-DD` or `MM/DD/YYYY` patterns.
- **Store name**: First non-empty, non-decorative line.
- **Line items**: Lines matching `<name> <price>` pattern, excluding totals/payment lines.
  Capped at 50 items.

Returns the same JSON shape as the LLM output.

---

## 13. Authentication & Authorization

### 13.1 Session-Based Auth

1. **Register**: hash password (bcrypt), create User (first user gets role `admin`),
   create UserSession (30-day expiry), sign session_id with `URLSafeTimedSerializer`,
   set `session_id` cookie.
2. **Login**: verify password, create session, set cookie.
3. **Logout**: delete session row, delete cookie.
4. **`GET /auth/me`**: validate session cookie → return current User.

### 13.2 Middleware Gate

`AuthMiddleware` requires `session_id` cookie on all `/api/*` paths except
`/api/v1/auth/*`, `/docs`, `/openapi.json`. Returns 401 JSON if missing.

### 13.3 Dependency: `get_current_user`

Used as `Depends(get_current_user)` in every protected router. Loads session → loads user → checks `is_active`. Raises 401 on failure.

### 13.4 Role-Based Access

- **Admin**: Required for `/admin/*` endpoints, `PATCH /stores/:id`.
  Checked via `_require_admin(user)` → raises `ForbiddenError` if `user.role != "admin"`.
- **Owner**: Receipt update/delete requires `receipt.user_id == current_user.id`.
  Household management requires `household.owner_id == current_user.id`.

### 13.5 Household Invites

Signed tokens via `URLSafeTimedSerializer` with salt `"household-invite"`,
max age 7 days. Token payload: `{"household_id": "<uuid>"}`.
Invite URL format: `/join/<token>`.

---

## 14. Real-Time Communication

### 14.1 WebSocket Endpoint

`WS /ws/jobs?session_id=<token>`

1. Validate session token against DB.
2. Register connection in `ConnectionManager` keyed by `user_id`.
3. Loop: receive messages (handle `ping` → `pong`); on disconnect, unregister.

### 14.2 Server-Push (Enhancement)

The Celery task should push ProcessingJob status updates to the WebSocket. After each
stage transition (`ocr` → `extraction` → `done` / `failed`), the task publishes a
message. The WebSocket `ConnectionManager` delivers it to the connected user.

Implementation approach: After the task updates the ProcessingJob in the DB, it also
publishes to a Redis pub/sub channel keyed by `user:<user_id>:jobs`. The FastAPI
process subscribes to these channels for connected users and forwards to WebSocket
clients. This decouples the Celery worker from the WebSocket process.

### 14.3 Client Handling

The frontend `WSService` parses incoming messages as `ProcessingJob` objects and
emits them to subscribers. The `useProcessingJobs` hook invalidates relevant
TanStack Query caches (`["jobs"]`, `["receipts"]`) on updates.

---

## 15. File Storage

### 15.1 Directory Layout (under `DATA_DIR`)

```
data/
├── receipts/
│   └── <user_id>/
│       └── <receipt_id>/
│           ├── original.<ext>     # jpg, png, heic, pdf
│           └── thumbnail.png      # PDF first-page render
├── products/
│   └── <item_id>/
│       └── image.webp             # Resized to 512×512, 85% quality
└── ledgerlens.db                  # SQLite database (if using SQLite)
```

### 15.2 Upload Limits

- Receipt files: JPEG, PNG, HEIC, PDF.
- Product images: JPEG, PNG, WebP; max 5 MB; resized to 512×512 WebP.

### 15.3 Serving

Files served via FastAPI `StaticFiles` mount at `/files/`, reverse-proxied by Nginx.
Relative paths stored in DB; URLs constructed as `/files/<relative_path>`.

### 15.4 Path Safety

`storage.get_receipt_path()` resolves the path and validates it falls under
`DATA_DIR` via `path.relative_to(root)` to prevent directory traversal.

---

## 16. Database Migrations

### 16.1 Alembic Configuration

- `alembic.ini`: script_location = `alembic`, async SQLAlchemy driver.
- `alembic/env.py`: uses app settings for URL, imports all models for metadata,
  `render_as_batch=True` for SQLite compatibility, runs migrations via `asyncio.run`.

### 16.2 Consolidated Initial Migration

The three existing migrations are consolidated into a single `0001_initial_schema.py`
that creates all 10 tables with their indexes, foreign keys, and constraints.

Tables created in order (respecting FK dependencies):
1. `users` (no FK deps)
2. `households` (FK → users)
3. `user_sessions` (FK → users)
4. `stores` (FK → users)
5. `model_configs` (no FK deps)
6. `canonical_items` (no FK deps)
7. `receipts` (FK → users, households, stores)
8. `line_items` (FK → receipts, canonical_items)
9. `match_suggestions` (FK → line_items, canonical_items)
10. `processing_jobs` (FK → receipts, model_configs)

SQLite pragmas (`journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON`,
`synchronous=NORMAL`) are set at engine connect time, not in migrations.

### 16.3 Future Migrations

New features add new migration files following Alembic's auto-generate workflow.
Always use `render_as_batch=True` for SQLite `ALTER TABLE` compatibility.

---

## 17. Testing Strategy

### 17.1 Backend

| Layer | Tool | Approach |
|---|---|---|
| Unit (services) | pytest + pytest-asyncio | Mock repositories; test business logic in isolation |
| Unit (repositories) | pytest + in-memory SQLite | Real DB queries against test schema |
| Integration | pytest + httpx `TestClient` | Full request cycle with test DB |
| Task | pytest + Celery eager mode | `task_always_eager=True` for synchronous execution |

#### Fixtures (`conftest.py`)

```python
@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def test_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
```

#### Factory (`factories.py`)

Provides `create_user(db, **overrides)`, `create_receipt(db, user, **overrides)`,
`create_line_item(db, receipt, **overrides)`, etc. for concise test setup.

### 17.2 Frontend

| Layer | Tool | Approach |
|---|---|---|
| Component | Vitest + Testing Library | Render components, assert DOM output |
| Hook | Vitest + renderHook | Test TanStack Query hooks with MSW |
| Integration | Vitest + MSW | Mock API, test page-level flows |

Configuration: `vitest.config.ts` with `jsdom` environment, `src/test-setup.ts`
imports `@testing-library/jest-dom`.

---

## 18. CI/CD

### 18.1 GitHub Actions (`.github/workflows/build.yml`)

```yaml
name: Build & Push to GHCR

on:
  push:
    branches: [main]
    tags: ["v*"]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v6

      - id: repo
        shell: bash
        run: echo "name=${GITHUB_REPOSITORY,,}" >> "$GITHUB_OUTPUT"

      - uses: docker/setup-buildx-action@v4

      - if: github.event_name != 'pull_request'
        uses: docker/login-action@v4
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - id: meta
        uses: docker/metadata-action@v6
        with:
          images: ${{ env.REGISTRY }}/${{ steps.repo.outputs.name }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - uses: docker/build-push-action@v7
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Single image**: `ghcr.io/<owner>/ledgerlens` (no separate backend/frontend images).

---

## 19. Configuration & Environment

### 19.1 Settings Class (`app/core/config.py`)

```python
class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/ledgerlens.db"
    DATA_DIR: str = "./data"

    # LLM
    LLM_BASE_URL: str = "http://127.0.0.1:11434/v1"
    LLM_MODEL: str = "llama3.2"
    LLM_API_KEY: str = ""
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_RETRIES: int = 1

    # Auth
    SECRET_KEY: str = "change-me"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Google CSE (optional, for product images)
    GOOGLE_CSE_API_KEY: str = ""
    GOOGLE_CSE_CX: str = ""

    # Fuzzy matching
    FUZZY_AUTO_LINK_THRESHOLD: int = 85
    FUZZY_SUGGEST_THRESHOLD: int = 60

    # Retroactive matching
    RETROACTIVE_BATCH_SIZE: int = 200
    RETROACTIVE_INTERVAL_SECONDS: int = 300

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    TASK_SOFT_TIME_LIMIT: int = 300
    TASK_HARD_TIME_LIMIT: int = 360

    # Tesseract
    TESSERACT_LANG: str = "eng"
    TESSERACT_PSM: int = 6
    TESSERACT_DPI: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

### 19.2 `.env.example`

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./data/ledgerlens.db
DATA_DIR=./data

# LLM (Ollama default)
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL=llama3.2
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=1

# Session secret — CHANGE IN PRODUCTION
SECRET_KEY=change-me-to-a-random-string

# Server
HOST=0.0.0.0
PORT=8000

# Celery / Redis
CELERY_BROKER_URL=redis://localhost:6379/0
TASK_SOFT_TIME_LIMIT=300
TASK_HARD_TIME_LIMIT=360
```

### 19.3 Docker Environment

When running inside the single container, `CELERY_BROKER_URL` defaults to
`redis://127.0.0.1:6379/0` (embedded Redis). `LLM_BASE_URL` should point to
an external Ollama instance (e.g. `http://host.docker.internal:11434/v1`).

---

## 20. Implementation Order

### Phase 1: Foundation

1. **Project scaffolding**: Create directory structure per §4.
2. **`app/core/`**: `config.py`, `database.py`, `exceptions.py`, `security.py`, `time.py`.
3. **Models**: All 10 models with `BaseMixin`.
4. **Schemas**: All Pydantic models.
5. **Single Alembic migration**: `0001_initial_schema.py`.
6. **`app/main.py`**: FastAPI app factory with lifespan, middleware, CORS.

### Phase 2: Auth & Users

7. **`repositories/user.py`**, **`repositories/session.py`**.
8. **`services/auth.py`**: register, login, logout, session management.
9. **`routers/auth.py`**: 4 endpoints.
10. **`middleware/auth.py`**, **`middleware/security.py`**.

### Phase 3: Core Receipt Flow

11. **`services/storage.py`**: file save/delete/path validation.
12. **`repositories/receipt.py`**, **`repositories/store.py`**, **`repositories/line_item.py`**.
13. **`services/receipt.py`**: upload, manual create, list, get, update, delete.
14. **`routers/receipts.py`**: all receipt endpoints.
15. **`services/scope.py`**: household-aware visibility filters.

### Phase 4: Processing Pipeline

16. **`services/ocr.py`**: Tesseract image + PDF extraction.
17. **`services/llm.py`**: OpenAI-compatible extraction.
18. **`services/heuristic.py`**: Regex fallback.
19. **`services/normalization.py`**: Store/item name normalisation.
20. **`services/matching.py`**: Fuzzy match engine.
21. **`services/extraction.py`**: Orchestrator (OCR → LLM/heuristic → normalise → persist).
22. **`worker.py`** + **`tasks/receipt_processing.py`**: Celery task, orphan recovery.
23. **`services/processing.py`**: Enqueue logic.

### Phase 5: Items, Stores, Dashboard

24. **`repositories/canonical_item.py`**, **`services/item.py`**, **`routers/items.py`**.
25. **`services/store.py`**, **`routers/stores.py`**.
26. **`services/dashboard.py`**, **`routers/dashboard.py`**.
27. **`services/image_fetcher.py`**: Google CSE product image fetch.

### Phase 6: Suggestions, Line Items, Jobs

28. **`repositories/match_suggestion.py`**, **`routers/suggestions.py`**.
29. **`routers/line_items.py`**.
30. **`repositories/processing_job.py`**, **`routers/jobs.py`**.

### Phase 7: Household & Admin

31. **`repositories/household.py`**, **`services/household.py`**, **`routers/household.py`**.
32. **`repositories/model_config.py`**, **`services/admin.py`**, **`routers/admin.py`**.

### Phase 8: WebSocket & Background

33. **`routers/ws.py`**: WebSocket with ConnectionManager.
34. **`services/retroactive_matching.py`**: Background scan loop.

### Phase 9: Frontend

35. **Project setup**: Vite + React + Tailwind v4 + PWA config.
36. **`services/api.ts`**, **`services/websocket.ts`**.
37. **`stores/appStore.ts`**: Consolidated Zustand store.
38. **`lib/types.ts`**, **`lib/utils.ts`**, **`lib/money.ts`**.
39. **`components/layout/`**: AppShell, ProtectedRoute.
40. **`components/ui/`**: Spinner, Badge, Pagination.
41. **Pages**: Login → Register → Dashboard → Receipts → ReceiptDetail → AddReceipt → ManualEntry → Items → ProductDetail → PriceTracker → Stores → Settings → HouseholdSettings → AdminModels → JoinHousehold.
42. **`components/receipt/`** + **`components/product/`**: Domain components.
43. **Hooks**: All 8 TanStack Query hooks.

### Phase 10: Infrastructure & Testing

44. **Dockerfile**: Multi-stage build per §9.1.
45. **`infra/`**: nginx.conf, supervisord.conf, entrypoint.sh.
46. **CI**: `.github/workflows/build.yml`.
47. **Tests**: Fixtures, factories, unit tests for services, integration tests for API flows.
48. **`.env.example`**, **`.dockerignore`**, **`.gitignore`**.

---

## Appendix A: Store Name Normalisation Rules

Known chain prefixes that collapse to canonical names:

| Pattern | Normalised To |
|---|---|
| `walmart *` | Walmart |
| `wal-mart *` | Walmart |
| `costco *` | Costco |
| `target *` | Target |
| `loblaws *` | Loblaws |
| `metro *` | Metro |
| `safeway *` | Safeway |
| `whole foods *` | Whole Foods |
| `dollarama *` | Dollarama |
| `shoppers drug mart *` | Shoppers Drug Mart |
| `no frills *` | No Frills |
| `sobeys *` | Sobeys |

All other names → `title()` case.

## Appendix B: Item Name Normalisation Rules

- Collapse whitespace.
- Strip trailing junk: weight suffixes (`500g`, `1.5kg`), barcodes (8+ digits), SKU patterns.
- Apply `title()` case.

## Appendix C: Fuzzy Matching Thresholds

| Score Range | Action |
|---|---|
| ≥ 85 (configurable) | **Auto-link**: set `canonical_item_id`, add OCR name as alias |
| 60–84 (configurable) | **Suggest**: create `MatchSuggestion(status=pending)` if `line_item_id` provided |
| < 60 | **No match**: create new `CanonicalItem` |

Scoring: `max(token_sort_ratio, partial_ratio)` via rapidfuzz.

## Appendix D: SQLite Pragmas

Applied at engine connect time (both API and worker processes):

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;
```
