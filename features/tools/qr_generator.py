import os
import logging
from telebot import TeleBot, types
import qrcode
from io import BytesIO


logger = logging.getLogger(__name__)

class QRCodeGenerator:
    def __init__(self, bot: TeleBot):
        self.bot = bot

    def generate_qr(self, message):
        data = message.text.replace("/qr", "", 1).strip()
        
        if not data:
            self.bot.reply_to(message, "⚠️ Masukkan teks atau link setelah perintah /qr. Contoh: /qr https://google.com atau /qr Halo Dunia")
            return

        pesan_tunggu = self.bot.send_message(message.chat.id, "Membuat Kode QR... 🔲")

        try:
            # Batas ukuran data agar QR code tidak terlalu kompleks
            if len(data) > 500:
                data = data[:500]
                self.bot.send_message(message.chat.id, "Data dipotong menjadi 500 karakter pertama.")

            # Membuat objek QRCode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            
            # Simpan gambar ke BytesIO
            img_fp = BytesIO()
            img.save(img_fp, format='PNG')
            img_fp.seek(0)
            
            # Kirim gambar
            self.bot.send_photo(
                message.chat.id, 
                img_fp, 
                caption=f"✅ Kode QR berhasil dibuat dari data:\n`{data}`",
                parse_mode='Markdown',
                reply_to_message_id=message.message_id
            )

        except Exception as e:
            logger.error(f"[QR] Error: {e}")
            self.bot.send_message(message.chat.id, f"❌ Maaf, ada error saat membuat QR Code: {e}")
            
        finally:
            self.bot.delete_message(message.chat.id, pesan_tunggu.message_id)
