import re
from urllib.parse import urlparse, parse_qs

import yt_dlp

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

from ingestion.youtube.cleaner import clean_youtube_text
from ingestion.youtube.whisper_fallback import transcribe_with_whisper
from ingestion.common.schema import build_result


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)

    if "youtu.be" in parsed.netloc:
        return parsed.path.lstrip("/")

    if "youtube.com" in parsed.netloc:
        query = parse_qs(parsed.query)

        if "v" in query:
            return query["v"][0]

        match = re.search(r"/(embed|shorts)/([A-Za-z0-9_-]{11})", parsed.path)

        if match:
            return match.group(2)

    raise ValueError(f"Could not extract video ID from URL: {url}")


def fetch_metadata(url: str) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "title": info.get("title", ""),
        "author": info.get("uploader", ""),
        "duration": info.get("duration"),
        "date": info.get("upload_date"),
    }


def fetch_transcript(video_id: str, url: str, languages=("en",)) -> str:
    """
    [Whisper fallback added] Previously, a TranscriptsDisabled or
    NoTranscriptFound error retried with an equivalent call
    (api.fetch(video_id) with no languages) — not a real fallback,
    just a second attempt at the same thing. Now it falls back to
    downloading the audio and transcribing it with Whisper, which is
    a genuinely different path that works even when captions don't
    exist at all.
    """
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=list(languages))
        return " ".join(segment.text for segment in transcript)

    except (TranscriptsDisabled, NoTranscriptFound):
        return transcribe_with_whisper(url)

    except VideoUnavailable as e:
        raise RuntimeError(f"Video unavailable: {video_id}") from e


def ingest_youtube(url: str) -> dict:
    video_id = extract_video_id(url)

    metadata = fetch_metadata(url)

    raw_text = fetch_transcript(video_id, url)

    cleaned_text = clean_youtube_text(raw_text)

    result = build_result(
        source_type="youtube",
        title=metadata["title"] or video_id,
        text=cleaned_text,
        source=url,
    )

    result["metadata"].update({
        "author": metadata["author"],
        "duration": metadata["duration"],
        "date": metadata["date"],
    })

    return result


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python transcript.py <youtube_url>")
    else:
        result = ingest_youtube(sys.argv[1])
        print(json.dumps(result, indent=2))