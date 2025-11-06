from features.downloader.youtube_downloader import YouTubeDownloader
from features.downloader.tiktok_downloader import TikTokDownloader
from features.downloader.instagram_downloader import InstagramDownloader
from features.ai.gemini_assistant import GeminiAssistant
from telebot import types
import re

# 🔹 Simpan link TikTok sementara
pending_links = {}

# ------------------------------------------------------------
# 🔍 Deteksi URL dan Platform
# ------------------------------------------------------------
def extract_url(text: str):
    match = re.search(r"(https?://[^\s]+)", text)
    return match.group(1) if match else None

def detect_platform(url: str):
    url = url.lower()
    if any(x in url for x in ["youtube.com", "youtu.be"]):
        return "youtube"
    elif any(x in url for x in ["tiktok.com", "vm.tiktok.com", "vt.tiktok.com"]):
        return "tiktok"
    elif any(x in url for x in ["instagram.com", "instagr.am"]):
        return "instagram"
    return None

# ------------------------------------------------------------
# 🚀 Register semua handler
# ------------------------------------------------------------
def register_handlers(bot):
    yt = YouTubeDownloader(bot)
    tt = TikTokDownloader(bot)
    ig = InstagramDownloader(bot)
    ai = GeminiAssistant(bot)

    # ========================================================
    # 🎯 Handler utama pesan teks
    # ========================================================
    @bot.message_handler(func=lambda msg: True)
    def handler(message):
        text = message.text.strip()
        url = extract_url(text)
        if not url:
            return ai.reply(message)

        platform = detect_platform(url)

        # YouTube
        if platform == "youtube":
            yt.send_format_buttons(message, url)
            return

        # TikTok
        elif platform == "tiktok":
            pending_links[message.chat.id] = url
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("🎥 Video (MP4)", callback_data="tt_video"),
                types.InlineKeyboardButton("🎵 Audio (MP3)", callback_data="tt_mp3"),
                types.InlineKeyboardButton("🖼 Gambar", callback_data="tt_image")
            )
            bot.send_message(
                message.chat.id,
                "🎬 Pilih format unduhan TikTok:",
                reply_markup=markup
            )
            return

        # Instagram
        elif platform == "instagram":
            return ig.download(message, url)

        else:
            return ai.reply(message)

    # ========================================================
    # 🎥 Callback YouTube
    # ========================================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("yt_"))
    def callback_youtube(call):
        try:
            format_type, url = call.data.split("|", 1)
            format_type = "mp4" if format_type == "yt_mp4" else "mp3"
            bot.answer_callback_query(call.id, f"🔽 Mengunduh {format_type.upper()}...")
            yt.download(call.message, url, format_type)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Terjadi error: {e}")

    # ========================================================
    # 🎵 Callback TikTok
    # ========================================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("tt_"))
    def callback_tiktok(call):
        try:
            url = pending_links.get(call.message.chat.id)
            if not url:
                bot.answer_callback_query(call.id, "❌ URL TikTok tidak ditemukan.")
                return

            bot.answer_callback_query(call.id, "📥 Mengunduh dari TikTok...")

            if call.data == "tt_video":
                tt.download_video(call.message, url)
            elif call.data == "tt_mp3":
                tt.download_audio(call.message, url)
            elif call.data == "tt_image":
                tt.download_images(call.message, url)

        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Terjadi error: {e}")
