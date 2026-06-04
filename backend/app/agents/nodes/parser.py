"""
Saransh — Parser Agent Node

Deterministic agent: extracts text from uploaded files.
Supports PDF, DOCX, TXT, CSV, XLSX, JSON.
No LLM calls — pure document parsing.
"""

import io
import json
import logging
import re

logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".json"}


def _parse_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text.strip())
    doc.close()
    return "\n\n".join(pages)


def _parse_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _parse_txt(file_bytes: bytes) -> str:
    """Decode plain text file."""
    # Try UTF-8 first, then fallback to latin-1
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def _parse_csv(file_bytes: bytes) -> str:
    """Parse CSV into a readable string representation."""
    import pandas as pd

    df = pd.read_csv(io.BytesIO(file_bytes))
    # Limit to first 500 rows to avoid massive text
    if len(df) > 500:
        df = df.head(500)
    return f"CSV Data ({len(df)} rows, {len(df.columns)} columns):\n\nColumns: {', '.join(df.columns.tolist())}\n\n{df.to_string(index=False)}"


def _parse_xlsx(file_bytes: bytes) -> str:
    """Parse Excel into a readable string representation."""
    import pandas as pd

    df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    if len(df) > 500:
        df = df.head(500)
    return f"Excel Data ({len(df)} rows, {len(df.columns)} columns):\n\nColumns: {', '.join(df.columns.tolist())}\n\n{df.to_string(index=False)}"


def _parse_json(file_bytes: bytes) -> str:
    """Parse JSON into a formatted string."""
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")

    data = json.loads(text)
    formatted = json.dumps(data, indent=2, ensure_ascii=False)

    # Truncate if too large
    if len(formatted) > 50000:
        formatted = formatted[:50000] + "\n\n... [truncated]"

    return f"JSON Data:\n\n{formatted}"


def _get_extension(filename: str) -> str:
    """Extract lowercase file extension."""
    parts = filename.rsplit(".", 1)
    if len(parts) < 2:
        return ""
    return f".{parts[-1].lower()}"


def _clean_text(text: str) -> str:
    """Basic text cleaning: normalize whitespace, remove control characters."""
    # Remove control characters (except newlines and tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Normalize multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Normalize multiple spaces
    text = re.sub(r' {3,}', ' ', text)
    return text.strip()


def parser_node(state: dict) -> dict:
    """
    Parser Agent: Extracts and cleans text from the uploaded file.

    Reads: file_bytes, filename
    Writes: raw_text, file_type, word_count, error
    """
    filename = state.get("filename", "unknown")
    file_bytes = state.get("file_bytes", b"")

    logger.info(f"Parser Agent: Processing '{filename}' ({len(file_bytes)} bytes)")

    ext = _get_extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        return {
            "error": f"Unsupported file type: '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            "raw_text": "",
            "file_type": ext,
            "word_count": 0,
        }

    if not file_bytes:
        return {
            "error": "File is empty",
            "raw_text": "",
            "file_type": ext,
            "word_count": 0,
        }

    parsers = {
        ".pdf": _parse_pdf,
        ".docx": _parse_docx,
        ".txt": _parse_txt,
        ".csv": _parse_csv,
        ".xlsx": _parse_xlsx,
        ".json": _parse_json,
    }

    try:
        parser_fn = parsers[ext]
        raw_text = parser_fn(file_bytes)
        raw_text = _clean_text(raw_text)

        if not raw_text.strip():
            return {
                "error": "No text could be extracted from the file. The file may be empty or contain only images.",
                "raw_text": "",
                "file_type": ext,
                "word_count": 0,
            }

        word_count = len(raw_text.split())
        logger.info(f"Parser Agent: Extracted {word_count} words from {ext} file")

        return {
            "raw_text": raw_text,
            "file_type": ext,
            "word_count": word_count,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Parser Agent: Failed to parse '{filename}': {e}")
        return {
            "error": f"Failed to parse file: {str(e)}",
            "raw_text": "",
            "file_type": ext,
            "word_count": 0,
        }
