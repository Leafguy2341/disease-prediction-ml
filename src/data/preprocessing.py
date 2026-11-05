"""Approved Phase 2 preparation and immutable split artifacts; no learned transforms."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import shutil
import tempfile
import zlib

import numpy as np
import pandas as pd

from .audit import exact_pattern_ids
from .io import markdown_table
from .loader import DatasetError, sha256_file
from .paths import OutputPaths
from .preprocessing_inspection import group_split_feasibility


SPLITS = ("train", "validation", "test")
METADATA = Path("artifacts/metadata/phase2")


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _digest(value) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def read_phase2_policy(root: Path) -> dict:
    policy = json.loads((root / "configs/phase2.json").read_text(encoding="utf-8"))
    if (policy.get("status") != "approved" or policy.get("drop_features") != ["regurgitation", "regurgitation.1"]
            or policy.get("minimum_unique_vectors_per_class") != 10 or policy.get("seed") != 42
            or policy.get("split_ratios") != [.7, .15, .15]
            or policy.get("split_method") != "seeded_group_quota_coverage_repair_v1"
            or policy.get("constant_features", {}).get("fit_in_phase2") is not False):
        raise DatasetError("configs/phase2.json khác chính sách đã duyệt; dừng, không tự đổi schema/ngưỡng/split.")
    return policy


def validate_raw_frame(frame: pd.DataFrame, policy: dict) -> list[str]:
    """Fail on invalid input rather than silently fixing, imputing or renaming."""
    target = policy["target"]
    if frame.empty or not frame.columns.is_unique or target not in frame:
        raise DatasetError("Raw rỗng, trùng tên cột hoặc thiếu nhãn bệnh.")
    features = frame.columns.drop(target).tolist()
    if len(features) != policy["expected_raw_symptom_features"]:
        raise DatasetError("Số đặc trưng raw khác schema đã duyệt; dừng để kiểm tra nguồn.")
    if not set(policy["drop_features"]).issubset(features):
        raise DatasetError("Thiếu một trong hai cột triệu chứng phải loại; không tự bỏ qua schema sai.")
    y = frame[target]
    if not y.map(lambda v: isinstance(v, str) and bool(v.strip())).all() or y.nunique() < 2:
        raise DatasetError("Nhãn bệnh phải đầy đủ, không rỗng và có ít nhất hai lớp; không tự chuẩn hóa nhãn.")
    x = frame[features]
    if (not all(pd.api.types.is_numeric_dtype(x[c]) for c in features)
            or x.isna().any().any() or not x.isin([0, 1]).all().all()):
        raise DatasetError("Triệu chứng raw phải là giá trị số 0/1, không thiếu; không tự ép giá trị/impute.")
    return features


def _packed(frame: pd.DataFrame, features: list[str]) -> np.ndarray:
    return np.ascontiguousarray(np.packbits(frame[features].to_numpy(dtype=np.uint8), axis=1, bitorder="big"))


def _data_fingerprint(frame: pd.DataFrame, features: list[str], target: str, classes: list[str]) -> str:
    digest = hashlib.sha256(_json({"features": features, "target": target, "classes": classes}).encode("utf-8"))
    digest.update(_packed(frame, features).tobytes())
    codes = frame[target].map({name: i for i, name in enumerate(classes)}).to_numpy(dtype="<u4")
    digest.update(codes.tobytes())
    return digest.hexdigest()


def preprocess_dataset(raw: pd.DataFrame, policy: dict) -> dict:
    """Execute approved ordering, then enforce coverage/overlap/dedup/reproducibility.

    Source row identifiers are 1-based DATA rows (header excluded). First surviving
    raw occurrence determines row order. Group IDs are exact-equality first-seen
    codes after schema removal, deduplication and eligibility, not clinical IDs.
    No transformer is fitted and no result is written until all constraints pass.
    """
    raw_features = validate_raw_frame(raw, policy)
    target, minimum = policy["target"], policy["minimum_unique_vectors_per_class"]
    features = [f for f in raw_features if f not in policy["drop_features"]]
    if not features:
        raise DatasetError("Schema không còn triệu chứng.")
    steps = []

    def record(step, frame, feature_count):
        steps.append({"step": step, "records": len(frame), "classes": int(frame[target].nunique()),
                      "symptom_features": feature_count})

    record("validated_raw", raw, len(raw_features))
    reduced = raw.loc[:, features + [target]]
    record("removed_ambiguous_features", reduced, len(features))
    unique_mask = ~reduced.duplicated(subset=features + [target], keep="first")
    dedup = reduced.loc[unique_mask].copy()
    source_rows = np.flatnonzero(unique_mask.to_numpy()) + 1
    record("exact_dedup_remaining_vector_and_label", dedup, len(features))
    # Once (vector,label) is unique, per-label row count == unique vectors per label.
    independent = dedup.groupby(target, sort=True).size().rename("unique_vectors")
    record("recalculated_independent_vectors_per_class", dedup, len(features))
    eligible_classes = independent.index[independent >= minimum]
    mask = dedup[target].isin(eligible_classes).to_numpy()
    data = dedup.loc[mask].reset_index(drop=True)
    data[features] = data[features].astype("uint8")
    source_rows = source_rows[mask]
    if data.empty or len(eligible_classes) < 2:
        raise DatasetError("Không đủ dữ liệu/lớp sau ngưỡng đã duyệt; không tự hạ ngưỡng.")
    record("eligible_classes_after_schema_and_dedup", data, len(features))
    group_ids, _ = exact_pattern_ids(data[features])
    record("generated_remaining_vector_groups", data, len(features))
    pairs = pd.DataFrame({"pattern_id": group_ids, "disease": data[target]})
    kwargs = {"minimum": minimum, "seed": policy["seed"], "ratios": policy["split_ratios"], "include_assignments": True}
    split = group_split_feasibility(pairs, **kwargs)
    if any(split["missing_classes"].values()):
        raise DatasetError(f"Không phủ đủ lớp trong ba tập với chính sách đã duyệt: {split['missing_classes']}. Không lưu split.")
    reproduced = group_split_feasibility(pairs, **kwargs)
    pd.testing.assert_frame_equal(split["group_assignment"], reproduced["group_assignment"])
    pd.testing.assert_frame_equal(split["class_support"], reproduced["class_support"])
    assignments = pd.DataFrame({"source_data_row_1based": source_rows, "group_id": group_ids})
    assignments["split"] = assignments["group_id"].map(split["group_assignment"].set_index("group_id")["split"])
    assignments["split_row_0based"] = assignments.groupby("split", sort=False).cumcount()
    if assignments["split"].isna().any() or data.duplicated(features + [target]).any():
        raise DatasetError("Phân bổ không đầy đủ hoặc vẫn còn exact duplicate; không lưu split.")
    if assignments.groupby("group_id")["split"].nunique().gt(1).any():
        raise DatasetError("Có group ở nhiều tập; không lưu split.")
    # Recompute vector intersections independently from the materialized row split.
    packed = _packed(data, features)
    vector_sets = {name: {row.tobytes() for row in packed[assignments["split"].eq(name).to_numpy()]} for name in SPLITS}
    vector_overlaps = {f"{a} / {b}": len(vector_sets[a] & vector_sets[b])
                       for a, b in (("train", "validation"), ("train", "test"), ("validation", "test"))}
    if any(vector_overlaps.values()) or any(split["overlaps"].values()):
        raise DatasetError("Vector triệu chứng trùng giữa các tập; không lưu split.")
    if len(data) != int(independent.loc[eligible_classes].sum()):
        raise DatasetError("Không bảo toàn các cặp vector/nhãn đủ điều kiện.")
    classes = sorted(data[target].unique().tolist())
    inventory = independent.rename_axis("disease").reset_index()
    inventory["eligible"] = inventory["unique_vectors"] >= minimum
    validation = {"exact_duplicate_rows": 0, "group_overlaps": split["overlaps"],
                  "symptom_vector_overlaps": vector_overlaps, "missing_classes": split["missing_classes"],
                  "singleton_validation_classes": int(split["class_support"]["validation"].eq(1).sum()),
                  "singleton_test_classes": int(split["class_support"]["test"].eq(1).sum()),
                  "deterministic_seed42_reproduction": bool(policy["seed"] == 42),
                  "deterministic_assignment_recomputed": True,
                  "conflicting_groups_preserved": int(pairs.groupby("pattern_id")["disease"].nunique().gt(1).sum()),
                  "fitted_transformers": [], "test_locked": True}
    record("validated_final_split_total", data, len(features))
    return {"data": data, "assignments": assignments, "features": features, "classes": classes,
            "policy": policy, "steps": pd.DataFrame(steps), "class_inventory": inventory,
            "split_summary": split["summary"], "class_support": split["class_support"],
            "validation": validation, "coverage_repairs": split["repairs"],
            "raw_columns": raw.columns.tolist(),
            "processed_sha256": _data_fingerprint(data, features, target, classes)}


def _gzip_csv(frame: pd.DataFrame, path: Path) -> None:
    """Gzip with no timestamp or temporary filename in its header."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0, compresslevel=6) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                frame.to_csv(text, index=False, lineterminator="\n", chunksize=5000)


