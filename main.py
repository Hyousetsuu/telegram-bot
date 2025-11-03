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
            """Mengirim file ke Telegram dengan retry otomatis"""
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    with open(path, "rb") as f:
                        if as_document:
                            bot.send_document(
                                message.chat.id,
                                f,
                                caption=caption,
                                timeout=600,  # 10 menit
                                disable_notification=False
                            )
                        else:
                            bot.send_video(
                                message.chat.id,
                                f,
                                caption=caption,
                                timeout=600,
                                supports_streaming=True
                            )
                    return True
                except Exception as e:
                    print(f"⚠️ Percobaan {attempt+1}/{max_retries} gagal: {e}")
                    bot.send_message(
                        message.chat.id,
                        f"⚠️ Percobaan {attempt+1}/{max_retries} gagal, mencoba lagi..."
                    )
                    time.sleep(10)
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

# ==============================
# 🎬 TikTok Downloader (lebih stabil)
# ==============================
def download_tiktok_video(message, url):
    try:
        bot.send_message(message.chat.id, "🎬 Mengambil video TikTok...")

        filename = "tiktok_video.mp4"
        success = False

        # 🔁 Coba download video maksimal 3 kali
        for attempt in range(3):
            try:
                resp = requests.get("https://www.tikwm.com/api/", params={"url": url}, timeout=15)
                data = resp.json()
                video_url = data.get("data", {}).get("play")
                if not video_url:
                    raise Exception("Link video tidak ditemukan.")

                # Download video dengan stream 
                with requests.get(video_url, stream=True, timeout=120) as r:
                    r.raise_for_status()
                    with open(filename, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                success = True
                break  # keluar dari loop kalau berhasil download

            except Exception as e:
                print(f"⚠️ Percobaan {attempt+1}/3 gagal download: {e}")
                bot.send_message(message.chat.id, f"⚠️ Percobaan {attempt+1}/3 gagal download, mencoba lagi...")
                time.sleep(5)

        if not success:
            bot.send_message(message.chat.id, "❌ Gagal mengunduh video TikTok setelah 3 percobaan.")
            return

        # 🔍 Cek ukuran file
        size = os.path.getsize(filename)
        bot.send_message(message.chat.id, f"✅ Download selesai. Ukuran file: {size / 1024 / 1024:.2f} MB")

        # ========================
        # 🔁 Kirim ke Telegram (retry upload)
        # ========================
        def send_with_retry(path, caption, as_document=False):
            """Mengirim file ke Telegram dengan retry otomatis"""
            max_retries = 3
            retry_delay = 15  # jeda antar percobaan dalam detik
            upload_timeout = 900  # waktu maksimum upload 15 menit

            for attempt in range(max_retries):
                try:
                    with open(path, "rb") as f:
                        if as_document:
                            bot.send_document(
                                message.chat.id,
                                f,
                                caption=caption,
                                timeout=upload_timeout
                            )
                        else:
                            bot.send_video(
                                message.chat.id,
                                f,
                                caption=caption,
                                timeout=upload_timeout,
                                supports_streaming=True
                            )
                    return True
                except Exception as e:
                    print(f"⚠️ Percobaan {attempt+1}/{max_retries} gagal upload: {e}")
                    bot.send_message(
                        message.chat.id,
                        f"⚠️ Upload percobaan {attempt+1}/{max_retries} gagal (coba lagi {retry_delay}s)..."
                    )
                    time.sleep(retry_delay)
            return False

        bot.send_message(message.chat.id, "🎬 Mengirim video ke Telegram... (harap tunggu beberapa menit)")

        # Jika file >45MB → kirim sebagai dokumen
        as_doc = size > 45 * 1024 * 1024
        if send_with_retry(filename, "🎥 Video TikTok berhasil diunduh!", as_document=as_doc):
            bot.send_message(message.chat.id, "✅ Video berhasil dikirim!")
        else:
            bot.send_message(message.chat.id, "❌ Gagal mengirim video setelah beberapa percobaan.")

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Gagal download TikTok.\nError: {e}")

    finally:
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass

# ==============================
# 📸 Instagram Downloader (pakai alternatif)
# ==============================
def download_instagram_video(message, url):
    try:
        bot.send_message(message.chat.id, "📸 Mengambil video Instagram...")
        # Gunakan API alternatif, lebih stabil
        resp = requests.get("https://instasupersave.com/api/convert", params={"url": url}, timeout=20)
        data = resp.json()
        if not data or "url" not in data.get("media", [{}])[0]:
            raise Exception("Tidak menemukan video valid.")
        video_url = data["media"][0]["url"]
        filename = "instagram_video.mp4"
        with requests.get(video_url, stream=True, timeout=120) as r:
            with open(filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        bot.send_video(message.chat.id, open(filename, "rb"), supports_streaming=True)
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
            time.sleep(10)
            continue
        except ConnectionResetError as e:
            print(f"⚠️ Koneksi direset oleh host: {e}")
            time.sleep(10)
            continue
        except Exception as e:
            print(f"⚠️ Error umum di polling: {e}")
            time.sleep(5)
            continue


