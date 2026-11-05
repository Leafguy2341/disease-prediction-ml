"""Exercise notebook helpers, never fit or deserialize project checkpoints locally."""
import ast
from collections import Counter
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import warnings

import numpy as np
import pandas as pd
import pytest
from sklearn import config_context
from threadpoolctl import threadpool_limits

from src.data.integrity import read_baseline, verify_training_inputs
from src.data.paths import OutputPaths
from src.models.ensemble import (IntegrityError, class_predictions, phase4_guard,
                                 require, validate_probabilities)
from src.models.runtime import load_training_data, MODEL_NAMES
from src.models.training import to_csr

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/05_structured_inference_check.ipynb"
SCHEMA = json.loads((ROOT / "artifacts/metadata/phase2/feature_schema.json").read_bytes())
FEATURES = SCHEMA["features"]


def notebook():
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def no_fit_or_test_payload():
    with phase4_guard(ROOT) as counters:
        yield
    assert not any(counters.values()), counters


@pytest.fixture
def api():
    namespace = {"np": np, "pd": pd, "time": time, "require": require,
                 "class_predictions": class_predictions,
                 "validate_probabilities": validate_probabilities}
    functions = []
    for cell in notebook()["cells"]:
        if cell["cell_type"] == "code":
            functions += [n for n in ast.parse("".join(cell["source"])).body
                          if isinstance(n, ast.FunctionDef)]
    exec(compile(ast.Module(body=functions, type_ignores=[]), "notebook_helpers", "exec"), namespace)
    return namespace


def test_notebook_uses_existing_bootstrap_loader_and_contains_no_training_or_artifact_writes():
    sys.path.insert(0, str(ROOT / "scripts"))
    from update_colab_notebooks import entry_source
    nb = notebook()
    assert len({c["id"] for c in nb["cells"]}) == len(nb["cells"])
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    by_id = {c["id"]: "".join(c["source"]) for c in code}
    assert {"shared-bootstrap", "verify", "input-contract", "case-selection",
            "prediction-helpers", "model-run", "visible-results", "evidence"} <= set(by_id)
    assert by_id["shared-bootstrap"] == entry_source(3)
    assert "phase.verify()" in by_id["verify"]
    assert "phase._load(name, trusted=True)" in by_id["model-run"]
    assert "model.named_steps[\"csr\"].func is to_csr" in by_id["model-run"]
    for c in code:
        assert isinstance(c["outputs"], list)
        assert c["execution_count"] is None or isinstance(c["execution_count"], int)
        tree = ast.parse("".join(c["source"]))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                name = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
                assert name not in {"fit", "fit_transform", "partial_fit", "train", "train_model",
                                    "build_pipeline", "dump", "write_text", "write_bytes", "to_csv",
                                    "save_phase4", "prepare_probabilities", "evaluate_hard", "evaluate_soft"}
    tags = {"input-contract", "case-selection", "prediction-helpers", "model-run", "visible-results"}
    source = "\n".join("".join(c["source"]) for c in code if c["id"] in tags)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert digest == nb["metadata"]["structured_inference_code_sha256"]
    assert repr(digest) in by_id["verify"]


def test_input_preserves_approved_375_order_and_values_without_mutating_list(api):
    present = ["fever", "cough"]
    frame = api["build_input"](present, FEATURES)
    assert present == ["fever", "cough"]
    assert frame.shape == (1, 375) and frame.columns.tolist() == FEATURES
    assert frame.to_numpy().dtype == np.uint8
    assert set(frame.columns[frame.iloc[0].astype(bool)]) == set(present)
    assert frame.to_numpy().sum() == 2


@pytest.mark.parametrize("case", ["unknown", "duplicate", "empty_list", "wrong_shape", "wrong_width",
                                 "wrong_order", "outside_0_1", "nan", "text_value", "all_zero"])
def test_notebook_negative_checks_reject_each_invalid_case(api, case):
    table = api["invalid_input_checks"](FEATURES).set_index("case")
    assert table.loc[case, "status"] == "PASS"


