from telebot import TeleBot
from dotenv import load_dotenv
import os
from main import YouTubeTranscript,create_yt_user
from telebot import types
import telebot
import re
from flask import Flask ,request
import logging

load_dotenv()
API_TOKEN =os.getenv("BOT_TOKEN")

# Configure logging
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
bot = TeleBot(API_TOKEN)

WEBHOOK_URL = os.getenv("WEBHOOK_URL")  

# Global dict to store last URL per chat_id
last_url = {}

# Webhook endpoint to handle incoming updates
@app.route('/webhook', methods=['POST'])
def webhook():
    json_data = request.get_json()
    bot.process_new_updates([telebot.types.Update.de_json(json_data)])
    return '', 200


# Homepage route
@app.route('/')
def home():
    return "Welcome to YouTube Subtitle Downloader Bot ", 200

# Set the webhook
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    if bot.set_webhook(WEBHOOK_URL):
        return "Webhook set successfully!", 200
    else:
        return "Failed to set webhook.", 400
    
#remove webhook
@app.route('/remove_webhook', methods=['GET'])
def remove_webhook():
    if bot.remove_webhook():
        return "Webhook removed successfully!", 200
    else:
        return "Failed to remove webhook.", 400


@bot.message_handler(commands=['start'])
def start(message):
    user = create_yt_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    logging.info(f"User info: {user}")
    keyboard = types.InlineKeyboardMarkup()
    about = types.InlineKeyboardButton(text="ℹ️ About", callback_data="about")
    settings = types.InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")
    donate = types.InlineKeyboardButton(text="💰 Donate", callback_data="donate")
   # source_code = types.InlineKeyboardButton(text="📦 Source Code", callback_data="source_code")
    developer_btn = types.InlineKeyboardButton(text="👨‍💻 Developer", url="https://t.me/tegegndev")
    keyboard.add(about, settings)
    keyboard.add(donate)
    #keyboard.add(source_code)
    keyboard.add(developer_btn)

    welcome_msg = (
        f"👋 Hello {message.from_user.first_name}!\n\n"
        "🎬 Send me a YouTube video URL and I'll download the subtitles for you as an SRT file.\n"
        "⬇️ Paste the link and I'll take care of the rest.\n\n"
        "— Developed by @yegna_tv"
    )

  
    bot.send_message(message.chat.id, welcome_msg, reply_markup=keyboard)


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

@bot.callback_query_handler(func=lambda call: call.data == "donate")
def callback_donate(call):
    bot.answer_callback_query(call.id)
    invoice = bot.send_invoice(
        chat_id=call.message.chat.id,
        title="Support the Bot",
        description="Donate 10 Telegram Stars to support development.",
        invoice_payload="donation",
        provider_token="",  
        currency="XTR",
        prices=[types.LabeledPrice(label="Donation", amount=1)],
        start_parameter="donate"
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout_query(pre_checkout_q):
    bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    bot.send_message(message.chat.id, "Thank you for your donation! ❤️\n Please Tell @yegna_tv your username so we can acknowledge your support!")

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
        logging.info(f"Received URL from {user_from.id} ({user_from.username}): {youtube_url}")
        
        # Construct filename
        video_info = ytdl.get_video_info()
        video_name = video_info['name']
        safe_name = "".join([c for c in video_name if c.isalpha() or c.isdigit() or c in " ._-"]).strip()
        filename = f"{safe_name}.srt"
        path = "subtitles"
        filepath = os.path.join(path, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ English subtitle downloaded successfully!")
            os.remove(filepath)  # Remove English SRT file after sending
            bot.delete_message(message.chat.id, status_msg.message_id)
            
            # Store URL for optional Amharic
            last_url[message.chat.id] = youtube_url
            
            # Send option for Amharic
            keyboard = types.InlineKeyboardMarkup()
            amharic_btn = types.InlineKeyboardButton(text="🌍 Translate to Amharic", callback_data="translate_amharic")
            keyboard.add(amharic_btn)
            bot.send_message(message.chat.id, "Would you like to translate the subtitles to Amharic?", reply_markup=keyboard)
        else:
            bot.edit_message_text("❌ Error: English file could not be saved.", chat_id=message.chat.id, message_id=status_msg.message_id)
            
    except Exception as e:
        logging.error(f"Error processing URL: {e}")
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "translate_amharic")
def callback_translate_amharic(call):
    chat_id = call.message.chat.id
    url = last_url.get(chat_id)
    if not url:
        bot.answer_callback_query(call.id, "No URL found. Please send a YouTube URL first.", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    status_msg = bot.send_message(chat_id, "⏳ Translating to Amharic version... Please wait.")
    
    try:
        ytdl = YouTubeTranscript(url, os.getenv("API_KEY"))
        ytdl.amharic_translate()
        
        # Construct filename
        video_info = ytdl.get_video_info()
        video_name = video_info['name']
        safe_name = "".join([c for c in video_name if c.isalpha() or c.isdigit() or c in " ._-"]).strip()
        amharic_filename = f"am_{safe_name}.srt"
        path = "subtitles"
        amharic_filepath = os.path.join(path, amharic_filename)
        
        if os.path.exists(amharic_filepath):
            with open(amharic_filepath, 'rb') as f:
                bot.send_document(chat_id, f, caption="✅ Amharic subtitle downloaded successfully!\n\n— Developed by @yegna_tv")
            os.remove(amharic_filepath)
            bot.delete_message(chat_id, status_msg.message_id)
        else:
            bot.edit_message_text("❌ Failed to generate Amharic subtitle.", chat_id=chat_id, message_id=status_msg.message_id)
    except Exception as e:
        logging.error(f"Error in Amharic translation: {e}")
        bot.edit_message_text(f"❌ An error occurred: {str(e)}", chat_id=chat_id, message_id=status_msg.message_id)

@bot.message_handler(regexp=r'https?://\S+')
def handle_invalid_url(message):
    bot.reply_to(message, "❌ Invalid URL. Please send a valid YouTube link.")




#bot.polling()
if __name__ == "__main__":
   print("Starting Flask server...")
   #bot.remove_webhook()
   #bot.polling()    
   app.run(port=5000,debug=True)