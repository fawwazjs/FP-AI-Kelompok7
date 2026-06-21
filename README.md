# Lokalator

**Lokalator** adalah platform digital berbasis kecerdasan buatan (AI) yang dirancang untuk melestarikan bahasa daerah di Indonesia, dengan fokus utama pada **Bahasa Jawa** dan **Bahasa Madura**. Platform ini membantu pengguna menerjemahkan teks dan dokumen (PDF/DOCX) secara kontekstual sekaligus mendeteksi tingkat kesopanan bahasa agar tetap menghormati norma kebudayaan lokal.

Proyek ini dikembangkan sebagai **Final Project** untuk mata kuliah **Kecerdasan Artifisial dan Machine Learning** oleh **Kelompok 7 Kelas A**.

---

## 👥 Anggota Kelompok 7
* **Ahmad Wildan Fawwaz** (5027241001)
* **Muhammad Rakha Hananditya Rauf** (5027241015)
* **Yasykur Khalis Jati Maulana Yuwono** (5027241122)
* **Aras Rizky Ananta** (5027221053)

---

## 🛠️ Fitur Utama
1. **Penerjemah Bahasa Daerah Kontekstual**: Menerjemahkan kalimat dua arah secara presisi antara Bahasa Indonesia ↔ Jawa (Ngoko & Krama) serta Indonesia ↔ Madura (Enja-Iya & Engghi-Bhanten).
2. **Deteksi Tingkat Kesopanan (Leksikal)**: Menganalisis kalimat input dan mengukur persentase kesopanan (Ngoko, Krama, Formal, Informal) lengkap dengan penjelasan konteks budayanya.
3. **Penerjemah Dokumen Massal**: Mengunggah berkas PDF atau DOCX untuk diekstrak, diterjemahkan, dan diunduh kembali tanpa merusak tata letak dokumen asli.
4. **Portal Analitik Bahasa**: Menampilkan visualisasi tren penurunan vitalitas bahasa ibu per generasi, daftar kosakata terpopuler, serta modul interaktif *Kata Hari Ini* (*Word of the Day*) beserta pelafalan audionya.

---

## ⚙️ Spesifikasi Teknologi (Tech Stack)
* **Frontend**: Next.js 16+ (React 19, TypeScript, Tailwind CSS v4, Lucide React Icons)
* **Backend**: FastAPI (Python 3.12+, Uvicorn Server)
* **Database**: SQLite (via SQLAlchemy ORM)
* **Pemrosesan Dokumen**: PyMuPDF (untuk PDF) & python-docx (untuk DOCX)
* **AI / LLM**: Google Gemini API (terjemahan konteks + chatbot multilingual)

---

## 📁 Struktur Direktori Proyek
```text
FP-AI-Kelompok7/
├── backend/            # Source code server FastAPI (Python)
├── frontend/           # Source code website Next.js (TypeScript & React)
├── Dataset/            # Dataset kamus Jawa-Indonesia, Madura-Indonesia
├── assets/             # Aset gambar & batik visual pendukung
├── .gitignore          # File konfigurasi abaikan git
└── README.md           # Dokumentasi utama proyek
```

---

## � Integrasi AI (Gemini)

Lokalator menggunakan **Google Gemini API** untuk dua kapabilitas AI:

### 1. Terjemahan Cerdas
Penerjemah teks otomatis memakai provider API terlebih dahulu agar terjemahan memperhatikan konteks kalimat utuh, imbuhan, reduplikasi, idiom, dan tingkat tutur target. Jika Gemini atau provider API tidak tersedia, sistem langsung memakai fallback kamus lokal tanpa menampilkan error ke pengguna.

Alur: `Input → Gemini structured translation → Gemini plain fallback → Google Translate opsional → Rule-based lokal`

### 2. Chatbot Multilingual
Fitur chatbot yang bisa diajak berbicara dalam Bahasa Indonesia, Jawa (Ngoko & Krama), dan Madura (Enja-Iya & Engghi-Bhanten). Chatbot memahami konteks budaya dan bisa membantu pengguna belajar bahasa daerah.

### Konfigurasi
Set salah satu environment variable berikut sebelum menjalankan backend:
```bash
# Satu key
export GEMINI_API_KEY="key_anda"

# Atau beberapa key, pisahkan dengan koma
export GEMINI_API_KEYS="key1,key2,key3"

uvicorn backend.main:app --port 8000 --reload
```
Jalankan `export` di terminal yang sama dengan `uvicorn`, lalu restart backend.

Alternatif lokal: buat file `.env` di root proyek (file ini sudah masuk `.gitignore`):
```bash
GEMINI_API_KEY=key_anda

# Opsional: fallback Google Translate untuk pasangan bahasa yang didukung
GOOGLE_TRANSLATE_API_KEY=key_google_translate

# Opsional: gunakan Translation LLM Cloud Translation Basic
# GOOGLE_TRANSLATE_MODEL=projects/PROJECT_ID/locations/REGION_NAME/models/general/translation-llm
```

Cek status konfigurasi dengan `GET /api/gemini-status`.

> Tanpa API key, backend tetap berfungsi dengan fallback kamus/rule lokal. Chatbot tetap membutuhkan `GEMINI_API_KEY` atau `GEMINI_API_KEYS`.

---

## 🚀 Panduan Setup & Instalasi Proyek (Step-by-Step)

### ⚡ Cara Cepat Menjalankan Aplikasi (Quick Start)
1. **Jalankan Backend (Terminal 1)**:
   ```bash
   source venv/bin/activate
   pip install -r backend/requirements.txt
   uvicorn backend.main:app --port 8000 --reload
   ```
2. **Jalankan Frontend (Terminal 2)**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. **Akses Aplikasi**:
   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Backend API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

Ikuti langkah-langkah di bawah ini secara berurutan untuk melakukan setup proyek dari awal di komputer Anda:

### Langkah 1: Clone Repository
Buka terminal Anda, lalu jalankan perintah:
```bash
git clone <url-repository-github-anda>
cd FP-AI-Kelompok7
```

---

### Langkah 2: Setup & Jalankan Backend (FastAPI)
Buka terminal baru (**Tab 1**), masuk ke root folder proyek, lalu lakukan setup environment Python:

1. **Buat Virtual Environment (venv)**:
   ```bash
   python3 -m venv venv
   ```
2. **Aktifkan Virtual Environment**:
   * **Linux/macOS**:
     ```bash
     source venv/bin/activate
     ```
   * **Windows (Command Prompt / Powershell)**:
     ```cmd
     .\venv\Scripts\activate
     ```
3. **Instal Library Pendukung**:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. **Jalankan Server FastAPI**:
   ```bash
   uvicorn backend.main:app --port 8000 --reload
   ```
   *Backend kini berjalan aktif di alamat: `http://127.0.0.1:8000`*

---

### Langkah 3: Setup & Jalankan Frontend (Next.js)
Buka jendela terminal baru lagi (**Tab 2**), masuk ke folder frontend, lalu lakukan setup package Node:

1. **Pindah ke folder frontend**:
   ```bash
   cd frontend
   ```
2. **Instal package npm**:
   ```bash
   npm install
   ```
3. **Jalankan Server Development Next.js**:
   ```bash
   npm run dev
   ```
   *Frontend kini berjalan aktif di alamat: `http://localhost:3000`*

---

## ⏹️ Cara Mematikan Aplikasi
Jika Anda ingin menonaktifkan server yang sedang berjalan:
- Cukup kembali ke terminal masing-masing (Tab FastAPI dan Tab Next.js) lalu tekan tombol **`Ctrl + C`** pada keyboard Anda. Proses server akan langsung terhenti.
