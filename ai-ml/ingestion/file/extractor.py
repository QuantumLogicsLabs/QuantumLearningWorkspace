"""Text extraction for office documents and delimited/text files."""
from __future__ import annotations

import csv
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from ingestion.common.cleaner import clean_text
from ingestion.common.exceptions import FileProcessingError, UnsupportedFileTypeError
from ingestion.common.schema import build_result

SUPPORTED_FILE_EXTENSIONS = {
    ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx", ".pptx", ".ppt",
}


def _extract_docx(path: Path) -> str:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = Document(str(path))
    blocks = []
    for element in document.element.body.iterchildren():
        if element.tag.endswith("}p"):
            text = Paragraph(element, document).text.strip()
            if text:
                blocks.append(text)
        elif element.tag.endswith("}tbl"):
            table = Table(element, document)
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    blocks.append(" | ".join(cells))
    return "\n".join(blocks)


def _extract_pptx(path: Path) -> str:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    def extract_shapes(shapes) -> list[str]:
        blocks = []
        for shape in shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                blocks.extend(extract_shapes(shape.shapes))
            elif shape.has_table:
                for row in shape.table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    if any(cells):
                        blocks.append(" | ".join(cells))
            elif shape.has_text_frame and shape.text.strip():
                blocks.append(shape.text.strip())
        return blocks

    presentation = Presentation(str(path))
    slides = []
    for index, slide in enumerate(presentation.slides, start=1):
        blocks = extract_shapes(slide.shapes)
        if blocks:
            slides.append(f"Slide {index}\n" + "\n".join(blocks))
    return "\n\n".join(slides)


def _extract_xlsx(path: Path) -> str:
    from openpyxl import load_workbook

    workbook = load_workbook(str(path), read_only=True, data_only=True)
    try:
        sheets = []
        for worksheet in workbook.worksheets:
            rows = []
            for row in worksheet.iter_rows(values_only=True):
                cells = [str(value).strip() for value in row if value is not None]
                if cells:
                    rows.append(" | ".join(cells))
            if rows:
                sheets.append(f"Sheet: {worksheet.title}\n" + "\n".join(rows))
        return "\n\n".join(sheets)
    finally:
        workbook.close()


def _extract_csv(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return "\n".join(
            " | ".join(cell.strip() for cell in row)
            for row in csv.reader(file, strict=True)
            if any(cell.strip() for cell in row)
        )


def _find_libreoffice() -> str:
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if not executable:
        raise FileProcessingError(
            "Reading legacy .doc and .ppt files requires LibreOffice "
            "(soffice) to be installed and available on PATH."
        )
    return executable


def _convert_legacy_office(path: Path) -> Path:
    executable = _find_libreoffice()
    target_extension = ".docx" if path.suffix.lower() == ".doc" else ".pptx"
    output_dir = Path(tempfile.mkdtemp(prefix="studymind-office-"))
    output_path = output_dir / f"{path.stem}{target_extension}"
    try:
        completed = subprocess.run(
            [
                executable,
                "--headless",
                "--convert-to",
                target_extension.lstrip("."),
                "--outdir",
                str(output_dir),
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise FileProcessingError(
            f"LibreOffice timed out converting {path.suffix} file."
        ) from error
    except OSError as error:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise FileProcessingError(
            f"Could not run LibreOffice to convert {path.suffix} file: {error}"
        ) from error
    if completed.returncode != 0 or not output_path.is_file():
        detail = (completed.stderr or completed.stdout).strip()
        shutil.rmtree(output_dir, ignore_errors=True)
        raise FileProcessingError(
            f"LibreOffice could not convert {path.suffix} file"
            + (f": {detail}" if detail else ".")
        )
    return output_path


def extract_file_text(file_path: str) -> str:
    """Extract cleaned text from one supported file, raising on invalid input."""
    path = Path(file_path)
    if not path.is_file():
        raise FileProcessingError(f"File not found: {file_path}")

    extension = path.suffix.lower()
    if extension not in SUPPORTED_FILE_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type {extension or '(no extension)'}. "
            f"Supported types: {', '.join(sorted(SUPPORTED_FILE_EXTENSIONS))}."
        )

    converters: dict[str, Callable[[Path], str]] = {
        ".docx": _extract_docx,
        ".txt": lambda source: source.read_text(encoding="utf-8-sig"),
        ".md": lambda source: source.read_text(encoding="utf-8-sig"),
        ".csv": _extract_csv,
        ".xlsx": _extract_xlsx,
        ".pptx": _extract_pptx,
    }

    try:
        if extension in {".doc", ".ppt"}:
            converted_path = _convert_legacy_office(path)
            try:
                text = (
                    _extract_docx(converted_path)
                    if extension == ".doc"
                    else _extract_pptx(converted_path)
                )
            finally:
                shutil.rmtree(converted_path.parent, ignore_errors=True)
        else:
            text = converters[extension](path)
    except (FileProcessingError, UnsupportedFileTypeError):
        raise
    except Exception as error:
        raise FileProcessingError(
            f"Could not extract text from {path.name}: {error}"
        ) from error

    cleaned_text = clean_text(text)
    if not cleaned_text:
        raise FileProcessingError(f"No text could be extracted from {path.name}.")
    return cleaned_text


def ingest_file(file_path: str, original_filename: str) -> dict:
    """Extract a file and return the shared ingestion result format."""
    extension = Path(original_filename).suffix.lower()
    text = extract_file_text(file_path)
    return build_result(
        source_type=extension.lstrip("."),
        title=Path(original_filename).stem,
        text=text,
        source=original_filename,
    )
