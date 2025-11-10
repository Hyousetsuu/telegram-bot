import os
import time
from PIL import Image
import pikepdf # Import library baru
from telebot import types

class Compressor: # Saya ganti nama jadi lebih umum (bukan ImageCompressor lagi)
    def __init__(self, bot):
        self.bot = bot
        self.temp_folder = "temp_compress"
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)

    def offer_compression(self, message):
        """Menawarkan opsi sesuai tipe file."""
        markup = types.InlineKeyboardMarkup()
        
        # Deteksi Tipe File
        is_image = False
        is_pdf = False

        if message.photo:
            is_image = True
        elif message.document:
            if message.document.mime_type.startswith("image/"):
                is_image = True
            elif message.document.mime_type == "application/pdf":
                is_pdf = True

        # Tampilkan tombol sesuai tipe
        if is_image:
            markup.add(
                types.InlineKeyboardButton("📉 Ringan (70%)", callback_data="img_70"),
                types.InlineKeyboardButton("😐 Sedang (50%)", callback_data="img_50"),
                types.InlineKeyboardButton("🗜 Ekstrem (30%)", callback_data="img_30")
            )
            text = "🖼 **Kompresor Gambar**\nPilih tingkat kompresi:"
            
        elif is_pdf:
            # PDF hanya punya 1 mode kompresi standar (aman)
            markup.add(types.InlineKeyboardButton("🗜 Kompres PDF Sekarang", callback_data="pdf_compress"))
            text = "📄 **Kompresor PDF**\nTekan tombol di bawah untuk memperkecil ukuran PDF."
            
        else:
            return # Tipe tidak didukung

        self.bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")

    def process_image(self, call, quality):
        """Proses Kompresi Gambar (JPG/PNG)."""
        msg = call.message.reply_to_message
        status_msg = self.bot.send_message(call.message.chat.id, f"⏳ Mengompres gambar ke {quality}%...")

        try:
            # 1. Ambil File ID
            if msg.photo:
                file_id = msg.photo[-1].file_id
                ext = ".jpg"
            else:
                file_id = msg.document.file_id
                ext = ".png" if "png" in msg.document.mime_type else ".jpg"

            # 2. Download
            file_info = self.bot.get_file(file_id)
            downloaded_data = self.bot.download_file(file_info.file_path)
            
            timestamp = int(time.time())
            input_path = os.path.join(self.temp_folder, f"img_in_{timestamp}{ext}")
            output_path = os.path.join(self.temp_folder, f"img_out_{timestamp}{ext}")

            with open(input_path, "wb") as f: f.write(downloaded_data)

            # 3. Kompres (Pillow)
            original_size = os.path.getsize(input_path) / 1024
            img = Image.open(input_path)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.save(output_path, "JPEG", optimize=True, quality=quality)
            compressed_size = os.path.getsize(output_path) / 1024

            # 4. Kirim
            self._send_result(call.message.chat.id, output_path, original_size, compressed_size, "Gambar")
            self.bot.delete_message(call.message.chat.id, status_msg.message_id)

        except Exception as e:
            self.bot.edit_message_text(f"❌ Gagal: {e}", call.message.chat.id, status_msg.message_id)
        finally:
            self._cleanup(input_path, output_path)

    def process_pdf(self, call):
        """Proses Kompresi PDF."""
        msg = call.message.reply_to_message
        status_msg = self.bot.send_message(call.message.chat.id, "⏳ Mengompres PDF (bisa agak lama)...")

        try:
            # 1. Download
            file_info = self.bot.get_file(msg.document.file_id)
            downloaded_data = self.bot.download_file(file_info.file_path)
            
            timestamp = int(time.time())
            input_path = os.path.join(self.temp_folder, f"pdf_in_{timestamp}.pdf")
            output_path = os.path.join(self.temp_folder, f"pdf_out_{timestamp}.pdf")

            with open(input_path, "wb") as f: f.write(downloaded_data)

            # 2. Kompres (pikepdf)
            original_size = os.path.getsize(input_path) / 1024
            
            with pikepdf.open(input_path) as pdf:
                # OPSI ALTERNATIF JIKA 'minimize_size' ERROR:
                # Hapus metadata yang tidak perlu untuk mengurangi ukuran file
                try:
                     del pdf.Root.Metadata
                except:
                     pass

                # Simpan dengan linearisasi (webview) yang seringkali sedikit lebih kecil
                # dan matikan kompresi objek stream agar kompatibel tapi tetap efisien
                pdf.save(output_path, linearize=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)

            compressed_size = os.path.getsize(output_path) / 1024

            # 3. Kirim
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