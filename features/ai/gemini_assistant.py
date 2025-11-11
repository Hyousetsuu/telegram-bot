import os
import re
import google.generativeai as genai
from datetime import datetime
import pytz

from features.services.weather_service import WeatherService
from features.services.news_service import NewsService

class GeminiAssistant:
    def __init__(self, bot):
        self.bot = bot
        self.weather_service = WeatherService()
        self.news_service = NewsService()

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        # UPDATE: Tambahkan info soal fitur kompresi di System Prompt
        SYSTEM_PROMPT = """
        Kamu adalah asisten bot Telegram yang cerdas dan ramah.
        
        FITUR CANGGIH YANG KAMU MILIKI:
        1. DOWNLOADER: Bisa download dari Instagram, TikTok, dan YouTube (jika ada link).
        2. FILE COMPRESSOR: Bisa memperkecil ukuran GAMBAR (JPG/PNG) dan file PDF.
        3. INFO: Bisa cek berita terkini dan prediksi cuaca.
        
        PANDUAN MENJAWAB:
        - Jika user minta download tanpa link -> Jawab: "Siap! Kirimkan linknya ya. 😉"
        - Jika user tanya "bisa kompres apa aja?" -> Jawab: "Aku bisa kompres gambar (JPG/PNG) dan juga file PDF lho! Kirim aja filenya. 📂"
        - JANGAN PERNAH bilang kamu tidak bisa melakukan hal-hal di atas.
        """

        self.model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT
        )

    # ... (Metode _get_local_time_str, _extract_city, _extract_news_params TETAP SAMA, tidak perlu diubah) ...
    def _get_local_time_str(self):
        tz = pytz.timezone("Asia/Jakarta")
        return datetime.now(tz).strftime("%A, %d %B %Y, Jam %H:%M WIB")

    def _extract_city(self, text):
        # ... (kode sama seperti sebelumnya) ...
        match = re.search(r"cuaca(?: di| kota)?\s+(.*)", text, re.IGNORECASE)
        if not match: return "Jakarta"
        raw = match.group(1).lower()
        for w in ["hari ini", "saat ini", "sekarang", "besok"]: raw = raw.replace(w, "")
        return re.sub(r'[?!.,]', '', raw).strip() or "Jakarta"

    def _extract_news_params(self, text):
        # ... (kode sama seperti sebelumnya) ...
        count_match = re.search(r"\b(\d+)\s*(?:berita|artikel|kabar)?\b", text, re.IGNORECASE)
        count = int(count_match.group(1)) if count_match else 5
        count = max(1, min(count, 10))
        raw_topic = re.search(r"berita\s+(.*)", text, re.IGNORECASE)
        raw_topic = raw_topic.group(1).lower() if raw_topic else ""
        raw_topic = re.sub(r'\b\d+\b', '', raw_topic)
        raw_topic = re.sub(r'[^\w\s]', '', raw_topic)
        for word in ["tentang", "topik", "terkini", "hari ini", "di ", "yang", "minta", "berikan"]:
            raw_topic = raw_topic.replace(word, " ")
        return " ".join(raw_topic.split()) or "indonesia", count

    def reply(self, message):
        text = message.text.lower()
        chat_id = message.chat.id

        # --- 1. Cek Waktu ---
        if any(kw in text for kw in ["jam berapa", "waktu sekarang"]):
             self.bot.reply_to(message, f"🕓 Sekarang: {self._get_local_time_str()}")
             return

        # --- 2. Handler Khusus Pertanyaan Kompresi (Biar lebih responsif) ---
        # Menangkap pertanyaan seperti: "bisa compress?", "cara kecilin gambar gimana?"
        if any(kw in text for kw in ["compress", "kompres", "kecilin file", "kecilin gambar", "perkecil ukuran"]):
            self.bot.reply_to(message, "📉 **Fitur Kompresor Gambar**\nBisa banget! Langsung aja kirim gambar atau foto yang mau dikecilin ukurannya ya. Nanti aku kasih pilihan kualitasnya. 😉", parse_mode="Markdown")
            return

        # --- 3. Cek Cuaca & Berita ---
        if "cuaca" in text and "berita" in text:
             self.bot.send_chat_action(chat_id, 'typing')
             t, c = self._extract_news_params(text)
             w = self.weather_service.get_weather(self._extract_city(text))
             n = self.news_service.get_news(t, count=c)
             self.bot.reply_to(message, f"{w}\n\n──────────────\n\n{n}", parse_mode="Markdown")
             return

        if "cuaca" in text:
            self.bot.send_chat_action(chat_id, 'typing')
            self.bot.reply_to(message, self.weather_service.get_weather(self._extract_city(text)), parse_mode="Markdown")
            return

        if "berita" in text:
            self.bot.send_chat_action(chat_id, 'typing')
            t, c = self._extract_news_params(text)
            self.bot.reply_to(message, self.news_service.get_news(t, count=c), parse_mode="Markdown")
            return

        # --- 4. Fallback ke Gemini AI ---
        try:
            self.bot.send_chat_action(chat_id, 'typing')
            res = self.model.generate_content(f"[Waktu: {self._get_local_time_str()}]\nUser: {message.text}")
            self.bot.reply_to(message, res.text, parse_mode="Markdown")
        except Exception as e:
            print(f"Gemini Error: {e}")
            self.bot.reply_to(message, "🤖 Maaf, sistem sedang sibuk.")