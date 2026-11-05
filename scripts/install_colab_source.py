"""DEPRECATED archive repair retained for history. Use the shared Drive source workflow."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
import uuid
import zipfile

PREFIX = "disease-prediction-ml/"
CONFIG_FILES = {"configs/runtime.json", "configs/phase3.json", "requirements-training.txt"}
REQUIRED = CONFIG_FILES | {
    "src/__init__.py", "src/data/loader.py", "src/data/paths.py", "src/data/preprocessing.py",
    "src/models/notebook.py", "src/models/runtime.py", "src/models/training.py", "src/models/reporting.py",
}


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".source-", delete=False) as stream:
        pending = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def install_source(archive: Path, project_dir: Path) -> dict:
    """Validate all source first; update .py files with backups, keep existing config."""
    root = Path(project_dir).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Project chưa tồn tại: {root}. Kiểm tra DRIVE_PROJECT_DIR và mount Drive.")
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Source archive có tên file trùng.")
        manifest = json.loads(package.read(PREFIX + "bundle_manifest.json"))
        for name in names:
            parts = PurePosixPath(name).parts
            if "\\" in name or ".." in parts or ":" in name or PurePosixPath(name).is_absolute():
                raise ValueError(f"Đường dẫn không hợp lệ trong source archive: {name}")
        selected = {name for name in manifest if
                    (name.startswith("src/") and name.endswith(".py")) or name in CONFIG_FILES}
        if not REQUIRED.issubset(selected):
            raise ValueError("Source archive thiếu Phase 3: " + ", ".join(sorted(REQUIRED - selected)))
        payloads = {}
        for relative in sorted(selected):
            payload = package.read(PREFIX + relative)
            if _digest(payload) != manifest[relative]:
                raise ValueError(f"Checksum source không khớp: {relative}")
            target = root
            for part in PurePosixPath(relative).parts:
                target = target / part
                if target.is_symlink():
                    raise ValueError(f"Không ghi qua symlink source/config: {target}")
            if not target.resolve().is_relative_to(root):
                raise ValueError(f"Source target nằm ngoài project: {relative}")
            if target.exists() and not target.is_file():
                raise ValueError(f"Source target không phải file: {target}")
            payloads[relative] = payload
    # All archive/path checks pass before any target is written.
    backup = None
    report = {"project_dir": str(root), "installed": [], "unchanged": [], "preserved_config": [], "backup_dir": None}
    for relative, payload in payloads.items():
        target = root / relative
        old = target.read_bytes() if target.is_file() else None
        if old == payload:
            report["unchanged"].append(relative)
            continue
        if old is not None and relative in CONFIG_FILES:
            report["preserved_config"].append(relative)
            continue
        if old is not None:
            if backup is None:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                backup = root / "artifacts/backups" / f"colab-source-{stamp}-{uuid.uuid4().hex[:8]}"
                if not backup.resolve().is_relative_to(root):
                    raise ValueError("Thư mục backup source nằm ngoài project.")
            _atomic_write(backup / relative, old)
        _atomic_write(target, payload)
        if _digest(target.read_bytes()) != _digest(payload):
            raise IOError(f"Checksum sau ghi source không khớp: {relative}")
        report["installed"].append(relative)
    report["backup_dir"] = str(backup) if backup else None
    return report


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Bổ sung source Phase 3 vào project Drive; giữ nguyên dữ liệu/config hiện có.")
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args()
    root = Path(args.project_dir).expanduser().resolve()
    drive = Path("/content/drive").resolve()
    if sys.platform != "linux" or not (drive / "MyDrive").is_dir() or not root.is_relative_to(drive):
        parser.error("Chạy file .pyz trên Colab sau khi mount Drive, với --project-dir nằm trong Drive.")
    try:
        report = install_source(Path(sys.argv[0]).resolve(), root)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f"Không cập nhật source: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    print("Source đã sẵn sàng. Restart kernel rồi Run All notebook 03. Dữ liệu và artifact Phase 2 giữ nguyên.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
