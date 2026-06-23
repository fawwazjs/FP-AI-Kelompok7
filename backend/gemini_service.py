# Lokalator Gemini AI Service
# Provides LLM-powered translation fallback and chatbot functionality.

import html
import json
import os
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
import httpx

logger = logging.getLogger("lokalator.gemini")

def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key.startswith(("GEMINI_", "GOOGLE_TRANSLATE_")) or key in os.environ:
                continue
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value
    except OSError as exc:
        logger.warning("Could not read local .env file: %s", exc)


_load_local_env()


def _load_api_keys() -> list[str]:
    raw = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or ""
    return [k.strip() for k in raw.split(",") if k.strip()]


GEMINI_API_KEYS: list[str] = _load_api_keys()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
GEMINI_USE_RAG = os.getenv("GEMINI_USE_RAG", "0").lower() in {"1", "true", "yes", "on"}
GEMINI_RAG_TIMEOUT_SECONDS = float(os.getenv("GEMINI_RAG_TIMEOUT_SECONDS", "1.5"))
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY", "").strip()
GOOGLE_TRANSLATE_URL = os.getenv(
    "GOOGLE_TRANSLATE_URL",
    "https://translation.googleapis.com/language/translate/v2",
)
GOOGLE_TRANSLATE_MODEL = os.getenv("GOOGLE_TRANSLATE_MODEL", "").strip()

_gemini_timeout = httpx.Timeout(
    float(os.getenv("GEMINI_TIMEOUT_SECONDS", "25")),
    connect=float(os.getenv("GEMINI_CONNECT_TIMEOUT_SECONDS", "5")),
    read=float(os.getenv("GEMINI_READ_TIMEOUT_SECONDS", "25")),
    write=float(os.getenv("GEMINI_WRITE_TIMEOUT_SECONDS", "10")),
    pool=float(os.getenv("GEMINI_POOL_TIMEOUT_SECONDS", "5")),
)
_gemini_client = httpx.Client(
    timeout=_gemini_timeout,
    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
)

# Round-robin counter for key rotation.
_key_index = 0
_key_lock = threading.Lock()
_rag_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="gemini-rag")
_translation_cache: dict[tuple[str, str, str, str], str] = {}
_translation_cache_lock = threading.Lock()


def _next_key() -> str:
    """Get the next API key in round-robin fashion."""
    global _key_index
    valid_keys = _valid_api_keys()
    with _key_lock:
        key = valid_keys[_key_index % len(valid_keys)]
        _key_index += 1
    return key

LANG_NAMES = {
    "id": "Bahasa Indonesia",
    "jv": "Bahasa Jawa",
    "mad": "Bahasa Madura",
}

LEVEL_DESCRIPTIONS = {
    "high": {
        "jv": "Krama Alus (tingkat tutur sopan/formal)",
        "mad": "Engghi-Bhanten (tingkat tutur sopan/formal)",
    },
    "low": {
        "jv": "Ngoko Lugu (tingkat tutur kasual/akrab)",
        "mad": "Enja-Iya (tingkat tutur kasual/akrab)",
    },
}


def _is_configured() -> bool:
    return bool(_valid_api_keys())


def _is_placeholder_key(key: str) -> bool:
    normalized = key.lower()
    return (
        not key
        or "placeholder" in normalized
        or "your_" in normalized
        or normalized in {"key1", "key2", "key3"}
    )


def _valid_api_keys() -> list[str]:
    return [key for key in GEMINI_API_KEYS if not _is_placeholder_key(key)]


def get_gemini_status() -> dict:
    return {
        "configured": _is_configured(),
        "keyCount": len(_valid_api_keys()),
        "model": GEMINI_MODEL,
        "ragEnabled": GEMINI_USE_RAG,
        "googleTranslateConfigured": bool(GOOGLE_TRANSLATE_API_KEY),
        "providers": [
            provider
            for provider in (
                "gemini" if _is_configured() else None,
                "google_translate" if GOOGLE_TRANSLATE_API_KEY else None,
                "local_fallback",
            )
            if provider
        ],
        "acceptedEnvVars": [
            "GEMINI_API_KEYS",
            "GEMINI_API_KEY",
            "GOOGLE_TRANSLATE_API_KEY",
            "GOOGLE_TRANSLATE_MODEL",
        ],
    }


