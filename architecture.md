# LedgerLens — Architecture Reference

> As-built architecture documentation for LedgerLens, a self-hosted, privacy-first
> receipt-tracking PWA. The system runs in a **single Docker container**.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Project Structure](#2-project-structure)
3. [Technology Stack](#3-technology-stack)
4. [Data Model](#4-data-model)
5. [Backend Architecture](#5-backend-architecture)
6. [Frontend Architecture](#6-frontend-architecture)
7. [Single-Container Docker Design](#7-single-container-docker-design)
8. [API Contract](#8-api-contract)
9. [Background Processing](#9-background-processing)
10. [OCR & LLM Pipeline](#10-ocr--llm-pipeline)
11. [Authentication & Authorization](#11-authentication--authorization)
12. [Real-Time Communication](#12-real-time-communication)
13. [File Storage](#13-file-storage)
14. [Database Migrations](#14-database-migrations)
15. [Testing](#15-testing)
16. [CI/CD](#16-cicd)
17. [Configuration & Environment](#17-configuration--environment)

---

## 1. System Overview

LedgerLens is a self-hosted receipt-tracking PWA. Users upload receipt images or PDFs,
which pass through an OCR → LLM extraction pipeline. The system normalises line items
into canonical products, offers fuzzy-match suggestions, tracks prices over time, and
provides spending dashboards — all shareable within a household.

### Design Principles

1. **Layered backend**: Router → Service → Repository. Routers handle HTTP concerns only; services contain business logic; repositories encapsulate all database queries.
2. **Domain exceptions**: No `HTTPException` below the router layer. Services raise domain-specific exceptions; routers translate them to HTTP responses.
3. **Single responsibility models**: Each ORM model in its own file, inheriting a `BaseMixin` that provides `id`, `created_at`, `updated_at`.
4. **Strict typing**: mypy strict mode (backend), TypeScript strict mode (frontend).
5. **Testability**: Every service accepts its DB session as a parameter. Repositories are easily mockable.
6. **Single container**: One Dockerfile, one image, four supervised processes (Redis, FastAPI, Celery worker, Nginx).

### Key Features

- **Receipt OCR + LLM extraction** — Tesseract OCR with OpenAI-compatible LLM (text or vision), heuristic fallback
- **Smart product matching** — RapidFuzz fuzzy matching with configurable auto-link and suggestion thresholds
- **Price tracking** — Historical price data per canonical product, filterable by store and date range
- **Household sharing** — Multi-user households with invite tokens and shared receipt visibility
- **Analytics dashboard** — Spending by category, store frequency, monthly trends
- **Real-time updates** — WebSocket push for processing job progress via Redis pub/sub
- **Background processing** — Celery task queue with retroactive matching loop

---

## 2. Project Structure

```
ledgerlens2/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app factory, lifespan, CORS, middleware
│   │   ├── core/
│   │   │   ├── config.py              # pydantic-settings Settings class
│   │   │   ├── database.py            # engine, session factory, Base, get_db
│   │   │   ├── dependencies.py        # FastAPI dependency injection (get_current_user, etc.)
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
│   │   │   ├── store_alias.py
│   │   │   ├── store_merge_suggestion.py
│   │   │   ├── processing_job.py
│   │   │   └── model_config.py
│   │   ├── schemas/                   # Pydantic request/response models
│   │   ├── repositories/             # Data access layer (one per model)
│   │   ├── prompts/                  # Jinja2 LLM prompt templates
│   │   │   ├── system.md.j2          # System prompt — text path (OCR-aware)
│   │   │   ├── user.md.j2            # User message — text path (OCR text + known entities)
│   │   │   ├── system_vision.md.j2   # System prompt — vision path (image-aware)
│   │   │   └── user_vision.md.j2     # User message — vision path (instruction + known entities)
│   │   ├── services/                 # Business logic layer
│   │   │   ├── auth.py               # login, register, session lifecycle
│   │   │   ├── receipt.py            # upload, manual create, update, delete, list
│   │   │   ├── extraction.py         # orchestrate OCR → vision/text LLM/heuristic → persist
│   │   │   ├── ocr.py                # Tesseract wrapper + PDF handler
│   │   │   ├── llm.py                # OpenAI-compatible chat extraction (text + vision paths)
│   │   │   ├── image_utils.py        # Base64 image encoding for vision LLM (resize, PDF pages)
│   │   │   ├── heuristic.py          # Regex-based receipt parser
│   │   │   ├── normalization.py      # Store name / item name normalisation
│   │   │   ├── matching.py           # Fuzzy match engine (rapidfuzz)
│   │   │   ├── store_matching.py     # Store fuzzy matching + alias resolution
│   │   │   ├── item.py               # Canonical item CRUD + price history
│   │   │   ├── store.py              # Store CRUD, merge, delete
│   │   │   ├── dashboard.py          # Aggregation queries
│   │   │   ├── household.py          # Household CRUD, invites, join
│   │   │   ├── admin.py              # ModelConfig CRUD
│   │   │   ├── processing.py         # Enqueue receipt, orphan recovery
│   │   │   ├── image_fetcher.py      # Google CSE image search
│   │   │   ├── storage.py            # File save/delete, path validation
│   │   │   ├── scope.py              # Household-aware visibility filters
│   │   │   ├── notifications.py      # Redis pub/sub for WebSocket
│   │   │   └── retroactive_matching.py
│   │   ├── routers/                  # HTTP + WebSocket endpoints
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
│   │   │   ├── auth.py                # Session cookie gate
│   │   │   └── security.py            # CSP + security headers
│   │   ├── tasks/
│   │   │   └── receipt_processing.py
│   │   └── worker.py                  # Celery app definition
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── router.tsx
│   │   ├── components/
│   │   │   ├── layout/                # AppShell, ProtectedRoute, AdminRoute
│   │   │   ├── receipt/               # EnrichedLineItem, EditLineItemDialog
│   │   │   ├── product/               # Product display components
│   │   │   └── ui/                    # Card, Button, Input, Dialog, Badge, etc.
│   │   ├── hooks/                     # TanStack Query hooks (8 modules), useTheme
│   │   ├── lib/                       # types.ts, utils.ts, money.ts
│   │   ├── pages/                     # 17 page components
│   │   ├── services/                  # api.ts, websocket.ts
│   │   └── stores/                    # appStore.ts, toastStore.ts, themeStore.ts (Zustand)
│   ├── public/
│   │   ├── favicon.svg
│   │   ├── manifest.json              # PWA web app manifest (start_url = /)
│   │   └── fonts/                     # Self-hosted Satoshi variable font
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── infra/
│   ├── nginx.conf                     # Reverse proxy configuration
│   ├── supervisord.conf               # Process supervisor
│   └── entrypoint.sh                  # Migration + supervisord launch
├── Dockerfile                         # Multi-stage all-in-one image
├── docker-compose.yml                 # Single-service convenience compose
├── .env.example
├── .github/workflows/
│   └── ghcr-publish.yml               # Docker image CI
└── CLAUDE.md                          # AI assistant design guidelines
```

---

## 3. Technology Stack

### Backend

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.13+ |
| Framework | FastAPI | 0.115+ |
| Server | Uvicorn | 0.34 |
| ORM | SQLAlchemy | 2.0+ (async) |
| Default DB | SQLite | via `aiosqlite` |
| Optional DB | PostgreSQL | via `asyncpg` |
| Migrations | Alembic | 1.14+ |
| OCR | Tesseract | via `pytesseract` 0.3 |
| PDF | PyMuPDF (`fitz`) | 1.25+ |
| Image processing | Pillow | 11.0+ |
| LLM client | OpenAI Python SDK | 1.60+ |
| Fuzzy matching | RapidFuzz | 3.14+ |
| Prompt templates | Jinja2 | 3.1+ |
| Task queue | Celery | 5.4+ |
| Broker | Redis | 5.0+ (embedded) |
| Auth tokens | itsdangerous | 2.2+ |
| Password hash | bcrypt | 4.2+ |
| Settings | pydantic-settings | 2.7+ |
| Package manager | uv | latest |

### Frontend

| Component | Technology | Version |
|---|---|---|
| Language | TypeScript | 5.9 |
| UI framework | React | 19 |
| Build tool | Vite | 8 |
| CSS | Tailwind CSS | 4 |
| Server state | TanStack React Query | 5 |
| Client state | Zustand | 5 |
| Routing | React Router | 7 |
| Charts | Recharts | 2 |
| Animation | Motion | 12 |
| Icons | Lucide React | 1.7+ |
| Date utilities | date-fns | 4 |
| Package manager | Bun | 1 |

### In-Container Infrastructure

| Component | Role |
|---|---|
| **Nginx** | Port 80 — serves SPA static files, proxies `/api/*`, `/ws/*`, `/files/*` to Uvicorn |
| **Uvicorn** | ASGI server on 127.0.0.1:8000 |
| **Celery worker** | prefork pool, concurrency=1, processes receipt jobs |
| **Redis** | In-memory broker on 127.0.0.1:6379, no persistence (pub/sub for WebSocket) |
| **Supervisor** | Manages all four processes, auto-restarts on failure |

---

## 4. Data Model

### Base Mixin

Every model inherits `BaseMixin` providing:

```python
class BaseMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
```

### Entity Summary (12 tables)

| Model | Table | Purpose | Key Relationships |
|---|---|---|---|
| `User` | `users` | Account with email/password/role | → Household?, → Receipt[] |
| `UserSession` | `user_sessions` | Server-side session rows (no `updated_at`) | → User |
| `Household` | `households` | Multi-user grouping | → User[] (members) |
| `Receipt` | `receipts` | Core receipt record (totals, dates, status, files) | → User, → Store?, → LineItem[], → ProcessingJob[] |
| `LineItem` | `line_items` | Individual line on a receipt (no `updated_at`) | → Receipt, → CanonicalItem?, → MatchSuggestion[] |
| `CanonicalItem` | `canonical_items` | Normalised product identity (name, aliases, category, image) | ← LineItem[], ← MatchSuggestion[] |
| `MatchSuggestion` | `match_suggestions` | Fuzzy-match proposal linking LineItem ↔ CanonicalItem | → LineItem, → CanonicalItem |
| `Store` | `stores` | Merchant (name, address, geo, chain) | → Receipt[], → StoreAlias[], → merged_into Store? |
| `StoreAlias` | `store_aliases` | OCR name variations mapped to canonical stores (indexed) | → Store |
| `StoreMergeSuggestion` | `store_merge_suggestions` | Fuzzy-match duplicate store pairs for admin review | → Store (a), → Store (b) |
| `ProcessingJob` | `processing_jobs` | Tracks async OCR/LLM pipeline runs (no `updated_at`) | → Receipt, → ModelConfig? |
| `ModelConfig` | `model_configs` | Admin-managed LLM endpoint configuration (includes vision flag) | — |

### Money Representation

All monetary values are stored as **integers in minor units (cents)**. The frontend
formats them via a shared `formatMoney(cents, currency)` helper. Currency is a 3-letter
ISO code (default `CAD`).

### Key Columns

#### `receipts`

| Column | Type | Notes |
|---|---|---|
| `status` | `String(20)` | `pending`, `processing`, `completed`, `failed` |
| `source` | `String(20)` | `camera`, `upload`, `manual` |
| `extraction_source` | `String(20)` | `llm`, `vision`, `heuristic` |
| `subtotal`, `tax`, `total` | `Integer` | Cents, nullable |
| `discount` | `Integer` | Total discount in cents, nullable |
| `payment_method` | `String(20)` | `cash`, `credit`, `debit`, `other`, nullable |
| `is_refund` | `Boolean` | Whether entire receipt is a return/refund |
| `ocr_confidence` | `Float` | 0.0–1.0, nullable |
| `raw_ocr_text` | `Text` | Text used for extraction: Tesseract output (text/heuristic path) or vision-model-read text (vision path, overwrites Tesseract output on success) |
| `duplicate_of` | FK → self | Duplicate detection reference |

#### `canonical_items`

| Column | Type | Notes |
|---|---|---|
| `name` | `String(255)` | Unique, the canonical product name |
| `aliases` | `JSON` | List of alternative names (from OCR) |
| `category` | `String(100)` | Optional product category |
| `image_path` | `String(500)` | Optional product image |
| `image_fetch_status` | `String(20)` | `pending`, `fetching`, `found`, `not_found`, `failed` |

#### `line_items`

| Column | Type | Notes |
|---|---|---|
| `name` | `String(500)` | LLM-cleaned product name |
| `raw_name` | `String(500)` | Verbatim OCR text, nullable |
| `quantity` | `Float` | Default 1.0 |
| `unit_price`, `total_price` | `Integer` | Cents, nullable |
| `discount` | `Integer` | Item-level discount in cents, nullable |
| `is_refund` | `Boolean` | Whether item is a return |
| `tax_code` | `String(5)` | Tax indicator (`H`, `G`, `P`, `F`), nullable |
| `weight_qty` | `String(50)` | Weight string for produce/deli, nullable |
| `confidence` | `Float` | Fuzzy match confidence, nullable |
| `position` | `Integer` | Order on receipt |

#### `stores`

| Column | Type | Notes |
|---|---|---|
| `name` | `String(255)` | Canonical store name |
| `address` | `String(500)` | Street address, nullable |
| `chain` | `String(100)` | Parent chain name (Walmart, Costco), nullable |
| `merged_into_id` | FK → self | Soft-redirect after merge, SET NULL |
| `is_verified` | `Boolean` | Admin-verified store |
| `latitude`, `longitude` | `Float` | Geo coordinates, nullable |

#### `store_aliases`

| Column | Type | Notes |
|---|---|---|
| `store_id` | FK → stores.id | CASCADE on delete, indexed |
| `alias_name` | `String(255)` | Original OCR text |
| `alias_name_lower` | `String(255)` | Lowered, unique constraint, indexed |
| `source` | `String(20)` | `auto`, `manual`, `ocr` |

#### `match_suggestions`

| Column | Type | Notes |
|---|---|---|
| `confidence` | `Float` | 0.0–100.0 from fuzzy matching |
| `status` | `String(20)` | `pending`, `accepted`, `rejected` |

---

## 5. Backend Architecture

### Application Factory (`app/main.py`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create data directory, engine, session factory
    # Start retroactive matching background loop
    yield
    # Cancel background tasks, dispose engine

app = FastAPI(title="LedgerLens API", lifespan=lifespan)

# Middleware (outermost first)
app.add_middleware(AuthMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(CORSMiddleware, ...)

# Routers at /api/v1
# WebSocket at /ws/jobs
# Static files at /files/
```

### Domain Exception Hierarchy

```python
class AppError(Exception):              # Base — 500
class NotFoundError(AppError): ...      # → 404
class ConflictError(AppError): ...      # → 409
class ForbiddenError(AppError): ...     # → 403
class ValidationError(AppError): ...    # → 400
class AuthenticationError(AppError): ...# → 401

# Specific: ReceiptNotFoundError, ItemNotFoundError, StoreNotFoundError,
#           JobNotFoundError, HouseholdNotFoundError, DuplicateEmailError,
#           ActiveJobExistsError, InvalidCredentialsError, OCRProcessingError
```

A global `@app.exception_handler(AppError)` maps exception types to HTTP status codes.

### Repository Layer

Each repository encapsulates all SQLAlchemy queries for a single model. Repositories
never import from `routers/` or raise HTTP exceptions. They return `None` when entities
are not found; the service layer raises domain errors.

### Service Layer

Services contain business logic and orchestrate repositories. They accept `AsyncSession`
as a parameter (injected by the router via `Depends(get_db)`).

### Router Layer

Routers are thin — parse HTTP inputs, construct services, call service methods, and
serialise responses via Pydantic schemas. No business logic lives here.

### Middleware

- **`AuthMiddleware`**: Requires `session_id` cookie on all `/api/*` paths except `/api/v1/auth/*`, `/docs`, `/openapi.json`.
- **`SecurityMiddleware`**: Adds `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`.

---

## 6. Frontend Architecture

### Routing

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
    /stores/:id
    /review
    /settings
    /settings/household
    /join/:token
  <AdminRoute>     → redirects to /dashboard if user.role !== "admin"
    /admin/models
```

All page components are lazy-loaded via `React.lazy`.

### Navigation

**Desktop sidebar** (7 items): Dashboard, Receipts, Review, Products, Stores, Prices, Settings

**Mobile bottom tab bar** (5 items, `navItems.slice(0, 5)`): Dashboard, Receipts, Review, Products, Stores. Prices is accessible from ProductDetail via deep link (`/price-tracker?item={id}`). Settings has a gear icon in the mobile header bar.

**Review badge**: `useReviewCounts()` polls `GET /review/counts` every 60s (admin-only, gated by `user.role`). Combined pending count rendered as accent-colored pill on the Review nav icon in both sidebar and tab bar.

### PWA Configuration

`public/manifest.json` configures the installable PWA:

- `start_url: "/"` — on a fresh launch (app killed/closed, opened from home screen icon), the browser navigates to `/`, which the router immediately redirects to `/dashboard`.
- `display: "standalone"` — hides browser chrome for a native app feel.
- When resuming via the OS app switcher (app backgrounded, not killed), the browser restores the existing URL. `start_url` is not consulted in this case; the user resumes where they left off.

`index.html` includes the PWA meta tags required for iOS standalone mode (`apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`) and `viewport-fit=cover` for notch/safe-area support.

### Theme System (Dark / Light / Auto)

Four-layer architecture for theme switching:

1. **FOUC prevention** — Inline `<script>` in `index.html` reads `localStorage("ledgerlens-theme")` and applies `.dark` class to `<html>` before first paint. Also sets `<meta name="theme-color">` to match.
2. **`themeStore`** (Zustand) — Holds `preference` (`"light" | "dark" | "auto"`) persisted to localStorage, and `resolvedTheme` (`"light" | "dark"`) derived from preference + system media query.
3. **`useTheme` hook** — Manages DOM side-effects: toggles `.dark` on `document.documentElement`, updates `<meta theme-color>`, listens to `matchMedia("prefers-color-scheme: dark")` for auto mode.
4. **`ThemeToggle` component** — Segmented pill with `Light | Auto | Dark` labels, animated sliding indicator via Motion `layoutId`. Placed in desktop sidebar (bottom) and Settings page.

CSS tokens in `index.css` use `@theme` (light defaults) with `.dark` overrides on custom properties. The `html.theme-transition` class provides smooth 300ms transitions during user-initiated toggles only.

The PWA manifest uses a static dark `theme_color` / `background_color` (`#1a1816`) for less jarring splash screens. Runtime status bar color is dynamic via the `<meta theme-color>` tag.

### State Management

| Store | Purpose |
|---|---|
| **`appStore`** (Zustand) | Auth state, user, UI preferences, dashboard filters, upload count |
| **`themeStore`** (Zustand) | Theme preference (`light`/`dark`/`auto`), resolved theme, localStorage sync |
| **`toastStore`** (Zustand) | Toast notification queue |
| **TanStack Query** | All server data: receipts, items, stores, dashboard, jobs, suggestions, household, admin |

### API Client (`services/api.ts`)

A `fetch`-based wrapper that:
- Prepends `/api/v1` to paths
- Sets `credentials: "include"` for cookies
- On 401, redirects to `/login`
- Exposes `api.get`, `api.post`, `api.patch`, `api.delete`, `api.upload`

### WebSocket (`services/websocket.ts`)

`WSService` singleton:
- Connects to `ws(s)://<host>/ws/jobs?session_id=<token>`
- Exponential backoff reconnection (1s → 30s max)
- Parses incoming `ProcessingJob` state updates
- `useJobNotifications` hook subscribes and invalidates TanStack Query caches

### Pages (17)

| Route | Page | Description |
|---|---|---|
| `/login` | Login | Email + password |
| `/register` | Register | Email + display name + password |
| `/dashboard` | Dashboard | Summary cards, spending charts |
| `/receipts` | Receipts | Paginated list with status/store/date filters |
| `/receipts/add` | AddReceipt | Camera capture + file upload |
| `/receipts/manual` | ManualEntry | Manual receipt form |
| `/receipts/:id` | ReceiptDetail | Receipt viewer with editable line items |
| `/items` | Items | Paginated product list with search |
| `/items/:id` | ProductDetail | Edit product, aliases, image, merge, price history link |
| `/price-tracker` | PriceTracker | Price history chart + table (supports `?item=` deep link) |
| `/stores` | Stores | Store cards with receipt counts, links to detail |
| `/stores/:id` | StoreDetail | Edit store name/address/chain, manage aliases, merge, delete |
| `/review` | Review | Admin: product match suggestions + store duplicate suggestions, batch ops |
| `/settings` | Settings | Profile, links to household/admin |
| `/settings/household` | HouseholdSettings | Create/edit household, invite, members |
| `/admin/models` | AdminModels | LLM model config CRUD |
| `/join/:token` | JoinHousehold | Accept invite |

---

## 7. Single-Container Docker Design

### Multi-Stage Dockerfile

**Stage 1** — Build frontend:
```
FROM oven/bun:1
→ bun install --frozen-lockfile
→ bun run build
→ produces /app/frontend/dist
```

**Stage 2** — Final all-in-one image:
```
FROM python:3.13-slim-bookworm
→ Install: tesseract-ocr, nginx, redis-server, supervisor
→ Install Python deps via uv (locked)
→ Copy backend, frontend dist, infra configs
→ EXPOSE 80
→ ENTRYPOINT /entrypoint.sh
```

### Process Supervision (`supervisord.conf`)

| Program | Command | Priority |
|---|---|---|
| redis | `redis-server --save "" --appendonly no --bind 127.0.0.1` | 10 |
| backend | `uvicorn app.main:app --host 127.0.0.1 --port 8000` | 20 |
| worker | `celery -A app.worker worker --pool=prefork --concurrency=1` | 20 |
| nginx | `nginx -g "daemon off;"` | 30 |

### Nginx Reverse Proxy

```
location /                      → SPA (try_files → /index.html)
location /api/v1/receipts/batch → proxy, rate limit: api zone (burst 5)
location /api/v1/auth/          → proxy, rate limit: auth zone (5 r/s, burst 10)
location /api/                  → proxy, rate limit: api zone (30 r/s, burst 60)
location /ws/                   → WebSocket upgrade, 3600s timeouts
location /files/                → proxy to 127.0.0.1:8000
```

**Security headers** (all responses, including static files):
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `server_tokens off` (hides nginx version)
- Note: HSTS is intentionally omitted — add it at the upstream HTTPS terminator

**Rate limiting zones** (defined at `http` context via `conf.d/` include):
- `api`: 30 r/s per IP, 429 on excess — covers all `/api/` traffic
- `auth`: 5 r/s per IP, 429 on excess — stricter zone for `/api/v1/auth/`
- `perip` connection limit: 50 concurrent connections per IP (slowloris protection)

### Entrypoint

1. Create data directory
2. Run `alembic upgrade head`
3. Start `supervisord`

### Docker Compose

Single `ledgerlens` service. Port 8080 (configurable via `LEDGERLENS_PORT`).
Volume mount: `${LEDGERLENS_DATA_DIR:-./data}:/app/data`.

---

## 8. API Contract

All endpoints under `/api/v1`. Auth via `session_id` cookie (httpOnly, sameSite=lax, 30-day max-age).

### Pagination Envelope

```json
{ "items": [...], "total": 42, "page": 1, "per_page": 20 }
```

### Error Response

```json
{ "detail": "Human-readable error message" }
```

### Endpoints

| Group | Method | Path | Description |
|---|---|---|---|
| **Auth** | POST | `/auth/register` | Register new user |
| | POST | `/auth/login` | Login |
| | POST | `/auth/logout` | Logout |
| | GET | `/auth/me` | Current user info |
| **Receipts** | POST | `/receipts` | Upload single receipt (multipart) |
| | POST | `/receipts/batch` | Upload multiple receipts (multipart, max 20) |
| | POST | `/receipts/manual` | Create manual receipt |
| | GET | `/receipts` | List with filters + pagination |
| | GET | `/receipts/:id` | Receipt detail with line items |
| | PATCH | `/receipts/:id` | Update receipt |
| | DELETE | `/receipts/:id` | Delete receipt |
| **Items** | GET | `/items` | List canonical items + pagination |
| | GET | `/items/:id` | Product detail |
| | PATCH | `/items/:id` | Update product |
| | POST | `/items/:id/merge` | Merge duplicate items into this one |
| | GET | `/items/:id/price-history` | Historical pricing |
| | GET | `/items/:id/images` | Product images |
| **Line Items** | PATCH | `/line-items/:id` | Edit/correct line item |
| | DELETE | `/line-items/:id` | Delete line item |
| **Stores** | GET | `/stores` | List stores (search, chain filter) |
| | GET | `/stores/:id` | Store detail with aliases |
| | PATCH | `/stores/:id` | Update store |
| | DELETE | `/stores/:id` | Delete store (blocked if has receipts) |
| | POST | `/stores/:id/merge` | Merge duplicates into this store |
| | GET | `/stores/:id/aliases` | List aliases |
| | POST | `/stores/:id/aliases` | Add manual alias |
| | DELETE | `/stores/:id/aliases/:aid` | Remove alias |
| | GET | `/stores/merge-suggestions` | Pending duplicate suggestions |
| | POST | `/stores/merge-suggestions/:id/accept` | Accept + execute merge |
| | POST | `/stores/merge-suggestions/:id/reject` | Dismiss suggestion |
| | POST | `/stores/scan-duplicates` | Trigger on-demand duplicate scan |
| **Suggestions** | GET | `/suggestions` | Match suggestions (enriched with line item name) |
| | POST | `/suggestions/:id/accept` | Accept + link |
| | POST | `/suggestions/:id/reject` | Reject suggestion |
| **Review** | GET | `/review/counts` | Combined pending counts (admin) |
| **Dashboard** | GET | `/dashboard` | Summary (totals, trends, top items) |
| | GET | `/dashboard/stats` | Detailed statistics |
| **Household** | POST | `/household` | Create household |
| | GET | `/household` | Current household |
| | PATCH | `/household` | Update household |
| | GET | `/household/members` | List members |
| | GET | `/household/invite-token` | Generate invite token |
| | POST | `/household/join` | Join with token |
| | DELETE | `/household/members/:id` | Remove member |
| **Jobs** | GET | `/jobs` | List processing jobs |
| | GET | `/jobs/:id` | Job detail |
| | DELETE | `/jobs/:id` | Cancel job |
| **Admin** | GET | `/admin/models` | List LLM configs |
| | POST | `/admin/models` | Create config |
| | PATCH | `/admin/models/:id` | Update config |
| | DELETE | `/admin/models/:id` | Delete config |
| **WebSocket** | WS | `/ws/jobs` | Real-time job status push |

---

## 9. Background Processing

### Celery Configuration

- Broker: Redis (embedded in container)
- Serializer: JSON
- Acks: late (task_acks_late=True)
- Prefetch: 1
- Soft time limit: 300s (configurable)
- Hard time limit: 360s (configurable)

### Worker Lifecycle

**On `worker_process_init`**: Create dedicated async engine + session factory (NullPool + SQLite WAL pragmas).

**On `worker_ready`**: Verify Tesseract binary; recover orphaned jobs (stale running → failed, stale queued → redispatch).

### Task: `process_receipt_task(job_id)`

1. Set job `status=processing`, `stage=ocr`
2. Run Tesseract OCR (image or multi-page PDF) — always runs, initially populates `raw_ocr_text`
3. Store `raw_ocr_text` and `ocr_confidence` on receipt
4. Set `stage=extraction`, run 3-tier extraction cascade:
   - **Tier 1 (Vision)**: if `ModelConfig.supports_vision`, send receipt image(s) directly to vision LLM → `extraction_source="vision"`. If the model returns `raw_text`, it overwrites `raw_ocr_text` with the vision-read text (what actually drove the result)
   - **Tier 2 (Text LLM)**: if vision skipped or failed and OCR has text, send OCR text to LLM → `extraction_source="llm"`
   - **Tier 3 (Heuristic)**: if text LLM fails or OCR is empty, apply regex extraction → `extraction_source="heuristic"`
   - If all tiers fail → `status=failed`
5. Normalise store name, resolve via StoreMatchingService (exact → alias → fuzzy → create), seed alias from raw OCR name
6. For each line item: fuzzy match → auto-link / suggest / create new CanonicalItem
7. Set receipt `status=completed`, job `status=completed`
8. Publish status to Redis pub/sub → WebSocket push
9. On error: set `status=failed` with error message

### Batch Uploads

The `POST /receipts/batch` endpoint accepts up to 20 files in a single multipart request.
Each file is validated (magic bytes, per-file 10 MB limit, aggregate 50 MB limit), then
processed through the existing `upload()` → `enqueue_receipt()` path. This creates N
independent `ProcessingJob` records in the Celery queue. With `concurrency=1`, the worker
processes them sequentially — no configuration changes needed. Partial success is supported:
the response includes both successful receipts and per-file errors.

### Retroactive Matching

Async background loop on the FastAPI process (via `asyncio.create_task` in lifespan).
Every 300s (configurable), scans unlinked `LineItem` rows, runs fuzzy matching, auto-links
or creates suggestions. Batch size: 200 (configurable).

---

## 10. OCR & LLM Pipeline

### OCR Service

```
Image → grayscale → upscale if < 1500px → binarize (threshold 150)
      → pytesseract (OEM 3, PSM 6, DPI 300) → text + confidence

PDF   → PyMuPDF rasterize each page at 300 DPI → OCR per page
      → concatenate text → average confidence
```

OCR **always runs** regardless of extraction path. Its output is stored in `raw_ocr_text` initially, but if the vision path succeeds and the model returns `raw_text`, that field is overwritten with the vision-read text — so `raw_ocr_text` always reflects the text that actually drove the extraction result. Both image and PDF handlers run via `asyncio.to_thread` to avoid blocking the event loop.

### Extraction Cascade

`extraction.py` runs a 3-tier cascade, stopping at the first tier that returns a usable result (i.e. a `total_cents` value):

```
Tier 1 — Vision LLM   (if ModelConfig.supports_vision)
          image(s) → vision LLM → JSON          extraction_source = "vision"
          ↓ (fail / skipped)
Tier 2 — Text LLM     (if OCR produced text)
          raw_ocr_text → LLM → JSON             extraction_source = "llm"
          ↓ (fail / skipped)
Tier 3 — Heuristic    (if OCR produced text)
          raw_ocr_text → regex → dict            extraction_source = "heuristic"
          ↓ (fail)
          receipt.status = "failed"
```

### LLM Service (`llm.py`)

Prompts are **Jinja2 templates** stored in `app/prompts/` and rendered at module load time
(system prompt) or per-request (user prompt). This separates prompt content from Python code,
making it easy to iterate on extraction instructions without touching service logic.

Two extraction functions expose text and vision paths — both return the same JSON schema and both return `{}` on failure so the caller's cascade logic is uniform:

- **`extract_receipt_data(raw_text, ...)`** — text path
  - Templates: `system.md.j2` (OCR-aware instructions, rendered once at import), `user.md.j2` (per-request with `raw_text` + known entities)
  - User message content: plain string

- **`extract_receipt_data_vision(file_path, ...)`** — vision path
  - Templates: `system_vision.md.j2` (image-aware instructions, no OCR error warnings), `user_vision.md.j2` (per-request with instruction + known entities, no `raw_text`)
  - User message content: multipart list `[{"type": "text", ...}, {"type": "image_url", "image_url": {"url": "data:image/...;base64,..."}}, ...]`
  - Image encoding handled by `image_utils.py`: resizes to max 2048px longest side, encodes to base64 data URLs; PDFs rasterized per-page via PyMuPDF at 200 DPI

The vision prompt output schema includes one additional top-level field not present in the text prompt:
- **`raw_text`**: the full receipt text as read from the image, with `\n` line breaks — stored in `receipt.raw_ocr_text` on success, overwriting Tesseract output

Both prompts otherwise share identical **output schema** covering:
- **Store fields**: `raw_store_name` (verbatim), `store_name` (cleaned), `store_address`, `store_chain`
- **Receipt-level**: `transaction_date`, `currency`, `subtotal_cents`, `tax_cents`, `total_cents`, `discount_total_cents`, `payment_method`, `is_refund_receipt`, `tax_breakdown[]`
- **Line items**: `raw_name`, `name` (expanded/cleaned), `quantity`, `unit_price_cents`, `total_price_cents`, `discount_cents`, `is_refund`, `tax_code`, `weight_qty`

**Shared behaviour (both paths)**:
- **Known-entity injection**: known store names (up to 50) and product names (up to 100) injected into user prompt so LLM can match garbled text against existing entities
- **JSON mode**: attempts `response_format={"type": "json_object"}` first; retries without if unsupported
- **Client**: OpenAI SDK pointed at configurable `base_url` (Ollama, vLLM, OpenAI, etc.)
- **Returns `{}`** on any failure → caller advances to next tier

### ModelConfig — Vision Flag

`ModelConfig.supports_vision` (Boolean, default `false`) controls whether the vision path is attempted for receipts processed by that model config. Set via the admin UI; the model card shows a "Vision" badge when enabled. Admins should only enable this for models that genuinely support multipart image content (e.g. `llama3.2-vision`, `llava`, `gpt-4o`). If the model doesn't support vision but the flag is set, the API call will fail and tier 2 takes over.

### Heuristic Service

Regex-based fallback when LLM fails:
- Total: `TOTAL`, `AMOUNT DUE`, `BALANCE`, `GRAND TOTAL`
- Tax: `TAX`, `HST`, `GST`, `PST`, `VAT`
- Date: `YYYY-MM-DD` or `MM/DD/YYYY`
- Store name: first non-decorative line
- Line items: `<name> <price>` pattern (max 50)

### Fuzzy Matching

| Score Range | Action |
|---|---|
| >= 85 (configurable) | **Auto-link**: set `canonical_item_id`, add as alias |
| 60–84 (configurable) | **Suggest**: create `MatchSuggestion(status=pending)` |
| < 60 | **No match**: create new `CanonicalItem` |

Scoring: `max(token_sort_ratio, partial_ratio)` via RapidFuzz.

**Auto-reject on rename**: When a user renames a canonical item (via `PATCH /items/:id`), `ItemService.update()` calls `MatchSuggestionRepository.reject_stale_for_canonical()`. This bulk-rejects any pending `MatchSuggestion` rows whose line item is already linked to that canonical item but the suggestion points to a different canonical item — preventing stale suggestions from silently overwriting user corrections.

### Normalisation

**Store names**: `normalize_store_name()` returns `(normalized_name, detected_chain)`. Strips store/location numbers (regex `#?\d{3,}$`), common suffixes ("supercenter", "supercentre", "superstore", "express"), and matches against 40+ chain prefix patterns. Known chains return canonical name + chain; unknown stores → `title()` case + `None`.

**Item names**: Collapse whitespace, strip trailing junk (weights, barcodes, SKUs), `title()` case.

### Store Matching

`StoreMatchingService` resolves OCR store names through a 5-step cascade:

| Step | Condition | Action |
|---|---|---|
| 1 | Exact name match | Link to existing store |
| 2 | Exact alias match | Link via `StoreAlias` lookup |
| 3 | Fuzzy score >= 88 | Auto-link + create alias |
| 4 | Fuzzy score >= 65 | Create `StoreMergeSuggestion` for review |
| 5 | No match | Create new `Store` |

Address-aware: same chain + different addresses → separate stores (shared chain). Same chain + one address missing → suggestion for review. Alias seeding: when the LLM cleans an OCR name, the raw version is immediately added as a `StoreAlias(source="ocr")`.

---

## 11. Authentication & Authorization

### Session-Based Auth

1. **Register**: bcrypt hash → create User (first user = admin) → create UserSession (30-day expiry) → set `session_id` cookie
2. **Login**: verify password → create session → set cookie
3. **Logout**: delete session row → delete cookie
4. **`GET /auth/me`**: validate session → return user

### SECRET_KEY Validation

The app refuses to start if `SECRET_KEY` is a known insecure default (`"change-me"`, `"change-me-to-a-random-string"`, or empty). A warning is logged if the key is shorter than 32 characters. This is enforced via a pydantic `model_validator` on `Settings`.

### Cookie Security

The `COOKIE_SECURE` setting controls the `secure` flag on session cookies:
- `"auto"` (default): secure when `X-Forwarded-Proto: https` or direct HTTPS
- `"true"`: always set secure flag
- `"false"`: never set secure flag (for HTTP-only setups behind a reverse proxy)

### Rate Limiting

Login and register endpoints are protected by a Redis-backed sliding window rate limiter (`core/rate_limit.py`). Uses Redis sorted sets via the existing Celery broker connection. **Fail-open**: if Redis is unavailable, requests are allowed through with a warning logged.

| Endpoint | Default Limit | Window | Config |
|----------|---------------|--------|--------|
| `/auth/login` | 5 attempts/IP | 15 min | `RATE_LIMIT_LOGIN_MAX`, `RATE_LIMIT_LOGIN_WINDOW_SECONDS` |
| `/auth/register` | 3 attempts/IP | 15 min | `RATE_LIMIT_REGISTER_MAX`, `RATE_LIMIT_REGISTER_WINDOW_SECONDS` |

Rate limit exceeded returns HTTP 429 with `Retry-After` header.

### Middleware Gate

`AuthMiddleware` requires `session_id` on all `/api/*` except `/api/v1/auth/*`, `/docs`, `/openapi.json`.

### Role-Based Access

- **Admin**: Required for `/admin/*` endpoints
- **Owner**: Receipt update/delete requires ownership; household management requires owner
- **Line items**: `PATCH /line-items/{id}` joins through the parent receipt and applies `receipt_visibility()` — a user can only edit line items on receipts they can see. Returns 404 (not 403) on access denial to prevent ID enumeration.

### Household Invites

Signed tokens via `URLSafeTimedSerializer`, salt `"household-invite"`, max age 7 days.

---

## 12. Real-Time Communication

### WebSocket Endpoint

`WS /ws/jobs?session_id=<token>`

1. Validate session token
2. Register connection keyed by `user_id`
3. Loop: receive messages (ping/pong); on disconnect, unregister

### Redis Pub/Sub Bridge

The Celery task publishes job status changes to Redis channel `user:<user_id>:jobs`.
The FastAPI process subscribes to channels for connected users and forwards to WebSocket clients.
This decouples the worker from the WebSocket process.

### Client Handling

The frontend `WSService` parses incoming `ProcessingJob` objects and emits to subscribers.
The `useJobNotifications` hook invalidates `["jobs"]` and `["receipts"]` query caches on updates.

---

## 13. File Storage

### Directory Layout

```
data/
├── receipts/<user_id>/<receipt_id>/
│   ├── original.<ext>      # jpg, png, heic, pdf
│   └── thumbnail.png       # first-page thumbnail
├── thumbnails/              # additional thumbnails
├── products/<item_id>/
│   └── image.webp           # 512x512, 85% quality
└── ledgerlens.db            # SQLite database
```

### Upload Limits

- Receipt files: JPEG, PNG, HEIC, PDF
- Product images: JPEG, PNG, WebP; max 5 MB; auto-resized to 512x512 WebP

### Serving

Files served via FastAPI `StaticFiles` at `/files/`, reverse-proxied by Nginx.
Path safety: `storage.get_receipt_path()` validates paths fall under `DATA_DIR`.

---

## 14. Database Migrations

### Alembic Configuration

- Async SQLAlchemy driver
- `render_as_batch=True` for SQLite `ALTER TABLE` compatibility
- All models imported for autogenerate metadata
- Runs via `asyncio.run`

### Migration History

1. `feded377c21d` — Initial schema (all 10 tables)
2. `36e5776eb341` — Drop `is_default` from `model_configs`

### SQLite Pragmas

Applied at engine connect time:

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;
```

---

## 15. Testing

### Backend

| Layer | Tool | Approach |
|---|---|---|
| Unit (services) | pytest + pytest-asyncio | Mock repositories; test business logic |
| Unit (repositories) | pytest + in-memory SQLite | Real DB queries |
| Integration | pytest + httpx | Full request cycle with test DB |
| Task | pytest + Celery eager mode | Synchronous execution |

### Frontend

| Layer | Tool | Approach |
|---|---|---|
| Component | Vitest + Testing Library | Render + assert DOM |
| Hook | Vitest + renderHook | TanStack Query hooks |
| Integration | Vitest + MSW | Mock API, page-level flows |

---

## 16. CI/CD

### GitHub Actions (`ghcr-publish.yml`)

- Triggers on semver tags (`v*`)
- Builds single Docker image via multi-stage Dockerfile
- Pushes to `ghcr.io/<owner>/ledgerlens2`
- Generates changelog from git logs
- Tags: semver (`1.0.0`, `1.0`), branch ref, SHA

---

## 17. Configuration & Environment

### Settings (`app/core/config.py`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/ledgerlens.db` | DB connection string |
| `DATA_DIR` | `./data` | File storage root |
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `llama3.2` | Model name |
| `LLM_API_KEY` | `""` | API key (optional for Ollama) |
| `LLM_TIMEOUT_SECONDS` | `30` | LLM request timeout |
| `LLM_MAX_RETRIES` | `1` | LLM retry count |
| `SECRET_KEY` | *(required)* | Session signing & encryption key |
| `COOKIE_SECURE` | `auto` | Cookie secure flag: `auto`, `true`, `false` |
| `RATE_LIMIT_LOGIN_MAX` | `5` | Max login attempts per IP per window |
| `RATE_LIMIT_LOGIN_WINDOW_SECONDS` | `900` | Login rate limit window |
| `RATE_LIMIT_REGISTER_MAX` | `3` | Max register attempts per IP per window |
| `RATE_LIMIT_REGISTER_WINDOW_SECONDS` | `900` | Register rate limit window |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis broker URL |
| `TASK_SOFT_TIME_LIMIT` | `300` | Celery soft timeout (seconds) |
| `TASK_HARD_TIME_LIMIT` | `360` | Celery hard timeout (seconds) |
| `GOOGLE_CSE_API_KEY` | `""` | Google Custom Search (optional) |
| `GOOGLE_CSE_CX` | `""` | Google CSE engine ID (optional) |
| `FUZZY_AUTO_LINK_THRESHOLD` | `85` | Auto-link score threshold (items) |
| `FUZZY_SUGGEST_THRESHOLD` | `60` | Suggestion score threshold (items) |
| `STORE_FUZZY_AUTO_LINK_THRESHOLD` | `88` | Auto-link score threshold (stores) |
| `STORE_FUZZY_SUGGEST_THRESHOLD` | `65` | Suggestion score threshold (stores) |
| `RETROACTIVE_BATCH_SIZE` | `200` | Items per retroactive scan |
| `RETROACTIVE_INTERVAL_SECONDS` | `300` | Retroactive scan frequency |
| `TESSERACT_LANG` | `eng` | OCR language |
| `TESSERACT_PSM` | `6` | Page segmentation mode |
| `TESSERACT_DPI` | `300` | OCR DPI |

### Docker Environment

Inside the container, Redis is on `127.0.0.1:6379`. For LLM, point `LLM_BASE_URL` to an
external Ollama instance (e.g. `http://host.docker.internal:11434/v1`).
