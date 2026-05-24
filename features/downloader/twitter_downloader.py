import os
import re
import requests
import subprocess
from telebot.types import InputMediaPhoto

class TwitterDownloader:
    def __init__(self, bot):
        self.bot = bot

    def _extract_photos_gallery_dl(self, url):
        """Mengekstrak URL foto dari Twitter menggunakan gallery-dl"""
        gallery_dl_path = "gallery-dl"
        venv_bin = os.path.join(".venv", "Scripts", "gallery-dl.exe") if os.name == "nt" else os.path.join(".venv", "bin", "gallery-dl")
        if os.path.exists(venv_bin):
            gallery_dl_path = venv_bin
            
        cmd = [gallery_dl_path, "-g", url]
        
        # Gunakan cookies jika ada
        if os.path.exists("cookies.txt"):
            cmd.extend(["--cookies", "cookies.txt"])
            
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if result.returncode == 0:
                urls = []
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("http") and ("twimg.com" in line or "x.com" in line):
                        urls.append(line)
                return urls
            else:
                print(f"[DEBUG] gallery-dl error on twitter: {result.stderr}")
        except Exception as e:
            print(f"[DEBUG] Gagal menjalankan gallery-dl: {e}")
        return []

    def _download_video_ytdlp(self, url, chat_id):
        """Mengunduh video/gif menggunakan yt-dlp secara lokal"""
        import yt_dlp
        import glob
        import time
        
        timestamp = int(time.time())
        output_template = f"downloads/tw_{chat_id}_{timestamp}_%(id)s.%(ext)s"
        
        ydl_opts = {
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
        }
        
        if os.path.exists("cookies.txt"):
            ydl_opts['cookiefile'] = "cookies.txt"
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                search_pattern = f"downloads/tw_{chat_id}_{timestamp}_*"
                found_files = glob.glob(search_pattern)
                if found_files:
                    return found_files[0]
        except Exception as e:
            print(f"[DEBUG] yt-dlp error on twitter: {e}")
        return None

    def download(self, message, url):
        chat_id = message.chat.id
        msg = self.bot.send_message(chat_id, "📥 Memproses link Twitter/X... Mohon tunggu.")
        
        try:
            # 1. Coba download Video / GIF dengan yt-dlp
            self.bot.edit_message_text("🔍 Mengunduh video/GIF dari Twitter...", chat_id=chat_id, message_id=msg.message_id)
            video_file_path = self._download_video_ytdlp(url, chat_id)
            
            if video_file_path:
                try:
                    file_size = os.path.getsize(video_file_path) / (1024 * 1024)
                    if file_size > 50:
                        self.bot.edit_message_text(f"❌ Gagal: Ukuran video terlalu besar ({file_size:.2f} MB). Batas Telegram Bot adalah 50 MB.", chat_id=chat_id, message_id=msg.message_id)
                        return

                    self.bot.edit_message_text("⬆️ Mengirim video ke obrolan...", chat_id=chat_id, message_id=msg.message_id)
                    
                    with open(video_file_path, 'rb') as video_file:
                        self.bot.send_video(chat_id, video_file, caption="🎥 **Video Twitter/X**\n\n✅ Diunduh via Bot", parse_mode="Markdown", timeout=300)
                    
                    self.bot.delete_message(chat_id, msg.message_id)
                finally:
                    if os.path.exists(video_file_path):
                        os.remove(video_file_path)
                return

            # 2. Jika yt-dlp gagal (tidak ada video), coba mode FOTO dengan gallery-dl
            self.bot.edit_message_text("🔍 Mencari foto di tweet ini...", chat_id=chat_id, message_id=msg.message_id)
            photos = self._extract_photos_gallery_dl(url)
            
            if photos:
                self.bot.edit_message_text("⬆️ Mengirim foto Twitter ke obrolan...", chat_id=chat_id, message_id=msg.message_id)
                if len(photos) > 1:
                    media_group = []
                    for i, photo_url in enumerate(photos[:10]):
                        if i == 0:
                            media_group.append(InputMediaPhoto(photo_url, caption="📸 **Foto Twitter/X**\n\n✅ Diunduh via Bot", parse_mode="Markdown"))
                        else:
                            media_group.append(InputMediaPhoto(photo_url))
                    self.bot.send_media_group(chat_id, media_group)
                else:
                    self.bot.send_photo(chat_id, photos[0], caption="📸 **Foto Twitter/X**\n\n✅ Diunduh via Bot", parse_mode="Markdown")
                
                self.bot.delete_message(chat_id, msg.message_id)
                return

            # 3. Jika keduanya gagal
            self.bot.edit_message_text("❌ Gagal mendapatkan media dari postingan Twitter. Pastikan tweet bersifat publik dan memiliki media (Foto/Video).", chat_id=chat_id, message_id=msg.message_id)

        except Exception as e:
            print(f"Twitter Downloader Error: {e}")
            try:
                self.bot.edit_message_text("❌ Terjadi kesalahan sistem saat memproses link Twitter.", chat_id=chat_id, message_id=msg.message_id)
            except:
                pass
