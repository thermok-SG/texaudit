from __future__ import annotations

from typing import Any

from .models import AuditReport, CheckResult, ManuscriptStats


def _limit_check(name: str, actual: int, max_value: int | None, unit: str) -> CheckResult:
    if max_value is None:
        return CheckResult(name, "INFO", f"{actual} {unit}; no limit configured.", actual=actual)
    status = "PASS" if actual <= max_value else "FAIL"
    return CheckResult(name, status, f"{actual} / {max_value} {unit}", actual=actual, expected=max_value)


def _configured_limit(name: str, actual: int, config: dict[str, Any], key: str, unit: str) -> CheckResult | None:
    maximum = config.get(key)
    if maximum is None:
        return None
    status = "PASS" if actual <= maximum else config.get("exceed_status", "FAIL")
    message = f"{actual} / {maximum} {unit}"
    if config.get("qualifier"):
        message += f"; {config['qualifier']}"
    return CheckResult(name, status, message, actual=actual, expected=maximum)


def _required_section(stats: ManuscriptStats, name: str, aliases: list[str], required: bool = True) -> CheckResult:
    found = any(alias.lower() in stats.section_names or alias.lower() in stats.environment_names for alias in aliases)
    if found:
        return CheckResult(name, "PASS", "Detected.")
    status = "FAIL" if required else "INFO"
    message = "Not detected." if required else "Not detected; optional for this journal."
    return CheckResult(name, status, message)


