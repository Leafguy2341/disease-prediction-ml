"""Colab/Drive preflight and a train/validation-only view of locked Phase 2."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

import numpy as np
import pandas as pd
import psutil
import sklearn

from src.data.loader import sha256_file
from src.data.paths import OutputPaths, RuntimePaths, detect_capabilities
from src.data.preprocessing import load_final_split

from src.data.integrity import META, TRAINING_FILES, verify_training_inputs

MODEL_NAMES = ("logistic_regression", "random_forest", "linear_svc", "knn", "bernoulli_nb")


def colab_project_paths(project_dir: str | Path, *, drive_mount: Path | None = None) -> RuntimePaths:
    """One explicit Drive folder supplies source, locked inputs and persistent outputs.

    Deliberately ignore legacy DISEASE_* environment/config path overrides here.
    Deprecated direct-folder API. Notebooks 00–03 use data.colab_runtime instead.
    """
    value = str(project_dir).strip()
    if value.startswith(("http://", "https://")):
        raise ValueError("DRIVE_PROJECT_DIR cần đường dẫn thư mục Drive đã mount, không phải URL chia sẻ.")
    root = Path(value).expanduser()
    if not value or not root.is_absolute():
        raise ValueError("DRIVE_PROJECT_DIR phải là đường dẫn đầy đủ tới thư mục project trên Drive đã mount.")
    if drive_mount is None:
        settings_file = root / "configs/runtime.json"
        if not settings_file.is_file():
            raise FileNotFoundError(f"Thiếu {settings_file}; dùng shared Colab bootstrap và đồng bộ source/config.")
        drive_mount = Path(json.loads(settings_file.read_text(encoding="utf-8"))["colab"]["drive_mount"])
    root, point = root.resolve(), drive_mount.resolve()
    if not root.is_relative_to(point) or root == point:
        raise ValueError("DRIVE_PROJECT_DIR phải nằm trong Google Drive đã mount, không phải ổ tạm hoặc thư mục local.")
    required = ("configs/runtime.json", "configs/phase3.json", "src/models/notebook.py")
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"DRIVE_PROJECT_DIR={root} thiếu: {', '.join(missing)}. "
            "Đặt cả folder code (src/, configs/, requirements-training.txt) cùng data/processed/ "
            "và artifacts/metadata/phase2/ ở thư mục này. Chỉ CSV hoặc notebook không đủ."
        )
    settings = json.loads((root / "configs/runtime.json").read_text(encoding="utf-8"))
    cache = Path(settings["colab"]["cache_dir"]).expanduser()
    ephemeral = Path(settings["colab"]["ephemeral_root"]).expanduser().resolve()
    if not cache.is_absolute() or not cache.resolve().is_relative_to(ephemeral) or cache.resolve().is_relative_to(point):
        raise ValueError("Cache trong configs/runtime.json phải ở ổ tạm Colab, bên ngoài Drive.")
    settings = {**settings, "runtime": "colab", "storage_root": str(root), "output_dir": str(root)}
    return RuntimePaths(project_root=root, storage_root=root, raw_dir=root / "data/raw", output_root=root,
                        runtime="colab", drive_mount=point, cache_dir=cache.resolve(),
                        copy_raw_to_local=False, settings=settings)


def read_training_config(root: Path) -> dict:
    config = json.loads((root / "configs/phase3.json").read_text(encoding="utf-8"))
    if (config["phase"] != 3 or config["seed"] != 42 or tuple(config["models"]) != MODEL_NAMES
            or config["selection_metric"] != "macro_f1" or config["zero_division"] != 0):
        raise ValueError("Phase 3 yêu cầu đúng 5 mô hình, seed 42, macro F1 và zero_division=0.")
    resource = config["resources"]
    if any(resource[k] <= 0 for k in ("max_workers", "blas_threads", "working_memory_mb", "prediction_batch_size")):
        raise ValueError("Giới hạn tài nguyên phải dương.")
    if not config["run_tag"] or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in config["run_tag"]):
        raise ValueError("run_tag chỉ dùng chữ, số, dấu - hoặc _.")
    return config


def runtime_snapshot() -> dict:
    vm = psutil.virtual_memory()
    cpu = platform.processor()
    info = Path("/proc/cpuinfo")
    if info.is_file():
        cpu = next((line.split(":", 1)[1].strip() for line in info.read_text().splitlines()
                    if line.startswith("model name")), cpu)
    gpu = []
    executable = shutil.which("nvidia-smi")
    if executable:
        try:
            result = subprocess.run([executable, "--query-gpu=name,memory.total", "--format=csv,noheader"],
                                    capture_output=True, text=True, timeout=10, check=False)
            gpu = result.stdout.strip().splitlines() if result.returncode == 0 else []
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {"python": platform.python_version(), "sklearn": sklearn.__version__,
            "numpy": np.__version__, "pandas": pd.__version__, "platform": platform.system(),
            "cpu": cpu, "logical_cpus": os.cpu_count(), "ram_total_gb": round(vm.total / 2**30, 3),
            "ram_available_gb": round(vm.available / 2**30, 3), "gpu": gpu,
            "gpu_used_by_estimators": False}


def colab_preflight(paths, config: dict) -> tuple[dict, dict]:
    """Legacy library adapter; current notebooks use shared A/B then independent Stage C."""
    capabilities = detect_capabilities()
    if (platform.system() != "Linux" or not capabilities.colab_runtime_detected
            or paths.runtime != "colab"):
        raise RuntimeError("COLAB NOT YET VERIFIED: chọn Select Kernel > Colab trong VS Code. Phase 3 không tự chuyển sang Python local.")
    my_drive = (paths.drive_mount / "MyDrive").resolve()
    if not my_drive.is_dir():
        raise FileNotFoundError("Drive chưa truy cập được. Chạy Colab: Mount Google Drive to Server... rồi preflight lại.")
    if not paths.output_root.resolve().is_relative_to(paths.drive_mount.resolve()):
        raise ValueError("Phase 3 yêu cầu output root persistent bên trong Google Drive đã mount.")
    if paths.cache_dir.resolve().is_relative_to(paths.drive_mount.resolve()):
        raise ValueError("Cache Phase 3 phải ở ổ tạm Colab, không nằm trên Drive.")
    import src
    if Path(src.__file__).resolve().parent != (paths.project_root / "src").resolve():
        raise RuntimeError("src đang cache từ checkout khác. Restart kernel sau khi đồng bộ source.")
    if not ((1, 5) <= tuple(int(p) for p in sklearn.__version__.split(".")[:2]) < (2, 0)):
        raise RuntimeError("Cần scikit-learn >=1.5,<2. Cài rõ bằng requirements-training.txt, restart kernel.")
    inputs = verify_training_inputs(OutputPaths(paths.output_root), config["expected_phase2"])
    env = runtime_snapshot()
    if env["ram_available_gb"] < config["resources"]["min_available_ram_gb"]:
        raise MemoryError("RAM khả dụng thấp hơn cấu hình Phase 3; chọn runtime có thêm RAM trước khi train.")
    folder = paths.output_root / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=folder, prefix=".runtime-rw-probe-", delete=False) as stream:
        probe = Path(stream.name)
        stream.write(b"phase3-drive-probe")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if sha256_file(probe) != hashlib.sha256(b"phase3-drive-probe").hexdigest():
            raise IOError("Drive read/write probe không khớp.")
    finally:
        probe.unlink()
    if probe.exists():
        raise IOError("Drive probe chưa được xóa; không báo thành công.")
    env.update({"runtime": "colab", "drive_read_write_verified": True,
                "source_root": str(paths.project_root), "output_root": str(paths.output_root),
                "test_payload_opened": False})
    return env, inputs


def cache_training_inputs(output: OutputPaths, cache_root: Path, inputs: dict) -> OutputPaths:
    """Copy only necessary compressed inputs once per manifest; no raw/test copy."""
    destination = cache_root / "phase3" / inputs["manifest_sha256"][:16]
    for relative in (*TRAINING_FILES, f"{META}/dataset_manifest.json"):
        source, target = output.root / relative, destination / relative
        expected = (inputs["manifest_sha256"] if relative.endswith("dataset_manifest.json")
                    else inputs["manifest"]["files"][relative]["sha256"])
        if target.is_file() and sha256_file(target) == expected:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".copy-", delete=False) as stream:
            pending = Path(stream.name)
        try:
            shutil.copyfile(source, pending)
            if sha256_file(pending) != expected:
                raise IOError(f"Checksum cache khác nguồn: {relative}")
            os.replace(pending, target)
        finally:
            pending.unlink(missing_ok=True)
    return OutputPaths(destination)


def load_training_data(output: OutputPaths, inputs: dict) -> dict:
    """Reuse the sole Phase 2 loader, with explicit train/validation calls only."""
    train = load_final_split(output, "train")
    validation = load_final_split(output, "validation")
    n_classes = len(inputs["labels"]["classes"])
    inventory = {row["split"]: row for row in inputs["splits"]["splits"]}
    for name, (x, y, groups) in (("train", train), ("validation", validation)):
        if (x.columns.tolist() != inputs["schema"]["features"]
                or len(x) != inventory[name]["dedup_records"] or len(x) != len(y) or len(y) != len(groups)
                or set(y.tolist()) != set(range(n_classes)) or not x.isin([0, 1]).all().all()
                or len(set(groups.tolist())) != inventory[name]["groups"]):
            raise ValueError(f"Schema, nhãn, groups hoặc kích thước {name} không khớp Phase 2.")
    if set(train[2].tolist()) & set(validation[2].tolist()):
        raise ValueError("Group overlap train/validation; dừng Phase 3.")
    return {"train": train, "validation": validation}


def phase3_resources(config: dict) -> dict:
    if not ((1, 5) <= tuple(int(p) for p in sklearn.__version__.split(".")[:2]) < (2, 0)):
        raise RuntimeError("Cần scikit-learn >=1.5,<2. Cài rõ bằng requirements-training.txt, restart kernel.")
    env = runtime_snapshot()
    if env["ram_available_gb"] < config["resources"]["min_available_ram_gb"]:
        raise MemoryError("RAM khả dụng thấp hơn cấu hình Phase 3; chọn runtime có thêm RAM trước khi train.")
    return env
