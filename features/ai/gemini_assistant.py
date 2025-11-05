import os
import re
import google.generativeai as genai

class GeminiAssistant:

    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("models/gemini-2.5-flash")

    def _remove_formatting(self, text: str):
        # hapus semua tanda tebal/miring
        text = re.sub(r"[*_`~]", "", text)
        return text

    def reply(self, message):
        try:
            res = self.model.generate_content(message.text)
            clean_text = self._remove_formatting(res.text)
            self.bot.reply_to(message, clean_text, parse_mode="Markdown")
        except Exception as e:
            self.bot.reply_to(message, f"🤖 AI Error: {e}")
