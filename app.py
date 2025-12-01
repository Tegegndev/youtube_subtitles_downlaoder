from telebot import TeleBot
from dotenv import load_dotenv
import os
from main import YouTubeTranscript
from telebot import types
import re

load_dotenv()
API_TOKEN =os.getenv("BOT_TOKEN")


bot = TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.InlineKeyboardMarkup()
    about = types.InlineKeyboardButton(text="ℹ️ About", callback_data="about")
    settings = types.InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")
    source_code = types.InlineKeyboardButton(text="📦 Source Code", callback_data="source_code")
    developer_btn = types.InlineKeyboardButton(text="👨‍💻 Developer", url="https://t.me/tegegndev")
    keyboard.add(about, settings)
    keyboard.add(source_code)
    keyboard.add(developer_btn)

    welcome_msg = (
        f"👋 Hello {message.from_user.first_name}!\n\n"
        "🎬 Send me a YouTube video URL and I'll download the subtitles for you as an SRT file.\n"
        "⬇️ Paste the link and I'll take care of the rest.\n\n"
        "✨ Tip: You can use /start anytime to see this message again.\n\n"
        "— Developed by @yegna_tv"
    )

    # Fixed typo: message.from_usewevhookr.id -> message.chat.id
    bot.send_message(message.chat.id, welcome_msg, reply_markup=keyboard)
    # Removed register_next_step_handler to allow regex handling

@bot.callback_query_handler(func=lambda call: call.data == "about")
def callback_about(call):
    about_text = (
        "ℹ️ *About YouTube Subtitle Bot*\n\n"
        "This bot helps you extract and download subtitles from YouTube videos easily.\n\n"
        "👨‍💻 *Developer:* [Tegegn](https://t.me/tegegndev)\n"
        "🐍 *Language:* Python\n"
        "📚 *Framework:* pyTelegramBotAPI\n\n"
        "Made with ❤️ by @yegna_tv"
    )
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, about_text, parse_mode='Markdown', disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data == "source_code")
def callback_source_code(call):
    bot.answer_callback_query(call.id, "Coming soon! 🚧", show_alert=True)

# Regex to match YouTube URLs
YOUTUBE_REGEX = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'

# Function to handle the YouTube URL
@bot.message_handler(regexp=YOUTUBE_REGEX)
def handle_url(message):
    try:
        status_msg = bot.reply_to(message, "⏳ Processing video... Please wait.")
        youtube_url = message.text
        
        ytdl = YouTubeTranscript(youtube_url, os.getenv("API_KEY"))
        
        # Check if we can get subtitles
        srt_text = ytdl.get_srt()
        
        # Handle error messages returned from main.py
        if srt_text.startswith("Error") or srt_text.startswith("No subtitles"):
            bot.edit_message_text(f"❌ {srt_text}", chat_id=message.chat.id, message_id=status_msg.message_id)
            return

        ytdl.save_to_srt()
        
        user_from = message.from_user
        print(f"Received URL from {user_from.id} ({user_from.username}): {youtube_url}")
        
        # Construct filename
        video_info = ytdl.get_video_info()
        filename = video_info['name'] + '.srt'
        path = "subtitles"
        filepath = os.path.join(path, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ Subtitle downloaded successfully!")
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("❌ Error: File could not be saved.", chat_id=message.chat.id, message_id=status_msg.message_id)
            
    except Exception as e:
        print(f"Error processing URL: {e}")
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")

@bot.message_handler(regexp=r'https?://\S+')
def handle_invalid_url(message):
    bot.reply_to(message, "❌ Invalid URL. Please send a valid YouTube link.")


bot.polling()