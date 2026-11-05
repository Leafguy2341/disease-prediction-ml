"""Opt-in check against existing Phase 1 evidence using the actual, unchanged CSV."""
import json
import os
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

from src.data.audit import audit_dataset
from src.data.eda import analyze_eda
from src.data.io import read_config
from src.data.loader import dataset_path, load_dataset, sha256_file
from src.data.paths import resolve_paths


@pytest.mark.skipif(os.environ.get("DISEASE_RUN_DATA_REGRESSION") != "1", reason="Set DISEASE_RUN_DATA_REGRESSION=1; requires original CSV and historical reports.")
def test_actual_source_csv_reproduces_all_historical_metrics_and_tables():
    root = Path(__file__).resolve().parents[1]
    config = read_config(root)
    source = dataset_path(resolve_paths(root), config)
    manifest = json.loads((root / "artifacts/metadata/dataset_manifest.json").read_text(encoding="utf-8"))
    assert sha256_file(source) == manifest["sha256"], "This regression must use the same source CSV."
    frame = load_dataset(source, config["target"])
    audit = audit_dataset(frame, config)
    eda = analyze_eda(frame, audit, config)
    for result, name in [(audit["summary"], "dataset_audit.json"), (eda["summary"], "eda_metrics.json")]:
        assert result == json.loads((root / "reports" / name).read_text(encoding="utf-8"))
    for prefix, results in [("audit", audit), ("eda", eda)]:
        for name, value in results.items():
            if isinstance(value, pd.DataFrame):
                indexed = name in {"class_profiles", "class_profile_counts", "cooccurrence", "correlation", "jaccard"}
                previous = pd.read_csv(root / "reports/tables" / f"{prefix}_{name}.csv", index_col=0 if indexed else None)
                # CSV round-trips turn empty strings/None into NA; normalize both sides equally.
                current = pd.read_csv(StringIO(value.to_csv(index=indexed)), index_col=0 if indexed else None)
                pd.testing.assert_frame_equal(current, previous, check_dtype=False, check_exact=False, rtol=1e-10, atol=1e-12)
    rows = pd.read_csv(root / "reports/tables/audit_row_pattern_ids.csv")
    assert rows["pattern_id"].tolist() == audit["pattern_ids"].tolist()


@pytest.mark.skipif(os.environ.get("DISEASE_RUN_DATA_REGRESSION") != "1", reason="Requires the original CSV and finalized Phase 2 outputs.")
def test_actual_finalized_splits_match_independent_preparation_and_reproduce_seed42():
    from src.data.preprocessing import read_phase2_policy, preprocess_dataset, load_final_split
    from src.data.paths import OutputPaths

    root = Path(__file__).resolve().parents[1]
    paths = resolve_paths(root)
    output = OutputPaths(paths.output_root)
    config = read_config(root)
    source = dataset_path(paths, config)
    manifest = json.loads((output.metadata_dir / "phase2/dataset_manifest.json").read_text(encoding="utf-8"))
    assert sha256_file(source) == manifest["raw"]["sha256"]
    raw = load_dataset(source, config["target"])
    policy = read_phase2_policy(root)
    a = preprocess_dataset(raw, policy)
    b = preprocess_dataset(raw, policy)
    pd.testing.assert_frame_equal(a["data"], b["data"])
    pd.testing.assert_frame_equal(a["assignments"], b["assignments"])
    assert a["processed_sha256"] == b["processed_sha256"] == manifest["processed"]["sha256"]
    assert (len(a["data"]), len(a["features"]), len(a["classes"])) == (187434, 375, 587)
    assert a["split_summary"]["dedup_records"].tolist() == [131248, 28120, 28066]
    assert a["split_summary"]["groups"].tolist() == [117211, 25127, 25128]
    assert a["validation"]["singleton_validation_classes"] == 33
    assert a["validation"]["singleton_test_classes"] == 41
    # Independent full-row pandas equality, not the packed-vector preparation helper.
    independent = raw.drop(columns=policy["drop_features"]).drop_duplicates()
    counts = independent.groupby(policy["target"]).size()
    independent = independent.loc[independent[policy["target"]].isin(counts.index[counts >= 10])]
    independent = independent[a["features"] + [policy["target"]]].reset_index(drop=True)
    pd.testing.assert_frame_equal(a["data"], independent)
    loaded, groups = [], []
    for name in ("train", "validation", "test"):
        x, encoded, group = load_final_split(output, name)
        assert x.columns.tolist() == a["features"] and len(set(encoded)) == 587
        restored = x.copy()
        restored[policy["target"]] = [a["classes"][i] for i in encoded]
        selected = a["assignments"].loc[a["assignments"]["split"].eq(name)]
        assert selected["group_id"].tolist() == group.tolist()
        restored["source_position"] = selected["source_data_row_1based"].to_numpy()
        loaded.append(restored)
        groups.append(set(group))
    combined = pd.concat(loaded).sort_values("source_position").drop(columns="source_position").reset_index(drop=True)
    pd.testing.assert_frame_equal(combined, independent)
    assert not (groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])
    assert not combined.duplicated().any()
    for relative, entry in manifest["files"].items():
        assert sha256_file(output.root / relative) == entry["sha256"]
