# HeritageGuard ML configuration.
# Central place for all paths, language codes, and model-id constants.

import os
from pathlib import Path

# Repo root = two levels up from this file (backend/ml/config.py -> repo root).
BASE_DIR = Path(__file__).resolve().parents[2]

DATASET_DIR = BASE_DIR / "Dataset"

# Where training writes / inference reads artifacts. Override with HG_MODEL_DIR.
MODEL_DIR = Path(os.getenv("HG_MODEL_DIR", str(BASE_DIR / "models")))

# Sub-paths for each artifact produced by the training pipeline.
NMT_DIR = MODEL_DIR / "nmt"                      # fine-tuned seq2seq model + tokenizer
CLASSIFIER_PATH = MODEL_DIR / "register_clf.joblib"   # TF-IDF + sklearn pipeline bundle

# Intermediate corpora produced by data prep (consumed by the Colab notebook).
PROCESSED_DIR = MODEL_DIR / "processed"
PARALLEL_CORPUS_PATH = PROCESSED_DIR / "parallel_corpus.jsonl"
CLASSIFIER_CORPUS_PATH = PROCESSED_DIR / "classifier_corpus.jsonl"

# Internal language codes used by the API.
LANG_ID = "id"
LANG_JV = "jv"
LANG_MAD = "mad"
SUPPORTED_LANGUAGES = {LANG_ID, LANG_JV, LANG_MAD}
SUPPORTED_LEVELS = {"low", "high"}

# Base pre-trained model to fine-tune. NLLB-200 distilled (600M) is a good
# size/quality trade-off for Colab's free GPU. Override with HG_BASE_MODEL.
BASE_NMT_MODEL = os.getenv("HG_BASE_MODEL", "facebook/nllb-200-distilled-600M")

# NLLB language codes. Javanese has an official code; Madurese does not, so we
# borrow Indonesian as the closest high-resource proxy for the base model and
# rely on fine-tuning to specialise it.
NLLB_LANG_CODES = {
    LANG_ID: "ind_Latn",
    LANG_JV: "jav_Latn",
    LANG_MAD: "ind_Latn",  # proxy; fine-tuning adapts it toward Madurese
}

# Level -> register label used to tag the target side during training so the
# model can be steered between polite (high) and casual (low) registers.
LEVEL_TAGS = {"high": "<halus>", "low": "<lugu>"}


def model_present() -> bool:
    """True only when both artifacts exist on disk."""
    return NMT_DIR.exists() and CLASSIFIER_PATH.exists()