def _generation_config(
    temperature: float,
    max_tokens: int,
    response_schema: dict | None = None,
) -> dict:
    config: dict = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
    }
    if response_schema:
        config["responseMimeType"] = "application/json"
        config["responseSchema"] = response_schema
    thinking_level = os.getenv("GEMINI_THINKING_LEVEL")
    thinking_budget = os.getenv("GEMINI_THINKING_BUDGET")
    if thinking_level:
        config["thinkingConfig"] = {"thinkingLevel": thinking_level}
    elif thinking_budget:
        try:
            config["thinkingConfig"] = {"thinkingBudget": int(thinking_budget)}
        except ValueError:
            logger.warning("Invalid GEMINI_THINKING_BUDGET value: %s", thinking_budget)
    elif GEMINI_MODEL.startswith("gemini-2.5"):
        config["thinkingConfig"] = {"thinkingBudget": 0}
    return config


def _get_rag_context_safe(query: str, target_lang: str | None = None, top_k: int = 5) -> str:
    if not GEMINI_USE_RAG:
        return ""

    def retrieve_context() -> str:
        from .rag_service import get_rag_context
        return get_rag_context(query, target_lang=target_lang, top_k=top_k)

    future = _rag_executor.submit(retrieve_context)
    try:
        return future.result(timeout=GEMINI_RAG_TIMEOUT_SECONDS)
    except TimeoutError:
        logger.warning("RAG context timed out after %.1fs; continuing without RAG.", GEMINI_RAG_TIMEOUT_SECONDS)
        return ""
    except Exception as exc:
        logger.warning("RAG context failed: %s", exc)
        return ""


def _call_gemini(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    system_instruction: str | None = None,
    response_schema: dict | None = None,
) -> str | None:
    """Call the Gemini API with key rotation. Returns the text response or None on failure."""
    if not _is_configured():
        logger.warning("Gemini API key not configured.")
        return None

    # Try up to len(keys) times, rotating on rate-limit (429) errors.
    attempts = len(_valid_api_keys())
    for _ in range(attempts):
        api_key = _next_key()
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": _generation_config(temperature, max_tokens, response_schema),
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        try:
            response = _gemini_client.post(
                GEMINI_URL,
                headers={"x-goog-api-key": api_key},
                json=payload,
            )
            if response.status_code == 429:
                # Rate limited on this key, try the next one.
                logger.info("Gemini key rate-limited, rotating to next key.")
                continue
            if response.status_code == 503:
                # Model overloaded, retry with next key after short wait.
                logger.info("Gemini model overloaded (503), rotating to next key.")
                time.sleep(0.5)
                continue
            if response.status_code != 200:
                logger.warning("Gemini API returned %s: %s", response.status_code, response.text[:200])
                return None
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            return parts[0].get("text", "").strip() if parts else None
        except httpx.TimeoutException as exc:
            logger.warning("Gemini API timed out: %s", exc)
            return None
        except Exception as exc:
            logger.warning("Gemini API call failed: %s", exc)
            return None
    logger.warning("All Gemini API keys are rate-limited.")
    return None


