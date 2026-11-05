"""Source-only folder preparation; no Phase 2/session receipt is required."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def editing_project(tmp_path):
    root = tmp_path / "editing workspace"
    files = [p for p in (ROOT / "src").rglob("*.py") if "__pycache__" not in p.parts]
    files += [ROOT / "configs" / n for n in (
        "runtime.json", "phase1.json", "phase2.json", "phase3.json", "phase5b.json", "dataset_source.json", "phase2_integrity.json")]
    files += [ROOT / n for n in ("requirements-training.txt", "requirements-notebooks.txt", "scripts/prepare_colab_source.ps1")]
    for source in files:
        target = root / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return root


def prepare(root, *args):
    if os.name != "nt":
        pytest.skip("PowerShell preparation belongs to the Windows editing workspace")
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                           str(root / "scripts/prepare_colab_source.ps1"), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_prepare_has_one_folder_and_no_data_or_receipts(editing_project):
    root = editing_project
    assert not (root / "data").exists()  # Source sync does not need locked data locally.
    result = prepare(root)
    assert result.returncode == 0, result.stderr
    stage = root / "dist/drive-source"
    assert (stage / "src/data/colab_runtime.py").is_file()
    assert (stage / "configs/phase2_integrity.json").is_file()
    assert (stage / "configs/phase5b.json").is_file()
    assert not (stage / "source_manifest.json").exists()
    assert not (root / "dist/colab-session").exists()
    assert not list(stage.rglob("*.csv*")) and not list(stage.rglob("*.joblib"))
    before = {p: p.stat().st_mtime_ns for p in stage.rglob("*") if p.is_file()}
    check = prepare(root, "-CheckOnly")
    assert check.returncode == 0, check.stderr
    assert before == {p: p.stat().st_mtime_ns for p in stage.rglob("*") if p.is_file()}


def test_refresh_preserves_historical_packages_and_detects_stale_source(editing_project):
    root = editing_project
    assert prepare(root).returncode == 0
    historical = root / "dist/colab-session/personal-runtime.py"
    historical.parent.mkdir(parents=True)
    historical.write_bytes(b"keep historical package")
    archive = root / "dist/old-source.zip"
    archive.write_bytes(b"keep archive")
    target = root / "src/data/colab_runtime.py"
    target.write_bytes(target.read_bytes() + b"\n# updated source\n")
    assert prepare(root, "-CheckOnly").returncode != 0
    result = prepare(root, "-Refresh")
    assert result.returncode == 0, result.stderr
    assert prepare(root, "-CheckOnly").returncode == 0
    assert historical.read_bytes() == b"keep historical package" and archive.read_bytes() == b"keep archive"


def test_refresh_preserves_unrelated_files_in_staging(editing_project):
    root = editing_project
    assert prepare(root).returncode == 0
    user_file = root / "dist/drive-source/personal-note.txt"
    user_file.write_bytes(b"do not delete")
    assert prepare(root, "-Refresh").returncode != 0
    assert user_file.read_bytes() == b"do not delete"
