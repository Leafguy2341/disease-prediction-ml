"""Source/storage/output paths and optional Colab capabilities, with no side effects on import."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import uuid


class DriveUnavailableError(FileNotFoundError):
    """Drive has not been made available to this runtime."""


def project_root(start: str | Path | None = None, root_override: str | Path | None = None, *, search_roots: tuple = ()) -> Path:
    """Only os/Path are required: this function is embedded in notebook bootstraps."""
    override = root_override if root_override is not None else os.environ.get("DISEASE_PROJECT_ROOT")
    if override is not None:
        root = Path(override).expanduser().resolve()
        if (root / "configs/phase1.json").is_file():
            return root
        raise FileNotFoundError(
            f"PROJECT_ROOT/DISEASE_PROJECT_ROOT = {root}\n"
            "Thiếu configs/phase1.json. Cần thư mục có configs/, src/ và notebooks/. "
            "Dùng đường dẫn trên máy/runtime chạy kernel; ổ D: không có trực tiếp trên Linux."
        )
    current = Path(start if start is not None else Path.cwd()).expanduser().resolve()
    if current.is_file():
        current = current.parent
    for parent in (current, *current.parents):
        for candidate in (parent, parent / "disease-prediction-ml"):
            if (candidate / "configs/phase1.json").is_file():
                return candidate
    for value in search_roots:
        candidate = Path(value).expanduser().resolve()
        if (candidate / "configs/phase1.json").is_file():
            return candidate
    raise FileNotFoundError(
        f"Không tìm thấy configs/phase1.json; CWD={current}. "
        "Đặt PROJECT_ROOT hoặc DISEASE_PROJECT_ROOT tới bản mã nguồn có configs/, src/ và notebooks/. "
        "Trên runtime từ xa cần upload/giải nén/checkout cả mã nguồn, không chỉ file .ipynb. "
        "Nếu mã nguồn ở Drive, hãy mount Drive bằng giao diện được hỗ trợ trước."
        + (" Các vị trí source bổ sung đã kiểm tra: " + ", ".join(map(str, search_roots)) if search_roots else "")
        + " CSV trên Drive chưa cung cấp mã nguồn. Nếu chỉ có data/, đặt SOURCE_ARCHIVE tới ZIP source đã upload để giải nén source vào ổ runtime."
    )


@dataclass(frozen=True)
class RuntimeCapabilities:
    colab_runtime_detected: bool
    drive_api_available: bool


def detect_capabilities() -> RuntimeCapabilities:
    # A package installed in local Python does not prove this is a hosted Colab VM.
    detected = any(os.environ.get(key) for key in ("COLAB_RELEASE_TAG", "COLAB_BACKEND_VERSION", "COLAB_JUPYTER_IP"))
    ipython = sys.modules.get("IPython")
    if ipython and hasattr(ipython, "get_ipython"):
        shell = ipython.get_ipython()
        detected = detected or bool(shell and type(shell).__module__.startswith("google.colab."))
    try:
        available = importlib.util.find_spec("google.colab.drive") is not None
    except (ImportError, AttributeError, ValueError):
        available = False
    # API presence says nothing about whether this frontend can display OAuth.
    return RuntimeCapabilities(bool(detected), available)


def _path(value: str | Path, base: Path) -> Path:
    value = Path(value).expanduser()
    return (value if value.is_absolute() else base / value).resolve()


def runtime_settings(root: Path, config_file: str | Path | None = None) -> dict:
    default_file = root / "configs/runtime.json"
    if not default_file.is_file():
        raise FileNotFoundError(f"Thiếu {default_file}; cần đồng bộ cả configs/ và src/ lên runtime.")
    settings = json.loads(default_file.read_text(encoding="utf-8"))
    chosen = config_file if config_file is not None else os.environ.get("DISEASE_PATH_CONFIG")
    if chosen is not None:
        chosen = _path(chosen, root)
        if not chosen.is_file():
            raise FileNotFoundError(f"DISEASE_PATH_CONFIG/PATH_CONFIG không có: {chosen}")
        extra = json.loads(chosen.read_text(encoding="utf-8"))
        if not isinstance(extra, dict):
            raise ValueError("Runtime config phải là JSON object.")
        settings["colab"] = {**settings["colab"], **extra.get("colab", {})}
        settings.update({k: v for k, v in extra.items() if k != "colab"})
    return settings


def _boolean(value) -> bool:
    if isinstance(value, bool):
        return value
    if str(value).lower() in {"1", "true", "yes"}:
        return True
    if str(value).lower() in {"0", "false", "no"}:
        return False
    raise ValueError(f"Giá trị boolean không hợp lệ: {value!r}")


@dataclass(frozen=True)
class OutputPaths:
    root: Path
    run_id: str | None = None

    @property
    def processed_dir(self) -> Path:
        return self.root / "data/processed"

    @property
    def reports_dir(self) -> Path:
        base = self.root / "reports"
        return base / "runs" / self.run_id if self.run_id else base

    @property
    def tables_dir(self) -> Path:
        return self.reports_dir / "tables"

    @property
    def figures_dir(self) -> Path:
        return self.reports_dir / "figures"

    @property
    def metadata_dir(self) -> Path:
        base = self.root / "artifacts/metadata"
        return base / "runs" / self.run_id if self.run_id else base

    @property
    def models_dir(self) -> Path:
        return self.root / "artifacts/models"  # Reserved; Phase 1 never writes a model.


def output_paths(value: Path | OutputPaths) -> OutputPaths:
    """Keep legacy writer calls working; notebooks pass a fresh OutputPaths run."""
    return value if isinstance(value, OutputPaths) else OutputPaths(Path(value))


@dataclass(frozen=True)
class RuntimePaths:
    project_root: Path
    storage_root: Path
    raw_dir: Path
    output_root: Path
    runtime: str
    drive_mount: Path
    cache_dir: Path
    copy_raw_to_local: bool
    settings: dict

    @property
    def interim_dir(self) -> Path:
        # Heavy scratch work is local to the runtime; nothing creates it implicitly.
        return self.cache_dir.parent / "interim"

    def new_run(self, prefix: str = "phase1") -> OutputPaths:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", prefix):
            raise ValueError("Run prefix chỉ được chứa chữ, số, dấu _ và -.")
        run_id = f"{prefix}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}-{uuid.uuid4().hex[:8]}"
        output = OutputPaths(self.output_root, run_id)
        # New directories guarantee historical reports are not overwritten.
        output.reports_dir.mkdir(parents=True, exist_ok=False)
        output.metadata_dir.mkdir(parents=True, exist_ok=False)
        return output

    def as_dict(self) -> dict:
        names = ("project_root", "storage_root", "raw_dir", "output_root", "runtime", "drive_mount", "cache_dir", "copy_raw_to_local")
        return {name: str(getattr(self, name)) if isinstance(getattr(self, name), Path) else getattr(self, name) for name in names}


def resolve_paths(root: str | Path | None = None, *, config_file: str | Path | None = None) -> RuntimePaths:
    root = project_root(root_override=root) if root is not None else project_root()
    settings = runtime_settings(root, config_file)
    runtime = os.environ.get("DISEASE_RUNTIME", settings["runtime"]).lower()
    if runtime not in {"auto", "local", "colab", "remote"}:
        raise ValueError("DISEASE_RUNTIME phải là auto, local, colab hoặc remote.")
    if runtime == "auto":
        runtime = "colab" if detect_capabilities().colab_runtime_detected else "local"
    drive_mount = _path(os.environ.get("DISEASE_DRIVE_MOUNT", settings["colab"]["drive_mount"]), root)
    storage = os.environ.get("DISEASE_STORAGE_ROOT", settings.get("storage_root"))
    if storage is None and runtime == "colab":
        if not (drive_mount / "MyDrive").is_dir():
            raise DriveUnavailableError(
                f"Chưa thấy Google Drive tại {drive_mount / 'MyDrive'}. Không tự mount hoặc tạo Drive giả. "
                "Hãy dùng bước mount tùy chọn/giao diện extension nếu hỗ trợ; "
                "hoặc cấu hình DISEASE_STORAGE_ROOT và DISEASE_OUTPUT_DIR tới storage đã truy cập được."
            )
        storage_root = (drive_mount / settings["colab"]["project_relative"]).resolve()
    else:
        storage_root = _path(storage or ".", root)
    raw_dir = _path(os.environ.get("DISEASE_RAW_DIR", settings["raw_dir"]), storage_root)
    output_root = _path(os.environ.get("DISEASE_OUTPUT_DIR", settings.get("output_dir")) or ".", storage_root)
    cache_default = settings["colab"]["cache_dir"] if runtime == "colab" else settings["local_cache_dir"]
    cache_dir = _path(os.environ.get("DISEASE_CACHE_DIR", cache_default), root)
    copy_raw = _boolean(os.environ.get("DISEASE_COPY_RAW_TO_LOCAL", settings["copy_raw_to_local"]))
    if runtime in {"colab", "remote"} and any(p.is_relative_to(drive_mount) for p in (storage_root, raw_dir, output_root)):
        if not (drive_mount / "MyDrive").is_dir():
            raise DriveUnavailableError(f"Chưa truy cập được {drive_mount / 'MyDrive'}; mount Drive trước khi đọc/ghi, kể cả khi đã chỉ định output_dir.")
    if runtime == "colab":
        ephemeral = _path(settings["colab"]["ephemeral_root"], root)
        if output_root.is_relative_to(ephemeral) and not output_root.is_relative_to(drive_mount):
            raise ValueError("DISEASE_OUTPUT_DIR đang ở vùng /content tạm thời. Chọn Drive hoặc storage lưu lâu dài.")
        if copy_raw and cache_dir.is_relative_to(drive_mount):
            raise ValueError("Cache CSV phải ở ổ tạm runtime, không nằm trong Google Drive.")
    return RuntimePaths(root, storage_root, raw_dir, output_root, runtime, drive_mount, cache_dir, copy_raw, settings)


def mount_google_drive(root: str | Path | None = None, *, config_file: str | Path | None = None, timeout_ms: int = 60000) -> Path:
    """Explicit opt-in only. Never install google.colab or mount from local Python."""
    root = project_root(root_override=root) if root is not None else project_root()
    settings = runtime_settings(root, config_file)
    point = _path(os.environ.get("DISEASE_DRIVE_MOUNT", settings["colab"]["drive_mount"]), root)
    return mount_drive_at(point, timeout_ms=timeout_ms)


def mount_drive_at(mountpoint: str | Path, *, timeout_ms: int = 60000) -> Path:
    """Explicit mount without requiring any project source/config to be reachable yet."""
    point = Path(mountpoint).expanduser().resolve()
    capabilities = detect_capabilities()
    if not capabilities.colab_runtime_detected:
        raise RuntimeError("Kernel này chưa được nhận diện là Colab. Không gọi drive.mount trong local/generic remote Jupyter.")
    if (point / "MyDrive").is_dir():
        return point
    if not capabilities.drive_api_available:
        raise RuntimeError("Runtime không có API google.colab.drive. Dùng mount của extension nếu hỗ trợ hoặc storage đã đồng bộ; không cài google.colab vào local để giả lập.")
    try:
        drive = importlib.import_module("google.colab.drive")
        drive.mount(str(point), timeout_ms=timeout_ms)
    except Exception as exc:
        raise RuntimeError(
            "Drive mount thất bại; có API không đảm bảo frontend VS Code hỗ trợ xác thực. "
            "Dùng lệnh mount của extension nếu có, Colab browser, hoặc storage đã mount và cấu hình lại đường dẫn."
        ) from exc
    if not (point / "MyDrive").is_dir():
        raise DriveUnavailableError(f"API đã trả về nhưng chưa truy cập được {point / 'MyDrive'}.")
    return point
