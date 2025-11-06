import os
import time
import requests
from io import BytesIO
from telebot import TeleBot

class TikTokDownloader:
    def __init__(self, bot: TeleBot):
        self.bot = bot
        self.api_url = "https://www.tikwm.com/api/"

    def _get_data(self, url):
        """Ambil data dari API TikWM"""
        res = requests.post(self.api_url, data={"url": url})
        if res.status_code != 200:
            return None
        data = res.json()
        if not data.get("data"):
            return None
        return data["data"]

    def _full_url(self, path: str):
        """Pastikan URL valid (tidak double https://)"""
        if path.startswith("http"):
            return path
        return f"https://www.tikwm.com{path}"

    # 🎥 Download Video (tanpa watermark)
    def download_video(self, message, url):
        try:
            self.bot.send_message(message.chat.id, "⏳ Mengambil video dari TikTok...")
            data = self._get_data(url)
            if not data:
                self.bot.send_message(message.chat.id, "❌ Gagal mengambil data video.")
                return

            video_url = self._full_url(data.get("play", ""))
            video_data = requests.get(video_url).content

            file = BytesIO(video_data)
            file.name = "tiktok.mp4"
            caption = f"🎬 {data.get('title', 'Video TikTok')}"

            self.bot.send_video(message.chat.id, file, caption=caption)
        except Exception as e:
            self.bot.send_message(message.chat.id, f"❌ Gagal unduh video: {e}")

    # 🎧 Download Audio
    def download_audio(self, message, url):
        try:
            self.bot.send_message(message.chat.id, "🎵 Mengambil audio TikTok...")
            data = self._get_data(url)
            if not data:
                self.bot.send_message(message.chat.id, "❌ Gagal mengambil data audio.")
                return

            music_url = self._full_url(data.get("music", ""))
            music_data = requests.get(music_url).content

            file = BytesIO(music_data)
            file.name = "tiktok.mp3"
            caption = f"🎶 Audio dari: {data.get('title', '-')}"
            self.bot.send_audio(message.chat.id, file, caption=caption)
        except Exception as e:
            self.bot.send_message(message.chat.id, f"❌ Gagal unduh audio: {e}")

    # 🖼 Download Gambar
    def download_images(self, message, url):
        try:
            self.bot.send_message(message.chat.id, "🖼 Mengambil gambar dari TikTok...")
            data = self._get_data(url)
            if not data or "images" not in data or not data["images"]:
                self.bot.send_message(message.chat.id, "❌ Tidak ditemukan gambar pada postingan ini.")
                return

            for i, img_path in enumerate(data["images"], start=1):
                img_url = self._full_url(img_path)
                img_data = requests.get(img_url).content
                file = BytesIO(img_data)
                file.name = f"tiktok_image_{i}.jpg"
                self.bot.send_photo(message.chat.id, file)

            self.bot.send_message(message.chat.id, "✅ Semua gambar berhasil diunduh!")
        except Exception as e:
            self.bot.send_message(message.chat.id, f"❌ Gagal unduh gambar: {e}")
