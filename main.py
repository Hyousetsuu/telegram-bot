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
def download_tiktok_media(message, url):
    try:
        bot.send_message(message.chat.id, "🎬 Mengambil postingan TikTok...")

        # download with resume
        def download_with_resume(url, final_path, temp_path, min_valid_size=20000, stream_timeout=200, max_attempts=5):
            if os.path.exists(final_path) and os.path.getsize(final_path) >= min_valid_size:
                return True

            for attempt in range(1, max_attempts + 1):
                try:
                    downloaded = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                    headers = {"Range": f"bytes={downloaded}-"} if downloaded > 0 else {}

                    with requests.get(url, headers=headers, stream=True, timeout=stream_timeout) as r:
                        if downloaded > 0 and r.status_code != 206:
                            try: os.remove(temp_path)
                            except: pass
                            downloaded = 0
                            r = requests.get(url, stream=True, timeout=stream_timeout)

                        r.raise_for_status()
                        mode = "ab" if downloaded else "wb"
                        with open(temp_path, mode) as f:
                            for chunk in r.iter_content(chunk_size=40960):
                                if chunk:
                                    f.write(chunk)

                    if os.path.exists(temp_path) and os.path.getsize(temp_path) >= min_valid_size:
                        if os.path.exists(final_path):
                            os.remove(final_path)
                        os.replace(temp_path, final_path)
                        return True

                    raise Exception("File incomplete")

                except Exception as e:
                    print(f"download_with_resume attempt {attempt}/{max_attempts} failed: {e}")
                    time.sleep(3)

            return False

        def send_media_group_safe(chat_id, paths):
            batch_size = 5
            delay_after_batch = 10

            index = 0
            while index < len(paths):
                batch = paths[index:index + batch_size]

                for p in batch:
                    if (not os.path.exists(p)) or (os.path.getsize(p) < 20000):
                        print(f"Skip corrupt: {p}")
                        continue

                    success = False
                    for attempt in range(6):  # ✅ retry lebih banyak
                        try:
                            with open(p, "rb") as f:
                                bot.send_photo(chat_id, f, timeout=180)  # ✅ timeout besar
                            success = True
                            break
                        except Exception as e:
                            print(f"send_photo failed ({attempt+1}/6): {e}")
                            time.sleep(4)

                    if success:
                        try: os.remove(p)  # ✅ Auto delete setelah terkirim
                        except: pass
                    else:
                        bot.send_message(chat_id, f"⚠️ Gagal kirim: {p}")

                index += batch_size
                if index < len(paths):
                    bot.send_message(chat_id, "⏳ Tunggu 10 detik sebelum lanjut...")
                    time.sleep(delay_after_batch)

        # API TikWM
        resp = requests.get("https://www.tikwm.com/api/", params={"url": url}, timeout=35)
        post_data = resp.json().get("data", {})

        # ✅ IMAGE MODE (FULL DOWNLOAD FIRST)
        images = post_data.get("images") or []
        if post_data.get("type") == "image" or images:
            img_urls = [img["url"] if isinstance(img, dict) else img for img in images]
            total = len(img_urls)
            bot.send_message(message.chat.id, f"🖼 Menemukan {total} gambar...")

            downloaded = []
            failed = 0

            # ✅ Download ALL first
            for i, u in enumerate(img_urls, start=1):
                fn = f"tiktok_pic_{i}.jpg"
                tp = fn + ".part"

                msg = bot.send_message(message.chat.id, f"⬇️ Download {i}/{total}...")
                ok = download_with_resume(u, fn, tp, min_valid_size=20000, max_attempts=10)

                try:
                    bot.delete_message(message.chat.id, msg.message_id)
                except:
                    pass

                if ok and os.path.exists(fn) and os.path.getsize(fn) > 20000:
                    downloaded.append(fn)
                else:
                    failed += 1
                    if os.path.exists(fn): os.remove(fn)
                    if os.path.exists(tp): os.remove(tp)

            if failed > 0:
                bot.send_message(message.chat.id, f"⚠️ {failed} gambar gagal di-download")

            if not downloaded:
                bot.send_message(message.chat.id, "❌ Tidak ada gambar valid untuk dikirim")
                return

            # ✅ SEND AFTER ALL DONE
            bot.send_message(message.chat.id, f"📤 Upload {len(downloaded)} gambar ke Telegram...")

            sent = 0
            for i in range(0, len(downloaded), 10):
                batch = downloaded[i:i+10]
                send_media_group_safe(message.chat.id, batch)
                sent += len(batch)
                bot.send_message(message.chat.id, f"✅ {sent}/{len(downloaded)} selesai")

            bot.send_message(message.chat.id, "🎯 Semua gambar berhasil dikirim ✅")
            return

        # ✅ VIDEO MODE
        video_url = post_data.get("play")
        if not video_url:
            raise Exception("URL video tidak ditemukan.")

        fn = "tiktok_video.mp4"
        tp = fn + ".part"
        bot.send_message(message.chat.id, "🎥 Mendownload video...")

        if not download_with_resume(video_url, fn, tp, min_valid_size=100000):
            raise Exception("Gagal download video!")

        size = os.path.getsize(fn)

        if size > 45*1024*1024:
            send_func = bot.send_document
            caption = "📦 Video TikTok"
        else:
            send_func = bot.send_video
            caption = "🎥 Video TikTok"

        success = False
        for attempt in range(6):  # ✅ retry upload
            try:
                with open(fn, "rb") as f:
                    send_func(message.chat.id, f, caption=caption, timeout=200)
                success = True
                break
            except Exception as e:
                print(f"send_video attempt {attempt+1} failed: {e}")
                time.sleep(6)

        if not success:
            raise Exception("Upload video gagal setelah 6 percobaan!")

        bot.send_message(message.chat.id, "✅ Video berhasil dikirim!")

    except Exception as e:
        print("download_tiktok_media error:", e)
        bot.send_message(message.chat.id, f"❌ Error: {e}")

    finally:
        for f in os.listdir():
            if f.endswith(".part") or f.startswith("tiktok_pic_") or f == "tiktok_video.mp4":
                try: os.remove(f)
                except: pass

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
        return download_tiktok_media(message, text)
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


