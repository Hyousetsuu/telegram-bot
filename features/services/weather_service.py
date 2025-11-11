import os
import requests
from datetime import datetime, timedelta
import pytz
from collections import Counter

class WeatherService:
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.base_url_current = "http://api.openweathermap.org/data/2.5/weather"
        self.base_url_forecast = "http://api.openweathermap.org/data/2.5/forecast"

    def _get_local_time(self):
        tz = pytz.timezone("Asia/Jakarta")
        return datetime.now(tz).strftime("%A, %d %B %Y, %H:%M WIB")

    def _get_tomorrow_date(self):
        """Mendapatkan format tanggal besok (YYYY-MM-DD) untuk filter forecast."""
        tz = pytz.timezone("Asia/Jakarta")
        tomorrow = datetime.now(tz) + timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%d")

    def get_forecast_tomorrow(self, city_name):
        """Mengambil prediksi khusus untuk besok."""
        try:
            params = {"q": city_name, "appid": self.api_key, "units": "metric", "lang": "id"}
            res = requests.get(self.base_url_forecast, params=params, timeout=10)
            data = res.json()

            if data.get("cod") != "200": return None

            tomorrow_date = self._get_tomorrow_date()
            temps = []
            conditions = []

            # Filter data hanya untuk tanggal besok
            for item in data.get("list", []):
                if tomorrow_date in item["dt_txt"]:
                    temps.append(item["main"]["temp"])
                    conditions.append(item["weather"][0]["description"])

            if not temps: return None

            # Hitung rangkuman (min, max, kondisi paling sering muncul)
            temp_min = min(temps)
            temp_max = max(temps)
            most_common_condition = Counter(conditions).most_common(1)[0][0]

            return (
                f"🔮 **Prediksi Besok ({tomorrow_date})**\n"
                f"🌡 Suhu: {temp_min:.1f}°C - {temp_max:.1f}°C\n"
                f"☁️ Kondisi: {most_common_condition.title()}"
            )
        except Exception as e:
            print(f"Forecast Error: {e}")
            return None

    def get_weather(self, city="Jakarta"):
        if not self.api_key: return "⚠️ API Key cuaca belum diset."

        try:
            # 1. Ambil Cuaca SAAT INI
            params = {"q": city, "appid": self.api_key, "units": "metric", "lang": "id"}
            res = requests.get(self.base_url_current, params=params, timeout=10)
            data = res.json()

            if data.get("cod") != 200: return f"⚠️ Tidak dapat menemukan data cuaca untuk kota {city}."

            current_weather = (
                f"🌤 **Cuaca Saat Ini: {city.title()}**\n"
                f"📅 {self._get_local_time()}\n"
                f"🌡 Suhu: {data['main']['temp']}°C (Terasa: {data['main']['feels_like']}°C)\n"
                f"☁️ Kondisi: {data['weather'][0]['description'].title()}\n"
                f"💧 Kelembapan: {data['main']['humidity']}%\n"
                f"💨 Angin: {data['wind']['speed']} m/s"
            )

            # 2. Ambil Prediksi BESOK (Opsional, ditambahkan di bawahnya)
            forecast = self.get_forecast_tomorrow(city)
            if forecast:
                return f"{current_weather}\n\n{forecast}"
            
            return current_weather

        except Exception as e:
            print(f"Weather Error: {e}")
            return "⚠️ Terjadi kesalahan saat mengambil data cuaca."