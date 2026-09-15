# Adding journal profiles

Journal rules live in YAML so that limits can be reviewed and updated without changing the audit code. This document covers both personal profiles and profiles contributed to `texaudit`.

## Use a personal profile

Create a YAML file anywhere on your computer and pass its path with `--profile`:

```bash
texaudit manuscript.tex --profile "/path/to/my-journal.yaml"
```

A personal profile is loaded directly and is not installed or copied. Keep it with the manuscript or another backed-up project folder.

Personal profiles must be self-contained. The `extends` mechanism described below resolves bundled profile names only when loading a built-in profile; it is not currently resolved for a file passed with `--profile`.

If no compliance rules are needed, the bundled `generic` profile already provides a manuscript breakdown:

```bash
texaudit manuscript.tex --journal generic
```

It deliberately carries a metrics-only coverage warning and should not be used as the parent of a journal profile.

## Complete example

Only add checks supported by the journal's published instructions. Omit unknown limits rather than guessing.

```yaml
journal:
  publisher: Example Publisher
  name: "Example Journal — Research Article"
  profile_version: "2026-09-15"
  source: "Example Journal guide for authors"
  source_url: "https://example.org/guide-for-authors"

sections:
  abstract:
    required: true
    max_words: 250
  plain_language_summary:
    required: false
    max_words: 200
  key_points:
    required: true
    min_items: 1
    max_items: 3
    max_characters_per_item: 140
  highlights:
    required: false
    min_items: 3
    max_items: 5
    max_characters_per_item: 85

limits:
  max_figures: 8
  max_tables: 5
  figures:
    max_items: 8
    exceed_status: WARNING
    qualifier: "The journal describes this as a recommendation."
  title:
    max_words: 20
    max_characters: 120
    exceed_status: WARNING
    qualifier: "The journal describes this as a recommendation."
  main_text:
    max_words: 5000
    exclude_methods: false
    exceed_status: FAIL
  methods:
    max_words: 2000
  display_items:
    max_items: 10
  references:
    max_items: 50
    exceed_status: WARNING
    qualifier: "The journal describes this as a guideline."

publication_units:
  enabled: false
  words_per_unit: 500
  warning_threshold: 25
  max_units: null

coverage:
  status: WARNING
  message: "Partial automated profile: confirm requirements not checked here."

presence_checks:
  data_availability:
    label: "Data Availability statement"
    required: true
    aliases:
      - "data availability"
      - "data availability statement"
      - "data and code availability"
```

## Supported fields

### Journal metadata

| Field | Meaning |
| --- | --- |
| `journal.name` | Human-readable name printed in the report |
| `journal.publisher` | Publisher name; metadata only |
| `journal.profile_version` | Date or version on which the rules were verified |
| `journal.source` | Title of the author guidance used |
| `journal.source_url` | Direct link to that guidance |

`journal.name` is the only metadata field that changes ordinary report output, but the source fields are strongly recommended. Use an article-type-specific name when a journal has different rules for Articles, Letters, Reviews, or other formats.

### Section checks

| Section | Supported fields |
| --- | --- |
| `abstract` | `required`, `max_words` |
| `plain_language_summary` | `required`, `max_words` |
| `key_points` | `required`, `min_items`, `max_items`, `max_characters_per_item` |
| `highlights` | `required`, `min_items`, `max_items`, `max_characters_per_item` |

Use YAML booleans `true` and `false`, not quoted strings. A configured required abstract or plain language summary fails when it is not detected. Optional highlights that are absent are reported as information because Elsevier commonly asks for them as a separate upload.

### Numerical limits

The `limits` mapping supports:

- `max_figures` and `max_tables` for hard limits (or `null` when none is configured)
- `figures.max_items` and `tables.max_items` when a count needs `exceed_status` or a `qualifier`; these take precedence over the corresponding simple field
- `title.max_words` and `title.max_characters`
- `main_text.max_words`; set `exclude_methods: true` when the journal excludes Methods from this allowance
- `methods.max_words`
- `display_items.max_items`, applied to figures plus tables
- `references.max_items`

