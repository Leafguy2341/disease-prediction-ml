"""Portable paths, read-only loading, safe capability detection and output routing."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from src.data import paths as module
from src.data.io import save_table
from src.data.loader import DatasetError, dataset_path, load_dataset, prepare_dataset, sha256_file
from src.data.paths import DriveUnavailableError, RuntimeCapabilities, resolve_paths, mount_google_drive

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path, monkeypatch):
    for key in list(module.os.environ):
        if key.startswith("DISEASE_") or key.startswith("COLAB_"):
            monkeypatch.delenv(key)
    root = tmp_path / "source with spaces"
    (root / "configs").mkdir(parents=True)
    for name in ["phase1.json", "runtime.json"]:
        (root / "configs" / name).write_bytes((REPO / "configs" / name).read_bytes())
    return root


def csv_at(directory, name="actual source.csv"):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("diseases,a,b\nA,1,0\nB,0,1\n", encoding="utf-8")
    return path


def colab_layout(project, tmp_path, monkeypatch):
    content = tmp_path / "content"
    drive = content / "drive"
    storage = drive / "MyDrive/ML_Projects/disease-prediction-ml"
    storage.mkdir(parents=True)
    config = project / "configs/colab-test.json"
    config.write_text(json.dumps({"runtime": "colab", "colab": {"drive_mount": str(drive), "cache_dir": str(content / "cache"), "ephemeral_root": str(content)}}), encoding="utf-8")
    return resolve_paths(project, config_file=config), storage, content


def test_local_resolution_independent_of_cwd(project, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = resolve_paths(project)
    assert paths.storage_root == project
    assert paths.output_root == project
    assert paths.runtime == "local"
    source = csv_at(paths.raw_dir)
    assert dataset_path(paths, {}) == source.resolve()


def test_colab_uses_drive_for_data_and_outputs(project, tmp_path, monkeypatch):
    paths, storage, content = colab_layout(project, tmp_path, monkeypatch)
    assert paths.project_root == project
    assert paths.storage_root == storage
    assert paths.output_root == storage
    assert paths.raw_dir == storage / "data/raw"
    assert paths.cache_dir == content / "cache"
    source = csv_at(paths.raw_dir)
    assert dataset_path(paths, {}) == source


def test_missing_drive_is_clear_and_does_not_create_fake_mount(project, tmp_path, monkeypatch):
    missing = tmp_path / "unmounted"
    monkeypatch.setenv("DISEASE_RUNTIME", "colab")
    monkeypatch.setenv("DISEASE_DRIVE_MOUNT", str(missing))
    with pytest.raises(DriveUnavailableError, match="Không tự mount"):
        resolve_paths(project)
    assert not missing.exists()


def test_remote_filesystem_needs_no_google_colab_api(project, tmp_path, monkeypatch):
    storage = tmp_path / "persistent mount"
    monkeypatch.setenv("DISEASE_RUNTIME", "remote")
    monkeypatch.setenv("DISEASE_STORAGE_ROOT", str(storage))
    monkeypatch.setattr(module, "detect_capabilities", lambda: RuntimeCapabilities(False, False))
    paths = resolve_paths(project)
    source = csv_at(paths.raw_dir)
    assert dataset_path(paths, {}) == source
    assert paths.output_root == storage


def test_explicit_drive_output_also_requires_a_real_mount(project, tmp_path, monkeypatch):
    drive = tmp_path / "unmounted-drive"
    monkeypatch.setenv("DISEASE_RUNTIME", "colab")
    monkeypatch.setenv("DISEASE_STORAGE_ROOT", str(project))
    monkeypatch.setenv("DISEASE_DRIVE_MOUNT", str(drive))
    monkeypatch.setenv("DISEASE_OUTPUT_DIR", str(drive / "MyDrive/results"))
    with pytest.raises(DriveUnavailableError):
        resolve_paths(project)
    assert not drive.exists()


def test_environment_overrides_runtime_config(project, tmp_path, monkeypatch):
    custom = tmp_path / "custom"
    monkeypatch.setenv("DISEASE_OUTPUT_DIR", str(custom))
    monkeypatch.setenv("DISEASE_RUNTIME", "local")
    monkeypatch.setenv("DISEASE_COPY_RAW_TO_LOCAL", "true")
    paths = resolve_paths(project)
    assert paths.output_root == custom
    assert paths.copy_raw_to_local


@pytest.mark.parametrize("key,value", [("DISEASE_RUNTIME", "invalid"), ("DISEASE_COPY_RAW_TO_LOCAL", "perhaps")])
def test_invalid_settings_fail_clearly(project, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        resolve_paths(project)


def test_missing_config_is_clear(project, monkeypatch):
    monkeypatch.setenv("DISEASE_PATH_CONFIG", "configs/absent.json")
    with pytest.raises(FileNotFoundError, match="DISEASE_PATH_CONFIG"):
        resolve_paths(project)


def test_auto_colab_with_no_drive_fails_instead_of_using_code_checkout(project, tmp_path, monkeypatch):
    monkeypatch.setattr(module, "detect_capabilities", lambda: RuntimeCapabilities(True, True))
    monkeypatch.setenv("DISEASE_DRIVE_MOUNT", str(tmp_path / "missing-drive"))
    with pytest.raises(DriveUnavailableError):
        resolve_paths(project)


def test_package_presence_does_not_make_local_python_colab(project, monkeypatch):
    monkeypatch.setattr(module.importlib.util, "find_spec", lambda _: object())
    assert not module.detect_capabilities().colab_runtime_detected
    assert resolve_paths(project).runtime == "local"


def test_mount_never_calls_drive_in_local_or_generic_remote(project, monkeypatch):
    monkeypatch.setattr(module, "detect_capabilities", lambda: RuntimeCapabilities(False, True))
    monkeypatch.setattr(module.importlib, "import_module", lambda _: pytest.fail("Must not import/call Drive here"))
    with pytest.raises(RuntimeError, match="Không gọi drive.mount"):
        mount_google_drive(project)


def test_mount_api_unavailable_has_alternative_instructions(project, tmp_path, monkeypatch):
    monkeypatch.setenv("DISEASE_DRIVE_MOUNT", str(tmp_path / "missing"))
    monkeypatch.setattr(module, "detect_capabilities", lambda: RuntimeCapabilities(True, False))
    with pytest.raises(RuntimeError, match="không có API"):
        mount_google_drive(project)


def test_mount_failure_is_actionable(project, tmp_path, monkeypatch):
    monkeypatch.setenv("DISEASE_DRIVE_MOUNT", str(tmp_path / "drive"))
    monkeypatch.setattr(module, "detect_capabilities", lambda: RuntimeCapabilities(True, True))
    def fail(*args, **kwargs):
        raise ValueError("frontend unavailable")
    monkeypatch.setattr(module.importlib, "import_module", lambda _: SimpleNamespace(mount=fail))
    with pytest.raises(RuntimeError, match="frontend VS Code"):
        mount_google_drive(project)


def test_successful_mount_is_verified_not_merely_assumed(project, tmp_path, monkeypatch):
    drive = tmp_path / "drive"
    monkeypatch.setenv("DISEASE_DRIVE_MOUNT", str(drive))
    monkeypatch.setattr(module, "detect_capabilities", lambda: RuntimeCapabilities(True, True))
    monkeypatch.setattr(module.importlib, "import_module", lambda _: SimpleNamespace(mount=lambda *a, **k: None))
    with pytest.raises(DriveUnavailableError, match="API đã trả về"):
        mount_google_drive(project)
    def mount(point, **kwargs):
        (Path(point) / "MyDrive").mkdir(parents=True)
    monkeypatch.setattr(module.importlib, "import_module", lambda _: SimpleNamespace(mount=mount))
    assert mount_google_drive(project) == drive


def test_missing_dataset_error(project):
    with pytest.raises(FileNotFoundError, match="DISEASE_DATA_PATH"):
        dataset_path(resolve_paths(project), {})


def test_ambiguous_csv_requires_explicit_choice(project):
    paths = resolve_paths(project)
    csv_at(paths.raw_dir, "one.csv")
    csv_at(paths.raw_dir, "two.csv")
    with pytest.raises(DatasetError, match="nhiều CSV"):
        dataset_path(paths, {})


def test_configured_actual_filename_is_used_without_renaming(project):
    source = csv_at(project / "data/raw", "Tên dữ liệu thật.CSV")
    config = project / "configs/custom.json"
    config.write_text(json.dumps({"raw_dataset": "data/raw/" + source.name}), encoding="utf-8")
    assert dataset_path(resolve_paths(project, config_file=config), {}) == source


def test_cached_copy_preserves_bytes_filename_and_results(project):
    paths = replace(resolve_paths(project), copy_raw_to_local=True)
    source = csv_at(paths.raw_dir)
    original = sha256_file(source)
    cached = prepare_dataset(paths, source)
    assert cached != source and cached.name == source.name
    assert sha256_file(cached) == sha256_file(source) == original
    pd.testing.assert_frame_equal(load_dataset(cached, "diseases"), load_dataset(source, "diseases"))
    assert prepare_dataset(paths, source) == cached


def test_corrupt_cache_does_not_overwrite_or_modify_source(project):
    paths = replace(resolve_paths(project), copy_raw_to_local=True)
    source = csv_at(paths.raw_dir)
    before = source.read_bytes()
    cached = prepare_dataset(paths, source)
    cached.write_bytes(b"corrupt cache")
    with pytest.raises(DatasetError, match="Cache sai checksum"):
        prepare_dataset(paths, source)
    assert cached.read_bytes() == b"corrupt cache" and source.read_bytes() == before


def test_colab_rejects_ephemeral_outputs_and_drive_cache(project, tmp_path, monkeypatch):
    paths, storage, content = colab_layout(project, tmp_path, monkeypatch)
    monkeypatch.setenv("DISEASE_OUTPUT_DIR", str(content / "temporary-results"))
    config = project / "configs/colab-test.json"
    with pytest.raises(ValueError, match="tạm thời"):
        resolve_paths(project, config_file=config)
    monkeypatch.delenv("DISEASE_OUTPUT_DIR")
    monkeypatch.setenv("DISEASE_COPY_RAW_TO_LOCAL", "true")
    monkeypatch.setenv("DISEASE_CACHE_DIR", str(storage / "cache"))
    with pytest.raises(ValueError, match="không nằm trong Google Drive"):
        resolve_paths(project, config_file=config)


def test_run_output_routing_preserves_old_reports(project):
    legacy = project / "reports/tables/old.csv"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"historical report")
    paths = resolve_paths(project)
    first, second = paths.new_run(), paths.new_run()
    assert first.run_id != second.run_id
    save_table(first, "new", pd.DataFrame({"x": [1]}))
    assert (first.tables_dir / "new.csv").is_file()
    assert legacy.read_bytes() == b"historical report"
    assert first.metadata_dir.is_relative_to(paths.output_root / "artifacts/metadata")


def test_src_imports_work_from_an_unrelated_directory(tmp_path):
    code = "import sys; sys.path.insert(0,sys.argv[1]); from src.data.loader import load_dataset; from src.data.io import load_dataset as legacy; from src.data.paths import resolve_paths; assert load_dataset is legacy"
    result = subprocess.run([sys.executable, "-c", code, str(REPO)], cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
