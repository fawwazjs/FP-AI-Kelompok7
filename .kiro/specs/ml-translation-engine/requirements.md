# Requirements Document

## Introduction

Saat ini HeritageGuard menggunakan mesin terjemahan dan deteksi register yang sepenuhnya **rule-based** (kamus kata, pencocokan frasa eksak, dan penghitungan skor leksikal) di `backend/translator_service.py`. Komentar di kode bahkan menyatakan bahwa output "mensimulasikan" MarianMT, IndoBERT, dan Random Forest Classifier, padahal tidak ada model ML sungguhan yang berjalan.

Fitur ini bertujuan mengganti mesin rule-based tersebut dengan **model machine learning sungguhan** untuk tiga kapabilitas inti:

1. **Terjemahan neural** (Neural Machine Translation) dua arah antara Indonesia ↔ Jawa dan Indonesia ↔ Madura, dengan kontrol tingkat tutur (ngoko/krama, enja-iya/engghi-bhanten).
2. **Deteksi bahasa & register** menggunakan klasifier terlatih (bukan penghitungan kata).
3. **Analisis tingkat kesopanan** (persentase ngoko/krama) menggunakan model klasifikasi.

Penggantian harus menjaga **kompatibilitas kontrak API** yang sudah ada (`/api/translate`, `/api/detect-register`, `/api/translate-document`) agar frontend Next.js dan fallback offline-nya tetap berfungsi tanpa perubahan kontrak. Karena ini proyek akademik dengan dataset terbatas (`Dataset/JawaIndo.csv`, `Dataset/madura.sql`, `Dataset/ngoko_krama.json`), requirements juga mencakup pelatihan model dari dataset yang ada serta mekanisme fallback ke rule-based bila model gagal dimuat.

### Tujuan Utama
- Mengganti inti `translate_and_classify` dan `detect_language_and_register` dengan inferensi model ML.
- Menyediakan pipeline pelatihan yang dapat direproduksi dari dataset lokal.
- Mempertahankan stabilitas kontrak API dan pengalaman pengguna.

### Keputusan Teknis (disepakati)
- **Terjemahan (NMT):** fine-tuning model Transformer pra-terlatih dari HuggingFace (mis. NLLB-200 distilled atau IndoBART) menggunakan PyTorch + `transformers`. Bukan dilatih dari nol.
- **Deteksi bahasa, register, dan analisis kesopanan:** model klasik **TF-IDF + scikit-learn** (mis. Logistic Regression / Linear SVM) yang dilatih dari dataset lokal, disimpan sebagai artefak `.joblib` ringan.
- **Lingkup:** arsitektur ML sungguhan yang di-fine-tune/dilatih dari dataset yang tersedia dengan ekspektasi akurasi realistis (data terbatas), **dengan fallback rule-based** sebagai jaring pengaman bila artefak model tidak tersedia.

### Di Luar Cakupan (Out of Scope)
- Mengubah arsitektur frontend atau menambah halaman baru.
- Mengganti penyimpanan database atau skema log.
- Menyediakan layanan terjemahan komersial berskala produksi/cloud GPU.

---

## Glossary
- **NMT**: Neural Machine Translation, model terjemahan berbasis jaringan saraf.
- **Register / Tingkat tutur**: Tingkat kesopanan bahasa (Jawa: ngoko/krama; Madura: enja-iya/engghi-bhanten; Indonesia: formal/informal).
- **Level**: Parameter API bernilai `low` (kasual) atau `high` (sopan) yang mengendalikan ragam target.
- **Fallback rule-based**: Mesin lama yang dipakai jika model ML tidak tersedia atau gagal.
- **Artefak model**: Berkas hasil pelatihan (bobot, tokenizer, label encoder) yang dimuat saat inferensi.
- **TF-IDF**: Term Frequency–Inverse Document Frequency, representasi fitur teks untuk model klasik scikit-learn.
- **Fine-tuning**: Melatih ulang sebagian/seluruh bobot model pra-terlatih pada dataset domain (Jawa/Madura).

---

## Requirements

### Requirement 1: Terjemahan Berbasis Model Neural
**User Story:** Sebagai pengguna penerjemah, saya ingin hasil terjemahan dihasilkan oleh model ML terlatih, sehingga terjemahan lebih natural dan kontekstual dibanding substitusi kata per kata.

