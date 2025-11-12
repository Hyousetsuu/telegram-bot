import instaloader
import os
import re
import shutil 

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
        )
        
        self._login()

    def _login(self):
        """Mencoba login atau memuat session yang ada."""
        if not self.username or not self.password:
            print("⚠️ Peringatan: INSTAGRAM_USER/PASS tidak ada di .env. Download IG mungkin akan gagal.")
            return

        session_file = os.path.join(self.session_path, f"session-{self.username}.json.xz")
        
        try:
            if os.path.exists(session_file):
                print("Mencoba memuat session Instagram yang ada...")
                self.loader.load_session_from_file(self.username, session_file)
                
                # Cek apakah session yang dimuat valid
                if not self.loader.context.is_logged_in:
                    # Jika tidak valid, lempar error agar login baru
                    raise Exception("Session file ada tapi tidak valid (gagal login).")
                
                print("Session Instagram berhasil dimuat.")
            else:
                # Jika file tidak ada, paksa login baru
                raise Exception("Session file tidak ditemukan, login baru diperlukan.")
                
        except Exception as e:
            # Jika GAGAL memuat session (atau file tidak ada), lakukan login baru
            print(f"Info: {e}. Melakukan login baru ke Instagram...")
            try:
                self.loader.login(self.username, self.password)
                print("Login Instagram berhasil. Menyimpan session...")
                self.loader.save_session_to_file(session_file)
                print("Session Instagram berhasil disimpan.")
            except Exception as login_err:
                print(f"❌ GAGAL LOGIN BARU: {login_err}. Download IG akan gagal.")

    def download(self, message, url: str):
        target_dir = None 
        try:
            status_msg = self.bot.send_message(message.chat.id, "⏳ Mengambil media dari Instagram...")

            shortcode_match = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)/?", url)
            if not shortcode_match:
                raise Exception("URL Instagram tidak valid.")
            shortcode = shortcode_match.group(1)
            
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            target_dir = f"ig_temp_{shortcode}"
            
            self.bot.edit_message_text("⬇️ Mengunduh media...", message.chat.id, status_msg.message_id)
            self.loader.download_post(post, target=target_dir)

            # Cari sub-folder (perbaikan dari bug sebelumnya)
            subfolders = [f.path for f in os.scandir(target_dir) if f.is_dir()]
            if not subfolders:
                # Fallback: jika tidak ada subfolder (kadang terjadi), cari di folder utama
                actual_download_path = target_dir
            else:
                actual_download_path = subfolders[0] 

            files = [os.path.join(actual_download_path, f) for f in os.listdir(actual_download_path) if f.endswith(('.jpg', '.mp4'))]
            if not files:
                raise Exception("Tidak menemukan file media.")

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
            if "403 Forbidden" in str(e) or "login_required" in str(e) or "Too many requests" in str(e):
                error_msg = "❌ Gagal: Instagram memblokir saya (Login/403). Sesi login mungkin perlu diverifikasi di HP/Browser."
            else:
                error_msg = f"❌ Instagram Error: {e}"
                
            if 'status_msg' in locals():
                self.bot.edit_message_text(error_msg, message.chat.id, status_msg.message_id)
            else:
                self.bot.send_message(message.chat.id, error_msg)
            return False

        finally:
            if target_dir and os.path.exists(target_dir):
                try:
                    shutil.rmtree(target_dir)
                except Exception as e:
                    print(f"Gagal membersihkan folder {target_dir}: {e}")