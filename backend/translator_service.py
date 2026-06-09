# HeritageGuard AI Translator and Politeness Service
# Simulates MarianMT, IndoBERT, and Random Forest Classifier outputs.

import re
import os
import json
import unicodedata
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
    'bisa': { 'high': 'saged', 'low': 'iso' }
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
    'bisa': { 'high': 'saged', 'low': 'bisa' }
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

def _translate_word_by_word(text: str, dictionary: dict, level: str) -> tuple[str, str | None, int]:
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
        entry = None
        for token_key in _key_variants(core):
            entry = dictionary.get(token_key)
            if entry:
                break
        if not entry:
            translated_parts.append(raw)
            alternative_parts.append(raw)
            continue

        translated_count += 1
        alt_level = "low" if level == "high" else "high"
        replacement = _apply_case(core, entry[level])
        alternative = _apply_case(core, entry[alt_level])
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
        translated_text, alternative, translated_count = _translate_word_by_word(text, dict_to_use, level)
        
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

indo_standard = {"saya", "mau", "makan", "tidur", "anda", "kamu", "tidak", "saja", "sudah", "sedang", "mengapa", "sangat", "pergi", "di", "warung", "dekat", "keraton"}
indo_slang = {"gue", "gua", "lu", "nggak", "aja", "udah", "lagi", "kenapa", "banget", "pengen", "bobo", "mager", "bodo", "yuk", "bro", "selow", "dong", "capek", "pusing"}

mad_enja_iya = {"sengko'", "ba'na", "ngakan", "tedhung", "entar", "roma", "molea", "ngakana", "enja'"}
mad_engghi_enten = {"bula", "dhika", "bisaa", "abhanto"}
mad_engghi_bhunten = {"bhiula", "panjhenengngan", "neddha", "asera", "alomampah", "engghi", "bhanten", "kaula'", "bhâdhân", "dada"}

# Core indicators for speech level routing
jv_ngoko_core = {'aku', 'kowe', 'arep', 'ora', 'sing', 'opo', 'sopo', 'piye', 'kene', 'kono', 'neng', 'karo', 'lan', 'dadi'}
jv_krama_core = {'kula', 'badhe', 'mboten', 'ingkang', 'punapa', 'sinten', 'kadospundi', 'mriki', 'mrika', 'dhateng', 'kaliyan', 'dados', 'panjenengan', 'sampeyan'}
jv_krama_inggil_verbs = {'dhahar', 'sare', 'tindak', 'rawuh', 'sowan', 'kersa', 'nampi', 'jumeneng', 'dalem', 'sugeng'}

mad_enja_iya_core = {"sengko'", "engko'", "ba'na", "ba'en", "enja'"}
mad_engghi_enten_core = {"bula", "bula'", "dhika", "dhiko", "sampeyan"}
mad_engghi_bhunten_core = {"kaula", "kaula'", "bhâdhân", "panjhenengngan", "engghi", "bhanten", "bhunten", "ajunan", "srèra"}

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

def detect_language_and_register(text: str) -> dict:
    clean_text = re.sub(r"[^\w\s']", ' ', text.lower())
    clean_text = re.sub(r"\s+", ' ', clean_text).strip()
    words = clean_text.split()
    
    if not words:
        return {
            "language": "Indonesia",
            "register": "formal",
            "explanation": "Teks kosong."
        }
        
    indo_score = sum(1 for w in words if w in indo_standard or w in indo_slang)
    jawa_score = sum(1 for w in words if w in jv_ngoko or w in jv_krama_lugu or w in jv_krama_alus)
    mad_score = sum(1 for w in words if w in mad_enja_iya or w in mad_engghi_enten or w in mad_engghi_bhunten)
    
    if any(w in words for w in ["kula", "badhe", "dhahar", "sare", "mangan", "turu", "arep", "kowe", "inggih", "mboten"]):
        jawa_score += 10
    if any(w in words for w in ["sèngko'", "sengko'", "kaula'", "bhâdhân", "bhadhan", "panjhenengngan", "dhika", "ba'na", "terro"]):
        mad_score += 10
        
    scores = {"Indonesia": indo_score, "Jawa": jawa_score, "Madura": mad_score}
    detected_lang = max(scores, key=scores.get)
    
    if scores[detected_lang] == 0:
        detected_lang = "Indonesia"
        
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
            
    elif detected_lang == "Jawa":
        has_ngoko_core = any(w in words for w in jv_ngoko_core)
        has_krama_core = any(w in words for w in jv_krama_core)
        has_inggil = any(w in words for w in jv_krama_inggil_verbs)
        krama_lugu_words = [w for w in words if w in jv_krama_lugu]
        
        if has_krama_core or "kula" in words:
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
                
    elif detected_lang == "Madura":
        has_enja_iya = any(w in words for w in mad_enja_iya_core)
        has_engghi_enten = any(w in words for w in mad_engghi_enten_core)
        has_engghi_bhunten = any(w in words for w in mad_engghi_bhunten_core)
        
        engghi_bhunten_words = [w for w in words if w in mad_engghi_bhunten]
        engghi_enten_words = [w for w in words if w in mad_engghi_enten]
        
        if has_engghi_bhunten or engghi_bhunten_words:
            register = "Engghi-bhunten"
            explanation = "Teks dideteksi sebagai Madura Engghi-bhunten (tingkat tutur halus/formal)."
        elif has_engghi_enten or engghi_enten_words:
            register = "Engghi-enten"
            explanation = "Teks dideteksi sebagai Madura Engghi-enten (tingkat tutur menengah)."
        else:
            register = "Enja-Iya"
            explanation = "Teks dideteksi sebagai Madura Enja-Iya (tingkat tutur kasual sehari-hari)."
            
    return {
        "language": detected_lang,
        "register": register,
        "explanation": explanation
    }
