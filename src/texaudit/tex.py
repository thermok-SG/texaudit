from __future__ import annotations

import re
from pathlib import Path

INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")
BEGIN_END_RE = re.compile(r"\\(begin|end)\s*\{([^}]+)\}")
SECTION_RE = re.compile(r"\\(?:section|subsection|subsubsection|paragraph)\*?\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")


def strip_comments(text: str) -> str:
    """Remove TeX comments while preserving escaped percent signs."""
    lines: list[str] = []
    for line in text.splitlines():
        out: list[str] = []
        backslashes = 0
        for char in line:
            if char == "\\":
                backslashes += 1
                out.append(char)
                continue
            if char == "%" and backslashes % 2 == 0:
                break
            out.append(char)
            backslashes = 0
        lines.append("".join(out))
    return "\n".join(lines)


def _resolve_include(base: Path, target: str) -> Path | None:
    candidate = (base / target).expanduser()
    candidates = [candidate]
    if candidate.suffix == "":
        candidates.append(candidate.with_suffix(".tex"))
    for path in candidates:
        if path.exists() and path.is_file():
            return path.resolve()
    return None


def load_tex(path: Path, *, follow_inputs: bool = True, _seen: set[Path] | None = None) -> tuple[str, list[str], list[str]]:
    """Load a TeX source, recursively expanding common include directives."""
    path = path.expanduser().resolve()
    seen = _seen if _seen is not None else set()
    if path in seen:
        return "", [], [f"Skipped recursive include: {path}"]
    seen.add(path)
    if not path.exists():
        raise FileNotFoundError(f"TeX file not found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    text = strip_comments(text)
    files = [str(path)]
    warnings: list[str] = []

    if not follow_inputs:
        return text, files, warnings

    def replace(match: re.Match[str]) -> str:
        target = match.group(1).strip()
        included = _resolve_include(path.parent, target)
        if included is None:
            warnings.append(f"Could not resolve included TeX file '{target}' referenced by {path.name}.")
            return ""
        nested_text, nested_files, nested_warnings = load_tex(included, follow_inputs=True, _seen=seen)
        files.extend(nested_files)
        warnings.extend(nested_warnings)
        return "\n" + nested_text + "\n"

    return INPUT_RE.sub(replace, text), files, warnings


def find_balanced(text: str, start: int, opener: str = "{", closer: str = "}") -> tuple[str, int] | None:
    """Return content/end index for a balanced brace group beginning at start."""
    if start >= len(text) or text[start] != opener:
        return None
    depth = 0
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start + 1:index], index + 1
    return None


def extract_environment_blocks(text: str, env_name: str) -> list[tuple[int, int, str]]:
    """Extract non-nested blocks for a named environment, supporting same-name nesting."""
    token_re = re.compile(r"\\(begin|end)\s*\{" + re.escape(env_name) + r"\}")
    blocks: list[tuple[int, int, str]] = []
    depth = 0
    start: int | None = None
    for match in token_re.finditer(text):
        kind = match.group(1)
        if kind == "begin":
            if depth == 0:
                start = match.start()
                content_start = match.end()
            depth += 1
        elif depth:
            depth -= 1
            if depth == 0 and start is not None:
                blocks.append((start, match.end(), text[content_start:match.start()]))
                start = None
    return blocks


def remove_spans(text: str, spans: list[tuple[int, int]]) -> str:
    # Merge overlaps before editing so a nested span (for example, AGU's 2025
    # plainlanguagesummary inside abstract) cannot invalidate outer offsets.
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    for start, end in reversed(merged):
        text = text[:start] + " " + text[end:]
    return text


def command_arguments(text: str, command: str) -> list[str]:
    """Extract first braced argument for a command, allowing one optional argument."""
    pattern = re.compile(r"\\" + re.escape(command) + r"\*?\s*(?:\[[^\]]*\])?\s*")
    results: list[str] = []
    for match in pattern.finditer(text):
        group = find_balanced(text, match.end())
        if group:
            value, _ = group
            results.append(value)
    return results


def command_argument_blocks(text: str, command: str, count: int) -> list[tuple[int, int, list[str]]]:
    """Extract the span and consecutive braced arguments of each command."""
    pattern = re.compile(r"\\" + re.escape(command) + r"\*?\s*")
    results: list[tuple[int, int, list[str]]] = []
    for match in pattern.finditer(text):
        cursor = match.end()
        arguments: list[str] = []
        for _ in range(count):
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
            group = find_balanced(text, cursor)
            if not group:
                break
            value, cursor = group
            arguments.append(value)
        if arguments:
            results.append((match.start(), cursor, arguments))
    return results
