"""
Whisper fallback for YouTube ingestion.

When a video has no available captions (transcripts disabled by the
uploader), this downloads the audio track and transcribes it locally
using OpenAI's Whisper model — free, runs on-device, no API key.

Requires:
    pip install openai-whisper yt-dlp
    ffmpeg installed on the system (not just pip) — Whisper and
    yt_dlp's audio extraction both depend on it. Check with:
        ffmpeg -version
    If missing: https://ffmpeg.org/download.html (or `winget install ffmpeg`
    on Windows, `brew install ffmpeg` on Mac, `apt install ffmpeg` on Linux).
"""
import os
import tempfile

import whisper
import yt_dlp

# "base" balances speed vs. accuracy for a first version. Larger models
# ("small", "medium") are more accurate but slower and require a bigger
# one-time download (up to ~1.5GB for "medium"). Worth discussing with
# the team if accuracy issues show up in practice.
DEFAULT_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

_model = None


def get_whisper_model(size: str = None):
    """
    Loads the Whisper model once and reuses it across calls — same
    singleton pattern as embedding/model.py's get_embedding_model().
    """
    global _model
    if _model is None:
        _model = whisper.load_model(size or DEFAULT_MODEL_SIZE)
    return _model


def download_audio(youtube_url: str, output_dir: str) -> str:
    """
    Downloads just the audio track (not video) to output_dir as an
    mp3, using yt_dlp. Returns the full path to the downloaded file.

    Raises RuntimeError with a clear message if the download fails
    (e.g. private/deleted/region-locked video) — this should NOT
    fail silently, per the objectives doc's note on silent-failure
    cases.
    """
    output_template = os.path.join(output_dir, "audio.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(
            f"Could not download audio for {youtube_url}: {e}"
        ) from e

    for filename in os.listdir(output_dir):
        if filename.startswith("audio"):
            return os.path.join(output_dir, filename)

    raise RuntimeError(
        f"Audio download for {youtube_url} completed but no output file was found"
    )


def transcribe_with_whisper(youtube_url: str, model_size: str = None) -> str:
    """
    Fallback transcription path: downloads audio and transcribes it
    with Whisper. Used when normal caption-based transcript fetching
    fails or returns empty text.

    Returns the transcribed text as a single string. Raises
    RuntimeError (not a silent empty return) if either the download
    or transcription step fails, so the caller can surface a clear
    error rather than silently returning nothing — per the objectives
    doc's Part A guidance on silent-failure cases.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = download_audio(youtube_url, tmpdir)

        try:
            model = get_whisper_model(model_size)
            result = model.transcribe(audio_path)
        except Exception as e:
            raise RuntimeError(
                f"Whisper transcription failed for {youtube_url}: {e}"
            ) from e

        text = result.get("text", "").strip()
        if not text:
            raise RuntimeError(
                f"Whisper produced no transcribable speech for {youtube_url} "
                "(video may have no spoken audio)"
            )

        return text
