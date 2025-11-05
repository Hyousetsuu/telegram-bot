import os
import time
import re
import yt_dlp

class YouTubeDownloader:
    def __init__(self, bot):
        self.bot = bot

    def download(self, message, url: str):
        self.bot.send_message(message.chat.id, "⏳ Mengambil video dari YouTube...")
        time.sleep(2) # ✅ Delay anti rate limit

        try:
            ydl_opts = {
                'format': 'mp4',
                'outtmpl': 'youtube_video.%(ext)s',
                'merge_output_format': 'mp4',
                'noplaylist': True,  # ✅ hanya ambil 1 video meski ada playlist
                'ratelimit': 500000, # ✅ batas speed → anti blokir
                'sleep_interval_requests': 2, # ✅ jeda tiap request
                'ignoreerrors': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(result).replace(".webm", ".mp4")

            if not os.path.exists(filename):
                raise Exception("Download gagal, file tidak ditemukan")

            with open(filename, "rb") as f:
                self.bot.send_video(
                    message.chat.id,
                    f,
                    supports_streaming=True,
                    caption=f"🎬 {result.get('title','Video')}"
                )

            self.bot.send_message(message.chat.id, "✅ Selesai kirim video YouTube!")
            return True

        except Exception as e:
            print(f"YouTube download error: {e}")
            self.bot.send_message(message.chat.id, f"❌ YouTube Error: {e}")
            return False

        finally:
            for f in os.listdir():
                if f.startswith("youtube_video"):
                    try: os.remove(f)
                    except: pass
