from telebot import TeleBot
from dotenv import load_dotenv
import os
from main import YouTubeTranscript


load_dotenv()
API_TOKEN =os.getenv("BOT_TOKEN")


bot = TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.from_user.id,"hey I am youtube subtitle downloader bot  send me youtube link to get subtitle")
    #next step handler
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