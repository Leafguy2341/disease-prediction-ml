"""Source repair only: no project datasets, Drive authentication or model training."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from install_colab_source import install_source
from package_colab import build_bundle


@pytest.fixture
def archive(tmp_path):
    path = tmp_path / "source.pyz"
    build_bundle(ROOT, path)
    return path


def snapshot(root):
    return {p.relative_to(root).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def test_repairs_source_backs_up_changes_and_preserves_config_and_locked_files(archive, tmp_path, monkeypatch):
    root = tmp_path / "Drive Project"
    for relative, payload in {
        "src/models/runtime.py": b"# user's old source\n",
        "src/models/personal_note.py": b"# keep personal code\n",
        "configs/runtime.json": b'{"custom_setting": "keep"}',
        "data/processed/test.csv.gz": b"locked synthetic test payload",
        "artifacts/metadata/phase2/feature_schema.json": b"locked synthetic metadata",
        "reports/previous.md": b"keep existing report",
    }.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    before = snapshot(root)
    original_open = Path.open
    def guarded_open(path, *args, **kwargs):
        if path.name == "test.csv.gz":
            pytest.fail("Source installation must not open a test CSV")
        return original_open(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", guarded_open)
        result = install_source(archive, root)
    assert (root / "src/models/notebook.py").is_file()
    assert (root / "src/models/training.py").read_bytes() == (ROOT / "src/models/training.py").read_bytes()
    assert not (root / "disease-prediction-ml").exists()  # No accidental extra project nesting.
    assert (Path(result["backup_dir"]) / "src/models/runtime.py").read_bytes() == b"# user's old source\n"
    assert "configs/runtime.json" in result["preserved_config"]
    after = snapshot(root)
    for relative in before:
        if relative != "src/models/runtime.py":
            assert before[relative] == after[relative], relative
    again = install_source(archive, root)
    assert again["installed"] == [] and again["backup_dir"] is None
    assert after == snapshot(root)


def test_corrupt_source_rejected_before_any_installation(archive, tmp_path):
    broken = tmp_path / "broken.pyz"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(broken, "w") as target:
        for name in source.namelist():
            target.writestr(name, b"corrupt" if name.endswith("src/models/notebook.py") else source.read(name))
    root = tmp_path / "project"
    root.mkdir()
    with pytest.raises(ValueError, match="Checksum"):
        install_source(broken, root)
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("name", ["../outside.py", "/absolute.py", "disease-prediction-ml/src/../../data/test.py"])
def test_unsafe_member_rejected_before_writes(archive, tmp_path, name):
    with zipfile.ZipFile(archive, "a") as package:
        package.writestr(name, b"unsafe")
    root = tmp_path / "project"
    root.mkdir()
    with pytest.raises(ValueError, match="không hợp lệ"):
        install_source(archive, root)
    assert list(root.iterdir()) == []


def test_missing_destination_is_not_created(archive, tmp_path):
    root = tmp_path / "mistyped-project"
    with pytest.raises(FileNotFoundError, match="DRIVE_PROJECT_DIR"):
        install_source(archive, root)
    assert not root.exists()


def test_zipapp_runs_with_standard_python_without_importing_project(archive):
    result = subprocess.run([sys.executable, str(archive), "--help"], capture_output=True, text=True, encoding="utf-8", check=True)
    assert "--project-dir" in result.stdout
    with zipfile.ZipFile(archive) as package:
        assert "__main__.py" in package.namelist()
        manifest = json.loads(package.read("disease-prediction-ml/bundle_manifest.json"))
        assert not any(name.endswith(".csv.gz") or name.endswith(".joblib") for name in manifest)

