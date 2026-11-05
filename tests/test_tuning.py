"""Offline tuning orchestration with synthetic fixtures. Never fit a real estimator."""
from copy import deepcopy
import ast
import io
import json
from pathlib import Path
from types import SimpleNamespace
import warnings

import matplotlib
matplotlib.use("Agg", force=True)  # Headless verification; never opens a Tk/desktop window.
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import f1_score

from src.data.paths import OutputPaths, RuntimePaths
from src.models import ensemble as en, training, tuning as tu, tuned_ensemble as te
from src.models.runtime import MODEL_NAMES, read_training_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def forbid_learning_test_and_protected_writes():
    with en.phase4_guard(ROOT) as counts:
        yield
    assert not any(counts.values())


@pytest.fixture
def config():
    return read_training_config(ROOT)


@pytest.fixture
def train():
    # Repeated vectors/groups include conflicting labels, just as the approved policy allows.
    rng = np.random.default_rng(42)
    x = pd.DataFrame(rng.integers(0, 2, (36, 375), dtype=np.uint8), columns=[f"unit_feature_{i}" for i in range(375)])
    y = np.tile(np.arange(3), 12)
    groups = np.repeat(np.arange(18), 2)
    x.iloc[1::2] = x.iloc[::2].to_numpy()
    return x, y, groups


def test_fixed_spaces_baseline_candidates_and_bounded_pipelines_without_fit(config):
    before = deepcopy(config)
    plan = tu.search_plan(config)
    assert plan["folds"] == 3 and plan["seed"] == 42
    assert len(tu.plan_table(config)) == 15
    for name, candidates in plan["candidates"].items():
        assert len(candidates) == 3 and candidates[0] == config["models"][name]
        key, values = tu.SEARCH[name]
        assert {p[key] for p in candidates} == set(values)
        for params in candidates:
            candidate = deepcopy(config)
            candidate["resources"] = plan["resources"]
            candidate["models"][name] = params
            pipeline = training.build_pipeline(name, candidate)
            assert pipeline.named_steps["variance"].threshold == 0
            assert not hasattr(pipeline.named_steps["variance"], "variances_")
            assert pipeline.named_steps["csr"].func is training.to_csr
            for _, step in pipeline.steps:
                step._validate_params()
    assert config == before
    enlarged = deepcopy(config)
    enlarged["resources"].update(max_workers=64, blas_threads=64, prediction_batch_size=4096, working_memory_mb=8192)
    limits = tu.search_plan(enlarged)["resources"]
    assert (limits["max_workers"], limits["blas_threads"], limits["prediction_batch_size"], limits["working_memory_mb"]) == (2, 1, 64, 128)


def test_actual_train_groups_used_deterministically_and_no_group_leakage(train, config):
    plan = tu.search_plan(config)
    first = tu.grouped_folds(train[1], train[2], 3, plan)
    second = tu.grouped_folds(train[1], train[2], 3, plan)
    np.testing.assert_array_equal(first[1], second[1])
    for (a, b), inventory in zip(first[0], first[2]):
        assert not set(train[2][a]) & set(train[2][b])
        assert len(set(train[2][b])) == inventory["holdout_groups"]
    assert set(np.concatenate([b for _, b in first[0]])) == set(range(len(train[0])))


