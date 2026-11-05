"""Small adversarial fixtures, not fabricated project data or EDA evidence."""
import numpy as np
import pandas as pd
import pytest

from src.data.audit import audit_dataset, exact_pattern_ids
from src.data.eda import analyze_eda
from src.data.io import DatasetError, dataset_path, load_dataset


@pytest.fixture
def config():
    return {"target": "diseases", "near_constant_threshold": .99, "correlation_threshold": .8}


@pytest.fixture
def small_frame():
    return pd.DataFrame({"diseases": ["A", "A", "B", "B", "B"],
                         "a": [1, 1, 1, 0, 0], "b": [0, 0, 0, 1, 1], "constant": [0] * 5})


def test_exact_duplicates_and_conflicts_are_distinct(small_frame, config):
    audit = audit_dataset(small_frame, config)
    summary = audit["summary"]
    assert summary["unique_feature_vectors"] == 2
    assert summary["exact_duplicate_excess_rows"] == int(small_frame.duplicated().sum()) == 2
    assert summary["rows_in_exact_duplicate_groups"] == 4
    assert summary["repeated_pattern_excess_rows"] == 3
    assert summary["rows_in_repeated_patterns"] == 5
    assert summary["conflicting_pattern_groups"] == 1
    assert summary["rows_in_conflicting_patterns"] == 3
    assert summary["empirical_pattern_majority_ceiling"] == .8
    assert audit["pattern_labels"]["rows"].sum() == len(small_frame)
    assert audit["pattern_groups"]["rows"].sum() == len(small_frame)


def test_lossless_bit_packing_preserves_last_column():
    frame = pd.DataFrame(np.zeros((4, 9), dtype=np.uint8))
    frame.iloc[1, 8] = 1
    frame.iloc[2, 0] = 1
    ids, counts = exact_pattern_ids(frame)
    assert ids[0] == ids[3]
    assert len(set(ids[:3])) == 3
    assert sorted(counts) == [1, 1, 2]


def test_mixed_values_and_missing_are_grouped_exactly():
    features = pd.DataFrame({"text": ["x", "x", "x", "y"], "value": [None, None, 256, 256]})
    ids, counts = exact_pattern_ids(features)
    assert ids[0] == ids[1]
    assert len(set(ids[[0, 2, 3]])) == 3
    assert sorted(counts) == [1, 1, 2]


def test_missing_target_is_not_treated_as_observed_disease(small_frame, config):
    small_frame.loc[[0, 1], "diseases"] = None
    audit = audit_dataset(small_frame, config)
    assert audit["summary"]["recommendation"] == "NO-GO"
    assert audit["summary"]["empirical_pattern_majority_ceiling"] is None
    assert audit["pattern_groups"]["missing_label_rows"].sum() == 2
    with pytest.raises(DatasetError, match="Nhãn"):
        analyze_eda(small_frame, audit, config)


def test_loader_does_not_wrap_invalid_values(tmp_path, config):
    path = tmp_path / "values.csv"
    path.write_text("diseases,a,b\nA,256,-1\nB,0,1\n", encoding="utf-8")
    frame = load_dataset(path, "diseases")
    assert frame.loc[0, "a"] == 256
    assert frame.loc[0, "b"] == -1
    audit = audit_dataset(frame, config)
    assert audit["summary"]["invalid_binary_cells"] == 2
    with pytest.raises(DatasetError, match="0/1"):
        analyze_eda(frame, audit, config)


@pytest.mark.parametrize("content", ["diseases,a,a\nA,0,1\n", "wrong,a\nA,1\n", "diseases,a\n"])
def test_schema_errors_have_actionable_messages(tmp_path, content):
    path = tmp_path / "bad.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(DatasetError):
        load_dataset(path, "diseases")


def test_missing_explicit_path_fails_without_silent_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("DISEASE_DATA_PATH", str(tmp_path / "absent.csv"))
    with pytest.raises(FileNotFoundError, match="DISEASE_DATA_PATH"):
        dataset_path(tmp_path, {"dataset_candidates": ["other.csv"]})


def test_cooccurrence_accumulates_without_uint8_overflow(config):
    frame = pd.DataFrame({"diseases": ["A"] * 150 + ["B"] * 150,
                          "a": np.ones(300, dtype=np.uint8),
                          "b": np.ones(300, dtype=np.uint8),
                          "c": np.tile([0, 1], 150).astype(np.uint8)})
    eda = analyze_eda(frame, audit_dataset(frame, config), config)
    assert eda["cooccurrence"].loc["a", "b"] == 300
    assert eda["cooccurrence"].loc["b", "c"] == 150
    assert np.isnan(eda["correlation"].loc["a", "b"])
    assert eda["jaccard"].loc["a", "c"] == .5


def test_phi_matches_independent_pandas_correlation(small_frame, config):
    eda = analyze_eda(small_frame, audit_dataset(small_frame, config), config)
    expected = small_frame.drop(columns="diseases").corr()
    np.testing.assert_allclose(eda["correlation"], expected, atol=1e-12, equal_nan=True)
    assert eda["symptom_frequency"].set_index("feature").loc["a", "present_count"] == 3
