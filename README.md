# texaudit

A small, transparent CLI for auditing TeX, DOCX, and plain-text manuscripts against journal requirements.

## Install (editable)

```bash
python -m pip install -e .
```

## Run

```bash
texaudit manuscript.tex --journal agu-jgr-earth-surface
texaudit manuscript.docx --journal agu-jgr-earth-surface
texaudit manuscript.txt --format text --journal agu-jgr-earth-surface
texaudit manuscript.docx --journal agu-jgr-earth-surface --json
texaudit manuscript.tex --profile path/to/custom-journal.yaml --follow-inputs
```

## Current MVP scope

- Supports `.tex`, `.docx`, `.txt`, and `.md` inputs, with automatic format detection.
- Expands `\input{}`, `\include{}`, and `\subfile{}` recursively for TeX inputs.
- Reads Word paragraph styles, headings, tables, captions, embedded drawings, and Office Math equations where available.
- Removes comments safely, including escaped percent signs.
- Counts text after stripping common LaTeX commands while preserving visible text.
- Reports separate totals for abstract, PLS, key points, captions, table captions, body text, acknowledgements, appendices, equations, references, figures, tables, subfigures, citations, and unresolved `??` markers.
- Applies journal checks from YAML profiles.
- Emits terminal and JSON reports.

## Intentional limitations

This is a manuscript-oriented parser, not a full TeX engine or Word rendering engine. It will not expand arbitrary user-defined TeX macros or perfectly interpret all Word citation-manager fields, floating objects, tracked changes, or linked figures. Plain-text mode is deliberately labelled as an estimate. Its report always shows component totals and warnings so its interpretation is auditable.
