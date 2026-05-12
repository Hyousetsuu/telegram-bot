import re
import os
import time
import platform
import psutil
from datetime import datetime
from telebot import types
from features.downloader.youtube_downloader import YouTubeDownloader
from features.downloader.tiktok_downloader import TikTokDownloader
from features.downloader.instagram_downloader import InstagramDownloader
from features.ai.gemini_assistant import GeminiAssistant
from features.tools.compressor import Compressor      
from features.tools.file_converter import FileConverter  

# Penyimpanan sementara untuk link yang sedang diproses
pending_links = {}

# Mencatat waktu bot pertama kali dijalankan untuk perhitungan Uptime
BOT_START_TIME = time.time()

# ------------------------------------------------------------
# 🔍 Helper Functions (Fungsi Bantuan)
# ------------------------------------------------------------

def extract_url(text: str):
    """Mencari link (URL) pertama di dalam teks."""
    match = re.search(r"(https?://[^\s]+)", text)
    return match.group(1) if match else None

def detect_platform(url: str):
    """Mendeteksi platform sosmed berdasarkan format URL."""
    url = url.lower()
    if any(x in url for x in ["youtube.com", "youtu.be"]): return "youtube"
    elif any(x in url for x in ["tiktok.com", "vm.tiktok.com", "vt.tiktok.com"]): return "tiktok"
    elif any(x in url for x in ["instagram.com", "instagr.am"]): return "instagram"
    return None

def format_uptime(seconds):
    """Mengubah detik menjadi format Hari, Jam, Menit, Detik."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if d > 0:
        return f"{d}h {h}j {m}m"
    return f"{h}j {m}m {s}d"

def get_progress_bar(percentage, length=10):
    """Membuat progress bar visual [████░░░░░░]."""
    filled = int(length * (percentage / 100))
    return '█' * filled + '░' * (length - filled)

# ------------------------------------------------------------
# 🚀 Register All Handlers (Fungsi Utama Pendaftaran)
# ------------------------------------------------------------
def register_handlers(bot):
    
    # Inisialisasi fitur
    yt = YouTubeDownloader(bot)
    tt = TikTokDownloader(bot)
    ig = InstagramDownloader(bot)
    ai = GeminiAssistant(bot)
    compressor = Compressor(bot) 
    converter = FileConverter(bot) 

    # ========================================================
    # 🏓 HANDLER 1: Command /ping (Wajib di Atas Handler Teks)
    # ========================================================
    @bot.message_handler(commands=['ping'])
    def handle_ping(message):
        """Menampilkan status server, penggunaan resource, dan uptime."""
        try:
            start_time = time.time()
            msg = bot.reply_to(message, "🔄 Pinging...")
            end_time = time.time()
            
            # Perhitungan Latency
            latency = int((end_time - start_time) * 1000)
            
            # Informasi Waktu
            now = datetime.now()
            days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            months = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            waktu_str = f"{days[now.weekday()]}, {now.day} {months[now.month]} {now.year} pukul {now.strftime('%H.%M.%S')}"
            
            # Uptime & Resource
            bot_uptime = format_uptime(time.time() - BOT_START_TIME)
            server_uptime = format_uptime(time.time() - psutil.boot_time())
            
            ram = psutil.virtual_memory()
            ram_used_mb = ram.used / (1024 * 1024)
            ram_total_gb = ram.total / (1024 * 1024 * 1024)
            
            process = psutil.Process(os.getpid())
            bot_ram_mb = process.memory_info().rss / (1024 * 1024)
            
            cpu_usage = psutil.cpu_percent(interval=0.1)
            cpu_cores = psutil.cpu_count(logical=False) or psutil.cpu_count()

            # --- TAMBAHAN BARU: STORAGE ---
            disk = psutil.disk_usage('/')
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_total_gb = disk.total / (1024 * 1024 * 1024)
            disk_percent = disk.percent

            # --- TAMBAHAN BARU: STATISTIK BOT ---
            total_antrean = len(pending_links)
            
            try:
                load1, load5, load15 = os.getloadavg()
                load_str = f"{load1:.2f} | {load5:.2f} | {load15:.2f}"
            except:
                load_str = "N/A"

            ping_text = f"""🏓 Pong!
