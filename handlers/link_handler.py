import re
from features.downloader.youtube_downloader import YouTubeDownloader
from features.downloader.tiktok_downloader import TikTokDownloader
from features.downloader.instagram_downloader import InstagramDownloader


class LinkHandler:
    def __init__(self, bot):
        self.bot = bot
        self.yt = YouTubeDownloader(bot)
        self.tt = TikTokDownloader(bot)
        self.ig = InstagramDownloader(bot)

    def parse_url(self, text: str):
        urls = re.findall(r"https?://[^\s]+", text)
        return urls[0] if urls else None

    def detect(self, text: str):
        url = self.parse_url(text)
        if not url:
            return None, None, None

        if "youtube.com" in url or "youtu.be" in url:
            return self.yt.download, "youtube", url

        if "tiktok.com" in url:
            return self.tt.download, "tiktok", url

        if "instagram.com" in url or "instagr.am" in url:
            return self.ig.download, "instagram", url

        return None, None, url
    