# 🔍 TF-IDF Search Engine

Proyek ini adalah implementasi mesin pencarian sederhana berbasis **TF-IDF (Term Frequency - Inverse Document Frequency)** menggunakan **Python**.  
Dilengkapi dengan antarmuka web untuk mempermudah pencarian, dan tampilan **hero section** interaktif dengan efek ketik (*typewriter effect*).

## ✨ Fitur
- Pencarian berbasis algoritma **TF-IDF** untuk menemukan dokumen paling relevan.
- Antarmuka web sederhana (via `Flask`) untuk mengunggah, mencari, dan menampilkan hasil.
- Fitur **hapus semua history dokumen**.
- Efek teks animasi di halaman utama (*typewriter effect*) seperti "Build Your Own..." yang berubah secara dinamis.
- Mendukung berbagai format file teks (`.txt`, `.md`, dll).

## 📂 Struktur Folder
```
PROJECT1/
│── app.py                # Server Flask
│── tfidf/                 # Folder utama logika TF-IDF
│   ├── search.py
│   ├── preprocess.py
│   └── ...
│── templates/             # File HTML (frontend)
│── static/                # File CSS, JS, gambar
│── uploads/               # Folder upload dokumen
│── README.md               # Dokumentasi proyek
```

## 🚀 Instalasi & Penggunaan
1. **Clone repository ini**
   ```bash
   git clone https://github.com/username/PROJECT1.git
   cd PROJECT1
   ```

2. **Install dependencies**
   Pastikan Python 3 sudah terpasang, lalu jalankan:
   ```bash
   pip install -r requirements.txt
   ```

3. **Jalankan aplikasi**
   ```bash
   python app.py
   ```
   Akses di browser melalui `http://127.0.0.1:5000`.

4. **Upload file & mulai pencarian**
   - Masuk ke halaman utama.
   - Upload dokumen yang ingin dicari.
   - Gunakan kolom pencarian untuk melihat hasilnya.

## 🛠 Teknologi yang Digunakan
- **Python** (Flask, math, re)
- **HTML, CSS, JavaScript**
- **Bootstrap** (styling)
- **Typewriter.js** atau JavaScript manual untuk efek ketik.

## 📜 Lisensi
Proyek ini menggunakan lisensi MIT. Silakan digunakan, dimodifikasi, dan dikembangkan.

---
Dibuat dengan ❤️ untuk pembelajaran & eksperimen.
