import os
import re
import requests
import urllib.parse
from telebot.types import InputMediaPhoto

class FacebookDownloader:
    def __init__(self, bot):
        self.bot = bot

    def _clean_url(self, url):
        """Membongkar link /share/ dengan membaca HTML Meta Refresh karena FB sering memblokir redirect biasa"""
        if "/share/" in url or "fb.watch" in url:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                res = requests.get(url, headers=headers, timeout=10)
                html = res.text
                
                # Cari URL asli dari tag meta refresh atau canonical di dalam HTML
                meta_refresh = re.search(r'content="0;?\s*URL=([^"]+)"', html, re.IGNORECASE)
                if meta_refresh:
                    return meta_refresh.group(1).replace("&amp;", "&")
                    
                canonical = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', html, re.IGNORECASE)
                if canonical:
                    return canonical.group(1).replace("&amp;", "&")
                    
            except Exception as e:
                print(f"URL Clean Error: {e}")
        return url

    def _extract_photos_gallery_dl(self, url):
        """Mengekstrak URL foto/album Facebook menggunakan gallery-dl"""
        import subprocess
        
        gallery_dl_path = "gallery-dl"
        venv_bin = os.path.join(".venv", "Scripts", "gallery-dl.exe") if os.name == "nt" else os.path.join(".venv", "bin", "gallery-dl")
        if os.path.exists(venv_bin):
            gallery_dl_path = venv_bin
            
        cmd = [gallery_dl_path, "--range", "1-10", "-g", url]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if result.returncode == 0:
                urls = [line.strip() for line in result.stdout.splitlines() if line.strip() and "fbcdn" in line]
                return urls
            else:
                print(f"[DEBUG] gallery-dl error: {result.stderr}")
        except Exception as e:
            print(f"[DEBUG] Gagal menjalankan gallery-dl: {e}")
        return []

    def _download_video_ytdlp(self, url, chat_id):
        """Mengunduh video/reel Facebook menggunakan yt-dlp secara lokal"""
        import yt_dlp
        import glob
        import time
        
        timestamp = int(time.time())
        output_template = f"downloads/fb_{chat_id}_{timestamp}_%(id)s.%(ext)s"
        
        ydl_opts = {
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'format': 'best[height<=720]/best',
        }
        
        cookies_file = "cookies.txt"
        if os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # Cari file yang sesuai
                search_pattern = f"downloads/fb_{chat_id}_{timestamp}_*"
                found_files = glob.glob(search_pattern)
                if found_files:
                    return found_files[0]
        except Exception as e:
            print(f"[DEBUG] yt-dlp error: {e}")
        return None

    def download(self, message, url):
        chat_id = message.chat.id
        msg = self.bot.send_message(chat_id, "📥 Mengupas link Facebook... Mohon tunggu.")
        
        try:
            # 1. Bersihkan URL dari topeng /share/ 
            clean_url = self._clean_url(url)
            print(f"[DEBUG] Original: {url} | Clean: {clean_url}") 
            
            is_photo = bool(re.search(r'(/p/|/posts/|photo)', clean_url.lower()))

            # ==========================================
            # 📸 MODE DOWNLOAD FOTO (SINGLE / ALBUM)
            # ==========================================
            if is_photo:
                self.bot.edit_message_text("🔍 Mencari data album gambar...", chat_id=chat_id, message_id=msg.message_id)
                
                media_data = self._extract_photos_gallery_dl(clean_url)
                
                # Jika berhasil menemukan BANYAK gambar (Carousel)
                if isinstance(media_data, list) and len(media_data) > 1:
                    self.bot.edit_message_text("⬆️ Mengirim album foto ke obrolan...", chat_id=chat_id, message_id=msg.message_id)
                    media_group = []
                    
                    for i, media_url in enumerate(media_data[:10]): # Maksimal Telegram adalah 10 foto per album
                        if i == 0:
                            media_group.append(InputMediaPhoto(media_url, caption="📸 **Album Facebook**\n\n✅ Diunduh via Bot", parse_mode="Markdown"))
                        else:
                            media_group.append(InputMediaPhoto(media_url))
                    
                    self.bot.send_media_group(chat_id, media_group)
                    self.bot.delete_message(chat_id, msg.message_id)
                    return
                
                # Fallback: Jika gagal ambil album, ambil 1 gambar utama
                fallback_image = None
                if isinstance(media_data, list) and len(media_data) == 1:
                    fallback_image = media_data[0]
                else:
                    headers = {"User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"}
                    try:
                        res = requests.get(clean_url, headers=headers, timeout=10)
                        match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', res.text)
                        if match: fallback_image = match.group(1).replace("&amp;", "&")
                    except Exception as e:
                        print(f"Fallback og:image error: {e}")

                if fallback_image:
                    self.bot.edit_message_text("⬆️ Mengirim foto ke obrolan...", chat_id=chat_id, message_id=msg.message_id)
                    self.bot.send_photo(chat_id, fallback_image, caption="📸 **Foto Facebook**\n\n✅ Diunduh via Bot", parse_mode="Markdown")
                    self.bot.delete_message(chat_id, msg.message_id)
                    return
                
                print("[DEBUG] Gagal mendeteksi gambar, mencoba fallback video...")

            # ==========================================
            # 🎥 MODE DOWNLOAD VIDEO & REELS
            # ==========================================
            self.bot.edit_message_text("🔍 Mengekstrak video dari URL...", chat_id=chat_id, message_id=msg.message_id)
            
            video_file_path = self._download_video_ytdlp(clean_url, chat_id)
            
            if not video_file_path:
                self.bot.edit_message_text("❌ Gagal mendapatkan media dari postingan. Pastikan postingan bersifat Publik.", chat_id=chat_id, message_id=msg.message_id)
                return

            try:
                file_size = os.path.getsize(video_file_path) / (1024 * 1024)
                if file_size > 50:
                    self.bot.edit_message_text(f"❌ Gagal: Ukuran video terlalu besar ({file_size:.2f} MB). Batas Telegram Bot adalah 50 MB.", chat_id=chat_id, message_id=msg.message_id)
                    return

                self.bot.edit_message_text("⬆️ Mengirim video ke obrolan...", chat_id=chat_id, message_id=msg.message_id)
                
                with open(video_file_path, 'rb') as video_file:
                    self.bot.send_video(chat_id, video_file, caption="🎥 **Video Facebook**\n\n✅ Diunduh via Bot", parse_mode="Markdown", timeout=300)
                
                self.bot.delete_message(chat_id, msg.message_id)
            finally:
                if os.path.exists(video_file_path):
                    os.remove(video_file_path)
                
        except Exception as e:
            print(f"Facebook Downloader Error: {e}")
            try:
                self.bot.edit_message_text("❌ Terjadi kesalahan sistem saat memproses media.", chat_id=chat_id, message_id=msg.message_id)
            except:
                pass