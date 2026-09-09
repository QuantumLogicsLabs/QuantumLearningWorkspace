class IngestionError(Exception):
    """Base class for all ingestion errors."""
    pass

class PDFProcessingError(IngestionError):
    """Raised when PDF extraction or OCR fails."""
    pass

class YouTubeTranscriptError(IngestionError):
    """Raised when YouTube transcripts are unavailable."""
    pass