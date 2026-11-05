"""Local fixture checks only: these do not claim a real Colab integration run."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType

import pytest

from src.data import colab_runtime as runtime
from src.data.integrity import read_baseline, verify_training_inputs, TRAINING_FILES
from src.data.paths import OutputPaths
from scripts.update_colab_notebooks import entry_source, migrate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def drive_tree(tmp_path):
    content = tmp_path / "content"
    point = content / "drive"
    root = point / "MyDrive/project with spaces"
    files = [p for p in (ROOT / "src").rglob("*.py") if "__pycache__" not in p.parts]
    files += list((ROOT / "configs").glob("*.json"))
    files += [ROOT / "requirements-training.txt", ROOT / "requirements-notebooks.txt"]
    files += [ROOT / name for name in runtime.RUNTIME_SCRIPTS]
    for source in files:
        target = root / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    config = json.loads((root / "configs/runtime.json").read_text(encoding="utf-8"))
    config["colab"].update(drive_mount=str(point), project_relative="MyDrive/project with spaces",
                           cache_dir=str(content / "cache"), runtime_workspace=str(content / "workspace"),
                           ephemeral_root=str(content))
    (root / "configs/runtime.json").write_text(json.dumps(config), encoding="utf-8")
    refresh_publication(root)
    return root, config, content


def refresh_publication(root):
    # Synthetic fixture publication; production expected digest comes from local Publish.
    payloads, publication = runtime.make_publication(root)
    (root / "configs/runtime.json").write_bytes(payloads["configs/runtime.json"])
    return publication["sha256"]


def child(root, body):
    # Only the environment gate is mocked in this isolated unit fixture. Actual file/import checks run.
    source = ("import runpy,json,sys\nfrom pathlib import Path\n"
              f"root=Path({str(root)!r})\n"
              "api=runpy.run_path(str(root/'src/data/colab_runtime.py'))\n"
              "api['bootstrap_runtime'].__globals__['is_colab']=lambda: True\n"
              "original=api['bootstrap_runtime']\n"
              "def with_fixture_pin(*a,**kw):\n"
              "    pin=json.loads((root/'configs/runtime.json').read_text())['runtime_publication']['sha256']\n"
              "    return original(*a,expected_payload_sha256=pin,**kw)\n"
              "api['bootstrap_runtime']=with_fixture_pin\n" + body)
    return subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def test_canonical_paths_are_derived_from_one_config(drive_tree):
    root, config, content = drive_tree
    point, actual, cache, workspace, ephemeral = runtime.canonical_paths(config)
    assert actual == root and ephemeral == content
    assert workspace == content / "workspace" and cache == content / "cache"
    assert not workspace.is_relative_to(point)


def test_real_windows_kernel_is_rejected_before_any_sync(drive_tree, monkeypatch):
    root, _, _ = drive_tree
    monkeypatch.setattr(runtime.platform, "system", lambda: "Windows")
    with pytest.raises(RuntimeError, match="Colab"):
        runtime.bootstrap_runtime(root)


def test_missing_drive_is_reported_and_not_created(drive_tree, monkeypatch):
    root, config, content = drive_tree
    # Exercise the common entry convention before code on a missing Drive can be imported.
    source = entry_source(1).replace(str(ROOT).replace("\\", "/"), "irrelevant")
    source = source.replace("Path('/content')", f"Path({str(content)!r})")
    monkeypatch.setattr(runtime.platform, "system", lambda: "Linux")
    absent = content / "missing-drive/MyDrive/project"
    source = source.replace(source.split("DRIVE_ROOT = Path(", 1)[1].split(")", 1)[0], repr(str(absent)))
    with pytest.raises(FileNotFoundError, match="Mount Drive"):
        exec(compile(source, "entry", "exec"), {})
    assert not absent.exists()


def test_missing_source_and_invalid_syntax_fail_precisely(drive_tree):
    root, _, _ = drive_tree
    target = root / "src/data/loader.py"
    target.unlink()
    with pytest.raises(FileNotFoundError, match="src/data/loader.py"):
        runtime.read_source(root, 1)
    target.write_bytes(b"def broken(")
    with pytest.raises(SyntaxError):
        runtime.read_source(root, 1)


def test_phase1_source_and_imports_need_no_phase2_or_phase3_data_artifacts(drive_tree):
    root, _, _ = drive_tree
    # A source release contains all public configs, but no dataset or model artifacts.
    (root / "source_manifest.json").write_bytes(b"obsolete receipt ignored")
    result = child(root, "r=api['bootstrap_runtime'](root,phase=1)\n"
                        "import src.data.loader\n"
                        "assert Path(src.data.loader.__file__).is_relative_to(r.paths.project_root)\n"
                        "assert r.stages=={'A':'PASS','B':'PASS'} and r.inputs is None\n"
                        "assert not (root/'data').exists()\n"
                        "print('unit fixture imports passed; not real Colab')\n")
    assert result.returncode == 0, result.stderr
    assert "Stage A PASS" in result.stdout and "Stage B PASS" in result.stdout


def test_stage_ab_pass_even_when_stage_c_manifest_is_missing(drive_tree):
    root, _, _ = drive_tree
    result = child(root, "r=api['bootstrap_runtime'](root,phase=3)\n"
                        "try:\n"
                        "    api['phase2_preflight'](r)\n"
                        "except FileNotFoundError:\n"
                        "    assert r.stages=={'A':'PASS','B':'PASS','C':'FAIL'}\n"
                        "    print('independent stages verified in unit fixture')\n"
                        "else: raise AssertionError('missing manifest must fail C')\n")
    assert result.returncode == 0, result.stderr
    assert "independent stages verified" in result.stdout


def test_changed_source_and_old_modules_require_restart(drive_tree):
    root, _, _ = drive_tree
    result = child(root, "r=api['bootstrap_runtime'](root,phase=1)\n"
                        "path=root/'src/data/loader.py'\n"
                        "path.write_bytes(path.read_bytes()+b'\\n# changed\\n')\n"
                        "payloads,_=api['make_publication'](root)\n"
                        "(root/'configs/runtime.json').write_bytes(payloads['configs/runtime.json'])\n"
                        "try:\n"
                        "    api['bootstrap_runtime'](root,phase=1)\n"
                        "except RuntimeError as e:\n"
                        "    assert 'Restart Kernel' in str(e)\n"
                        "else: raise AssertionError('stale imported source accepted')\n")
    assert result.returncode == 0, result.stderr


def test_old_checkout_modules_are_not_silently_reused(drive_tree, monkeypatch):
    root, config, _ = drive_tree
    payloads, hashes = runtime.read_source(root, 1)
    workspace = runtime.canonical_paths(config)[3]
    stale = ModuleType("src.stale_example")
    stale.__file__ = str(root / "src/stale_example.py")
    monkeypatch.setitem(sys.modules, "src.stale_example", stale)
    with pytest.raises(RuntimeError, match="Restart Kernel"):
        runtime.copy_source(workspace, payloads, hashes)
    assert not workspace.exists()


def test_new_session_refreshes_owned_workspace_when_source_changes(drive_tree):
    root, config, _ = drive_tree
    payloads, hashes = runtime.read_source(root, 1)
    result = child(root, "r=api['bootstrap_runtime'](root,phase=1)\n")
    assert result.returncode == 0, result.stderr
    old_fp = runtime.source_fingerprint(hashes)
    target = root / "src/data/loader.py"
    target.write_bytes(target.read_bytes() + b"\n# next session\n")
    refresh_publication(root)
    result = child(root, "r=api['bootstrap_runtime'](root,phase=1)\n")
    assert result.returncode == 0, result.stderr
    workspace = runtime.canonical_paths(config)[3]
    assert (workspace / "src/data/loader.py").read_bytes() == target.read_bytes()
    assert runtime.source_fingerprint(runtime.read_source(root, 1)[1]) != old_fp


def test_notebooks_have_one_short_direct_drive_setup_and_keep_model_cells():
    for path in (ROOT / "notebooks").glob("*.ipynb"):
        nb = json.loads(path.read_text(encoding="utf-8"))
        cells = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
        setup = [s for s in cells if "bootstrap_runtime" in s]
        assert len(setup) == 1
        limit = 40 if path.name in {"colab_smoke_test.ipynb", "06_final_model_evaluation.ipynb"} else 12
        assert len(setup[0].splitlines()) <= limit
        assert all("colab-session" not in s and "source_manifest.json" not in s and "SOURCE_ARCHIVE" not in s for s in cells)
        for source in cells:
            compile(source, str(path), "exec")
        assert migrate(path.name, deepcopy(nb)) == nb


def test_smoke_migration_preserves_an_inserted_user_drive_mount_cell():
    from copy import deepcopy
    notebook = json.loads((ROOT / "notebooks/colab_smoke_test.ipynb").read_text(encoding="utf-8"))
    mount = {"cell_type": "code", "id": "user-mount-regression", "metadata": {}, "execution_count": 9,
             "source": ["from google.colab import drive\n", "drive.mount('/content/drive')"],
             "outputs": [{"output_type": "stream", "name": "stdout", "text": ["User mount output retained\n"]}]}
    notebook["cells"].insert(1, mount)
    before = deepcopy(notebook)
    assert migrate("colab_smoke_test.ipynb", notebook) == before


def test_approved_manifests_and_precise_artifact_failures_are_read_only(monkeypatch, tmp_path):
    import hashlib
    files = {}
    metadata = {
        "feature_schema.json": {"features": ["a", "b"], "target": "diseases",
                                "csv_column_order": ["a", "b", "diseases"], "schema_sha256": "fixture-schema"},
        "label_mapping.json": {"classes": ["A", "B"], "class_to_id": {"A": 0, "B": 1}, "id_to_class": ["A", "B"]},
        "preprocessing_policy.json": {"seed": 42, "minimum_unique_vectors_per_class": 10,
                                      "drop_features": ["regurgitation", "regurgitation.1"]},
        "split_metadata.json": {"seed": 42},
    }
    for name in TRAINING_FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json.dumps(metadata[path.name]).encode() if path.name in metadata else b"approved fixture")
        files[name] = {"sha256": runtime.sha256(path), "bytes": path.stat().st_size}
    manifest = {"status": "finalized", "test_locked": True, "files": files,
                "processed": {"records": 4, "features": 2, "classes": 2, "schema_sha256": "fixture-schema"}}
    path = tmp_path / "artifacts/metadata/phase2/dataset_manifest.json"
    first = json.dumps(manifest).encode()
    second = json.dumps({**manifest, "environment": {"python": "another observed runtime"}}).encode()
    baseline = {"version": 1, "approved_manifest_sha256": [hashlib.sha256(b).hexdigest() for b in (first, second)],
                "processed": manifest["processed"], "files": files}
    original_open = Path.open
    def guard(path, *args, **kwargs):
        if path.name == "test.csv.gz":
            pytest.fail("Stage C must not open the test payload")
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guard)
    for payload in (first, second):
        path.write_bytes(payload)
        assert verify_training_inputs(OutputPaths(tmp_path), baseline=baseline)["manifest_sha256"] == hashlib.sha256(payload).hexdigest()
    corrupt = tmp_path / "data/processed/validation.csv.gz"
    corrupt.write_bytes(b"changed fixture")
    with pytest.raises(ValueError, match=r"file=.*validation.csv.gz; expected=[0-9a-f]+; actual=[0-9a-f]+"):
        verify_training_inputs(OutputPaths(tmp_path), baseline=baseline)
    path.write_bytes(first + b" ")
    with pytest.raises(ValueError, match="manifest checksum mismatch"):
        verify_training_inputs(OutputPaths(tmp_path), baseline=baseline)
