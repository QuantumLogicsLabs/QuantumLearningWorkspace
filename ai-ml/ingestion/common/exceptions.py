class IngestionError(Exception):
    """Base class for all ingestion errors."""
    pass

class PDFProcessingError(IngestionError):
    """Raised when PDF extraction or OCR fails."""
    pass

class FileProcessingError(IngestionError):
    """Raised when an uploaded file cannot be read or converted."""
    pass

class UnsupportedFileTypeError(IngestionError):
    """Raised when an uploaded file extension is not supported."""
    pass

class YouTubeTranscriptError(IngestionError):
    """Raised when YouTube transcripts are unavailable."""
    pass