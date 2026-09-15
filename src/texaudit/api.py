"""Public object-oriented interface for running manuscript audits.

The :class:`TexAudit` class binds a journal profile and parser options together.
It is useful when an application audits several manuscripts with the same rules;
the lower-level functions remain available for callers that need individual
parsing or rule-evaluation steps.
"""

from __future__ import annotations

from pathlib import Path

from .audit import audit as apply_profile
from .models import AuditReport
from .profiles import load_profile
from .readers import SUPPORTED_FORMATS, parse_source


class TexAudit:
    """Configure and run manuscript audits against one journal profile.

    Args:
        journal: Name of a bundled profile, such as
            ``"agu-jgr-earth-surface"``.
        profile_path: Path to a self-contained custom YAML profile. When given,
            this takes precedence over ``journal`` to match the command-line API.
        source_format: ``"auto"`` to infer the input type from its extension, or
            one of ``"tex"``, ``"docx"``, and ``"text"``.
        follow_inputs: Whether TeX parsers recursively expand ``\\input``,
            ``\\include``, and ``\\subfile`` commands.

    Raises:
        FileNotFoundError: If ``profile_path`` does not exist.
        ValueError: If no profile is selected, a bundled name is unknown, or the
            requested source format is unsupported.
    """

    def __init__(
        self,
        *,
        journal: str | None = None,
        profile_path: str | Path | None = None,
        source_format: str = "auto",
        follow_inputs: bool = True,
    ) -> None:
        """Load the selected profile and retain parser options for later audits."""

        if source_format not in SUPPORTED_FORMATS:
            choices = ", ".join(sorted(SUPPORTED_FORMATS))
            raise ValueError(f"Unsupported format '{source_format}'. Choose one of: {choices}.")
        self.profile, self.profile_path = load_profile(
            journal=journal,
            profile_path=str(profile_path) if profile_path is not None else None,
        )
        self.source_format = source_format
        self.follow_inputs = follow_inputs

    def audit(self, source_file: str | Path) -> AuditReport:
        """Parse one manuscript and evaluate it against the configured profile.

        Args:
            source_file: Path to a TeX, DOCX, text, or Markdown manuscript.

        Returns:
            A structured report containing detected statistics and checks.

        Raises:
            FileNotFoundError: If the manuscript or an expected input is absent.
            ValueError: If automatic input-format detection fails.
        """

        stats = parse_source(
            Path(source_file),
            source_format=self.source_format,
            follow_inputs=self.follow_inputs,
        )
        return apply_profile(stats, self.profile, self.profile_path)
