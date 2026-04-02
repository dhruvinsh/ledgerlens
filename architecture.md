# LedgerLens 2 Architecture

## Overview

LedgerLens 2 is a self-hosted receipt tracking PWA that extracts structured data from receipt images/PDFs using OCR and LLM-powered extraction. It runs as a single Docker container with Nginx, FastAPI, Celery, and Redis managed by Supervisor.

---

## Project Structure

```
ledgerlens2/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app + lifespan
│   │   ├── worker.py          # Celery configuration
│   │   ├── core/              # Config, DB, auth, exceptions
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── repositories/      # Data access layer
│   │   ├── services/          # Business logic layer
│   │   ├── routers/           # API route handlers
│   │   ├── middleware/        # Auth & security middleware
│   │   └── tasks/             # Celery async tasks
│   ├── alembic/               # Database migrations
│   ├── tests/
│   └── pyproject.toml         # Python deps (uv)
├── frontend/                  # React + TypeScript SPA
│   ├── src/
│   │   ├── pages/             # Page components (lazy-loaded)
│   │   ├── components/        # Reusable components (Shadcn/ui)
│   │   ├── hooks/             # React Query hooks
│   │   ├── services/          # API client & WebSocket
│   │   ├── stores/            # Zustand state management
│   │   └── lib/               # Types & utilities
│   └── package.json           # NPM deps (Bun)
├── infra/                     # Docker & process management
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── supervisord.conf
│   └── nginx.conf
└── docker-compose.yml
```

---

## Backend

### Stack

- **Framework**: FastAPI 0.115+, Uvicorn
- **Language**: Python 3.13+, fully async
- **ORM**: SQLAlchemy 2.0 (async) + aiosqlite
- **Database**: SQLite (WAL mode) with optional PostgreSQL
- **Migrations**: Alembic (always `--autogenerate`, never hand-written)
- **Task Queue**: Celery with Redis broker
- **OCR**: Tesseract (via pytesseract)
- **LLM**: OpenAI SDK (compatible with Ollama, vLLM, OpenAI)
- **Fuzzy Matching**: RapidFuzz

### Layered Architecture

```
Routers (API) → Services (business logic) → Repositories (data access) → Models (ORM)
```

- **Routers** (`app/routers/`): FastAPI `APIRouter` instances, one per resource. Handle HTTP concerns only.
- **Services** (`app/services/`): Business logic, coordination across repos and external services.
- **Repositories** (`app/repositories/`): SQLAlchemy queries, data access encapsulation.
- **Models** (`app/models/`): Declarative ORM models inheriting `BaseMixin` (id, created_at, updated_at).

### Data Models

#### User
- `id`, `email` (unique), `password_hash` (bcrypt), `role` (admin|member)
- `household_id` FK (nullable), `is_active`
- First registered user becomes admin

#### Household
- `id`, `name`, `owner_id` FK, `sharing_mode` (shared|private)
- Members join via time-limited invite tokens (7 days)

#### Receipt
- `id`, `user_id` FK (CASCADE), `household_id` FK (SET NULL), `store_id` FK (SET NULL)
- `transaction_date`, `currency` (default "CAD"), `subtotal`/`tax`/`total` (cents)
- `discount` (cents, planned), `payment_method` (cash|credit|debit|other, planned), `is_refund` (bool, planned)
- `source` (camera|upload|manual), `status` (pending|processing|processed|reviewed|failed|deleted)
- `file_path`, `thumbnail_path`, `page_count`
- `raw_ocr_text`, `ocr_confidence`, `extraction_source` (llm|heuristic)
- `duplicate_of` FK (self-reference), `notes`
- Indexes: `(user_id, transaction_date)`, `(household_id, transaction_date)`, `(store_id)`

#### LineItem
- `id`, `receipt_id` FK (CASCADE), `canonical_item_id` FK (SET NULL)
- `name` (LLM-cleaned), `raw_name` (verbatim OCR text, planned), `quantity`, `unit_price`, `total_price` (cents)
- `discount` (cents, planned), `is_refund` (bool, planned), `tax_code` (H/G/P/F, planned), `weight_qty` (e.g. "1.230 kg", planned)
- `confidence`, `position`, `is_corrected`

#### CanonicalItem
- `id`, `name` (unique, indexed), `category`, `aliases` (JSON array)
- `product_url`, `image_path`, `image_source`, `image_fetch_status`

#### MatchSuggestion
- `id`, `line_item_id` FK (CASCADE), `canonical_item_id` FK (CASCADE)
- `confidence`, `status` (pending|accepted|rejected)
- Unique: `(line_item_id, canonical_item_id)`

#### Store
- `id`, `name` (indexed), `address`, `chain`
- `latitude`, `longitude`, `created_by` FK (RESTRICT), `is_verified`
- `merged_into_id` FK (SET NULL) — soft-redirect after merge - Relationships: `receipts`, `aliases` 
#### StoreAlias - `id`, `store_id` FK (CASCADE), `alias_name`, `alias_name_lower` (unique, indexed)
- `source` (auto|manual|ocr)
- Maps OCR name variations to canonical stores

