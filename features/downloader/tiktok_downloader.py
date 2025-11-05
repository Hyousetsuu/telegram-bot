import os
import time
import requests

class TikTokDownloader:

    def __init__(self, bot):
        self.bot = bot

    def download(self, message, url):
        return self.download_tiktok_media(message, url)

    def download_tiktok_media(self, message, url):
        try:
            self.bot.send_message(message.chat.id, "🎬 Mengambil postingan TikTok...")

            post_data = self._get_tiktok_data(url)

            if post_data.get("type") == "image" or post_data.get("images"):
                return self._handle_image_mode(message, post_data)

            return self._handle_video_mode(message, post_data)

        except Exception as e:
            print("download_tiktok_media error:", e)
            self.bot.send_message(message.chat.id, f"❌ Error: {e}")
            return False  # ❌ Gagal
        finally:
            self._cleanup_tempfiles()

    # 🔥 TikTok API fetch
    def _get_tiktok_data(self, url):
        resp = requests.get("https://www.tikwm.com/api/", params={"url": url}, timeout=35)
        return resp.json().get("data", {})

    # ✅ Resume Download Utility
    def _download_with_resume(self, url, final_path, temp_path,
                              min_valid_size=20000, stream_timeout=200, max_attempts=6):

        if os.path.exists(final_path) and os.path.getsize(final_path) >= min_valid_size:
            return True

        for attempt in range(1, max_attempts + 1):
            try:
                downloaded = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                headers = {"Range": f"bytes={downloaded}-"} if downloaded > 0 else {}

                with requests.get(url, headers=headers, stream=True, timeout=stream_timeout) as r:
                    if downloaded > 0 and r.status_code != 206:
                        os.remove(temp_path)
                        downloaded = 0
                        r = requests.get(url, stream=True, timeout=stream_timeout)

                    r.raise_for_status()
                    mode = "ab" if downloaded else "wb"
                    with open(temp_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=40960):
                            if chunk:
                                f.write(chunk)

                if os.path.exists(temp_path) and os.path.getsize(temp_path) >= min_valid_size:
                    if os.path.exists(final_path):
                        os.remove(final_path)
                    os.replace(temp_path, final_path)
                    return True

            except Exception as e:
                print(f"download_with_resume attempt {attempt}/{max_attempts} failed: {e}")
                time.sleep(3)

        return False

    # ✅ Send multiple images safely with retry
    def _send_media_group_safe(self, chat_id, paths):
        batch_size = 5
        delay_after_batch = 10

        for i in range(0, len(paths), batch_size):
            batch = paths[i:i + batch_size]

            for p in batch:
                if not os.path.exists(p) or os.path.getsize(p) < 20000:
                    continue

                for attempt in range(6):
                    try:
                        with open(p, "rb") as f:
                            self.bot.send_photo(chat_id, f, timeout=180)
                        os.remove(p)
                        break
                    except Exception as e:
                        print(f"send_photo failed attempt {attempt+1}: {e}")
                        time.sleep(4)

            if i + batch_size < len(paths):
                self.bot.send_message(chat_id, "⏳ Tunggu 10 detik sebelum lanjut...")
                time.sleep(delay_after_batch)

    # ✅ Image Mode Handler
    def _handle_image_mode(self, message, post_data):
        images = post_data.get("images") or []
        img_urls = [img["url"] if isinstance(img, dict) else img for img in images]

        self.bot.send_message(message.chat.id, f"🖼 Menemukan {len(img_urls)} gambar...")

        downloaded = []

        for i, u in enumerate(img_urls, start=1):
            fn = f"tiktok_pic_{i}.jpg"
            tp = fn + ".part"

            msg = self.bot.send_message(message.chat.id, f"⬇️ Download {i}/{len(img_urls)}...")
            ok = self._download_with_resume(u, fn, tp)

            try:
                self.bot.delete_message(message.chat.id, msg.message_id)
            except:
                pass

            if ok:
                downloaded.append(fn)

        if not downloaded:
            self.bot.send_message(message.chat.id, "❌ Tidak ada gambar valid untuk dikirim")
            return False  # ❌ Gagal

        self.bot.send_message(message.chat.id, f"📤 Upload {len(downloaded)} gambar ke Telegram...")
        self._send_media_group_safe(message.chat.id, downloaded)
        self.bot.send_message(message.chat.id, "✅ Semua gambar berhasil dikirim!")
        return True  # ✅ Berhasil

    # ✅ Video Mode Handler
    def _handle_video_mode(self, message, post_data):
        video_url = post_data.get("play")
        if not video_url:
            raise Exception("URL video tidak ditemukan.")

        fn = "tiktok_video.mp4"
        tp = fn + ".part"

        self.bot.send_message(message.chat.id, "🎥 Mendownload video...")

        if not self._download_with_resume(video_url, fn, tp, min_valid_size=150000):
            raise Exception("Gagal download video!")

        size = os.path.getsize(fn)
        send_func = self.bot.send_document if size > 45*1024*1024 else self.bot.send_video
        caption = "📦 Video TikTok" if size > 45*1024*1024 else "🎥 Video TikTok"

        for attempt in range(6):
            try:
                with open(fn, "rb") as f:
                    send_func(message.chat.id, f, caption=caption, timeout=200)
                self.bot.send_message(message.chat.id, "✅ Video berhasil dikirim!")
                return True  # ✅ Berhasil
            except Exception as e:
                print(f"send_video attempt {attempt+1} failed: {e}")
                time.sleep(6)

        self.bot.send_message(message.chat.id, "❌ Upload video gagal setelah 6 percobaan!")
        return False  # ❌ Gagal

    # ✅ Cleanup Temp
    def _cleanup_tempfiles(self):
        for f in os.listdir():
            if f.endswith(".part") or f.startswith("tiktok_pic_") or f == "tiktok_video.mp4":
                try:
                    os.remove(f)
                except:
                    pass
