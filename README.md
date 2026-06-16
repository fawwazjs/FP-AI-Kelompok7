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
* **Machine Learning**: HuggingFace Transformers (NLLB-200 fine-tuned untuk NMT) & scikit-learn (TF-IDF + Logistic Regression untuk deteksi bahasa/register). Backend otomatis fallback ke mesin rule-based bila artefak model tidak tersedia.

---

## 📁 Struktur Direktori Proyek
```text
FP-AI-Kelompok7/
├── backend/            # Source code server FastAPI (Python)
│   └── ml/             # Layer ML: config, data prep, inferensi (NMT + classifier)
├── frontend/           # Source code website Next.js (TypeScript & React)
├── training/           # Notebook Google Colab untuk melatih model
├── models/             # Artefak model hasil training (di-gitignore; dibuat dari notebook)
├── assets/             # Aset gambar & batik visual pendukung
├── .gitignore          # File konfigurasi abaikan git (venv, node_modules, db disembunyikan)
└── README.md           # Dokumentasi utama proyek
```

---

## 🧠 Model Machine Learning

HeritageGuard kini memakai model ML sungguhan untuk terjemahan dan deteksi register, dengan **fallback rule-based** otomatis agar aplikasi tetap berjalan walau model belum dilatih.

### Apakah harus melatih model dulu?
- **Tanpa training**: backend langsung jalan memakai mesin rule-based (kamus + frasa). Tidak ada langkah tambahan.
- **Dengan model ML**: latih model lewat notebook Colab, taruh artefaknya di `models/`, lalu backend otomatis memakainya.

### Langkah melatih (Google Colab, GPU gratis)
1. Buka `training/HeritageGuard_Train_Colab.ipynb` di [Google Colab](https://colab.research.google.com/).
2. Set **Runtime ▸ Change runtime type ▸ GPU**.
3. Edit `REPO_URL` di sel clone agar menunjuk ke repo kamu, lalu jalankan semua sel berurutan.
4. Notebook akan: menyiapkan korpus dari `Dataset/`, melatih classifier scikit-learn, fine-tune NLLB-200, lalu menghasilkan `heritageguard_models.zip`.
5. Unduh zip itu, ekstrak ke folder `models/` di root repo sehingga strukturnya:
   ```text
   models/
     nmt/                 # model + tokenizer hasil fine-tune
     register_clf.joblib  # bundle classifier (bahasa, register, gaya)
   ```

### Mengaktifkan model di backend
1. Pasang dependensi ML (uncomment baris torch/transformers di `backend/requirements.txt`):
   ```bash
   pip install -r backend/requirements.txt
   pip install torch transformers sentencepiece
   ```
2. Jalankan backend seperti biasa. Cek `GET /api/health` — field `engine` akan bernilai `ml` jika model aktif, atau `rule-based` jika fallback.
3. (Opsional) Ubah lokasi artefak lewat env `HG_MODEL_DIR`.

> **Catatan akademik**: dataset proyek relatif kecil (kamus + dump kalimat), sehingga kualitas terjemahan neural terbatas. Arsitektur ML sudah sungguhan dan dapat ditingkatkan dengan menambah data paralel.

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