def audit(stats: ManuscriptStats, profile: dict[str, Any], profile_path: str | None = None) -> AuditReport:
    journal = profile.get("journal", {})
    profile_name = journal.get("name", "Custom profile")
    checks: list[CheckResult] = []
    limits = profile.get("limits", {})
    sections = profile.get("sections", {})

    abstract_cfg = sections.get("abstract", {})
    if abstract_cfg:
        if stats.abstract_words == 0:
            checks.append(CheckResult("Abstract", "FAIL" if abstract_cfg.get("required", True) else "WARNING", "Not detected."))
        else:
            checks.append(_limit_check("Abstract", stats.abstract_words, abstract_cfg.get("max_words"), "words"))

    pls_cfg = sections.get("plain_language_summary", {})
    if pls_cfg:
        if stats.plain_language_summary_words == 0:
            checks.append(CheckResult("Plain language summary", "FAIL" if pls_cfg.get("required", False) else "INFO", "Not detected; optional for this journal."))
        else:
            checks.append(_limit_check("Plain language summary", stats.plain_language_summary_words, pls_cfg.get("max_words"), "words"))

    kp_cfg = sections.get("key_points", {})
    if kp_cfg:
        minimum = kp_cfg.get("min_items", 1 if kp_cfg.get("required") else None)
        maximum = kp_cfg.get("max_items")
        outside_range = (minimum is not None and stats.key_point_count < minimum) or (maximum is not None and stats.key_point_count > maximum)
        if minimum is not None and maximum is not None:
            expected = f"{minimum}-{maximum}"
        else:
            expected = maximum if maximum is not None else f">={minimum}"
        status = "FAIL" if outside_range else "PASS"
        checks.append(CheckResult("Key points", status, f"{stats.key_point_count} / {expected} items", actual=stats.key_point_count, expected=expected))
        max_chars = kp_cfg.get("max_characters_per_item")
        if max_chars is not None:
            status = "PASS" if stats.key_point_max_characters <= max_chars else "FAIL"
            checks.append(CheckResult("Longest key point", status, f"{stats.key_point_max_characters} / {max_chars} characters", actual=stats.key_point_max_characters, expected=max_chars))

    highlights_cfg = sections.get("highlights", {})
    if highlights_cfg:
        if stats.highlight_count == 0 and not highlights_cfg.get("required", False):
            checks.append(CheckResult("Highlights", "INFO", "Not detected; Elsevier highlights are normally uploaded as a separate file."))
        else:
            minimum = highlights_cfg.get("min_items")
            maximum = highlights_cfg.get("max_items")
            outside_range = (minimum is not None and stats.highlight_count < minimum) or (maximum is not None and stats.highlight_count > maximum)
            expected = f"{minimum}-{maximum}" if minimum is not None and maximum is not None else maximum
            checks.append(CheckResult("Highlights", "FAIL" if outside_range else "PASS", f"{stats.highlight_count} / {expected} items", actual=stats.highlight_count, expected=expected))
            max_chars = highlights_cfg.get("max_characters_per_item")
            if max_chars is not None:
                status = "PASS" if stats.highlight_max_characters <= max_chars else "FAIL"
                checks.append(CheckResult("Longest highlight", status, f"{stats.highlight_max_characters} / {max_chars} characters", actual=stats.highlight_max_characters, expected=max_chars))

    checks.append(_limit_check("Figures", stats.figure_count, limits.get("max_figures"), "figures"))
    checks.append(_limit_check("Tables", stats.table_count, limits.get("max_tables"), "tables"))

    title_cfg = limits.get("title", {})
    for result in (
        _configured_limit("Title", stats.title_words, title_cfg, "max_words", "words"),
        _configured_limit("Title", stats.title_characters, title_cfg, "max_characters", "characters"),
    ):
        if result:
            checks.append(result)

    main_text_cfg = limits.get("main_text", {})
    if main_text_cfg:
        main_text_words = stats.body_words - (stats.methods_words if main_text_cfg.get("exclude_methods") else 0)
        result = _configured_limit("Main text", main_text_words, main_text_cfg, "max_words", "words")
        if result:
            checks.append(result)
    methods_cfg = limits.get("methods", {})
    if methods_cfg:
        result = _configured_limit("Methods", stats.methods_words, methods_cfg, "max_words", "words")
        if result:
            checks.append(result)
    display_cfg = limits.get("display_items", {})
    if display_cfg:
        result = _configured_limit("Display items", stats.figure_count + stats.table_count, display_cfg, "max_items", "figures/tables")
        if result:
            checks.append(result)
    references_cfg = limits.get("references", {})
    if references_cfg:
        result = _configured_limit("References", stats.reference_count, references_cfg, "max_items", "references")
        if result:
            checks.append(result)

    pu = profile.get("publication_units", {})
    if pu.get("enabled"):
        words_per_unit = int(pu.get("words_per_unit", 500))
        total = (stats.agu_word_count / words_per_unit) + stats.figure_count + stats.table_count
        max_units = pu.get("max_units")
        warning_threshold = pu.get("warning_threshold")
        if max_units is not None:
            status = "PASS" if total <= float(max_units) else "FAIL"
            threshold_label = f"; hard limit {max_units}."
            expected = max_units
        elif warning_threshold is not None:
            status = "PASS" if total <= float(warning_threshold) else "WARNING"
            threshold_label = f"; overlength-fee threshold {warning_threshold}."
            expected = warning_threshold
        else:
            status = "INFO"
            threshold_label = ""
            expected = None
        message = f"{total:.2f} PUs = {stats.agu_word_count} counted words / {words_per_unit} + {stats.figure_count} figures + {stats.table_count} tables" + threshold_label
        checks.append(CheckResult("Publication units", status, message, actual=round(total, 2), expected=expected))

    for key, cfg in profile.get("presence_checks", {}).items():
        aliases = cfg.get("aliases", [key.replace("_", " ")])
        checks.append(_required_section(stats, cfg.get("label", key.replace("_", " ").title()), aliases, cfg.get("required", False)))

    if stats.unresolved_marker_count:
        checks.append(CheckResult("Unresolved markers", "WARNING", f"Found {stats.unresolved_marker_count} '??' marker(s) in TeX source.", actual=stats.unresolved_marker_count))
    else:
        checks.append(CheckResult("Unresolved markers", "PASS", "No '??' markers detected in TeX source."))
    if stats.warnings:
        for warning in stats.warnings:
            checks.append(CheckResult("Parser", "WARNING", warning))
    return AuditReport(profile_name=profile_name, profile_path=profile_path, stats=stats, checks=checks)
