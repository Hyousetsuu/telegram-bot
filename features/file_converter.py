import os
import datetime
import shutil
from io import BytesIO 
from telebot import TeleBot, types
from PIL import Image
import fitz
import logging

logger = logging.getLogger(__name__)

class FileConverter:
    def __init__(self, bot: TeleBot):
        self.bot = bot
        self.temp_dir = 'temp_conversions'
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def _cleanup(self, filepaths):
        for fp in filepaths:
            if fp and os.path.exists(fp):
                os.remove(fp)

    def img_to_pdf(self, message):
        replied_message = message.reply_to_message
        if not replied_message or not replied_message.photo:
            self.bot.reply_to(message, "Gunakan perintah ini dengan membalas (reply) pesan yang berisi **gambar**.")
            return

        pesan_tunggu = self.bot.send_message(message.chat.id, "Memulai konversi gambar ke PDF... 🖼️➡️📄")
        input_filepath = None
        output_filepath = None
        
        try:
            photo = replied_message.photo[-1] 
            file_info = self.bot.get_file(photo.file_id)
            input_filepath = os.path.join(self.temp_dir, f"{photo.file_id}.jpg")
            
            downloaded_file = self.bot.download_file(file_info.file_path)
            with open(input_filepath, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            output_filename = f"{message.chat.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            output_filepath = os.path.join(self.temp_dir, output_filename)
            
            image = Image.open(input_filepath).convert('RGB')
            image.save(output_filepath, "PDF")
            
            with open(output_filepath, 'rb') as f:
                self.bot.send_document(message.chat.id, f, caption=f"✅ Gambar dikonversi ke PDF!")

        except Exception as e:
            logger.error(f"[ImgToPDF] Error: {e}")
            self.bot.send_message(message.chat.id, f"❌ Maaf, ada error saat konversi Image ke PDF: {e}")
        
        finally:
            self.bot.delete_message(message.chat.id, pesan_tunggu.message_id)
            self._cleanup([input_filepath, output_filepath])


    def pdf_to_img(self, message):
        replied_message = message.reply_to_message
        is_pdf = replied_message and replied_message.document and replied_message.document.mime_type == 'application/pdf'
        
        if not is_pdf:
            self.bot.reply_to(message, "Gunakan perintah ini dengan membalas (reply) pesan yang berisi **file PDF**.")
            return

        document = replied_message.document
        pesan_tunggu = self.bot.send_message(message.chat.id, "Memulai konversi PDF ke Gambar (JPEG)... 📄➡️🖼️")
        input_filepath = None
        output_filepaths = []

        try:
            if document.file_size > 10 * 1024 * 1024: 
                raise ValueError(f"File PDF terlalu besar. Batas maksimum 10MB.")

            file_info = self.bot.get_file(document.file_id)
            input_filepath = os.path.join(self.temp_dir, document.file_name)
            
            downloaded_file = self.bot.download_file(file_info.file_path)
            with open(input_filepath, 'wb') as new_file:
                new_file.write(downloaded_file)

            doc = fitz.open(input_filepath)
            num_pages = doc.page_count
            
            if num_pages > 10: 
                doc.close()
                raise ValueError(f"PDF memiliki {num_pages} halaman. Batas maksimum 10 halaman.")

            photo_files = []
            
            for page_num in range(num_pages):
                self.bot.edit_message_text(f"Mengerjakan halaman {page_num + 1}/{num_pages}...", message.chat.id, pesan_tunggu.message_id)
                
                page = doc.load_page(page_num)
                zoom = 2.0
                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                
                output_filename = f"{document.file_id}_page{page_num+1}.jpg"
                output_filepath = os.path.join(self.temp_dir, output_filename)
                pix.save(output_filepath)
                output_filepaths.append(output_filepath)
                
                with open(output_filepath, 'rb') as f_out:
                    photo_files.append(types.InputMediaPhoto(f_out.read(), caption=f"Halaman {page_num+1} dari {num_pages}"))

            doc.close()
            
            if photo_files:
                self.bot.send_media_group(message.chat.id, photo_files)
                self.bot.send_message(message.chat.id, f"✅ Total {num_pages} halaman berhasil dikonversi ke Gambar.")

        except Exception as e:
            logger.error(f"[PDFToImg] Error: {e}")
            self.bot.send_message(message.chat.id, f"❌ Maaf, ada error saat konversi PDF ke Gambar: {str(e)}")
            
        finally:
            self.bot.delete_message(message.chat.id, pesan_tunggu.message_id)
            self._cleanup([input_filepath] + output_filepaths)
