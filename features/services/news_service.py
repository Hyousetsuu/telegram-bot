from gnews import GNews
from datetime import datetime
import pytz

class NewsService:
    def __init__(self):
        self.base_gnews = GNews(language='id', country='ID')

    def _get_local_time(self):
        tz = pytz.timezone("Asia/Jakarta")
        return datetime.now(tz).strftime("%A, %d %B %Y, %H:%M WIB")

    def get_news(self, topic="indonesia", count=5):
        try:
            final_news = []
            seen_titles = set()

            # Fungsi helper untuk mencari dan menggabungkan berita
            def fetch_and_add(period_code):
                if len(final_news) >= count: return

                # Set periode waktu pencarian (1d = 24jam, 7d = seminggu, etc)
                self.base_gnews.period = period_code
                self.base_gnews.max_results = count

                if topic.lower() == "indonesia":
                    new_articles = self.base_gnews.get_top_news()
                else:
                    new_articles = self.base_gnews.get_news(topic)

                for article in new_articles:
                    # Cek duplikasi berdasarkan judul agar tidak ada berita kembar
                    if article['title'] not in seen_titles and len(final_news) < count:
                        final_news.append(article)
                        seen_titles.add(article['title'])

            # --- STRATEGI MUNDUR WAKTU ---
            # 1. Cari berita HARI INI ('1d')
            fetch_and_add('1d')

            # 2. Jika masih kurang dari permintaan, cari 7 HARI TERAKHIR ('7d')
            if len(final_news) < count:
                print(f"[DEBUG] Kurang! Mundur 7 hari untuk topik: {topic}")
                fetch_and_add('7d')

            # 3. Jika MASIH kurang, cari 1 BULAN TERAKHIR ('1m')
            if len(final_news) < count:
                 print(f"[DEBUG] Masih kurang! Mundur 30 hari untuk topik: {topic}")
                 fetch_and_add('1m')

            # --- FORMAT HASIL ---
            if not final_news:
                return f"⚠️ Tidak ditemukan berita tentang '{topic}' dalam 30 hari terakhir."

            news_list = []
            for i, article in enumerate(final_news[:count], 1):
                title = article.get('title').split(" - ")[0]
                source = article.get('publisher', {}).get('title', 'Google News')
                url = article.get('url')
                # Tambahkan sedikit info waktu publish jika tersedia
                published = article.get('published date', '')[5:16] # Ambil tanggal-bulannya saja
                
                news_list.append(f"{i}. [{title}]({url})\n   └ 📰 _{source}_ ({published})")

            return f"📰 **Berita Google: {topic.title()}**\n📅 {self._get_local_time()}\n\n" + "\n".join(news_list)

        except Exception as e:
            print(f"GNews Error: {e}")
            return "⚠️ Terjadi kesalahan saat mengambil berita dari Google."