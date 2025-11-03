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
import socket

# ==============================
# 🔐 Load environment variables
# ==============================
load_dotenv()
try:
    socket.create_connection(("api.telegram.org", 443), timeout=10)
    print("✅ Koneksi ke Telegram API berhasil.")
except Exception as e:
    print(f"⚠️ Tidak bisa konek ke Telegram API: {e}")
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

        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4', res='360p').first()
        if stream is None:
            raise Exception("Stream tidak tersedia atau video dibatasi!")

        filename = "youtube_video.mp4"
        bot.send_message(message.chat.id, "⬇️ Mulai download video...")
        video_path = stream.download(filename=filename)

        size = os.path.getsize(video_path)
        bot.send_message(message.chat.id, f"✅ Download selesai. Ukuran file: {size / 1024 / 1024:.2f} MB")

        # ======= Jika file >45 MB, kompres ==========
        if size > 45 * 1024 * 1024:
            bot.send_message(message.chat.id, "📦 File besar terdeteksi, mencoba kompres ke 480p...")
            try:
                from moviepy.editor import VideoFileClip
                clip = VideoFileClip(video_path)
                compressed_path = "compressed_video.mp4"
                clip_resized = clip.resize(height=480)
                clip_resized.write_videofile(
                    compressed_path,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile="temp-audio.m4a",
                    remove_temp=True,
                    threads=4,
                    preset="ultrafast"
                )
                clip.close()
                os.remove(video_path)
                video_path = compressed_path
                size = os.path.getsize(video_path)
                bot.send_message(message.chat.id, f"✅ Kompres selesai. Ukuran baru: {size / 1024 / 1024:.2f} MB")
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ Gagal kompres video: {e}")

        # ========== Coba kirim file ke Telegram (lebih stabil) ==========
        bot.send_message(message.chat.id, "🎬 Mengirim video ke Telegram... (harap tunggu, bisa memakan waktu beberapa menit)")

        time.sleep(2)  # beri waktu agar file tidak terkunci

        def send_with_retry(path, caption, as_document=False):
            """Mengirim file dengan retry otomatis"""
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    with open(path, "rb") as f:
                        if as_document:
                            bot.send_document(
                                message.chat.id,
                                f,
                                timeout=300,  # tunggu hingga 5 menit
                                visible_file_name=os.path.basename(path)
                            )
                        else:
                            bot.send_video(
                                message.chat.id,
                                f,
                                timeout=300,  # tunggu hingga 5 menit
                                supports_streaming=True
                            )
                    return True
                except Exception as e:
                    print(f"⚠️ Percobaan {attempt+1}/{max_retries} gagal: {e}")
                    time.sleep(5)
            return False

        # 🔹 Coba kirim sebagai dokumen dulu (lebih aman)
        if send_with_retry(video_path, "🎥 Video berhasil diunduh!", as_document=True):
            bot.send_message(message.chat.id, "✅ Video berhasil dikirim sebagai dokumen!")
        else:
            bot.send_message(message.chat.id, "⚠️ Gagal kirim sebagai dokumen, mencoba kirim sebagai video...")
            if send_with_retry(video_path, "🎥 Video berhasil diunduh!", as_document=False):
                bot.send_message(message.chat.id, "✅ Video berhasil dikirim sebagai video!")
            else:
                bot.send_message(message.chat.id, "❌ Gagal mengirim video setelah beberapa kali percobaan.")


    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Terjadi error di download_youtube_video:\n{e}")

    finally:
        # bersihkan file lokal
        for file in ["youtube_video.mp4", "compressed_video.mp4", "temp-audio.m4a"]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass

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

    platform = detect_platform(text)
    if platform == "youtube":
        return download_youtube_video(message, text)
    elif platform == "tiktok":
        return download_tiktok_video(message, text)
    elif platform == "instagram":
        return download_instagram_video(message, text)

    keywords = ["download", "unduh", "save video", "ambil video"]
    if any(keyword in text.lower() for keyword in keywords):
        return bot.reply_to(
            message,
            "✅ Tentu! Silakan kirim link videonya ya 🎯\n"
            "YouTube, TikTok & Instagram bisa 👌"
        )

    try:
        response = model.generate_content(text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"🤖 AI error: {e}")


# ==============================
# 🚀 Start bot (Auto Reconnect)
# ==============================
if __name__ == "__main__":
    print("🤖 Bot sedang berjalan...")

    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except requests.exceptions.ConnectionError as e:
            print(f"⚠️ Koneksi ke Telegram terputus: {e}")
            time.sleep(10)  # tunggu 10 detik sebelum reconnect
            continue
        except Exception as e:
            print(f"⚠️ Error umum di polling: {e}")
            time.sleep(5)
            continue