#### StoreMergeSuggestion - `id`, `store_a_id` FK, `store_b_id` FK, `confidence`, `status`
- Pairs of potentially-duplicate stores for admin review
- Unique: `(store_a_id, store_b_id)`

#### ProcessingJob
- `id`, `receipt_id` FK (CASCADE), `model_config_id` FK (SET NULL)
- `status` (queued|running|completed|failed), `stage` (ocr|extraction|matching)
- `celery_task_id`, `error_message`, `started_at`, `completed_at`

#### ModelConfig
- `id`, `name`, `provider_type` (openai|ollama), `base_url`, `model_name`
- `api_key_encrypted`, `is_active`, `timeout_seconds`, `max_retries`
- `last_health_check`, `health_status`

#### UserSession
- `id`, `user_id` FK, `token_hash`, `ip_address`, `user_agent`, `expires_at`

### API Endpoints

All under `/api/v1/` unless noted. Auth via `session_id` httponly cookie.

| Router | Key Endpoints |
|--------|---------------|
| `auth` | POST register, login, logout; GET /me |
| `receipts` | POST upload, manual; GET list, detail; PATCH update; POST reprocess; DELETE |
| `items` | CRUD canonical items |
| `stores` | GET list (search, pagination), GET detail, PATCH update (admin) |
| `suggestions` | GET list; POST accept/reject match suggestions |
| `dashboard` | GET spending analytics |
| `household` | CRUD household, invite/join |
| `admin` | CRUD model configs, health checks |
| `jobs` | GET list/detail, POST cancel |
| `line_items` | PATCH update |
| `ws` | WebSocket /ws/jobs (real-time job updates) |

### Receipt Processing Pipeline

```
Upload → Save file → Create Receipt (pending) → Enqueue ProcessingJob
                                                        ↓
                                              Celery Worker picks up
                                                        ↓
                                              OCR (Tesseract)
                                                        ↓
                                              Load known stores + products from DB
                                                        ↓
                                              LLM Extraction (with known context)
                                                        ↓
                                              Fallback: Heuristic (regex)
                                                        ↓
                                              Store Normalization & Matching
                                                        ↓
                                              Line Item Creation (with discount, refund, tax_code, weight)
                                                        ↓
                                              Fuzzy Match → CanonicalItems
                                                        ↓
                                              Receipt status → "processed"
                                                        ↓
                                              WebSocket notification
```

### LLM-Enhanced Extraction 
The LLM receives three inputs:
1. **Raw OCR text** — the receipt content
2. **Known store names** (up to 50) — enables OCR error correction at extraction time
3. **Known product names** (up to 100) — enables matching garbled item names to existing canonical items

The LLM extracts richer data than the current minimal schema:
- **Per-item**: raw_name (verbatim OCR) + name (cleaned, expanded abbreviations, title case), quantity, unit/total price, discount_cents, is_refund, tax_code (H/G/P/F), weight_qty
- **Receipt-level**: raw_store_name + store_name, store_chain, store_address, subtotal/tax/total, discount_total, tax_breakdown (per tax type), payment_method, is_refund_receipt
- **Item intelligence**: Combines multi-line items, associates discount/coupon lines with their items, marks refund items, parses weighted produce

### Alias Seeding from Extraction

Both stores and products build aliases immediately during extraction:
- When LLM cleans `raw_name` → `name` for an item, the `raw_name` is added as a CanonicalItem alias (if it differs)
- When LLM cleans `raw_store_name` → `store_name`, the raw version becomes a StoreAlias with `source="ocr"`
- On subsequent receipts, alias lookups match instantly — no LLM or fuzzy matching needed for previously-seen OCR variations
- This creates a self-improving system: each receipt processed makes future matching faster and more accurate

### Product Matching (MatchingService)

Resolution order for line item names:
1. Exact canonical name match → link
2. Exact alias match → link
3. Fuzzy >= auto-link threshold (85) → link + add alias
4. Fuzzy >= suggest threshold (60) → create MatchSuggestion for review
5. No match → create new CanonicalItem

Uses `rapidfuzz.fuzz.token_sort_ratio` + `partial_ratio`, max score wins.

### Store Matching (StoreMatchingService)

Resolution order for OCR-extracted store names:
1. Exact canonical name match (case-insensitive)
2. Exact alias match (via StoreAlias table)
3. Fuzzy >= auto-link threshold (88) + address check → link + add alias
4. Fuzzy >= suggest threshold (65) → create StoreMergeSuggestion
5. No match → create new Store

**Address-aware matching**: Same chain + different address = separate stores (shared `chain` value). Same chain + matching/missing address = same store.

**LLM-enhanced extraction**: The LLM prompt receives existing store names as context, enabling it to fix OCR errors at the source (e.g., "WAL-MART SUPERCNTR" → "Walmart"). The LLM also returns `store_chain` for chain detection.

