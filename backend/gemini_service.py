# HeritageGuard Gemini AI Service
# Provides LLM-powered translation fallback and chatbot functionality.

import os
import logging
import httpx

logger = logging.getLogger("heritageguard.gemini")

GEMINI_API_KEYS: list[str] = [
    k.strip() for k in os.getenv("GEMINI_API_KEYS", 
    "AIzaSyA_placeholder1,AIzaSyB_placeholder2,AIzaSyC_placeholder3" # key
    ).split(",")
    if k.strip()
]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
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
    if not GEMINI_API_KEYS:
        return False
    first = GEMINI_API_KEYS[0]
    return first and "placeholder" not in first.lower() and "YOUR_" not in first


def _call_gemini(prompt: str, temperature: float = 0.3, max_tokens: int = 1024) -> str | None:
    """Call the Gemini API with key rotation. Returns the text response or None on failure."""
    if not _is_configured():
        logger.warning("Gemini API key not configured.")
        return None

    # Try up to len(keys) times, rotating on rate-limit (429) errors.
    attempts = len(GEMINI_API_KEYS)
    for _ in range(attempts):
        api_key = _next_key()
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        try:
            response = httpx.post(
                GEMINI_URL,
                params={"key": api_key},
                json=payload,
                timeout=120.0,
            )
            if response.status_code == 429:
                # Rate limited on this key, try the next one.
                logger.info("Gemini key rate-limited, rotating to next key.")
                continue
            if response.status_code == 503:
                # Model overloaded, retry with next key after short wait.
                logger.info("Gemini model overloaded (503), rotating to next key.")
                import time
                time.sleep(1)
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


def detect_with_gemini(text: str) -> dict | None:
    """Use Gemini + RAG to detect language and register, with per-word analysis.

    Returns {language, register, explanation, ngokoPercentage, kramaPercentage, wordAnalysis} or None.
    """
    rag_context = ""
    try:
        from .rag_service import get_rag_context
        rag_context = get_rag_context(text, top_k=8)
    except Exception:
        pass

    prompt = f"""Kamu adalah ahli linguistik bahasa daerah Indonesia yang menguasai Bahasa Indonesia, Bahasa Jawa, dan Bahasa Madura.

Analisis teks berikut dan berikan:
1. Bahasa dominan keseluruhan (Indonesia, Jawa, Madura)
2. Register/tingkat tutur:
   - Indonesia: "formal" atau "informal"
   - Jawa: "ngoko lugu", "ngoko alus", "krama lugu", atau "krama alus"
   - Madura: "Enja-Iya", "Engghi-enten", atau "Engghi-bhunten"
3. Persentase kesopanan: ngokoPercentage (kasual) dan kramaPercentage (sopan) yang totalnya 100
4. Analisis per-kata: untuk SETIAP kata dalam teks, tentukan bahasanya (Indonesia/Jawa/Madura/Asing) dan tingkat tuturnya (netral/ngoko/krama/halus/kasar)

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
Untuk level per kata: gunakan "netral" untuk Indonesia/Asing, "ngoko"/"krama"/"krama inggil" untuk Jawa, "enja-iya"/"engghi-bhunten" untuk Madura."""

    result = _call_gemini(prompt, temperature=0.1, max_tokens=4096)
    if not result:
        logger.warning("detect_with_gemini: _call_gemini returned None")
        return None

    try:
        import json
        clean = result.strip()
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:])
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        parsed = json.loads(clean)
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


def translate_with_gemini(text: str, source_lang: str, target_lang: str, level: str) -> str | None:
    """Use Gemini to translate text when the rule-based engine can't handle it.

    Uses RAG to ground the translation in our local dictionary data.
    Returns translated text or None if Gemini is unavailable/failed.
    """
    src_name = LANG_NAMES.get(source_lang, source_lang)
    tgt_name = LANG_NAMES.get(target_lang, target_lang)
    level_desc = LEVEL_DESCRIPTIONS.get(level, {}).get(target_lang, "")

    # RAG: retrieve relevant dictionary entries to ground the translation
    rag_context = ""
    try:
        from .rag_service import get_rag_context
        rag_context = get_rag_context(text, target_lang=target_lang, top_k=10)
    except Exception:
        pass

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
    """Chat with Gemini using RAG context. History is a list of {role, text} dicts.

    Returns the assistant response or None if unavailable.
    """
    if not _is_configured():
        return None

    # RAG: retrieve relevant context based on user message
    rag_context = ""
    try:
        from .rag_service import get_rag_context
        rag_context = get_rag_context(message, top_k=8)
    except Exception:
        pass

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

    attempts = len(GEMINI_API_KEYS)
    for _ in range(attempts):
        api_key = _next_key()
        try:
            response = httpx.post(
                GEMINI_URL,
                params={"key": api_key},
                json=payload,
                timeout=120.0,
            )
            if response.status_code == 429:
                logger.info("Gemini chat key rate-limited, rotating.")
                continue
            if response.status_code == 503:
                logger.info("Gemini chat model overloaded (503), rotating.")
                import time
                time.sleep(1)
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
