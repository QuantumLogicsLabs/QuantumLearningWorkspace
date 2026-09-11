"""Structured errors for the YouTube ingestion pipeline.

Every error carries a machine-readable `code`, an HTTP `status_code` the
API layer should return, and a human-readable `message`. This lets the
FastAPI layer turn these into clean JSON instead of a raw 500 traceback.
"""


class YouTubeIngestError(Exception):
    """Base class for all YouTube ingestion errors."""

    code = "youtube_ingest_error"
    status_code = 500

    def __init__(
        self,
        message: str,
        video_id: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.video_id = video_id
        self.details = details or {}

    def to_dict(self) -> dict:
        payload: dict[str, object] = {
            "error": self.code,
            "message": self.message,
        }

        if self.video_id:
            payload["video_id"] = self.video_id

        if self.details:
            payload["details"] = self.details

        return payload

class InvalidYouTubeURLError(YouTubeIngestError):
    """The URL is not a recognizable YouTube video URL."""

    code = "invalid_url"
    status_code = 400


class VideoUnavailableError(YouTubeIngestError):
    """The video is private, deleted, region-locked, or otherwise unreachable."""

    code = "video_unavailable"
    status_code = 404


class TranscriptNotAvailableError(YouTubeIngestError):
    """The video exists but no usable transcript could be produced.

    This covers: transcripts disabled by the uploader, no transcript in any
    language, a transcript that fetched but came back empty, and transcript
    fetch failures after a listing succeeded.
    """

    code = "transcript_not_available"
    status_code = 422


class TranscriptFetchError(YouTubeIngestError):
    """Transient/upstream failure (rate limiting, IP block, network, etc.)."""

    code = "transcript_fetch_failed"
    status_code = 502