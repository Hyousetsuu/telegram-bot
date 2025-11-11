import os
import time
import glob
import yt_dlp
from telebot import types

class YouTubeDownloader:
    def __init__(self, bot):
        self.bot = bot
        self.download_path = "downloads"
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def send_format_buttons(self, message):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📹 Video (MP4)", callback_data="yt_mp4"),
            types.InlineKeyboardButton("🎵 Audio (MP3)", callback_data="yt_mp3")
        )
        self.bot.send_message(message.chat.id, "🎬 Pilih format unduhan YouTube:", reply_markup=markup)

    def download(self, message, url: str, format_type="mp4"):
        status_msg = self.bot.send_message(message.chat.id, f"⏳ Memproses {format_type.upper()}... Mohon tunggu.")
        
        try:
            timestamp = int(time.time())
            output_template = os.path.join(self.download_path, f"{timestamp}_%(id)s.%(ext)s")

            ydl_opts = {
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
            }

            if format_type == "mp3":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            else:
                # BATASI KUALITAS VIDEO agar tidak terlalu besar (max 720p)
                # 'best[height<=720]' akan mencari video terbaik yang resolusinya tidak lebih dari 720p
                ydl_opts.update({
                    'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
                     'merge_output_format': 'mp4',
                })

            # 1. DOWNLOAD
            self.bot.edit_message_text(f"⬇️ Sedang mengunduh {format_type.upper()} dari YouTube...", message.chat.id, status_msg.message_id)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_title = info.get('title', 'Video YouTube')

            # 2. CARI FILE
            search_pattern = os.path.join(self.download_path, f"{timestamp}_*")
            found_files = glob.glob(search_pattern)
            if not found_files: raise Exception("File tidak ditemukan.")
            final_file_path = found_files[0]

            # 3. CEK UKURAN FILE (PENTING!)
            file_size = os.path.getsize(final_file_path) / (1024 * 1024) # Konversi ke MB
            if file_size > 50:
                self.bot.edit_message_text(f"❌ Gagal: Ukuran file terlalu besar ({file_size:.2f} MB). Batas Telegram Bot hanya 50 MB.", message.chat.id, status_msg.message_id)
                os.remove(final_file_path)
                return False

            # 4. UPLOAD (Tambah timeout jadi 5 menit agar lebih sabar)
            self.bot.edit_message_text(f"⬆️ Mengirim {format_type.upper()} ({file_size:.1f} MB)...", message.chat.id, status_msg.message_id)
            with open(final_file_path, 'rb') as file:
                if format_type == "mp3":
                    self.bot.send_audio(message.chat.id, file, caption=f"🎵 {video_title}", timeout=300)
                else:
                    self.bot.send_video(message.chat.id, file, caption=f"🎬 {video_title}", supports_streaming=True, timeout=300)

            self.bot.delete_message(message.chat.id, status_msg.message_id)
            os.remove(final_file_path)
            return True

        except Exception as e:
            print(f"YouTube Error: {e}")
            error_msg = "❌ Gagal memproses video. Pastikan link valid dan tidak dikunci region."
            if "too large" in str(e) or "Entity Too Large" in str(e):
                error_msg = "❌ File terlalu besar untuk dikirim bot."
                
            try:
                self.bot.edit_message_text(error_msg, message.chat.id, status_msg.message_id)
            except:
                self.bot.send_message(message.chat.id, error_msg)
                
            # Bersihkan file jika ada sisa
            for f in glob.glob(os.path.join(self.download_path, f"{timestamp}_*")):
                try: os.remove(f)
                except: pass
            return False