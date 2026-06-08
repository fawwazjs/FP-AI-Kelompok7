from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..database import get_db
from ..core.metrics import metrics_registry


router = APIRouter(tags=["health"])


@router.get("/")
def read_root(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "message": "HeritageGuard API is active",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/healthz")
def healthz(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pemeriksaan kesehatan database gagal.",
        ) from exc
    return {"status": "ok", "database": "ok"}


@router.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return metrics_registry.render_prometheus()
