"""Convert lightly structured TeX fragments into reproducible text metrics.

The routines are intentionally heuristic: they preserve visible arguments of
common formatting commands while discarding citations, references, and maths.
They do not attempt to execute TeX or expand arbitrary user macros.
"""

from __future__ import annotations

import re

from .tex import find_balanced

MATH_ENVS = {"equation", "equation*", "align", "align*", "alignat", "alignat*", "gather", "gather*", "multline", "multline*", "displaymath"}
VERBATIM_ENVS = {"verbatim", "verbatim*", "lstlisting", "minted", "comment", "filecontents", "filecontents*"}


def replace_known_commands(text: str) -> str:
    """Replace TeX commands while preserving likely human-visible arguments.

    Unknown commands conservatively retain their braced arguments because many
    manuscript-specific macros simply wrap visible prose.
    """
    commands_with_last_text_arg = {
        "textit", "textbf", "emph", "textrm", "textsf", "texttt", "underline", "added",
        "deleted", "replaced", "revise", "change", "mbox", "ensuremath", "url", "href",
        "SI", "si", "qty", "num", "gls", "acrshort", "acrlong", "citeauthor",
    }
    # First, turn line breaks/nonbreaking spaces into regular spaces.
    text = text.replace("~", " ").replace("\\\\", " ")
    output: list[str] = []
    i = 0
    while i < len(text):
        if text[i] != "\\":
            output.append(text[i])
            i += 1
            continue
        match = re.match(r"\\([A-Za-z@]+|.)", text[i:])
        if not match:
            i += 1
            continue
        command = match.group(1)
        end = i + len(match.group(0))
        # Ignore optional argument(s), then capture all immediate braced groups.
        cursor = end
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        while cursor < len(text) and text[cursor] == "[":
            close = text.find("]", cursor + 1)
            if close < 0:
                break
            cursor = close + 1
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
        args: list[str] = []
        while cursor < len(text) and text[cursor] == "{":
            group = find_balanced(text, cursor)
            if not group:
                break
            value, cursor = group
            args.append(value)
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
        if command in {"begin", "end", "cite", "citep", "citet", "parencite", "textcite", "autocite", "footcite", "nocite", "ref", "eqref", "autoref", "cref", "Cref", "label", "includegraphics", "bibliography", "addbibresource"}:
            output.append(" ")
        elif command in commands_with_last_text_arg and args:
            # href{url}{label}; SI{number}{unit}; replaced{old}{new}; retain final visible-like argument.
            output.append(" " + args[-1] + " ")
        elif command in {"item", "par", "newline", "linebreak", "caption", "captionof"}:
            output.append(" ")
            if command in {"caption", "captionof"} and args:
                output.append(" " + args[-1] + " ")
        elif args:
            # Conservative fallback: keep arguments; custom formatting macros often wrap prose.
            output.append(" " + " ".join(args) + " ")
        else:
            output.append(" ")
        i = cursor if cursor > end else end
    return "".join(output)


def clean_visible_text(text: str) -> str:
    """Strip non-prose TeX syntax and normalise whitespace for measurement."""

    text = re.sub(r"(?s)\\begin\{(?:verbatim\*?|lstlisting|minted|comment|filecontents\*?)\}.*?\\end\{(?:verbatim\*?|lstlisting|minted|comment|filecontents\*?)\}", " ", text)
    # Inline and display math are not prose. Display equations are counted separately by caller.
    text = re.sub(r"(?s)\\\[.*?\\\]", " ", text)
    text = re.sub(r"(?s)\$\$.*?\$\$", " ", text)
    text = re.sub(r"(?<!\\)\$(?:\\.|[^$])*\$", " ", text)
    text = replace_known_commands(text)
    text = re.sub(r"[{}]", " ", text)
    text = re.sub(r"\\[^\s]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def count_words(text: str) -> int:
    """Count Unicode word-like tokens in visible manuscript text."""

    cleaned = clean_visible_text(text)
    # Numbers and alphabetic words count; isolated punctuation does not.
    tokens = re.findall(r"[\wÀ-ÖØ-öø-ÿ]+(?:[’'\-][\wÀ-ÖØ-öø-ÿ]+)*", cleaned, flags=re.UNICODE)
    return len(tokens)


def count_characters(text: str) -> int:
    """Count visible characters after collapsing whitespace to single spaces."""

    return len(re.sub(r"\s+", " ", clean_visible_text(text)).strip())
