"""Adversarial fixtures for counting and split feasibility, not project evidence."""
import pandas as pd
import pytest

from src.data.audit import audit_dataset
from src.data.paths import OutputPaths
from src.data.preprocessing_inspection import (
    class_eligibility, group_split_feasibility, inspect_header, inspect_regurgitation, write_review,
    threshold_split_comparison, both_features_removal_impact, threshold_comparison_figure,
)


def test_literal_header_does_not_confuse_suffix_with_duplicate(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text("diseases,regurgitation,regurgitation.1\nA,0,1\n", encoding="utf-8")
    assert inspect_header(csv) == {"columns": 3, "duplicate_names": {}, "regurgitation": 1, "regurgitation.1": 1}
    csv.write_text("diseases,regurgitation,regurgitation\nA,0,1\n", encoding="utf-8")
    assert inspect_header(csv)["duplicate_names"] == {"regurgitation": 2}


def test_projection_distinguishes_new_conflict_from_expanded_existing_conflict():
    # Three base vectors: A/B pure merge; C,D/E existing-conflict expansion; F/F pure merge.
    frame = pd.DataFrame({"diseases": ["A", "B", "C", "D", "E", "F", "F", "A"],
                          "base1": [0, 0, 0, 0, 0, 1, 1, 0],
                          "base2": [0, 0, 1, 1, 1, 0, 0, 0],
                          "regurgitation": [0, 1, 0, 0, 1, 0, 1, 0],
                          "regurgitation.1": [0] * 8})
    before = frame.copy(deep=True)
    audit = audit_dataset(frame, {"target": "diseases", "near_constant_threshold": .99})
    result = inspect_regurgitation(frame, audit, "diseases")
    row = result["projections"].set_index("removed_columns").loc["regurgitation"]
    assert row.to_dict() == {"unique_vectors": 3, "merged_groups": 3, "collapsed_original_vectors": 3,
                             "conflicting_groups": 2, "new_conflicts_from_pure": 1,
                             "expanded_label_sets": 2, "hypothetical_dedup_records": 6}
    assert result["counts"] == {"matching_rows": 5, "differing_rows": 3, "regurgitation_ones": 3,
                                "regurgitation.1_ones": 0, "both_ones": 0, "exactly_one": 3}
    support = result["disease_support"].set_index("disease")
    assert support.index.tolist() == ["B", "E", "F"]
    assert support.loc["F", "regurgitation_unique_vectors"] == 1
    pd.testing.assert_frame_equal(frame, before)


def test_eligibility_counts_conflicting_labels_separately_and_ignores_raw_multiplicity():
    pairs = pd.DataFrame({"pattern_id": [0, 0, 1, 2], "disease": ["A", "B", "A", "A"], "rows": [100, 5, 1, 1]})
    table, inventory = class_eligibility(pairs, raw_rows=107)
    table = table.set_index("min_unique_vectors")
    assert table.loc[1, "dedup_records"] == 4
    assert table.loc[3, "retained_classes"] == 1
    assert table.loc[3, "dedup_records"] == 3
    assert table.loc[3, "pct_of_dedup_records"] == 75
    assert table.loc[5, "retained_classes"] == 0
    assert inventory.set_index("disease")["unique_vectors"].to_dict() == {"A": 3, "B": 1}


def test_shared_multilabel_groups_are_disjoint_and_coverage_reproducible():
    pairs = pd.DataFrame([(g, label, 1000 if g == 0 else 1)
                          for g in range(5) for label in ["A", "B"]]
                         + [(g, "C", 1) for g in range(5, 25)], columns=["pattern_id", "disease", "rows"])
    before = pairs.copy(deep=True)
    a = group_split_feasibility(pairs, seed=42)
    b = group_split_feasibility(pairs.sample(frac=1, random_state=1), seed=42)
    pd.testing.assert_frame_equal(a["summary"], b["summary"])
    pd.testing.assert_frame_equal(a["class_support"], b["class_support"])
    assert a["overlaps"] == {"train / validation": 0, "train / test": 0, "validation / test": 0}
    assert a["missing_classes"] == {"train": [], "validation": [], "test": []}
    assert a["summary"]["dedup_records"].sum() == 30
    assert a["summary"]["groups"].sum() == 25
    support = a["class_support"].set_index("disease")
    assert support.loc["A", ["train", "validation", "test"]].tolist() == support.loc["B", ["train", "validation", "test"]].tolist()
    pd.testing.assert_frame_equal(pairs, before)


def test_infeasible_coverage_is_reported_instead_of_claiming_stratification():
    pairs = pd.DataFrame({"pattern_id": [0, 1, 1, 2, 0, 2], "disease": ["A", "A", "B", "B", "C", "C"]})
    result = group_split_feasibility(pairs, minimum=2)
    assert any(result["missing_classes"].values())
    assert not any(result["overlaps"].values())
    assert result["summary"]["dedup_records"].sum() == 6
    for name, absent in result["missing_classes"].items():
        support = result["class_support"]
        assert absent == support.loc[support[name] == 0, "disease"].tolist()


def test_rejects_duplicate_edges_instead_of_inflating_independent_support():
    pairs = pd.DataFrame({"pattern_id": [0, 0], "disease": ["A", "A"]})
    with pytest.raises(ValueError):
        class_eligibility(pairs, raw_rows=2)
    with pytest.raises(ValueError):
        group_split_feasibility(pairs)


def test_export_is_aggregate_only_and_checks_all_destinations_before_writing(tmp_path):
    output = OutputPaths(tmp_path)
    output.tables_dir.mkdir(parents=True)
    previous = output.tables_dir / "preprocessing_summary.csv"
    previous.write_text("old evidence\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_review(output, "report", {"preprocessing_summary": pd.DataFrame({"count": [1]})})
    assert not (output.reports_dir / "preprocessing_decision_review.md").exists()
    assert previous.read_text(encoding="utf-8") == "old evidence\n"
    with pytest.raises(ValueError):
        write_review(output, "report", {"preprocessing_assignments": pd.DataFrame({"pattern_id": [1]})})


def test_identical_rerun_preserves_report_bytes(tmp_path):
    output = OutputPaths(tmp_path)
    tables = {"preprocessing_summary": pd.DataFrame({"count": [1]})}
    path = write_review(output, "Báo cáo\n", tables)
    old = path.read_bytes()
    write_review(output, "Báo cáo\n", tables)
    assert path.read_bytes() == old


def test_threshold_comparison_keeps_denominator_and_uses_identical_splitter():
    rows, start = [], 0
    for disease, count in [("A", 1), ("B", 3), ("C", 5), ("D", 10), ("E", 15)]:
        rows.extend((g, disease) for g in range(start, start + count))
        start += count
    pairs = pd.DataFrame(rows, columns=["pattern_id", "disease"])
    analysis = threshold_split_comparison(pairs, raw_rows=3400, seed=42)
    table = analysis["comparison"]
    assert table["retained_classes"].tolist() == [5, 4, 3, 2, 1]
    assert table["excluded_classes"].tolist() == [0, 1, 2, 3, 4]
    assert table["dedup_records"].tolist() == [34, 33, 30, 25, 15]
    assert table.iloc[-1]["pct_of_dedup_records"] == pytest.approx(15 / 34 * 100)
    assert analysis["denominator_records"] == 34
    assert table.iloc[0][["missing_train_classes", "missing_validation_classes", "missing_test_classes"]].sum() >= 2
    for row in table.itertuples():
        baseline = group_split_feasibility(pairs, minimum=row.min_unique_vectors, seed=42)
        pd.testing.assert_frame_equal(analysis["splits"][row.min_unique_vectors]["summary"], baseline["summary"])
        for name in ("validation", "test"):
            assert getattr(row, f"singleton_{name}_classes") == int(baseline["class_support"][name].eq(1).sum())
        assert row.maximum_pairwise_group_overlap == 0


def test_removing_both_features_can_remove_class_eligibility_without_changing_labels():
    frame = pd.DataFrame({"diseases": ["A", "A", "B", "B", "A", "A"],
                          "context": [0, 0, 0, 1, 0, 0],
                          "regurgitation": [0, 1, 0, 1, 1, 1],
                          "regurgitation.1": [0, 0, 1, 1, 0, 0]})
    before = frame.copy(deep=True)
    audit = audit_dataset(frame, {"target": "diseases", "near_constant_threshold": .99})
    result = both_features_removal_impact(frame, audit, "diseases", minimum=2)
    summary, classes = result["summary"], result["class_impact"].set_index("disease")
    assert summary["class_filter_applied"] is False
    assert summary["comparison_denominator_records"] == 4
    assert summary["records_with_either_feature_one"] == 3
    assert summary["raw_records_with_either_feature_one"] == 5
    assert summary["pct_records_with_either_feature_one"] == 75
    assert result["associated_disease_names"] == ["A", "B"]
    assert summary["unique_vectors_before"] == 4 and summary["unique_vectors_after"] == 2
    assert summary["collapsed_original_vectors"] == 2
    assert summary["original_vectors_in_merged_groups"] == 3
    assert summary["merged_projected_groups"] == 1
    assert summary["new_conflicts_from_pure"] == 1
    assert summary["hypothetical_dedup_records_after_projection"] == 3
    assert classes.loc["A", "unique_vectors_before"] == 2
    assert classes.loc["A", "unique_vectors_after"] == 1
    assert classes.loc["B", "vectors_lost"] == 0
    assert summary["eligible_classes_before"] == 2 and summary["eligible_classes_after"] == 1
    assert result["lost_eligible_classes"] == ["A"] and result["gained_eligible_classes"] == []
    assert not {"regurgitation", "regurgitation.1"}.intersection(classes.index)
    pd.testing.assert_frame_equal(frame, before)


def test_explicit_report_update_keeps_existing_csv_protection(tmp_path):
    output = OutputPaths(tmp_path)
    table = pd.DataFrame({"count": [1]})
    path = write_review(output, "initial", {"preprocessing_summary": table})
    with pytest.raises(FileExistsError):
        write_review(output, "revised", {"preprocessing_summary": table})
    write_review(output, "revised", {"preprocessing_summary": table}, update_report=True)
    assert path.read_text(encoding="utf-8") == "revised"
    with pytest.raises(FileExistsError):
        write_review(output, "should not be written", {"preprocessing_summary": pd.DataFrame({"count": [2]})}, update_report=True)
    assert path.read_text(encoding="utf-8") == "revised"


@pytest.mark.parametrize("save", [True, False])
def test_comparison_plot_saves_one_png_or_renders_in_memory(tmp_path, save):
    from io import BytesIO
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg

    table = pd.DataFrame({"min_unique_vectors": [1, 3, 5, 10, 15], "retained_classes": [100, 95, 90, 85, 80],
                          "pct_of_dedup_records": [100, 99.9, 99.8, 99.6, 99.3],
                          "dedup_records": [1000, 999, 998, 996, 993]})
    analysis = {"comparison": table, "seed": 42, "original_classes": 100, "denominator_records": 1000}
    fig, path = threshold_comparison_figure(analysis, OutputPaths(tmp_path), save=save)
    try:
        assert len(fig.axes) == 2
        assert path.suffix == ".png"
        if save:
            assert list((tmp_path / "reports/figures").iterdir()) == [path]
            pixels = mpimg.imread(path)
        else:
            buffer = BytesIO()
            fig.savefig(buffer, format="png", dpi=160)
            buffer.seek(0)
            pixels = mpimg.imread(buffer)
            assert list(tmp_path.iterdir()) == []
        assert pixels.shape[0] > 600 and pixels.shape[1] > 1500 and pixels.std() > .05
        assert "thu hẹp" in fig.axes[1].get_title()
    finally:
        plt.close(fig)
