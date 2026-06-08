from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.exceptions import register_exception_handlers
from .core.config import get_settings
from .core.middleware import InMemoryRateLimitMiddleware, MetricsMiddleware, SecurityHeadersMiddleware
from .database import init_db
from .routers import documents, health, insights, translation


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_storage_dirs()
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    if settings.rate_limit_enabled:
        app.add_middleware(
            InMemoryRateLimitMiddleware,
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )

    if settings.security_headers_enabled:
        app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(MetricsMiddleware)

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(translation.router)
    app.include_router(documents.router)
    app.include_router(insights.router)
    return app


app = create_app()
