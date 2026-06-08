import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from ..database import Base


class TranslationLog(Base):
    __tablename__ = "translation_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_hash = Column(String(64), index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    source_text = Column(String, index=True, nullable=False)
    translated_text = Column(String, nullable=False)
    source_lang = Column(String(16), nullable=False)
    target_lang = Column(String(16), nullable=False)
    politeness_level = Column(String(64), nullable=False)
    ngoko_pct = Column(Float, nullable=False)
    krama_pct = Column(Float, nullable=False)


class VocabularyStat(Base):
    __tablename__ = "vocabulary_stats"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(128), index=True, nullable=False)
    language = Column(String(16), index=True, nullable=False)
    count = Column(Integer, default=1, nullable=False)
