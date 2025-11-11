import os
import re
import google.generativeai as genai
from datetime import datetime
import pytz

# Pastikan layanan ini ada di folder features/services/
from features.services.weather_service import WeatherService
from features.services.news_service import NewsService

class GeminiAssistant:
    def __init__(self, bot):
        self.bot = bot
        self.weather_service = WeatherService()
        self.news_service = NewsService()

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        # ========================================================
        # SYSTEM PROMPT 
        # ========================================================
        SYSTEM_PROMPT = """
        Kamu adalah asisten bot Telegram yang cerdas, serba bisa, dan sangat membantu.
        Kamu memiliki DUA peran:

        1.  **AI PENGETAHUAN UMUM:** Kamu bisa menjawab pertanyaan apa saja (seperti Gemini). Ini termasuk sejarah, fakta unik, resep, kode, terjemahan, dll.
        2.  **OPERATOR FITUR BOT:** Kamu juga terhubung dengan fitur-fitur bot berikut:
            - Downloader (YouTube, TikTok, IG)
            - Kompresor (Gambar/PDF)
            - Konverter (Gambar <-> PDF)
            - Info (Berita & Cuaca)

        PANDUAN MENJAWAB:
        -   **JIKA** pertanyaan adalah tentang pengetahuan umum (Contoh: "fun fact surakarta", "ibu kota prancis?", "cara masak nasi"), **JAWAB LANGSUNG** menggunakan pengetahuan AI-mu.
        -   **JIKA** user bertanya soal fitur (Contoh: "bisa kompres?"), JAWAB dengan instruksi (Contoh: "Bisa! Kirim aja filenya, nanti aku kasih pilihan.").
        -   **JANGAN PERNAH** bilang "Saya tidak punya database" atau "Saya tidak bisa" untuk pertanyaan pengetahuan umum. Kamu adalah AI, kamu pasti tahu.
        """

        self.model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT
        )

    def _get_local_time_str(self):
        tz = pytz.timezone("Asia/Jakarta")
        return datetime.now(tz).strftime("%A, %d %B %Y, Jam %H:%M WIB")

    def _extract_city(self, text):
        """Mengekstrak nama kota dengan Regex yang lebih baik."""
        text_lower = text.lower()
        match_di = re.search(r"cuaca(?:[\w\s]+)?\bdi\s+([a-zA-Z\s]+)", text_lower)
        if match_di:
            city = match_di.group(1).strip().replace("hari ini", "").replace("besok", "").strip()
            return city
        match_langsung = re.search(r"cuaca\s+(?!di\b)([a-zA-Z\s]+)", text_lower)
        if match_langsung:
            city = match_langsung.group(1).strip().replace("hari ini", "").replace("besok", "").strip()
            if not city: return "Jakarta"
            return city
        return "Jakarta"

    def _extract_news_params(self, text):
        """Ekstrak topik dan jumlah berita."""
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
        """Handler utama AI: Cek fitur dulu, baru fallback ke AI."""
        
        # Pastikan message.text ada (jika user kirim foto tanpa caption)
        if not message.text:
            return # Abaikan jika pesan tidak punya teks

        text = message.text.lower()
        chat_id = message.chat.id

        # --- 1. Cek Waktu ---
        if any(kw in text for kw in ["jam berapa", "waktu sekarang"]):
             self.bot.reply_to(message, f"🕓 Sekarang: {self._get_local_time_str()}")
             return

        # --- 2. Cek Cuaca & Berita ---
        if "cuaca" in text and "berita" in text:
             self.bot.send_chat_action(chat_id, 'typing')
             t, c = self._extract_news_params(text)
             w = self.weather_service.get_weather(self._extract_city(text))
             n = self.news_service.get_news(t, count=c)
             self.bot.reply_to(message, f"{w}\n\n──────────────\n\n{n}", parse_mode="Markdown")
             return

        if "cuaca" in text:
            self.bot.send_chat_action(chat_id, 'typing')
            city = self._extract_city(text)
            self.bot.reply_to(message, self.weather_service.get_weather(city), parse_mode="Markdown")
            return

        if "berita" in text:
            self.bot.send_chat_action(chat_id, 'typing')
            t, c = self._extract_news_params(text)
            self.bot.reply_to(message, self.news_service.get_news(t, count=c), parse_mode="Markdown")
            return
            
        # --- 3. Handler Khusus Pertanyaan Fitur (Agar AI tidak bingung) ---
        # (Ini adalah "guard" agar AI tidak halusinasi)
        if any(kw in text for kw in ["compress", "kompres", "kecilin file"]):
             self.bot.reply_to(message, "📉 Bisa! Langsung aja kirim file Gambar atau PDF nya, nanti aku kasih pilihan aksi.", parse_mode="Markdown")
             return
        if any(kw in text for kw in ["convert", "konversi", "ubah file"]):
             self.bot.reply_to(message, "🔄 Siap! Kirim file (Gambar/PDF) nanti aku kasih pilihan konversi.", parse_mode="Markdown")
             return

        # --- 4. Fallback ke PENGETAHUAN UMUM (Gemini AI) ---
        # (Pertanyaan "fun fact surakarta" akan masuk ke sini)
        try:
            self.bot.send_chat_action(chat_id, 'typing')
            res = self.model.generate_content(f"[Waktu: {self._get_local_time_str()}]\nUser: {message.text}")
            self.bot.reply_to(message, res.text, parse_mode="Markdown")
        except Exception as e:
            print(f"Gemini Error: {e}")
            self.bot.reply_to(message, "🤖 Maaf, sistem AI sedang sibuk.")