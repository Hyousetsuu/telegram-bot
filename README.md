# 🤖 Asisten AI Telegram Multi-Fungsi

Ini bukan sekadar bot biasa — **ini adalah Asisten AI Telegram yang ditenagai oleh Google Gemini**, dirancang untuk menjadi alat *"semua-dalam-satu"* Anda.

Bot ini dapat diajak berbicara untuk menjawab pertanyaan pengetahuan umum, sekaligus dilengkapi dengan berbagai tools produktivitas seperti **downloader media sosial**, **kompresor file**, **konverter file**, dan **penyedia informasi real-time**.

Semua fitur dirancang untuk bekerja secara intuitif — cukup kirim link untuk mengunduh, kirim file untuk mengedit, atau kirim teks untuk mengobrol.

---

## 🚀 Fitur Utama

### 💬 Asisten AI & Informasi
- **Asisten AI (Gemini):** Ditenagai oleh `gemini-2.5-flash`, bot dapat menjawab pertanyaan pengetahuan umum, memberi ide, membuatkan kode, atau sekadar diajak ngobrol.  
- **Info Cuaca Real-time:** Memberikan informasi cuaca saat ini dan prediksi untuk hari berikutnya di lokasi yang diminta (menggunakan OpenWeatherMap).  
- **Berita Terkini:** Mengambil berita terbaru dari Google News (`gnews`) berdasarkan topik atau wilayah yang Anda minta.  

---

### 📥 Downloader Media (Otomatis)
- **YouTube:** Unduh video (MP4) atau audio (MP3) secara otomatis.  
- **TikTok:** Unduh video tanpa watermark, audio, atau slideshow gambar.  
- **Instagram:** Unduh foto atau video (Reels/Post).  

---

### 🧰 Alat Produktivitas (Otomatis)
Bot ini menggunakan *smart handler* — cukup kirim file, dan bot akan menawarkan aksi otomatis yang relevan.  

- **Kompresor Gambar:** Mengecilkan ukuran file `.jpg` atau `.png` dengan tiga pilihan kualitas (Ringan, Sedang, Ekstrem).  
- **Kompresor PDF:** Mengoptimalkan ukuran file `.pdf` menggunakan `pikepdf`.  
- **Konverter Gambar → PDF:** Menggabungkan beberapa gambar menjadi satu dokumen `.pdf`.  
- **Konverter PDF → Gambar:** Mengubah setiap halaman `.pdf` menjadi beberapa file `.jpg` (maksimal 5 halaman).  

---

## 🧠 Teknologi & Library Utama

| Kategori | Teknologi / Library |
|-----------|--------------------|
| **Bahasa Pemrograman** | Python 3.10+ |
| **Framework Bot** | [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) |
| **Model AI** | [google-generativeai](https://pypi.org/project/google-generativeai/) |
| **Downloader** | yt-dlp (YouTube/TikTok), instaloader (Instagram) |
| **Manipulasi File** | Pillow, pikepdf, PyMuPDF (fitz) |
| **Layanan Informasi** | gnews, requests |
| **Konfigurasi Lingkungan** | python-dotenv |
| **Dependensi Eksternal** | FFmpeg *(wajib diinstal untuk menggabungkan video & audio)* |

---

## ⚙️ Cara Menjalankan Secara Lokal

### 1️⃣ Clone Repository
```bash
git clone https://github.com/Hyousetsuu/telegram-bot
cd telegram-bot
2️⃣ Buat & Aktifkan Virtual Environment
bash
Salin kode
# Buat environment
python -m venv .venv

# Aktifkan di Windows
.venv\Scripts\activate
3️⃣ Install Dependensi
Pastikan FFmpeg sudah terinstal di sistem Anda, lalu jalankan:

bash
Salin kode
pip install -r requirements.txt
4️⃣ Buat File .env
Buat file bernama .env di direktori utama dan isi dengan API key Anda seperti berikut:

toml
Salin kode
# Token dari @BotFather
BOT_TOKEN="12345:ABCDEFG..."

# API Key dari Google AI Studio
GEMINI_API_KEY="AIzaSy..."

# API Key dari OpenWeatherMap
OPENWEATHER_API_KEY="abcdef..."

# (Opsional - agar download Instagram lebih stabil)
INSTAGRAM_USER="username_ig_anda"
INSTAGRAM_PASS="password_ig_anda"
5️⃣ Jalankan Bot
bash
Salin kode
python main.py
🌐 Cara Menjalankan Secara Online (Render.com)
Push seluruh file (termasuk requirements.txt) ke repository GitHub Anda.

Masuk ke Render.com dan buat akun.

Klik "New" → "Web Service" dan hubungkan ke repository GitHub Anda.

Isi konfigurasi berikut:

Build Command: pip install -r requirements.txt

Start Command: python main.py

Buka tab Environment → klik "Add Environment Variable", lalu tambahkan semua key dari file .env satu per satu.

Klik "Create Web Service" — Render akan otomatis men-deploy bot Anda.

👨‍💻 Pengembang
Nama	Peran
Fiko Nanda Ramadani	Developer
Lintang Wahyu Aji Saputro	Developer
Nabila Wahyu Ningtias	Developer
Dhian Joedhistiro	Developer
Egie Irawan	Developer

🔗 Bot Aktif
🌟 Coba langsung di Telegram: @JKW48_Bot