def _validate_export_result(result: dict) -> None:
    """Recheck the concrete data/assignment just before any file publication."""
    data, assignment = result["data"], result["assignments"]
    features, target = result["features"], result["policy"]["target"]
    if (data.columns.tolist() != features + [target] or len(data) != len(assignment)
            or data.duplicated(features + [target]).any()
            or set(assignment["split"]) != set(SPLITS)
            or assignment["source_data_row_1based"].duplicated().any()
            or not assignment["source_data_row_1based"].is_monotonic_increasing):
        raise DatasetError("Dữ liệu/assignment cuối bị thay đổi hoặc không hợp lệ; không export.")
    if not data[features].isin([0, 1]).all().all() or data[features].isna().any().any():
        raise DatasetError("Dữ liệu cuối không còn đúng binary schema.")
    groups, _ = exact_pattern_ids(data[features])
    if (not np.array_equal(groups, assignment["group_id"].to_numpy())
            or assignment.groupby("group_id")["split"].nunique().gt(1).any()):
        raise DatasetError("Assignment không khớp vector hoặc trùng group giữa các tập.")
    for name in SPLITS:
        selected = assignment["split"].eq(name)
        if (set(data.loc[selected, target]) != set(result["classes"])
                or assignment.loc[selected, "split_row_0based"].tolist() != list(range(int(selected.sum())))):
            raise DatasetError("Coverage hoặc thứ tự hàng của split không hợp lệ.")
        expected = result["split_summary"].set_index("split").loc[name]
        if (selected.sum() != expected["dedup_records"]
                or assignment.loc[selected, "group_id"].nunique() != expected["groups"]):
            raise DatasetError("Metadata số dòng/group không khớp split thực tế.")
    if _data_fingerprint(data, features, target, result["classes"]) != result["processed_sha256"]:
        raise DatasetError("Dữ liệu cuối khác fingerprint đã kiểm tra; không export.")


