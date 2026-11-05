"""Audit-tool tests only; no trained models, fitting or locked test CSV."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_phase3_results.py"
API = runpy.run_path(str(SCRIPT))


def test_read_only_guard_blocks_storage_writes_mutations_test_and_fitting(tmp_path):
    from sklearn.feature_selection import VarianceThreshold
    storage = tmp_path / "drive"
    storage.mkdir()
    kept = storage / "keep.txt"
    kept.write_text("unchanged", encoding="utf-8")
    previous = sys.getprofile()
    with API["read_only_audit"](storage) as counts:
        assert kept.read_text(encoding="utf-8") == "unchanged"
        with pytest.raises(RuntimeError, match="persistent write"):
            kept.write_text("changed", encoding="utf-8")
        with pytest.raises(RuntimeError, match="filesystem mutation"):
            kept.unlink()
        with pytest.raises(RuntimeError, match="test payload"):
            (tmp_path / "test.csv.gz").read_bytes()
        with pytest.raises(API["AuditFitForbidden"], match="fitting is forbidden"):
            VarianceThreshold().fit([[0], [1]])  # Guard stops before the fit body.
        (tmp_path / "scratch.txt").write_text("ephemeral", encoding="utf-8")
    assert sys.getprofile() is previous
    assert kept.read_text(encoding="utf-8") == "unchanged"
    assert counts["model_or_feature_fit_attempts"] == counts["test_payload_open_attempts"] == 1
    assert counts["persistent_write_attempts"] == 2


def test_warning_records_preserve_messages_counts_and_stages():
    a = "ConvergenceWarning: unit fixture: iteration limit"
    b = "FutureWarning: unit fixture: renamed argument"
    result = API["warning_rows"]({"warnings": [a, a]}, {"warnings": [a, a, b]})
    assert result["status"] == "PASS" and result["recorded_total"] == 3
    assert result["rows"] == [
        {"step": "fit", "category": "ConvergenceWarning", "message": "unit fixture: iteration limit",
         "occurrences": 2, "severity": "BLOCKER",
         "recommended_response": "Resolve convergence credibility before comparison; do not retrain without approval."},
        {"step": "validation_predict", "category": "FutureWarning", "message": "unit fixture: renamed argument",
         "occurrences": 1, "severity": "INFO",
         "recommended_response": "Compatibility notice; preserve it and review the affected API."}]
    assert API["warning_rows"]({}, {})["status"] == "NOT VERIFIED"
    mismatch = API["warning_rows"]({"warnings": [a]}, {"warnings": [b]})
    assert mismatch["status"] == "REVIEW" and mismatch["rows"][0]["step"] == "unknown_stage"


def test_experiment_selection_never_guesses_between_runs(tmp_path):
    choose = API["choose_experiment"]
    for name in ("run-one", "run-two"):
        folder = tmp_path / "artifacts/models/phase3" / name / "knn"
        folder.mkdir(parents=True)
        (folder / "fit.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="candidates"):
        choose(tmp_path, ["knn"])
    assert choose(tmp_path, ["knn"], "run-one").name == "run-one"
    with pytest.raises(ValueError, match="one folder"):
        choose(tmp_path, ["knn"], "../escape")


def test_packet_is_lossless_and_has_a_verifiable_checksum(capsys):
    packet = {"readiness": "NOT VERIFIED", "fixture": "Tiếng Việt, không phải kết quả model"}
    API["emit_packet"](packet)
    lines = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    raw = gzip.decompress(base64.b64decode(lines["AUDIT_GZIP_BASE64"]))
    assert hashlib.sha256(raw).hexdigest() == lines["AUDIT_SHA256"]
    assert json.loads(raw) == packet


def test_missing_project_checkpoints_stop_read_only_before_cache_or_model_load(tmp_path, monkeypatch):
    from src.models.runtime import read_training_config
    root = SCRIPT.parents[1]
    session = SimpleNamespace(paths=SimpleNamespace(project_root=root, storage_root=root,
                                                   cache_dir=tmp_path / "cache", runtime="Windows unit test"),
                              config=read_training_config(root), identity=None)
    import joblib
    monkeypatch.setattr(joblib, "load", lambda *a, **kw: pytest.fail("No checkpoint is available to load"))
    # This fixture applies while project artifacts remain remote-only.
    if (root / "artifacts/models/phase3").is_dir():
        pytest.skip("Real checkpoints now exist; do not assume their inventory")
    with pytest.raises(ValueError, match="candidates"):
        API["audit_phase3"](session)
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("damaged_csv", [False, True])
def test_full_orchestration_with_untrained_test_doubles_never_fits_or_writes(tmp_path, monkeypatch, damaged_csv):
    """Positive/negative routing fixture; not actual fitted models or project metrics."""
    import numpy as np
    import pandas as pd
    from sklearn.base import BaseEstimator
    from src.data import integrity
    from src.data.paths import OutputPaths
    from src.models import runtime, training

    root = SCRIPT.parents[1]
    storage = tmp_path / "drive"
    features = [f"fixture_{i}" for i in range(375)]
    mask = np.arange(375) < 318
    x = pd.DataFrame(np.zeros((4, 375), dtype=np.uint8), columns=features)
    x.iloc[[1, 3], :318] = 1
    y, groups = np.array([0, 1, 2, 2]), np.arange(4)
    processed = {"records": 8, "classes": 3, "features": 375, "sha256": "synthetic-data-only"}
    config = runtime.read_training_config(root)
    config["expected_phase2"] = processed
    config["resources"]["min_available_ram_gb"] = 0
    inventory = {n: {"sha256": "unit-only"} for n in (
        "data/processed/train.csv.gz", "data/processed/validation.csv.gz",
        "artifacts/metadata/phase2/feature_schema.json", "artifacts/metadata/phase2/label_mapping.json")}
    inputs = {"manifest": {"processed": processed, "files": inventory}, "manifest_sha256": "unit-manifest",
              "schema": {"features": features}, "labels": {"classes": ["A", "B", "C"]}}
    monkeypatch.setattr(integrity, "read_baseline", lambda *a: {"approved_manifest_sha256": ["unit-manifest"]})
    monkeypatch.setattr(integrity, "verify_training_inputs", lambda *a, **kw: inputs)
    monkeypatch.setattr(runtime, "cache_training_inputs", lambda *a, **kw: OutputPaths(tmp_path / "cache"))
    monkeypatch.setattr(runtime, "load_training_data", lambda *a: {"train": (x, y, groups), "validation": (x, y, groups)})
    identity = training.experiment_identity(root, config, inputs)
    run = storage / "artifacts/models/phase3" / identity["experiment_id"]

    class TestStep(BaseEstimator):
        def __init__(self):
            self.fitted_ = True
        def fit(self, *a, **kw):
            raise AssertionError("No fitting even for a test double")
        def get_params(self, **kw):
            return {}

    class TestVariance(TestStep):
        feature_names_in_ = features
        variances_ = np.where(mask, .25, 0)
        def get_support(self):
            return mask

    class TestEstimator(TestStep):
        n_features_in_ = 318

    class TestCSR(TestStep):
        func = staticmethod(training.to_csr)

    class TestPipeline:
        n_features_in_ = 375
        classes_ = np.arange(3)
        def __init__(self):
            self.steps = [("variance", TestVariance()), ("csr", TestCSR()), ("estimator", TestEstimator())]
            self.named_steps = dict(self.steps)

    monkeypatch.setattr(training, "build_pipeline", lambda *a: TestPipeline())
    monkeypatch.setattr(training, "load_fitted_checkpoint", lambda *a, **kw: TestPipeline())
    monkeypatch.setattr(training, "_predict", lambda *a: (y.copy(), 0.0))
    scores = training.validation_metrics(y, y, 3)
    rows, summary_models = [], []
    for name in runtime.MODEL_NAMES:
        folder = run / name
        folder.mkdir(parents=True)
        (folder / "pipeline.joblib").write_bytes(b"unit-only; never deserialize this fixture")
        np.savez_compressed(folder / "validation_predictions.npz", y_true=y, y_pred=y, group_id=groups, row_0based=np.arange(4))
        fit = {"identity": identity, "model": name, "status": "fitted", "pipeline_sha256": training.sha256_file(folder / "pipeline.joblib"),
               "fit_seconds": 1.0, "n_input_features": 375, "n_retained_features": 318, "parameters": {},
               "environment": {"unit_fixture_not_a_training_run": True}, "sampled_peak_rss_mb": 1.0,
               "variance_threshold": 0, "warnings": []}
        (folder / "fit.json").write_bytes(training.json_bytes(fit))
        metadata = {**fit, "status": "completed", "metrics": scores, "prediction_seconds": 2.0,
                    "fit_metadata_sha256": training.sha256_file(folder / "fit.json"),
                    "predictions_sha256": training.sha256_file(folder / "validation_predictions.npz")}
        (folder / "metadata.json").write_bytes(training.json_bytes(metadata))
        rows.append({"model": name, **scores, "fit_seconds": 1.0, "prediction_seconds": 2.0,
                     "n_retained_features": 318, "sampled_peak_rss_mb": 1.0, "warnings": 0})
        summary_models.append({"model": name, "metrics": scores})
    csv = storage / "reports/tables" / f"phase3_{run.name}_validation_comparison.csv"
    csv.parent.mkdir(parents=True)
    if damaged_csv:
        rows[0]["macro_f1"] = .123
    pd.DataFrame(rows).to_csv(csv, index=False)
    summary = storage / "artifacts/metadata/phase3" / run.name / "run_summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_bytes(training.json_bytes({"identity": identity, "models": summary_models,
                                             "comparison_sha256": training.sha256_file(csv), "figures": [], "phase4_ready": True}))
    before = {p.relative_to(storage).as_posix(): (training.sha256_file(p), p.stat().st_mtime_ns) for p in storage.rglob('*') if p.is_file()}
    session = SimpleNamespace(paths=SimpleNamespace(storage_root=storage, project_root=root, cache_dir=tmp_path / "cache", runtime="unit doubles only"),
                              config=config, identity=identity)
    result = API["audit_phase3"](session)
    assert all(m["status"] == "PASS" for m in result["models"].values()), {n: m.get("error", m["status"]) for n, m in result["models"].items()}
    assert result["feature_masks_identical"] == "PASS"
    assert result["readiness"] == ("BLOCKER" if damaged_csv else "REVIEW")
    assert (result["comparison_csv_and_summary"] == "PASS") is not damaged_csv
    assert all(result["guards"][k] == 0 for k in ("model_or_feature_fit_attempts", "test_payload_open_attempts", "persistent_write_attempts"))
    after = {p.relative_to(storage).as_posix(): (training.sha256_file(p), p.stat().st_mtime_ns) for p in storage.rglob('*') if p.is_file()}
    assert before == after
