import os
import time
import requests

class TikTokDownloader:

    def __init__(self, bot):
        self.bot = bot

    # ===== ENTRY POINT =====
    def download(self, message, url, mode="auto"):
        return self.download_tiktok_media(message, url, mode)

    def download_tiktok_media(self, message, url, mode="auto"):
        try:
            self.bot.send_message(message.chat.id, "🎬 Mengambil postingan TikTok... 🤖")

            post_data = self._get_tiktok_data(url)

            if not isinstance(post_data, dict) or not post_data:
                self.bot.send_message(message.chat.id, "❌ Gagal membaca data TikTok. Coba ulangi.")
                return False

            # === MODE AUDIO ===
            if mode == "audio" or mode == "mp3":
                return self._handle_audio_mode(message, post_data)

            # === MODE GAMBAR (SLIDE) ===
            if post_data.get("images"):
                return self._handle_image_mode(message, post_data)

            # === MODE VIDEO ===
            return self._handle_video_mode(message, post_data)

        except Exception as e:
            print("download_tiktok_media error:", e)
            self.bot.send_message(message.chat.id, f"❌ Error: {e}")
            return False

        finally:
            self._cleanup_tempfiles()

    # ===== API FETCH =====
    def _get_tiktok_data(self, url):
        apis = [
            ("https://www.tikwm.com/api/", "data"),
            ("https://api.tikmate.app/api/lookup", "videoUrl"),
            ("https://www.tikcdn.io/api/v1/tiktok/video", "videoUrl")
        ]

        for api, keycheck in apis:
            try:
                resp = requests.get(api, params={"url": url}, timeout=15)

                # Pastikan respons JSON dan bukan string/HTML
                try:
                    data = resp.json()
                except:
                    continue  # jika bukan JSON → skip API ini

                # TikWM
                if isinstance(data, dict) and isinstance(data.get("data"), dict):
                    return data["data"]

                # Fallback API (Tikmate / Tikcdn)
                if isinstance(data, dict) and keycheck in str(data):
                    normalized = self._normalize_data(data)
                    if isinstance(normalized, dict):   # pastikan hasil dict
                        return normalized

            except Exception as e:
                print("Fallback error", api, e)
                continue

        return {}  # jika semuanya gagal


    # ===== NORMALIZE FALLBACK =====
    def _normalize_data(self, data):
    # Pastikan input dict
        if not isinstance(data, dict):
            return {}

        # Ambil URL video
        play = data.get("videoUrl") or data.get("play") or ""

        # Ambil URL audio
        music = data.get("musicUrl") or data.get("music") or ""

        # Pastikan music selalu dictionary
        if isinstance(music, str):
            music = {"play_url": music}
        elif isinstance(music, dict):
            music = {"play_url": music.get("play_url") or music.get("url") or ""}

        images = data.get("imageUrls") or data.get("images") or []

        # Normalisasi list gambar
        clean_images = []
        for img in images:
            if isinstance(img, dict):
                clean_images.append(img.get("url"))
            else:
                clean_images.append(img)

        return {
            "play": play,
            "images": clean_images,
            "music": music
        }



    # ===== DOWNLOAD RESUME SUPPORT =====
    def _download_with_resume(self, url, final_path, temp_path,
                              min_valid_size=20000, timeout=200, attempts=5):

        if os.path.exists(final_path) and os.path.getsize(final_path) >= min_valid_size:
            return True

        for _ in range(attempts):
            try:
                downloaded = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                headers = {"Range": f"bytes={downloaded}-"} if downloaded else {}

                with requests.get(url, headers=headers, stream=True, timeout=timeout) as r:
                    r.raise_for_status()
                    mode = "ab" if downloaded else "wb"

                    with open(temp_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=40960):
                            if chunk:
                                f.write(chunk)

                if os.path.exists(temp_path) and os.path.getsize(temp_path) >= min_valid_size:
                    os.replace(temp_path, final_path)
                    return True

            except:
                time.sleep(2)

        return False

    # ===== IMAGE MODE =====
    def _handle_image_mode(self, message, post_data):
        image_urls = [i["url"] if isinstance(i, dict) else i for i in post_data.get("images", [])]

        if not image_urls:
            raise Exception("Slide gambar tidak ditemukan.")

        self.bot.send_message(message.chat.id, f"🖼 Menemukan {len(image_urls)} gambar...")

        for index, url in enumerate(image_urls, start=1):
            fname = f"tiktok_img_{index}.jpg"
            part = fname + ".part"

            if self._download_with_resume(url, fname, part):
                with open(fname, "rb") as f:
                    self.bot.send_photo(message.chat.id, f)
                os.remove(fname)

        self.bot.send_message(message.chat.id, "✅ Semua gambar berhasil dikirim!")

    # ===== VIDEO MODE =====
    def _handle_video_mode(self, message, post_data):
        video_url = post_data.get("play")
        if not video_url:
            raise Exception("URL video tidak ditemukan.")

        fname = "tiktok_video.mp4"
        part = fname + ".part"

        self.bot.send_message(message.chat.id, "🎥 Mengunduh video...")

        if not self._download_with_resume(video_url, fname, part, min_valid_size=120000):
            raise Exception("Gagal download video!")

        with open(fname, "rb") as f:
            self.bot.send_video(message.chat.id, f, caption="🎥 Video TikTok")

    # ===== AUDIO MODE (FIXED) =====
        # ===== AUDIO MODE (BENAR) =====
    def _handle_audio_mode(self, message, post_data):
        music = post_data.get("music")

        # Normalisasi jika music masih string
        if isinstance(music, str):
            music = {"play_url": music}
        elif isinstance(music, dict):
            music = {"play_url": music.get("play_url") or music.get("url") or music.get("music")}

        audio_url = music.get("play_url") if music else None

        if not audio_url:
            raise Exception("URL audio tidak ditemukan.")

        fname = "tiktok_audio.mp3"
        part = fname + ".part"

        self.bot.send_message(message.chat.id, "🎧 Mengunduh audio MP3...")

        if not self._download_with_resume(audio_url, fname, part, min_valid_size=15000):
            raise Exception("Gagal download audio!")

        with open(fname, "rb") as f:
            self.bot.send_audio(message.chat.id, f, caption="🎶 Audio TikTok (MP3)")

        self.bot.send_message(message.chat.id, "✅ MP3 berhasil dikirim!")

    # ===== CLEANER =====
    def _cleanup_tempfiles(self):
        for f in os.listdir():
            if f.endswith(".part") or f.startswith("tiktok_"):
                try: os.remove(f)
                except: pass
