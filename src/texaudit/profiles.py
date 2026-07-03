from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml


def builtin_profile_names() -> list[str]:
    folder = resources.files("texaudit").joinpath("profiles")
    return sorted(path.name.removesuffix(".yaml") for path in folder.iterdir() if path.name.endswith(".yaml"))


def load_profile(journal: str | None = None, profile_path: str | None = None) -> tuple[dict[str, Any], str | None]:
    if profile_path:
        path = Path(profile_path).expanduser().resolve()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data, str(path)
    if not journal:
        raise ValueError("Provide --journal NAME or --profile PATH. Use --list-journals to see built-in profiles.")
    resource = resources.files("texaudit").joinpath("profiles", f"{journal}.yaml")
    if not resource.is_file():
        choices = ", ".join(builtin_profile_names()) or "(none)"
        raise ValueError(f"Unknown journal profile '{journal}'. Available: {choices}")
    return yaml.safe_load(resource.read_text(encoding="utf-8")) or {}, str(resource)
