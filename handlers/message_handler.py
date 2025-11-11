import re
from telebot import types
from features.downloader.youtube_downloader import YouTubeDownloader
from features.downloader.tiktok_downloader import TikTokDownloader
from features.downloader.instagram_downloader import InstagramDownloader
from features.ai.gemini_assistant import GeminiAssistant
from features.tools.compressor import Compressor      
from features.tools.file_converter import FileConverter  

pending_links = {}

# ------------------------------------------------------------
# 🔍 Helper Functions (Fungsi Bantuan)
# ------------------------------------------------------------

def extract_url(text: str):
    """Mencari link (URL) pertama di dalam teks."""
    # --- PERBAIKAN BUG DI SINI ---
    # Menghapus 'https' ekstra dari regex
    match = re.search(r"(https?://[^\s]+)", text)
    # -----------------------------
    return match.group(1) if match else None

def detect_platform(url: str):
    """Mendeteksi platform sosmed berdasarkan format URL."""
    url = url.lower()
    if any(x in url for x in ["youtube.com", "youtu.be"]): return "youtube"
    elif any(x in url for x in ["tiktok.com", "vm.tiktok.com", "vt.tiktok.com"]): return "tiktok"
    elif any(x in url for x in ["instagram.com", "instagr.am"]): return "instagram"
    return None

# ------------------------------------------------------------
# 🚀 Register All Handlers (Fungsi Utama Pendaftaran)
# ------------------------------------------------------------
def register_handlers(bot):
    
    yt = YouTubeDownloader(bot)
    tt = TikTokDownloader(bot)
    ig = InstagramDownloader(bot)
    ai = GeminiAssistant(bot)
    compressor = Compressor(bot) 
    converter = FileConverter(bot) 

    # ========================================================
    # 🖼 HANDLER 1: Menangkap FILE (Foto & Dokumen)
    # ========================================================
    @bot.message_handler(content_types=['photo', 'document'])
    def handle_files(message):
        """
        Handler ini menangkap semua kiriman file dan menawarkan
        aksi (Kompres/Konversi) melalui tombol balasan.
        """
        try:
            markup = types.InlineKeyboardMarkup()
            
            # KASUS 1: USER MENGIRIM FOTO
            if message.photo:
                # Menambahkan kembali 3 tombol kompresi + 1 tombol konversi
                markup.add(types.InlineKeyboardButton("--- 🗜 Kompres Gambar ---", callback_data="action_ignore"))
                markup.add(
                    types.InlineKeyboardButton("📉 Ringan (70%)", callback_data="action_compress_img_70"),
                    types.InlineKeyboardButton("😐 Sedang (50%)", callback_data="action_compress_img_50"),
                    types.InlineKeyboardButton("🧱 Ekstrem (30%)", callback_data="action_compress_img_30")
                )
                markup.add(types.InlineKeyboardButton("--- 🔄 Konversi ---", callback_data="action_ignore"))
                markup.add(types.InlineKeyboardButton("Ubah ke PDF", callback_data="action_convert_img_pdf"))
                bot.reply_to(message, "Pilih aksi untuk Gambar ini:", reply_markup=markup)
                return

            # KASUS 2: USER MENGIRIM DOKUMEN
            if message.document:
                mime = message.document.mime_type
                
                # Jika dokumen adalah Gambar (misal PNG)
                if mime.startswith("image/"):
                    markup.add(types.InlineKeyboardButton("--- 🗜 Kompres Gambar ---", callback_data="action_ignore"))
                    markup.add(
                        types.InlineKeyboardButton("📉 Ringan (70%)", callback_data="action_compress_img_70"),
                        types.InlineKeyboardButton("😐 Sedang (50%)", callback_data="action_compress_img_50"),
                        types.InlineKeyboardButton("🧱 Ekstrem (30%)", callback_data="action_compress_img_30")
                    )
                    markup.add(types.InlineKeyboardButton("--- 🔄 Konversi ---", callback_data="action_ignore"))
                    markup.add(types.InlineKeyboardButton("Ubah ke PDF", callback_data="action_convert_img_pdf"))
                    bot.reply_to(message, "Pilih aksi untuk file Gambar ini:", reply_markup=markup)
                    return
                
                # Jika dokumen adalah PDF
                elif mime == "application/pdf":
                    markup.add(
                        types.InlineKeyboardButton("🗜 Kompres PDF", callback_data="action_compress_pdf"),
                        types.InlineKeyboardButton("🔄 Konversi ke Gambar", callback_data="action_convert_pdf_img")
                    )
                    bot.reply_to(message, "Pilih aksi untuk file PDF ini:", reply_markup=markup)
                    return
            
            pass

        except Exception as e:
            print(f"File Handler Error: {e}")

    # ========================================================
    # 🎯 HANDLER 2: Menangkap PESAN TEKS (Link & AI Fallback)
    # ========================================================
    @bot.message_handler(content_types=['text'])
    def handler_text(message):
        """
        Handler ini menangkap semua pesan teks (link atau obrolan AI).
        """
        try:
            text = message.text.strip()
            url = extract_url(text) # <-- Sekarang sudah diperbaiki

            if not url:
                return ai.reply(message) # Ke AI

            platform = detect_platform(url)
            if platform == "youtube":
                pending_links[message.chat.id] = url
                yt.send_format_buttons(message) # <-- Ini akan jalan lagi
            elif platform == "tiktok":
                pending_links[message.chat.id] = url
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("🎥 Video (MP4)", callback_data="tt_video"),
                    types.InlineKeyboardButton("🎵 Audio (MP3)", callback_data="tt_mp3"),
                    types.InlineKeyboardButton("🖼 Gambar", callback_data="tt_image")
                )
                bot.send_message(message.chat.id, "🎬 Pilih format unduhan TikTok:", reply_markup=markup)
            elif platform == "instagram":
                ig.download(message, url)
            else:
                ai.reply(message) # Link tidak dikenal
        except Exception as e:
            print(f"Text Handler Error: {e}")
            bot.reply_to(message, "❌ Terjadi error saat memproses pesan teks.")


    # ========================================================
    #  CALLBACK HANDLERS (Semua Tombol)
    # ========================================================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("action_"))
    def callback_actions(call):
        """Menangani tombol aksi untuk Kompres/Konversi."""
        try:
            action = call.data
            
            # Aksi Kompresor (dengan 3 pilihan)
            if action == "action_compress_img_70":
                compressor.process_image(call, 70) 
            elif action == "action_compress_img_50":
                compressor.process_image(call, 50)
            elif action == "action_compress_img_30":
                compressor.process_image(call, 30)
            elif action == "action_compress_pdf":
                compressor.process_pdf(call)
                
            # Aksi Konverter
            elif action == "action_convert_img_pdf":
                converter.process_img_to_pdf(call)
            elif action == "action_convert_pdf_img":
                converter.process_pdf_to_img(call)
                
            elif action == "action_ignore":
                bot.answer_callback_query(call.id, text="Pilih aksi...")
            else:
                bot.answer_callback_query(call.id, "Aksi tidak diketahui.")

        except Exception as e:
            print(f"Action Callback Error: {e}")
            bot.send_message(call.message.chat.id, f"❌ Gagal memproses aksi: {e}")

    
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
            print(f"YouTube Callback Error: {e}")
            bot.send_message(call.message.chat.id, "❌ Error saat memproses link YouTube.")

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
            print(f"TikTok Callback Error: {e}")
            bot.send_message(call.message.chat.id, "❌ Error saat memproses link TikTok.")