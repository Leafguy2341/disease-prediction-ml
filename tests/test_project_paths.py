"""Regression coverage for notebook kernels started outside the project root."""
from pathlib import Path

import pytest

from src.data.io import project_root


@pytest.fixture
def layout(tmp_path, monkeypatch):
    monkeypatch.delenv("DISEASE_PROJECT_ROOT", raising=False)
    root = tmp_path / "workspace/disease-prediction-ml"
    (root / "configs").mkdir(parents=True)
    (root / "configs/phase1.json").write_text("{}", encoding="utf-8")
    (root / "notebooks").mkdir()
    return root


@pytest.mark.parametrize("location", ["root", "notebooks", "workspace"])
def test_discovery_from_supported_working_directories(layout, location):
    start = {"root": layout, "notebooks": layout / "notebooks", "workspace": layout.parent}[location]
    assert project_root(start) == layout.resolve()


def test_explicit_root_from_unrelated_kernel_directory(layout, tmp_path):
    elsewhere = tmp_path / "runtime"
    elsewhere.mkdir()
    assert project_root(elsewhere, root_override=layout) == layout.resolve()


def test_environment_root_from_unrelated_kernel_directory(layout, tmp_path, monkeypatch):
    monkeypatch.setenv("DISEASE_PROJECT_ROOT", str(layout))
    assert project_root(tmp_path) == layout.resolve()


def test_invalid_explicit_root_does_not_silently_fall_back(layout):
    with pytest.raises(FileNotFoundError, match="configs/phase1.json"):
        project_root(layout, root_override=layout / "notebooks")


def test_explicit_root_takes_priority_over_stale_environment(layout, monkeypatch):
    monkeypatch.setenv("DISEASE_PROJECT_ROOT", str(layout / "missing"))
    assert project_root(root_override=layout) == layout.resolve()


def test_missing_remote_project_explains_required_files(tmp_path):
    with pytest.raises(FileNotFoundError, match="configs/, src/"):
        project_root(tmp_path)
