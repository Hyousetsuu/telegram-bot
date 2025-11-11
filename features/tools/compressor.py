import os
import time
from PIL import Image
import pikepdf
from telebot import types

class Compressor:
    def __init__(self, bot):
        self.bot = bot
        self.temp_folder = "temp_compress"
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)
        
        self.MAX_DOWNLOAD_SIZE = 20 * 1024 * 1024 # 20MB

    def _get_file_id_from_call(self, call):
        """Helper untuk mengambil file_id dari pesan yang dibalas oleh tombol."""
        msg = call.message.reply_to_message # Ini adalah pesan file asli
        
        file_id, ext = None, ".tmp"
        file_size = 0

        if msg.photo:
            file_id = msg.photo[-1].file_id
            file_size = msg.photo[-1].file_size
            ext = ".jpg"
        elif msg.document:
            file_id = msg.document.file_id
            file_size = msg.document.file_size
            mime = msg.document.mime_type
            if mime.startswith("image/"):
                ext = ".png" if "png" in mime else ".jpg"
            elif mime == "application/pdf":
                ext = ".pdf"
        
        if file_size > self.MAX_DOWNLOAD_SIZE:
            raise Exception(f"File terlalu besar ({file_size / (1024*1024):.1f} MB). Batas 20 MB.")
            
        if not file_id:
            raise Exception("File tidak dapat ditemukan.")
            
        return file_id, ext

    def process_image(self, call, quality):
        """Proses Kompresi Gambar (Dipanggil oleh callback)."""
        # Edit pesan tombol menjadi "Memproses..."
        self.bot.edit_message_text("⏳ Mengompres gambar...", call.message.chat.id, call.message.message_id, reply_markup=None)
        status_msg = None
        input_path, output_path = None, None
        
        try:
            file_id, ext = self._get_file_id_from_call(call)
            
            # Buat pesan status baru
            status_msg = self.bot.send_message(call.message.chat.id, f"⏳ Mengunduh & mengompres ke {quality}%...")

            file_info = self.bot.get_file(file_id)
            data = self.bot.download_file(file_info.file_path)
            
            ts = int(time.time())
            input_path = os.path.join(self.temp_folder, f"img_in_{ts}{ext}")
            output_path = os.path.join(self.temp_folder, f"img_out_{ts}{ext}")

            with open(input_path, "wb") as f: f.write(data)

            ori_size = os.path.getsize(input_path) / 1024
            img = Image.open(input_path)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.save(output_path, "JPEG", optimize=True, quality=quality)
            comp_size = os.path.getsize(output_path) / 1024

            self._send_result(call.message.chat.id, output_path, ori_size, comp_size, "Gambar")
            self.bot.delete_message(call.message.chat.id, status_msg.message_id) # Hapus pesan status
            
        except Exception as e:
            print(f"Image Error: {e}")
            if status_msg: self.bot.edit_message_text(f"❌ Gagal: {e}", call.message.chat.id, status_msg.message_id)
            else: self.bot.send_message(call.message.chat.id, f"❌ Gagal: {e}")
        finally:
            self._cleanup(input_path, output_path)

    def process_pdf(self, call):
        """Proses Kompresi PDF (Dipanggil oleh callback)."""
        self.bot.edit_message_text("⏳ Mengompres PDF...", call.message.chat.id, call.message.message_id, reply_markup=None)
        status_msg = None
        input_path, output_path = None, None
        
        try:
            file_id, ext = self._get_file_id_from_call(call)
            if ext != ".pdf": raise Exception("Bukan file PDF.")
            
            status_msg = self.bot.send_message(call.message.chat.id, "⏳ Mengunduh & mengompres PDF...")

            file_info = self.bot.get_file(file_id)
            data = self.bot.download_file(file_info.file_path)
            
            ts = int(time.time())
            input_path = os.path.join(self.temp_folder, f"pdf_in_{ts}.pdf")
            output_path = os.path.join(self.temp_folder, f"pdf_out_{ts}.pdf")

            with open(input_path, "wb") as f: f.write(data)

            ori_size = os.path.getsize(input_path) / 1024
            
            with pikepdf.open(input_path) as pdf:
                try: del pdf.Root.Metadata
                except: pass
                try: pdf.remove_unreferenced_resources()
                except: pass
                pdf.save(output_path, object_stream_mode=pikepdf.ObjectStreamMode.generate)

            comp_size = os.path.getsize(output_path) / 1024

            if comp_size >= ori_size:
                self.bot.edit_message_text("ℹ️ PDF ini sudah optimal.", call.message.chat.id, status_msg.message_id)
            else:
                self._send_result(call.message.chat.id, output_path, ori_size, comp_size, "PDF")
                self.bot.delete_message(call.message.chat.id, status_msg.message_id)
        except Exception as e:
            print(f"PDF Error: {e}")
            if status_msg: self.bot.edit_message_text(f"❌ Gagal: {e}", call.message.chat.id, status_msg.message_id)
            else: self.bot.send_message(call.message.chat.id, f"❌ Gagal: {e}")
        finally:
            self._cleanup(input_path, output_path)

    def _send_result(self, chat_id, file_path, ori_size, comp_size, type_name):
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
        for path in paths:
            try:
                if path and os.path.exists(path): os.remove(path)
            except: pass