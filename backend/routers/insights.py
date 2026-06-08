from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TranslationLog, VocabularyStat
from ..schemas import InsightMetrics, InsightsResponse, PopularWord, VitalityTrends


router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/insights", response_model=InsightsResponse)
def get_insights(db: Session = Depends(get_db)) -> InsightsResponse:
    try:
        total_translations = db.query(TranslationLog).count()
        total_vocabulary = db.query(VocabularyStat.word, VocabularyStat.language).distinct().count()

        total_count = func.sum(VocabularyStat.count).label("total_count")
        top_words = (
            db.query(VocabularyStat.word, VocabularyStat.language, total_count)
            .group_by(VocabularyStat.word, VocabularyStat.language)
            .order_by(total_count.desc(), VocabularyStat.word.asc())
            .limit(10)
            .all()
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data insight sementara tidak tersedia.",
        ) from exc

    return InsightsResponse(
        metrics=InsightMetrics(
            total_vocabulary=total_vocabulary,
            active_contributors=0,
            vitality_status="Belum diukur",
            preservation_accuracy=None,
            total_translations=total_translations,
        ),
        popular_words=[
            PopularWord(word=row.word, language=row.language, count=int(row.total_count or 0))
            for row in top_words
        ],
        vitality_trends=VitalityTrends(years=[], jv_scores=[], mad_scores=[]),
    )
