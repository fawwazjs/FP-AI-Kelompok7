# HeritageGuard ML data preparation.
#
# Builds two corpora from the local Dataset/ files:
#   1. parallel_corpus.jsonl   -> for fine-tuning the NMT model
#   2. classifier_corpus.jsonl -> for training the TF-IDF register classifier
#
# This module deliberately has NO heavy dependencies (no torch / transformers)
# so it can run both locally and at the top of the Colab notebook.

import csv
import json
import re
from pathlib import Path

from . import config

# Reuse the battle-tested dataset parsing already present in the rule-based
# service so the corpora match what the app understands.
from ..translator_service import (
    ID_TO_JV,
    ID_TO_MAD,
    PHRASES_DB,
    _clean_dataset_value,
    _clean_madura_sentence,
    _looks_like_short_phrase,
    _normalize_text_key,
    _word_count,
)

_ROW_RE = re.compile(
    r"\((\d+),\s*'((?:[^'\\]|\\.)*)',\s*'((?:[^'\\]|\\.)*)',\s*(\d+),\s*(\d+),\s*(NULL|'(?:[^'\\]|\\.)*')\)"
)


def _add_pair(rows: list, source: str, target: str, src_lang: str, tgt_lang: str, level: str):
    source = source.strip()
    target = target.strip()
    if not source or not target:
        return
    rows.append({
        "source": source,
        "target": target,
        "src_lang": src_lang,
        "tgt_lang": tgt_lang,
        "level": level,
    })


