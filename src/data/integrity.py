"""Phase 2 integrity independent of source deployment. Never open the test payload."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .loader import sha256_file
from .paths import OutputPaths

META = "artifacts/metadata/phase2"
TRAINING_FILES = (
    "data/processed/train.csv.gz", "data/processed/validation.csv.gz",
    *(f"{META}/{name}" for name in ("feature_schema.json", "label_mapping.json",
                                   "preprocessing_policy.json", "split_metadata.json", "split_assignments.csv.gz")),
)


def read_baseline(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Thiếu approved data baseline: {path}. Đồng bộ configs/phase2_integrity.json; không tạo baseline từ dữ liệu Drive chưa xác minh.")
    baseline = json.loads(path.read_text(encoding="utf-8-sig"))
    if (baseline.get("version") != 1 or not baseline.get("approved_manifest_sha256")
            or not set(TRAINING_FILES).issubset(baseline.get("files", {})) or not baseline.get("processed")):
        raise ValueError(f"Approved data baseline không hợp lệ: {path}")
    return baseline


def verify_training_inputs(output: OutputPaths, expected: dict | None = None, *, baseline: dict | None = None) -> dict:
    """Low-level legacy expected-fingerprint API; shared Stage C always supplies a baseline."""
    manifest_path = output.root / META / "dataset_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Thiếu {manifest_path}. Đồng bộ bộ Phase 2 đã khóa; không chạy lại preprocessing.")
    payload = manifest_path.read_bytes()
    manifest_sha = hashlib.sha256(payload).hexdigest()
    if baseline is not None and manifest_sha not in baseline["approved_manifest_sha256"]:
        raise ValueError(f"Phase 2 manifest checksum mismatch: file={manifest_path}; expected={baseline['approved_manifest_sha256']}; actual={manifest_sha}")
    manifest = json.loads(payload.decode("utf-8-sig"))
    if manifest.get("status") != "finalized" or not manifest.get("test_locked"):
        raise ValueError(f"Phase 2 chưa finalized/test chưa khóa: {manifest_path}")
    expected = baseline["processed"] if baseline is not None else expected
    if expected and any(manifest["processed"].get(k) != v for k, v in expected.items()):
        raise ValueError(f"Fingerprint/số lượng Phase 2 khác approved baseline: {manifest_path}")
    if baseline is not None:
        if manifest["files"] != baseline["files"]:
            differences = [n for n in manifest["files"].keys() | baseline["files"].keys()
                           if manifest["files"].get(n) != baseline["files"].get(n)]
            raise ValueError(f"Manifest file inventory khác approved baseline: {differences}")
    for relative in TRAINING_FILES:
        path = output.root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Thiếu artifact Phase 2: {path}. Không tái tạo dữ liệu.")
        entry = (baseline["files"] if baseline is not None else manifest["files"])[relative]
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            raise ValueError(f"Checksum Phase 2 mismatch: file={path}; expected={entry['sha256']}; actual={actual}")
        if path.stat().st_size != entry["bytes"]:
            raise ValueError(f"Phase 2 size mismatch: file={path}; expected={entry['bytes']}; actual={path.stat().st_size}")
    def read(name):
        return json.loads((output.root / META / name).read_text(encoding="utf-8"))
    schema, labels, policy, splits = (read(n) for n in (
        "feature_schema.json", "label_mapping.json", "preprocessing_policy.json", "split_metadata.json"))
    if (len(schema["features"]) != manifest["processed"]["features"]
            or schema["schema_sha256"] != manifest["processed"]["schema_sha256"]
            or schema["csv_column_order"] != [*schema["features"], schema["target"]]
            or len(labels["classes"]) != manifest["processed"]["classes"]
            or labels["class_to_id"] != {label: i for i, label in enumerate(labels["classes"])}
            or labels["id_to_class"] != labels["classes"]
            or policy["seed"] != 42 or splits["seed"] != 42
            or policy["minimum_unique_vectors_per_class"] != 10
            or policy["drop_features"] != ["regurgitation", "regurgitation.1"]):
        raise ValueError("Schema, mapping, policy hoặc split metadata không nhất quán.")
    return {"manifest": manifest, "manifest_sha256": manifest_sha,
            "schema": schema, "labels": labels, "policy": policy, "splits": splits}
