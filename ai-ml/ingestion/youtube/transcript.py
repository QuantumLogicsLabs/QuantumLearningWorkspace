import re
from typing import Any
from urllib.parse import urlparse, parse_qs

import yt_dlp
from yt_dlp.utils import DownloadError

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    CouldNotRetrieveTranscript,
)

from ingestion.youtube.cleaner import clean_youtube_text
from ingestion.youtube.exceptions import (
    InvalidYouTubeURLError,
    VideoUnavailableError,
    TranscriptNotAvailableError,
    TranscriptFetchError,
)
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

    raise InvalidYouTubeURLError(f"Could not extract a video ID from URL: {url}")


def fetch_metadata(url: str) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(url, download=False)
    except DownloadError as e:
        raise VideoUnavailableError(
            f"Could not load video metadata for {url}. It may be private, "
            f"deleted, region-locked, or age-restricted.",
            details={"reason": str(e)},
        ) from e

    return {
        "title": info.get("title", ""),
        "author": info.get("uploader", ""),
        "duration": info.get("duration"),
        "date": info.get("upload_date"),
    }

def fetch_transcript(video_id: str, languages=("en",)) -> dict:
    """
    Returns {"text": str, "language_code": str, "is_generated": bool}.

    Raises:
        VideoUnavailableError: video is private/deleted/unreachable.
        TranscriptNotAvailableError: video exists but has no usable transcript
            (disabled by uploader, none in any language, or empty once fetched).
        TranscriptFetchError: transient upstream failure (rate limit, IP block).
    """
    api = YouTubeTranscriptApi()

    # Step 1: find out what transcripts actually exist for this video.
    try:
        transcript_list = api.list(video_id)
    except VideoUnavailable as e:
        raise VideoUnavailableError(
            f"The video {video_id} is unavailable, private, or has been removed.",
            video_id=video_id,
        ) from e
    except TranscriptsDisabled as e:
        raise TranscriptNotAvailableError(
            f"The uploader has disabled transcripts/captions for video {video_id}.",
            video_id=video_id,
            details={"reason": "transcripts_disabled"},
        ) from e
    except CouldNotRetrieveTranscript as e:
        # Covers RequestBlocked/IpBlocked/PoTokenRequired/YouTubeRequestFailed etc.
        raise TranscriptFetchError(
            f"Could not check transcript availability for video {video_id}: {e}",
            video_id=video_id,
        ) from e

    available = [
        {
            "language": t.language,
            "language_code": t.language_code,
            "is_generated": t.is_generated,
        }
        for t in transcript_list
    ]

    if not available:
        raise TranscriptNotAvailableError(
            f"No transcript (manual or auto-generated) exists for video {video_id} "
            f"in any language.",
            video_id=video_id,
            details={"available_languages": []},
        )

    # Step 2: prefer a manually created transcript in a requested language,
    # then an auto-generated one in a requested language, then just take
    # whatever exists (manually created first) rather than failing outright.
    transcript = None
    try:
        transcript = transcript_list.find_transcript(list(languages))
    except NoTranscriptFound:
        transcript = sorted(transcript_list, key=lambda t: t.is_generated)[0]

    # Step 3: actually fetch it.
    try:
        fetched = transcript.fetch()
    except CouldNotRetrieveTranscript as e:
        raise TranscriptFetchError(
            f"Found a transcript listing for video {video_id} "
            f"(language={transcript.language_code}) but failed to fetch it: {e}",
            video_id=video_id,
            details={"available_languages": available},
        ) from e

    merged = " ".join(segment.text for segment in fetched).strip()

    if not merged:
        raise TranscriptNotAvailableError(
            f"Transcript for video {video_id} (language={transcript.language_code}) "
            f"fetched successfully but contained no text.",
            video_id=video_id,
            details={"available_languages": available},
        )

    return {
        "text": merged,
        "language_code": transcript.language_code,
        "is_generated": transcript.is_generated,
    }


def ingest_youtube(url: str) -> dict:
    video_id = extract_video_id(url)

    metadata = fetch_metadata(url)

    transcript_data = fetch_transcript(video_id)

    cleaned_text = clean_youtube_text(transcript_data["text"])

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
        "transcript_language": transcript_data["language_code"],
        "transcript_auto_generated": transcript_data["is_generated"],
    })

    return result


if __name__ == "__main__":
    import sys
    import json

    from ingestion.youtube.exceptions import YouTubeIngestError

    if len(sys.argv) < 2:
        print("Usage: python transcript.py <youtube_url>")
    else:
        try:
            result = ingest_youtube(sys.argv[1])
            print(json.dumps(result, indent=2))
        except YouTubeIngestError as e:
            print(json.dumps(e.to_dict(), indent=2))
            sys.exit(1)