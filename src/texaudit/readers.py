from __future__ import annotations

from pathlib import Path

from .docx_reader import parse_docx
from .models import ManuscriptStats
from .parser import parse_manuscript
from .text_reader import parse_text

SUPPORTED_FORMATS = {"auto", "tex", "docx", "text"}


def detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".tex", ".ltx"}:
        return "tex"
    if suffix == ".docx":
        return "docx"
    if suffix in {".txt", ".md"}:
        return "text"
    raise ValueError(f"Could not infer format from '{path.name}'. Use --format tex, docx, or text.")


def parse_source(path: Path, *, source_format: str = "auto", follow_inputs: bool = True) -> ManuscriptStats:
    if source_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format '{source_format}'. Choose one of: {', '.join(sorted(SUPPORTED_FORMATS))}.")
    resolved = detect_format(path) if source_format == "auto" else source_format
    if resolved == "tex":
        return parse_manuscript(path, follow_inputs=follow_inputs)
    if resolved == "docx":
        return parse_docx(path)
    return parse_text(path)
