import instaloader
import os
import re
import shutil # Kita pakai shutil untuk menghapus folder

class InstagramDownloader:
    def __init__(self, bot):
        self.bot = bot
        self.username = os.getenv("INSTAGRAM_USER")
        self.password = os.getenv("INSTAGRAM_PASS")
        
        self.session_path = "ig_session"
        if not os.path.exists(self.session_path):
            os.makedirs(self.session_path)
            
        self.loader = instaloader.Instaloader(
            download_video_thumbnails=False, 
            save_metadata=False, 
            compress_json=False,
            # HAPUS dirname_pattern DARI SINI
            # Ini adalah salah satu penyebab kebingungan path
        )
        
        self._login()

    def _login(self):
        """Mencoba login atau memuat session yang ada."""
        if not self.username or not self.password:
            print("⚠️ Peringatan: INSTAGRAM_USER/PASS tidak ada di .env. Download IG mungkin akan gagal.")
            return

        # Tentukan path file session DENGAN BENAR
        session_file = os.path.join(self.session_path, f"session-{self.username}.json.xz")
        
        try:
            if os.path.exists(session_file):
                print("Memuat session Instagram...")
                self.loader.load_session_from_file(self.username, session_file)
                print("Session Instagram berhasil dimuat.")
            else:
                print("Melakukan login baru ke Instagram...")
                self.loader.login(self.username, self.password)
                print("Login Instagram berhasil. Menyimpan session...")
                self.loader.save_session_to_file(session_file)
                print("Session Instagram berhasil disimpan.")
        except Exception as e:
            print(f"❌ Gagal login Instagram: {e}. Download mungkin akan gagal.")

    def download(self, message, url: str):
        target_dir = None # Ini adalah folder 'ig_temp_...'
        try:
            status_msg = self.bot.send_message(message.chat.id, "⏳ Mengambil media dari Instagram...")

            shortcode_match = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)/?", url)
            if not shortcode_match:
                raise Exception("URL Instagram tidak valid.")
            shortcode = shortcode_match.group(1)
            
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            target_dir = f"ig_temp_{shortcode}"
            
            self.bot.edit_message_text("⬇️ Mengunduh media...", message.chat.id, status_msg.message_id)
            # Instaloader akan men-download ke: 'ig_temp_SHORTCODE/NAMA_PROFIL/'
            self.loader.download_post(post, target=target_dir)

            # --- PERBAIKAN LOGIKA PENCARIAN FILE ---
            # 1. Cari sub-folder yang dibuat instaloader
            subfolders = [f.path for f in os.scandir(target_dir) if f.is_dir()]
            if not subfolders:
                raise Exception("Instaloader tidak membuat subfolder profil.")
                
            actual_download_path = subfolders[0] # Ini adalah path 'ig_temp_.../NAMA_PROFIL'

            # 2. Cari file di dalam sub-folder tersebut
            files = [os.path.join(actual_download_path, f) for f in os.listdir(actual_download_path) if f.endswith(('.jpg', '.mp4'))]
            if not files:
                raise Exception("Tidak menemukan file media di dalam subfolder.")
            # ----------------------------------------

            self.bot.edit_message_text(f"⬆️ Mengirim {len(files)} media...", message.chat.id, status_msg.message_id)
            for fpath in files:
                with open(fpath, "rb") as media:
                    if fpath.endswith(".mp4"):
                        self.bot.send_video(message.chat.id, media, caption="🎬 Video Instagram", timeout=120)
                    else:
                        self.bot.send_photo(message.chat.id, media, caption="🖼 Foto Instagram", timeout=120)

            self.bot.delete_message(message.chat.id, status_msg.message_id)
            return True

        except Exception as e:
            print(f"Instagram download error: {e}")
            if "403 Forbidden" in str(e) or "login required" in str(e) or "Too many requests" in str(e):
                error_msg = "❌ Gagal: Instagram memblokir saya (403). Sesi login mungkin tidak valid atau terlalu banyak permintaan. Coba lagi nanti."
            else:
                error_msg = f"❌ Instagram Error: {e}"
                
            if 'status_msg' in locals():
                self.bot.edit_message_text(error_msg, message.chat.id, status_msg.message_id)
            else:
                self.bot.send_message(message.chat.id, error_msg)
            return False

        finally:
            # Membersihkan folder 'ig_temp_...' (yang berisi sub-folder)
            if target_dir and os.path.exists(target_dir):
                try:
                    shutil.rmtree(target_dir)
                except Exception as e:
                    print(f"Gagal membersihkan folder {target_dir}: {e}")