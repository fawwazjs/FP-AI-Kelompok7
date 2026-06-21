# Lokalator RAG (Retrieval-Augmented Generation) Service
# Uses sentence-transformers + ChromaDB to ground Gemini responses in local dataset.

import csv
import json
import logging
import os
import re
import threading
from pathlib import Path

logger = logging.getLogger("lokalator.rag")

BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_DIR = BASE_DIR / "Dataset"

PERSIST_DIR = Path(os.getenv("RAG_PERSIST_DIR", str(BASE_DIR / "chroma_db")))

# Embedding model - multilingual, supports Indonesian/Javanese/Madurese text
EMBEDDING_MODEL_NAME = os.getenv(
    "LOKALATOR_EMBEDDING_MODEL",
    os.getenv("HG_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"),
)

# Singletons
_embedding_model = None
_chroma_collection = None
_init_lock = threading.Lock()
_initialized = False


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info("Loaded embedding model: %s", EMBEDDING_MODEL_NAME)
    return _embedding_model


def _get_collection():
    global _chroma_collection, _initialized
    if _chroma_collection is not None:
        return _chroma_collection

    with _init_lock:
        if _chroma_collection is not None:
            return _chroma_collection

        import chromadb

        # Persist to disk so embedding only happens once
        PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        chroma_client = chromadb.PersistentClient(path=str(PERSIST_DIR))
        _chroma_collection = chroma_client.get_or_create_collection(
            name="lokalator_knowledge",
            metadata={"hnsw:space": "cosine"}
        )

        # Only build if empty
        if _chroma_collection.count() == 0:
            _build_knowledge_base()
            _initialized = True
        else:
            _initialized = True

    return _chroma_collection


def _build_knowledge_base():
    """Parse all datasets and insert into ChromaDB."""
    chunks = []

    # 1. ngoko_krama.json - Javanese dictionary with speech levels
    chunks.extend(_parse_ngoko_krama())

    # 2. JawaIndo2.csv - Javanese-Indonesian pairs
    chunks.extend(_parse_jawa_indo2())

    # 3. JawaIndo.csv - Indonesian-Javanese dictionary
    chunks.extend(_parse_jawa_indo())

    # 4. madura.sql - Madurese-Indonesian sentence pairs
    chunks.extend(_parse_madura_sql())

    if not chunks:
        logger.warning("No chunks produced from datasets!")
        return

    # Embed and insert in batches
    model = _get_embedding_model()
    batch_size = 100
    total = len(chunks)
    logger.info("Building knowledge base: %d chunks to embed...", total)

    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadatas = [c["metadata"] for c in batch]
        embeddings = model.encode(texts).tolist()
        _chroma_collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    logger.info("Knowledge base ready: %d documents indexed.", total)


def _parse_ngoko_krama() -> list:
    """Parse ngoko_krama.json into searchable chunks."""
    path = DATASET_DIR / "ngoko_krama.json"
    if not path.exists():
        return []
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for key, rec in data.get("employees", {}).items():
        indo = str(rec.get("indonesia", "")).strip()
        ngoko = str(rec.get("ngoko", "")).strip()
        krama_alus = str(rec.get("kramaalus", "")).strip()
        krama_inggil = str(rec.get("kramainggil", "")).strip()
        if not indo or indo.lower() == "none":
            continue
        # Create a rich text chunk that contains all speech levels
        text = f"Bahasa Indonesia: {indo}"
        if ngoko and ngoko.lower() != "none":
            text += f" | Jawa Ngoko: {ngoko}"
        if krama_alus and krama_alus.lower() != "none":
            text += f" | Jawa Krama Lugu: {krama_alus}"
        if krama_inggil and krama_inggil.lower() != "none":
            text += f" | Jawa Krama Inggil: {krama_inggil}"
        chunks.append({
            "id": f"jv_dict_{key}",
            "text": text,
            "metadata": {
                "source": "ngoko_krama.json",
                "language": "jv",
                "type": "dictionary",
                "indo": indo.lower(),
            }
        })
    return chunks


def _parse_jawa_indo2() -> list:
    """Parse JawaIndo2.csv (jawa,indonesia)."""
    path = DATASET_DIR / "JawaIndo2.csv"
    if not path.exists():
        return []
    chunks = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, rec in enumerate(reader):
            jawa = (rec.get("jawa") or "").strip()
            indo = (rec.get("indonesia") or "").strip()
            if not jawa or not indo:
                continue
            text = f"Jawa: {jawa} | Indonesia: {indo}"
            chunks.append({
                "id": f"jv_indo2_{i}",
                "text": text,
                "metadata": {"source": "JawaIndo2.csv", "language": "jv", "type": "dictionary"}
            })
    return chunks


