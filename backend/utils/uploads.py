import hashlib
import re
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status


PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

ALLOWED_MIME_BY_EXT = {
    ".pdf": {PDF_MIME},
    ".docx": {DOCX_MIME},
}


@dataclass(frozen=True)
class SavedUpload:
    path: Path
    original_filename: str
    extension: str
    sha256: str
    size_bytes: int


def sanitize_download_name(filename: str, fallback: str = "document") -> str:
    original = Path(filename or fallback).name
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(original).stem).strip("._")
    suffix = Path(original).suffix.lower()
    return f"{(stem or fallback)[:80]}{suffix}"


def save_validated_upload(file: UploadFile, upload_dir: Path, max_bytes: int) -> SavedUpload:
    original_filename = sanitize_download_name(file.filename or "document")
    suffix = Path(original_filename).suffix.lower()
    if suffix not in ALLOWED_MIME_BY_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format file tidak didukung. Gunakan PDF atau DOCX.",
        )

    if file.content_type not in ALLOWED_MIME_BY_EXT[suffix]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipe konten file tidak valid.",
        )

    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"{uuid.uuid4().hex}{suffix}"
    hasher = hashlib.sha256()
    total = 0

    try:
        with destination.open("wb") as buffer:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Ukuran file terlalu besar.",
                    )
                hasher.update(chunk)
                buffer.write(chunk)

        _validate_magic(destination, suffix)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File unggahan tidak dapat divalidasi.",
        ) from exc
    finally:
        file.file.close()

    return SavedUpload(
        path=destination,
        original_filename=original_filename,
        extension=suffix.removeprefix("."),
        sha256=hasher.hexdigest(),
        size_bytes=total,
    )


def _validate_magic(path: Path, suffix: str) -> None:
    if suffix == ".pdf":
        with path.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Signature file PDF tidak valid.",
                )
        return

    if suffix == ".docx":
        if not zipfile.is_zipfile(path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signature file DOCX tidak valid.",
            )
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Struktur file DOCX tidak valid.",
                )
