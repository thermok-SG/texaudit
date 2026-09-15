# texaudit

`texaudit` is a small, transparent command-line tool for checking LaTeX, Word, and plain-text manuscripts against journal requirements. It reports word counts, figures, tables, references, section presence, and journal-specific limits without uploading the manuscript anywhere.

> [!IMPORTANT]
> `texaudit` began as a LaTeX-first tool. Word (`.docx`) support is useful but best-effort and may be less accurate, especially for text boxes, linked or floating figures, tracked changes, citation-manager fields, and documents with heavily customised styles. Always review the report and the journal's current author instructions before submitting.

## What you need

- A Windows, macOS, or Linux computer
- Python 3.10 or newer
- The manuscript as `.tex`, `.docx`, `.txt`, or `.md`

You do **not** need Git, Anaconda, mamba, or programming experience. `texaudit` is not yet on PyPI and does not currently have a standalone installer, so the steps below install it from the source folder.

## Install without Git

### 1. Download texaudit

1. Open the [texaudit GitHub page](https://github.com/thermok-SG/texaudit).
2. Select **Code**, then **Download ZIP**.
3. Extract the downloaded ZIP file to a folder you can find again.

### 2. Install Python

Download Python from [python.org](https://www.python.org/downloads/) if Python 3.10 or newer is not already installed.

- On Windows, enable **Add python.exe to PATH** if the installer offers that option.
- On macOS, use the current universal installer from python.org.
- On Linux, Python is often already installed; otherwise use the software manager supplied with the distribution.

### 3. Open a terminal in the extracted folder

On Windows, open the extracted `texaudit` folder in File Explorer, click the address bar, type `powershell`, and press Enter.

On macOS, open Terminal, type `cd ` with a trailing space, drag the extracted folder onto the Terminal window, and press Return. The same `cd` approach works in most Linux terminals.

### 4. Install

On Windows, run:

```powershell
py -m pip install .
```

On macOS or Linux, run:

```bash
python3 -m pip install .
```

The installation also installs the small libraries needed to read YAML profiles and Word files.

### 5. Check the installation

Windows:

```powershell
py -m texaudit.cli --list-journals
```

macOS or Linux:

```bash
python3 -m texaudit.cli --list-journals
```

You should see a list of built-in journal names. Installation also normally creates a shorter `texaudit` command, but the commands above work even when that shortcut is not on the system path.

## Audit a manuscript

Choose a journal name from `--list-journals`, then provide the manuscript path and journal. Put quotation marks around any path containing spaces.

Windows example:

```powershell
py -m texaudit.cli "C:\Users\YourName\Documents\my manuscript.docx" --journal agu-jgr-earth-surface
```

macOS or Linux example:

```bash
python3 -m texaudit.cli "/Users/YourName/Documents/my manuscript.tex" --journal agu-jgr-earth-surface
```

If the shorter command works on your computer, the same audit is:

```bash
texaudit "my manuscript.tex" --journal agu-jgr-earth-surface
```

The input format is inferred from the file extension. Common examples are:

```bash
texaudit manuscript.tex --journal agu-grl
texaudit manuscript.docx --journal agu-tectonics
texaudit manuscript.txt --journal agu-jgr-earth-surface
```

The tool reads the manuscript locally. It does not send manuscript content to a website or external service.

## Understanding the report

The report shows the detected manuscript components followed by journal checks:

- `PASS` means the detected value satisfies the configured rule.
- `WARNING` means the result needs human review or exceeds a recommendation rather than a hard limit.
- `FAIL` means the detected manuscript violates a configured requirement.
- `INFO` gives useful context where no pass/fail rule applies.

For AGU profiles, publication units are calculated as counted words divided by 500, plus one unit for each figure and table. The displayed counted-word total includes the abstract, body, acknowledgements, appendices, captions, and one word per equation, following AGU's stated formula.

A clean report is a useful pre-submission check, not a guarantee that a journal will accept the file. Requirements and templates change, and automated parsing is necessarily approximate.

## Word documents: preparation and caveats

The DOCX reader was checked against the structure of AGU's Word manuscript template. It reads ordinary paragraphs and styles, headings, tables, captions, embedded drawings, and Office Math equations where those features are represented normally in the file.

Because the project started with LaTeX, Word support has more edge cases. Before auditing a `.docx` file:

1. Work on a copy of the manuscript.
2. Remove unused template instructions and example text.
3. Accept or reject tracked changes if the version being counted should not include them.
4. Use the template's normal headings and caption styles where possible.
5. Compare the reported figure, table, equation, and reference counts with the document yourself.

Text in text boxes or unusual floating objects may be missed. Linked images may not count like embedded images. Citation-manager fields, custom styles, deleted tracked text, and complex layouts can also produce unexpected results. These limitations are why parser messages are shown as warnings rather than hidden.

Old binary Word files (`.doc`) are not supported; save them as `.docx` first.

## LaTeX behaviour and caveats

For TeX input, `texaudit` understands AGU's unusual template commands and environments for elements such as the abstract, plain language summary, and key points. It follows `\input{}`, `\include{}`, and `\subfile{}` recursively by default.

It is a manuscript parser, not a complete TeX engine. It cannot evaluate arbitrary user-defined macros, conditionals, or generated content exactly. Bibliographies are most reliable when the rendered reference content is present in the manuscript or an included `.bbl` file. Use `--no-follow-inputs` if referenced TeX files should not be opened.

Plain-text and Markdown audits have the least structural information and should be treated as estimates.

## Useful options

```text
--list-journals          List the built-in profile names
--journal NAME           Use a built-in journal profile
--profile FILE.yaml      Use a profile file from your computer
--json                   Print machine-readable JSON instead of the terminal report
--output FILE            Write the displayed report to a file
--no-follow-inputs       Do not follow TeX input/include/subfile commands
--format tex|docx|text   Override automatic input-format detection
```

For example:

```bash
texaudit manuscript.docx --journal agu-jgr-earth-surface --json --output audit.json
texaudit manuscript.tex --profile my-journal.yaml
texaudit manuscript.tex --journal agu-grl --no-follow-inputs
```

The command exits with status code `1` when a check fails and `0` otherwise, which makes it suitable for scripts and continuous-integration checks. A report containing warnings but no failures exits successfully.

## Built-in journal profiles

Run `texaudit --list-journals` for the authoritative list installed on your computer. The current profiles concentrate on journals commonly used in Earth science:

| Publisher | Profiles |
| --- | --- |
| AGU | Geophysical Research Letters; all eight Journal of Geophysical Research journals; Tectonics; Water Resources Research |
| Nature Portfolio | Nature Geoscience Article; Nature Geoscience Brief Communication; Nature Communications Article |
| Elsevier | Earth and Planetary Science Letters; Geomorphology; Journal of Hydrology; Tectonophysics |

Profile choice includes article type because limits can differ within one journal. For example, `agu-grl` is specifically a GRL Research Letter. Use the profile that matches the intended submission type, not merely the publisher.

The AGU profiles were checked against official guidance on 2026-09-15. Nature and Elsevier profiles distinguish hard limits from recommendations where the journal guidance does. Elsevier highlights are normally uploaded as a separate file, so their absence from the manuscript is informational; if highlights are present, their number and length are checked.

Journal rules can change. Each YAML file records its source, URL, and verification date so that the assumptions remain visible.

## Add or change a journal profile

Profiles are deliberately stored as readable YAML files rather than hard-coded in Python. You can copy a profile, edit the values in a text editor, and use it immediately without reinstalling:

```bash
texaudit manuscript.tex --profile "/path/to/my-journal.yaml"
```

For a complete field reference, example profile, testing checklist, and instructions for contributing a built-in profile, see [Adding journal profiles](src/texaudit/profiles/ADDING_PROFILES.md).

Custom files passed with `--profile` must contain all rules they need. The `extends` key currently works only between bundled profiles.

## Update or uninstall

If you installed from a downloaded ZIP, download and extract the new version, open a terminal in that new folder, and run the install command again with `--upgrade`:

```bash
python3 -m pip install --upgrade .
```

Use `py` instead of `python3` on Windows. To uninstall:

```bash
python3 -m pip uninstall texaudit
```

If Git is already installed, installation or updating can be done directly from GitHub:

```bash
python3 -m pip install --upgrade "git+https://github.com/thermok-SG/texaudit.git"
```

## Troubleshooting

### `texaudit: command not found`

Use the longer command shown in the installation check:

```bash
python3 -m texaudit.cli --list-journals
```

On Windows use `py` instead of `python3`.

### Python is not found

Install Python 3.10 or newer, close and reopen the terminal, and try again. On Windows, `py --version` should print the installed version. On macOS or Linux, use `python3 --version`.

### Permission or `externally-managed-environment` error

Python installations supplied by some operating systems prevent global package installation. A simple isolated alternative is [pipx](https://pipx.pypa.io/stable/installation/). Once pipx is installed, open a terminal in the extracted folder and run:

```bash
pipx install .
```

### The manuscript section was not detected

Check the parser warnings, then confirm that the heading or environment resembles the journal template. For Word, use standard heading/caption styles and remove tracked changes. For TeX, check custom macros and included files. The component counts in the report are intended to make detection mistakes visible.

## Development setup

Contributors may use any Python environment manager. With the existing micromamba environment used for this project:

```bash
micromamba activate texaudit
python -m pip install -e . pytest
pytest -q
```

Without micromamba, create and activate a standard Python virtual environment and run the same `pip` and `pytest` commands.

## License

See [LICENSE](LICENSE).