def _reuse_locked_export(result: dict, source: Path, output: OutputPaths, payloads: dict,
                         expected_source_sha256: str) -> dict:
    """Verify semantic equality and stored checksums across runtime/package versions.

    Python/pandas/zlib versions and source checksums describe the ORIGINAL export.
    They are not a reason to rewrite a locked test set when every actual row,
    assignment, policy, schema and label mapping still matches exactly.
    """
    try:
        manifest = json.loads((output.root / METADATA / "dataset_manifest.json").read_text(encoding="utf-8"))
        if (manifest["status"] != "finalized" or not manifest["test_locked"]
                or manifest["raw"]["sha256"] != expected_source_sha256
                or manifest["processed"]["sha256"] != result["processed_sha256"]
                or manifest["policy_sha256"] != _digest(result["policy"])
                or manifest["steps"] != result["steps"].to_dict("records")):
            raise ValueError("Nguồn/policy/dữ liệu không khớp bộ đã khóa.")
        expected_files = {f"data/processed/{name}.csv.gz" for name in SPLITS}
        expected_files.update((METADATA / name).as_posix() for name in [*payloads, "split_assignments.csv.gz"])
        if set(manifest["files"]) != expected_files:
            raise ValueError("Danh sách artifact không khớp bộ Phase 2 hoàn chỉnh.")
        for relative, entry in manifest["files"].items():
            path = output.root / relative
            if not path.is_file():
                raise FileNotFoundError(f"Bộ split đã khóa thiếu file: {path}")
            if sha256_file(path) != entry["sha256"]:
                raise ValueError(f"Checksum không khớp: {relative}")
        for name, expected in payloads.items():
            stored = json.loads((output.root / METADATA / name).read_text(encoding="utf-8"))
            if stored != expected:
                raise ValueError(f"Schema/mapping/policy/split metadata khác: {name}")
        assignments = pd.read_csv(output.root / METADATA / "split_assignments.csv.gz")
        pd.testing.assert_frame_equal(assignments, result["assignments"], check_exact=True)
        target, features = result["policy"]["target"], result["features"]
        for name in SPLITS:
            stored = pd.read_csv(output.processed_dir / f"{name}.csv.gz",
                                 dtype={**{f: "uint8" for f in features}, target: str}, keep_default_na=False)
            expected = result["data"].loc[result["assignments"]["split"].eq(name)].reset_index(drop=True)
            pd.testing.assert_frame_equal(stored, expected, check_exact=True)
        if sha256_file(source) != expected_source_sha256:
            raise DatasetError("Raw thay đổi trong lúc kiểm tra bộ đã khóa.")
        return manifest
    except (KeyError, ValueError, AssertionError) as exc:
        raise FileExistsError(f"Giữ split/artifact đã khóa; không ghi đè. Kiểm tra tái sử dụng thất bại: {exc}") from exc