━━━━━━━━━━━━━━━━━━
📡 Latency: {latency}ms
🕐 Waktu: {waktu_str}

🤖 BOT INFO
├ Uptime Bot: {bot_uptime}
├ Antrean Link: {total_antrean} proses berjalan
├ Python: v{platform.python_version()}
└ Platform: {platform.system().lower()} ({platform.machine()})

🖥️ SERVER INFO
├ Hostname: {platform.node()}
├ Uptime Server: {server_uptime}
└ CPU: {cpu_cores} Core(s)

📊 RESOURCE USAGE
├ CPU Usage: {cpu_usage}% [{get_progress_bar(cpu_usage)}]
├ RAM: {ram_used_mb:.1f} MB / {ram_total_gb:.2f} GB ({ram.percent}%)
├ RAM Bot: {bot_ram_mb:.1f} MB
└ Disk: {disk_used_gb:.1f} GB / {disk_total_gb:.1f} GB ({disk_percent}%)
   [{get_progress_bar(disk_percent)}]

✅ Status: Online"""

            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=ping_text)
        except Exception as e:
            print(f"Ping Error: {e}")
            bot.reply_to(message, "❌ Gagal mengambil data ping.")

    # ========================================================
    # 🖼 HANDLER 2: Menangkap FILE (Foto & Dokumen)
    # ========================================================
    @bot.message_handler(content_types=['photo', 'document'])
    def handle_files(message):
        try:
            markup = types.InlineKeyboardMarkup()
            
            if message.photo:
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

            if message.document:
                mime = message.document.mime_type
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
                elif mime == "application/pdf":
                    markup.add(
                        types.InlineKeyboardButton("🗜 Kompres PDF", callback_data="action_compress_pdf"),
                        types.InlineKeyboardButton("🔄 Konversi ke Gambar", callback_data="action_convert_pdf_img")
                    )
                    bot.reply_to(message, "Pilih aksi untuk file PDF ini:", reply_markup=markup)

        except Exception as e:
            print(f"File Handler Error: {e}")

    # ========================================================
    # 🎯 HANDLER 3: Menangkap PESAN TEKS (Link & AI Fallback)
    # ========================================================
    @bot.message_handler(content_types=['text'])
    def handler_text(message):
        try:
            text = message.text.strip()
            url = extract_url(text)

            if not url:
                return ai.reply(message)

            platform_type = detect_platform(url)
            if platform_type == "youtube":
                pending_links[message.chat.id] = url
                yt.send_format_buttons(message)
            elif platform_type == "tiktok":
                pending_links[message.chat.id] = url
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("🎥 Video (MP4)", callback_data="tt_video"),
                    types.InlineKeyboardButton("🎵 Audio (MP3)", callback_data="tt_mp3"),
                    types.InlineKeyboardButton("🖼 Gambar", callback_data="tt_image")
                )
                bot.send_message(message.chat.id, "🎬 Pilih format unduhan TikTok:", reply_markup=markup)
            elif platform_type == "instagram":
                ig.download(message, url)
            else:
                ai.reply(message)
        except Exception as e:
            print(f"Text Handler Error: {e}")
            bot.reply_to(message, "❌ Terjadi error saat memproses pesan teks.")

    # ========================================================
    # 🛠 CALLBACK HANDLERS (Logika Tombol)
    # ========================================================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("action_"))
    def callback_actions(call):
        try:
            action = call.data
            if action == "action_compress_img_70": compressor.process_image(call, 70) 
            elif action == "action_compress_img_50": compressor.process_image(call, 50)
            elif action == "action_compress_img_30": compressor.process_image(call, 30)
            elif action == "action_compress_pdf": compressor.process_pdf(call)
            elif action == "action_convert_img_pdf": converter.process_img_to_pdf(call)
            elif action == "action_convert_pdf_img": converter.process_pdf_to_img(call)
            elif action == "action_ignore": bot.answer_callback_query(call.id, text="Pilih aksi...")
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