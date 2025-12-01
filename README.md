
---

# YouTube Transcript Tool

This tool extracts YouTube video IDs from different URL formats, retrieves subtitle data, converts it into SRT format, and saves the output locally. It also manages lightweight cookie generation and keeps timestamps properly formatted.

---

## Features

* Extracts video IDs from:

  * `watch?v=...`
  * `youtu.be/...`
  * `/embed/...`
  * `/shorts/...`
  * Regex fallback
* Auto-generated cookies with timed refresh
* Builds valid `.srt` subtitles
* Auto filenames based on video title
* Helper methods for:

  * Raw response
  * Video info
  * Subtitle languages
  * SRT output

---

## Project Structure

```
your_project/
│── main.py
│── cookies.json
│── .env
│── subtitles/
```

---

## Requirements

* Python 3.8+
* requests
* python-dotenv

Install:

```bash
pip install requests python-dotenv
```

---

## Usage

```python
from main import YouTubeTranscript
import os

api_key = os.getenv("API_KEY")

yt = YouTubeTranscript(
    "https://www.youtube.com/watch?v=WOvj84xq_fc",
    api_key
)

print(yt.get_srt()[:300])
yt.save_to_srt()
```

---

## Environment Variables

Create a `.env` file:

```
API_KEY=your_key
BASE_URL=your_url
```

---

## How It Works

1. Extracts video ID from the provided URL.
2. Loads or generates cookies.
3. Retrieves subtitle data.
4. Converts segments into SRT format.
5. Saves the SRT file to `/subtitles/`.

---

## Saving SRT Files

```
yt.save_to_srt(
    filename="video.srt",
    path="subtitles",
    language="en_auto",
    mode="default"
)
```

If no filename is given, the video title is used.

---

## Common Issues

| Issue           | Cause                              |
| --------------- | ---------------------------------- |
| Missing fields  | The response lacked expected keys  |
| Wrong filenames | Special characters in video titles |
| Empty subtitles | No subtitle segments available     |

---

## Running the Script

```bash
python3 main.py
```

---