def export_preprocessed(result: dict, source: Path, output: OutputPaths, *, expected_source_sha256: str) -> dict:
    """Stage/round-trip locally, preflight all targets, publish manifest LAST.

    Existing finalized files retain their stored checksums and exact row content.
    Compatible reruns reuse them across environments; no force/overwrite option.
    Temporary files use the runtime's local tempfile storage, not persistent Drive.
    """
    if output.run_id is not None:
        raise ValueError("Phase 2 dùng output root cố định, không dùng reports/runs.")
    if sha256_file(source) != expected_source_sha256:
        raise DatasetError("Raw thay đổi từ lúc đọc; dừng trước khi lưu.")
    _validate_export_result(result)
    data, assignments, features = result["data"], result["assignments"], result["features"]
    target, classes = result["policy"]["target"], result["classes"]
    schema = {"schema_version": 1, "status": "approved_before_training_fitted_variance_removal",
              "features": features, "n_features": len(features), "target": target,
              "csv_column_order": features + [target], "feature_dtype": "uint8", "allowed_values": [0, 1],
              "excluded_features": result["policy"]["drop_features"],
              "exclusion_reason": result["policy"]["drop_reason"],
              "binary_interpretation": result["policy"]["binary_interpretation"],
              "group_id_is_feature": False, "constant_feature_removal_fitted": False}
    schema["schema_sha256"] = _digest(schema)
    mapping = {"classes": classes, "class_to_id": {name: i for i, name in enumerate(classes)},
               "id_to_class": classes, "ordering": "Python Unicode lexicographic; exact original labels",
               "encoded_dtype": "int64", "csv_target": "original disease string, not encoded",
               "unknown_label_policy": "raise; no implicit remapping"}
    split_metadata = {"seed": result["policy"]["seed"], "target_ratios": result["policy"]["split_ratios"],
                      "method": result["policy"]["split_method"], "group_definition": result["policy"]["group_definition"],
                      "group_id_encoding": "zero-based first-seen exact equality after eligibility; bound to dataset fingerprint and feature order",
                      "source_row_encoding": "1-based raw DATA row; CSV header excluded",
                      "output_row_order": "first surviving raw occurrence, stable order within each split",
                      "coverage_repairs": result["coverage_repairs"], "splits": result["split_summary"].to_dict("records"),
                      "validation": result["validation"], "class_support": result["class_support"].to_dict("records"),
                      "class_eligibility_after_approved_schema": result["class_inventory"].to_dict("records"),
                      "test_usage": result["policy"]["test_usage"], "prior_full_dataset_eda": True}
    payloads = {"feature_schema.json": schema, "label_mapping.json": mapping,
                "preprocessing_policy.json": result["policy"], "split_metadata.json": split_metadata}
    if (output.root / METADATA / "dataset_manifest.json").is_file():
        return _reuse_locked_export(result, source, output, payloads, expected_source_sha256)
    with tempfile.TemporaryDirectory(prefix="disease-phase2-") as temp:
        stage = Path(temp)
        for name in SPLITS:
            selected = data.loc[assignments["split"].eq(name)]
            path = stage / "data/processed" / f"{name}.csv.gz"
            _gzip_csv(selected, path)
            reread = pd.read_csv(path, dtype={**{f: "uint8" for f in features}, target: str}, keep_default_na=False)
            pd.testing.assert_frame_equal(reread, selected.reset_index(drop=True), check_exact=True)
        _gzip_csv(assignments, stage / METADATA / "split_assignments.csv.gz")
        for name, payload in payloads.items():
            (stage / METADATA / name).write_text(_json(payload), encoding="utf-8", newline="")
        files = {p.relative_to(stage).as_posix(): {"sha256": sha256_file(p), "bytes": p.stat().st_size}
                 for p in sorted(stage.rglob("*")) if p.is_file()}
        manifest = {"phase": 2, "status": "finalized", "raw": {"filename": source.name,
                    "sha256": expected_source_sha256, "bytes": source.stat().st_size,
                    "columns": result["raw_columns"]},
                    "processed": {"sha256": result["processed_sha256"], "records": len(data),
                    "features": len(features), "classes": len(classes), "schema_sha256": schema["schema_sha256"],
                    "fingerprint_encoding": "SHA256(UTF8(json.dumps({features,target,classes}, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + LF) + packed X bits big-endian row-major + label IDs uint32 little-endian row-major)"},
                    "steps": result["steps"].to_dict("records"), "files": files,
                    "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "zlib": zlib.ZLIB_VERSION},
                    "splitter_source_sha256": sha256_file(Path(__file__).with_name("preprocessing_inspection.py")),
                    "preprocessing_source_sha256": sha256_file(Path(__file__)),
                    "policy_sha256": _digest(result["policy"]), "format": "CSV.gz, UTF-8, LF; no gzip timestamp/filename",
                    "raw_unchanged": True, "roundtrip_verified": True, "test_locked": True}
        commit = METADATA / "dataset_manifest.json"
        (stage / commit).write_text(_json(manifest), encoding="utf-8", newline="")
        staged = [p for p in sorted(stage.rglob("*")) if p.is_file() and p != stage / commit] + [stage / commit]
        for path in staged:
            destination = output.root / path.relative_to(stage)
            if destination.exists() and sha256_file(destination) != sha256_file(path):
                raise FileExistsError(f"Giữ split/artifact đã khóa: {destination}. Nội dung khác; chọn output root khác để tái tạo, không ghi đè.")
            if (output.root / commit).exists() and not destination.is_file():
                raise FileNotFoundError(f"Bộ split đã khóa thiếu file: {destination}; dừng để kiểm tra tính toàn vẹn.")
        if sha256_file(source) != expected_source_sha256:
            raise DatasetError("Raw thay đổi trong lúc chuẩn bị export; không lưu split.")
        for path in staged:
            destination = output.root / path.relative_to(stage)
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as stream, path.open("rb") as incoming:
                    shutil.copyfileobj(incoming, stream)
            if sha256_file(destination) != sha256_file(path):
                raise IOError(f"Checksum sau ghi không khớp: {destination}")
    if sha256_file(source) != expected_source_sha256:
        raise DatasetError("Raw thay đổi trong lúc export; cần kiểm tra trước khi dùng kết quả.")
    return manifest