Nested limits can set `exceed_status: WARNING` when published guidance is advisory. The default status is `FAIL`. A short `qualifier` is appended to the report message. Set a known unlimited value to `null`, or omit a rule that should not be checked.

### AGU publication units

Set `publication_units.enabled: true` to calculate publication units as counted words divided by `words_per_unit`, plus the detected figures and tables. Use either:

- `max_units` for a hard limit, which produces `FAIL` when exceeded; or
- `warning_threshold` for a fee or advisory threshold, which produces `WARNING` when exceeded.

The counted-word components follow the AGU-specific calculation implemented by `ManuscriptStats.agu_word_count`. Do not enable this section for a publisher that uses a different formula merely because it also calls its measure a publication unit.

### Required-section presence

Each entry under `presence_checks` can have:

- `label`: the name printed in the report
- `required`: whether absence is a failure (`true`) or information (`false`)
- `aliases`: lower-case section or environment names that the parser may detect

Aliases are matched to detected section/environment names. They are not arbitrary searches of every sentence, so prefer actual heading variants used by the journal template.

### Profile coverage notice

Use an optional top-level `coverage` mapping when the available automated rules cover only part of a journal's submission requirements. `coverage.status` should normally be `WARNING`, and `coverage.message` should identify the important requirements that still need manual review. This prevents a small collection of passing automated checks from presenting itself as a comprehensive pass.

Every bundled public profile must resolve to a `coverage` notice with `status: WARNING`. A shared publisher profile may supply it through inheritance. This keeps an otherwise clean numerical audit from being mistaken for complete submission readiness. Personal profiles may omit it, but omission does not imply that every editorial or submission-system requirement is machine-checkable.

When a published limit combines content the parser does not fully measure (for example, author names, affiliations, and body text in one character allowance), do not apply that limit to a partial measurement. Name the composite rule in the coverage warning until the data model and all relevant readers can calculate it faithfully.

## Add a built-in profile

Built-in profiles live in this directory and use lower-case, hyphenated filenames, for example `example-journal-research-article.yaml`. The filename without `.yaml` becomes the value accepted by `--journal`.

Shared publisher rules may live in a filename beginning with `_`. Such files are hidden from `--list-journals`. A built-in profile can inherit one of them:

```yaml
extends: _example-publisher
journal:
  name: "Example Journal — Research Article"
sections:
  abstract:
    max_words: 200
```

Mappings are merged recursively, so the child above changes only the abstract limit. Lists and scalar values replace the parent's value. Keep inherited rules conservative: a publisher-wide rule belongs in a shared profile only when it truly applies to every child journal and article type using it.

Then:

1. Add the YAML file under `src/texaudit/profiles/`.
2. Confirm it appears in `texaudit --list-journals` (underscore-prefixed shared profiles should not appear).
3. Audit a small representative manuscript with `--journal your-profile-name`.
4. Add tests for profile discovery, inherited values, and every unusual limit or status.
5. Add or retain a `WARNING` coverage notice that names material manual checks.
6. Run `pytest -q`.
7. Build a wheel and check that the YAML file is packaged; `pyproject.toml` includes `profiles/*.yaml` as package data.

## Research and review checklist

Before contributing a rule:

- Prefer the journal's current official author instructions or template over third-party summaries.
- Record the direct source URL and the date checked in `profile_version`.
- Confirm the article type. Do not combine limits for Articles, Letters, Reviews, and Brief Communications.
- Distinguish mandatory limits from recommendations, fee thresholds, and submission-system guidance.
- Check what the journal includes in its word count: abstract, Methods, captions, tables, references, appendices, and equations may be treated differently.
- Check whether highlights, key points, summaries, or graphical abstracts belong in the manuscript or are separate uploads.
- Avoid inventing a numerical rule where the instructions give none.
- Compare the profile against the publisher's actual LaTeX or Word template, because section names and document structure affect detection.
- Keep the profile narrow enough that its command-line name unambiguously identifies both journal and article type.

Profiles make requirements auditable, but they cannot make the parser understand a manuscript feature it does not yet recognise. If a new journal relies on a structurally different section, template command, or Word style, add parser fixtures and support before claiming that check works.
