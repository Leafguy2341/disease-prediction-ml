"""No classifier/feature-transformer fit; metrics may encode their temporary labels."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.exceptions import NotFittedError
from sklearn.utils.validation import check_is_fitted

from src.data.loader import sha256_file
from src.data.paths import OutputPaths
from src.models import training, reporting
from src.models.runtime import MODEL_NAMES, read_training_config

ROOT = Path(__file__).resolve().parents[1]


def metric_label_encoding_only(frame):
    if (frame.f_globals.get("__name__") != "sklearn.preprocessing._label"
            or type(frame.f_locals.get("self")).__name__ != "LabelEncoder"):
        return False
    parent = frame.f_back
    while parent is not None:
        if parent.f_globals.get("__name__") == "sklearn.metrics._classification":
            return True
        parent = parent.f_back
    return False


@pytest.fixture(autouse=True)
def no_training_or_locked_test(monkeypatch):
    """Forbid learning; allow only temporary LabelEncoder inside metric calculation."""
    previous = sys.getprofile()
    original_open = Path.open

    def profile(frame, event, arg):
        if (event == "call" and frame.f_globals.get("__name__", "").startswith("sklearn.")
                and frame.f_code.co_name in {"fit", "fit_transform", "partial_fit"}
                and not metric_label_encoding_only(frame)):
            pytest.fail("Preflight must never fit an estimator or transformer")
        if previous is not None:
            previous(frame, event, arg)

    def guarded_open(path, *args, **kwargs):
        if path.resolve() == (ROOT / "data/processed/test.csv.gz").resolve():
            pytest.fail("Preflight must not open the locked test payload")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    sys.setprofile(profile)
    try:
        yield
    finally:
        sys.setprofile(previous)


def test_visible_notebook_pipeline_constructors_match_the_training_api_without_fit():
    notebook = json.loads((ROOT / "notebooks/03_model_training.ipynb").read_text(encoding="utf-8"))
    assert len(notebook["cells"]) >= 14  # Original 14 baseline cells remain at the same positions.
    config = read_training_config(ROOT)
    namespace = {"session": type("SessionConfig", (), {"config": config})()}
    # Cell 6 contains only imports and the common constructor, never a fit call.
    exec(compile("".join(notebook["cells"][6]["source"]), "pipeline-constructors-only", "exec"), namespace)
    for index, name in zip(range(7, 12), MODEL_NAMES):
        tree = ast.parse("".join(notebook["cells"][index]["source"]))
        assignment = next(node for node in tree.body if isinstance(node, ast.Assign))
        # Execute only the constructor assignment, not display/train_model/fit callbacks.
        exec(compile(ast.Module(body=[assignment], type_ignores=[]), "estimator-constructor-only", "exec"), namespace)
        actual = namespace[assignment.targets[0].id]
        expected = training.build_pipeline(name, config)
        assert [name for name, _ in actual.steps] == [name for name, _ in expected.steps]
        for (_, step), (_, reference) in zip(actual.steps, expected.steps):
            assert type(step) is type(reference)
            assert step.get_params(deep=False) == reference.get_params(deep=False)
        for _, step in actual.steps:
            step._validate_params()
        with pytest.raises(NotFittedError):
            check_is_fitted(actual.named_steps["variance"])
        with pytest.raises(NotFittedError):
            check_is_fitted(actual.named_steps["estimator"])


def test_prediction_batching_preserves_row_order_without_a_trained_model():
    class PredictionSpy:
        def __init__(self):
            self.sizes = []

        def predict(self, frame):
            self.sizes.append(len(frame))
            return frame["fixture_expected"].to_numpy()

    spy = PredictionSpy()
    x = pd.DataFrame({"fixture_expected": np.arange(135) % 3})
    prediction, elapsed = training._predict(spy, x, 64, lambda message: None)
    assert spy.sizes == [64, 64, 7]
    np.testing.assert_array_equal(prediction, x["fixture_expected"])
    assert elapsed >= 0


def test_metrics_use_the_supplied_labels_predictions_and_all_classes():
    metrics = training.validation_metrics(np.array([0, 1, 2, 2]), np.array([0, 2, 2, 2]), 3)
    assert metrics == pytest.approx({"accuracy": .75, "macro_precision": 5 / 9,
                                     "macro_recall": 2 / 3, "macro_f1": .6, "weighted_f1": .65})


def completed_fixture(tmp_path):
    """Artificial checkpoint BYTES for integrity tests; never a fitted model/real result."""
    identity = {"experiment_id": "unit-only-no-fit", "fixture": True}
    folder = tmp_path / "models" / "bernoulli_nb"
    folder.mkdir(parents=True)
    (folder / "pipeline.joblib").write_bytes(b"unit checksum fixture; not a serialized model")
    fit = {"status": "fitted", "model": folder.name, "identity": identity,
           "pipeline_sha256": sha256_file(folder / "pipeline.joblib")}
    (folder / "fit.json").write_bytes(training.json_bytes(fit))
    y, groups = np.array([0, 1, 2, 2]), np.array([10, 11, 12, 13])
    prediction = np.array([0, 2, 2, 2])
    np.savez_compressed(folder / "validation_predictions.npz", y_true=y, y_pred=prediction,
                        group_id=groups, row_0based=np.arange(len(y)))
    metadata = {**fit, "status": "completed", "fit_metadata_sha256": sha256_file(folder / "fit.json"),
                "predictions_sha256": sha256_file(folder / "validation_predictions.npz"),
                "metrics": training.validation_metrics(y, prediction, 3)}
    (folder / "metadata.json").write_bytes(training.json_bytes(metadata))
    return folder, identity, y, groups, metadata


def test_completed_checkpoint_reuse_verifies_predictions_without_fit_or_deserialization(tmp_path, monkeypatch):
    folder, identity, y, groups, metadata = completed_fixture(tmp_path)
    monkeypatch.setattr(training, "build_pipeline", lambda *a, **kw: pytest.fail("Reuse must not build/fit"))
    monkeypatch.setattr(training.joblib, "load", lambda *a, **kw: pytest.fail("Completed reuse must not deserialize"))
    config = read_training_config(ROOT)
    data = {"train": (None, None, None), "validation": (None, y, groups)}
    before = {p.name: (sha256_file(p), p.stat().st_mtime_ns) for p in folder.iterdir()}
    result = training.run_model(folder.name, config, identity, data, folder.parent, progress=lambda message: None)
    assert result["status"] == "reused" and result["metrics"] == metadata["metrics"]
    assert before == {p.name: (sha256_file(p), p.stat().st_mtime_ns) for p in folder.iterdir()}


@pytest.mark.parametrize("damage", ["model_bytes", "identity", "prediction_bytes", "metrics", "label_order", "group_order"])
def test_checkpoint_corruption_or_misalignment_is_rejected_without_deserialization(tmp_path, monkeypatch, damage):
    folder, identity, y, groups, metadata = completed_fixture(tmp_path)
    monkeypatch.setattr(training.joblib, "load", lambda *a, **kw: pytest.fail("Must not deserialize"))
    if damage == "model_bytes":
        (folder / "pipeline.joblib").write_bytes(b"damaged")
    elif damage == "identity":
        identity = {**identity, "changed_version": True}
    elif damage == "prediction_bytes":
        (folder / "validation_predictions.npz").write_bytes(b"damaged")
    elif damage == "metrics":
        metadata["metrics"]["macro_f1"] = 1.0
        (folder / "metadata.json").write_bytes(training.json_bytes(metadata))
    elif damage == "label_order":
        y = y[::-1]
    else:
        groups = groups[::-1]
    with pytest.raises(ValueError):
        training.read_completed_checkpoint(folder, identity, y, groups)


def test_fit_only_checkpoint_requires_explicit_trust_before_deserialization(tmp_path, monkeypatch):
    folder, identity, *_ = completed_fixture(tmp_path)
    (folder / "metadata.json").unlink()
    monkeypatch.setattr(training.joblib, "load", lambda *a, **kw: pytest.fail("Untrusted checkpoint must not deserialize"))
    with pytest.raises(ValueError, match="trusted=True"):
        training.load_fitted_checkpoint(folder, identity)


def test_unfitted_pipelines_and_module_transformer_round_trip_in_fresh_copied_source(tmp_path):
    source = tmp_path / "runtime-source"
    shutil.copytree(ROOT / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__"))
    config = read_training_config(ROOT)
    archive = tmp_path / "unfitted-pipelines.joblib"
    joblib.dump({name: training.build_pipeline(name, config) for name in MODEL_NAMES}, archive)
    script = """
