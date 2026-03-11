"""Locate and order the SQL assets that build the warehouse."""
from __future__ import annotations

from pathlib import Path

from pulse.config import PATHS

# Build order matters: schemas -> bronze -> silver/star -> gold marts.
LAYERS: dict[str, str] = {
    "init": "database/init",
    "staging": "database/staging",
    "warehouse": "database/warehouse",
    "analytics": "database/analytics",
}


def layer_files(layer: str) -> list[Path]:
    directory = PATHS.root / LAYERS[layer]
    return sorted(directory.glob("*.sql"))


def all_files() -> list[Path]:
    files: list[Path] = []
    for layer in LAYERS:
        files.extend(layer_files(layer))
    return files


def read(relative_path: str) -> str:
    return (PATHS.root / relative_path).read_text(encoding="utf-8")
