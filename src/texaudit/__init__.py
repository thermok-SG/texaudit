"""Audit LaTeX, DOCX, and text manuscripts against journal profiles.

Most library users should start with :class:`TexAudit`. Lower-level parsing and
report model APIs remain available from their respective modules.
"""

from .api import TexAudit
from .models import AuditReport, CheckResult, ManuscriptStats

__all__ = ["AuditReport", "CheckResult", "ManuscriptStats", "TexAudit"]
__version__ = "0.2.1"
