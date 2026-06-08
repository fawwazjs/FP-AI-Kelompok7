from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .core.config import get_settings


Base = declarative_base()


def _connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


settings = get_settings()
engine = create_engine(
    settings.database_url,
    connect_args=_connect_args(settings.database_url),
    echo=settings.sql_echo,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    from .models import TranslationLog, VocabularyStat  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_translation_log_columns()


def _ensure_translation_log_columns() -> None:
    inspector = inspect(engine)
    if "translation_logs" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("translation_logs")}
    if "request_hash" in existing_columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE translation_logs ADD COLUMN request_hash VARCHAR(64)"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_translation_logs_request_hash ON translation_logs (request_hash)")
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
