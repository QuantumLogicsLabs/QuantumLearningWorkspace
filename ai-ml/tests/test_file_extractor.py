import pytest

from ingestion.common.exceptions import FileProcessingError, UnsupportedFileTypeError
from ingestion.file import extractor
from ingestion.file.extractor import extract_file_text, ingest_file


def test_extracts_text_and_markdown(tmp_path):
    text_file = tmp_path / "notes.txt"
    text_file.write_text("  Intro to learning  \n\n  Study goals  ", encoding="utf-8")
    markdown_file = tmp_path / "notes.md"
    markdown_file.write_text("# Topic\n\nA **useful** note.", encoding="utf-8")

    assert extract_file_text(str(text_file)) == "Intro to learning Study goals"
    assert extract_file_text(str(markdown_file)) == "# Topic A **useful** note."


def test_extracts_csv_rows_and_builds_common_result(tmp_path):
    csv_file = tmp_path / "scores.csv"
    csv_file.write_text("Name,Score\nAda,95\n", encoding="utf-8-sig")

    assert extract_file_text(str(csv_file)) == "Name | Score Ada | 95"
    result = ingest_file(str(csv_file), "scores.csv")
    assert result["source_type"] == "csv"
    assert result["title"] == "scores"
    assert result["text"] == "Name | Score Ada | 95"


def test_extracts_xlsx_worksheet_rows(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    path = tmp_path / "scores.xlsx"
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Results"
    worksheet.append(["Name", "Score"])
    worksheet.append(["Ada", 95])
    workbook.save(path)

    assert extract_file_text(str(path)) == "Sheet: Results Name | Score Ada | 95"


def test_extracts_docx_paragraphs_and_tables(tmp_path):
    docx = pytest.importorskip("docx")
    path = tmp_path / "lesson.docx"
    document = docx.Document()
    document.add_paragraph("Introduction")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Term"
    table.cell(0, 1).text = "Meaning"
    document.add_paragraph("Summary")
    document.save(path)

    assert extract_file_text(str(path)) == "Introduction Term | Meaning Summary"


def test_extracts_pptx_slides(tmp_path):
    pptx = pytest.importorskip("pptx")
    path = tmp_path / "lesson.pptx"
    presentation = pptx.Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide.shapes.add_textbox(0, 0, 5000000, 500000).text = "Key idea"
    presentation.save(path)

    assert extract_file_text(str(path)) == "Slide 1 Key idea"


@pytest.mark.parametrize(
    ("legacy_extension", "modern_extension", "create_document"),
    [
        (".doc", ".docx", "docx"),
        (".ppt", ".pptx", "pptx"),
    ],
)
def test_legacy_office_formats_use_converted_file(
    tmp_path, monkeypatch, legacy_extension, modern_extension, create_document
):
    if create_document == "docx":
        docx = pytest.importorskip("docx")
        document = docx.Document()
        document.add_paragraph("Legacy content")
        save_converted = document.save
    else:
        pptx = pytest.importorskip("pptx")
        presentation = pptx.Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_textbox(0, 0, 5000000, 500000).text = "Legacy content"
        save_converted = presentation.save

    legacy_file = tmp_path / f"legacy{legacy_extension}"
    legacy_file.write_bytes(b"legacy")
    converted_file = tmp_path / f"legacy{modern_extension}"
    save_converted(converted_file)
    monkeypatch.setattr(extractor, "_convert_legacy_office", lambda _: converted_file)

    assert extract_file_text(str(legacy_file)).endswith("Legacy content")


def test_unsupported_and_empty_files_fail_explicitly(tmp_path):
    unsupported = tmp_path / "notes.bin"
    unsupported.write_bytes(b"data")
    with pytest.raises(UnsupportedFileTypeError):
        extract_file_text(str(unsupported))

    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(FileProcessingError, match="No text"):
        extract_file_text(str(empty))


def test_legacy_office_error_explains_libreoffice_requirement(tmp_path, monkeypatch):
    legacy_file = tmp_path / "legacy.doc"
    legacy_file.write_bytes(b"legacy")
    monkeypatch.setattr(extractor.shutil, "which", lambda _: None)

    with pytest.raises(FileProcessingError, match="LibreOffice"):
        extract_file_text(str(legacy_file))


def test_invalid_csv_is_reported_as_file_processing_error(tmp_path):
    invalid_csv = tmp_path / "invalid.csv"
    invalid_csv.write_text('"unterminated', encoding="utf-8")
    with pytest.raises(FileProcessingError):
        extract_file_text(str(invalid_csv))
