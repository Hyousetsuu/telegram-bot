import os
import logging
from telebot import TeleBot, types
from gtts import gTTS
from io import BytesIO


logger = logging.getLogger(__name__)

class TextToSpeechConverter:
    def __init__(self, bot: TeleBot):
        self.bot = bot
        self.temp_dir = 'temp_tts'
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            
    def text_to_audio(self, message):
        text = message.text.replace("/tts", "", 1).strip()
        
        if not text:
            self.bot.reply_to(message, "⚠️ Masukkan teks setelah perintah /tts. Contoh: /tts Selamat pagi semuanya!")
            return
        
        pesan_tunggu = self.bot.send_message(message.chat.id, "Membuat audio dari teks... 🎤➡️🎶")
        
        try:
           
            if len(text) > 200:
                text = text[:200]
                self.bot.send_message(message.chat.id, "Teks dipotong menjadi 200 karakter pertama untuk konversi audio.")

            mp3_fp = BytesIO()
            
            # Konversi teks ke suara (menggunakan bahasa Indonesia)
            tts = gTTS(text=text, lang='id')
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            
            # Kirim file audio sebagai voice message
            self.bot.send_voice(
                message.chat.id, 
                mp3_fp, 
                caption=f"✅ Audio berhasil dibuat dari teks.",
                reply_to_message_id=message.message_id
            )
            
        except Exception as e:
            logger.error(f"[TTS] Error: {e}")
            self.bot.send_message(message.chat.id, f"❌ Maaf, ada error saat konversi Teks ke Suara: {e}")
            
        finally:
            self.bot.delete_message(message.chat.id, pesan_tunggu.message_id)
