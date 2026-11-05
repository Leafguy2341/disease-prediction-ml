"""Regression: Drive/source must be available before any project-root-dependent import."""
import ast
import builtins
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from src.data import bootstrap as module
from src.data.bootstrap import bootstrap_project, resolve_source_archive, unpack_source_archive
from src.data.paths import project_root


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    for name in ("DISEASE_PROJECT_ROOT", "DISEASE_DRIVE_MOUNT", "DISEASE_DRIVE_PROJECT"):
        monkeypatch.delenv(name, raising=False)
    content = tmp_path / "content"
    content.mkdir()
    monkeypatch.chdir(content)
    defaults = {"drive_mount": str(content / "drive"), "project_relative": "MyDrive/ML_Projects/disease-prediction-ml"}
    drive_project = Path(defaults["drive_mount"]) / defaults["project_relative"]
    return content, defaults, drive_project


def bundle_at(path, *, corrupt=False, extra=None):
    files = {"configs/phase1.json": "{}", "configs/runtime.json": "{}",
             "src/data/paths.py": "# source paths\n", "src/data/audit.py": "# audit source\n",
             "notebooks/00_dataset_audit.ipynb": "{}"}
    manifest = {name: hashlib.sha256(value.encode()).hexdigest() for name, value in files.items()}
    if corrupt:
        manifest["src/data/audit.py"] = "incorrect"
    with zipfile.ZipFile(path, "w") as package:
        for name, value in files.items():
            package.writestr("disease-prediction-ml/" + name, value)
        package.writestr("disease-prediction-ml/bundle_manifest.json", json.dumps(manifest))
        if extra:
            package.writestr(extra, "unexpected entry")
    return path


def source_marker(root):
    (root / "configs").mkdir(parents=True)
    (root / "configs/phase1.json").write_text("{}", encoding="utf-8")


def test_mount_is_called_before_root_lookup(runtime, monkeypatch):
    content, defaults, source = runtime
    order = []
    def mount(point):
        order.append("mount")
        source_marker(source)
    def lookup(**kwargs):
        order.append("root")
        return project_root(**kwargs)
    monkeypatch.setattr(module, "mount_drive_at", mount)
    monkeypatch.setattr(module, "project_root", lookup)
    assert bootstrap_project(defaults, mount_requested=True) == source
    assert order == ["mount", "root"]


def test_archive_uploaded_to_drive_is_found_by_its_exact_name(runtime, monkeypatch):
    content, defaults, project = runtime
    project.mkdir(parents=True)
    archive = bundle_at(project / "uploaded-source.zip")
    monkeypatch.setattr(module, "mount_drive_at", lambda _: pytest.fail("Never mount implicitly"))
    resolved = resolve_source_archive(content / archive.name, search_roots=(project,), drive_mount=defaults["drive_mount"])
    assert resolved == archive
    assert not (content / "disease-prediction-ml").exists()  # Discovery does not extract or copy files.


def test_misnamed_archive_lists_actual_drive_zip_without_selecting_another_version(runtime):
    content, defaults, project = runtime
    project.mkdir(parents=True)
    archive = bundle_at(project / "source-new-version.zip")
    with pytest.raises(FileNotFoundError) as exc:
        resolve_source_archive(content / "source-old-version.zip", search_roots=(project,), drive_mount=defaults["drive_mount"])
    message = str(exc.value)
    assert f"SOURCE_ARCHIVE = {str(archive)!r}" in message
    assert "Drive đang truy cập được" in message
    assert "Thư mục đã kiểm tra" in message
    assert not (content / "disease-prediction-ml").exists()


def test_missing_drive_explains_upload_is_not_a_mount(runtime):
    content, defaults, _ = runtime
    with pytest.raises(FileNotFoundError) as exc:
        resolve_source_archive(content / "source.zip", drive_mount=defaults["drive_mount"])
    message = str(exc.value)
    assert "Kernel chưa truy cập được Drive" in message
    assert str(Path(defaults["drive_mount"]) / "MyDrive") in message
    assert "Không thấy ZIP" in message


def test_same_named_drive_archives_require_explicit_selection(runtime):
    content, defaults, project = runtime
    project.mkdir(parents=True)
    first = bundle_at(project / "source.zip")
    second = bundle_at(project.parent / "source.zip")
    with pytest.raises(FileNotFoundError, match="nhiều ZIP cùng tên") as exc:
        resolve_source_archive(content / "source.zip", search_roots=(project, project.parent), drive_mount=defaults["drive_mount"])
    assert f"SOURCE_ARCHIVE = {str(first)!r}" in str(exc.value)
    assert f"SOURCE_ARCHIVE = {str(second)!r}" in str(exc.value)
    assert resolve_source_archive(first, search_roots=(project.parent,)) == first


def test_already_accessible_drive_source_is_found_without_mount(runtime, monkeypatch):
    content, defaults, source = runtime
    source_marker(source)
    monkeypatch.setattr(module, "mount_drive_at", lambda _: pytest.fail("Must not mount implicitly"))
    assert bootstrap_project(defaults) == source


