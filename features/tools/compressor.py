import os
import time
from PIL import Image
import pikepdf # Import library baru
from telebot import types

class Compressor:
    def __init__(self, bot):
        self.bot = bot
        self.temp_folder = "temp_compress"
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)
        
        # Batas download file dari API Telegram adalah 20MB
        self.MAX_DOWNLOAD_SIZE = 20 * 1024 * 1024 

    def offer_compression(self, message):
        """Menawarkan opsi DAN memvalidasi ukuran file."""
        markup = types.InlineKeyboardMarkup()
        
        file_size = 0
        is_image = False
        is_pdf = False

        if message.photo:
            file_size = message.photo[-1].file_size
            is_image = True
        elif message.document:
            file_size = message.document.file_size # Ambil ukuran file
            mime = message.document.mime_type
            if mime.startswith("image/"):
                is_image = True
            elif mime == "application/pdf":
                is_pdf = True

        # --- VALIDASI UKURAN FILE (Sangat Penting) ---
        if file_size > self.MAX_DOWNLOAD_SIZE:
            size_mb = file_size / (1024 * 1024)
            self.bot.reply_to(
                message, 
                f"❌ **File Terlalu Besar**\n"
                f"Ukuran file Anda ({size_mb:.1f} MB) melebihi batas 20 MB.",
                parse_mode="Markdown"
            )
            return # Hentikan proses
        # ------------------------------------

        text = ""
        if is_image:
            markup.add(
                types.InlineKeyboardButton("📉 Ringan (70%)", callback_data="img_70"),
                types.InlineKeyboardButton("😐 Sedang (50%)", callback_data="img_50"),
                types.InlineKeyboardButton("🗜 Ekstrem (30%)", callback_data="img_30")
            )
            text = "🖼 **Kompresor Gambar**\nPilih tingkat kompresi:"
            
        elif is_pdf:
            markup.add(types.InlineKeyboardButton("🗜 Kompres PDF Sekarang", callback_data="pdf_compress"))
            text = "📄 **Kompresor PDF**\nTekan tombol di bawah untuk memperkecil ukuran PDF."
            
        else:
            return # Tipe tidak didukung

        self.bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")

    def process_image(self, call, quality):
        """Proses Kompresi Gambar (JPG/PNG)."""
        msg = call.message.reply_to_message
        status_msg = self.bot.send_message(call.message.chat.id, f"⏳ Mengompres gambar...")
        input_path, output_path = None, None

        try:
            if msg.photo:
                file_id, ext = msg.photo[-1].file_id, ".jpg"
            else:
                file_id, ext = msg.document.file_id, ".png" if "png" in msg.document.mime_type else ".jpg"

            file_info = self.bot.get_file(file_id)
            downloaded_data = self.bot.download_file(file_info.file_path)
            
            timestamp = int(time.time())
            input_path = os.path.join(self.temp_folder, f"img_in_{timestamp}{ext}")
            output_path = os.path.join(self.temp_folder, f"img_out_{timestamp}{ext}")

            with open(input_path, "wb") as f: f.write(downloaded_data)

            original_size = os.path.getsize(input_path) / 1024
            img = Image.open(input_path)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.save(output_path, "JPEG", optimize=True, quality=quality)
            compressed_size = os.path.getsize(output_path) / 1024

            self._send_result(call.message.chat.id, output_path, original_size, compressed_size, "Gambar")
            self.bot.delete_message(call.message.chat.id, status_msg.message_id)

        except Exception as e:
            print(f"Image Error: {e}")
            self.bot.edit_message_text("❌ Gagal mengompres gambar. File mungkin rusak.", call.message.chat.id, status_msg.message_id)
        finally:
            self._cleanup(input_path, output_path)

    def process_pdf(self, call):
        """Proses Kompresi PDF (Metode Kompatibel TANPA linearize)."""
        msg = call.message.reply_to_message
        status_msg = self.bot.send_message(call.message.chat.id, "⏳ Mengompres PDF (Mode Kompatibel)...")
        input_path, output_path = None, None

        try:
            file_info = self.bot.get_file(msg.document.file_id)
            downloaded_data = self.bot.download_file(file_info.file_path)
            
            timestamp = int(time.time())
            input_path = os.path.join(self.temp_folder, f"pdf_in_{timestamp}.pdf")
            output_path = os.path.join(self.temp_folder, f"pdf_out_{timestamp}.pdf")

            with open(input_path, "wb") as f: f.write(downloaded_data)

            original_size = os.path.getsize(input_path) / 1024
            
            with pikepdf.open(input_path) as pdf:
                
                # --- INI METODE YANG BENAR (TANPA 'minimize_size') ---
                # 1. Hapus metadata (jika ada)
                try: 
                    del pdf.Root.Metadata
                except: 
                    pass
                
                # 2. Hapus data tidak terpakai
                try:
                    pdf.remove_unreferenced_resources()
                except:
                    pass

                # 3. Simpan dengan kompresi stream (TANPA linearize)
                pdf.save(
                    output_path, 
                    object_stream_mode=pikepdf.ObjectStreamMode.generate
                )
                # ----------------------------------------------------

            compressed_size = os.path.getsize(output_path) / 1024
            
            # Cek apakah ukurannya benar-benar berkurang
            if compressed_size >= original_size:
                self.bot.edit_message_text("ℹ️ Info: File PDF ini sudah optimal (tidak bisa dikecilkan lagi).", call.message.chat.id, status_msg.message_id)
            else:
                self._send_result(call.message.chat.id, output_path, original_size, compressed_size, "PDF")
                self.bot.delete_message(call.message.chat.id, status_msg.message_id)

        except Exception as e:
            print(f"PDF Error: {e}")
            self.bot.edit_message_text(f"❌ Gagal kompres PDF: File mungkin terkunci/rusak.", call.message.chat.id, status_msg.message_id)
        finally:
            self._cleanup(input_path, output_path)

    def _send_result(self, chat_id, file_path, ori_size, comp_size, type_name):
        """Helper untuk mengirim file hasil."""
        saved = ori_size - comp_size
        percent = (saved / ori_size) * 100 if ori_size > 0 else 0
        
        caption = (
            f"✅ **{type_name} Berhasil Dikompres!**\n"
            f"📦 Sebelum: {ori_size:.1f} KB\n"
            f"📄 Sesudah: {comp_size:.1f} KB\n"
            f"🔕 Hemat: {saved:.1f} KB ({percent:.0f}%)"
        )
        with open(file_path, "rb") as f:
            self.bot.send_document(chat_id, f, caption=caption, parse_mode="Markdown")

    def _cleanup(self, *paths):
        """Membersihkan file sementara."""
        for path in paths:
            try:
                if os.path.exists(path): os.remove(path)
            except: pass