import telebot
from telebot import types
from pytubefix import YouTube
import requests
import os
from dotenv import load_dotenv  # <--- tambahan

# Load file .env
load_dotenv()

# Ambil token dari environment variable
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("⚠️ BOT_TOKEN tidak ditemukan! Pastikan file .env berisi token kamu.")

bot = telebot.TeleBot(TOKEN)

# ---------------- MENU ----------------
@bot.message_handler(commands=['menu', 'start'])
def menu(message):
    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("🎥 YouTube Video", callback_data="youtube")
    btn2 = types.InlineKeyboardButton("🎧 YouTube MP3", callback_data="youtube-mp3")
    btn3 = types.InlineKeyboardButton("🎬 TikTok Video", callback_data="tiktok")
    btn4 = types.InlineKeyboardButton("🎵 TikTok MP3", callback_data="tiktokmp3")
    btn5 = types.InlineKeyboardButton("📸 Instagram Video", callback_data="ig")
    btn6 = types.InlineKeyboardButton("🎶 Instagram MP3", callback_data="igmp3")
    btn7 = types.InlineKeyboardButton("ℹ Info", callback_data="info")

    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)
    markup.add(btn7)

    # Ambil data user
    user = message.from_user or {}
    first_name = getattr(user, "first_name", "") or ""
    last_name = getattr(user, "last_name", "") or ""
    username = getattr(user, "username", None)
    user_id = getattr(user, "id", None)

    if username:
        display = f"@{username}"
    else:
        display = (first_name + (" " + last_name if last_name else "")).strip() or "Teman"

    # Mention yang bisa diklik
    if user_id:
        mention = f'<a href="tg://user?id={user_id}">{display}</a>'
    else:
        mention = display

    welcome_text = (
        f"🤖 <b>Selamat datang di FENDLI BOT!</b>\n\n"
        f"Halo, {mention}! 👋\n"
        "Aku siap bantu kamu ambil video atau musik favoritmu dari berbagai platform 🎶\n\n"
        "Pilih fitur yang kamu mau di bawah ini ⬇️"
    )

    # Kirim gambar + pesan sambutan
    try:
        photo_path = "Logo.png"  # ubah ke nama file gambar kamu
        with open(photo_path, "rb") as photo:
            bot.send_photo(
                message.chat.id,
                photo,
                caption=welcome_text,
                parse_mode="HTML",
                reply_markup=markup
            )
    except Exception as e:
        print(f"⚠️ Gagal kirim foto: {e}")
        bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_response(call):
    cmd = {
        "youtube": "/youtube link_video",
        "youtube-mp3": "/mp3 link_video",
        "tiktok": "/tiktok link_video",
        "tiktokmp3": "/tiktokmp3 link_video",
        "ig": "/ig link_instagram",
        "igmp3": "/igmp3 link_instagram"
    }
    if call.data in cmd:
        bot.send_message(call.message.chat.id, f"Gunakan:\n`{cmd[call.data]}`", parse_mode="Markdown")
    else:
        bot.send_message(call.message.chat.id,
                         "🤖 Bot ini mendukung:\n• YouTube (Video & MP3)\n• TikTok (Video & MP3)\n• Instagram (Video & MP3)")


# ---------------- YOUTUBE VIDEO ----------------
@bot.message_handler(commands=['youtube'])
def youtube_download(message):
    try:
        url = message.text.split(" ")[1]
        bot.send_message(message.chat.id, "⏳ Sedang memproses video YouTube...")

        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by("resolution").last()

        video_path = stream.download(filename="youtube_video.mp4")
        size = os.path.getsize(video_path)

        if size > 50 * 1024 * 1024:
            bot.send_document(message.chat.id, open(video_path, "rb"))
        else:
            bot.send_video(message.chat.id, open(video_path, "rb"))

        os.remove(video_path)

    except Exception as e:
        bot.send_message(message.chat.id,
                         f"⚠ Gagal download video YouTube.\nError: {e}\n\nGunakan: /youtube link_video")


# ---------------- YOUTUBE → MP3 ----------------
@bot.message_handler(commands=['mp3'])
def youtube_to_mp3(message):
    try:
        url = message.text.split(" ")[1]
        bot.send_message(message.chat.id, "🎧 Mengambil audio YouTube...")

        yt = YouTube(url)
        stream = yt.streams.filter(only_audio=True).first()
        audio_path = stream.download(filename="audio.mp3")

        bot.send_audio(message.chat.id, open(audio_path, "rb"))
        os.remove(audio_path)

    except Exception as e:
        bot.send_message(message.chat.id,
                         f"⚠ Gagal mengambil audio.\nError: {e}\n\nGunakan: /mp3 link_video")


