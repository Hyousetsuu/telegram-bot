import os
import time
import fitz  # PyMuPDF
from PIL import Image
from telebot import types

class FileConverter:
    def __init__(self, bot):
        self.bot = bot
        self.temp_folder = "temp_convert"
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

    def process_img_to_pdf(self, call):
        """Proses Konversi Gambar ke PDF (Dipanggil oleh callback)."""
        self.bot.edit_message_text("⏳ Mengonversi Gambar ke PDF...", call.message.chat.id, call.message.message_id, reply_markup=None)
        status_msg = None
        input_path, output_path = None, None
        
        try:
            file_id, ext = self._get_file_id_from_call(call)
            if ext not in [".jpg", ".png", ".jpeg"]:
                raise Exception("Bukan file gambar.")
            
            status_msg = self.bot.send_message(call.message.chat.id, "⏳ Mengunduh & mengonversi...")

            file_info = self.bot.get_file(file_id)
            data = self.bot.download_file(file_info.file_path)
            
            ts = int(time.time())
            input_path = os.path.join(self.temp_folder, f"conv_in_{ts}{ext}")
            output_path = os.path.join(self.temp_folder, f"conv_out_{ts}.pdf")

            with open(input_path, "wb") as f: f.write(data)

            img = Image.open(input_path)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.save(output_path, "PDF", resolution=100.0)

            with open(output_path, "rb") as f:
                self.bot.send_document(call.message.chat.id, f, caption="✅ Konversi Gambar ke PDF berhasil!")
            self.bot.delete_message(call.message.chat.id, status_msg.message_id)

        except Exception as e:
            print(f"ImgToPdf Error: {e}")
            if status_msg: self.bot.edit_message_text(f"❌ Gagal: {e}", call.message.chat.id, status_msg.message_id)
            else: self.bot.send_message(call.message.chat.id, f"❌ Gagal: {e}")
        finally:
            self._cleanup(input_path, output_path)

    def process_pdf_to_img(self, call):
        """Proses Konversi PDF ke Gambar (Dipanggil oleh callback)."""
        self.bot.edit_message_text("⏳ Mengonversi PDF ke Gambar...", call.message.chat.id, call.message.message_id, reply_markup=None)
        status_msg = None
        input_path = None
        output_files = []
        
        try:
            file_id, ext = self._get_file_id_from_call(call)
            if ext != ".pdf":
                raise Exception("Bukan file PDF.")
            
            status_msg = self.bot.send_message(call.message.chat.id, "⏳ Mengunduh & mengonversi PDF...")

            file_info = self.bot.get_file(file_id)
            data = self.bot.download_file(file_info.file_path)
            
            ts = int(time.time())
            input_path = os.path.join(self.temp_folder, f"conv_in_{ts}.pdf")
            with open(input_path, "wb") as f: f.write(data)

            doc = fitz.open(input_path)
            
            total_pages = len(doc)
            page_count = min(total_pages, 5) # Batasi 5 halaman
            
            for i in range(page_count):
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=150)
                output_path = os.path.join(self.temp_folder, f"conv_out_{ts}_page_{i+1}.jpg")
                pix.save(output_path)
                output_files.append(output_path)
            doc.close()

            self.bot.edit_message_text(f"✅ Berhasil mengonversi {page_count} halaman! Mengirim gambar...", call.message.chat.id, status_msg.message_id)
            for file_path in output_files:
                with open(file_path, "rb") as f:
                    self.bot.send_document(call.message.chat.id, f, caption=f"{os.path.basename(file_path)}")
            
            if total_pages > page_count:
                self.bot.send_message(call.message.chat.id, f"ℹ️ Info: Hanya {page_count} halaman pertama yang dikonversi (batas maksimum).")

        except Exception as e:
            print(f"PdfToImg Error: {e}")
            if status_msg: self.bot.edit_message_text(f"❌ Gagal: {e}", call.message.chat.id, status_msg.message_id)
            else: self.bot.send_message(call.message.chat.id, f"❌ Gagal: {e}")
        finally:
            self._cleanup(input_path, *output_files)

    def _cleanup(self, *paths):
        """Membersihkan file sementara."""
        for path in paths:
            try:
                if path and os.path.exists(path): 
                    os.remove(path)
            except: 
                pass