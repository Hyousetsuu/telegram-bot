🤖 Asisten AI Telegram Multi-Fungsi
Ini bukan sekadar bot biasa. Ini adalah asisten AI Telegram yang ditenagai oleh Google Gemini, dirancang untuk menjadi alat "semua-dalam-satu" Anda.

Bot ini dapat diajak bicara untuk menjawab pertanyaan pengetahuan umum, sekaligus dilengkapi dengan berbagai tools produktivitas seperti downloader media sosial, kompresor file, konverter file, dan penyedia informasi real-time.

Semua fitur dirancang untuk bekerja secara intuitif. Cukup kirim link untuk mengunduh, kirim file untuk mengedit, atau kirim teks untuk mengobrol.

🚀 Fitur Utama
Bot ini menggabungkan beberapa fungsi utama ke dalam satu antarmuka yang mulus:

1. Asisten AI & Informasi
Asisten AI (Gemini): Ditenagai oleh gemini-2.5-flash, bot dapat menjawab pertanyaan pengetahuan umum, memberi ide, membuatkan kode, atau sekadar diajak ngobrol.

Info Cuaca Real-time: Memberikan cuaca saat ini DAN prediksi untuk hari berikutnya di lokasi yang diminta (didukung oleh OpenWeatherMap).

Berita Terkini: Mengambil berita terbaru dari Google News (gnews) berdasarkan topik, dengan dukungan pencarian internasional.

2. Downloader Media (Otomatis)
YouTube: Mengunduh video (MP4) atau audio (MP3) saat link dikirim.

TikTok: Mengunduh video tanpa watermark, audio, atau slideshow gambar.

Instagram: Mengunduh foto atau video (Reels/Post) dari link.

3. Alat Produktivitas (Otomatis)
Bot ini menggunakan handler cerdas. Cukup kirim file, dan bot akan menawarkan pilihan aksi:

Kompresor Gambar: Memperkecil ukuran file .jpg atau .png dengan 3 pilihan kualitas (Ringan, Sedang, Ekstrem).

Kompresor PDF: Mengoptimalkan dan memperkecil ukuran file .pdf (menggunakan pikepdf).

Konverter Gambar ke PDF: Mengubah file .jpg atau .png menjadi satu dokumen .pdf.

Konverter PDF ke Gambar: Mengubah halaman dari file .pdf menjadi beberapa gambar .jpg (maks. 5 halaman).

🧰 Teknologi & Library Utama
Proyek ini dibangun dengan Python 3.10+ dan memanfaatkan berbagai library modern:

Bot Framework: pyTelegramBotAPI

Model AI: google-generativeai

Downloader: yt-dlp (YouTube/TikTok), instaloader (Instagram)

Manipulasi File:

Pillow (Kompresi & Konversi Gambar)

pikepdf (Kompresi PDF)

PyMuPDF (fitz) (Konversi PDF ke Gambar)

Layanan Info: gnews (Berita), requests (Cuaca)

Konfigurasi: python-dotenv (Manajemen API Key)

PENTING: Proyek ini juga membutuhkan FFmpeg agar dapat menggabungkan video dan audio (khususnya untuk yt-dlp).

⚙️ Cara Menjalankan Secara Lokal
Clone Repository

Bash

git clone https://github.com/URL_REPOSITORY_ANDA.git
cd telegram-bot
Buat & Aktifkan Virtual Environment

Bash

# Buat venv
python -m venv .venv
# Aktifkan di Windows
.\.venv\Scripts\activate
Install Dependensi Pastikan ffmpeg sudah terinstal di sistem Anda. Lalu instal library Python:

Bash

pip install -r requirements.txt
Buat File .env Buat file bernama .env di direktori utama dan isi dengan API Key Anda.

Ini, TOML

# Token dari @BotFather
BOT_TOKEN="12345:ABCDEFG..."

# API Key dari Google AI Studio
GEMINI_API_KEY="AIzaSy..."

# API Key dari OpenWeatherMap
OPENWEATHER_API_KEY="abcdef..."

# Opsional (Sangat disarankan agar download IG stabil)
INSTAGRAM_USER="username_ig_anda"
INSTAGRAM_PASS="password_ig_anda"
Jalankan Bot

Bash

python main.py
🌐 Cara Menjalankan Online (Render.com)
Push seluruh file (termasuk requirements.txt) ke repository GitHub Anda.

Buka Render.com dan buat akun.

Klik "New" -> "Web Service" dan hubungkan ke repository GitHub Anda.

Isi bagian berikut saat setup:

Build Command: pip install -r requirements.txt

Start Command: python main.py

(PENTING) Buka tab "Environment" di dashboard Render Anda.

Klik "Add Environment Variable" dan tambahkan semua Key dari file .env Anda satu per satu (misal: Key: BOT_TOKEN, Value: 12345:ABCDEFG...).

Klik "Create Web Service". Render akan otomatis men-deploy bot Anda.

👨‍💻 Pengembang
Fiko nanda Ramadani

Lintang Wahyu Aji Saputro

Nabila Wahyu Ningtias

Dhian Joedhistiro

Egie Irawan

Bot yang sudah jadi: @JKW48_Bot