def load_final_split(output: OutputPaths, name: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Load X in approved order, encoded y and aligned groups. Test is final-eval only."""
    if name not in SPLITS:
        raise ValueError(f"Split phải là một trong {SPLITS}.")
    folder = output.root / METADATA
    manifest = json.loads((folder / "dataset_manifest.json").read_text(encoding="utf-8"))
    relevant = [f"data/processed/{name}.csv.gz", *(str(METADATA / f).replace("\\", "/")
                for f in ("feature_schema.json", "label_mapping.json", "split_assignments.csv.gz"))]
    for relative in relevant:
        if sha256_file(output.root / relative) != manifest["files"][relative]["sha256"]:
            raise DatasetError(f"Artifact không đúng fingerprint: {relative}")
    schema = json.loads((folder / "feature_schema.json").read_text(encoding="utf-8"))
    labels = json.loads((folder / "label_mapping.json").read_text(encoding="utf-8"))
    target, features = schema["target"], schema["features"]
    frame = pd.read_csv(output.processed_dir / f"{name}.csv.gz", dtype={**{f: "uint8" for f in features}, target: str}, keep_default_na=False)
    if frame.columns.tolist() != schema["csv_column_order"]:
        raise DatasetError("Thứ tự cột split không khớp feature schema.")
    assignments = pd.read_csv(folder / "split_assignments.csv.gz")
    selected = assignments.loc[assignments["split"].eq(name)].sort_values("split_row_0based")
    if selected["split_row_0based"].tolist() != list(range(len(frame))):
        raise DatasetError("Group metadata không khớp hàng của split.")
    encoded = frame[target].map(labels["class_to_id"])
    if encoded.isna().any():
        raise DatasetError("Nhãn split không có trong label mapping.")
    return frame[features], encoded.to_numpy(dtype=np.int64), selected["group_id"].to_numpy(dtype=np.int64)


def preprocessing_report(result: dict, manifest: dict) -> str:
    v = result["validation"]
    return f"""# Phase 2 — Preprocessing đã hoàn tất theo chính sách được duyệt

CSV gốc `{manifest['raw']['filename']}` giữ nguyên, SHA-256 `{manifest['raw']['sha256']}`.
Fingerprint dữ liệu sau xử lý: `{manifest['processed']['sha256']}`.

## Chính sách và số lượng qua từng bước

Loại `regurgitation` và `regurgitation.1` vì không xác minh được cách phân biệt chúng từ lời kể người dùng; đây là quyết định schema đã được duyệt cho ML và suy luận tương lai. Việc loại làm mất một phần phân biệt vector, không phải kết luận rằng cột vô ích hay accuracy sẽ tốt hơn. Diễn giải tạm thời: 1 = ghi nhận hiện diện, 0 = chưa ghi nhận hiện diện, không chứng minh vắng mặt lâm sàng.

{markdown_table(result['steps'])}

Thứ tự: xác thực raw → bỏ hai cột → exact dedup theo **vector còn lại và nhãn** → đếm lại vector/lớp → giữ lớp ≥10 → group theo vector còn lại → split. Giữ mọi nhãn khác nhau của cùng vector; không bỏ phiếu đa số. Ngưỡng 10 được tính sau schema/dedup, không dùng lại support trước bỏ cột. Còn **{len(result['data']):,} bản ghi, {len(result['classes'])} lớp, {len(result['features'])} triệu chứng**, chưa loại cột hằng.

## Split cố định, seed 42

Dùng đúng thuật toán đã kiểm tra: hoán vị group với hạn ngạch khoảng 70/15/15, sửa thiếu lớp theo support tăng dần; chỉ chuyển group khi không làm mất lớp ở tập cho, tối thiểu thay đổi sai lệch support và phá hòa theo group ID. Không đổi seed/ngưỡng để tìm kết quả tốt hơn.

{markdown_table(result['split_summary'].round(4))}

- Lớp vắng train/validation/test: `{v['missing_classes']}`.
- Giao group: `{v['group_overlaps']}`; giao vector kiểm tra độc lập bằng pack-bit equality: `{v['symptom_vector_overlaps']}`.
- Exact duplicate (vector, nhãn) còn lại: **{v['exact_duplicate_rows']}**.
- Nhóm nhiều nhãn được giữ: **{v['conflicting_groups_preserved']:,}**.
- Lớp chỉ có 1 vector validation/test: **{v['singleton_validation_classes']}/{v['singleton_test_classes']}**. Đủ mặt lớp không bảo đảm metric từng bệnh ổn định.
- Tính lại assignment và support với seed 42 cho cùng dữ liệu có thứ tự: **khớp hoàn toàn**. CSV nén dùng header gzip không timestamp/filename; đọc lại sau ghi khớp dữ liệu và thứ tự cột.

## Dữ liệu và artifact tái sử dụng

`data/processed/{{train,validation,test}}.csv.gz` gồm đúng danh sách triệu chứng đã duyệt theo thứ tự, rồi cột `diseases` dạng nhãn gốc. Nén CSV giảm I/O Drive, đọc trực tiếp bằng pandas. Không chèn group/row ID vào đặc trưng.

`artifacts/metadata/phase2/` chứa `feature_schema.json` (thứ tự cột), `label_mapping.json` (mã 0-based theo tên nhãn nguyên bản sắp xếp Unicode), `preprocessing_policy.json`, `split_metadata.json` (support từng lớp và lớp bị loại), `split_assignments.csv.gz` (raw data-row 1-based, group, split, split-row 0-based), `dataset_manifest.json` (SHA-256 raw/processed/từng file, phiên bản môi trường và mã nguồn). ID group phụ thuộc thứ tự dữ liệu/schema và gắn với fingerprint. Hàm `load_final_split` đọc đúng X/y/groups theo các artifact này; không thay label mapping giữa các tập.

Các đường dẫn trên tính từ output root đã cấu hình, lưu persistent trên Colab/Drive; source/cache có thể ở runtime tạm. Không tự mount, cài gói hoặc tải dữ liệu. Lần kiểm tra này dùng Windows Python; chưa có thực thi Colab thật.

**Test đã khóa:** chỉ dùng đánh giá cuối, không chọn đặc trưng/hyperparameter. Phase 1 đã thăm dò toàn CSV nên không tuyên bố test chưa từng được xem. Chưa fit `VarianceThreshold`, chọn đặc trưng, PCA hay mô hình. `VarianceThreshold(0)` chỉ được fit trên train bên trong model pipeline ở giai đoạn huấn luyện sau này; giữ nguyên mọi cột hằng ở Phase 2. Mọi thay đổi schema ở train/inference sau này phải đi qua artifact/pipeline đã duyệt, không tự bịa nghĩa lâm sàng cho cột.

Các báo cáo, bảng và hình kiểm tra trước đó giữ làm lịch sử; chúng mô tả giả định trước phê duyệt, không thay thế số liệu cuối trong báo cáo này. Raw và mọi kết quả Phase 1 giữ nguyên. **Dừng sau Phase 2, chưa huấn luyện hay triển khai chatbot.**
"""
