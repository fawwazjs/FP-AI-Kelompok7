# HeritageGuard Gemini AI Service
# Provides LLM-powered translation fallback and chatbot functionality.

import os
import logging
import httpx

logger = logging.getLogger("heritageguard.gemini")

GEMINI_API_KEYS: list[str] = [
    k.strip() for k in os.getenv("GEMINI_API_KEYS", "YOUR_GEMINI_API_KEY_HERE").split(",")
    if k.strip()
]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# Round-robin counter for key rotation.
_key_index = 0
_key_lock = __import__("threading").Lock()


def _next_key() -> str:
    """Get the next API key in round-robin fashion."""
    global _key_index
    with _key_lock:
        key = GEMINI_API_KEYS[_key_index % len(GEMINI_API_KEYS)]
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
    return bool(GEMINI_API_KEYS) and GEMINI_API_KEYS[0] != "YOUR_GEMINI_API_KEY_HERE"


def _call_gemini(prompt: str, temperature: float = 0.3) -> str | None:
    """Call the Gemini API with key rotation. Returns the text response or None on failure."""
    if not _is_configured():
        logger.warning("Gemini API key not configured.")
        return None

    # Try up to len(keys) times, rotating on rate-limit (429) errors.
    attempts = min(len(GEMINI_API_KEYS), 5)
    for _ in range(attempts):
        api_key = _next_key()
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024,
            },
        }

        try:
            response = httpx.post(
                GEMINI_URL,
                params={"key": api_key},
                json=payload,
                timeout=30.0,
            )
            if response.status_code == 429:
                # Rate limited on this key, try the next one.
                logger.info("Gemini key rate-limited, rotating to next key.")
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
        except Exception as exc:
            logger.warning("Gemini API call failed: %s", exc)
            return None
    logger.warning("All Gemini API keys are rate-limited.")
    return None


def translate_with_gemini(text: str, source_lang: str, target_lang: str, level: str) -> str | None:
    """Use Gemini to translate text when the rule-based engine can't handle it.

    Returns translated text or None if Gemini is unavailable/failed.
    """
    src_name = LANG_NAMES.get(source_lang, source_lang)
    tgt_name = LANG_NAMES.get(target_lang, target_lang)
    level_desc = LEVEL_DESCRIPTIONS.get(level, {}).get(target_lang, "")

    prompt = f"""Kamu adalah penerjemah bahasa daerah Indonesia yang ahli dalam Bahasa Jawa dan Bahasa Madura.

Terjemahkan teks berikut dari {src_name} ke {tgt_name}.
{"Gunakan tingkat tutur: " + level_desc + "." if level_desc else ""}

Aturan:
- Berikan HANYA hasil terjemahan, tanpa penjelasan atau komentar tambahan.
- Jangan menambahkan tanda kutip di awal/akhir.
- Pertahankan tanda baca dan kapitalisasi yang wajar.
- Jika ada kata yang tidak bisa diterjemahkan, biarkan dalam bahasa aslinya.

Teks yang akan diterjemahkan:
{text}"""

    return _call_gemini(prompt, temperature=0.2)


# --- Chatbot ---

CHATBOT_SYSTEM_PROMPT = """Kamu adalah HeritageGuard AI, asisten cerdas untuk pelestarian bahasa daerah Indonesia. Kamu fasih berbahasa Indonesia, Jawa (Ngoko & Krama), dan Madura (Enja-Iya & Engghi-Bhanten).

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
- Jawaban singkat dan padat, tidak perlu terlalu panjang kecuali diminta."""


def chat_with_gemini(message: str, history: list[dict] | None = None) -> str | None:
    """Chat with Gemini. History is a list of {role, text} dicts.

    Returns the assistant response or None if unavailable.
    """
    if not _is_configured():
        return None

    # Build the conversation contents for Gemini API.
    contents = []

    # System instruction as the first user turn (Gemini doesn't have a system role in contents).
    contents.append({
        "role": "user",
        "parts": [{"text": CHATBOT_SYSTEM_PROMPT}]
    })
    contents.append({
        "role": "model",
        "parts": [{"text": "Baik, saya HeritageGuard AI. Saya siap membantu Anda dengan bahasa Jawa dan Madura. Silakan bertanya atau berbicara dalam bahasa apapun — Indonesia, Jawa, atau Madura."}]
    })

    # Append conversation history.
    if history:
        for msg in history[-10:]:  # Keep last 10 messages for context window
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["text"]}]})

    # Append current message.
    contents.append({"role": "user", "parts": [{"text": message}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        },
    }

    attempts = min(len(GEMINI_API_KEYS), 5)
    for _ in range(attempts):
        api_key = _next_key()
        try:
            response = httpx.post(
                GEMINI_URL,
                params={"key": api_key},
                json=payload,
                timeout=30.0,
            )
            if response.status_code == 429:
                logger.info("Gemini chat key rate-limited, rotating.")
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
        except Exception as exc:
            logger.warning("Gemini chat failed: %s", exc)
            return None
    logger.warning("All Gemini API keys rate-limited for chat.")
    return None
