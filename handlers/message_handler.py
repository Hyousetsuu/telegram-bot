from features.downloader.youtube_downloader import YouTubeDownloader
from features.downloader.tiktok_downloader import TikTokDownloader
from features.downloader.instagram_downloader import InstagramDownloader
from features.ai.gemini_assistant import GeminiAssistant
import re


def extract_url(text: str):
    url_pattern = r"(https?://[^\s]+)"
    match = re.search(url_pattern, text)
    return match.group(1) if match else None


def detect_platform(url: str):
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "tiktok.com" in url:
        return "tiktok"
    elif "instagram.com" in url or "instagr.am" in url:
        return "instagram"
    return None


def register_handlers(bot):
    yt = YouTubeDownloader(bot)
    tt = TikTokDownloader(bot)
    ig = InstagramDownloader(bot)
    ai = GeminiAssistant(bot)

    # ✅ Fallback pesan ketika gagal
    def send_fail_message(message, platform):
        fail_messages = {
            "youtube": "⚠️ Tidak bisa mendownload video YouTube ini.",
            "tiktok": "⚠️ Tidak bisa mendownload video TikTok ini.",
            "instagram": "⚠️ Tidak bisa mendownload video Instagram ini."
        }
        return bot.reply_to(message, fail_messages.get(platform, "⚠️ Gagal memproses link ini."))

    # ✅ Handler utama
    @bot.message_handler(func=lambda msg: True)
    def handler(message):
        text = message.text.strip().lower()

        # ==================================================
        # ✅ COMMAND MP3 → Download AUDIO TikTok
        # ==================================================
        if text.startswith("/mp3") or text.startswith("mp3 "):
            url = extract_url(message.text)
            if not url:
                return bot.send_message(message.chat.id, "🎧 Format yang benar:\n/mp3 <link TikTok>")
            return tt.download(message, url, mode="audio")

        # ==================================================
        # ✅ Jika tidak ada link → balas sebagai Chat AI
        # ==================================================
        url = extract_url(message.text)
        if not url:
            return ai.reply(message)

        # ==================================================
        # ✅ Tentukan platform berdasarkan link
        # ==================================================
        platform = detect_platform(url)

        # ✅ YouTube → Video
        if platform == "youtube":
            if not yt.download(message, url):
                return send_fail_message(message, platform)

        # ✅ TikTok → Default = Video
        elif platform == "tiktok":
            if not tt.download(message, url, mode="video"):
                return send_fail_message(message, platform)

        # ✅ Instagram → Video/Reel
        elif platform == "instagram":
            if not ig.download(message, url):
                return send_fail_message(message, platform)

        # ✅ Jika bukan link platform dikenal → AI jawab
        else:
            return ai.reply(message)
