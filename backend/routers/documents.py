import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from ..core.config import Settings, get_settings
from ..database import get_db
from ..document_service import (
    PYMUPDF_AVAILABLE,
    PYTHON_DOCX_AVAILABLE,
    process_and_translate_docx,
    process_and_translate_pdf,
)
from ..models import TranslationLog
from ..schemas.translation import SupportedLanguage
from ..utils.text import redacted_summary, request_hash
from ..utils.uploads import DOCX_MIME, PDF_MIME, sanitize_download_name, save_validated_upload


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/translate-document")
def translate_document(
    file: UploadFile = File(...),
    target_lang: SupportedLanguage = Form(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    if target_lang == "id":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target terjemahan dokumen harus Bahasa Jawa atau Bahasa Madura.",
        )

    saved = save_validated_upload(file, settings.upload_dir, settings.max_upload_bytes)
    output_ext = _output_extension(saved.extension)
    safe_original = sanitize_download_name(saved.original_filename)
    output_filename = f"translated_{Path(safe_original).stem}.{output_ext}"
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = settings.output_dir / f"{saved.sha256[:16]}_{output_filename}"

    try:
        if saved.extension == "pdf":
            summary = process_and_translate_pdf(str(saved.path), str(output_path), target_lang)
        else:
            summary = process_and_translate_docx(str(saved.path), str(output_path), target_lang)

        _record_document_translation_once(db, saved.sha256, target_lang, summary)
    except HTTPException:
        _cleanup_paths(saved.path, output_path)
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        _cleanup_paths(saved.path, output_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Terjemahan dokumen tidak dapat dicatat.",
        ) from exc
    except Exception as exc:
        logger.exception("Document translation failed")
        _cleanup_paths(saved.path, output_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjemahan dokumen gagal diproses.",
        ) from exc

    return FileResponse(
        path=output_path,
        filename=output_filename,
        media_type=_media_type(output_ext),
        background=BackgroundTask(_cleanup_paths, saved.path, output_path),
    )


def _output_extension(input_extension: str) -> str:
    if input_extension == "pdf":
        return "pdf" if PYMUPDF_AVAILABLE else "txt"
    if input_extension == "docx":
        return "docx" if PYTHON_DOCX_AVAILABLE else "txt"
    return "txt"


def _media_type(extension: str) -> str:
    if extension == "pdf":
        return PDF_MIME
    if extension == "docx":
        return DOCX_MIME
    return "text/plain; charset=utf-8"


def _record_document_translation_once(
    db: Session,
    file_hash: str,
    target_lang: str,
    summary: dict,
) -> None:
    req_hash = request_hash("document", file_hash, target_lang)
    existing = db.query(TranslationLog.id).filter(TranslationLog.request_hash == req_hash).first()
    if existing:
        return

    db.add(
        TranslationLog(
            request_hash=req_hash,
            source_text=f"[uploaded_document:{file_hash[:12]}]",
            translated_text=redacted_summary(summary.get("file_created", "")),
            source_lang="id",
            target_lang=target_lang,
            politeness_level=summary["politeness_summary"],
            ngoko_pct=15.0 if target_lang == "jv" else 10.0,
            krama_pct=85.0 if target_lang == "jv" else 90.0,
        )
    )
    db.commit()


def _cleanup_paths(*paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)
