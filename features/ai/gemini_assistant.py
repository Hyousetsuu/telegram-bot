import os
import re
import requests
import google.generativeai as genai
from datetime import datetime
import pytz

from features.services.weather_service import WeatherService

class GeminiAssistant:
    def __init__(self, bot):
        self.bot = bot
        self.weather_service = WeatherService()

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        SYSTEM_PROMPT = """
        Kamu adalah asisten bot Telegram yang cerdas dan ramah.
        
        FITUR CANGGIH YANG KAMU MILIKI:
        1. DOWNLOADER: Bisa download dari Instagram, TikTok, dan YouTube (jika ada link).
        2. FILE COMPRESSOR: Bisa memperkecil ukuran GAMBAR (JPG/PNG) dan file PDF.
        3. INFO: Bisa cek cuaca terkini.
        
        PANDUAN MENJAWAB:
        - Jika user minta download tanpa link -> Jawab: "Siap! Kirimkan linknya ya. 😉"
        - Jika user tanya "bisa kompres apa aja?" -> Jawab: "Aku bisa kompres gambar (JPG/PNG) dan juga file PDF lho! Kirim aja filenya. 📂"
        - JANGAN PERNAH bilang kamu tidak bisa melakukan hal-hal di atas.
        """

        self.model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT
        )

    def _get_local_time_str(self):
        tz = pytz.timezone("Asia/Jakarta")
        return datetime.now(tz).strftime("%A, %d %B %Y, Jam %H:%M WIB")

    def _extract_city(self, text):
        match = re.search(r"cuaca(?: di| kota)?\s+(.*)", text, re.IGNORECASE)
        if not match: return "Jakarta"
        raw = match.group(1).lower()
        for w in ["hari ini", "saat ini", "sekarang", "besok"]: raw = raw.replace(w, "")
        return re.sub(r'[?!.,]', '', raw).strip() or "Jakarta"

    def reply(self, message):
        text = message.text.lower()
        chat_id = message.chat.id

        # Waktu
        if any(kw in text for kw in ["jam berapa", "waktu sekarang"]):
            self.bot.reply_to(message, f"🕓 Sekarang: {self._get_local_time_str()}")
            return

        # Kompresi
        if any(kw in text for kw in ["compress", "kompres", "kecilin file", "kecilin gambar", "perkecil ukuran"]):
            self.bot.reply_to(
                message,
                "📉 *Fitur Kompresor Gambar*\nBisa banget! Kirim aja gambar atau PDF-nya 😉",
                parse_mode="Markdown"
            )
            return

        # Cuaca
        if "cuaca" in text:
            self.bot.send_chat_action(chat_id, 'typing')
            self.bot.reply_to(message, self.weather_service.get_weather(self._extract_city(text)), parse_mode="Markdown")
            return

        # Fallback — ke Gemini AI
        try:
            self.bot.send_chat_action(chat_id, 'typing')
            res = self.model.generate_content(f"[Waktu: {self._get_local_time_str()}]\nUser: {message.text}")
            self.bot.reply_to(message, res.text, parse_mode="Markdown")
        except Exception as e:
            print(f"Gemini Error: {e}")
            self.bot.reply_to(message, "🤖 Maaf, sistem sedang sibuk.")