def _parse_json_response(raw: str) -> dict | None:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = "\n".join(clean.split("\n")[1:])
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()

    try:
        parsed = json.loads(clean)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        start = clean.find("{")
        end = clean.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(clean[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


def detect_with_gemini(text: str) -> dict | None:
    """Use Gemini + RAG to detect language and register, with per-word analysis.

    Returns {language, register, explanation, ngokoPercentage, kramaPercentage, wordAnalysis} or None.
    """
    rag_context = _get_rag_context_safe(text, top_k=5)

    prompt = f"""Kamu adalah ahli linguistik bahasa daerah Indonesia yang menguasai Bahasa Indonesia, Bahasa Jawa, dan Bahasa Madura.

Analisis teks berikut dan berikan:
1. Bahasa dominan keseluruhan (Indonesia, Jawa, Madura, atau Tidak pasti)
2. Register/tingkat tutur:
   - Indonesia: "formal" atau "informal"
   - Jawa: "ngoko lugu", "ngoko alus", "krama lugu", atau "krama alus"
   - Madura: "Enja-Iya", "Engghi-enten", atau "Engghi-bhunten"
3. Persentase kesopanan: ngokoPercentage (kasual) dan kramaPercentage (sopan) yang totalnya 100
4. Analisis per-kata: untuk SETIAP kata dalam teks, tentukan bahasanya (Indonesia/Jawa/Madura/Asing) dan tingkat tuturnya (netral/ngoko/krama/halus/kasar)

Aturan keputusan bahasa:
- Tentukan bahasa keseluruhan berdasarkan persentase kata yang benar-benar teridentifikasi, bukan dari satu kata saja.
- Jika kurang dari 50% kata mendukung satu bahasa Indonesia/Jawa/Madura, gunakan language "Tidak pasti" dan register "tidak diketahui".
- Jika dua bahasa sama kuat, misalnya 50%-50%, gunakan language "Tidak pasti" dan register "ambigu".
- Jika teks dominan bahasa asing seperti Inggris, gunakan language "Tidak pasti"; jangan memaksa hasil ke Madura hanya karena satu token pendek mirip kosakata lokal.

{"Referensi kosakata dari database lokal:" if rag_context else ""}
{rag_context}

Teks yang dianalisis: "{text}"

Jawab HANYA dalam format JSON berikut (tanpa markdown, tanpa penjelasan lain):
{{
  "language": "...",
  "register": "...",
  "explanation": "...",
  "ngokoPercentage": 0.0,
  "kramaPercentage": 0.0,
  "wordAnalysis": [
    {{"word": "kata1", "language": "Jawa", "level": "krama"}},
    {{"word": "kata2", "language": "Indonesia", "level": "netral"}}
  ]
}}

Untuk explanation, jelaskan singkat dalam Bahasa Indonesia (1-2 kalimat).
ngokoPercentage + kramaPercentage harus = 100.
Untuk level per kata sesuaikan dengan konteks:
- Indonesia: gunakan "formal", "informal", atau "netral"
- Jawa: gunakan "ngoko lugu", "ngoko alus", "krama lugu", "krama alus", atau "krama inggil"
- Madura: gunakan "enja-iya", "engghi-enten", atau "engghi-bhunten"
- Asing: gunakan "netral" """

    result = _call_gemini(prompt, temperature=0.1, max_tokens=2048)
    if not result:
        logger.warning("detect_with_gemini: _call_gemini returned None")
        return None

    try:
        parsed = _parse_json_response(result)
        if not parsed:
            raise json.JSONDecodeError("No JSON object found", result, 0)
        if "language" in parsed and "register" in parsed:
            return {
                "language": parsed["language"],
                "register": parsed["register"],
                "explanation": parsed.get("explanation", "Dianalisis oleh Gemini AI."),
                "ngokoPercentage": parsed.get("ngokoPercentage", 50.0),
                "kramaPercentage": parsed.get("kramaPercentage", 50.0),
                "wordAnalysis": parsed.get("wordAnalysis", []),
            }
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("detect_with_gemini: JSON parse failed: %s | raw: %s", exc, result[:200])
    return None


TRANSLATION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "translatedText": {
            "type": "string",
            "description": "Final translated text only, preserving line breaks and punctuation where appropriate.",
        },
        "detectedSourceLanguage": {
            "type": "string",
            "description": "Detected dominant source language code: id, jv, mad, or unknown.",
        },
        "targetRegister": {
            "type": "string",
            "description": "Register actually used in the translation.",
        },
        "confidence": {
            "type": "number",
            "description": "Model confidence that the translation matches the requested language and register.",
        },
        "notes": {
            "type": "string",
            "description": "Brief Indonesian note about context, ambiguity, or fallback terms.",
        },
    },
    "required": ["translatedText", "detectedSourceLanguage", "targetRegister", "confidence", "notes"],
}

GOOGLE_TRANSLATE_CODES = {
    "id": "id",
    "jv": "jv",
}


def _cache_get(cache_key: tuple[str, str, str, str]) -> str | None:
    with _translation_cache_lock:
        return _translation_cache.get(cache_key)


def _cache_set(cache_key: tuple[str, str, str, str], value: str) -> None:
    with _translation_cache_lock:
        if len(_translation_cache) >= 256:
            _translation_cache.pop(next(iter(_translation_cache)))
        _translation_cache[cache_key] = value


def _valid_translation_output(source_text: str, translated: str) -> bool:
    translated = translated.strip()
    if not translated:
        return False
    if translated.startswith("{") and translated.endswith("}"):
        return False
    source_len = max(len(source_text.strip()), 1)
    return len(translated) <= max(source_len * 6, 120)


