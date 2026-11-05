"""Compatibility imports, analysis configuration and report table helpers."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .loader import DatasetError, dataset_path, load_dataset, sha256_file
from .paths import OutputPaths, project_root, output_paths


def read_config(root: Path) -> dict:
    config = json.loads((root / "configs/phase1.json").read_text(encoding="utf-8"))
    if not 0.5 < config["near_constant_threshold"] <= 1:
        raise DatasetError("near_constant_threshold phải thuộc (0.5, 1].")
    return config


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def save_table(root: Path | OutputPaths, name: str, frame: pd.DataFrame, *, index: bool = False) -> None:
    folder = output_paths(root).tables_dir
    folder.mkdir(parents=True, exist_ok=True)
    frame.to_csv(folder / f"{name}.csv", index=index, encoding="utf-8-sig")


def markdown_table(frame: pd.DataFrame, limit: int = 15) -> str:
    """Small tables without adding the optional tabulate dependency."""
    display = frame.head(limit).copy()
    clean = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    rows = ["| " + " | ".join(map(clean, display.columns)) + " |",
            "| " + " | ".join(["---"] * len(display.columns)) + " |"]
    rows += ["| " + " | ".join(map(clean, row)) + " |" for row in display.itertuples(index=False, name=None)]
    return "\n".join(rows)
