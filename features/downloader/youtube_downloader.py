import time
import requests
from io import BytesIO
from telebot import types

import yt_dlp

class YouTubeDownloader:
    def __init__(self, bot):
        self.bot = bot

    # -------------------------
    # Tombol format
    # -------------------------
    def send_format_buttons(self, message, url):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📹 Download MP4", callback_data=f"yt_mp4|{url}"),
            types.InlineKeyboardButton("🎵 Download MP3", callback_data=f"yt_mp3|{url}")
        )
        self.bot.send_message(message.chat.id, "🎬 Pilih format unduhan YouTube:", reply_markup=markup)

    # -------------------------
    # Download video/audio
    # -------------------------
    def download(self, message, url: str, format_type="mp4", max_retries=3):
        for attempt in range(1, max_retries + 1):
            try:
                self.bot.send_message(message.chat.id, f"⏳ Mengunduh YouTube {format_type.upper()}... (Percobaan {attempt}/{max_retries})")
                time.sleep(1)

                # -------------------------
                # Pilihan format
                # -------------------------
                if format_type == "mp3":
                    ydl_opts = {
                        'format': 'bestaudio[ext=m4a]/bestaudio',
                        'noplaylist': True,
                        'quiet': True,
                        'extract_flat': True,
                    }
                else:  # mp4
                    ydl_opts = {
                        'format': 'best[ext=mp4]/best',
                        'noplaylist': True,
                        'quiet': True,
                    }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if format_type == "mp3":
                        audio_url = info.get("url")
                        audio_data = requests.get(audio_url, timeout=15).content
                        file = BytesIO(audio_data)
                        file.name = "youtube_audio.m4a"
                        caption = f"🎵 {info.get('title', 'Audio YouTube')}"
                        self.bot.send_audio(message.chat.id, file, caption=caption)
                    else:
                        # MP4 progressive check
                        video_url = info.get("url")
                        if not video_url:
                            self.bot.send_message(message.chat.id, "❌ Video ini hanya DASH, tidak bisa dikirim tanpa FFmpeg.")
                            return
                        video_data = requests.get(video_url, timeout=30).content
                        file = BytesIO(video_data)
                        file.name = "youtube_video.mp4"
                        caption = f"🎬 {info.get('title', 'Video YouTube')}"
                        self.bot.send_video(message.chat.id, file, caption=caption, supports_streaming=True)

                self.bot.send_message(message.chat.id, f"✅ Selesai kirim {format_type.upper()}!")
                return True

            except requests.exceptions.RequestException as e:
                if attempt == max_retries:
                    self.bot.send_message(message.chat.id, f"❌ Gagal: {e}")
                    return False
                time.sleep(2)

            except Exception as e:
                if attempt == max_retries:
                    self.bot.send_message(message.chat.id, f"❌ Gagal: {e}")
                    return False
                time.sleep(2)
