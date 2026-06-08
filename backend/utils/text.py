import hashlib
import re


WORD_RE = re.compile(r"[A-Za-z']+")


def normalize_for_hash(text: str) -> str:
    return " ".join(text.strip().lower().split())


def request_hash(*parts: str) -> str:
    normalized = "\x1f".join(normalize_for_hash(part) for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def redacted_summary(text: str) -> str:
    return f"[redacted:{len(text)} chars:{len(text.split())} words]"


def extract_indexable_words(text: str, *, min_length: int = 4) -> list[str]:
    return [word for word in WORD_RE.findall(text.lower()) if len(word) >= min_length]
