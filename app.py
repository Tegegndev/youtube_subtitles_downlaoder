from telebot import TeleBot
from dotenv import load_dotenv
import os
from main import YouTubeTranscript
from telebot import types


load_dotenv()
API_TOKEN =os.getenv("BOT_TOKEN")


bot = TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.InlineKeyboardMarkup()
    about = types.InlineKeyboardButton(text="ℹ️ About", callback_data="about")
    settings = types.InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")
    developer_btn = types.InlineKeyboardButton(text="👨‍💻 Developer", url="https://t.me/tegegndev")
    keyboard.add(about, settings)
    keyboard.add(developer_btn)

    welcome_msg = (
        f"👋 Hello {message.from_user.first_name}!\n\n"
        "🎬 Send me a YouTube video URL and I'll download the subtitles for you as an SRT file.\n"
        "⬇️ Paste the link and I'll take care of the rest.\n\n"
        "✨ Tip: You can use /start anytime to see this message again.\n\n"
        "— Developed by @yegna_tv"
    )

    bot.send_message(message.from_user.id, welcome_msg, reply_markup=keyboard)
    bot.register_next_step_handler(message, handle_url)

# Function to handle the YouTube URL
def handle_url(message):
    youtube_url = message.text
    ytdl = YouTubeTranscript(youtube_url, os.getenv("API_KEY"))
    srt_text = ytdl.get_srt()
    ytdl.save_to_srt()
    user_from = message.from_user
    print(f"Received URL from {user_from.id} ({user_from.username}): {youtube_url}")
    # Here you would add the logic to download subtitles using the YouTubeTranscript class
    # For demonstration, we will just echo back the URL
    filename = ytdl.get_video_info()['name']+'.srt'
    path = "subtitles"
    filepath = os.path.join(path, filename)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(filepath, 'rb') as f:
        bot.send_document(message.from_user.id, f)
    bot.send_message(message.from_user.id, "Subtitle downloaded successfully!")


bot.polling()