def _parse_jawa_indo() -> list:
    """Parse JawaIndo.csv (Indonesia,Javanese,Alphabet) — limited to short entries."""
    path = DATASET_DIR / "JawaIndo.csv"
    if not path.exists():
        return []
    chunks = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, rec in enumerate(reader):
            indo = (rec.get("Indonesia") or "").strip()
            jawa = (rec.get("Javanese") or "").strip()
            if not indo or not jawa:
                continue
            # Skip overly long dictionary glosses — keep only short, usable entries
            if len(jawa) > 80 or len(indo) > 40:
                continue
            text = f"Indonesia: {indo} | Jawa: {jawa}"
            chunks.append({
                "id": f"jv_indo_{i}",
                "text": text,
                "metadata": {"source": "JawaIndo.csv", "language": "jv", "type": "dictionary"}
            })
    return chunks


def _parse_madura_sql(limit: int = 3000) -> list:
    """Parse madura.sql sentence pairs."""
    path = DATASET_DIR / "madura.sql"
    if not path.exists():
        return []
    chunks = []
    row_re = re.compile(
        r"\((\d+),\s*'((?:[^'\\]|\\.)*)',\s*'((?:[^'\\]|\\.)*)',\s*(\d+),\s*(\d+),\s*(NULL|'(?:[^'\\]|\\.)*')\)"
    )
    pending_mad = {}
    loaded = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("("):
                continue
            if line.endswith(",") or line.endswith(";"):
                line = line[:-1]
            match = row_re.match(line)
            if not match:
                continue
            lang = match.group(2)
            sentence = match.group(3).replace("\\'", "'")
            pair_key = (match.group(5), match.group(4))
            if lang == "MAD":
                pending_mad[pair_key] = sentence
                continue
            if lang != "IND" or pair_key not in pending_mad:
                continue
            mad = pending_mad.pop(pair_key)
            indo = sentence
            # Clean up
            mad_clean = re.sub(r"\{[^}]*\}", "", mad).strip()
            indo_clean = re.sub(r"\{[^}]*\}", "", indo).strip()
            if not mad_clean or not indo_clean:
                continue
            text = f"Madura: {mad_clean} | Indonesia: {indo_clean}"
            chunks.append({
                "id": f"mad_{loaded}",
                "text": text,
                "metadata": {"source": "madura.sql", "language": "mad", "type": "dictionary"}
            })
            loaded += 1
            if loaded >= limit:
                break
    return chunks


# --- Public API ---

def retrieve(query: str, top_k: int = 10, language_filter: str | None = None) -> list[dict]:
    """Retrieve relevant knowledge chunks for a query.

    Returns list of {text, metadata, distance} dicts.
    """
    try:
        collection = _get_collection()
        model = _get_embedding_model()
    except Exception as exc:
        logger.warning("RAG retrieval failed during init: %s", exc)
        return []

    query_embedding = model.encode(query).tolist()

    where_filter = None
    if language_filter and language_filter in ("jv", "mad"):
        where_filter = {"language": language_filter}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
        )
    except Exception as exc:
        logger.warning("ChromaDB query failed: %s", exc)
        return []

    docs = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            docs.append({"text": doc, "metadata": meta, "distance": dist})
    return docs


def get_rag_context(query: str, target_lang: str | None = None, top_k: int = 8) -> str:
    """Build a context string from retrieved chunks for Gemini prompts."""
    lang_filter = target_lang if target_lang in ("jv", "mad") else None
    results = retrieve(query, top_k=top_k, language_filter=lang_filter)
    if not results:
        return ""
    context_parts = []
    for r in results:
        context_parts.append(f"- {r['text']}")
    return "\n".join(context_parts)


def is_available() -> bool:
    """Check if RAG service can be used."""
    try:
        _get_embedding_model()
        _get_collection()
        return True
    except Exception:
        return False


def get_stats() -> dict:
    """Get knowledge base statistics."""
    try:
        collection = _get_collection()
        return {
            "total_documents": collection.count(),
            "embedding_model": EMBEDDING_MODEL_NAME,
            "status": "ready",
        }
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


if __name__ == "__main__":
    """Run this script to pre-build the knowledge base index.
    
    Usage: python -m backend.rag_service
    """
    import time
    print("Building Lokalator RAG knowledge base...")
    start = time.time()
    stats = get_stats()
    elapsed = time.time() - start
    print(f"Done in {elapsed:.1f}s")
    print(f"Stats: {stats}")