@pytest.mark.parametrize("value", [None, "cough", [1], np.ones(375), pd.DataFrame(np.ones((1, 375)))])
def test_input_rejects_wrong_contract_types(api, value):
    with pytest.raises(ValueError):
        if isinstance(value, pd.DataFrame):
            api["validate_input"](value, FEATURES)
        else:
            api["build_input"](value, FEATURES)


class PrefittedDouble:
    """A prediction-only test double; has no fit method or trained project result."""
    def __init__(self):
        self.classes_ = np.arange(3)
        self.predict_calls = self.proba_calls = 0
        self.probability = np.array([[.1, .2, .7]])

    def predict(self, x):
        self.predict_calls += 1
        return np.array([2], dtype=np.int64)

    def predict_proba(self, x):
        self.proba_calls += 1
        return self.probability.copy()


def test_invalid_frame_is_rejected_before_calling_model(api):
    model = PrefittedDouble()
    frame = api["build_input"](["cough"], FEATURES).iloc[:, ::-1]
    with pytest.raises(ValueError):
        api["infer_one"](model, "logistic_regression", frame, FEATURES, ["A", "B", "C"])
    assert model.predict_calls == model.proba_calls == 0


def test_top3_uses_real_probability_values_and_decodes_order(api):
    frame = api["build_input"](["cough"], FEATURES)
    model = PrefittedDouble()
    result = api["infer_one"](model, "logistic_regression", frame, FEATURES, ["A", "B", "C"])
    assert result["label_en"] == "C"
    assert [r["label_en"] for r in result["top3"]] == ["C", "B", "A"]
    assert [r["score"] for r in result["top3"]] == [.7, .2, .1]
    assert result["score_kind"] == "uncalibrated_model_score"
    assert model.predict_calls == model.proba_calls == 1


def test_svc_never_calls_or_fabricates_probabilities(api):
    model = PrefittedDouble()
    frame = api["build_input"](["cough"], FEATURES)
    result = api["infer_one"](model, "linear_svc", frame, FEATURES, ["A", "B", "C"])
    assert result["top3"] is None and result["score_kind"] == "label_only_no_probability"
    assert model.proba_calls == 0


@pytest.mark.parametrize("problem", ["class_order", "nan", "sum", "shape", "argmax"])
def test_malformed_probability_is_not_reported_as_a_result(api, problem):
    model = PrefittedDouble()
    if problem == "class_order": model.classes_ = model.classes_[::-1]
    elif problem == "nan": model.probability[0, 0] = np.nan
    elif problem == "sum": model.probability *= .5
    elif problem == "shape": model.probability = np.array([[.2, .8]])
    else: model.probability = np.array([[.8, .1, .1]])
    frame = api["build_input"](["cough"], FEATURES)
    with pytest.raises(IntegrityError):
        api["infer_one"](model, "logistic_regression", frame, FEATURES, ["A", "B", "C"])


def test_timing_separates_warmup_from_repeated_predict_and_proba(api):
    model = PrefittedDouble()
    frame = api["build_input"](["cough"], FEATURES)
    times = api["measure_inference"](model, "logistic_regression", frame, FEATURES, ["A", "B", "C"], repeats=7)
    assert model.predict_calls == model.proba_calls == 8
    assert times["repeats"] == 7 and times["warmup_s"] >= 0
    for method in ("predict", "predict_proba"):
        assert 0 <= times[method + "_min_ms"] <= times[method + "_median_ms"] <= times[method + "_max_ms"]


def test_case_selection_covers_all_categories_without_selecting_test_rows(api):
    x = pd.DataFrame(np.ones((6, 375), dtype=np.uint8), columns=FEATURES)
    y = np.array([0, 0, 0, 1, 1, 2])
    p = {"logistic_regression": np.array([0, 1, 0, 1, 1, 2]),
         "linear_svc": np.array([1, 1, 0, 1, 1, 2])}
    cases = api["select_validation_cases"](x, y, p)
    assert len(cases) <= 4
    assert {r["row_0based"] for r in cases} == {0, 1, 5}
    assert all(key in " / ".join(c["reason"] for c in cases)
               for key in ("LR đúng", "LR sai", "model bất đồng", "support nhỏ nhất"))