def _translation_system_instruction() -> str:
    return """Kamu adalah penerjemah profesional Bahasa Indonesia, Bahasa Jawa, dan Bahasa Madura.

Prinsip kerja:
- Terjemahkan berdasarkan makna kalimat/paragraf utuh, bukan padanan kata per kata.
- Analisis imbuhan, reduplikasi, frasa idiomatik, subjek-objek, dan alur kalimat sebelum memilih padanan.
- Pertahankan maksud, nada, tanda baca, baris baru, nama orang/tempat, angka, dan istilah yang memang tidak perlu diterjemahkan.
- Untuk Bahasa Jawa, patuhi register target: Ngoko untuk kasual, Krama/Krama Alus untuk sopan.
- Untuk Bahasa Madura, patuhi register target: Enja-Iya untuk kasual, Engghi-Bhanten untuk sopan.
- Dalam konteks lokasi, frasa Indonesia "di jalan" ke Jawa Krama adalah "wonten teng dalan" dan ke Ngoko adalah "neng dalan"; jangan menerjemahkan "jalan" sebagai verba "mlampah/mlaku" dalam konteks ini.
- Jika ada referensi kamus lokal, gunakan sebagai panduan terminologi, tetapi jangan memaksakan padanan jika merusak konteks kalimat.
- Jangan menambahkan penjelasan di dalam translatedText."""


def _translation_prompt(
    text: str,
    source_lang: str,
    target_lang: str,
    level: str,
    rag_context: str,
) -> str:
    src_name = LANG_NAMES.get(source_lang, source_lang)
    tgt_name = LANG_NAMES.get(target_lang, target_lang)
    level_desc = LEVEL_DESCRIPTIONS.get(level, {}).get(target_lang, "netral")
    glossary = f"\nReferensi kamus lokal yang relevan:\n{rag_context}\n" if rag_context else ""
    return f"""Terjemahkan input berikut.

Source language: {src_name} ({source_lang})
Target language: {tgt_name} ({target_lang})
Target register: {level_desc}

{glossary}
Input:
<<<
{text}
>>>

Output wajib berupa JSON sesuai schema. translatedText harus hanya berisi hasil terjemahan akhir."""


