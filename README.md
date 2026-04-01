# LedgerLens

> [!CAUTION]
> This project is a personal experiment, designed and built entirely around my own workflow and interests **fully** vibe-driven! If you want to contribute, I would love to have your help, as long as your changes don’t interfere with my own experience. Requests that do not disrupt my process are always welcome and appreciated.


Self-hosted, privacy-first receipt tracking. Upload receipts, extract data with OCR + LLM, track prices, and manage household spending — all from a single Docker container.

## What It Does

- **Scan receipts** — Upload photos or PDFs; Tesseract OCR + an LLM extract store, items, prices, and totals automatically
- **Track products** — Fuzzy matching links receipt line items to canonical products, building a price history over time
- **Spending analytics** — Dashboard with category breakdowns, store frequency, and monthly trends
- **Household sharing** — Invite family members to share receipts and see combined spending
- **Manual entry** — Add receipts by hand when a scan isn't practical
- **Works with any LLM** — Ollama, vLLM, OpenAI, or any OpenAI-compatible API

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- An OpenAI-compatible LLM endpoint (e.g., [Ollama](https://ollama.com/) running locally)

### Run with Docker Compose

```bash
git clone https://github.com/your-org/ledgerlens2.git
cd ledgerlens2
cp .env.example .env
# Edit .env — at minimum, set SECRET_KEY to a random string
docker compose up -d
```

Open [http://localhost:8080](http://localhost:8080). Register the first user (automatically becomes admin).

### Run with Docker directly

```bash
docker build -t ledgerlens .
docker run -d \
  -p 8080:80 \
  -v ./data:/app/data \
  -e SECRET_KEY=your-random-secret-here \
  -e LLM_BASE_URL=http://host.docker.internal:11434/v1 \
  -e LLM_MODEL=llama3.2 \
  --name ledgerlens \
  ledgerlens
```

### Using Ollama

If Ollama is running on the host machine:

```bash
# Pull a model
ollama pull llama3.2

# LedgerLens will connect via LLM_BASE_URL=http://host.docker.internal:11434/v1
```

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me` | **Change this.** Session signing key |
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | LLM endpoint (Ollama, OpenAI, etc.) |
| `LLM_MODEL` | `llama3.2` | Model name for receipt extraction |
| `LLM_API_KEY` | — | API key (not needed for Ollama) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/ledgerlens.db` | Database connection |
| `FUZZY_AUTO_LINK_THRESHOLD` | `85` | Score above which items auto-link to products |
| `FUZZY_SUGGEST_THRESHOLD` | `60` | Score above which a match suggestion is created |
| `TESSERACT_LANG` | `eng` | OCR language pack |
| `GOOGLE_CSE_API_KEY` | — | Optional: Google Custom Search for product images |
| `GOOGLE_CSE_CX` | — | Optional: Google CSE engine ID |

See `.env.example` for the full list.

## Architecture

Single Docker container running four processes via Supervisor:

```
┌─────────────────────────────────────────────┐
│                  Container                  │
│                                             │
│  ┌─────────┐    ┌──────────┐   ┌─────────┐ │
│  │  Nginx  │───▶│  FastAPI  │   │  Redis  │ │
│  │  :80    │    │  :8000   │◀─▶│  :6379  │ │
│  └─────────┘    └──────────┘   └────┬────┘ │
│       │                             │      │
│       │         ┌──────────┐        │      │
│       │         │  Celery  │◀───────┘      │
│       │         │  Worker  │               │
│       │         └──────────┘               │
│  SPA static                                │
│  files (/)       OCR + LLM                 │
│                  pipeline                  │
└─────────────────────────────────────────────┘
         │
    ./data volume
    ├── ledgerlens.db
    ├── receipts/
    └── products/
```

**Backend**: Python 3.11, FastAPI, SQLAlchemy 2 (async), Alembic, Celery  
**Frontend**: React 19, TypeScript, Vite, Tailwind CSS 4, TanStack Query, Zustand  
**OCR**: Tesseract via pytesseract  
**LLM**: OpenAI SDK (works with any compatible endpoint)

See [architectur.md](architectur.md) for the full architecture reference.

## Development

### Backend

```bash
cd backend
uv sync                    # Install dependencies
cp ../.env.example ../.env # Configure environment
uv run uvicorn app.main:app --reload --port 8000
```

In a separate terminal:
```bash
cd backend
uv run celery -A app.worker worker --pool=prefork --concurrency=1 --loglevel=info
```

Requires Redis running locally (`redis-server`) and Tesseract installed (`apt install tesseract-ocr`).

### Frontend

```bash
cd frontend
bun install
bun run dev    # Vite dev server on port 5173
```

The Vite dev server proxies `/api` and `/ws` to `localhost:8000`.

### Database Migrations

```bash
cd backend

# Generate a migration after model changes
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head
```

### Running Tests

```bash
# Backend
cd backend
uv run pytest

# Frontend
cd frontend
bun run test
```

## Tech Stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Celery, Redis |
| Frontend | React 19, TypeScript 5.9, Vite 8, Tailwind CSS 4, TanStack Query 5, Zustand 5 |
| OCR | Tesseract, PyMuPDF, Pillow |
| LLM | OpenAI Python SDK (Ollama / vLLM / OpenAI) |
| Matching | RapidFuzz |
| Database | SQLite (default), PostgreSQL (optional) |
| Infrastructure | Docker, Nginx, Supervisor |
| CI/CD | GitHub Actions → GHCR |

## Data & Privacy

- All data stays on your machine — no cloud services required
- Receipt images and database stored in the `./data` volume
- LLM processing can be fully local via Ollama
- No telemetry or analytics

## License

All rights reserved.
