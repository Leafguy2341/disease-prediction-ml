"""Single Drive -> ephemeral-workspace bootstrap; dataset integrity is a separate stage."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import sys
import tempfile
from types import SimpleNamespace

PUBLIC_CONFIGS = {"runtime.json", "phase1.json", "phase2.json", "phase3.json",
                  "phase5b.json", "handover_data_requirements.json",
                  "dataset_source.json", "phase2_integrity.json"}
REQUIREMENTS = {"requirements-notebooks.txt", "requirements-training.txt"}
RUNTIME_SCRIPTS = {"scripts/audit_phase3_results.py", "scripts/audit_post_tuning.py",
                   "scripts/audit_final_ml_gaps.py", "scripts/package_handover.py"}
COMMON_REQUIRED = {
    "src/__init__.py", "src/data/__init__.py", "src/data/colab_runtime.py",
    "src/data/paths.py", "src/data/loader.py", "src/data/io.py",
    "src/data/audit.py", "src/data/eda.py", "src/data/reporting.py",
    "src/evaluation/__init__.py", "src/evaluation/plots.py", "src/evaluation/report.py",
    "configs/runtime.json", "configs/phase1.json", "configs/dataset_source.json",
}
OWNED = ".colab-runtime-owned"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_fingerprint(files: dict) -> str:
    """Only .py files in one source tree; configuration cannot create a self pin."""
    names = sorted(n for n in files if n.startswith("src/") and n.endswith(".py"))
    return hashlib.sha256("".join(f"{n}\0{files[n]}\n" for n in names).encode()).hexdigest()


def is_colab() -> bool:
    ipython = sys.modules.get("IPython")
    shell = ipython.get_ipython() if ipython and hasattr(ipython, "get_ipython") else None
    return platform.system() == "Linux" and (
        any(os.environ.get(k) for k in ("COLAB_RELEASE_TAG", "COLAB_BACKEND_VERSION", "COLAB_JUPYTER_IP"))
        or bool(shell and type(shell).__module__.startswith("google.colab.")))


def canonical_paths(settings: dict) -> tuple[Path, Path, Path, Path, Path]:
    colab = settings["colab"]
    point, ephemeral = (Path(colab[k]).expanduser() for k in ("drive_mount", "ephemeral_root"))
    relative = PurePosixPath(colab["project_relative"])
    cache, workspace = (Path(colab[k]).expanduser() for k in ("cache_dir", "runtime_workspace"))
    if (any(not p.is_absolute() for p in (point, ephemeral, cache, workspace))
            or relative.is_absolute() or ".." in relative.parts
            or not relative.parts or relative.parts[0] != "MyDrive"):
        raise ValueError("configs/runtime.json: mount/workspace/cache phải tuyệt đối; project_relative phải ở MyDrive/.")
    point, ephemeral, cache, workspace = (p.resolve() for p in (point, ephemeral, cache, workspace))
    root = (point / str(relative)).resolve()
    if root == point or not root.is_relative_to(point):
        raise ValueError("Canonical root phải ở trong Drive đã mount.")
    for name, value in (("workspace", workspace), ("cache", cache)):
        if value == ephemeral or not value.is_relative_to(ephemeral) or value.is_relative_to(point):
            raise ValueError(f"{name} phải ở ổ tạm runtime, ngoài Drive.")
    if cache.is_relative_to(workspace) or workspace.is_relative_to(cache):
        raise ValueError("Source workspace và cache dữ liệu phải là hai thư mục riêng.")
    if settings.get("storage_root") not in (None, ".") or settings.get("output_dir") not in (None, "."):
        raise ValueError("Storage/output phải cùng canonical Drive root.")
    for key in ("raw_dir", "raw_dataset"):
        value = settings.get(key)
        if value is not None and (Path(value).is_absolute() or ".." in PurePosixPath(value).parts
                                  or not (root / value).resolve().is_relative_to(root)):
            raise ValueError(f"{key} phải tương đối trong canonical root.")
    return point, root, cache, workspace, ephemeral


def write_probe(folder: Path) -> None:
    """Write/read/hash/delete a tiny file, leaving no permanent marker."""
    with tempfile.TemporaryDirectory(dir=folder, prefix=".runtime-probe-") as temporary:
        path = Path(temporary) / "probe"
        payload = b"disease-prediction-runtime-check"
        path.write_bytes(payload)
        if sha256(path) != hashlib.sha256(payload).hexdigest():
            raise IOError(f"Write/read checksum failed: {path}")
    if Path(temporary).exists():
        raise IOError(f"Probe cleanup failed: {temporary}")


def _collect_source(root: Path, phase: int) -> tuple[dict, dict]:
    required = set(COMMON_REQUIRED)
    if phase >= 2:
        required |= {"src/data/preprocessing.py", "src/data/preprocessing_inspection.py", "configs/phase2.json"}
    if phase == 3:
        required |= {"src/models/__init__.py", "src/models/runtime.py", "src/models/notebook.py",
                     "src/models/training.py", "src/models/reporting.py", "configs/phase3.json",
                     "requirements-training.txt"}
    missing = sorted(n for n in required if not (root / n).is_file())
    if missing:
        raise FileNotFoundError(f"Source Drive chưa đủ tại {root}: {', '.join(missing)}. Đồng bộ src/ và configs/; không dùng archive/session package.")
    paths = {p.relative_to(root).as_posix(): p for p in (root / "src").rglob("*.py")
             if "__pycache__" not in p.parts}
    paths.update({f"configs/{n}": root / "configs" / n for n in PUBLIC_CONFIGS if (root / "configs" / n).is_file()})
    paths.update({n: root / n for n in REQUIREMENTS if (root / n).is_file()})
    for name in RUNTIME_SCRIPTS:
        if not (root / name).is_file():
            raise FileNotFoundError(f"Missing runtime helper {name}; publish the complete source payload, not individual files.")
        paths[name] = root / name
    for name in PUBLIC_CONFIGS:
        if not (root / "configs" / name).is_file():
            raise FileNotFoundError(f"Missing public config: configs/{name}; publish the complete source payload.")
    payloads = {}
    for name, path in paths.items():
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"Source file trỏ ra ngoài canonical root: {name}")
        payload = path.read_bytes()
        if name.endswith(".py"):
            compile(payload, str(path), "exec")  # Syntax check only, never execute source here.
        payloads[name] = payload
    return payloads, {n: hashlib.sha256(b).hexdigest() for n, b in payloads.items()}


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()


def _base_settings(settings):
    return {k: v for k, v in settings.items() if k not in {"runtime_publication", "expected_source_fingerprint"}}


def make_publication(root: Path) -> tuple[dict, dict]:
    """Standard-library-only staging API. Reads source/config/scripts, never data."""
    root = Path(root).resolve()
    payloads, hashes = _collect_source(root, 3)
    base = _base_settings(json.loads(payloads["configs/runtime.json"].decode("utf-8-sig")))
    files = {n: {"sha256": hashes[n], "bytes": len(b)} for n, b in payloads.items() if n != "configs/runtime.json"}
    descriptor = {"version": 1, "settings": base, "files": files}
    digest = hashlib.sha256(_canonical(descriptor)).hexdigest()
    settings = {**base, "expected_source_fingerprint": source_fingerprint(hashes),
                "runtime_publication": {"version": 1, "files": files, "sha256": digest}}
    payloads["configs/runtime.json"] = (json.dumps(settings, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    return payloads, settings["runtime_publication"]


def read_source(root: Path, phase: int, *, expected_payload_sha256: str | None = None) -> tuple[dict, dict]:
    """Verify the exact published closure. No Phase 2 payloads or receipts."""
    payloads, hashes = _collect_source(Path(root), phase)
    settings = json.loads(payloads["configs/runtime.json"].decode("utf-8-sig"))
    publication = settings.get("runtime_publication", {})
    files = {n: {"sha256": hashes[n], "bytes": len(b)} for n, b in payloads.items() if n != "configs/runtime.json"}
    descriptor = {"version": 1, "settings": _base_settings(settings), "files": files}
    actual = hashlib.sha256(_canonical(descriptor)).hexdigest()
    if publication.get("version") != 1 or publication.get("files") != files or publication.get("sha256") != actual:
        raise ValueError("SOURCE RELEASE MISMATCH: incomplete/mixed source publication. Run prepare_colab_source.ps1 -Publish, wait for cloud sync, then Restart Kernel.")
    if expected_payload_sha256 is not None and actual != expected_payload_sha256:
        raise ValueError(f"STALE SOURCE RELEASE: expected local={expected_payload_sha256}; Drive={actual}; wait for cloud sync. No data/model was loaded.")
    return payloads, hashes


def copy_source(workspace: Path, payloads: dict, hashes: dict) -> None:
    """Refresh only an owned ephemeral workspace, never replace loaded Python code."""
    loaded = [(n, m) for n, m in list(sys.modules.items()) if n == "src" or n.startswith("src.")]
    fingerprint = source_fingerprint(hashes)
    same = workspace.is_dir() and all((workspace / n).is_file() and sha256(workspace / n) == h for n, h in hashes.items())
    if same:
        actual = {p.relative_to(workspace).as_posix() for p in (workspace / "src").rglob("*.py")}
        same = actual == {n for n in hashes if n.startswith("src/")}
    if loaded:
        expected = (workspace / "src").resolve()
        for name, module in loaded:
            location = getattr(module, "__file__", None)
            if not location or not Path(location).resolve().is_relative_to(expected):
                raise RuntimeError(f"Module {name} đã nạp từ source khác. Restart Kernel rồi chạy setup.")
        if not same or getattr(sys.modules.get("src"), "_colab_source_fingerprint", None) != fingerprint:
            raise RuntimeError(f"Source/config đã đổi trên Drive (source={fingerprint}). Restart Kernel trước khi đồng bộ workspace.")
    if same:
        return
    if workspace.exists() and not (workspace / OWNED).is_file():
        raise FileExistsError(f"Workspace chưa được đánh dấu là cache dự án: {workspace}. Không ghi đè file người dùng.")
    workspace.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=workspace.parent, prefix=".source-") as temporary:
        stage = Path(temporary) / "project"
        stage.mkdir()
        (stage / OWNED).write_text("Ephemeral source only; do not store datasets or outputs here.\n", encoding="utf-8")
        for name, payload in payloads.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            if sha256(target) != hashes[name]:
                raise IOError(f"Source copy checksum failed: {name}")
        if workspace.exists():
            # Workspace is outside Drive, owned by this bootstrap, and no src modules are loaded.
            workspace.rename(Path(temporary) / "previous")
        stage.rename(workspace)


def bootstrap_runtime(project_root: str | Path, *, phase: int = 1, expected_payload_sha256: str | None = None):
    """Stage A/B only. It does not read a Phase 2 manifest, source receipt or dataset."""
    if not is_colab():
        raise RuntimeError("Chọn Google Colab kernel chính thức; notebook không tự dùng .venv/local Python.")
    if phase not in (1, 2, 3):
        raise ValueError("phase phải là 1, 2 hoặc 3.")
    if not isinstance(expected_payload_sha256, str) or len(expected_payload_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_payload_sha256):
        raise ValueError("Paste the 64-character RUNTIME_PAYLOAD_SHA256 printed by local Publish into EXPECTED_RUNTIME_PAYLOAD before bootstrap. Do not derive it from Drive.")
    root = Path(project_root).expanduser().resolve()
    config = root / "configs/runtime.json"
    if not config.is_file():
        raise FileNotFoundError(f"Thiếu {config}. Mount Drive và kiểm tra đúng canonical root/src/configs.")
    settings = json.loads(config.read_text(encoding="utf-8-sig"))
    point, canonical, cache, workspace, ephemeral = canonical_paths(settings)
    if not ephemeral.is_dir():
        raise FileNotFoundError(f"Không có ổ runtime Colab: {ephemeral}")
    if not (point / "MyDrive").is_dir():
        raise FileNotFoundError(f"Drive chưa mount tại {point}. Chạy Colab: Mount Google Drive to Server... và cell mount.")
    if root != canonical:
        raise ValueError(f"Drive root sai: đang dùng {root}; configs/runtime.json khai báo {canonical}.")
    payloads, hashes = read_source(root, phase, expected_payload_sha256=expected_payload_sha256)
    write_probe(ephemeral)
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    write_probe(reports)
    stages = {"A": "PASS"}
    print(f"Stage A PASS | Colab Python {platform.python_version()} | Drive={root} | runtime/Drive read-write OK", flush=True)
    fingerprint = source_fingerprint(hashes)
    pinned = settings.get("expected_source_fingerprint")
    if pinned and pinned != fingerprint:
        raise ValueError(f"Source revision không khớp pin khai báo trong runtime.json: expected={pinned}; actual={fingerprint}; tree={root / 'src'}")
    copy_source(workspace, payloads, hashes)
    if str(workspace) in sys.path:
        sys.path.remove(str(workspace))
    sys.path.insert(0, str(workspace))
    importlib.invalidate_caches()
    try:
        from src.data.paths import RuntimePaths
        import src
        import src.data.loader
        if phase >= 2:
            import src.data.preprocessing
        if phase == 3:
            import src.models.notebook  # Definitions only; no fit/model construction.
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(f"Thiếu module {exc.name}. Source ở {workspace}; nếu là dependency, cài chủ động requirements-notebooks.txt/requirements-training.txt rồi Restart Kernel.") from exc
    src._colab_source_fingerprint = fingerprint
    settings = {**settings, "canonical_colab": True}
    paths = RuntimePaths(workspace, root, root / settings["raw_dir"], root, "colab", point, cache,
                         bool(settings.get("copy_raw_to_local", False)), settings)
    stages["B"] = "PASS"
    print(f"Stage B PASS | imports={workspace} | source fingerprint={fingerprint}", flush=True)
    print(f"Runtime payload verified: {expected_payload_sha256} | {len(payloads)} files (source/config/scripts only)", flush=True)
    return SimpleNamespace(paths=paths, source_fingerprint=fingerprint, payload_sha256=expected_payload_sha256, stages=stages, inputs=None,
                           environment={"runtime": "colab", "python": platform.python_version(),
                                        "drive_read_write_verified": True, "source_root": str(workspace),
                                        "output_root": str(root), "test_payload_opened": False})


def phase2_preflight(runtime) -> dict:
    """Stage C: independent approved data baseline, never source/session receipts."""
    from src.data.integrity import read_baseline, verify_training_inputs
    from src.data.paths import OutputPaths
    try:
        baseline = read_baseline(runtime.paths.project_root / "configs/phase2_integrity.json")
        runtime.inputs = verify_training_inputs(OutputPaths(runtime.paths.storage_root), baseline=baseline)
    except (OSError, ValueError):
        runtime.stages["C"] = "FAIL"
        print("Stage C FAIL | Stage A/B vẫn PASS; xem file/hash cụ thể trong lỗi.", flush=True)
        raise
    runtime.stages["C"] = "PASS"
    print(f"Stage C PASS | manifest={runtime.inputs['manifest_sha256']} | 7 train/validation/metadata checksums OK", flush=True)
    return runtime.inputs


def smoke_test(runtime) -> dict:
    from src.data.paths import OutputPaths
    from src.models.runtime import cache_training_inputs, load_training_data
    inputs = runtime.inputs or phase2_preflight(runtime)
    cached = cache_training_inputs(OutputPaths(runtime.paths.storage_root), runtime.paths.cache_dir, inputs)
    data = load_training_data(cached, inputs)
    dimensions = {n: {"records": len(x), "features": x.shape[1], "classes": len(set(y.tolist())),
                      "groups": len(set(g.tolist()))} for n, (x, y, g) in data.items()}
    result = {"runtime": runtime.paths.runtime, "stages": dict(runtime.stages),
              "source_fingerprint": runtime.source_fingerprint, "source_root": str(runtime.paths.project_root),
              "storage_root": str(runtime.paths.storage_root), "inputs": dimensions,
              "schema_order_and_encoding": True, "drive_write_read_checksum_delete": True,
              "test_payload_opened": False, "models_trained": 0}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result
