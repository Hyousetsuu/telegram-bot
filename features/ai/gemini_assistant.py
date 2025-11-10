import os
import re
import google.generativeai as genai

class GeminiAssistant:
    def __init__(self, bot):
        self.bot = bot

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        SYSTEM_PROMPT = """
        Kamu adalah asisten bot Telegram yang cerdas dan ramah.

        FITUR CANGGIH YANG KAMU MILIKI:
        1. DOWNLOADER: Bisa download dari Instagram, TikTok, dan YouTube (jika ada link).
        2. FILE COMPRESSOR: Bisa memperkecil ukuran GAMBAR (JPG/PNG) dan file PDF.

        PANDUAN MENJAWAB:
        - Jika user minta download tanpa link -> Jawab: "Siap! Kirimkan linknya ya. 😉"
        - Jika user tanya "bisa kompres apa aja?" -> Jawab: "Aku bisa kompres gambar (JPG/PNG) dan juga file PDF lho! Kirim aja filenya. 📂"
        - JANGAN PERNAH bilang kamu tidak bisa melakukan hal-hal di atas.
        """

        self.model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT
        )

    def handle_message(self, message):
        """Menangani pesan teks dari user."""
        text = message.text.lower()

        # 🔍 Deteksi perintah kompresi
        if any(kw in text for kw in ["compress", "kompres", "kecilin file", "kecilin gambar", "perkecil ukuran"]):
            self.bot.reply_to(
                message,
                "📉 **Fitur Kompresor Gambar**\n"
                "Bisa banget! Langsung aja kirim gambar atau PDF yang mau dikecilin ukurannya ya. 😉",
                parse_mode="Markdown"
            )
            return

        # 🤖 Balasan dari Gemini
        try:
            self.bot.send_chat_action(message.chat.id, 'typing')
            res = self.model.generate_content(f"User: {text}")
            self.bot.reply_to(message, res.text, parse_mode="Markdown")
        except Exception as e:
            print(f"Gemini Error: {e}")
            self.bot.reply_to(message, "🤖 Maaf, sistem sedang sibuk.")

    def reply(self, message):
        """Alias agar tidak error saat dipanggil dari handler."""
        self.handle_message(message)