# ---------------- TIKTOK (NO WATERMARK) ----------------
@bot.message_handler(commands=['tiktok'])
def tiktok_download(message):
    try:
        url = message.text.split(" ")[1]
        bot.send_message(message.chat.id, "🎬 Sedang mengambil video TikTok...")

        api_url = "https://www.tikwm.com/api/"
        params = {"url": url}
        resp = requests.get(api_url, params=params, timeout=10).json()

        if resp.get("data") and resp["data"].get("play"):
            video_url = resp["data"]["play"]
        else:
            raise Exception("Gagal mendapatkan link video tanpa watermark.")

        filename = "tiktok_video.mp4"
        with open(filename, "wb") as f:
            f.write(requests.get(video_url, timeout=20).content)

        bot.send_video(message.chat.id, open(filename, "rb"))
        os.remove(filename)

    except Exception as e:
        bot.send_message(message.chat.id,
                         f"⚠ Tidak bisa download TikTok.\nError: {e}\n\nGunakan: /tiktok link_video")


# ---------------- TIKTOK → MP3 ----------------
@bot.message_handler(commands=['tiktokmp3', 'ttmp3'])
def tiktok_to_mp3(message):
    try:
        url = message.text.split(" ")[1]
        bot.send_message(message.chat.id, "🎵 Mengambil audio dari video TikTok...")

        api_url = "https://www.tikwm.com/api/"
        params = {"url": url}
        resp = requests.get(api_url, params=params, timeout=10).json()

        if resp.get("data") and resp["data"].get("music"):
            audio_url = resp["data"]["music"]
        else:
            raise Exception("Gagal mendapatkan link audio dari TikTok.")

        filename = "tiktok_audio.mp3"
        with open(filename, "wb") as f:
            f.write(requests.get(audio_url, timeout=20).content)

        bot.send_audio(message.chat.id, open(filename, "rb"))
        os.remove(filename)

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⚠ Tidak bisa mengambil audio TikTok.\nError: {e}\n\nGunakan: /tiktokmp3 link_video"
        )


# ---------------- INSTAGRAM VIDEO ----------------
@bot.message_handler(commands=['ig'])
def instagram_download(message):
    try:
        url = message.text.split(" ")[1]
        bot.send_message(message.chat.id, "📸 Sedang mengambil video Instagram...")

        api_url = "https://snapinsta.app/api/ajaxSearch"
        data = {"q": url, "t": "media"}
        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://snapinsta.app/"
        }

        resp = requests.post(api_url, data=data, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise Exception(f"Server error ({resp.status_code})")

        html = resp.text

        # Cari link video mp4 di response
        import re
        match = re.search(r'href="(https://[^"]+\.mp4)"', html)
        if not match:
            raise Exception("Tidak dapat menemukan link video yang valid.")

        video_url = match.group(1)
        filename = "instagram_video.mp4"

        with open(filename, "wb") as f:
            f.write(requests.get(video_url, timeout=20).content)

        bot.send_video(message.chat.id, open(filename, "rb"))
        os.remove(filename)

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⚠ Tidak bisa download video Instagram.\nError: {e}\n\nGunakan: /ig link_instagram"
        )


# ---------------- INSTAGRAM → MP3 ----------------
@bot.message_handler(commands=['igmp3'])
def instagram_to_mp3(message):
    try:
        url = message.text.split(" ")[1]
        bot.send_message(message.chat.id, "🎶 Mengambil audio dari video Instagram...")

        api_url = "https://snapinsta.app/api/ajaxSearch"
        data = {"q": url, "t": "media"}
        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://snapinsta.app/"
        }

        resp = requests.post(api_url, data=data, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise Exception(f"Server error ({resp.status_code})")

        html = resp.text

        # Ekstrak link video
        import re
        match = re.search(r'href="(https://[^"]+\.mp4)"', html)
        if not match:
            raise Exception("Tidak dapat menemukan link video di response.")

        video_url = match.group(1)
        video_file = "temp_instagram.mp4"
        audio_file = "instagram_audio.mp3"

        # Download video
        with open(video_file, "wb") as f:
            f.write(requests.get(video_url, timeout=20).content)

        # Konversi ke MP3
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(video_file)
            audio.export(audio_file, format="mp3")
            bot.send_audio(message.chat.id, open(audio_file, "rb"))
        except Exception:
            bot.send_message(message.chat.id, "⚠ Tidak bisa konversi ke MP3. Pastikan `pydub` dan `ffmpeg` terpasang.")

        # Bersihkan file
        if os.path.exists(video_file):
            os.remove(video_file)
        if os.path.exists(audio_file):
            os.remove(audio_file)

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⚠ Tidak bisa ambil audio dari Instagram.\nError: {e}\n\nGunakan: /igmp3 link_instagram"
        )



# ---------------- START BOT ----------------
if __name__ == "__main__":
    print("✅ Bot berjalan...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
