from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ManuscriptStats:
    source: str
    files_read: list[str] = field(default_factory=list)
    title_words: int = 0
    abstract_words: int = 0
    plain_language_summary_words: int = 0
    key_point_count: int = 0
    key_point_max_characters: int = 0
    body_words: int = 0
    acknowledgements_words: int = 0
    appendix_words: int = 0
    figure_caption_words: int = 0
    table_caption_words: int = 0
    table_text_words: int = 0
    open_research_words: int = 0
    reference_words: int = 0
    equation_count: int = 0
    figure_count: int = 0
    table_count: int = 0
    subfigure_count: int = 0
    citation_command_count: int = 0
    unresolved_marker_count: int = 0
    section_names: list[str] = field(default_factory=list)
    environment_names: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def agu_word_count(self) -> int:
        # AGU: abstract + body + acknowledgements + captions + appendices + one per equation.
        # Excludes title/front matter, PLS, key points, table cell text, ORS, references, SI.
        return (
            self.abstract_words
            + self.body_words
            + self.acknowledgements_words
            + self.appendix_words
            + self.figure_caption_words
            + self.table_caption_words
            + self.equation_count
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["agu_word_count"] = self.agu_word_count
        return data


@dataclass
class CheckResult:
    name: str
    status: str  # PASS, WARNING, FAIL, INFO
    message: str
    actual: Any = None
    expected: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditReport:
    profile_name: str
    profile_path: str | None
    stats: ManuscriptStats
    checks: list[CheckResult]

    @property
    def overall_status(self) -> str:
        statuses = {check.status for check in self.checks}
        if "FAIL" in statuses:
            return "FAIL"
        if "WARNING" in statuses:
            return "WARNING"
        return "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "profile_path": self.profile_path,
            "overall_status": self.overall_status,
            "stats": self.stats.to_dict(),
            "checks": [check.to_dict() for check in self.checks],
        }
