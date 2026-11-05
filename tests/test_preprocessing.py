"""Approved preparation invariants on small adversarial fixtures, never ML fitting."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.loader import DatasetError, sha256_file
from src.data.paths import OutputPaths
from src.data.preprocessing import (
    export_preprocessed, load_final_split, preprocess_dataset, read_phase2_policy, validate_raw_frame,
)


@pytest.fixture
def approved_fixture():
    policy = read_phase2_policy(Path(__file__).resolve().parents[1])
    rows = []
    for disease, count in [("A", 12), ("B", 12), ("C", 9)]:
        for vector in range(count):
            rows.append({"diseases": disease, **{f"s{i}": (vector >> i) & 1 for i in range(4)},
                         "constant_zero": 0, "constant_one": 1,
                         "regurgitation": 0, "regurgitation.1": 0})
    # Both same-label extra distinctions and raw exact copies must disappear AFTER dropping features.
    for i in [0, 1, 2, 3, 24]:
        row = dict(rows[i]); row["regurgitation"] = 1; rows.append(row)
    rows.extend([dict(rows[0]), dict(rows[0])])
    frame = pd.DataFrame(rows)
    policy["expected_raw_symptom_features"] = frame.shape[1] - 1
    return frame, policy


def test_approved_ordering_dedups_then_counts_support_and_preserves_conflicting_labels(approved_fixture):
    frame, policy = approved_fixture
    before = frame.copy(deep=True)
    result = preprocess_dataset(frame, policy)
    steps = result["steps"].set_index("step")
    assert steps.loc["validated_raw", "records"] == 40
    assert steps.loc["removed_ambiguous_features", "records"] == 40
    assert steps.loc["exact_dedup_remaining_vector_and_label", "records"] == 33
    assert steps.loc["eligible_classes_after_schema_and_dedup", "records"] == 24
    # C had 10 original symptom vectors but only 9 AFTER the approved schema removal.
    assert frame.loc[frame.diseases.eq("C")].drop_duplicates().shape[0] == 10
    inventory = result["class_inventory"].set_index("disease")
    assert inventory.loc["C", "unique_vectors"] == 9 and not inventory.loc["C", "eligible"]
    assert result["classes"] == ["A", "B"]
    assert result["features"] == ["s0", "s1", "s2", "s3", "constant_zero", "constant_one"]
    assert len(result["data"]) == 24 and result["assignments"].group_id.nunique() == 12
    assert result["validation"]["conflicting_groups_preserved"] == 12
    assert not result["data"].duplicated().any()
    assert result["validation"]["fitted_transformers"] == []
    assert all(result["split_summary"].classes == 2)
    assert not any(result["validation"]["symptom_vector_overlaps"].values())
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize("bad", [256, -1, None, "1"])
def test_validates_even_removed_columns_before_any_transformation(approved_fixture, bad):
    frame, policy = approved_fixture
    frame = frame.copy()
    frame["regurgitation"] = frame["regurgitation"].astype(object)
    frame.loc[0, "regurgitation"] = bad
    with pytest.raises(DatasetError, match="0/1"):
        preprocess_dataset(frame, policy)


def test_missing_schema_and_blank_labels_are_not_silently_fixed(approved_fixture):
    frame, policy = approved_fixture
    with pytest.raises(DatasetError):
        validate_raw_frame(frame.drop(columns="regurgitation.1"), policy)
    frame.loc[0, "diseases"] = " "
    with pytest.raises(DatasetError, match="Nhãn"):
        validate_raw_frame(frame, policy)


def test_full_preparation_reproduction_is_deterministic_with_source_positions(approved_fixture):
    frame, policy = approved_fixture
    a = preprocess_dataset(frame, policy)
    b = preprocess_dataset(frame.set_axis(np.arange(100, 100 + len(frame))), policy)
    pd.testing.assert_frame_equal(a["data"], b["data"])
    pd.testing.assert_frame_equal(a["assignments"], b["assignments"])
    assert a["processed_sha256"] == b["processed_sha256"]
    assert a["assignments"].source_data_row_1based.tolist() == list(range(1, 25))


def test_infeasible_coverage_stops_without_changing_approved_rules(approved_fixture, monkeypatch):
    frame, policy = approved_fixture
    calls = []
    def infeasible(pairs, **kwargs):
        calls.append(kwargs)
        return {"missing_classes": {"train": ["A"], "validation": [], "test": []}}
    monkeypatch.setattr("src.data.preprocessing.group_split_feasibility", infeasible)
    with pytest.raises(DatasetError, match="Không phủ đủ lớp"):
        preprocess_dataset(frame, policy)
    assert len(calls) == 1 and calls[0]["minimum"] == 10 and calls[0]["seed"] == 42
    assert calls[0]["ratios"] == [.7, .15, .15]


def test_export_roundtrip_reusable_schema_mapping_and_deterministic_gzip(approved_fixture, tmp_path):
    frame, policy = approved_fixture
    source = tmp_path / "raw.csv"
    frame.to_csv(source, index=False)
    raw_sha = sha256_file(source)
    result = preprocess_dataset(frame, policy)
    output = OutputPaths(tmp_path / "persistent-output")
    manifest = export_preprocessed(result, source, output, expected_source_sha256=raw_sha)
    first = {str(p.relative_to(output.root)): (sha256_file(p), p.stat().st_mtime_ns)
             for p in output.root.rglob("*") if p.is_file()}
    export_preprocessed(result, source, output, expected_source_sha256=raw_sha)
    assert first == {str(p.relative_to(output.root)): (sha256_file(p), p.stat().st_mtime_ns)
                     for p in output.root.rglob("*") if p.is_file()}
    second = OutputPaths(tmp_path / "second-output")
    again = export_preprocessed(result, source, second, expected_source_sha256=raw_sha)
    assert manifest == again
    assert sha256_file(source) == raw_sha and not (tmp_path / "data/processed").exists()
    assert len(list(output.processed_dir.iterdir())) == 3
    all_groups = []
    for name in ("train", "validation", "test"):
        x, y, groups = load_final_split(output, name)
        assert x.columns.tolist() == result["features"]
        assert "constant_zero" in x and "constant_one" in x
        assert not {"group_id", "source_data_row_1based", "regurgitation", "regurgitation.1"}.intersection(x.columns)
        assert set(y) == {0, 1} and len(x) == len(y) == len(groups)
        selected = result["assignments"]["split"].eq(name)
        expected = result["data"].loc[selected].reset_index(drop=True)
        pd.testing.assert_frame_equal(x, expected[result["features"]])
        assert y.tolist() == expected[policy["target"]].map({label: i for i, label in enumerate(result["classes"])}).tolist()
        assert groups.tolist() == result["assignments"].loc[selected, "group_id"].tolist()
        all_groups.append(set(groups))
    assert not (all_groups[0] & all_groups[1] or all_groups[0] & all_groups[2] or all_groups[1] & all_groups[2])
    for relative, meta in manifest["files"].items():
        assert sha256_file(output.root / relative) == meta["sha256"]
    saved_policy = json.loads((output.metadata_dir / "phase2/preprocessing_policy.json").read_text(encoding="utf-8"))
    assert saved_policy["minimum_unique_vectors_per_class"] == 10 and not saved_policy["constant_features"]["fit_in_phase2"]


def test_locked_files_and_changed_raw_are_never_overwritten(approved_fixture, tmp_path):
    frame, policy = approved_fixture
    source = tmp_path / "raw.csv"; frame.to_csv(source, index=False)
    sha = sha256_file(source); result = preprocess_dataset(frame, policy)
    output = OutputPaths(tmp_path / "out")
    export_preprocessed(result, source, output, expected_source_sha256=sha)
    manifest = output.metadata_dir / "phase2/dataset_manifest.json"
    before = manifest.read_bytes()
    target = output.processed_dir / "test.csv.gz"
    target.write_bytes(b"unrelated existing data")
    with pytest.raises(FileExistsError, match="đã khóa"):
        export_preprocessed(result, source, output, expected_source_sha256=sha)
    assert target.read_bytes() == b"unrelated existing data" and manifest.read_bytes() == before
    with pytest.raises(DatasetError, match="fingerprint"):
        load_final_split(output, "test")
    source.write_bytes(b"changed source")
    with pytest.raises(DatasetError, match="Raw thay đổi"):
        export_preprocessed(result, source, output, expected_source_sha256=sha)


def test_modified_assignment_is_rejected_before_any_publication(approved_fixture, tmp_path):
    frame, policy = approved_fixture
    source = tmp_path / "raw.csv"; frame.to_csv(source, index=False)
    result = deepcopy(preprocess_dataset(frame, policy))
    group = result["assignments"].group_id.iloc[0]
    matches = result["assignments"].index[result["assignments"].group_id.eq(group)]
    result["assignments"].loc[matches[0], "split"] = "test"
    result["assignments"].loc[matches[1], "split"] = "train"
    output = OutputPaths(tmp_path / "out")
    with pytest.raises(DatasetError):
        export_preprocessed(result, source, output, expected_source_sha256=sha256_file(source))
    assert not output.root.exists()


def test_locked_export_is_reused_across_runtime_versions_without_rewriting(approved_fixture, tmp_path, monkeypatch):
    frame, policy = approved_fixture
    source = tmp_path / "raw.csv"; frame.to_csv(source, index=False)
    sha = sha256_file(source)
    result = preprocess_dataset(frame, policy)
    output = OutputPaths(tmp_path / "out")
    original = export_preprocessed(result, source, output, expected_source_sha256=sha)
    before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in output.root.rglob("*") if p.is_file()}
    monkeypatch.setattr("src.data.preprocessing.platform.python_version", lambda: "different-Colab-version")
    monkeypatch.setattr("src.data.preprocessing.zlib.ZLIB_VERSION", "different-zlib-version")
    reused = export_preprocessed(result, source, output, expected_source_sha256=sha)
    assert reused == original
    assert before == {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in output.root.rglob("*") if p.is_file()}


def test_same_dataset_with_different_valid_group_assignment_cannot_replace_locked_split(approved_fixture, tmp_path):
    frame, policy = approved_fixture
    source = tmp_path / "raw.csv"; frame.to_csv(source, index=False)
    output = OutputPaths(tmp_path / "out"); sha = sha256_file(source)
    original = preprocess_dataset(frame, policy)
    export_preprocessed(original, source, output, expected_source_sha256=sha)
    before = {str(p): sha256_file(p) for p in output.root.rglob("*") if p.is_file()}
    # Different seed is test-only input; the real config loader forbids changing approved seed 42.
    changed = deepcopy(policy); changed["seed"] = 43
    other = preprocess_dataset(frame, changed)
    assert other["processed_sha256"] == original["processed_sha256"]
    with pytest.raises(FileExistsError, match="đã khóa"):
        export_preprocessed(other, source, output, expected_source_sha256=sha)
    assert before == {str(p): sha256_file(p) for p in output.root.rglob("*") if p.is_file()}
