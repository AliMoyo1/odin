from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractedBlock:
    text: str
    page_number: int | None
    section_ref: str | None


def extract(file_path: Path) -> list[ExtractedBlock]:
    """Extract text blocks from a file. Returns [] for unsupported types (images)."""
    ext = file_path.suffix.lower().lstrip(".")

    if ext == "pdf":
        return _extract_pdf(file_path)
    if ext == "docx":
        return _extract_docx(file_path)
    if ext == "md":
        return _extract_markdown(file_path)
    if ext == "html":
        return _extract_html(file_path)
    if ext in {"txt", "csv", "json", "py", "js", "ts", "yaml", "yml", "xml"}:
        return _extract_raw(file_path)
    # Images and other types: not indexed
    return []


def _extract_pdf(path: Path) -> list[ExtractedBlock]:
    import pdfplumber

    blocks: list[ExtractedBlock] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                blocks.append(ExtractedBlock(
                    text=text,
                    page_number=i,
                    section_ref=None,
                ))
    return blocks


def _extract_docx(path: Path) -> list[ExtractedBlock]:
    from docx import Document

    doc = Document(str(path))
    blocks: list[ExtractedBlock] = []
    current_section: str | None = None
    current_text: list[str] = []

    def _flush() -> None:
        text = "\n".join(current_text).strip()
        if text:
            blocks.append(ExtractedBlock(
                text=text,
                page_number=None,
                section_ref=current_section,
            ))
        current_text.clear()

    for para in doc.paragraphs:
        if para.style.name.startswith("Heading"):
            _flush()
            current_section = para.text.strip() or current_section
        else:
            if para.text.strip():
                current_text.append(para.text)

    _flush()
    return blocks


def _extract_markdown(path: Path) -> list[ExtractedBlock]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    blocks: list[ExtractedBlock] = []
    current_section: str | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        body = "\n".join(current_lines).strip()
        if body:
            blocks.append(ExtractedBlock(
                text=body,
                page_number=None,
                section_ref=current_section,
            ))
        current_lines.clear()

    for line in lines:
        if line.startswith("#"):
            _flush()
            current_section = line.lstrip("#").strip()
        else:
            current_lines.append(line)

    _flush()
    return blocks


def _extract_html(path: Path) -> list[ExtractedBlock]:
    from bs4 import BeautifulSoup

    raw = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n").strip()
    if not text:
        return []
    return [ExtractedBlock(text=text, page_number=None, section_ref=None)]


def _extract_raw(path: Path) -> list[ExtractedBlock]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return []
    return [ExtractedBlock(text=text, page_number=None, section_ref=None)]
