# HeritageGuard

**HeritageGuard** adalah platform digital berbasis kecerdasan buatan (AI) yang dirancang untuk melestarikan bahasa daerah di Indonesia, dengan fokus utama pada **Bahasa Jawa** dan **Bahasa Madura**. Platform ini membantu pengguna menerjemahkan teks dan dokumen (PDF/DOCX) secara kontekstual sekaligus mendeteksi tingkat kesopanan bahasa agar tetap menghormati norma kebudayaan lokal.

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
4. **Portal Insights & Statistik**: Menampilkan visualisasi tren penurunan vitalitas bahasa ibu per generasi, daftar kosakata terpopuler, serta modul interaktif *Kata Hari Ini* (*Word of the Day*) beserta pelafalan audionya.

---

## ⚙️ Spesifikasi Teknologi (Tech Stack)
* **Frontend**: Next.js 16+ (React 19, TypeScript, Tailwind CSS v4, Lucide React Icons)
* **Backend**: FastAPI (Python 3.12+, Uvicorn Server)
* **Database**: SQLite (via SQLAlchemy ORM)
* **Pemrosesan Dokumen**: PyMuPDF (untuk PDF) & python-docx (untuk DOCX)
* **AI / LLM**: Google Gemini API (terjemahan fallback + chatbot multilingual)

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

HeritageGuard menggunakan **Google Gemini API** untuk dua kapabilitas AI:

### 1. Fallback Terjemahan Cerdas
Ketika kalimat input mengandung kata-kata di luar kamus lokal (rule-based tidak bisa menerjemahkan dengan baik), sistem otomatis memanggil Gemini untuk menghasilkan terjemahan lengkap dengan tingkat tutur yang sesuai.

Alur: `Input → Rule-based (kamus lokal) → Jika coverage rendah → Gemini AI`

### 2. Chatbot Multilingual
Fitur chatbot yang bisa diajak berbicara dalam Bahasa Indonesia, Jawa (Ngoko & Krama), dan Madura (Enja-Iya & Engghi-Bhanten). Chatbot memahami konteks budaya dan bisa membantu pengguna belajar bahasa daerah.

### Konfigurasi
Set environment variable `GEMINI_API_KEYS` (pisahkan dengan koma untuk rotasi multi-key):
```bash
export GEMINI_API_KEYS="key1,key2,key3"
uvicorn backend.main:app --port 8000 --reload
```
Sistem akan merotasi key secara round-robin. Jika satu key kena rate-limit (429), otomatis pindah ke key berikutnya.

> Tanpa API key, backend tetap berfungsi (fitur terjemahan rule-based aktif, chatbot mengembalikan error 503).

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
