from features.downloader.youtube_downloader import YouTubeDownloader
from features.downloader.tiktok_downloader import TikTokDownloader
from features.downloader.instagram_downloader import InstagramDownloader
from features.ai.gemini_assistant import GeminiAssistant
from telebot import types
import re

pending_links = {}

def extract_url(text: str):
    match = re.search(r"(https?://[^\s]+)", text)
    return match.group(1) if match else None

def detect_platform(url: str):
    url = url.lower()
    if "youtube" in url or "youtu.be" in url:
        return "youtube"
    if "tiktok" in url or "vm.tiktok" in url or "vt.tiktok" in url:
        return "tiktok"
    if "instagram" in url or "instagr" in url:
        return "instagram"
    return None

def register_handlers(bot):
    yt = YouTubeDownloader(bot)
    tt = TikTokDownloader(bot)
    ig = InstagramDownloader(bot)
    ai = GeminiAssistant(bot)

    # =============== MENU TOMBOL BAWAH ===============
    @bot.message_handler(commands=['start'])
    def start(message):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(
            types.KeyboardButton("📥 Cara Downloader"),
            types.KeyboardButton("📉 Cara File Compressor"),
            types.KeyboardButton("ℹ️ INFO")
        )
        bot.send_message(
            message.chat.id,
            "Halo! Pilih menu di bawah ya 😊",
            reply_markup=kb
        )

    # =============== HANDLER PESAN ===============
    @bot.message_handler(func=lambda msg: True)
    def handler(message):
        text = message.text.strip()

        # ------ TOMBOL MENU ------
        if text == "📥 Cara Downloader":
            bot.send_message(
                message.chat.id,
                "🎬 *Cara Download Video:*\n"
                "1. Buka Instagram / TikTok / YouTube\n"
                "2. Copy link video\n"
                "3. Kirim link tersebut ke bot ini\n"
                "4. Pilih format download yang muncul ✅",
                parse_mode="Markdown"
            )
            return

        if text == "📉 Cara File Compressor":
            bot.send_message(
                message.chat.id,
                "📉 *Cara Kompres File:*\n"
                "• Kirim gambar (.jpg / .png) atau file PDF\n"
                "• Bot akan mengecilkan ukuran file otomatis 😉",
                parse_mode="Markdown"
            )
            return

        if text == "ℹ️ INFO":
            bot.send_message(
                message.chat.id,
                "ℹ️ *INFO FITUR BOT:*\n\n"
                "1. *DOWNLOADER* → Kirim link IG/TikTok/YT\n"
                "2. *FILE COMPRESSOR* → Kirim gambar atau PDF\n"
                "3. *INFO CUACA* → Ketik: `cuaca nama_kota`\n\n"
                "Contoh: `cuaca jakarta`",
                parse_mode="Markdown"
            )
            return

        # ------ DETEKSI LINK ------
        url = extract_url(text)
        if not url:
            return ai.reply(message)

        platform = detect_platform(url)

        if platform == "youtube":
            yt.send_format_buttons(message, url)
            return

        if platform == "tiktok":
            pending_links[message.chat.id] = url
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("🎥 Video (MP4)", callback_data="tt_video"),
                types.InlineKeyboardButton("🎵 Audio (MP3)", callback_data="tt_mp3"),
                types.InlineKeyboardButton("🖼 Gambar", callback_data="tt_image")
            )
            bot.send_message(message.chat.id, "Pilih format unduhan:", reply_markup=kb)
            return

        if platform == "instagram":
            return ig.download(message, url)

        return ai.reply(message)

    # =============== CALLBACK TIKTOK ===============
    @bot.callback_query_handler(func=lambda call: call.data.startswith("tt_"))
    def callback_tiktok(call):
        url = pending_links.get(call.message.chat.id)
        if not url:
            bot.answer_callback_query(call.id, "❌ Link tidak ditemukan.")
            return

        bot.answer_callback_query(call.id, "⏳ Diproses...")

        if call.data == "tt_video":
            tt.download_video(call.message, url)
        elif call.data == "tt_mp3":
            tt.download_audio(call.message, url)
        elif call.data == "tt_image":
            tt.download_images(call.message, url)
