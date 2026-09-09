import os
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from ingestion.pdf.cleaner import clean_pdf_text
from ingestion.common.schema import build_result
from ingestion.common.exceptions import PDFProcessingError

def extract_pdf_text(file_path: str) -> str:
    """
    Advanced extraction using IBM's Docling. 
    Handles OCR, tables, and layout automatically.
    """
    if not os.path.exists(file_path):
        raise PDFProcessingError(f"File not found: {file_path}")

    try:
        # Initialize the converter
        converter = DocumentConverter()
        
        # Convert the PDF (Docling automatically detects if it needs OCR)
        result = converter.convert(file_path)
        
        # Export to Markdown (best for RAG) or Plain Text
        # .export_to_markdown() is highly recommended for LLMs
        extracted_text = result.document.export_to_markdown()
        
        if not extracted_text.strip():
            raise PDFProcessingError("Extraction resulted in empty text.")
            
        return extracted_text

    except Exception as e:
        raise PDFProcessingError(f"Docling failed to process PDF: {str(e)}")

def ingest_pdf(file_path: str, original_filename: str) -> dict:
    """Standard pipeline logic."""
    raw_text = extract_pdf_text(file_path)
    cleaned_text = clean_pdf_text(raw_text)
    title = os.path.splitext(original_filename)[0]

    return build_result(
        source_type="pdf",
        title=title,
        text=cleaned_text,
        source=file_path,
    )