from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter


def _load_reader(pdf_path: Path) -> PdfReader:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    return PdfReader(str(pdf_path))


def extract_text_pdf(pdf_path: Path, *, max_pages: int | None = None) -> str:
    reader = _load_reader(pdf_path)
    if reader.is_encrypted:
        raise RuntimeError("PDF is encrypted and cannot be processed without unlocking it first")

    pages = reader.pages[:max_pages] if max_pages else reader.pages
    texts: list[str] = []
    for page in pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            texts.append("")
    return "\n\n".join(texts)


def probe_pdf_file(pdf_path: Path, *, max_pages_to_scan: int = 5) -> dict:
    reader = _load_reader(pdf_path)
    file_size = pdf_path.stat().st_size
    encrypted = reader.is_encrypted

    text_out = ""
    if not encrypted:
        text_out = extract_text_pdf(pdf_path, max_pages=max_pages_to_scan)

    text_content = text_out.strip()
    text_chars = len(text_content)
    lines_with_text = [line for line in text_content.splitlines() if line.strip()]
    has_text_layer = text_chars >= 120 or len(lines_with_text) >= 6
    has_chinese = any("\u4e00" <= ch <= "\u9fff" for ch in text_out)
    language = "ch" if has_chinese else "en"

    return {
        "path": str(pdf_path.absolute()),
        "pages": len(reader.pages),
        "size_mb": round(file_size / 1024 / 1024, 2),
        "has_text_layer": has_text_layer,
        "language": language,
        "encrypted": encrypted,
        "needs_ocr": not has_text_layer and not encrypted,
    }


def write_text_layer_markdown(pdf_path: Path, output_path: Path) -> Path:
    reader = _load_reader(pdf_path)
    if reader.is_encrypted:
        raise RuntimeError("PDF is encrypted and cannot be processed without unlocking it first")

    page_texts: list[str] = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            text = ""
        if text:
            page_texts.append(text)
        else:
            page_texts.append(f"[第{idx}页内容为空]")
    text = "\n\n===PAGE_BREAK===\n\n".join(page_texts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def split_pdf_pages(
    pdf_path: Path,
    *,
    max_pages: int,
    parts_dir: Path,
) -> list[Path]:
    reader = _load_reader(pdf_path)
    total = len(reader.pages)
    if total <= max_pages:
        return [pdf_path]

    parts_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    for start in range(0, total, max_pages):
        end = min(start + max_pages, total)
        writer = PdfWriter()
        for page_idx in range(start, end):
            writer.add_page(reader.pages[page_idx])
        out = parts_dir / f"{pdf_path.stem}_p{start + 1}-{end}.pdf"
        with out.open("wb") as handle:
            writer.write(handle)
        parts.append(out)
    return parts
