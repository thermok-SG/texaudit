"""Discover and load YAML journal profiles, including built-in inheritance."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml


def builtin_profile_names() -> list[str]:
    """Return sorted public profile names bundled with the installed package."""

    folder = resources.files("texaudit").joinpath("profiles")
    return sorted(
        path.name.removesuffix(".yaml")
        for path in folder.iterdir()
        if path.name.endswith(".yaml") and not path.name.startswith("_")
    )


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge mappings while replacing lists and scalar values."""

    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_builtin(name: str, seen: set[str] | None = None) -> tuple[dict[str, Any], Any]:
    """Load one bundled profile and recursively resolve its ``extends`` key."""

    seen = set() if seen is None else seen
    if name in seen:
        raise ValueError(f"Circular journal profile inheritance involving '{name}'.")
    seen.add(name)
    resource = resources.files("texaudit").joinpath("profiles", f"{name}.yaml")
    if not resource.is_file():
        choices = ", ".join(builtin_profile_names()) or "(none)"
        raise ValueError(f"Unknown journal profile '{name}'. Available: {choices}")
    data = yaml.safe_load(resource.read_text(encoding="utf-8")) or {}
    parent = data.pop("extends", None)
    if parent:
        parent_data, _ = _load_builtin(parent, seen)
        data = _deep_merge(parent_data, data)
    return data, resource


def load_profile(journal: str | None = None, profile_path: str | None = None) -> tuple[dict[str, Any], str | None]:
    """Load a custom profile path or a named bundled profile.

    ``profile_path`` takes precedence when both selectors are supplied. Custom
    profiles are intentionally loaded verbatim and therefore cannot inherit a
    bundled profile.

    Returns:
        A tuple of the profile mapping and its resolved source identifier.

    Raises:
        FileNotFoundError: If a custom profile path does not exist.
        ValueError: If no selector is supplied, a built-in name is unknown, or
            built-in inheritance is circular.
        yaml.YAMLError: If YAML syntax is invalid.
    """

    if profile_path:
        path = Path(profile_path).expanduser().resolve()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data, str(path)
    if not journal:
        raise ValueError("Provide --journal NAME or --profile PATH. Use --list-journals to see built-in profiles.")
    data, resource = _load_builtin(journal)
    return data, str(resource)
