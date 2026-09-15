"""Command-line interface for configuring, running, and rendering an audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .api import TexAudit
from .profiles import builtin_profile_names
from .render import render_terminal


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(description="Audit TeX, DOCX, or plain-text manuscripts against a journal profile.")
    parser.add_argument("source_file", nargs="?", help="Manuscript file (.tex, .docx, .txt, or .md).")
    parser.add_argument("--journal", help="Built-in journal profile name.")
    parser.add_argument("--profile", help="Path to a custom YAML journal profile.")
    parser.add_argument("--format", choices=["auto", "tex", "docx", "text"], default="auto", help="Input format (default: infer from file extension).")
    parser.add_argument("--no-follow-inputs", dest="follow_inputs", action="store_false", help="Do not expand \\input, \\include, or \\subfile files.")
    parser.set_defaults(follow_inputs=True)
    parser.add_argument("--json", action="store_true", help="Emit JSON rather than a terminal report.")
    parser.add_argument("--output", help="Write the report to this file as well as stdout.")
    parser.add_argument("--list-journals", action="store_true", help="List built-in journal profiles and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command-line program and return a process exit status.

    Exit status ``0`` means there were no failing checks, ``1`` means the audit
    completed with at least one failure, and ``2`` means the request could not
    be processed.
    """

    args = build_parser().parse_args(argv)
    if args.list_journals:
        print("\n".join(builtin_profile_names()))
        return 0
    if not args.source_file:
        print("error: SOURCE_FILE is required unless --list-journals is used.", file=sys.stderr)
        return 2
    try:
        auditor = TexAudit(
            journal=args.journal,
            profile_path=args.profile,
            source_format=args.format,
            follow_inputs=args.follow_inputs,
        )
        report = auditor.audit(Path(args.source_file))
    except (OSError, ValueError, yaml_error()) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report.to_dict(), indent=2) if args.json else render_terminal(report)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 1 if report.overall_status == "FAIL" else 0


def yaml_error():
    """Return PyYAML's parse-error type, with a safe import fallback."""

    try:
        import yaml
        return yaml.YAMLError
    except ImportError:  # pragma: no cover
        return Exception


if __name__ == "__main__":
    raise SystemExit(main())