def test_scoring_fixed_label_universe_missing_classes_are_zero_not_dropped(config):
    y = np.array([0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])
    groups = np.array([0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    folds, _, inventory, _ = tu.grouped_folds(y, groups, 3, tu.search_plan(config))
    assert any(r["missing_train_classes"] or r["missing_holdout_classes"] for r in inventory)
    for _, score_rows in folds:
        truth = y[score_rows]
        actual = training.validation_metrics(truth, truth, 3)["macro_f1"]
        assert actual == pytest.approx(f1_score(truth, truth, labels=np.arange(3), average="macro", zero_division=0))
        assert actual == pytest.approx(len(set(truth)) / 3)


def synthetic_trials(plan, *, fail_model=None):
    return [{"model": name, "candidate": i, "parameters": params,
             "attempts": [{"fold": k, "status": "failed" if name == fail_model else "completed",
                           "macro_f1": .5 if i == 0 else .6 if i == 1 else .6}
                          for k in range(plan["folds"])]}
            for name in MODEL_NAMES for i, params in enumerate(plan["candidates"][name])]


def test_selection_uses_only_complete_cv_mean_stable_ties_and_rejects_partial(config):
    plan = tu.search_plan(config)
    records = synthetic_trials(plan)
    chosen = tu.select_configurations(records, plan)
    assert all(r["candidate"] == 1 for r in chosen.values())
    records[1]["attempts"][0].update(status="failed", macro_f1=.99)
    assert tu.select_configurations(records, plan)[MODEL_NAMES[0]]["candidate"] == 2
    records[0]["attempts"].pop()
    with pytest.raises(en.IntegrityError, match="chưa hoàn tất"):
        tu.select_configurations(records, plan)
    with pytest.raises(en.IntegrityError, match="mọi candidate lỗi"):
        tu.select_configurations(synthetic_trials(plan, fail_model="knn"), plan)


def test_fold_orchestrator_train_only_logs_warnings_times_errors_and_resume_without_refitting(tmp_path, train, config, monkeypatch):
    plan = tu.search_plan(config)
    folds, _, _, _ = tu.grouped_folds(train[1], train[2], 3, plan)
    calls = []
    def score(name, params, cfg, fit_data, holdout, n_classes, progress):
        assert not set(fit_data[0].index) & set(holdout[0].index)
        fit_groups = train[2][fit_data[0].index]
        score_groups = train[2][holdout[0].index]
        assert not set(fit_groups) & set(score_groups)
        assert len(fit_data[0]) < len(train[0])  # No full train / external validation in CV.
        calls.append((name, params))
        warnings.warn("synthetic fold warning", UserWarning)
        if name == "knn" and params["n_neighbors"] == 7:
            raise RuntimeError("synthetic candidate failure")
        return {"macro_f1": .5, "prediction_seconds": .001}
    monkeypatch.setattr(tu, "_fold_score", score)
    state = tmp_path / "trials.json"
    logs = []
    records = tu.search_train_only(train, config, plan, folds, 3, state, "unit-experiment", progress=logs.append)
    assert len(calls) == 45 and len(records) == 15
    assert all(a["elapsed_seconds"] >= 0 and a["warnings"] for r in records for a in r["attempts"])
    assert sum(a["status"] == "failed" for r in records for a in r["attempts"]) == 3
    assert tu.select_configurations(records, plan)["knn"]["candidate"] == 0
    assert logs and "CV logistic_regression" in logs[0]
    monkeypatch.setattr(tu, "_fold_score", lambda *a, **kw: pytest.fail("Completed fold must not refit"))
    assert tu.search_train_only(train, config, plan, folds, 3, state, "unit-experiment", progress=lambda _: None) == records
    state.write_bytes(state.read_bytes().replace(b'"macro_f1": 0.5', b'"macro_f1": 0.9', 1))
    with pytest.raises(en.IntegrityError, match="checksum"):
        tu._read_state(state, "unit-experiment")


def test_fold_builds_fresh_full_pipeline_and_never_fits_holdout(train, config, monkeypatch):
    class PipelineDouble:
        def fit(self, x, y):
            assert len(x) == 24 and x.index.tolist() == list(range(24))
            return self
        def predict(self, x):
            assert x.index.tolist() == list(range(24, 36))
            return train[1][24:]
    built = []
    monkeypatch.setattr(tu, "build_pipeline", lambda name, cfg: built.append(deepcopy(cfg)) or PipelineDouble())
    cfg = deepcopy(config)
    cfg["resources"] = tu.search_plan(config)["resources"]
    for _ in range(2):
        result = tu._fold_score("logistic_regression", {**cfg["models"]["logistic_regression"], "C": .5}, cfg,
                                (train[0].iloc[:24], train[1][:24]), (train[0].iloc[24:], train[1][24:]), 3, lambda _: None)
        assert result["macro_f1"] == 1
    assert len(built) == 2 and built[0]["models"]["logistic_regression"]["C"] == .5


def test_interrupt_is_recorded_and_retry_only_unfinished_fold(tmp_path, train, config, monkeypatch):
    plan = tu.search_plan(config)
    folds = tu.grouped_folds(train[1], train[2], 3, plan)[0]
    calls = []
    def interrupted(*args):
        calls.append(1)
        if len(calls) == 2:
            raise KeyboardInterrupt("unit stop")
        return {"macro_f1": .5}
    monkeypatch.setattr(tu, "_fold_score", interrupted)
    state = tmp_path / "trials.json"
    with pytest.raises(KeyboardInterrupt):
        tu.search_train_only(train, config, plan, folds, 3, state, "unit", progress=lambda _: None)
    assert tu._read_state(state, "unit")[0]["attempts"][-1]["status"] == "interrupted"
    tu.search_train_only(train, config, plan, folds, 3, state, "unit", progress=lambda _: None)
    assert len(calls) == 46  # 45 successes, one interrupted; first completed fold reused.


def test_scheduling_budget_stops_before_fit_and_never_selects_partial(tmp_path, train, config, monkeypatch):
    plan = tu.search_plan(config)
    plan["max_search_seconds_per_invocation"] = 0
    monkeypatch.setattr(tu, "_fold_score", lambda *a: pytest.fail("No budget, no fit"))
    with pytest.raises(TimeoutError, match="resume"):
        tu.search_train_only(train, config, plan, tu.grouped_folds(train[1], train[2], 3, plan)[0], 3,
                             tmp_path / "trials.json", "unit", progress=lambda _: None)


def test_cv_memory_guard_stops_before_large_group_matrix(train, config, monkeypatch):
    monkeypatch.setattr(tu.psutil, "virtual_memory", lambda: SimpleNamespace(available=1024))
    with pytest.raises(MemoryError, match="trước allocation"):
        tu.grouped_folds(train[1], train[2], 3, tu.search_plan(config))


@pytest.mark.parametrize("score", [float("nan"), float("inf"), 1.1])
def test_invalid_fold_scores_persist_as_errors_not_fake_metrics(tmp_path, train, config, monkeypatch, score):
    plan = tu.search_plan(config)
    folds = tu.grouped_folds(train[1], train[2], 3, plan)[0]
    monkeypatch.setattr(tu, "_fold_score", lambda *a, **kw: {"macro_f1": score})
    state = tmp_path / "trials.json"
    records = tu.search_train_only(train, config, plan, folds, 3, state, "unit", progress=lambda _: None)
    assert all(a["status"] == "failed" and "macro_f1" not in a for r in records for a in r["attempts"])
    assert tu._read_state(state, "unit") == records


def test_disabled_and_missing_runs_do_not_touch_data_models_or_write(tmp_path):
    sentinel = SimpleNamespace(paths=SimpleNamespace(storage_root=tmp_path))
    assert tu.run_tuning(None) is None
    assert te.evaluate_tuned_ensemble(None) is None
    assert te.evaluate_tuned_ensemble(sentinel, enabled=True) is None
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("bad", ["../phase3", "/etc", "tuning-v1-test", "tuning-v1-" + "f" * 17])
def test_checkpoint_namespace_rejects_traversal(tmp_path, bad):
    with pytest.raises(en.IntegrityError):
        tu.read_tuning_result(tmp_path, bad)


@pytest.fixture
def completed_run(tmp_path, train, config, monkeypatch):
    root = tmp_path / "drive"
    root.mkdir()
    paths = RuntimePaths(ROOT, root, root / "data/raw", root, "unit-only", tmp_path / "mount", tmp_path / "cache", False, {})
    # Synthetic fingerprints, never a claim about the actual Phase 2 dataset.
    files = {n: {"sha256": str(i) * 64} for i, n in enumerate(("data/processed/train.csv.gz", "data/processed/validation.csv.gz",
        "artifacts/metadata/phase2/feature_schema.json", "artifacts/metadata/phase2/label_mapping.json"), 1)}
    inputs = {"manifest": {"files": files, "processed": {"sha256": "a" * 64}}, "manifest_sha256": "b" * 64}
    validation = (train[0].iloc[:9].copy().reset_index(drop=True), train[1][:9].copy(), np.arange(100, 109))
    session = SimpleNamespace(paths=paths, config=config, inputs=inputs, data={"train": train, "validation": validation})
    class BaselineDouble(en.Phase4):
        def verify(self):
            self.inputs = inputs
            self.x, self.y, self.groups = validation
            self.classes, self.features = ["unit-a", "unit-b", "unit-c"], train[0].columns.tolist()
            self.metadata = {name: {"metrics": training.validation_metrics(self.y, self.y, 3), "prediction_seconds": .1} for name in MODEL_NAMES}
            self.records = {en.BASELINE: {"id": en.BASELINE, "mode": "single", "members": ["logistic_regression"],
                                         "status": "completed", "tie_rows": 0, **en.score_prediction(self.y, self.y, 3)}}
            return pd.DataFrame()
    for name in MODEL_NAMES:
        folder = root / "artifacts/models/phase3" / en.EXPERIMENT / name
        folder.mkdir(parents=True)
        (folder / "pipeline.joblib").write_bytes(b"synthetic untouched baseline; NOT fitted")
    monkeypatch.setattr(tu, "Phase4", BaselineDouble)
    monkeypatch.setattr(te, "Phase4", BaselineDouble)
    monkeypatch.setattr(tu, "_fold_score", lambda *a, **kw: {"macro_f1": .5})
    fitted = []
    def selected_double(name, cfg, identity, data, model_root, **kwargs):
        assert data["train"] is train
        selection_path = root / "artifacts/metadata/tuning" / identity["tuning_experiment"] / "selection.json"
        assert len(json.loads(selection_path.read_text())["knn"]["fold_scores"]) == 3
        assert len(json.loads(selection_path.read_text())) == 5  # All five frozen BEFORE validation.
        fitted.append(name)
        folder = model_root / name
        folder.mkdir(parents=True)
        (folder / "pipeline.joblib").write_bytes(b"synthetic selected checksum fixture; NOT fitted")
        fit = {"model": name, "status": "fitted", "identity": identity,
            "pipeline_sha256": training.sha256_file(folder / "pipeline.joblib"), "n_input_features": 375,
            "n_retained_features": 375, "variance_threshold": 0}
        (folder / "fit.json").write_bytes(training.json_bytes(fit))
        stream = io.BytesIO()
        np.savez_compressed(stream, y_true=validation[1], y_pred=validation[1], group_id=validation[2], row_0based=np.arange(9))
        (folder / "validation_predictions.npz").write_bytes(stream.getvalue())
        record = {**fit, "status": "completed", "fit_metadata_sha256": training.sha256_file(folder / "fit.json"),
                  "predictions_sha256": training.sha256_file(folder / "validation_predictions.npz"),
                  "metrics": training.validation_metrics(validation[1], validation[1], 3), "prediction_seconds": .02}
        (folder / "metadata.json").write_bytes(training.json_bytes(record))
        return record
    monkeypatch.setattr(tu, "run_model", selected_double)
    baseline_before = {p: p.read_bytes() for p in (root / "artifacts/models/phase3").rglob('*') if p.is_file()}
    result = tu.run_tuning(session, enabled=True, trusted=True, progress=lambda _: None)
    assert fitted == list(MODEL_NAMES)
    assert all(p.read_bytes() == b for p, b in baseline_before.items())
    return session, result, BaselineDouble, baseline_before


def test_complete_run_manifest_selection_resume_and_no_baseline_mutation(completed_run, monkeypatch):
    session, result, _, before = completed_run
    config_before = deepcopy(session.config)
    assert tu.read_tuning_result(session.paths.storage_root) == result
    monkeypatch.setattr(tu, "run_model", lambda *a, **kw: pytest.fail("Completed run must not refit selected"))
    monkeypatch.setattr(tu, "_fold_score", lambda *a, **kw: pytest.fail("Completed run must not redo CV"))
    assert tu.run_tuning(session, enabled=True, trusted=True, progress=lambda _: None) == result
    assert session.config == config_before
    assert all(p.read_bytes() == b for p, b in before.items())
    assert not result["validation_used_for_search"] and not result["application_model_changed"]
    assert len(result["files"]) == 26


@pytest.mark.parametrize("damage", ["pipeline", "selection", "cv", "extra_test_path", "identity"])
def test_tuned_result_corruption_stops_before_deserialize(completed_run, damage, monkeypatch):
    session, result, _, _ = completed_run
    root = session.paths.storage_root
    meta, models, _ = tu._paths(root, result["experiment_id"])
    monkeypatch.setattr(training.joblib, "load", lambda *a: pytest.fail("Corrupt must not load"))
    if damage == "pipeline":
        (models / "knn/pipeline.joblib").write_bytes(b"damaged")
    elif damage == "selection":
        (meta / "selection.json").write_text('{}')
    elif damage == "cv":
        (meta / "cv_assignments.npz").write_bytes(b"damaged")
    elif damage == "identity":
        result["experiment_id"] = "tuning-v1-" + "0" * 16
        (meta / "manifest.json").write_bytes(training.json_bytes(result))
    else:
        result["files"]["data/processed/test.csv.gz"] = {"sha256": "0" * 64, "bytes": 0}
        (meta / "manifest.json").write_bytes(training.json_bytes(result))
    with pytest.raises(en.IntegrityError):
        tu.read_tuning_result(root, meta.name)


def test_missing_selected_checkpoint_skips_without_affecting_baseline(completed_run, monkeypatch, capsys):
    session, result, _, before = completed_run
    models = tu._paths(session.paths.storage_root, result["experiment_id"])[1]
    (models / "knn/pipeline.joblib").unlink()
    monkeypatch.setattr(te, "Phase4", lambda *a: pytest.fail("Missing tuned input must skip before baseline reinspection"))
    assert te.evaluate_tuned_ensemble(session, enabled=True, trusted=True) is None
    assert "SKIPPED" in capsys.readouterr().out
    assert all(p.read_bytes() == b for p, b in before.items())


@pytest.mark.parametrize("damage", ["features", "classes", "parameters", "source", "identity", "environment"])
def test_tuned_verification_rejects_order_configuration_source_environment(completed_run, monkeypatch, damage):
    session, result, BaselineDouble, _ = completed_run
    baseline = BaselineDouble(session)
    baseline.verify()
    def load_double(folder, identity, *, trusted):
        model = training.build_pipeline(folder.name, identity["config"])
        variance = model.named_steps["variance"]
        variance.n_features_in_ = 375
        variance.feature_names_in_ = np.array(baseline.features[::-1] if damage == "features" else baseline.features)
        model.named_steps["estimator"].classes_ = np.array([2, 1, 0] if damage == "classes" else [0, 1, 2])
        if damage == "parameters":
            model.set_params(estimator__C=999)
        return model
    monkeypatch.setattr(en, "load_fitted_checkpoint", load_double)
    if damage == "source":
        original = te.sha256_file
        monkeypatch.setattr(te, "sha256_file", lambda path: "f" * 64 if path.name == "tuning.py" else original(path))
    elif damage == "identity":
        result = deepcopy(result)
        result["identity"]["training_data_fingerprint"] = "f" * 64
    elif damage == "environment":
        original = te.experiment_identity
        def changed_environment(*args):
            identity = original(*args)
            identity["versions"]["sklearn"] = "incompatible-unit-version"
            return identity
        monkeypatch.setattr(te, "experiment_identity", changed_environment)
    with pytest.raises(en.IntegrityError):
        te.TunedPhase4(session).verify_tuned(result, baseline, trusted=True)


def test_multiple_completed_runs_require_explicit_id(tmp_path):
    for suffix in ("0", "1"):
        folder = tmp_path / "artifacts/metadata/tuning" / ("tuning-v1-" + suffix * 16)
        folder.mkdir(parents=True)
        (folder / "manifest.json").write_text('{}')
    with pytest.raises(en.IntegrityError, match="nhiều tuning run"):
        tu.read_tuning_result(tmp_path)


def test_tuned_ensemble_uses_original_votes_and_saves_only_new_namespace(completed_run, monkeypatch):
    session, result, _, before = completed_run
    loaded = []
    def load_double(self, name, *, trusted):
        loaded.append(name)
        model = training.build_pipeline(name, self.config)
        model.named_steps["variance"].feature_names_in_ = np.array(self.features)
        return model  # Constructor/metadata only, NOT a fitted estimator.
    monkeypatch.setattr(te.TunedPhase4, "_load", load_double)
    def probability_double(self, *, trusted):
        self.probabilities = {name: np.eye(3)[self.predictions[name]] for name in MODEL_NAMES if name != "linear_svc"}
        return pd.DataFrame([{"synthetic_unit_fixture": True}])
    monkeypatch.setattr(te.TunedPhase4, "prepare_probabilities", probability_double)
    output = te.evaluate_tuned_ensemble(session, enabled=True, trusted=True)
    assert loaded == list(MODEL_NAMES)
    assert len(output["comparison"]) == 11
    assert set(output["comparison"]["combination"]) >= set(en.HARD) | set(en.SOFT)
    assert not output["recommendation"]["application_model_changed"]
    manifest = json.loads(Path(output["manifest"]).read_text(encoding='utf-8'))
    assert manifest["base_models_fitted"] == 0 and not any(manifest["guards"].values())
    assert set(manifest["hard"]) == set(en.HARD) and set(manifest["soft"]) == set(en.SOFT)
    assert all("tuned-ensemble-" in name for name in manifest["files"])
    assert all(p.read_bytes() == b for p, b in before.items())


def test_missing_probability_is_na_and_never_fabricates_metrics(completed_run, monkeypatch):
    session, _, _, _ = completed_run
    def verify_double(self, result, baseline, *, trusted):
        self.x, self.y, self.groups = baseline.x, baseline.y, baseline.groups
        self.features, self.classes, self.baseline = baseline.features, baseline.classes, baseline
        self.metadata = deepcopy(baseline.metadata)
        self.predictions = {name: self.y.copy() for name in MODEL_NAMES}
        self.run = baseline.run
        self.records = deepcopy(baseline.records)
        self.identity = result["identity"]
        self.experiment = result["experiment_id"]
        return pd.DataFrame()
    monkeypatch.setattr(te.TunedPhase4, "verify_tuned", verify_double)
    monkeypatch.setattr(te.TunedPhase4, "prepare_probabilities", lambda *a, **kw: pd.DataFrame())
    output = te.evaluate_tuned_ensemble(session, enabled=True, trusted=True)
    soft = output["comparison"].set_index("combination").loc[list(en.SOFT)]
    assert (soft["status"] == "not_available").all() and soft["macro_f1"].isna().all()
    assert json.loads(Path(output["manifest"]).read_text())["base_models_fitted"] == 0


def test_metric_wins_before_cost_proxy_and_does_not_replace_default():
    phase = object.__new__(te.TunedPhase4)
    phase.records = {"expensive": {"members": ["logistic_regression", "knn", "linear_svc"]}}
    phase.table = lambda: pd.DataFrame([
        {"combination": "baseline_logistic_regression", "status": "completed", "macro_f1": .7, "base_models": 1, "pipeline_bytes": 1, "source": "verified_baseline"},
        {"combination": "expensive", "status": "completed", "macro_f1": .7000000001, "base_models": 3, "pipeline_bytes": 500, "source": "tuned"}])
    assert phase.recommendation()["candidate"] == "expensive"
    assert phase.recommendation()["application_model_changed"] is False


def test_notebook_extensions_disabled_in_memory_respect_user_switches():
    for name, start, flag in (("03_model_training.ipynb", 14, "RUN_HYPERPARAMETER_TUNING"),
                              ("04_ensemble.ipynb", 17, "RUN_TUNED_ENSEMBLE")):
        nb = json.loads((ROOT / "notebooks" / name).read_text(encoding='utf-8'))
        # User audit appendices after the three tuning cells are independent history.
        appended = nb["cells"][start:start + 3]
        assert len(appended) == 3
        code = '\n'.join(''.join(c['source']) for c in appended if c['cell_type']=='code')
        assert 'bootstrap_runtime' not in code and 'colab-session' not in code
        compile(code, name, 'exec')
        # Users intentionally enable these switches. Force only the TEST COPY
        # off; do not require editing their notebook or discard saved outputs.
        tree = ast.parse(code)
        assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == flag for t in n.targets))
        assert isinstance(assignment.value, ast.Constant) and type(assignment.value.value) is bool
        assignment.value = ast.copy_location(ast.Constant(False), assignment.value)
        namespace = {"session": SimpleNamespace(config=read_training_config(ROOT))}
        exec(compile(ast.fix_missing_locations(tree), name, 'exec'), namespace)
        assert namespace[flag] is False  # Disabled paths only; original file untouched.
        if name.startswith('04'):
            calls = [n for n in ast.walk(ast.parse(code)) if isinstance(n, ast.Call)]
            assert not any(isinstance(n.func, ast.Attribute) and n.func.attr in {'fit','train','train_model','fit_transform'} for n in calls)
