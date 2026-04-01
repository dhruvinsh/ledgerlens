import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.exceptions import (
    AppError,
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.middleware.auth import AuthMiddleware
from app.middleware.security import SecurityMiddleware
from app.routers import (
    admin,
    auth,
    dashboard,
    household,
    items,
    jobs,
    line_items,
    receipts,
    stores,
    suggestions,
    ws,
)
from app.services.notifications import start_job_update_subscriber
from app.services.retroactive_matching import start_retroactive_loop


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)

    # Start retroactive matching background loop
    retroactive_task = asyncio.create_task(
        start_retroactive_loop(async_session_factory)
    )

    # Start Redis → WebSocket bridge for real-time job updates
    ws_bridge_task = asyncio.create_task(start_job_update_subscriber())

    yield

    # Shutdown
    ws_bridge_task.cancel()
    retroactive_task.cancel()
    with suppress(asyncio.CancelledError):
        await retroactive_task
    with suppress(asyncio.CancelledError):
        await ws_bridge_task


app = FastAPI(title="LedgerLens API", lifespan=lifespan)

# Middleware (outermost first)
app.add_middleware(AuthMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    status_map: dict[type, int] = {
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


# API Routers
for router_module in [auth, receipts, items, stores, dashboard, household, admin, jobs, line_items, suggestions]:
    app.include_router(router_module.router, prefix="/api/v1")

# WebSocket (no /api/v1 prefix)
app.include_router(ws.router)

# Static files — ensure directory exists before mounting (runs at import time,
# before lifespan which would otherwise create it too late)
Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=settings.DATA_DIR), name="files")


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
