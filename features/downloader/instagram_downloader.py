import instaloader
import os
import re

class InstagramDownloader:
    def __init__(self, bot):
        self.bot = bot

    def download(self, message, url: str):
        filename = None  # biar gak error di finally
        try:
            self.bot.send_message(message.chat.id, "⏳ Mengambil media dari Instagram...")

            # ✅ regex lebih fleksibel: dukung /p/, /reel/, /tv/
            shortcode_match = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)/?", url)
            if not shortcode_match:
                raise Exception("URL Instagram tidak valid.")

            shortcode = shortcode_match.group(1)
            loader = instaloader.Instaloader(download_video_thumbnails=False, save_metadata=False, compress_json=False)
            post = instaloader.Post.from_shortcode(loader.context, shortcode)

            filename = f"ig_{shortcode}"
            loader.download_post(post, target=filename)

            # ✅ cari file yang benar (gambar atau video)
            files = [os.path.join(filename, f) for f in os.listdir(filename) if f.endswith(('.jpg', '.mp4'))]
            if not files:
                raise Exception("Tidak menemukan file media.")

            for fpath in files:
                with open(fpath, "rb") as media:
                    if fpath.endswith(".mp4"):
                        self.bot.send_video(message.chat.id, media, caption="🎬 Video Instagram", timeout=200)
                    else:
                        self.bot.send_photo(message.chat.id, media, caption="🖼 Foto Instagram", timeout=200)

            self.bot.send_message(message.chat.id, "✅ Selesai mengirim media dari Instagram!")
            return True

        except Exception as e:
            print(f"Instagram download error: {e}")
            self.bot.send_message(message.chat.id, f"❌ Instagram Error: {e}")
            return False

        finally:
            # ✅ bersihkan file sementara
            if filename and os.path.exists(filename):
                for f in os.listdir(filename):
                    try:
                        os.remove(os.path.join(filename, f))
                    except:
                        pass
                try:
                    os.rmdir(filename)
                except:
                    pass