def test_missing_selection_category_fails_instead_of_changing_the_rule(api):
    x = pd.DataFrame(np.ones((2, 375), dtype=np.uint8), columns=FEATURES)
    y = np.array([0, 1])
    with pytest.raises(IntegrityError, match="LR sai"):
        api["select_validation_cases"](x, y, {"logistic_regression": y.copy()})


def test_real_locked_train_validation_load_and_input_roundtrip_without_models(api):
    inputs = verify_training_inputs(OutputPaths(ROOT), baseline=read_baseline(ROOT / "configs/phase2_integrity.json"))
    data = load_training_data(OutputPaths(ROOT), inputs)
    x, y, groups = data["validation"]
    assert x.shape == (28120, 375) and len(np.unique(y)) == 587
    assert data["train"][0].shape == (131248, 375)
    for index in (0, 1, len(y) - 1):
        present = [f for f in FEATURES if x.iloc[index][f] == 1]
        assert present
        actual = api["build_input"](present, FEATURES)
        np.testing.assert_array_equal(actual.to_numpy()[0], x.iloc[index].to_numpy())


@pytest.mark.parametrize("bad_model", [None, "knn"])
def test_actual_notebook_loop_releases_models_and_reports_failures_without_fallback(api, bad_model):
    """Execute the real orchestration cell over doubles, not fake project metrics."""
    loaded = []

    def load(name, *, trusted):
        assert trusted is True
        loaded.append(name)
        model = PrefittedDouble()
        model.named_steps = {
            "variance": SimpleNamespace(feature_names_in_=np.array(FEATURES),
                                         get_support=lambda: np.arange(375) < 318),
            "csr": SimpleNamespace(func=to_csr),
            "estimator": SimpleNamespace(n_features_in_=318),
        }
        if name == bad_model:
            model.probability[0, 0] = np.nan
        return model

    frame = api["build_input"](["cough"], FEATURES)
    ns = {**api, "FEATURES": FEATURES, "CLASSES": ["A", "B", "C"], "MODEL_NAMES": MODEL_NAMES,
          "Counter": Counter, "warnings": warnings, "gc": gc,
          "threadpool_limits": threadpool_limits, "config_context": config_context,
          "to_csr": to_csr, "check_is_fitted": lambda step: None, "display": lambda value: None,
          "session": SimpleNamespace(config={"resources": {"blas_threads": 1, "working_memory_mb": 128}}),
          "phase": SimpleNamespace(_load=load, guard=lambda: phase4_guard(ROOT),
                                   predictions={n: np.array([2]) for n in MODEL_NAMES}),
          "validation_cases": [{"case_id": "unit-val", "row_0based": 0, "truth_id": 2}],
          "validation_inputs": {"unit-val": frame},
          "simulated_features": {"sim-base": ["cough"], "sim-add": ["cough", "fever"]},
          "simulated_inputs": {"sim-base": frame,
                               "sim-add": api["build_input"](["cough", "fever"], FEATURES)}}
    cell = next(c for c in notebook()["cells"] if c["id"] == "model-run")
    exec(compile("".join(cell["source"]), "model_run_cell", "exec"), ns)
    assert loaded == list(MODEL_NAMES)
    assert len(ns["checkpoints"]) == 5 and "model" not in ns
    successful = 5 if bad_model is None else 4
    assert len(ns["validation_results"]) == len(ns["timings"]) == successful
    assert len(ns["simulated_results"]) == successful * 2
    assert all(r["truth_id"] is None for r in ns["simulated_results"])
    assert all(r["correct"] for r in ns["validation_results"])
    if bad_model:
        failed = next(r for r in ns["checkpoints"] if r["model"] == bad_model)
        assert failed["reload_schema_environment"] == "PASS" and failed["inference"] == "FAIL"
        assert len(ns["model_issues"]) == 1
        assert not any(r["model"] == bad_model for r in ns["validation_results"] + ns["simulated_results"])
    else:
        assert not ns["model_issues"]
        assert all(r["inference"] == "PASS" for r in ns["checkpoints"])
