"""Validate exported evidence against raw data and independent pandas operations."""
from pathlib import Path
import argparse
import json
import sys

import matplotlib.image as mpimg
import nbformat
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.io import read_config, dataset_path, load_dataset, save_json, sha256_file
from src.data.paths import OutputPaths, resolve_paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-run")
    parser.add_argument("--eda-run")
    parser.add_argument("--execution-run")
    args = parser.parse_args()
    paths = resolve_paths(ROOT)
    audit_output = OutputPaths(paths.output_root, args.audit_run)
    eda_output = OutputPaths(paths.output_root, args.eda_run)
    execution_output = OutputPaths(paths.output_root, args.execution_run)
    config = read_config(ROOT)
    path = dataset_path(paths, config)
    read_json = lambda path: json.loads(path.read_text(encoding="utf-8"))
    table = lambda name: pd.read_csv((audit_output if name.startswith("audit_") else eda_output).tables_dir / f"{name}.csv")
    audit = read_json(audit_output.reports_dir / "dataset_audit.json")
    eda = read_json(eda_output.reports_dir / "eda_metrics.json")
    manifest = read_json(audit_output.metadata_dir / "dataset_manifest.json")
    assert sha256_file(path) == manifest["sha256"]
    df = load_dataset(path, config["target"])
    features = df.drop(columns=config["target"])
    # Independent of lossless packbits grouping used by src.data.audit.
    assert int(df.duplicated().sum()) == audit["exact_duplicate_excess_rows"]
    assert int(features.duplicated().sum()) == audit["repeated_pattern_excess_rows"]
    assert int(df.duplicated(keep=False).sum()) == audit["rows_in_exact_duplicate_groups"]
    assert int(features.duplicated(keep=False).sum()) == audit["rows_in_repeated_patterns"]
    assert df.shape == (audit["rows"], audit["columns"])
    groups = table("audit_pattern_groups")
    pairs = table("audit_pattern_labels")
    row_ids = table("audit_row_pattern_ids")
    classes = table("audit_class_distribution")
    assert len(row_ids) == len(df)
    assert np.array_equal(row_ids["data_row_1based"], np.arange(1, len(df) + 1))
    assert np.array_equal(row_ids["disease"], df[config["target"]])
    assert row_ids["pattern_id"].nunique() == audit["unique_feature_vectors"] == len(groups)
    assert groups["rows"].sum() == pairs["rows"].sum() == classes["samples"].sum() == len(df)
    assert len(groups[groups["distinct_labels"] > 1]) == audit["conflicting_pattern_groups"]
    assert groups.loc[groups["distinct_labels"] > 1, "rows"].sum() == audit["rows_in_conflicting_patterns"]
    pd.testing.assert_series_equal(
        row_ids.groupby("pattern_id").size().sort_index(),
        groups.set_index("pattern_id")["rows"].sort_index(), check_names=False,
    )
    pd.testing.assert_series_equal(
        df[config["target"]].value_counts().sort_index(),
        classes.set_index("disease")["samples"].sort_index(), check_names=False,
    )
    assert np.isclose(groups["majority_label_rows"].sum() / len(df), audit["empirical_pattern_majority_ceiling"])
    freq = table("eda_symptom_frequency").set_index("feature")
    active = table("eda_active_distribution")
    cooccurrence = pd.read_csv(eda_output.tables_dir / "eda_cooccurrence.csv", index_col=0)
    correlation = pd.read_csv(eda_output.tables_dir / "eda_correlation.csv", index_col=0)
    np.testing.assert_array_equal(features.sum().to_numpy(), freq.loc[features.columns, "present_count"].to_numpy())
    np.testing.assert_array_equal(np.diag(cooccurrence), freq.loc[cooccurrence.index, "present_count"])
    np.testing.assert_array_equal(cooccurrence, cooccurrence.T)
    np.testing.assert_allclose(correlation, correlation.T, equal_nan=True, atol=1e-12)
    assert freq["present_count"].sum() == int(np.dot(active["active_symptoms"], active["rows"]))
    assert active["rows"].sum() == len(df)
    assert eda["recommendation"] == audit["recommendation"]
    existing_notebook_verified = None
    if "preserved_existing_notebook" in manifest:
        existing = manifest["preserved_existing_notebook"]
        if (ROOT.parent / existing["name"]).is_file():
            assert sha256_file(ROOT.parent / existing["name"]) == existing["sha256"]
            existing_notebook_verified = True
    notebooks = []
    for name in ["00_dataset_audit.ipynb", "01_eda.ipynb"]:
        notebook_file = execution_output.reports_dir / "notebooks" / name if args.execution_run else ROOT / "notebooks" / name
        notebook = nbformat.read(notebook_file, as_version=4)
        nbformat.validate(notebook)
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        if args.execution_run:
            assert all(c.execution_count is not None for c in code_cells)
        errors = [o for c in code_cells for o in c.get("outputs", []) if o.output_type == "error"]
        assert not errors
        notebooks.append({"name": name, "code_cells": len(code_cells), "errors": len(errors),
                          "embedded_pngs": sum("image/png" in o.get("data", {}) for c in code_cells for o in c.get("outputs", []))})
    assert notebooks[1]["embedded_pngs"] == 8
    images = []
    for image in sorted(eda_output.figures_dir.glob("*.png")):
        array = mpimg.imread(image)
        assert array.shape[0] > 400 and array.shape[1] > 800
        assert array.std() > .01
        assert "<svg" in image.with_suffix(".svg").read_text(encoding="utf-8")
        images.append({"name": image.name, "shape": list(array.shape), "sha256": sha256_file(image)})
    assert len(images) == 8
    if audit_output.models_dir.is_dir():
        assert not [p for p in audit_output.models_dir.iterdir() if p.name != ".gitkeep"]
    for name in [ROOT / "README.md", audit_output.reports_dir / "dataset_audit.md", eda_output.reports_dir / "eda_summary.md"]:
        assert name.stat().st_size > 500
    result = {"status": "PASS", "independent_raw_duplicate_checks": True,
              "raw_sha256": manifest["sha256"], "existing_notebook_verified": existing_notebook_verified,
              "tables": len(set(audit_output.tables_dir.glob("audit_*.csv"))) + len(set(eda_output.tables_dir.glob("eda_*.csv"))),
              "notebook_execution_checked": bool(args.execution_run),
              "notebooks": notebooks, "figures": images,
              "no_trained_model_artifacts": True,
              "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha256_file(p)
                                for folder in ["src", "scripts", "configs"]
                                for p in sorted((ROOT / folder).rglob("*")) if p.suffix in {".py", ".json"}}}
    validation_output = paths.new_run("validation")
    save_json(validation_output.metadata_dir / "validation.json", result)
    print(f"Validation metadata: {validation_output.metadata_dir}")
    print(json.dumps({k: v for k, v in result.items() if k not in {"source_sha256", "figures"}}, indent=2))


if __name__ == "__main__":
    main()