#### Acceptance Criteria
1. WHEN pengguna mengirim permintaan ke `POST /api/translate` dengan `source_lang`, `target_lang`, dan `level` yang valid THEN sistem SHALL menghasilkan `translatedText` dari inferensi model NMT Transformer hasil fine-tuning (mis. NLLB-200 distilled / IndoBART), bukan dari pencocokan kamus rule-based.
2. WHERE pasangan bahasa adalah Indonesia↔Jawa atau Indonesia↔Madura THE sistem SHALL mendukung terjemahan dua arah menggunakan model.
3. IF dukungan dua arah untuk suatu pasangan bahasa tidak tersedia THEN sistem SHALL menyediakan terjemahan satu arah sebagai fallback alih-alih menggagalkan permintaan.
4. WHEN `level` bernilai `high` atau `low` THEN sistem SHALL menghasilkan output yang sesuai ragam tutur yang diminta (krama/engghi-bhanten untuk `high`, ngoko/enja-iya untuk `low`).
5. WHERE pasangan bahasa adalah Jawa↔Madura (tanpa Indonesia) THE sistem SHALL menghasilkan terjemahan, baik melalui model langsung maupun pivot melalui Bahasa Indonesia.
6. WHEN `source_lang` sama dengan `target_lang` THEN sistem SHALL mengembalikan teks asli tanpa menjalankan terjemahan.
7. WHEN permintaan terjemahan dengan input valid berhasil diproses THEN sistem SHALL mengembalikan kode status HTTP `200`.
8. THE response `/api/translate` SHALL mempertahankan struktur field yang sama seperti sekarang (`translatedText`, `politenessLevel`, `ngokoPercentage`, `kramaPercentage`, `context`, `alternativeText`).

### Requirement 2: Deteksi Bahasa & Register Berbasis Klasifier
**User Story:** Sebagai pengguna fitur deteksi, saya ingin bahasa dan tingkat tutur dideteksi oleh model klasifikasi terlatih, sehingga hasilnya lebih akurat untuk kalimat campuran dan di luar kosakata kamus.

#### Acceptance Criteria
1. WHEN pengguna mengirim teks ke `POST /api/detect-register` THEN sistem SHALL mengklasifikasikan bahasa (Indonesia/Jawa/Madura) menggunakan model TF-IDF + scikit-learn terlatih.
2. WHEN bahasa terdeteksi THEN sistem SHALL mengklasifikasikan register yang sesuai (mis. formal/informal, ngoko lugu/krama alus, enja-iya/engghi-bhunten) menggunakan model.
3. THE response `/api/detect-register` SHALL mempertahankan struktur field yang sama (`language`, `register`, `explanation`).
4. WHEN teks input kosong atau hanya berisi spasi THEN sistem SHALL menolak dengan kode status `400` (perilaku validasi yang ada dipertahankan).
5. IF input gagal validasi karena alasan lain (mis. teks terlalu panjang) THEN sistem SHALL mengembalikan kode status yang sesuai dan berbeda (mis. `413`), bukan `400`.
6. WHILE model menghasilkan prediksi THE sistem SHALL menyertakan tingkat keyakinan atau alasan dalam field `explanation` agar tetap informatif.

### Requirement 3: Analisis Tingkat Kesopanan Berbasis Model
**User Story:** Sebagai pengguna, saya ingin persentase ngoko/krama dihitung oleh model klasifikasi, sehingga indikator kesopanan mencerminkan analisis ML, bukan rasio penghitungan kata.

#### Acceptance Criteria
1. WHEN sebuah terjemahan atau analisis dilakukan untuk bahasa Jawa atau Madura THEN sistem SHALL menghasilkan `ngokoPercentage` dan `kramaPercentage` dari model klasifikasi register.
2. THE total `ngokoPercentage` dan `kramaPercentage` SHALL berjumlah 100 (atau 0/0 untuk Bahasa Indonesia netral) agar konsisten dengan tampilan frontend.
3. WHEN bahasa adalah Indonesia THEN sistem SHALL mengembalikan nilai netral seperti perilaku saat ini.

### Requirement 4: Pipeline Pelatihan Model yang Dapat Direproduksi
**User Story:** Sebagai pengembang/anggota kelompok, saya ingin skrip pelatihan yang dapat dijalankan ulang dari dataset lokal, sehingga model dapat dilatih, dievaluasi, dan diperbarui secara transparan.

