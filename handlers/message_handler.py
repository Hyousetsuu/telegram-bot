from features.downloader.youtube_downloader import YouTubeDownloader
from features.downloader.tiktok_downloader import TikTokDownloader
from features.downloader.instagram_downloader import InstagramDownloader
from features.downloader.file_converter import FileConverter
from features.downloader.tts_converter import TextToSpeechConverter
from features.downloader.qr_generator import QRCodeGenerator
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
    converter = FileConverter(bot)
    tts = TextToSpeechConverter(bot)
    qr = QRCodeGenerator(bot)
    ai = GeminiAssistant(bot)

    # ========================================================
    # 🎯 Handler utama pesan teks (Termasuk deteksi link dan command)
    # ========================================================
    @bot.message_handler(func=lambda msg: True, content_types=['text'])
    def handler(message):
        text = message.text.strip()
        url = extract_url(text)
        
        # --- Pemeriksaan Command Konversi File ---
        if text.startswith('/imgtopdf'):
            return converter.img_to_pdf(message)
        elif text.startswith('/pdftoimg'):
            return converter.pdf_to_img(message)
        
        # --- Pemeriksaan Command Teks ke Suara ---
        elif text.startswith('/tts'):
            return tts.text_to_audio(message)
            
        # --- Pemeriksaan Command QR Code ---
        elif text.startswith('/qr'):
            return qr.generate_qr(message)
        # ------------------------------------

        if not url:
            # Jika bukan link dan bukan command konversi, kirim ke AI
            return ai.reply(message)

        # Jika ada URL
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
            # Jika URL tidak dikenali (URL lain), kirim ke AI
            return ai.reply(message)

    # ========================================================
    # 📚 Handler untuk Perintah Konversi (Dipastikan terdeteksi)
    # ========================================================
    @bot.message_handler(commands=['imgtopdf'])
    def handle_img_to_pdf_command(message):
        return converter.img_to_pdf(message)

    @bot.message_handler(commands=['pdftoimg'])
    def handle_pdf_to_img_command(message):
        return converter.pdf_to_img(message)

    @bot.message_handler(commands=['tts'])
    def handle_tts_command(message):
        return tts.text_to_audio(message)

    @bot.message_handler(commands=['qr'])
    def handle_qr_command(message):
        return qr.generate_qr(message)

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
