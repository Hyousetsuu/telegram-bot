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

    # ✅ Pesan fallback bila gagal download
    def send_fail_message(message, platform):
        fail_messages = {
            "youtube": "Maaf, saya tidak bisa mendownload video YouTube ini saat ini. "
                       "Coba gunakan website seperti y2mate.is atau keepvid.app ya!",
            "tiktok": "Maaf, saya tidak bisa mendownload video TikTok ini. "
                      "Kamu bisa coba di snaptik.app atau musicaldown.com!",
            "instagram": "Maaf, saya tidak bisa mendownload video Instagram ini. "
                         "Gunakan snapinsta.app atau instavideo.net ya!"
        }
        bot.reply_to(message, fail_messages.get(platform, "Gagal memproses link ini."))

    @bot.message_handler(func=lambda msg: True)
    def handler(message):
        text = message.text.strip()

        url = extract_url(text)
        if not url:
            # Jika user menyebut salah satu platform tanpa URL
            if any(p in text.lower() for p in ["instagram", "ig"]):
                return bot.send_message(message.chat.id, "📌 Kirim link Instagram videonya ya!")
            if any(p in text.lower() for p in ["tiktok", "tt"]):
                return bot.send_message(message.chat.id, "📌 Kirim link TikTok videonya ya!")
            if any(p in text.lower() for p in ["youtube", "yt"]):
                return bot.send_message(message.chat.id, "📌 Kirim link YouTube videonya ya!")

            # Kalau bukan permintaan download
            return ai.reply(message)

        if not url:
            return ai.reply(message)

        platform = detect_platform(url)

        if platform == "youtube":
            if not yt.download(message, url):  # jika downloader return False
                return send_fail_message(message, platform)

        elif platform == "tiktok":
            if not tt.download(message, url):
                return send_fail_message(message, platform)

        elif platform == "instagram":
            if not ig.download(message, url):
                return send_fail_message(message, platform)

        else:
            return ai.reply(message)