def test_csv_on_drive_does_not_fabricate_source(runtime, monkeypatch):
    content, defaults, source = runtime
    def mount(point):
        raw = source / "data/raw"
        raw.mkdir(parents=True)
        (raw / "actual dataset.csv").write_text("diseases,a\nA,1\n", encoding="utf-8")
    monkeypatch.setattr(module, "mount_drive_at", mount)
    with pytest.raises(FileNotFoundError, match="SOURCE_ARCHIVE"):
        bootstrap_project(defaults, mount_requested=True)
    assert not (source / "configs").exists()


def test_explicit_archive_unpacks_without_needing_src_or_drive(runtime, monkeypatch):
    content, defaults, drive_source = runtime
    archive = bundle_at(content / "project-source.zip")
    monkeypatch.setattr(module, "mount_drive_at", lambda _: pytest.fail("Must not mount implicitly"))
    root = bootstrap_project(defaults, source_archive=archive)
    assert root == content / "disease-prediction-ml"
    assert (root / "src/data/audit.py").is_file()


def test_archive_reuse_keeps_notebook_outputs_and_user_code(runtime):
    content, _, _ = runtime
    archive = bundle_at(content / "source.zip")
    root = unpack_source_archive(archive)
    notebook = root / "notebooks/00_dataset_audit.ipynb"
    notebook.write_text("user notebook outputs", encoding="utf-8")
    assert unpack_source_archive(archive) == root
    assert notebook.read_text(encoding="utf-8") == "user notebook outputs"
    code = root / "src/data/audit.py"
    code.write_text("user code edit", encoding="utf-8")
    with pytest.raises(FileExistsError, match="Không ghi đè"):
        unpack_source_archive(archive)
    assert code.read_text(encoding="utf-8") == "user code edit"


@pytest.mark.parametrize("bad_name", ["../outside.txt", "disease-prediction-ml/../../outside.txt", "/absolute.txt"])
def test_unsafe_archive_paths_are_rejected_before_extraction(runtime, bad_name):
    content, _, _ = runtime
    archive = bundle_at(content / "source.zip", extra=bad_name)
    with pytest.raises(ValueError, match="Đường dẫn"):
        unpack_source_archive(archive)
    assert not (content / "disease-prediction-ml").exists()


def test_corrupt_archive_is_rejected_before_extraction(runtime):
    content, _, _ = runtime
    archive = bundle_at(content / "source.zip", corrupt=True)
    with pytest.raises(ValueError, match="checksum"):
        unpack_source_archive(archive)
    assert not (content / "disease-prediction-ml").exists()


def test_csv_zip_cannot_replace_project_source(runtime):
    content, _, _ = runtime
    archive = content / "only-data.zip"
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("actual dataset.csv", "diseases,a\nA,1\n")
    with pytest.raises(ValueError, match="ZIP dữ liệu"):
        unpack_source_archive(archive)


def test_embedded_bootstrap_works_before_src_import_is_possible(runtime, monkeypatch):
    content, _, _ = runtime
    repo = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo / "scripts"))
    from build_notebooks import BOOTSTRAP
    archive = bundle_at(content / "source.zip")
    source = BOOTSTRAP.split("if str(ROOT) not in sys.path:", 1)[0]
    source = source.replace("SOURCE_ARCHIVE = None", "SOURCE_ARCHIVE = " + repr(str(archive)), 1)
    importer = builtins.__import__
    def no_src(name, *args, **kwargs):
        if name == "src" or name.startswith("src.") or name in {"pandas", "numpy"}:
            pytest.fail("Pre-root bootstrap must require only the standard library")
        return importer(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_src)
    namespace = {}
    exec(compile(source, "standalone_bootstrap", "exec"), namespace)
    assert namespace["ROOT"] == content / "disease-prediction-ml"


def test_next_notebook_finds_extracted_source_without_reconfiguring_archive(runtime):
    content, defaults, _ = runtime
    archive = bundle_at(content / "source.zip")
    first = bootstrap_project(defaults, source_archive=archive)
    assert bootstrap_project(defaults) == first


def test_updater_preserves_user_mount_and_path_settings(runtime, monkeypatch):
    repo = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo / "scripts"))
    from update_notebook_setup import preserve_settings
    from build_notebooks import BOOTSTRAP
    old = 'PROJECT_ROOT = None\nPATH_CONFIG = "custom.json"\nMOUNT_DRIVE = True\nSOURCE_ARCHIVE = "chosen.zip"\n'
    updated = preserve_settings(old, BOOTSTRAP)
    assignments = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(updated).body
                   if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                   and n.targets[0].id in {"PROJECT_ROOT", "PATH_CONFIG", "MOUNT_DRIVE", "SOURCE_ARCHIVE", "SOURCE_DIRECTORY"}}
    assert assignments == {"PROJECT_ROOT": None, "PATH_CONFIG": "custom.json", "MOUNT_DRIVE": True,
                           "SOURCE_ARCHIVE": "chosen.zip", "SOURCE_DIRECTORY": None}
