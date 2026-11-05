"""DEPRECATED archive/CWD bootstrap, retained for history and legacy callers only.

Notebooks 00–03 now use src/data/colab_runtime.py and canonical Drive source.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import zipfile

from .paths import mount_drive_at, project_root


def resolve_source_archive(source_archive: str | Path, *, search_roots: tuple = (),
                           drive_mount: str | Path | None = None) -> Path:
    """Find an explicitly named ZIP in visible runtime folders; never change its name."""
    requested = Path(source_archive).expanduser().resolve()
    if requested.is_file():
        return requested
    directories = dict.fromkeys(Path(p).expanduser().resolve() for p in
                                (requested.parent, Path.cwd(), *search_roots))
    candidates, unavailable = set(), []
    for directory in directories:
        try:
            if directory.is_dir():
                candidates.update(p.resolve() for p in directory.iterdir()
                                  if p.is_file() and p.suffix.lower() == ".zip")
        except OSError:
            unavailable.append(str(directory))
    matching = sorted(p for p in candidates if p.name == requested.name)
    if len(matching) == 1:
        print(f"ZIP cùng tên được tìm thấy trên runtime: {matching[0]}", flush=True)
        return matching[0]
    details = [f"Không tìm thấy ZIP tại SOURCE_ARCHIVE={str(requested)!r}.",
               f"Kernel hiện tại: CWD={Path.cwd()}."]
    if len(matching) > 1:
        details.append("Có nhiều ZIP cùng tên; đặt SOURCE_ARCHIVE tới đường dẫn đầy đủ để chọn đúng file.")
    if drive_mount is not None:
        my_drive = Path(drive_mount).expanduser().resolve() / "MyDrive"
        if my_drive.is_dir():
            details.append(f"Drive đang truy cập được tại {my_drive}. ZIP trên Drive không tự nằm trực tiếp trong /content/.")
        else:
            details.append(f"Kernel chưa truy cập được Drive tại {my_drive}. Upload lên Google Drive chưa làm file xuất hiện trong runtime. "
                           "Kết nối/mount Drive bằng giao diện được hỗ trợ trước; VS Code không bảo đảm hỗ trợ xác thực drive.mount.")
    if candidates:
        details.append("Các ZIP thực sự nhìn thấy (chép đúng dòng SOURCE_ARCHIVE vào cell cấu hình):")
        details.extend(f"SOURCE_ARCHIVE = {str(p)!r}" for p in sorted(candidates)[:20])
        if len(candidates) > 20:
            details.append(f"Còn {len(candidates) - 20} ZIP khác; kiểm tra thư mục đã upload.")
    else:
        details.append("Không thấy ZIP trong các thư mục đã kiểm tra. Dùng đường dẫn đầy đủ của file trên Drive đã kết nối hoặc upload ZIP vào kernel hiện tại.")
    details.append("Thư mục đã kiểm tra: " + ", ".join(str(p) for p in directories))
    if unavailable:
        details.append("Không đọc được: " + ", ".join(unavailable))
    raise FileNotFoundError("\n".join(details))


def unpack_source_archive(source_archive: str | Path, source_directory: str | Path | None = None, *, required_files: tuple = ()) -> Path:
    """Unpack an explicitly selected project bundle; never overwrite existing source."""
    archive = Path(source_archive).expanduser().resolve()
    if not archive.is_file():
        raise FileNotFoundError(f"SOURCE_ARCHIVE không có: {archive}. Upload ZIP source lên runtime/Drive và dùng đường dẫn thực.")
    destination = Path(source_directory).expanduser().resolve() if source_directory is not None else Path.cwd()
    target = destination / "disease-prediction-ml"
    prefix = "disease-prediction-ml/"
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        required = {prefix + name for name in ["configs/phase1.json", "configs/runtime.json", "src/data/paths.py", "src/data/audit.py", *required_files]}
        if not required.issubset(names):
            missing = ", ".join(sorted(name.removeprefix(prefix) for name in required - names))
            raise ValueError(f"ZIP source cũ/thiếu file: {missing}. Dùng ZIP mới do scripts/package_colab.py tạo; ZIP dữ liệu CSV không thay thế source.")
        for name in names:
            parts = PurePosixPath(name).parts
            if not name.startswith(prefix) or "\\" in name or ".." in parts or ":" in name or PurePosixPath(name).is_absolute():
                raise ValueError(f"Đường dẫn không hợp lệ trong ZIP source: {name}")
        manifest_name = prefix + "bundle_manifest.json"
        manifest = json.loads(bundle.read(manifest_name)) if manifest_name in names else {}
        for relative, digest in manifest.items():
            if prefix + relative not in names or hashlib.sha256(bundle.read(prefix + relative)).hexdigest() != digest:
                raise ValueError(f"ZIP source sai checksum: {relative}")
        if target.exists():
            # Reruns may reuse identical code, while notebooks can have new outputs.
            code = {k: v for k, v in manifest.items() if k.startswith(("src/", "configs/", "scripts/"))}
            if code and all((target / name).is_file() and hashlib.sha256((target / name).read_bytes()).hexdigest() == digest for name, digest in code.items()):
                return target
            raise FileExistsError(f"Source đã tồn tại và khác ZIP: {target}. Không ghi đè; chọn SOURCE_DIRECTORY mới hoặc dùng PROJECT_ROOT trỏ tới source hiện có.")
        # Every checked member is below target, which does not exist. Other CWD files are untouched.
        destination.mkdir(parents=True, exist_ok=True)
        bundle.extractall(destination)
    return target


def bootstrap_project(defaults: dict, *, root_override: str | Path | None = None, mount_requested: bool = False,
                      source_archive: str | Path | None = None, source_directory: str | Path | None = None,
                      required_files: tuple = ()) -> Path:
    """Mount (opt-in), unpack (opt-in), then resolve code; never read the dataset here."""
    point = Path(os.environ.get("DISEASE_DRIVE_MOUNT", defaults["drive_mount"])).expanduser().resolve()
    if mount_requested:
        mount_drive_at(point)  # Must run before root lookup; does not import src or read its config.
    extracted = (unpack_source_archive(source_archive, source_directory, required_files=required_files)
                 if source_archive is not None else None)
    drive_project = Path(os.environ.get("DISEASE_DRIVE_PROJECT", defaults["project_relative"])).expanduser()
    if not drive_project.is_absolute():
        drive_project = point / drive_project
    explicit = root_override if root_override is not None else extracted
    root = project_root(root_override=explicit, search_roots=(drive_project,))
    missing = [name for name in required_files if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Mã nguồn tại {root} chưa đủ cho notebook này: {', '.join(missing)}. "
            "Runtime đang có source cũ/thiếu file. Upload ZIP source MỚI, đặt SOURCE_ARCHIVE tới ZIP đó, "
            "PROJECT_ROOT=None và giải nén ở SOURCE_DIRECTORY mới; hoặc đồng bộ đủ src/ và configs/. "
            "Chỉ upload notebook/CSV hoặc cài pip không bổ sung module nội bộ src.data."
        )
    return root