#### Acceptance Criteria
1. THE proyek SHALL menyediakan skrip atau modul pelatihan terpisah (mis. di `backend/ml/` atau `training/`) yang membaca dataset dari folder `Dataset/`.
2. WHEN skrip pelatihan dijalankan THEN sistem SHALL menghasilkan artefak model yang tersimpan ke lokasi yang dapat dikonfigurasi.
3. THE pipeline pelatihan SHALL mendokumentasikan langkah preprocessing (pembersihan dataset, pemisahan train/validasi) dan metrik evaluasi (mis. BLEU/akurasi).
4. WHERE dataset tidak cukup untuk melatih NMT dari nol THE pipeline SHALL mendukung fine-tuning model pra-terlatih sebagai pendekatan utama yang didokumentasikan.
5. IF fine-tuning tidak tersedia atau gagal THEN pipeline SHALL berhenti secara anggun (graceful) dengan pesan kesalahan yang jelas, dan SHALL tetap mengizinkan pelatihan dari nol dengan peringatan eksplisit tentang keterbatasan data.
6. THE artefak model SHALL dikecualikan dari kontrol versi melalui `.gitignore` jika berukuran besar, dengan instruksi cara menghasilkannya.

### Requirement 5: Pemuatan Model & Fallback yang Aman
**User Story:** Sebagai pengguna, saya ingin aplikasi tetap berfungsi meskipun model ML gagal dimuat, sehingga layanan tidak mati total.

#### Acceptance Criteria
1. WHEN server backend dimulai THEN sistem SHALL memuat artefak model satu kali (lazy/eager) dan menyimpannya untuk digunakan ulang antar-permintaan.
2. IF artefak model tidak ditemukan atau gagal dimuat THEN sistem SHALL mencatat peringatan dan menggunakan mesin rule-based yang ada sebagai fallback tanpa crash.
3. WHEN model digunakan untuk inferensi pada satu permintaan THEN sistem SHALL menyelesaikan respons dalam batas waktu yang wajar untuk penggunaan interaktif.
4. THE pemuatan model SHALL tidak memblokir endpoint `/api/health` agar pemeriksaan kesehatan tetap responsif.

### Requirement 6: Penerjemahan Dokumen Memakai Model
**User Story:** Sebagai pengguna penerjemah dokumen, saya ingin dokumen (PDF/DOCX/DOC/TXT) diterjemahkan memakai model ML yang sama, sehingga hasil dokumen konsisten dengan penerjemah teks.

#### Acceptance Criteria
1. WHEN pengguna mengunggah dokumen ke `POST /api/translate-document` THEN sistem SHALL menerjemahkan isi dokumen menggunakan model ML yang sama dengan endpoint teks.
2. THE alur ekstraksi, rekonstruksi, dan unduh dokumen SHALL tetap berfungsi tanpa perubahan kontrak.
3. WHERE volume teks dokumen besar THE sistem SHALL memproses terjemahan secara batch/efisien agar tidak melebihi batasan memori yang wajar.

### Requirement 7: Ketergantungan & Dokumentasi
**User Story:** Sebagai anggota kelompok yang menyetel proyek, saya ingin dependensi ML terdokumentasi dengan jelas, sehingga proyek dapat dijalankan ulang di mesin lain.

#### Acceptance Criteria
1. THE `backend/requirements.txt` SHALL diperbarui dengan pustaka ML yang dibutuhkan (mis. PyTorch/Transformers/scikit-learn) beserta batasan versi.
2. THE README SHALL diperbarui dengan instruksi cara melatih/mengunduh model dan menjalankan backend dengan model aktif.
3. WHERE pustaka ML berat dan opsional THE dokumentasi mode fallback rule-based SHALL lengkap dan tersedia sebelum fitur fallback diaktifkan, sehingga proyek tetap bisa dijalankan tanpa model dengan instruksi yang jelas.

### Requirement 8: Pengujian & Validasi
**User Story:** Sebagai pengembang, saya ingin pengujian memverifikasi jalur inferensi model dan fallback, sehingga regresi dapat terdeteksi.

#### Acceptance Criteria
1. THE rangkaian uji SHALL mencakup kasus inferensi model untuk tiap arah terjemahan yang didukung.
2. THE rangkaian uji SHALL memverifikasi mekanisme fallback aktif ketika artefak model tidak tersedia.
3. WHEN pengujian dijalankan tanpa artefak model THEN uji SHALL tetap lulus dengan menggunakan jalur fallback (tidak bergantung pada keberadaan model besar).
4. THE struktur respons API SHALL diverifikasi tetap kompatibel dengan ekspektasi frontend.
