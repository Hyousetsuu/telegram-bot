import telebot
import os
from dotenv import load_dotenv
from handlers.message_handler import register_handlers

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN tidak ditemukan dalam .env!")

bot = telebot.TeleBot(TOKEN)
apihelper.SESSION_RETRY = True
apihelper.RETRIES = 5
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")

register_handlers(bot)  # ✅ Register handler auto-link

if __name__ == "__main__":
    print("🤖 Bot Running...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)