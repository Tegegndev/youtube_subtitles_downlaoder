import requests
import json
import os
import time
import base64
import random
import string
import uuid
from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs
import dotenv
import logging
from googletrans import Translator

dotenv.load_dotenv()

# Configure logging
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SUPABASE_EDGE_URL = os.getenv("SUPABASE_EDGE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Keep this secret

def create_yt_user(telegram_id, username=None, first_name=None, last_name=None):
    payload = {
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name
    }

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(SUPABASE_EDGE_URL, json=payload, headers=headers, timeout=15)
        if response.status_code in (200, 201):
            logging.info("User created or updated successfully.")
            logging.info(response.json())
            return response.json()
        else:
            logging.error(f"Failed to create/update user: {response.text} (Status: {response.status_code})")
            return {"error": response.text, "status_code": response.status_code}
    except requests.RequestException as e:
        logging.error(f"Request exception in create_yt_user: {str(e)}")
        return {"error": str(e)}

api_key = os.getenv("API_KEY")

class YouTubeTranscript:
    COOKIE_FILE = "cookies.json"
    REFRESH_INTERVAL = 3600  # 1 hour
    BASE_URL = os.getenv('BASE_URL')

    def __init__(self, video_url, api_key):
        self.video_url = video_url
        self.video_id = self._extract_video_id(video_url)
        self.api_key = api_key
        self.base_url =  f"{self.BASE_URL}/api/v2/video-transcript"
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'api-key': f'Bearer {self.api_key}',
            'referer': f'https:/{self.BASE_URL}/detail/{self.video_id}?type=1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
        }
        self.cookies = self._load_or_generate_cookies()
        self.response = None

    def _extract_video_id(self, url):
        """
        Extract video ID from various YouTube URL formats.
        Supports: watch?v=, embed/, shorts/, youtu.be/
        """
        # Comprehensive regex for YouTube Video IDs
        pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        
        raise ValueError(f"Unable to extract video ID from URL: {url}")

    def _generate_sbox_guid(self):
        ts = int(time.time() * 1000)
        rand = ''.join(random.choices(string.ascii_letters + string.digits, k=15))
        payload = f"{ts}|15|{rand}"
        return base64.b64encode(payload.encode()).decode()

    def _load_or_generate_cookies(self):
        # Always generate fresh cookies on run, do not load from file
        new_cookies = {
            'sbox-guid': self._generate_sbox_guid(),
            'anonymous_user_id': str(uuid.uuid4())
        }
        save_data = {"cookies": new_cookies, "saved_at": time.time()}
        with open(self.COOKIE_FILE, "w") as f:
            json.dump(save_data, f)
        return new_cookies

    def fetch_transcript(self):
        params = {'platform': 'youtube', 'video_id': self.video_id}
        self.response = requests.get(self.base_url, headers=self.headers, cookies=self.cookies, params=params)
        return self.response.json()

    def get_raw_response(self):
        if self.response is None:
            self.fetch_transcript()
        return self.response.json()

    def _get_transcript_data(self, language='en', mode='default'):
        if self.response is None:
            self.fetch_transcript()
            
        resp_json = self.response.json()
        if not resp_json or 'data' not in resp_json:
             return None

        data = resp_json['data']
        if 'transcripts' not in data:
             return None

        transcripts_map = data['transcripts']
        
        # Handle missing language key (KeyError fix)
        if language not in transcripts_map:
            # Prefer 'en', then 'en_auto', then first available
            if 'en' in transcripts_map:
                language = 'en'
            elif 'en_auto' in transcripts_map:
                language = 'en_auto'
            else:
                available_languages = list(transcripts_map.keys())
                if available_languages:
                    language = available_languages[0]
                    logging.warning(f"Requested language not found. Falling back to '{language}'")
                else:
                    return None

        # Handle missing mode key
        if mode not in transcripts_map[language]:
            available_modes = list(transcripts_map[language].keys())
            if available_modes:
                mode = available_modes[0]
            else:
                return None

        return transcripts_map[language][mode]

    def get_srt(self, language='en', mode='default'):
        transcripts = self._get_transcript_data(language, mode)
        
        if not transcripts:
             return "Error: Could not retrieve transcript data."

        srt_lines = []
        for i, segment in enumerate(transcripts, start=1):
            start_time = self._format_time(segment['start'])
            end_time = self._format_time(segment['end'])
            text = segment['text']
            srt_lines.append(f"{i}\n{start_time} --> {end_time}\n{text}\n")
        return "\n".join(srt_lines)

    def _format_time(self, time_str):
        # Convert HH:MM:SS to HH:MM:SS,mmm
        h, m, s = time_str.split(':')
        return f"{h}:{m}:{s},000"

    def get_video_id(self):
        if self.response is None:
            self.fetch_transcript()
        return self.response.json()['data']['videoId']

    def get_video_info(self):
        if self.response is None:
            self.fetch_transcript()
        return self.response.json()['data']['videoInfo']

    def get_language_codes(self):
        if self.response is None:
            self.fetch_transcript()
        return self.response.json()['data']['language_code']

    def save_to_srt(self, filename=None, path="subtitles", language='en', mode='default'):
        """
        Saves the SRT content to a file.
        
        
        :param filename: Name of the file to save (e.g., 'transcript.srt')
        :param path: Directory path to save the file (default: 'subtitles')
        :param language: Language code for the transcript (default: 'en')
        :param mode: Transcript mode ('default', 'custom', or 'auto')
        """
        # Create the directory if it doesn't exist
        os.makedirs(path, exist_ok=True)
        if not filename:
            video_name = self.get_video_info()['name']
            safe_name = "".join([c for c in video_name if c.isalpha() or c.isdigit() or c in " ._-"]).strip()
            filename = safe_name + '.srt'
        # Get the SRT content
        srt_content = self.get_srt(language=language, mode=mode)
        
        # Full file path
        file_path = os.path.join(path, filename)
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        logging.info(f"SRT file saved to: {file_path}")
    
    def amharic_translate(self):
        t = Translator()
        
        transcripts = self._get_transcript_data()
        if not transcripts:
            logging.warning("No transcripts available for translation.")
            return

        # Limit to first 1 segment for testing
        if len(transcripts) > 1:
            transcripts = transcripts[:1]
            logging.info("Limiting translation to first 1 segment for testing.")

        # Sanitize filename
        video_name = self.get_video_info().get('name', 'video')
        safe_name = "".join([c for c in video_name if c.isalpha() or c.isdigit() or c in " ._-"]).strip()
        filename = f"am_{safe_name}.srt"
        full_path = os.path.join('subtitles', filename)
        os.makedirs('subtitles', exist_ok=True)
        
        logging.info(f"Starting Amharic translation for {len(transcripts)} segments.")
        
        def translate_text(text):
            print(f"Translating: {text[:50]}...")
            try:
                print("Before translate call")
                result = t.translate(text, dest='am').text
                print("After translate call")
                logging.info(f"Translated segment: '{text[:50]}...' to Amharic.")
                return result
            except Exception as e:
                print(f"Translation failed: {str(e)}")
                logging.warning(f"Translation failed for segment '{text[:50]}...': {str(e)}. Using original text.")
                return text

        # Perform translation sequentially without threading
        texts = [s['text'] for s in transcripts]
        translated_texts = []
        for text in texts:
            translated_texts.append(translate_text(text))

        logging.info("Translation completed. Generating SRT file.")
        srt_lines = []
        for i, (segment, translated_text) in enumerate(zip(transcripts, translated_texts), start=1):
            start_time = self._format_time(segment['start'])
            end_time = self._format_time(segment['end'])
            srt_lines.append(f"{i}\n{start_time} --> {end_time}\n{translated_text}\n")
            
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(srt_lines))
        logging.info(f"Amharic translation saved to {full_path}")

if __name__ == "__main__":
    yt = YouTubeTranscript("https://www.youtube.com/watch?v=WOvj84xq_fc",api_key)
    srt = yt.get_srt()
    print(srt[:500])
    if srt.startswith("Error"):
        print("Failed to retrieve transcript data. Skipping further processing.")
        
    else:
        print(yt.get_video_info())
        yt.save_to_srt()
        yt.amharic_translate()
        # Print Amharic version
        video_name = yt.get_video_info()['name']
        safe_name = "".join([c for c in video_name if c.isalpha() or c.isdigit() or c in " ._-"]).strip()
        amharic_path = os.path.join('subtitles', f"am_{safe_name}.srt")
        if os.path.exists(amharic_path):
            with open(amharic_path, 'r', encoding='utf-8') as f:
                print(f.read()[:500])
        else:
            print("Amharic SRT file not found.")