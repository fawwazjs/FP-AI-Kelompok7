# HeritageGuard ML inference layer.
#
# Loads the fine-tuned NMT model and the TF-IDF register classifier when their
# artifacts are present. All heavy imports (torch / transformers / joblib) are
# done lazily inside the loaders so the backend runs fine without them, falling
# back to the rule-based engine.

import logging
import threading

from . import config

logger = logging.getLogger("heritageguard.ml")

# Singletons, guarded by a lock so concurrent requests load the model once.
_nmt_bundle = None          # dict: {model, tokenizer} or False if unavailable
_classifier_bundle = None   # sklearn bundle or False if unavailable
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# NMT (translation) model
# ---------------------------------------------------------------------------
def _load_nmt():
    """Load the fine-tuned seq2seq model + tokenizer. Returns dict or False."""
    global _nmt_bundle
    if _nmt_bundle is not None:
        return _nmt_bundle

    with _lock:
        if _nmt_bundle is not None:
            return _nmt_bundle
        if not config.NMT_DIR.exists():
            logger.info("NMT artifacts not found at %s; using rule-based fallback.", config.NMT_DIR)
            _nmt_bundle = False
            return _nmt_bundle
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(str(config.NMT_DIR))
            model = AutoModelForSeq2SeqLM.from_pretrained(str(config.NMT_DIR))
            model.eval()
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device)
            _nmt_bundle = {"model": model, "tokenizer": tokenizer, "device": device, "torch": torch}
            logger.info("Loaded fine-tuned NMT model from %s on %s.", config.NMT_DIR, device)
        except Exception as exc:  # noqa: BLE001 - any failure -> safe fallback
            logger.warning("Failed to load NMT model (%s); using rule-based fallback.", exc)
            _nmt_bundle = False
    return _nmt_bundle


def nmt_available() -> bool:
    return bool(_load_nmt())


def translate(text: str, source: str, target: str, level: str) -> str | None:
    """Translate one text with the NMT model. Returns None if unavailable."""
    bundle = _load_nmt()
    if not bundle:
        return None
    if not text.strip():
        return ""

    tokenizer = bundle["tokenizer"]
    model = bundle["model"]
    torch = bundle["torch"]

    src_code = config.NLLB_LANG_CODES.get(source)
    tgt_code = config.NLLB_LANG_CODES.get(target)
    level_tag = config.LEVEL_TAGS.get(level, "")

    # Steer register by prepending the level tag to the source text.
    model_input = f"{level_tag} {text}".strip()

    try:
        if hasattr(tokenizer, "src_lang") and src_code:
            tokenizer.src_lang = src_code
        encoded = tokenizer(model_input, return_tensors="pt", truncation=True, max_length=256)
        encoded = {k: v.to(bundle["device"]) for k, v in encoded.items()}

        gen_kwargs = {"max_length": 256, "num_beams": 4}
        # NLLB needs the forced BOS token for the target language.
        if tgt_code and hasattr(tokenizer, "convert_tokens_to_ids"):
            forced = tokenizer.convert_tokens_to_ids(tgt_code)
            if forced is not None and forced >= 0:
                gen_kwargs["forced_bos_token_id"] = forced

        with torch.no_grad():
            output = model.generate(**encoded, **gen_kwargs)
        decoded = tokenizer.batch_decode(output, skip_special_tokens=True)
        return decoded[0].strip() if decoded else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("NMT inference failed (%s); falling back.", exc)
        return None


# ---------------------------------------------------------------------------
# Register / language classifier
# ---------------------------------------------------------------------------
def _load_classifier():
    """Load the TF-IDF + sklearn bundle. Returns bundle dict or False."""
    global _classifier_bundle
    if _classifier_bundle is not None:
        return _classifier_bundle

    with _lock:
        if _classifier_bundle is not None:
            return _classifier_bundle
        if not config.CLASSIFIER_PATH.exists():
            logger.info("Classifier artifact not found at %s; using rule-based fallback.", config.CLASSIFIER_PATH)
            _classifier_bundle = False
            return _classifier_bundle
        try:
            import joblib

            bundle = joblib.load(config.CLASSIFIER_PATH)
            _classifier_bundle = bundle
            logger.info("Loaded register classifier from %s.", config.CLASSIFIER_PATH)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load classifier (%s); using rule-based fallback.", exc)
            _classifier_bundle = False
    return _classifier_bundle


def classifier_available() -> bool:
    return bool(_load_classifier())


def classify_language(text: str) -> dict | None:
    """Predict language + register + confidence. Returns None if unavailable.

    Expected bundle structure (produced by training):
        {
          "lang_clf": <sklearn Pipeline>,   # text -> 'Indonesia'/'Jawa'/'Madura'
          "register_clf": {                  # per-language register pipelines
              "Jawa": <Pipeline>, "Madura": <Pipeline>, "Indonesia": <Pipeline>
          }
        }
    """
    bundle = _load_classifier()
    if not bundle or not text.strip():
        return None
    try:
        lang_clf = bundle["lang_clf"]
        language = lang_clf.predict([text])[0]
        lang_conf = _max_proba(lang_clf, [text])

        register = ""
        reg_conf = None
        register_clfs = bundle.get("register_clf", {})
        reg_clf = register_clfs.get(language)
        if reg_clf is not None:
            register = reg_clf.predict([text])[0]
            reg_conf = _max_proba(reg_clf, [text])

        return {
            "language": language,
            "register": register,
            "language_confidence": lang_conf,
            "register_confidence": reg_conf,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Classifier inference failed (%s); falling back.", exc)
        return None


def classify_politeness(text: str, lang: str) -> dict | None:
    """Return {'ngoko': float, 'krama': float, 'level': str} or None.

    Uses the per-language register classifier's probability over high/low
    style to derive the ngoko/krama split shown in the frontend.
    """
    bundle = _load_classifier()
    if not bundle or lang not in (config.LANG_JV, config.LANG_MAD):
        return None
    try:
        lang_label = "Jawa" if lang == config.LANG_JV else "Madura"
        style_clfs = bundle.get("style_clf", {})
        style_clf = style_clfs.get(lang_label)
        if style_clf is None:
            return None
        # Probability of the "high" (krama/halus) class.
        proba = style_clf.predict_proba([text])[0]
        classes = list(style_clf.classes_)
        if "high" in classes:
            krama = round(float(proba[classes.index("high")]) * 100, 1)
        else:
            krama = 50.0
        ngoko = round(100.0 - krama, 1)
        level = "high" if krama >= ngoko else "low"
        return {"ngoko": ngoko, "krama": krama, "level": level}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Politeness classification failed (%s); falling back.", exc)
        return None


def _max_proba(clf, X) -> float | None:
    """Best-effort max class probability for an sklearn estimator."""
    try:
        proba = clf.predict_proba(X)[0]
        return round(float(max(proba)) * 100, 1)
    except Exception:  # noqa: BLE001
        return None
