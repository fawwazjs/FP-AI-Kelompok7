from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..database import get_db
from ..models import TranslationLog, VocabularyStat
from ..schemas import TranslationRequest, TranslationResponse
from ..services.cache import TTLCache
from ..translator_service import translate_and_classify
from ..utils.text import extract_indexable_words, redacted_summary, request_hash


router = APIRouter(prefix="/api", tags=["translation"])
_translation_cache: TTLCache[dict] | None = None
_translation_cache_config: tuple[int, int] | None = None


@router.post("/translate", response_model=TranslationResponse)
def translate_text(
    req: TranslationRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TranslationResponse:
    text = req.text.strip()
    if len(text) > settings.max_text_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Teks terlalu panjang. Maksimum {settings.max_text_chars} karakter.",
        )

    cache_key = request_hash(text, req.source_lang, req.target_lang, req.level)
    cache = _get_translation_cache(settings) if settings.translation_cache_enabled else None
    result = cache.get(cache_key) if cache else None
    if result is None:
        try:
            result = translate_and_classify(text, req.source_lang, req.target_lang, req.level)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Layanan terjemahan sementara tidak tersedia.",
            ) from exc

        if cache:
            cache.set(cache_key, result)

    try:
        _record_translation_once(db, req, result)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Terjemahan tidak dapat dicatat.",
        ) from exc

    return TranslationResponse(**result)


def _get_translation_cache(settings: Settings) -> TTLCache[dict]:
    global _translation_cache, _translation_cache_config

    cache_config = (settings.translation_cache_max_items, settings.translation_cache_ttl_seconds)
    if _translation_cache is None or _translation_cache_config != cache_config:
        _translation_cache = TTLCache(
            max_items=settings.translation_cache_max_items,
            ttl_seconds=settings.translation_cache_ttl_seconds,
        )
        _translation_cache_config = cache_config

    return _translation_cache


def _record_translation_once(db: Session, req: TranslationRequest, result: dict) -> None:
    req_hash = request_hash(req.text, req.source_lang, req.target_lang, req.level)
    existing = db.query(TranslationLog.id).filter(TranslationLog.request_hash == req_hash).first()
    if existing:
        return

    db.add(
        TranslationLog(
            request_hash=req_hash,
            source_text=redacted_summary(req.text),
            translated_text=redacted_summary(result["translatedText"]),
            source_lang=req.source_lang,
            target_lang=req.target_lang,
            politeness_level=result["politenessLevel"],
            ngoko_pct=result["ngokoPercentage"],
            krama_pct=result["kramaPercentage"],
        )
    )

    for word in extract_indexable_words(req.text):
        stat = db.query(VocabularyStat).filter(VocabularyStat.word == word).first()
        if stat:
            stat.count += 1
        else:
            db.add(VocabularyStat(word=word, language=req.source_lang, count=1))

    db.commit()
