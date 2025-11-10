import re
from telebot import types
from features.downloader.youtube_downloader import YouTubeDownloader
from features.downloader.tiktok_downloader import TikTokDownloader
from features.downloader.instagram_downloader import InstagramDownloader
from features.ai.gemini_assistant import GeminiAssistant
from features.tools.compressor import Compressor

# 🔹 Simpan link sementara (chat_id -> url)
pending_links = {}

# ------------------------------------------------------------
# 🔍 Helper Functions
# ------------------------------------------------------------
def extract_url(text: str):
    match = re.search(r"(https?://[^\s]+)", text)
    return match.group(1) if match else None

def detect_platform(url: str):
    url = url.lower()
    if any(x in url for x in ["youtube.com", "youtu.be"]): return "youtube"
    elif any(x in url for x in ["tiktok.com", "vm.tiktok.com", "vt.tiktok.com"]): return "tiktok"
    elif any(x in url for x in ["instagram.com", "instagr.am"]): return "instagram"
    return None

# ------------------------------------------------------------
# 🚀 Register All Handlers
# ------------------------------------------------------------
def register_handlers(bot):
    # Inisialisasi Fitur
    yt = YouTubeDownloader(bot)
    tt = TikTokDownloader(bot)
    ig = InstagramDownloader(bot)
    ai = GeminiAssistant(bot)
    compressor = Compressor(bot) # <-- Inisialisasi Compressor

    # ========================================================
    # 🖼 Handler Khusus Gambar (Foto & Dokumen Gambar)
    # ========================================================
    @bot.message_handler(content_types=['photo', 'document'])
    def handle_files(message):
        is_valid = False
        # Cek apakah Foto
        if message.photo: is_valid = True
        # Cek apakah Dokumen (Gambar atau PDF)
        elif message.document:
            mime = message.document.mime_type
            if mime.startswith("image/") or mime == "application/pdf":
                is_valid = True
        
        if is_valid:
            compressor.offer_compression(message)
            return # Stop agar tidak lanjut ke handler teks)

    # ========================================================
    # 🎯 Handler Utama Pesan Teks
    # ========================================================
    @bot.message_handler(func=lambda msg: True)
    def handler_text(message):
        text = message.text.strip()
        url = extract_url(text)

        # Jika tidak ada URL, serahkan ke AI
        if not url:
            return ai.reply(message)

        platform = detect_platform(url)

        # --- YOUTUBE ---
        if platform == "youtube":
            pending_links[message.chat.id] = url
            yt.send_format_buttons(message) # Tidak perlu kirim URL lagi

        # --- TIKTOK ---
        elif platform == "tiktok":
            pending_links[message.chat.id] = url
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("🎥 Video (MP4)", callback_data="tt_video"),
                types.InlineKeyboardButton("🎵 Audio (MP3)", callback_data="tt_mp3"),
                types.InlineKeyboardButton("🖼 Gambar", callback_data="tt_image")
            )
            bot.send_message(message.chat.id, "🎬 Pilih format unduhan TikTok:", reply_markup=markup)

        # --- INSTAGRAM ---
        elif platform == "instagram":
            ig.download(message, url)

        # --- LINK LAIN (Fallback ke AI) ---
        else:
            ai.reply(message)

    # ========================================================
    # 🗜 Callback Compressor
    # ========================================================
    @bot.callback_query_handler(func=lambda call: "img_" in call.data or "pdf_" in call.data)
    def callback_compressor(call):
        try:
            if "img_" in call.data:
                # Handle Gambar
                quality = int(call.data.split("_")[1])
                bot.answer_callback_query(call.id, "Mulai kompres gambar...")
                compressor.process_image(call, quality)
            elif "pdf_" in call.data:
                # Handle PDF
                bot.answer_callback_query(call.id, "Mulai kompres PDF...")
                compressor.process_pdf(call)
        except Exception as e:
             print(f"Callback Error: {e}")

    # ========================================================
    # 🎥 Callback YouTube
    # ========================================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("yt_"))
    def callback_youtube(call):
        try:
            url = pending_links.get(call.message.chat.id)
            if not url:
                bot.answer_callback_query(call.id, "❌ Link kadaluarsa. Kirim ulang.")
                return

            format_type = "mp4" if call.data == "yt_mp4" else "mp3"
            bot.answer_callback_query(call.id, f"🔽 Mengunduh {format_type.upper()}...")
            yt.download(call.message, url, format_type)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Error YouTube: {e}")

    # ========================================================
    # 🎵 Callback TikTok
    # ========================================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("tt_"))
    def callback_tiktok(call):
        try:
            url = pending_links.get(call.message.chat.id)
            if not url:
                bot.answer_callback_query(call.id, "❌ Link kadaluarsa.")
                return

            bot.answer_callback_query(call.id, "📥 Memproses TikTok...")
            if call.data == "tt_video": tt.download_video(call.message, url)
            elif call.data == "tt_mp3": tt.download_audio(call.message, url)
            elif call.data == "tt_image": tt.download_images(call.message, url)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Error TikTok: {e}")