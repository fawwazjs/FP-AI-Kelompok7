# Lokalator AI Translator and Politeness Service
# Simulates MarianMT, IndoBERT, and Random Forest Classifier outputs.

import re
import os
import json
import unicodedata
import csv
from collections import Counter
from pathlib import Path

SUPPORTED_LANGUAGES = {"id", "jv", "mad"}
SUPPORTED_LEVELS = {"low", "high"}

BASE_DIR = Path(__file__).resolve().parents[1]

def _dataset_path(*parts: str) -> Path:
    return BASE_DIR.joinpath(*parts)

def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))

def _normalize_text_key(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace("’", "'")
    text = re.sub(r"[\[\]{}()\"“”]", " ", text)
    text = re.sub(r"[^\w\s'\-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _key_variants(text: str) -> set[str]:
    base = _normalize_text_key(text)
    plain = _normalize_text_key(_strip_accents(text))
    return {v for v in (base, plain) if v}

def _clean_dataset_value(value) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    if not value or value.lower() == "none":
        return ""
    value = re.sub(r"\s+", " ", value)
    return value.lower()

def _word_count(text: str) -> int:
    normalized = _normalize_text_key(text)
    return len(normalized.split()) if normalized else 0

# Phrase-level exact translation database
PHRASES_DB = {
    'id_jv': {
        'saya ingin makan nasi goreng': {
            'high': 'Kula kersa dhahar sekul goreng.',
            'low': 'Aku pengen mangan sego goreng.',
            'context': 'Krama Alus (Sopan) digunakan untuk berbicara dengan orang tua/dihormati. Ngoko Lugu (Kasual) untuk teman sebaya.'
        },
        'kamu mau pergi ke mana': {
            'high': 'Panjenengan badhe tindak dhateng pundi?',
            'low': 'Kowe arep lungo nang endi?',
            'context': 'Tingkat Krama menggunakan kata "Panjenengan" dan "Tindak" untuk menghormati lawan bicara.'
        },
        'terima kasih banyak atas bantuannya': {
            'high': 'Matur nuwun sanget saking pitulunganipun.',
            'low': 'Matur nuwun banget kanggo bantuane.',
            'context': 'Kata "sanget" (sangat) dan "pitulunganipun" (bantuannya) mencerminkan kesopanan tingkat tinggi.'
        },
        'selamat pagi bagaimana kabar anda': {
            'high': 'Sugeng enjang, kadospundi kabar panjenengan?',
            'low': 'Sugeng enjing, piye kabarmu?',
            'context': 'Sapaan formal menggunakan "Sugeng enjang" dan menanyakan kabar dengan "kadospundi".'
        },
        'nama saya ahmad saya tinggal di surabaya': {
            'high': 'Nami kula Ahmad, kula dalem ing Surabaya.',
            'low': 'Jenengku Ahmad, aku manggon ing Surabaya.',
            'context': 'Menyebut diri sendiri di tingkat Krama menggunakan kata "Nami" (nama) dan "Dalem/Manggen" (tinggal).'
        },
        'aku sedang di jalan': {
            'high': 'Kula wonten teng dalan',
            'low': 'Aku neng dalan',
            'context': 'Frasa "di jalan" dibaca sebagai keterangan tempat, bukan verba "berjalan".'
        },
        'saya sedang di jalan': {
            'high': 'Kula wonten teng dalan',
            'low': 'Aku neng dalan',
            'context': 'Frasa "di jalan" dibaca sebagai keterangan tempat, bukan verba "berjalan".'
        },
        'aku di jalan': {
            'high': 'Kula wonten teng dalan',
            'low': 'Aku neng dalan',
            'context': 'Frasa "di jalan" dibaca sebagai keterangan tempat, bukan verba "berjalan".'
        },
        'saya di jalan': {
            'high': 'Kula wonten teng dalan',
            'low': 'Aku neng dalan',
            'context': 'Frasa "di jalan" dibaca sebagai keterangan tempat, bukan verba "berjalan".'
        }
    },
    'id_mad': {
        'saya ingin makan nasi goreng': {
            'high': 'Bhiula terro neddha\'a nase\' goreng.',
            'low': 'Sengko\' terro ngakana nase\' goreng.',
            'context': 'Engghi-Bhanten menggunakan subjek "Bhiula" dan verba "neddha". Enja-Iya menggunakan "Sengko\'" dan "ngakan".'
        },
        'kamu mau pergi ke mana': {
            'high': 'Panjhenengngan badhi alomampaha ka dhimma?',
            'low': 'Ba\'na terro entarra ka dhimma?',
            'context': 'Tingkat halus (Engghi-Bhanten) memakai kata "Panjhenengngan" dan verba halus "alomampah".'
        },
        'terima kasih banyak atas bantuannya': {
            'high': 'Mator sakalangkong sanget saking bantoan panjhenengngan.',
            'low': 'Sakalangkong raje saking bantoanna.',
            'context': '"Sakalangkong" adalah frasa khas Madurese untuk berterima kasih. Penambahan "mator" menambah kesopanan.'
        },
        'selamat pagi bagaimana kabar anda': {
            'high': 'Salamat pagi, kadospundi kabar panjhenengngan?',
            'low': 'Salamat pagi, de\'remmah kabarra?',
            'context': 'Menanyakan kabar secara kasual menggunakan kata "de\'remmah". Secara formal memakai "kadospundi".'
        },
        'nama saya ahmad saya tinggal di surabaya': {
            'high': 'Nyama bhiula Ahmad, bhiula nengghu e Surabaya.',
            'low': 'Nyama sengko\' Ahmad, sengko\' nyonggheng e Surabaya.',
            'context': '"Nengghu" adalah bentuk halus Madura untuk tinggal/berkediaman, sedangkan "nyonggheng" bernada kasual.'
        }
    }
}

# Word Dictionaries
ID_TO_JV = {
    'saya': { 'high': 'kula', 'low': 'aku' },
    'kamu': { 'high': 'panjenengan', 'low': 'kowe' },
    'dia': { 'high': 'piyambakipun', 'low': 'dheweke' },
    'ingin': { 'high': 'badhe', 'low': 'pengen' },
    'makan': { 'high': 'dhahar', 'low': 'mangan' },
    'makanan': { 'high': 'dhaharan', 'low': 'panganan' },
    'nasi': { 'high': 'sekul', 'low': 'sego' },
    'minum': { 'high': 'ngunjuk', 'low': 'ngombe' },
    'tidur': { 'high': 'sare', 'low': 'turu' },
    'pergi': { 'high': 'tindak', 'low': 'lunga' },
    'ke': { 'high': 'dhateng', 'low': 'nang' },
    'mana': { 'high': 'pundi', 'low': 'endi' },
    'sini': { 'high': 'mriki', 'low': 'kene' },
    'sana': { 'high': 'mrika', 'low': 'kono' },
    'apa': { 'high': 'punapa', 'low': 'opo' },
    'siapa': { 'high': 'sinten', 'low': 'sopo' },
    'bagaimana': { 'high': 'kadospundi', 'low': 'piye' },
    'mengapa': { 'high': 'punapa amargi', 'low': 'kenopo' },
    'rumah': { 'high': 'griya', 'low': 'omah' },
    'air': { 'high': 'toya', 'low': 'banyu' },
    'jalan': { 'high': 'mlampah', 'low': 'mlaku' },
    'sekarang': { 'high': 'sakmenika', 'low': 'saiki' },
    'tidak': { 'high': 'mboten', 'low': 'ora' },
    'ya': { 'high': 'inggih', 'low': 'iyo' },
    'baik': { 'high': 'sae', 'low': 'apik' },
    'banyak': { 'high': 'kathah', 'low': 'akeh' },
    'sedikit': { 'high': 'sekedhik', 'low': 'sithik' },
    'besar': { 'high': 'ageng', 'low': 'gede' },
    'kecil': { 'high': 'alit', 'low': 'cilik' },
    'tua': { 'high': 'sepuh', 'low': 'tuwo' },
    'sangat': { 'high': 'sanget', 'low': 'banget' },
    'dari': { 'high': 'saking', 'low': 'soko' },
    'dan': { 'high': 'kaliyan', 'low': 'lan' },
    'dengan': { 'high': 'kaliyan', 'low': 'karo' },
    'bisa': { 'high': 'saged', 'low': 'iso' },
    'cara': { 'high': 'cara', 'low': 'cara' },
    'laku': { 'high': 'tindak', 'low': 'laku' },
    'memperlakukan': { 'high': 'nindakaken', 'low': 'nglakoni' },
    'perlakukan': { 'high': 'nindakaken', 'low': 'nglakoni' },
}

ID_TO_MAD = {
    'saya': { 'high': 'bhiula', 'low': 'sengko\'' },
    'kamu': { 'high': 'panjhenengngan', 'low': 'ba\'na' },
    'dia': { 'high': 'dhibi\'na', 'low': 'dhibi\'na' },
    'ingin': { 'high': 'terro', 'low': 'terro' },
    'makan': { 'high': 'neddha', 'low': 'ngakan' },
    'nasi': { 'high': 'nase\'', 'low': 'nase\'' },
    'minum': { 'high': 'ngonjhung', 'low': 'ngenom' },
    'tidur': { 'high': 'asera', 'low': 'tedhung' },
    'pergi': { 'high': 'alomampah', 'low': 'entar' },
    'ke': { 'high': 'ka', 'low': 'ka' },
    'mana': { 'high': 'dhimma', 'low': 'dhimma' },
    'sini': { 'high': 'enna\'', 'low': 'enna\'' },
    'sana': { 'high': 'issa\'', 'low': 'issa\'' },
    'apa': { 'high': 'punapa', 'low': 'apa' },
    'siapa': { 'high': 'sinten', 'low': 'sapa' },
    'bagaimana': { 'high': 'kadospundi', 'low': 'de\'remmah' },
    'mengapa': { 'high': 'anapo', 'low': 'anapo' },
    'rumah': { 'high': 'dalem', 'low': 'roma' },
    'air': { 'high': 'toya', 'low': 'aeng' },
    'jalan': { 'high': 'ajalan', 'low': 'ajalan' },
    'sekarang': { 'high': 'sateya', 'low': 'sateya' },
    'tidak': { 'high': 'bhanten', 'low': 'enja\'' },
    'ya': { 'high': 'engghi', 'low': 'iya' },
    'baik': { 'high': 'sae', 'low': 'bagus' },
    'banyak': { 'high': 'banya\'', 'low': 'banya\'' },
    'sedikit': { 'high': 'sakone\'', 'low': 'sakone\'' },
    'besar': { 'high': 'ageng', 'low': 'raje' },
    'kecil': { 'high': 'alit', 'low': 'kene\'' },
    'tua': { 'high': 'sepuh', 'low': 'towa' },
    'sangat': { 'high': 'ongghu', 'low': 'ongghu' },
    'dari': { 'high': 'saking', 'low': 'dhari' },
    'dan': { 'high': 'sareng', 'low': 'ban' },
    'dengan': { 'high': 'sareng', 'low': 'ban' },
    'bisa': { 'high': 'saged', 'low': 'bisa' },
    'cara': { 'high': 'cara', 'low': 'cara' },
}

def _register_phrase(pair_key: str, source_text: str, high: str, low: str, context: str):
    phrase_bucket = PHRASES_DB.setdefault(pair_key, {})
    for key in _key_variants(source_text):
        phrase_bucket.setdefault(key, {
            "high": high,
            "low": low,
            "context": context
        })

def _load_javanese_dataset():
    json_path = _dataset_path("Dataset", "ngoko_krama.json")
    if not json_path.exists():
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            ngoko_krama = json.load(f)
    except Exception:
        return

    for rec in ngoko_krama.get("employees", {}).values():
        indo = _clean_dataset_value(rec.get("indonesia"))
        ngoko = _clean_dataset_value(rec.get("ngoko"))
        krama_lugu = _clean_dataset_value(rec.get("kramaalus"))
        krama_inggil = _clean_dataset_value(rec.get("kramainggil"))
        high = krama_inggil or krama_lugu
        low = ngoko or high

        if not indo or not high or not low:
            continue

        if _word_count(indo) <= 5:
            _register_phrase(
                "id_jv",
                indo,
                high,
                low,
                "Entri berasal dari dataset ngoko-krama lokal; gunakan ragam tinggi untuk konteks hormat dan ragam rendah untuk percakapan akrab."
            )

        if _word_count(indo) == 1 and _word_count(high) <= 3 and _word_count(low) <= 3:
            for key in _key_variants(indo):
                ID_TO_JV.setdefault(key, {"high": high, "low": low})

def _clean_madura_sentence(value: str) -> str:
    value = value.replace("\\'", "'")
    value = re.sub(r"\{[^}]*\}", " ", value)
    value = re.sub(r"\[[^\]]*\]", " ", value)
    value = re.sub(r"\b(n|v|adv|pron|p|num)\.", " ", value, flags=re.IGNORECASE)
    value = value.split(";", 1)[0].split(",", 1)[0]
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[.!?]+$", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value.lower()

def _looks_like_short_phrase(value: str) -> bool:
    if not value or _word_count(value) > 5:
        return False
    return bool(re.fullmatch(r"[\w\s'\-̀-ỹ]+", value, flags=re.UNICODE))

def _load_madura_sentence_pairs(limit: int = 3000):
    sql_path = _dataset_path("Dataset", "madura.sql")
    if not sql_path.exists():
        return

    row_re = re.compile(r"\((\d+),\s*'((?:[^'\\]|\\.)*)',\s*'((?:[^'\\]|\\.)*)',\s*(\d+),\s*(\d+),\s*(NULL|'(?:[^'\\]|\\.)*')\)")
    pending_mad: dict[tuple[str, str], str] = {}
    loaded = 0

    try:
        with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
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
                sentence = match.group(3)
                pair_key = (match.group(5), match.group(4))

                if lang == "MAD":
                    pending_mad[pair_key] = sentence
                    continue

                if lang != "IND" or pair_key not in pending_mad:
                    continue

                mad = _clean_madura_sentence(pending_mad[pair_key])
                indo = _clean_madura_sentence(sentence)
                if not _looks_like_short_phrase(mad) or not _looks_like_short_phrase(indo):
                    continue

                _register_phrase(
                    "id_mad",
                    indo,
                    mad,
                    mad,
                    "Entri berasal dari pasangan kalimat kamus Madura lokal. Tingkat tutur tidak selalu tersedia, sehingga output digunakan sebagai padanan leksikal."
                )

                if _word_count(indo) == 1 and _word_count(mad) <= 3:
                    for key in _key_variants(indo):
                        ID_TO_MAD.setdefault(key, {"high": mad, "low": mad})

                loaded += 1
                if loaded >= limit:
                    break
    except Exception:
        return

_load_javanese_dataset()
_load_madura_sentence_pairs()

# Reverse lists for target -> source translations
REV_JV = {}
REV_MAD = {}
for w, val in ID_TO_JV.items():
    for key in _key_variants(val['high']):
        REV_JV.setdefault(key, w)
    for key in _key_variants(val['low']):
        REV_JV.setdefault(key, w)
for w, val in ID_TO_MAD.items():
    for key in _key_variants(val['high']):
        REV_MAD.setdefault(key, w)
    for key in _key_variants(val['low']):
        REV_MAD.setdefault(key, w)

def get_word_count(text: str):
    return _word_count(text)

def _apply_case(source_token: str, replacement: str) -> str:
    if source_token[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement

def _split_token(raw: str) -> tuple[str, str, str] | None:
    match = re.match(r"^([^\w']*)([\w'\-̀-ỹ]+)([^\w']*)$", raw, flags=re.UNICODE)
    if not match:
        return None
    return match.group(1), match.group(2), match.group(3)

def _lookup_dictionary_entry(token: str, dictionary: dict) -> dict | None:
    for token_key in _key_variants(token):
        entry = dictionary.get(token_key)
        if entry:
            return entry
    return None

def _dedupe_before_suffix(token: str, suffix: str) -> str | None:
    if not token.endswith(suffix):
        return None
    stem = token[:-len(suffix)]
    if len(stem) >= 2 and stem[-1] == stem[-2]:
        return f"{stem[:-1]}{suffix}"
    return None

def _jv_possessive(translated: str, level: str) -> str:
    if level == "high":
        suffix = "nipun" if translated[-1:].lower() in "aiueo" else "ipun"
    else:
        suffix = "ne" if translated[-1:].lower() in "aiueo" else "e"
    return f"{translated}{suffix}"

def _jv_causative(translated: str, level: str) -> str:
    if level == "high":
        return f"{translated}aken"
    if translated.endswith("u"):
        return f"{translated[:-1]}okno"
    return f"{translated}no"

def _jv_passive(base_token: str, translated: str, level: str) -> str:
    if base_token == "makan":
        return "dipundhahar" if level == "high" else "dipangan"
    if level == "high":
        return f"dipun{translated}"
    return f"di{translated}"

def _jv_locative_compound(token: str, level: str) -> tuple[str, str | None] | None:
    locative_nouns = {
        "jalan": {
            "high": ("wonten margi", "neng dalan"),
            "low": ("neng dalan", "wonten margi"),
        },
    }
    if not token.startswith("di") or len(token) <= 2:
        return None
    base = token[2:]
    entry = locative_nouns.get(base)
    if not entry:
        return None
    return entry[level]

def _translate_inflected_indonesian_token(
    token: str,
    dictionary: dict,
    level: str,
    target_lang: str,
) -> tuple[str, str | None] | None:
    normalized_candidates = [token]
    for suffix in ("nya", "kan", "kannya"):
        normalized = _dedupe_before_suffix(token, suffix)
        if normalized and normalized not in normalized_candidates:
            normalized_candidates.append(normalized)

    for normalized in normalized_candidates:
        entry = _lookup_dictionary_entry(normalized, dictionary)
        if entry:
            alt_level = "low" if level == "high" else "high"
            return entry[level], entry[alt_level] if entry[alt_level] != entry[level] else None

        if target_lang != "jv":
            continue

        if "-" in normalized:
            parts = normalized.split("-")
            if len(parts) == 2 and parts[0] == parts[1] and parts[0]:
                repeated = _translate_inflected_indonesian_token(
                    parts[0],
                    dictionary,
                    level,
                    target_lang,
                )
                if repeated:
                    translated, alternative = repeated
                    alt = f"{alternative}-{alternative}" if alternative else None
                    return f"{translated}-{translated}", alt

        locative = _jv_locative_compound(normalized, level)
        if locative:
            return locative

        if normalized.startswith("di") and len(normalized) > 2:
            base = normalized[2:]
            base_translation = _translate_inflected_indonesian_token(
                base,
                dictionary,
                level,
                target_lang,
            )
            if base_translation:
                translated, alternative = base_translation
                alt_level = "low" if level == "high" else "high"
                alt = _jv_passive(base, alternative, alt_level) if alternative else None
                return _jv_passive(base, translated, level), alt

        if normalized.endswith("nya") and len(normalized) > 3:
            base_translation = _translate_inflected_indonesian_token(
                normalized[:-3],
                dictionary,
                level,
                target_lang,
            )
            if base_translation:
                translated, alternative = base_translation
                alt = _jv_possessive(alternative, "low" if level == "high" else "high") if alternative else None
                return _jv_possessive(translated, level), alt

        if normalized.endswith("kan") and len(normalized) > 3:
            for derived in (f"men{normalized}", f"me{normalized}"):
                entry = _lookup_dictionary_entry(derived, dictionary)
                if entry:
                    alt_level = "low" if level == "high" else "high"
                    return entry[level], entry[alt_level] if entry[alt_level] != entry[level] else None

            base_entry = _lookup_dictionary_entry(normalized[:-3], dictionary)
            if base_entry:
                alt_level = "low" if level == "high" else "high"
                return (
                    _jv_causative(base_entry[level], level),
                    _jv_causative(base_entry[alt_level], alt_level),
                )

        if normalized.startswith("memper") and normalized.endswith("kan"):
            base_entry = _lookup_dictionary_entry(normalized[6:-3], dictionary)
            if base_entry:
                alt_level = "low" if level == "high" else "high"
                return (
                    _jv_causative(base_entry[level], level),
                    _jv_causative(base_entry[alt_level], alt_level),
                )

    return None

def _translate_word_by_word(text: str, dictionary: dict, level: str, target_lang: str = "jv") -> tuple[str, str | None, int]:
    translated_parts = []
    alternative_parts = []
    translated_count = 0

    for raw in re.split(r"(\s+)", text):
        if not raw or raw.isspace():
            translated_parts.append(raw)
            alternative_parts.append(raw)
            continue

        split = _split_token(raw)
        if not split:
            translated_parts.append(raw)
            alternative_parts.append(raw)
            continue

        prefix, core, suffix = split
        entry = _lookup_dictionary_entry(core, dictionary)
        inflected = None if entry else _translate_inflected_indonesian_token(core, dictionary, level, target_lang)
        if not entry and not inflected:
            translated_parts.append(raw)
            alternative_parts.append(raw)
            continue

        translated_count += 1
        if entry:
            alt_level = "low" if level == "high" else "high"
            replacement = _apply_case(core, entry[level])
            alternative = _apply_case(core, entry[alt_level])
        else:
            replacement_text, alternative_text = inflected or (core, None)
            replacement = _apply_case(core, replacement_text)
            alternative = _apply_case(core, alternative_text) if alternative_text else replacement
        translated_parts.append(f"{prefix}{replacement}{suffix}")
        alternative_parts.append(f"{prefix}{alternative}{suffix}")

    translated = "".join(translated_parts)
    alternative = "".join(alternative_parts)
    return translated, alternative if alternative != translated else None, translated_count

def _translate_reverse_word_by_word(text: str, reverse_dictionary: dict) -> tuple[str, int]:
    translated_parts = []
    translated_count = 0

    for raw in re.split(r"(\s+)", text):
        if not raw or raw.isspace():
            translated_parts.append(raw)
            continue

        split = _split_token(raw)
        if not split:
            translated_parts.append(raw)
            continue

        prefix, core, suffix = split
        replacement = None
        for token_key in _key_variants(core):
            replacement = reverse_dictionary.get(token_key)
            if replacement:
                break
        if not replacement:
            translated_parts.append(raw)
            continue

        translated_count += 1
        translated_parts.append(f"{prefix}{_apply_case(core, replacement)}{suffix}")

    return "".join(translated_parts), translated_count

def translate_and_classify(text: str, source: str, target: str, level: str) -> dict:
    source = source if source in SUPPORTED_LANGUAGES else "id"
    target = target if target in SUPPORTED_LANGUAGES else "id"
    level = level if level in SUPPORTED_LEVELS else "high"
    clean_text = _normalize_text_key(text)
    match_key = f"{source}_{target}"
    
    translated_text = ""
    politeness_level = "Netral"
    ngoko_pct = 50.0
    krama_pct = 50.0
    context = ""
    alternative = None

    # Source == Target (No Translation needed)
    if source == target:
        translated_text = text
        politeness_info = run_politeness_analysis(text, source)
        return {
            "translatedText": translated_text,
            "politenessLevel": politeness_info["level"],
            "ngokoPercentage": politeness_info["ngoko"],
            "kramaPercentage": politeness_info["krama"],
            "context": politeness_info["context"],
            "alternativeText": None
        }

    # Direct Jawa<->Madura model is not available yet; pivot through Indonesian
    # so the public API remains stable when a trained model is added later.
    if source != "id" and target != "id":
        pivot = translate_and_classify(text, source, "id", level)
        result = translate_and_classify(pivot["translatedText"], "id", target, level)
        result["context"] = (
            f"{result['context']} Terjemahan dialihkan melalui Bahasa Indonesia "
            f"karena model langsung {source}->{target} belum tersedia."
        )
        return result

    # 1. Check phrase matches (Indonesian -> Regional)
    if match_key in PHRASES_DB and clean_text in PHRASES_DB[match_key]:
        entry = PHRASES_DB[match_key][clean_text]
        translated_text = entry[level]
        alternative = entry['low'] if level == 'high' else entry['high']
        context = entry['context']
        politeness_level = "Krama Alus" if level == 'high' else "Ngoko Lugu"
        if target == 'mad':
            politeness_level = "Engghi-Bhanten" if level == 'high' else "Enja-Iya"
        ngoko_pct = 10.0 if level == 'high' else 90.0
        krama_pct = 90.0 if level == 'high' else 10.0
    
    # 2. Check phrase matches in reverse (Regional -> Indonesian)
    elif target == 'id' and f"id_{source}" in PHRASES_DB:
        reverse_db = PHRASES_DB[f"id_{source}"]
        found = False
        for id_key, val in reverse_db.items():
            high_matches = clean_text in _key_variants(val['high'])
            low_matches = clean_text in _key_variants(val['low'])
            if high_matches:
                translated_text = id_key.capitalize()
                alternative = val['low']
                politeness_level = "Krama Alus" if source == 'jv' else "Engghi-Bhanten"
                context = "Kalimat input terdeteksi menggunakan tingkat tutur formal/sopan."
                ngoko_pct = 15.0
                krama_pct = 85.0
                found = True
                break
            elif low_matches:
                translated_text = id_key.capitalize()
                alternative = val['high']
                politeness_level = "Ngoko Lugu" if source == 'jv' else "Enja-Iya"
                context = "Kalimat input terdeteksi menggunakan tingkat tutur kasual/informal."
                ngoko_pct = 85.0
                krama_pct = 15.0
                found = True
                break
        
        if not found:
            # Word-by-word reverse translation
            rev_dict = REV_JV if source == 'jv' else REV_MAD
            translated_text, translated_count = _translate_reverse_word_by_word(text, rev_dict)
            politeness_info = run_politeness_analysis(text, source)
            politeness_level = politeness_info["level"]
            ngoko_pct = politeness_info["ngoko"]
            krama_pct = politeness_info["krama"]
            context = (
                "Diterjemahkan secara literal kata-demi-kata ke Bahasa Indonesia. "
                f"Kosakata cocok: {translated_count}."
            )

    # 3. Word-by-word fallback (Indonesian -> Regional)
    else:
        dict_to_use = ID_TO_JV if target == 'jv' else ID_TO_MAD
        translated_text, alternative, translated_count = _translate_word_by_word(text, dict_to_use, level, target)
        
        is_high = level == 'high'
        politeness_level = "Krama Alus" if target == 'jv' else "Engghi-Bhanten"
        if not is_high:
            politeness_level = "Ngoko Lugu" if target == 'jv' else "Enja-Iya"
        
        ngoko_pct = 15.0 if is_high else 85.0
        krama_pct = 85.0 if is_high else 15.0
        
        if target == 'jv':
            context = "Tingkat tutur Krama Alus digunakan untuk menghormati orang tua/guru." if is_high else "Tingkat tutur Ngoko Lugu digunakan untuk teman akrab/lebih muda."
        else:
            context = "Tingkat tutur Engghi-Bhanten mencerminkan rasa hormat yang tinggi." if is_high else "Tingkat tutur Enja-Iya digunakan untuk percakapan kasual sehari-hari."
        context = f"{context} Kosakata cocok: {translated_count}."

    return {
        "translatedText": translated_text,
        "politenessLevel": politeness_level,
        "ngokoPercentage": ngoko_pct,
        "kramaPercentage": krama_pct,
        "context": context,
        "alternativeText": alternative
    }

def run_politeness_analysis(text: str, lang: str) -> dict:
    if lang == 'id':
        return {"level": "Netral", "ngoko": 0, "krama": 0, "context": "Teks menggunakan Bahasa Indonesia netral."}
    
    clean = _normalize_text_key(text)
    words = clean.split()
    
    high_count = 0
    low_count = 0
    dict_to_check = ID_TO_JV if lang == 'jv' else ID_TO_MAD

    for w in words:
        for val in dict_to_check.values():
            if w in _key_variants(val['high']):
                high_count += 1
            elif w in _key_variants(val['low']):
                low_count += 1
                
    total = high_count + low_count
    high_pct = 50.0
    low_pct = 50.0
    if total > 0:
        high_pct = round((high_count / total) * 100, 1)
        low_pct = 100.0 - high_pct
    
    if lang == 'jv':
        level = "Krama Alus" if high_pct > 70 else ("Ngoko Lugu" if low_pct > 70 else "Ngoko Alus")
        context = "Krama Alus digunakan untuk berbicara sopan kepada tetua." if high_pct > 70 else "Ngoko Lugu digunakan kepada kawan sebaya."
    else:
        level = "Engghi-Bhanten" if high_pct > 70 else ("Enja-Iya" if low_pct > 70 else "Campuran Madura")
        context = "Engghi-Bhanten digunakan saat berbicara dengan kiai/orang tua." if high_pct > 70 else "Enja-Iya digunakan untuk teman sebaya."
        
    return {
        "level": level,
        "ngoko": low_pct,
        "krama": high_pct,
        "context": context
    }

# ==========================================
# REGISTER DETECTOR IMPLEMENTATION
# ==========================================

# Vocabulary Sets
jv_ngoko = {"aku", "kowe", "arep", "mangan", "turu", "luwe", "iki", "yo", "ora", "sing", "opo", "sopo", "piye", "kene", "kono", "nopo", "sego"}
jv_krama_lugu = {"sampeyan", "nedha", "tilem", "kesah", "tenri"}
jv_krama_alus = {"kula", "badhe", "dhahar", "sare", "panjenengan", "wonten", "inggih", "mboten", "saking", "pundi", "punapa", "sinten", "kadospundi", "sekul"}
jv_kasar = {"jancok", "jancuk", "dancok", "cuk", "asu", "bajingan", "raimu", "ndasmu", "matamu", "picek"}

indo_standard = {"saya", "mau", "makan", "tidur", "anda", "kamu", "tidak", "saja", "sudah", "sedang", "mengapa", "sangat", "pergi", "di", "warung", "dekat", "keraton"}
indo_slang = {"gue", "gua", "lu", "nggak", "aja", "udah", "lagi", "kenapa", "banget", "pengen", "bobo", "mager", "bodo", "yuk", "bro", "selow", "dong", "capek", "pusing"}

mad_enja_iya = {"sengko'", "ba'na", "terro", "ngakan", "ngakana", "nase", "nase'", "tedhung", "entar", "entarra", "roma", "molea", "enja'"}
mad_engghi_enten = {"bula", "dhika", "bisaa", "abhanto"}
mad_engghi_bhunten = {"bhiula", "panjhenengngan", "badhi", "neddha", "neddha'a", "asera", "alomampah", "alomampaha", "engghi", "bhanten", "kaula'", "bhâdhân", "dada"}

# Core indicators for speech level routing
jv_ngoko_core = {'aku', 'kowe', 'arep', 'ora', 'sing', 'opo', 'sopo', 'piye', 'kene', 'kono', 'neng', 'karo', 'lan', 'dadi'}
jv_krama_core = {'kula', 'badhe', 'mboten', 'ingkang', 'punapa', 'sinten', 'kadospundi', 'mriki', 'mrika', 'dhateng', 'kaliyan', 'dados', 'panjenengan', 'sampeyan'}
jv_krama_inggil_verbs = {'dhahar', 'sare', 'tindak', 'rawuh', 'sowan', 'kersa', 'nampi', 'jumeneng', 'dalem', 'sugeng'}

mad_enja_iya_core = {"sengko'", "engko'", "ba'na", "ba'en", "terro", "ngakan", "ngakana", "nase", "nase'", "enja'"}
mad_engghi_enten_core = {"bula", "bula'", "dhika", "dhiko", "ka", "dhimma", "sampeyan"}
mad_engghi_bhunten_core = {"kaula", "kaula'", "bhâdhân", "panjhenengngan", "badhi", "alomampah", "alomampaha", "engghi", "bhanten", "bhunten", "ajunan", "srèra"}

# Lazily populate them from Dataset files if they exist
json_path = _dataset_path('Dataset', 'ngoko_krama.json')
sql_path = _dataset_path('Dataset', 'madura.sql')

if os.path.exists(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            ngoko_krama = json.load(f)
        for k, rec in ngoko_krama['employees'].items():
            n = str(rec.get('ngoko')).lower().strip()
            kl = str(rec.get('kramaalus')).lower().strip()
            ka = str(rec.get('kramainggil')).lower().strip()
            
            has_n = n and n != 'none' and n != ''
            has_kl = kl and kl != 'none' and kl != ''
            has_ka = ka and ka != 'none' and ka != ''
            
            if has_n:
                is_distinct = False
                if has_kl and n != kl:
                    is_distinct = True
                if has_ka and n != ka:
                    is_distinct = True
                if is_distinct:
                    jv_ngoko.add(n)
            if has_kl:
                jv_krama_lugu.add(kl)
            if has_ka:
                jv_krama_alus.add(ka)
        jv_ngoko = jv_ngoko - jv_krama_alus - jv_krama_lugu
    except Exception as e:
        pass

if os.path.exists(sql_path):
    try:
        row_re = re.compile(r"\((\d+),\s*'((?:[^'\\]|\\.)*)',\s*'((?:[^'\\]|\\.)*)',\s*(\d+),\s*(\d+),\s*(NULL|'(?:[^'\\]|\\.)*')\)")
        with open(sql_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line_str = line.strip()
                if not line_str.startswith('('):
                    continue
                if line_str.endswith(','): line_str = line_str[:-1]
                elif line_str.endswith(';'): line_str = line_str[:-1]
                m = row_re.match(line_str)
                if m:
                    lang = m.group(2)
                    sent = m.group(3).lower()
                    if lang == 'MAD':
                        clean_sent = re.sub(r'\{[a-z0-9,\s\.\?\-]+\}', '', sent)
                        clean_sent = re.sub(r'\[.*?\]', '', clean_sent)
                        words = [re.sub(r"[^\w']", "", w) for w in clean_sent.split() if w]
                        for w in words:
                            if not w: continue
                            if '{l}' in sent: mad_enja_iya.add(w)
                            elif '{t}' in sent: mad_engghi_enten.add(w)
                            elif '{a}' in sent or '{at}' in sent: mad_engghi_bhunten.add(w)
        mad_enja_iya = mad_enja_iya - mad_engghi_bhunten - mad_engghi_enten
    except Exception as e:
        pass

mad_neutral = set()

def _tokenize_detector_text(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).lower().replace("’", "'")
    normalized = re.sub(r"[^\w\s'\-̀-ỹ]", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.split() if normalized else []

def _detector_variants(token: str) -> set[str]:
    variants = set(_key_variants(token))
    variants.update(_key_variants(token.replace("'", "")))
    return {variant for variant in variants if variant}

def _add_tokens(target: set[str], value: str):
    for token in _tokenize_detector_text(value):
        target.update(_detector_variants(token))

def _load_detector_dictionary_terms():
    for entry in ID_TO_JV.values():
        high = entry.get("high", "")
        low = entry.get("low", "")
        if _normalize_text_key(high) == _normalize_text_key(low):
            _add_tokens(jv_ngoko, low)
        else:
            _add_tokens(jv_krama_alus, high)
            _add_tokens(jv_ngoko, low)
    for entry in ID_TO_MAD.values():
        high = entry.get("high", "")
        low = entry.get("low", "")
        if _normalize_text_key(high) == _normalize_text_key(low):
            _add_tokens(mad_enja_iya, low)
        else:
            _add_tokens(mad_engghi_bhunten, high)
            _add_tokens(mad_enja_iya, low)

def _load_madura_headword_terms():
    if not os.path.exists(sql_path):
        return
    try:
        with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip().rstrip(",;")
                if not line.startswith("(") or not line.endswith(")"):
                    continue
                try:
                    fields = next(csv.reader(
                        [line[1:-1]],
                        delimiter=",",
                        quotechar="'",
                        escapechar="\\",
                        skipinitialspace=True,
                    ))
                except Exception:
                    continue
                if len(fields) < 2:
                    continue
                headword = fields[1].strip()
                pos_tag = fields[7].strip() if len(fields) > 7 else "NULL"
                has_local_orthography = bool(re.search(r"[̀-ỹ']", headword, flags=re.UNICODE))
                has_pos_tag = pos_tag.upper() != "NULL" and bool(pos_tag)
                if not (has_pos_tag or has_local_orthography):
                    continue
                for token in _tokenize_detector_text(headword):
                    if len(token) > 2 and token not in {"the", "and", "for", "to", "of"}:
                        mad_neutral.update(_detector_variants(token))
    except Exception:
        return

_load_detector_dictionary_terms()
_load_madura_headword_terms()

# Manual high-confidence forms that often appear in short detector inputs.
for token in ("piro", "pira", "sak", "saiki", "iki", "niku", "niki", "kok"):
    _add_tokens(jv_ngoko, token)
for token in ("pinten", "menika", "sakmenika"):
    _add_tokens(jv_krama_alus, token)
for token in ("tello", "tello'", "tellok"):
    _add_tokens(mad_neutral, token)
for token in ("aku", "jam"):
    _add_tokens(indo_standard, token)

LANGUAGE_ORDER = {"Jawa": 0, "Madura": 1, "Indonesia": 2, "Asing": 3}
FOREIGN_STOPWORDS = {"i", "to", "the", "a", "an", "of", "and", "or", "is", "am", "are", "was", "were"}
LEVEL_ORDER = {
    "ngoko kasar": 0,
    "ngoko lugu": 1,
    "ngoko": 1,
    "krama lugu": 2,
    "krama alus": 3,
    "krama": 3,
    "krama inggil": 4,
    "enja-iya": 5,
    "engghi-enten": 6,
    "engghi-bhunten": 7,
    "informal": 8,
    "netral": 9,
}

def _candidate_sort_key(candidate: dict) -> tuple[int, int, str]:
    return (
        LANGUAGE_ORDER.get(candidate["language"], 99),
        LEVEL_ORDER.get(candidate["level"], 99),
        candidate["level"],
    )

def _append_candidate(candidates: list[dict], language: str, level: str):
    candidate = {"language": language, "level": level}
    if (language, level) not in {(item["language"], item["level"]) for item in candidates}:
        candidates.append(candidate)

def _detector_candidates(token: str) -> list[dict]:
    if token in FOREIGN_STOPWORDS:
        return [{"language": "Asing", "level": "netral"}]

    variants = _detector_variants(token)
    candidates: list[dict] = []

    if variants & (jv_kasar | {_strip_accents(item) for item in jv_kasar}):
        _append_candidate(candidates, "Jawa", "ngoko kasar")
    if variants & (jv_ngoko | jv_ngoko_core):
        _append_candidate(candidates, "Jawa", "ngoko lugu")
    if variants & jv_krama_lugu:
        _append_candidate(candidates, "Jawa", "krama lugu")
    if variants & (jv_krama_alus | jv_krama_core):
        _append_candidate(candidates, "Jawa", "krama alus")
    if variants & jv_krama_inggil_verbs:
        _append_candidate(candidates, "Jawa", "krama inggil")

    if variants & mad_enja_iya:
        _append_candidate(candidates, "Madura", "enja-iya")
    if variants & (mad_engghi_enten | mad_engghi_enten_core):
        _append_candidate(candidates, "Madura", "engghi-enten")
    if variants & (mad_engghi_bhunten | mad_engghi_bhunten_core):
        _append_candidate(candidates, "Madura", "engghi-bhunten")
    if variants & mad_neutral:
        _append_candidate(candidates, "Madura", "netral")

    if variants & indo_slang:
        _append_candidate(candidates, "Indonesia", "informal")
    if variants & indo_standard:
        _append_candidate(candidates, "Indonesia", "netral")

    if not candidates:
        return [{"language": "Asing", "level": "netral"}]
    return sorted(candidates, key=_candidate_sort_key)

def _summarize_register(language: str, level_counts: Counter) -> str:
    if language == "Jawa":
        if level_counts[("Jawa", "ngoko kasar")]:
            return "ngoko kasar"
        high = (
            level_counts[("Jawa", "krama lugu")]
            + level_counts[("Jawa", "krama alus")]
            + level_counts[("Jawa", "krama inggil")]
        )
        low = level_counts[("Jawa", "ngoko lugu")]
        if high and low:
            return "campuran ngoko-krama"
        if level_counts[("Jawa", "krama inggil")]:
            return "krama alus"
        if high:
            return "krama alus"
        if low:
            return "ngoko lugu"
        return "tidak diketahui"

    if language == "Madura":
        if level_counts[("Madura", "engghi-bhunten")]:
            return "Engghi-bhunten"
        if level_counts[("Madura", "engghi-enten")]:
            return "Engghi-enten"
        if level_counts[("Madura", "enja-iya")]:
            return "Enja-Iya"
        if level_counts[("Madura", "netral")]:
            return "netral"
        return "tidak diketahui"

    if language == "Indonesia":
        return "informal" if level_counts[("Indonesia", "informal")] else "formal"

    return "tidak diketahui"

def _legacy_detect_language_and_register(text: str) -> dict:
    clean_text = re.sub(r"[^\w\s']", ' ', text.lower())
    clean_text = re.sub(r"\s+", ' ', clean_text).strip()
    words = clean_text.split()
    
    if not words:
        return {
            "language": "Tidak pasti",
            "register": "tidak diketahui",
            "explanation": "Teks kosong, sehingga bahasa dan tingkat tutur belum bisa dianalisis.",
            "ngokoPercentage": 0.0,
            "kramaPercentage": 0.0,
            "wordAnalysis": [],
        }
        
    def analyze_words() -> list[dict]:
        analysis = []
        for word in words:
            if len(word) <= 1:
                analysis.append({"word": word, "language": "Tidak pasti", "level": "tidak dikenal"})
            elif word in jv_kasar:
                analysis.append({"word": word, "language": "Jawa", "level": "ngoko kasar"})
            elif word in jv_krama_alus or word in jv_krama_core or word in jv_krama_inggil_verbs:
                analysis.append({"word": word, "language": "Jawa", "level": "krama"})
            elif word in jv_krama_lugu:
                analysis.append({"word": word, "language": "Jawa", "level": "krama lugu"})
            elif word in jv_ngoko or word in jv_ngoko_core:
                analysis.append({"word": word, "language": "Jawa", "level": "ngoko"})
            elif word in mad_engghi_bhunten or word in mad_engghi_bhunten_core:
                analysis.append({"word": word, "language": "Madura", "level": "engghi-bhunten"})
            elif word in mad_engghi_enten or word in mad_engghi_enten_core:
                analysis.append({"word": word, "language": "Madura", "level": "engghi-enten"})
            elif word in mad_enja_iya or word in mad_enja_iya_core:
                analysis.append({"word": word, "language": "Madura", "level": "enja-iya"})
            elif word in indo_slang:
                analysis.append({"word": word, "language": "Indonesia", "level": "informal"})
            elif word in indo_standard:
                analysis.append({"word": word, "language": "Indonesia", "level": "netral"})
            else:
                analysis.append({"word": word, "language": "Tidak pasti", "level": "tidak dikenal"})
        return analysis

    word_analysis = analyze_words()
    language_counts = {"Indonesia": 0, "Jawa": 0, "Madura": 0}
    for item in word_analysis:
        language = item["language"]
        if language in language_counts:
            language_counts[language] += 1

    total_words = len(words)
    top_score = max(language_counts.values())
    top_languages = [language for language, count in language_counts.items() if count == top_score]
    top_percentage = round((top_score / total_words) * 100, 1) if total_words else 0.0
    min_language_percentage = 50.0
    
    if top_score == 0:
        return {
            "language": "Tidak pasti",
            "register": "tidak diketahui",
            "explanation": (
                "Tidak ada kosakata yang cocok dengan indikator Indonesia, Jawa, atau Madura "
                "di kamus lokal. Sistem tidak lagi memaksa hasil ke Indonesia formal saat bukti tidak cukup."
            ),
            "ngokoPercentage": 0.0,
            "kramaPercentage": 0.0,
            "wordAnalysis": word_analysis,
        }

    if len(top_languages) > 1:
        return {
            "language": "Tidak pasti",
            "register": "ambigu",
            "explanation": (
                "Persentase indikator bahasa seimbang, sehingga sistem tidak cukup yakin untuk memilih satu bahasa."
            ),
            "ngokoPercentage": 50.0,
            "kramaPercentage": 50.0,
            "wordAnalysis": word_analysis,
        }

    if top_percentage < min_language_percentage:
        return {
            "language": "Tidak pasti",
            "register": "tidak diketahui",
            "explanation": (
                f"Hanya {top_percentage}% token yang cocok dengan indikator {top_languages[0]}; "
                "bukti belum cukup untuk menetapkan bahasa keseluruhan."
            ),
            "ngokoPercentage": 0.0,
            "kramaPercentage": 0.0,
            "wordAnalysis": word_analysis,
        }

    detected_lang = top_languages[0]
        
    register = ""
    explanation = ""
    
    if detected_lang == "Indonesia":
        slang_words = [w for w in words if w in indo_slang]
        if slang_words:
            register = "informal"
            explanation = f"Teks dideteksi sebagai Bahasa Indonesia informal karena menggunakan kosakata informal/slang seperti: {', '.join(slang_words)}."
        else:
            register = "formal"
            explanation = "Teks dideteksi sebagai Bahasa Indonesia formal karena menggunakan kosakata baku."
        ngoko_pct = 0.0
        krama_pct = 0.0
            
    elif detected_lang == "Jawa":
        has_ngoko_core = any(w in words for w in jv_ngoko_core)
        has_krama_core = any(w in words for w in jv_krama_core)
        has_inggil = any(w in words for w in jv_krama_inggil_verbs)
        krama_lugu_words = [w for w in words if w in jv_krama_lugu]
        kasar_words = [w for w in words if w in jv_kasar]
        
        if kasar_words:
            register = "ngoko kasar"
            explanation = (
                "Teks dideteksi sebagai Jawa ragam kasar/informal karena memuat kata umpatan "
                f"atau ekspresi sangat informal seperti: {', '.join(kasar_words)}."
            )
        elif has_krama_core or "kula" in words:
            if has_inggil:
                register = "krama alus"
                explanation = "Teks dideteksi sebagai Jawa Krama Alus (formal/sangat sopan) karena menggunakan kata ganti/partikel Krama serta verba penghormatan Krama Inggil."
            else:
                register = "krama lugu"
                explanation = "Teks dideteksi sebagai Jawa Krama Lugu (formal/menengah) karena menggunakan kosakata Krama Lugu tanpa campuran verba Krama Inggil."
        elif has_ngoko_core or "kowe" in words or "aku" in words:
            if has_inggil:
                register = "ngoko alus"
                explanation = "Teks dideteksi sebagai Jawa Ngoko Alus karena memadukan kerangka kata Ngoko dengan kata penghormatan Krama Inggil untuk menghormati mitra tutur."
            else:
                register = "ngoko lugu"
                explanation = "Teks dideteksi sebagai Jawa Ngoko Lugu (kasual sehari-hari) dengan kosakata informal."
        else:
            if has_inggil:
                register = "krama alus"
                explanation = "Teks dideteksi sebagai Jawa Krama Alus karena memuat verba penghormatan tinggi."
            elif krama_lugu_words:
                register = "krama lugu"
                explanation = "Teks dideteksi sebagai Jawa Krama Lugu berdasarkan kosa kata tingkat menengah."
            else:
                register = "ngoko lugu"
                explanation = "Teks dideteksi sebagai Jawa Ngoko Lugu."
        if register.startswith("krama"):
            ngoko_pct = 15.0
            krama_pct = 85.0
        elif register == "ngoko alus":
            ngoko_pct = 55.0
            krama_pct = 45.0
        elif register == "ngoko kasar":
            ngoko_pct = 98.0
            krama_pct = 2.0
        else:
            ngoko_pct = 85.0
            krama_pct = 15.0
                
    elif detected_lang == "Madura":
        has_enja_iya = any(w in words for w in mad_enja_iya_core)
        has_engghi_enten = any(w in words for w in mad_engghi_enten_core)
        has_engghi_bhunten = any(w in words for w in mad_engghi_bhunten_core)
        
        engghi_bhunten_words = [w for w in words if w in mad_engghi_bhunten]
        engghi_enten_words = [w for w in words if w in mad_engghi_enten]
        
        if has_engghi_bhunten or engghi_bhunten_words:
            register = "Engghi-bhunten"
            explanation = "Teks dideteksi sebagai Madura Engghi-bhunten (tingkat tutur halus/formal)."
            ngoko_pct = 15.0
            krama_pct = 85.0
        elif has_engghi_enten or engghi_enten_words:
            register = "Engghi-enten"
            explanation = "Teks dideteksi sebagai Madura Engghi-enten (tingkat tutur menengah)."
            ngoko_pct = 45.0
            krama_pct = 55.0
        else:
            register = "Enja-Iya"
            explanation = "Teks dideteksi sebagai Madura Enja-Iya (tingkat tutur kasual sehari-hari)."
            ngoko_pct = 85.0
            krama_pct = 15.0
            
    return {
        "language": detected_lang,
        "register": register,
        "explanation": explanation,
        "ngokoPercentage": ngoko_pct,
        "kramaPercentage": krama_pct,
        "wordAnalysis": word_analysis,
    }

def detect_language_and_register(text: str) -> dict:
    words = _tokenize_detector_text(text)

    if not words:
        return {
            "language": "Tidak pasti",
            "register": "tidak diketahui",
            "explanation": "Teks kosong, sehingga bahasa dan tingkat tutur belum bisa dianalisis.",
            "ngokoPercentage": 0.0,
            "kramaPercentage": 0.0,
            "wordAnalysis": [],
        }

    word_analysis = []
    language_counts = Counter()
    level_counts = Counter()

    for word in words:
        candidates = _detector_candidates(word)
        evidence_candidates = [item for item in candidates if item["language"] != "Asing"]
        display_candidates = evidence_candidates or candidates
        language = " / ".join(dict.fromkeys(item["language"] for item in display_candidates))
        level = " / ".join(dict.fromkeys(item["level"] for item in display_candidates))

        word_analysis.append({
            "word": word,
            "language": language,
            "level": level,
            "candidates": display_candidates,
        })

        primary_by_language = {}
        for candidate in evidence_candidates:
            language = candidate["language"]
            current = primary_by_language.get(language)
            if current is None or (
                current["level"] == "netral" and candidate["level"] != "netral"
            ):
                primary_by_language[language] = candidate

        for candidate in primary_by_language.values():
            language_counts[candidate["language"]] += 1
            level_counts[(candidate["language"], candidate["level"])] += 1

    regional_total = sum(
        count
        for (language, level), count in level_counts.items()
        if language in {"Jawa", "Madura"} and level != "netral"
    )
    low_count = (
        level_counts[("Jawa", "ngoko kasar")]
        + level_counts[("Jawa", "ngoko lugu")]
        + level_counts[("Madura", "enja-iya")]
    )
    high_count = (
        level_counts[("Jawa", "krama lugu")]
        + level_counts[("Jawa", "krama alus")]
        + level_counts[("Jawa", "krama inggil")]
        + level_counts[("Madura", "engghi-enten")]
        + level_counts[("Madura", "engghi-bhunten")]
    )
    ngoko_pct = round((low_count / regional_total) * 100, 1) if regional_total else 0.0
    krama_pct = round((high_count / regional_total) * 100, 1) if regional_total else 0.0

    if not language_counts:
        return {
            "language": "Tidak pasti",
            "register": "tidak diketahui",
            "explanation": (
                "Tidak ada token yang cocok dengan leksikon lokal Indonesia, Jawa, atau Madura. "
                "Setiap kata tetap ditandai asing/netral tanpa dipaksa ke salah satu bahasa."
            ),
            "ngokoPercentage": 0.0,
            "kramaPercentage": 0.0,
            "wordAnalysis": word_analysis,
        }

    total_words = len(words)
    top_score = max(language_counts.values())
    top_percentage = (top_score / total_words) * 100 if total_words else 0.0

    top_languages = [language for language, count in language_counts.items() if count == top_score]

    if len(top_languages) > 1:
        return {
            "language": "Tidak pasti",
            "register": "ambigu",
            "explanation": (
                "Analisis per-kata menemukan kandidat dari beberapa bahasa dengan kekuatan seimbang. "
                "Label tiap kata ditampilkan independen, termasuk kata yang punya lebih dari satu kandidat bahasa."
            ),
            "ngokoPercentage": ngoko_pct,
            "kramaPercentage": krama_pct,
            "wordAnalysis": word_analysis,
        }

    if top_percentage < 75.0:
        return {
            "language": "Tidak pasti",
            "register": "tidak diketahui",
            "explanation": (
                f"Meskipun indikator terbanyak adalah bahasa {top_languages[0]} ({round(top_percentage, 1)}%), "
                "sistem membutuhkan dominasi minimal 75% dari total kata untuk dapat menetapkan bahasa keseluruhan secara pasti."
            ),
            "ngokoPercentage": 0.0,
            "kramaPercentage": 0.0,
            "wordAnalysis": word_analysis,
        }

    detected_lang = top_languages[0]
    register = _summarize_register(detected_lang, level_counts)
    evidence_count = sum(language_counts.values())
    detected_count = language_counts[detected_lang]
    explanation = (
        f"Bahasa dominan dihitung dari kandidat leksikal per kata: {detected_lang} "
        f"muncul {detected_count} dari {evidence_count} kandidat lokal. "
        "Kata yang cocok di lebih dari satu bahasa tetap menampilkan semua kandidatnya."
    )

    return {
        "language": detected_lang,
        "register": register,
        "explanation": explanation,
        "ngokoPercentage": ngoko_pct,
        "kramaPercentage": krama_pct,
        "wordAnalysis": word_analysis,
    }
