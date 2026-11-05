"""Read-only CSV discovery/loading and optional verified cache; never download data."""
from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path
import shutil

import pandas as pd

from .paths import RuntimePaths, resolve_paths


class DatasetError(ValueError):
    """Actionable input/schema error, without inventing or dropping data."""


def _existing_file(value, base: Path) -> Path:
    path = Path(value).expanduser()
    path = (path if path.is_absolute() else base / path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Không có CSV đã chỉ định: {path}. Kiểm tra DISEASE_DATA_PATH/raw_dataset và mount/sync storage.")
    return path


def dataset_path(location: Path | RuntimePaths, config: dict) -> Path:
    base = location.storage_root if isinstance(location, RuntimePaths) else Path(location)
    canonical = isinstance(location, RuntimePaths) and location.settings.get("canonical_colab", False)
    override = None if canonical else os.environ.get("DISEASE_DATA_PATH")
    if override is not None:
        return _existing_file(override, base)
    paths = location if isinstance(location, RuntimePaths) else resolve_paths(location)
    configured = paths.settings.get("raw_dataset")
    if configured is not None:
        return _existing_file(configured, paths.storage_root)
    available = sorted(p for p in paths.raw_dir.glob("*") if p.is_file() and p.suffix.lower() == ".csv")
    known_names = {Path(p).name for p in config.get("dataset_candidates", [])}
    known = [p for p in available if p.name in known_names]
    candidates = known or available
    if len(candidates) == 1:
        return candidates[0].resolve()
    if len(candidates) > 1:
        raise DatasetError("Có nhiều CSV phù hợp: " + ", ".join(p.name for p in candidates) + ". Chỉ định DISEASE_DATA_PATH hoặc raw_dataset; không tự đoán file.")
    # Backward-compatible local layout; never search a code checkout for Colab data.
    if paths.runtime == "local" and paths.storage_root == paths.project_root and paths.raw_dir == paths.storage_root / "data/raw":
        legacy = [paths.project_root / p for p in config.get("dataset_candidates", [])]
        for candidate in legacy:
            if candidate.is_file():
                return candidate.resolve()
    raise FileNotFoundError(
        f"Không có CSV trong {paths.raw_dir}. Giữ đúng tên file thực tế; cấu hình DISEASE_DATA_PATH "
        "hoặc raw_dataset, kiểm tra Drive/mount và đồng bộ dữ liệu. Không tạo dữ liệu thay thế."
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_dataset(paths: RuntimePaths, source: Path) -> Path:
    """Copy only when opted in. Cache by content hash, retain the actual filename."""
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"CSV nguồn không có: {source}")
    if not paths.copy_raw_to_local:
        return source
    digest = sha256_file(source)
    destination = paths.cache_dir / digest / source.name
    if destination.resolve() == source:
        return source
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) != digest:
            raise DatasetError(f"Cache sai checksum: {destination}. Chọn cache directory mới; không ghi đè file này.")
        return destination
    created = False
    try:
        with destination.open("xb") as output:
            created = True
            with source.open("rb") as stream:
                shutil.copyfileobj(stream, output, length=1024 * 1024)
        if sha256_file(destination) != digest:
            raise DatasetError("Checksum của bản cache khác CSV nguồn; dừng phân tích.")
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)  # Only the partial cache file this call created.
        raise
    return destination


def load_dataset(path: Path, target: str) -> pd.DataFrame:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream), [])
    if not header or any(not h.strip() for h in header):
        raise DatasetError("CSV rỗng hoặc tên cột trống; cần kiểm tra file nguồn.")
    if len(header) != len(set(header)):
        raise DatasetError("CSV có tên cột trùng. Không tự đổi tên vì có thể che giấu lỗi schema.")
    if target not in header or len(header) < 2:
        raise DatasetError(f"Cần cột nhãn {target!r} và ít nhất một đặc trưng. Có: {header[:8]}")
    try:
        frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except (pd.errors.ParserError, UnicodeError) as exc:
        raise DatasetError(f"Không đọc được CSV theo schema/UTF-8: {exc}") from exc
    if frame.empty:
        raise DatasetError("CSV không có dòng dữ liệu.")
    frame.attrs["input_dtypes"] = frame.dtypes.astype(str).to_dict()
    for column in frame.columns.drop(target):
        series = frame[column]
        if pd.api.types.is_numeric_dtype(series) and series.notna().all() and series.isin([0, 1]).all():
            frame[column] = series.astype("uint8")
    return frame
