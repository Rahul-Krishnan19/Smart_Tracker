"""
FastAPI application entry point.
Configures middleware, CORS, rate limiting, and mounts routes.
"""
import os
from contextlib import asynccontextmanager
from alembic.config import Config
from alembic import command
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api.routes import auth, transactions, gmail, analytics, insights
from app.scheduler import scheduler, register_startup_jobs


def _run_db_migrations():
    """Run Alembic migrations on startup instead of Base.metadata.create_all."""
    ini_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    )
    alembic_cfg = Config(ini_path)
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    _run_db_migrations()
    scheduler.start()
    register_startup_jobs()
    yield
    # --- shutdown ---
    scheduler.shutdown(wait=False)


# Rate limiter (shared state)
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    # Disable interactive docs in production; enable during development
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — only allow configured frontend origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(gmail.router, prefix="/api/gmail", tags=["gmail"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(insights.router)


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "healthy", "app": settings.app_name}
