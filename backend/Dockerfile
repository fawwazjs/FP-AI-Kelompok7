FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers

WORKDIR /app

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip \
    && pip install --index-url ${TORCH_INDEX_URL} torch \
    && pip install -r /app/backend/requirements.txt

COPY backend /app/backend
COPY Dataset /app/Dataset

RUN mkdir -p /data /app/temp_uploads /app/temp_outputs /app/chroma_db /app/.cache/huggingface /app/.cache/sentence-transformers \
    && RAG_PERSIST_DIR=/app/chroma_db python -m backend.rag_service

ENV DATABASE_URL=sqlite:////data/lokalator.db \
    RAG_PERSIST_DIR=/app/chroma_db \
    UPLOAD_DIR=/app/temp_uploads \
    OUTPUT_DIR=/app/temp_outputs \
    GEMINI_USE_RAG=1 \
    MAX_TEXT_CHARS=2000 \
    MAX_UPLOAD_BYTES=5242880

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).read()"

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
