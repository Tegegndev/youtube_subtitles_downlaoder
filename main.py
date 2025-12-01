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

dotenv.load_dotenv()

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
        # Handle youtu.be short links
        if 'youtu.be' in url:
            path = urlparse(url).path.lstrip('/')
            return path.split('?')[0]
        
        # Parse query parameters for v=
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'v' in query_params:
            return query_params['v'][0]
        
        # Handle embed URLs
        if '/embed/' in parsed_url.path:
            return parsed_url.path.split('/embed/')[1].split('?')[0]
        
        # Handle shorts URLs
        if '/shorts/' in parsed_url.path:
            return parsed_url.path.split('/shorts/')[1].split('?')[0]
        
        # Fallback: regex for 11-character ID in path
        match = re.search(r'([a-zA-Z0-9_-]{11})', url)
        if match:
            return match.group(1)
        
        raise ValueError(f"Unable to extract video ID from URL: {url}")

    def _generate_sbox_guid(self):
        ts = int(time.time() * 1000)
        rand = ''.join(random.choices(string.ascii_letters + string.digits, k=15))
        payload = f"{ts}|15|{rand}"
        return base64.b64encode(payload.encode()).decode()

    def _load_or_generate_cookies(self):
        if Path(self.COOKIE_FILE).exists():
            with open(self.COOKIE_FILE) as f:
                data = json.load(f)
            if time.time() - data.get("saved_at", 0) < self.REFRESH_INTERVAL:
                return data["cookies"]

        # Generate fresh
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

    def get_srt(self, language='en_auto', mode='default'):
        if self.response is None:
            self.fetch_transcript()
        data = self.response.json()['data']
        transcripts = data['transcripts'][language][mode]
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

    def save_to_srt(self, filename=None, path="subtitles", language='en_auto', mode='default'):
        """
        Saves the SRT content to a file.
        
        
        :param filename: Name of the file to save (e.g., 'transcript.srt')
        :param path: Directory path to save the file (default: 'subtitles')
        :param language: Language code for the transcript (default: 'en_auto')
        :param mode: Transcript mode ('default', 'custom', or 'auto')
        """
        # Create the directory if it doesn't exist
        os.makedirs(path, exist_ok=True)
        if not filename:
            filename = self.get_video_info()['name']+'.srt'
        # Get the SRT content
        srt_content = self.get_srt(language=language, mode=mode)
        
        # Full file path
        file_path = os.path.join(path, filename)
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        print(f"SRT file saved to: {file_path}")

if __name__ == "__main__":
    yt = YouTubeTranscript("https://www.youtube.com/watch?v=WOvj84xq_fc",api_key)
    print(yt.get_srt()[:500])
    print(yt.get_video_info())
    yt.save_to_srt()