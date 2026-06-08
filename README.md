# HeritageGuard 🛡️

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
* **Database**: PostgreSQL (via SQLAlchemy ORM)
* **Cache Opsional**: Redis untuk cache terdistribusi saat trafik mulai naik
* **Reverse Proxy**: NGINX untuk routing lokal, batas ukuran upload, dan header HTTP
* **Observability**: Prometheus + Grafana OSS untuk metrik request dan latensi
* **Pemrosesan Dokumen**: PyMuPDF (untuk PDF) & python-docx (untuk DOCX)

---

## 📁 Struktur Direktori Proyek
```text
FP-AI-Kelompok7/
├── backend/            # Source code server FastAPI (Python)
├── frontend/           # Source code website Next.js (TypeScript & React)
├── assets/             # Aset gambar & batik visual pendukung
├── .gitignore          # File konfigurasi abaikan git (venv, node_modules, db disembunyikan)
└── README.md           # Dokumentasi utama proyek
```

---

## 🚀 Panduan Setup & Instalasi Proyek (Step-by-Step)

Ikuti langkah-langkah di bawah ini secara berurutan untuk menjalankan proyek ini di komputer Anda setelah melakukan clone:

### Langkah 1: Clone Repository
Buka terminal Anda, lalu jalankan perintah:
```bash
git clone <url-repository-github-anda>
cd FP-AI-Kelompok7
```

---

### Langkah 2: Setup & Jalankan Backend (FastAPI)
Buka terminal baru (**Tab 1**), masuk ke root folder proyek, lalu lakukan setup environment Python:

1. **Buat konfigurasi environment**:
   ```bash
   cp .env.example .env
   ```
   Ubah nilai `POSTGRES_PASSWORD` dan `DATABASE_URL` di `.env` agar memakai password lokal Anda.

2. **Jalankan PostgreSQL lokal**:
   ```bash
   docker compose up -d postgres
   ```
   Jika ingin menjalankan komponen opsional untuk observability/proxy/cache:
   ```bash
   docker compose up -d postgres redis nginx prometheus grafana
   ```
   NGINX tersedia di `http://localhost:8080`, Prometheus di `http://localhost:9090`, dan Grafana di `http://localhost:3001`.

3. **Buat Virtual Environment (venv)**:
   ```bash
   python3 -m venv venv
   ```
4. **Aktifkan Virtual Environment**:
   * **Linux/macOS**:
     ```bash
     source venv/bin/activate
     ```
   * **Windows (Command Prompt / Powershell)**:
     ```cmd
     .\venv\Scripts\activate
     ```
5. **Instal Library Pendukung**:
   ```bash
   pip install -r backend/requirements.txt
   ```
6. **Jalankan Server FastAPI**:
   ```bash
   uvicorn backend.main:app --port 8000 --reload
   ```
   *Backend kini berjalan aktif di alamat: `http://127.0.0.1:8000`*

Endpoint metrik backend tersedia di `http://127.0.0.1:8000/metrics` dan dipakai Prometheus.

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

Jika backend berjalan di host berbeda, buat `frontend/.env.local` dan set:
```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

---

## ⏹️ Cara Mematikan Aplikasi
Jika Anda ingin menonaktifkan server yang sedang berjalan:
- Cukup kembali ke terminal masing-masing (Tab FastAPI dan Tab Next.js) lalu tekan tombol **`Ctrl + C`** pada keyboard Anda. Proses server akan langsung terhenti.
