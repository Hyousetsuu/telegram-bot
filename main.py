import telebot
from telebot import types
from pytubefix import YouTube
import requests
import os
import re
from dotenv import load_dotenv
import google.generativeai as genai
import time
from telebot import apihelper
from telebot import util

# ==============================
# 🔐 Load environment variables
# ==============================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN:
    raise Exception("❌ BOT_TOKEN tidak ditemukan di .env")

if not GEMINI_API_KEY:
    raise Exception("❌ GEMINI_API_KEY tidak ditemukan di .env")

bot = telebot.TeleBot(TOKEN)
apihelper.SESSION_RETRY = True
apihelper.RETRIES = 5
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")

# ==============================
# 🧠 Fungsi Deteksi Link
# ==============================
def detect_platform(url: str):
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "tiktok.com" in url:
        return "tiktok"
    elif "instagram.com" in url or "instagr.am" in url:
        return "instagram"
    return None


# ==============================
# 🎥 Downloader Functions
# ==============================
def download_youtube_video(message, url):
    try:
        bot.send_message(message.chat.id, "⏳ Sedang memproses video YouTube...")

        # Tambahkan timeout pada YouTube object
        yt = YouTube(url, timeout=20)

        # Ambil resolusi tertinggi yang paling stabil
        stream = yt.streams.get_highest_resolution()

        if stream is None:
            raise Exception("Stream tidak tersedia atau video dibatasi!")

        filename = "youtube_video.mp4"

        # ✅ Retry download 3x jika timeout
        for attempt in range(3):
            try:
                video_path = stream.download(filename="youtube_video.mp4", timeout=60)
                break
            except Exception as e:
                if attempt == 2:
                    raise e
                time.sleep(2)  # tunggu dulu sebelum mencoba lagi

        size = os.path.getsize(video_path)

        # Kirim sesuai batas file Telegram
        if size > 50 * 1024 * 1024:
            bot.send_message(message.chat.id, "📦 File besar, mengirim sebagai dokumen...")
            bot.send_document(message.chat.id, open(video_path, "rb"))
        else:
            bot.send_video(message.chat.id, open(video_path, "rb"))

        os.remove(video_path)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Gagal download YouTube.\nError: {e}")



def download_tiktok_video(message, url):
    try:
        bot.send_message(message.chat.id, "🎬 Mengambil video TikTok...")
        resp = requests.get("https://www.tikwm.com/api/", params={"url": url}, timeout=10).json()
        video_url = resp.get("data", {}).get("play")
        if not video_url:
            raise Exception("Tidak menemukan link video.")
        filename = "tiktok_video.mp4"
        with open(filename, "wb") as f:
            f.write(requests.get(video_url, timeout=20).content)
        bot.send_video(message.chat.id, open(filename, "rb"))
        os.remove(filename)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Gagal download TikTok.\nError: {e}")


def download_instagram_video(message, url):
    try:
        bot.send_message(message.chat.id, "📸 Mengambil video Instagram...")
        resp = requests.post(
            "https://snapinsta.app/api/ajaxSearch",
            data={"q": url, "t": "media"},
            headers={
                "User-Agent": "Mozilla/5.0",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://snapinsta.app/"
            },
            timeout=15
        )
        html = resp.text
        match = re.search(r'href="(https://[^"]+\.mp4)"', html)
        if not match:
            raise Exception("Tidak menemukan link video valid.")
        video_url = match.group(1)
        filename = "instagram_video.mp4"
        with open(filename, "wb") as f:
            f.write(requests.get(video_url, timeout=20).content)
        bot.send_video(message.chat.id, open(filename, "rb"))
        os.remove(filename)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Gagal download Instagram.\nError: {e}")


# ==============================
# 💬 Handler utama (AI + Auto Link)
# ==============================
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    text = message.text.strip()
    
    # Jika pesan adalah link video → JANGAN pakai AI
    platform = detect_platform(text)
    if platform == "youtube":
        return download_youtube_video(message, text)
    elif platform == "tiktok":
        return download_tiktok_video(message, text)
    elif platform == "instagram":
        return download_instagram_video(message, text)

    # Jika user minta download tapi belum kasih link
    keywords = ["download", "unduh", "save video", "ambil video"]
    if any(keyword in text.lower() for keyword in keywords):
        return bot.reply_to(
            message,
            "✅ Tentu! Silakan kirim link videonya ya 🎯\n"
            "YouTube, TikTok & Instagram bisa 👌"
        )

    # Jika bukan link dan bukan permintaan download → pakai AI
    try:
        response = model.generate_content(text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"🤖 AI error: {e}")



# ==============================
# 🚀 Start bot
# ==============================
print("🤖 Bot sedang berjalan...")

while True:
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=10, restart_on_change=True)
    except Exception as e:
        # Jangan spam error, cukup logging singkat
        print("⚠️ Koneksi terputus, mencoba lagi...")
        time.sleep(5)

