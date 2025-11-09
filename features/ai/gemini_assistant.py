import os
import re
import requests
import google.generativeai as genai
from datetime import datetime
import pytz


class GeminiAssistant:
    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("models/gemini-2.5-flash")

        # ambil API key dari .env
        self.weather_key = os.getenv("OPENWEATHER_API_KEY")
        self.news_key = os.getenv("NEWS_API_KEY")

    def _remove_formatting(self, text: str):
        return re.sub(r"[*_`~]", "", text)

    def _get_local_time(self):
        tz = pytz.timezone("Asia/Jakarta")
        now = datetime.now(tz)
        return now.strftime("%A, %d %B %Y, %H:%M WIB")

    def _get_weather(self, city="Jakarta"):
        try:
            url = (
                f"http://api.openweathermap.org/data/2.5/weather?q={city}"
                f"&appid={self.weather_key}&units=metric&lang=id"
            )
            r = requests.get(url, timeout=10)
            data = r.json()

            if data.get("cod") != 200:
                return "Tidak dapat mengambil data cuaca saat ini."

            weather = data["weather"][0]["description"].capitalize()
            temp = data["main"]["temp"]
            hum = data["main"]["humidity"]
            wind = data["wind"]["speed"]

            return (
                f"🌤 Cuaca {city.title()} ({self._get_local_time()}):\n"
                f"- Kondisi: {weather}\n"
                f"- Suhu: {temp}°C\n"
                f"- Kelembapan: {hum}%\n"
                f"- Angin: {wind} m/s"
            )
        except Exception as e:
            print("Weather error:", e)
            return "Tidak dapat mengambil data cuaca saat ini."

    def _get_news(self, country="id", count=3, topic=None):
        try:
            if topic:
                url = (
                    f"https://newsapi.org/v2/everything?q={topic}&language=id"
                    f"&apiKey={self.news_key}&pageSize={count}"
                )
            else:
                # default pakai keyword Indonesia supaya selalu ada
                url = (
                    f"https://newsapi.org/v2/everything?q=indonesia&language=id"
                    f"&apiKey={self.news_key}&pageSize={count}"
                )

            r = requests.get(url, timeout=10)
            data = r.json()

            if data.get("status") != "ok":
                return "Tidak dapat mengambil berita terkini saat ini."

            articles = data.get("articles", [])[:count]
            if not articles:
                return "Tidak ada berita terkini saat ini."

            hasil = [
                f"{i+1}. {a['title']} ({a['source']['name']})"
                for i, a in enumerate(articles)
            ]
            judul = f"📰 Berita {topic.title()} terkini" if topic else "📰 Berita terkini"
            return f"{judul} ({self._get_local_time()}):\n" + "\n".join(hasil)
        except Exception as e:
            print("News error:", e)
            return "Tidak dapat mengambil berita terkini saat ini."

    def _get_full_report(self, city="Surakarta", topic="indonesia"):
        """Gabungkan waktu, berita, dan cuaca"""
        now = self._get_local_time()
        news = self._get_news(count=3, topic=topic)
        weather = self._get_weather(city)
        return f"🕓 Sekarang adalah {now}\n\n{news}\n\n{weather}"

    def reply(self, message):
        text = message.text.lower()

        # 🔹 kombinasi otomatis (sinkron semua)
        if any(kata in text for kata in ["hari ini", "tanggal", "hari apa", "berita hari ini"]):
            return self.bot.reply_to(message, self._get_full_report())

        # 🌤 + 📰 kombinasi manual
        if "cuaca" in text and "berita" in text:
            city_match = re.search(r"cuaca di ([a-zA-Z\s]+)", text)
            city = city_match.group(1).strip() if city_match else "Jakarta"

            topic_match = re.search(r"berita tentang ([a-zA-Z\s]+)", text)
            topic = topic_match.group(1).strip() if topic_match else "indonesia"

            res = self._get_full_report(city=city, topic=topic)
            return self.bot.reply_to(message, res)

        # 🌤 cuaca saja
        elif "cuaca" in text:
            city_match = re.search(r"cuaca di ([a-zA-Z\s]+)", text)
            city = city_match.group(1).strip() if city_match else "Jakarta"
            return self.bot.reply_to(message, self._get_weather(city))

        # 📰 berita saja
        elif "berita" in text:
            topic_match = re.search(r"berita tentang ([a-zA-Z\s]+)", text)
            topic = topic_match.group(1).strip() if topic_match else "indonesia"
            return self.bot.reply_to(message, self._get_news(count=3, topic=topic))

        # 🕓 waktu saja
        elif any(kata in text for kata in ["jam berapa", "waktu sekarang"]):
            return self.bot.reply_to(message, f"🕓 Sekarang adalah {self._get_local_time()}.")

        # 🤖 default ke AI
        try:
            res = self.model.generate_content(message.text)
            clean_text = self._remove_formatting(res.text)
            self.bot.reply_to(message, clean_text, parse_mode="Markdown")
        except Exception as e:
            self.bot.reply_to(message, f"🤖 AI Error: {e}")
