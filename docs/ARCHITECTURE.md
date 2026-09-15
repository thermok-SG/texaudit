# Architecture

This document describes how `texaudit` is organised, where to make changes, and which boundaries are intentional.

## Data flow

An audit has four stages:

```text
manuscript path
    │
    ▼
format reader ──────► ManuscriptStats
                          │
journal YAML ─────────────┤
                          ▼
                     rule evaluation
                          │
                          ▼
                     AuditReport
                          │
                   ┌──────┴──────┐
                   ▼             ▼
              terminal text     JSON
```

The readers convert different source formats into the same `ManuscriptStats` model. Rule evaluation therefore does not need to know whether a value came from TeX, DOCX, or plain text. Rendering similarly consumes an `AuditReport` without reparsing the manuscript.

## Public interface

`texaudit.TexAudit` is the primary library interface. It owns the selected profile and input options, and its `audit()` method runs the pipeline for one manuscript. Keeping this small stateful layer as a class makes repeated audits straightforward while leaving text transformations as testable pure functions.

The command-line interface creates a `TexAudit` instance, renders its report, and translates the overall status into a process exit code. Existing lower-level functions remain public for specialised uses and backwards compatibility.

## Module responsibilities

| Module | Responsibility |
| --- | --- |
| `api.py` | Public `TexAudit` orchestration class |
| `cli.py` | Argument parsing, output selection, and process exit codes |
| `readers.py` | Input-format detection and reader dispatch |
| `parser.py` | LaTeX manuscript structure, same-stem `.bbl` discovery, and component extraction |
| `tex.py` | Low-level TeX loading, balanced groups, environments, and spans |
| `docx_reader.py` | Word styles, paragraphs, tables, drawings, fields, and equations |
| `text_reader.py` | Best-effort plain-text and Markdown section parsing |
| `counting.py` | Visible-text cleanup plus word and character metrics |
| `profiles.py` | YAML profile discovery, loading, and built-in inheritance |
| `audit.py` | Journal-rule evaluation independent of input format |
| `models.py` | Shared statistics, check, and report data models |
| `render.py` | Human-readable terminal report formatting |

The YAML files under `src/texaudit/profiles/` contain policy data rather than parser logic. See [Adding journal profiles](../src/texaudit/profiles/ADDING_PROFILES.md) before changing them.

## Why only the orchestration layer is a class

A class is useful when data and operations have a meaningful shared lifecycle. `TexAudit` has one: select a profile and parser configuration, then audit one or more manuscripts with it. `ManuscriptStats`, `CheckResult`, and `AuditReport` are data classes because they carry structured state.

Most parsing helpers do not benefit from mutable object state. Functions such as `count_words()`, `strip_comments()`, and `load_profile()` map explicit inputs to explicit outputs. Keeping them as functions makes dependencies visible, prevents state leaking between manuscripts, and makes focused tests easier. File-format parser classes may become worthwhile later if they acquire interchangeable configuration or plugin behaviour, but adding them now would mostly wrap stateless functions.

## Extension guidelines

- Add a new input format by writing a reader that returns `ManuscriptStats`, then register it in `readers.py`.
- Add a new measurable component to `ManuscriptStats`, populate it in each reader that can detect it, and expose it in JSON or terminal output as appropriate.
- Add a profile rule in `audit.py` only after defining and documenting its YAML representation.
- Keep publisher policy in YAML. Keep document-structure recognition in readers.
- Emit a parser warning when a format cannot reliably measure something; do not silently imply that an undetectable value is zero.
- Add a minimal fixture for every new template construct or parsing edge case.

## Known boundaries

`texaudit` does not execute TeX, render Word documents, or contact journal submission systems. TeX macro expansion and complex Word layout therefore remain heuristic. Profile results describe what the parser detected under documented rules, not a guarantee about what a publisher's production system will count.
