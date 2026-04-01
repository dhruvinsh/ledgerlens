from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Paths that don't require authentication
PUBLIC_PREFIXES = (
    "/api/v1/auth/",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/health",
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Only gate /api/* paths
        if not path.startswith("/api/"):
            return await call_next(request)

        # Allow public endpoints
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Require session_id cookie
        session_id = request.cookies.get("session_id")
        if not session_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"},
            )

        return await call_next(request)
