"""Select the appropriate manuscript reader from a path or format override."""

from __future__ import annotations

from pathlib import Path

from .docx_reader import parse_docx
from .models import ManuscriptStats
from .parser import parse_manuscript
from .text_reader import parse_text

SUPPORTED_FORMATS = {"auto", "tex", "docx", "text"}


def detect_format(path: Path) -> str:
    """Infer a supported parser name from a manuscript filename extension.

    Raises:
        ValueError: If the extension has no supported reader.
    """

    suffix = path.suffix.lower()
    if suffix in {".tex", ".ltx"}:
        return "tex"
    if suffix == ".docx":
        return "docx"
    if suffix in {".txt", ".md"}:
        return "text"
    raise ValueError(f"Could not infer format from '{path.name}'. Use --format tex, docx, or text.")


def parse_source(path: Path, *, source_format: str = "auto", follow_inputs: bool = True) -> ManuscriptStats:
    """Parse a manuscript through the selected format-specific reader.

    Args:
        path: Manuscript file to parse.
        source_format: ``"auto"`` or one of ``"tex"``, ``"docx"``, and
            ``"text"``.
        follow_inputs: Whether the TeX reader expands common include commands.

    Returns:
        Format-independent manuscript measurements.
    """

    if source_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format '{source_format}'. Choose one of: {', '.join(sorted(SUPPORTED_FORMATS))}.")
    resolved = detect_format(path) if source_format == "auto" else source_format
    if resolved == "tex":
        return parse_manuscript(path, follow_inputs=follow_inputs)
    if resolved == "docx":
        return parse_docx(path)
    return parse_text(path)
