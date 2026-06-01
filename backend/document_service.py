# HeritageGuard Document Parsing & Reconstruction Engine
# Handles PDF (PyMuPDF) and DOCX (python-docx) translations.

import os
from .translator_service import translate_and_classify

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import docx
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False

def process_and_translate_pdf(input_path: str, output_path: str, target_lang: str) -> dict:
    summary_info = {
        "words_translated": 0,
        "politeness_summary": "Krama Alus" if target_lang == "jv" else "Engghi-Bhanten",
        "file_created": output_path
    }

    # If PyMuPDF is not installed, do fallback
    if not PYMUPDF_AVAILABLE:
        with open(input_path, 'rb') as f:
            dummy_text = f.read().decode('utf-8', errors='ignore')[:500]
        
        words = len(dummy_text.split())
        summary_info["words_translated"] = words
        
        res = translate_and_classify(dummy_text, 'id', target_lang, 'high')
        
        with open(output_path, 'w') as f:
            f.write(f"=== HERITAGEGUARD TRANSLATED DOCUMENT (FALLBACK MODE) ===\n")
            f.write(f"Bahasa Target: {target_lang}\n")
            f.write(f"Jumlah Kata: {words}\n")
            f.write(f"=========================================================\n\n")
            f.write(res['translatedText'])
        return summary_info

    # Read PDF text
    doc = fitz.open(input_path)
    all_text = []
    for page in doc:
        all_text.append(page.get_text())
    doc.close()

    full_text = "\n".join(all_text)
    words = len(full_text.split())
    summary_info["words_translated"] = words

    # Translate in large paragraph chunks
    translated_chunks = []
    for chunk in full_text.split('\n\n'):
        if chunk.strip():
            res = translate_and_classify(chunk, 'id', target_lang, 'high')
            translated_chunks.append(res['translatedText'])
        else:
            translated_chunks.append('')

    with open(output_path, 'w') as f:
        f.write(f"=== HERITAGEGUARD TRANSLATED PDF SUMMARY ===\n")
        f.write(f"Bahasa Target: {target_lang}\n")
        f.write(f"Jumlah Kata: {words}\n")
        f.write(f"============================================\n\n")
        f.write("\n\n".join(translated_chunks))

    return summary_info

def process_and_translate_docx(input_path: str, output_path: str, target_lang: str) -> dict:
    summary_info = {
        "words_translated": 0,
        "politeness_summary": "Krama Alus" if target_lang == "jv" else "Engghi-Bhanten",
        "file_created": output_path
    }

    if not PYTHON_DOCX_AVAILABLE:
        with open(input_path, 'r', errors='ignore') as f:
            dummy_text = f.read()[:500]
        
        words = len(dummy_text.split())
        summary_info["words_translated"] = words
        
        res = translate_and_classify(dummy_text, 'id', target_lang, 'high')
        
        with open(output_path, 'w') as f:
            f.write(f"=== HERITAGEGUARD TRANSLATED DOCX (FALLBACK MODE) ===\n")
            f.write(f"Bahasa Target: {target_lang}\n\n")
            f.write(res['translatedText'])
        return summary_info

    # Real docx translation
    doc = docx.Document(input_path)
    new_doc = docx.Document()
    new_doc.add_heading("HeritageGuard Document Translation", 0)

    total_words = 0
    for p in doc.paragraphs:
        if p.text.strip():
            total_words += len(p.text.split())
            res = translate_and_classify(p.text, 'id', target_lang, 'high')
            new_doc.add_paragraph(res['translatedText'])
        else:
            new_doc.add_paragraph('')

    new_doc.save(output_path)
    summary_info["words_translated"] = total_words
    return summary_info