import json, sys
from pathlib import Path
import joblib, numpy as np
from src.models.training import to_csr
def deny_fit(frame, event, arg):
    if event == 'call' and frame.f_globals.get('__name__', '').startswith('sklearn.') and frame.f_code.co_name in {'fit','fit_transform','partial_fit'}:
        raise AssertionError('No fitting allowed')
sys.setprofile(deny_fit)
pipelines = joblib.load(sys.argv[1])
for pipeline in pipelines.values():
    assert not hasattr(pipeline.named_steps['variance'], 'variances_')
    transformer = pipeline.named_steps['csr']
    assert transformer.func is to_csr
    converted = transformer.transform(np.array([[0, 1], [1, 0]], dtype=np.uint8))
    assert converted.format == 'csr' and converted.dtype == np.float64
    assert converted.toarray().tolist() == [[0, 1], [1, 0]]
assert Path(sys.modules['src.models.training'].__file__).is_relative_to(Path(sys.argv[2]))
print(json.dumps({'unfitted_pipelines_reloaded':len(pipelines),'fit_calls':0}))
"""
    env = {**os.environ, "PYTHONPATH": str(source), "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-c", script, str(archive), str(source)], cwd=tmp_path,
                            env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"unfitted_pipelines_reloaded": 5, "fit_calls": 0}


def test_failed_records_have_no_fabricated_metrics_or_figures(tmp_path):
    records = [{"model": "knn", "status": "failed", "error": "unit fixture: no fit attempted"}]
    table = reporting.comparison_table(records)
    assert table[list(reporting.METRICS)].isna().all().all()
    assert reporting.validation_figures(records, OutputPaths(tmp_path), {}, None, None) == []
    assert list(tmp_path.iterdir()) == []