**Two-level filtering**:
- Chain filter: `?chain=Walmart` → all Walmart locations
- Store filter: `?store_id=abc` → single location

### Normalization

- `normalize_store_name(name)` → `(normalized, chain|None)`: strips store numbers, suffixes; matches against known chains dict
- `normalize_item_name(name)` → lowered, whitespace-collapsed

### Real-time Updates

- WebSocket at `/ws/jobs?session_id={token}`
- Redis pub/sub: Celery worker publishes → backend subscriber → WebSocket to client
- Messages: `{"type": "job_update", "job_id": "...", "status": "...", "stage": "..."}`

### Retroactive Matching

Background loop (every 300s, batch of 200): re-matches unmatched LineItems against newly added CanonicalItems.

### Authentication

- Cookie-based sessions (`session_id`, httponly, samesite=lax)
- Password hashing: bcrypt
- Token signing: itsdangerous URLSafeTimedSerializer (30-day max age)
- Invite tokens: 7-day expiry, household-scoped
- AuthMiddleware on all `/api/*` except `/api/v1/auth/*`

### Middleware Order (outermost first)

1. AuthMiddleware — session validation
2. SecurityMiddleware — security headers
3. CORSMiddleware — CORS (localhost:5173 in dev)

---

## Frontend

### Stack

- **Framework**: React 19, TypeScript 5.9
- **Build**: Vite 8, Bun
- **Styling**: Tailwind CSS 4, Lucide icons
- **State**: Zustand 5 (UI state) + React Query 5 (server state)
- **Routing**: React Router 7 (lazy-loaded pages)
- **Charts**: Recharts
- **Animation**: Motion (Framer Motion successor)
- **Components**: Shadcn/ui pattern

### Routes

```
/                     → redirect to /dashboard
/login, /register     → public
/dashboard            → spending analytics
/receipts             → receipt list + filters
/receipts/add         → upload receipt
/receipts/manual      → manual entry form
/receipts/:id         → receipt detail + line items
/items                → canonical items list
/items/:id            → product detail + price history
/price-tracker        → price trends
/stores               → store list (chain grouping, merge UI)
/stores/:id           → store detail /stores/merge-suggestions → duplicate review /settings             → user preferences
/settings/household   → household management
/admin/models         → LLM model config (admin)
/join/:token          → household invite acceptance
```

### State Management

- **Zustand** (`stores/appStore.ts`): user, auth state, dashboard filters (dateFrom, dateTo, storeId, chain, category)
- **React Query** (`hooks/`): server state caching, mutations with invalidation
- **WebSocket** (`services/websocket.ts`): auto-reconnect, exponential backoff, job notifications

### API Client

Fetch-based (`services/api.ts`): GET/POST/PATCH/DELETE/upload methods, credentials included, 401 → redirect to login.

---

## Infrastructure

### Docker (Single Container)

Multi-stage build → `python:3.13-slim-bookworm` with Tesseract, Nginx, Redis, Supervisor.

**Supervisor manages 4 processes:**
1. Redis (localhost:6379, in-memory only)
2. Backend (Uvicorn, localhost:8000)
3. Celery Worker (prefork, concurrency=1)
4. Nginx (port 80, reverse proxy + SPA)

### Nginx

- `/` → SPA static files (try_files → /index.html)
- `/api/*` → proxy to backend:8000
- `/ws/*` → WebSocket upgrade to backend:8000
- `/files/*` → proxy to backend:8000

### Container Startup (entrypoint.sh)

1. Create `appuser` with configurable UID/GID (`PUID`/`PGID` env vars)
2. Apply umask
3. Ensure data directory ownership
4. Run `alembic upgrade head`
5. Start Supervisor

### Data Persistence

```
./data/
├── ledgerlens.db              # SQLite database
├── receipts/{user_id}/{receipt_id}/
│   ├── original.{ext}         # Uploaded file
│   └── thumbnail.jpg
└── products/{item_id}/
    └── image.jpg
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/ledgerlens.db` | Database |
| `SECRET_KEY` | `change-me` | Session signing |
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | LLM endpoint (Ollama) |
| `LLM_MODEL` | `llama3.2` | Model name |
| `LLM_API_KEY` | — | API key (optional) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Task queue broker |
| `FUZZY_AUTO_LINK_THRESHOLD` | `85` | Product auto-link score |
| `FUZZY_SUGGEST_THRESHOLD` | `60` | Product suggestion score |
| `STORE_FUZZY_AUTO_LINK_THRESHOLD` | `88` | Store auto-link score (planned) |
| `STORE_FUZZY_SUGGEST_THRESHOLD` | `65` | Store suggestion score (planned) |
| `TESSERACT_LANG` | `eng` | OCR language |
| `TESSERACT_PSM` | `6` | Tesseract page segmentation |
| `TESSERACT_DPI` | `300` | OCR resolution |
| `PUID` / `PGID` | `1000` | Container user/group IDs |