def _translate_with_gemini_structured(
    text: str,
    source_lang: str,
    target_lang: str,
    level: str,
    rag_context: str,
) -> dict | None:
    prompt = _translation_prompt(text, source_lang, target_lang, level, rag_context)
    max_tokens = min(2048, max(256, len(text) // 2 + 256))
    raw = _call_gemini(
        prompt,
        temperature=0.2,
        max_tokens=max_tokens,
        system_instruction=_translation_system_instruction(),
        response_schema=TRANSLATION_RESPONSE_SCHEMA,
    )
    if not raw:
        return None

    parsed = _parse_json_response(raw)
    if not parsed:
        logger.warning("Gemini structured translation did not return JSON: %s", raw[:200])
        return None

    translated = str(parsed.get("translatedText", "")).strip()
    if not _valid_translation_output(text, translated):
        logger.warning("Gemini structured translation failed validation: %s", translated[:200])
        return None

    return {
        "translatedText": translated,
        "provider": "gemini",
        "confidence": float(parsed.get("confidence", 0.0) or 0.0),
        "notes": str(parsed.get("notes", "")).strip(),
        "targetRegister": str(parsed.get("targetRegister", "")).strip(),
    }


def _translate_with_gemini_plain(
    text: str,
    source_lang: str,
    target_lang: str,
    level: str,
    rag_context: str,
) -> str | None:
    src_name = LANG_NAMES.get(source_lang, source_lang)
    tgt_name = LANG_NAMES.get(target_lang, target_lang)
    level_desc = LEVEL_DESCRIPTIONS.get(level, {}).get(target_lang, "")

    prompt = f"""Kamu adalah penerjemah bahasa daerah Indonesia yang ahli dalam Bahasa Jawa dan Bahasa Madura.

Terjemahkan teks berikut dari {src_name} ke {tgt_name}.
{"Gunakan tingkat tutur: " + level_desc + "." if level_desc else ""}

{"Berikut referensi kosakata dari kamus lokal yang relevan:" if rag_context else ""}
{rag_context}

Aturan:
- Berikan HANYA hasil terjemahan, tanpa penjelasan atau komentar tambahan.
- Jangan menambahkan tanda kutip di awal/akhir.
- Pertahankan tanda baca dan kapitalisasi yang wajar.
- Gunakan referensi kamus di atas sebagai acuan utama untuk kosakata.
- Jika ada kata yang tidak bisa diterjemahkan, biarkan dalam bahasa aslinya.
- Terjemahkan makna kalimat secara utuh; jangan menerjemahkan token satu per satu jika hasilnya tidak natural.

Teks yang akan diterjemahkan:
{text}"""

    max_tokens = min(768, max(128, len(text) // 2 + 128))
    translated = _call_gemini(
        prompt,
        temperature=0.2,
        max_tokens=max_tokens,
        system_instruction=_translation_system_instruction(),
    )
    return translated.strip() if translated and _valid_translation_output(text, translated) else None


def translate_with_gemini(text: str, source_lang: str, target_lang: str, level: str) -> str | None:
    """Translate with Gemini using sentence-level context; returns only the translated text."""
    cache_key = (text.strip(), source_lang, target_lang, level)
    cached = _cache_get(cache_key)
    if cached:
        return cached

    rag_context = _get_rag_context_safe(text, target_lang=target_lang, top_k=5)
    structured = _translate_with_gemini_structured(text, source_lang, target_lang, level, rag_context)
    translated = structured["translatedText"] if structured else None
    if not translated:
        translated = _translate_with_gemini_plain(text, source_lang, target_lang, level, rag_context)
    if translated:
        _cache_set(cache_key, translated)
    return translated


def translate_with_google_translate(text: str, source_lang: str, target_lang: str) -> str | None:
    """Optional Google Translate fallback for language pairs supported by Cloud Translation."""
    if not GOOGLE_TRANSLATE_API_KEY:
        return None
    source_code = GOOGLE_TRANSLATE_CODES.get(source_lang)
    target_code = GOOGLE_TRANSLATE_CODES.get(target_lang)
    if not source_code or not target_code or source_code == target_code:
        return None

    payload = {
        "q": text,
        "source": source_code,
        "target": target_code,
        "format": "text",
    }
    if GOOGLE_TRANSLATE_MODEL:
        payload["model"] = GOOGLE_TRANSLATE_MODEL
    try:
        response = _gemini_client.post(
            GOOGLE_TRANSLATE_URL,
            params={"key": GOOGLE_TRANSLATE_API_KEY},
            json=payload,
        )
        if response.status_code != 200:
            logger.warning("Google Translate returned %s: %s", response.status_code, response.text[:200])
            return None
        data = response.json()
        translations = data.get("data", {}).get("translations", [])
        if not translations:
            return None
        translated = html.unescape(str(translations[0].get("translatedText", "")).strip())
        return translated if _valid_translation_output(text, translated) else None
    except httpx.TimeoutException as exc:
        logger.warning("Google Translate timed out: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Google Translate failed: %s", exc)
        return None


def translate_with_context_api(
    text: str,
    source_lang: str,
    target_lang: str,
    level: str,
) -> dict | None:
    """API-first translation chain: Gemini, Google Translate, then caller fallback."""
    cache_key = (text.strip(), source_lang, target_lang, level)
    cached = _cache_get(cache_key)
    if cached:
        return {"translatedText": cached, "provider": "cache", "confidence": 1.0, "notes": "Dari cache terjemahan API."}

    rag_context = _get_rag_context_safe(text, target_lang=target_lang, top_k=5)
    gemini_result = _translate_with_gemini_structured(text, source_lang, target_lang, level, rag_context)
    if gemini_result:
        _cache_set(cache_key, gemini_result["translatedText"])
        return gemini_result

    plain = _translate_with_gemini_plain(text, source_lang, target_lang, level, rag_context)
    if plain:
        _cache_set(cache_key, plain)
        return {
            "translatedText": plain,
            "provider": "gemini",
            "confidence": 0.75,
            "notes": "Gemini fallback non-JSON digunakan setelah structured output gagal.",
        }

    google_result = translate_with_google_translate(text, source_lang, target_lang)
    if google_result:
        _cache_set(cache_key, google_result)
        return {
            "translatedText": google_result,
            "provider": "google_translate",
            "confidence": 0.65,
            "notes": "Google Translate digunakan sebagai fallback API; tingkat tutur regional mungkin tidak sepresisi Gemini.",
        }

    return None


# --- Chatbot ---

CHATBOT_SYSTEM_PROMPT = """Kamu adalah Lokalator AI, asisten cerdas untuk pelestarian bahasa daerah Indonesia. Kamu fasih berbahasa Indonesia, Jawa (Ngoko & Krama), dan Madura (Enja-Iya & Engghi-Bhanten).

Kemampuanmu:
- Menjawab pertanyaan tentang budaya Jawa dan Madura
- Berbicara dalam Bahasa Jawa (Ngoko maupun Krama) dan Bahasa Madura
- Menjelaskan perbedaan tingkat tutur dan kapan harus menggunakannya
- Membantu belajar kosakata dan tata bahasa daerah
- Menerjemahkan kalimat jika diminta
- Menjelaskan konteks budaya di balik ungkapan-ungkapan daerah

Panduan:
- Jika pengguna berbicara dalam Bahasa Jawa, jawab dalam Bahasa Jawa (sesuaikan tingkat tuturnya).
- Jika pengguna berbicara dalam Bahasa Madura, jawab dalam Bahasa Madura.
- Jika pengguna berbicara Indonesia, jawab dalam Bahasa Indonesia.
- Selalu ramah, informatif, dan mendukung pelestarian bahasa daerah.
- Jawaban singkat dan padat, tidak perlu terlalu panjang kecuali diminta.

BATASAN PENTING:
- Kamu HANYA boleh membahas topik seputar Bahasa Indonesia, Bahasa Jawa, dan Bahasa Madura.
- Termasuk: kosakata, tata bahasa, budaya Jawa/Madura, tradisi, sastra daerah, tingkat tutur, terjemahan, dan pembelajaran bahasa.
- TOLAK SECARA TEGAS permintaan untuk membuat kode pemrograman (coding), hal tidak senonoh (NSFW), atau ujaran kebencian.
- Jika pengguna bertanya di luar topik tersebut (misalnya politik, teknologi umum, matematika, dll), tolak dengan sopan dan arahkan kembali ke topik bahasa/budaya daerah.
- Contoh penolakan: "Maaf, saya hanya bisa membantu seputar Bahasa Indonesia, Jawa, dan Madura beserta budayanya. Ada yang ingin Anda tanyakan tentang bahasa daerah?" """


def chat_with_gemini(message: str, history: list[dict] | None = None) -> str | None:
    """Chat with Gemini using RAG context. History is a list of {role, text} dicts.

    Returns the assistant response or None if unavailable.
    """
    if not _is_configured():
        return None

    # RAG is optional because embedding retrieval is too slow for interactive chat on
    # small local machines unless the index/model is already warm.
    rag_context = _get_rag_context_safe(message, top_k=5)

    # Build the conversation contents for Gemini API.
    contents = []

    # System instruction with RAG context
    system_with_rag = CHATBOT_SYSTEM_PROMPT
    if rag_context:
        system_with_rag += f"\n\nBerikut referensi kosakata/kalimat dari database bahasa daerah yang relevan dengan pertanyaan pengguna:\n{rag_context}\n\nGunakan referensi di atas untuk menjawab dengan akurat."

    contents.append({
        "role": "user",
        "parts": [{"text": system_with_rag}]
    })
    contents.append({
        "role": "model",
        "parts": [{"text": "Baik, saya Lokalator AI. Saya siap membantu Anda dengan bahasa Jawa dan Madura. Silakan bertanya atau berbicara dalam bahasa apapun — Indonesia, Jawa, atau Madura."}]
    })

    # Append conversation history.
    if history:
        for msg in history[-6:]:  # Keep the prompt small for lower latency.
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["text"]}]})

    # Append current message.
    contents.append({"role": "user", "parts": [{"text": message}]})

    payload = {
        "contents": contents,
        "generationConfig": _generation_config(0.7, 768),
    }

    attempts = len(_valid_api_keys())
    for _ in range(attempts):
        api_key = _next_key()
        try:
            response = _gemini_client.post(
                GEMINI_URL,
                params={"key": api_key},
                json=payload,
            )
            if response.status_code == 429:
                logger.info("Gemini chat key rate-limited, rotating.")
                continue
            if response.status_code == 503:
                logger.info("Gemini chat model overloaded (503), rotating.")
                time.sleep(0.5)
                continue
            if response.status_code != 200:
                logger.warning("Gemini chat returned %s: %s", response.status_code, response.text[:200])
                return None
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            return parts[0].get("text", "").strip() if parts else None
        except httpx.TimeoutException as exc:
            logger.warning("Gemini chat timed out: %s", exc)
            return None
        except Exception as exc:
            logger.warning("Gemini chat failed: %s", exc)
            return None
    logger.warning("All Gemini API keys rate-limited for chat.")
    return None