def build_parallel_corpus() -> list:
    """Collect ID<->JV and ID<->MAD sentence/word pairs with register level tags."""
    rows: list = []

    # --- Phrase database (already register-aware: high / low) ---
    for pair_key, bucket in PHRASES_DB.items():
        _, tgt = pair_key.split("_", 1)  # e.g. "id_jv" -> tgt = "jv"
        if tgt not in (config.LANG_JV, config.LANG_MAD):
            continue
        for indo_phrase, entry in bucket.items():
            for level in ("high", "low"):
                regional = entry.get(level)
                if not regional:
                    continue
                # id -> regional
                _add_pair(rows, indo_phrase, regional, config.LANG_ID, tgt, level)
                # regional -> id (reverse direction)
                _add_pair(rows, regional, indo_phrase, tgt, config.LANG_ID, level)

    # --- Word dictionaries (high/low aware) ---
    for word, val in ID_TO_JV.items():
        for level in ("high", "low"):
            _add_pair(rows, word, val[level], config.LANG_ID, config.LANG_JV, level)
            _add_pair(rows, val[level], word, config.LANG_JV, config.LANG_ID, level)
    for word, val in ID_TO_MAD.items():
        for level in ("high", "low"):
            _add_pair(rows, word, val[level], config.LANG_ID, config.LANG_MAD, level)
            _add_pair(rows, val[level], word, config.LANG_MAD, config.LANG_ID, level)

    # --- JawaIndo CSV dictionaries (word-level, register-neutral -> tag low) ---
    rows.extend(_parse_jawa_csv(config.DATASET_DIR / "JawaIndo2.csv", swapped=False))
    rows.extend(_parse_jawa_csv_primary(config.DATASET_DIR / "JawaIndo.csv"))

    # --- Madura SQL parallel sentences ---
    rows.extend(_parse_madura_sql(config.DATASET_DIR / "madura.sql"))

    # De-duplicate identical (source, target, level) triples.
    seen = set()
    unique = []
    for r in rows:
        key = (r["source"].lower(), r["target"].lower(), r["src_lang"], r["tgt_lang"], r["level"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


def _parse_jawa_csv(path: Path, swapped: bool) -> list:
    """JawaIndo2.csv has header: jawa,indonesia."""
    rows: list = []
    if not path.exists():
        return rows
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for rec in reader:
            jawa = _clean_dataset_value(rec.get("jawa"))
            indo = _clean_dataset_value(rec.get("indonesia"))
            # The indonesian side often holds a gloss with synonyms; keep the
            # first short comma-separated sense only.
            indo = indo.split(",", 1)[0].strip()
            if not jawa or not indo or _word_count(indo) > 5 or _word_count(jawa) > 5:
                continue
            _add_pair(rows, indo, jawa, config.LANG_ID, config.LANG_JV, "low")
            _add_pair(rows, jawa, indo, config.LANG_JV, config.LANG_ID, "low")
    return rows


def _parse_jawa_csv_primary(path: Path) -> list:
    """JawaIndo.csv has header: Indonesia,Javanese,Alphabet (gloss-heavy)."""
    rows: list = []
    if not path.exists():
        return rows
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for rec in reader:
            indo = _clean_dataset_value(rec.get("Indonesia"))
            jawa_raw = _clean_dataset_value(rec.get("Javanese"))
            if not indo or not jawa_raw:
                continue
            # The Javanese column is dictionary prose; take the first clean sense.
            jawa = re.split(r"[;,.]", jawa_raw, 1)[0].strip()
            jawa = re.sub(r"^\d+\s+", "", jawa)  # strip leading sense numbers
            if not jawa or _word_count(indo) > 4 or _word_count(jawa) > 4:
                continue
            _add_pair(rows, indo, jawa, config.LANG_ID, config.LANG_JV, "low")
            _add_pair(rows, jawa, indo, config.LANG_JV, config.LANG_ID, "low")
    return rows


def _parse_madura_sql(path: Path, limit: int = 20000) -> list:
    """Parse the descr `sentences` table: alternating MAD / IND rows pair up."""
    rows: list = []
    if not path.exists():
        return rows
    pending_mad: dict = {}
    loaded = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("("):
                continue
            if line.endswith(",") or line.endswith(";"):
                line = line[:-1]
            match = _ROW_RE.match(line)
            if not match:
                continue
            lang = match.group(2)
            sentence = match.group(3)
            pair_key = (match.group(5), match.group(4))  # (lemma_id, index)
            if lang == "MAD":
                pending_mad[pair_key] = sentence
                continue
            if lang != "IND" or pair_key not in pending_mad:
                continue
            mad = _clean_madura_sentence(pending_mad.pop(pair_key))
            indo = _clean_madura_sentence(sentence)
            if not _looks_like_short_phrase(mad) or not _looks_like_short_phrase(indo):
                continue
            _add_pair(rows, indo, mad, config.LANG_ID, config.LANG_MAD, "low")
            _add_pair(rows, mad, indo, config.LANG_MAD, config.LANG_ID, "low")
            loaded += 1
            if loaded >= limit:
                break
    return rows


def build_classifier_corpus() -> list:
    """Build (text, language, register) rows for the TF-IDF classifier.

    Labels are language-level: 'Indonesia', 'Jawa', 'Madura'. The register sub
    label is derived from the level tag of the regional side.
    """
    rows: list = []
    parallel = build_parallel_corpus()
    for r in parallel:
        # We only label the regional/indonesian text by its own language.
        lang_label = {
            config.LANG_ID: "Indonesia",
            config.LANG_JV: "Jawa",
            config.LANG_MAD: "Madura",
        }
        # Source side
        rows.append({
            "text": r["source"],
            "language": lang_label[r["src_lang"]],
            "level": r["level"],
        })
    # De-duplicate by text+language.
    seen = set()
    unique = []
    for r in rows:
        key = (r["text"].lower(), r["language"])
        if key in seen or not r["text"].strip():
            continue
        seen.add(key)
        unique.append(r)
    return unique


def write_corpora() -> dict:
    """Write both corpora to PROCESSED_DIR as JSONL. Returns counts."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    parallel = build_parallel_corpus()
    with open(config.PARALLEL_CORPUS_PATH, "w", encoding="utf-8") as f:
        for row in parallel:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    classifier = build_classifier_corpus()
    with open(config.CLASSIFIER_CORPUS_PATH, "w", encoding="utf-8") as f:
        for row in classifier:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "parallel_pairs": len(parallel),
        "classifier_rows": len(classifier),
        "parallel_path": str(config.PARALLEL_CORPUS_PATH),
        "classifier_path": str(config.CLASSIFIER_CORPUS_PATH),
    }


if __name__ == "__main__":
    stats = write_corpora()
    print("HeritageGuard data prep complete:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
