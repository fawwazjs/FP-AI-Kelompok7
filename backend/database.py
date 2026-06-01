import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./heritageguard.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TranslationLog(Base):
    __tablename__ = "translation_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    source_text = Column(String, index=True)
    translated_text = Column(String)
    source_lang = Column(String)
    target_lang = Column(String)
    politeness_level = Column(String)
    ngoko_pct = Column(Float)
    krama_pct = Column(Float)

class VocabularyStat(Base):
    __tablename__ = "vocabulary_stats"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, unique=True, index=True)
    language = Column(String)
    count = Column(Integer, default=1)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
