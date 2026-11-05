"""Small synthetic fits and fake-Drive tests. These are not project/Colab metrics."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg", force=True)
import numpy as np
import pandas as pd
import pytest

from src.data.paths import OutputPaths
from src.data.preprocessing import read_phase2_policy, preprocess_dataset, export_preprocessed
from src.data.loader import sha256_file
from src.models import runtime, training
from src.models.runtime import (MODEL_NAMES, TRAINING_FILES, cache_training_inputs, colab_preflight,
                                colab_project_paths, load_training_data, read_training_config, verify_training_inputs)
from src.models.training import (build_pipeline, experiment_identity, load_fitted_checkpoint,
                                 read_completed_checkpoint, run_model, train_models, validation_metrics)
from src.models.reporting import comparison_table, save_comparison, save_handoff, validation_figures

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def store(tmp_path):
    # Forty vectors shared across three labels; all classes meet the approved >=10 rule.
    rows = []
    for group in range(40):
        for label in ("A", "B", "C"):
            rows.append({"diseases": label, **{f"b{i}": (group >> i) & 1 for i in range(6)},
                         "constant": 0, "regurgitation": group % 2, "regurgitation.1": int(group % 3 == 0)})
    raw = pd.DataFrame(rows)
    policy = read_phase2_policy(ROOT)
    policy["expected_raw_symptom_features"] = raw.shape[1] - 1
    result = preprocess_dataset(raw, policy)
    source = tmp_path / "fixture.csv"
    raw.to_csv(source, index=False)
    output = OutputPaths(tmp_path / "drive/MyDrive/ML_Projects/disease-prediction-ml")
    manifest = export_preprocessed(result, source, output, expected_source_sha256=sha256_file(source))
    config = read_training_config(ROOT)
    config["expected_phase2"] = {k: manifest["processed"][k] for k in ("records", "classes", "features", "sha256")}
    config["resources"].update(max_workers=1, min_available_ram_gb=0, prediction_batch_size=8)
    config["models"]["random_forest"].update(n_estimators=4, max_leaf_nodes=8)
    return output, config


def test_training_preflight_cache_and_loader_never_open_test_payload(store, tmp_path, monkeypatch):
    output, config = store
    original_open = Path.open
    def guarded_open(path, *args, **kwargs):
        if path.name == "test.csv.gz":
            pytest.fail("Phase 3 must not open test CSV, even for checksums")
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded_open)
    inputs = verify_training_inputs(output, config["expected_phase2"])
    cache = cache_training_inputs(output, tmp_path / "content/cache", inputs)
    cached = {str(p.relative_to(cache.root)).replace("\\", "/") for p in cache.root.rglob("*") if p.is_file()}
    assert cached == set(TRAINING_FILES) | {"artifacts/metadata/phase2/dataset_manifest.json"}
    assert not (cache.processed_dir / "test.csv.gz").exists()
    before = {str(p): p.stat().st_mtime_ns for p in cache.root.rglob("*") if p.is_file()}
    cache_training_inputs(output, tmp_path / "content/cache", inputs)
    assert before == {str(p): p.stat().st_mtime_ns for p in cache.root.rglob("*") if p.is_file()}
    data = load_training_data(cache, inputs)
    assert set(data) == {"train", "validation"}
    for x, y, groups in data.values():
        assert x.columns.tolist() == inputs["schema"]["features"]
        assert len(x) == len(y) == len(groups)
        assert set(y) == {0, 1, 2}


def test_missing_and_corrupt_inputs_stop_without_recreating(store):
    output, config = store
    missing = output.processed_dir / "validation.csv.gz"
    missing.unlink()
    with pytest.raises(FileNotFoundError, match="validation.csv.gz"):
        verify_training_inputs(output, config["expected_phase2"])
    missing.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="Checksum"):
        verify_training_inputs(output, config["expected_phase2"])


@pytest.mark.parametrize("damage", ["feature_order", "unknown_label"])
def test_loader_rejects_schema_and_label_misalignment_in_synthetic_fixture(store, damage):
    from src.data.loader import DatasetError
    output, config = store
    inputs = verify_training_inputs(output, config["expected_phase2"])
    path = output.processed_dir / "train.csv.gz"
    frame = pd.read_csv(path)
    if damage == "feature_order":
        columns = frame.columns.tolist()
        columns[0], columns[1] = columns[1], columns[0]
        frame = frame[columns]
    else:
        frame.loc[0, inputs["schema"]["target"]] = "label not in approved mapping"
    frame.to_csv(path, index=False, compression="gzip")
    # Deliberately forged SYNTHETIC manifest: exercise the loader beyond the checksum gate.
    manifest_path = output.metadata_dir / "phase2/dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["data/processed/train.csv.gz"]["sha256"] = sha256_file(path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(DatasetError):
        load_training_data(output, inputs)


def test_colab_preflight_rejects_local_and_missing_drive(store, tmp_path, monkeypatch):
    output, config = store
    paths = SimpleNamespace(project_root=ROOT, output_root=output.root, runtime="colab",
                            drive_mount=tmp_path / "drive", cache_dir=tmp_path / "content/cache")
    monkeypatch.setattr(runtime, "detect_capabilities", lambda: SimpleNamespace(colab_runtime_detected=False))
    with pytest.raises(RuntimeError, match="COLAB NOT YET VERIFIED"):
        colab_preflight(paths, config)
    monkeypatch.setattr(runtime, "detect_capabilities", lambda: SimpleNamespace(colab_runtime_detected=True))
    monkeypatch.setattr(runtime.platform, "system", lambda: "Linux")
    paths.drive_mount = tmp_path / "missing-drive"
    with pytest.raises(FileNotFoundError, match="Mount Google Drive"):
        colab_preflight(paths, config)


def test_fake_colab_drive_rw_probe_and_ephemeral_output_guard(store, tmp_path, monkeypatch):
    output, config = store
    paths = SimpleNamespace(project_root=ROOT, output_root=output.root, runtime="colab",
                            drive_mount=tmp_path / "drive", cache_dir=tmp_path / "content/cache")
    monkeypatch.setattr(runtime, "detect_capabilities", lambda: SimpleNamespace(colab_runtime_detected=True))
    monkeypatch.setattr(runtime.platform, "system", lambda: "Linux")
    environment, inputs = colab_preflight(paths, config)
    assert environment["drive_read_write_verified"] and environment["test_payload_opened"] is False
    assert not list((output.models_dir / "phase3").glob(".rw-probe-*"))
    paths.output_root = tmp_path / "content/ephemeral"
    with pytest.raises(ValueError, match="persistent"):
        colab_preflight(paths, config)


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_each_pipeline_fits_variance_on_train_only_and_predicts(name):
    config = read_training_config(ROOT)
    config["models"]["random_forest"].update(n_estimators=3, max_leaf_nodes=8)
    rng = np.random.default_rng(42)
    x = pd.DataFrame(rng.integers(0, 2, size=(45, 7)), columns=[f"s{i}" for i in range(7)])
    x["only_validation_varies"] = 0
    val = x.iloc[:9].copy()
    val["only_validation_varies"] = 1
    pipeline = build_pipeline(name, config).fit(x, np.tile([0, 1, 2], 15))
    assert not pipeline.named_steps["variance"].get_support()[-1]
    assert set(pipeline.predict(val)).issubset({0, 1, 2})
    assert pipeline.named_steps["variance"].threshold == 0
    assert (name != "linear_svc") == hasattr(pipeline, "predict_proba")


def test_real_synthetic_fits_checkpoints_resume_and_three_figures(store, monkeypatch):
    output, config = store
    inputs = verify_training_inputs(output, config["expected_phase2"])
    data = load_training_data(output, inputs)
    identity = experiment_identity(ROOT, config, inputs)
    records = list(train_models(config, identity, data, output, progress=lambda _: None))
    assert len(records) == 5 and all(r["status"] == "completed" for r in records)
    assert all(r["n_retained_features"] < data["train"][0].shape[1] for r in records)
    folder = output.models_dir / "phase3" / identity["experiment_id"]
    for record in records:
        own = folder / record["model"]
        with pytest.raises(ValueError, match="trusted=True"):
            load_fitted_checkpoint(own, identity)
        pipeline = load_fitted_checkpoint(own, identity, trusted=True)
        metadata, prediction = read_completed_checkpoint(own, identity, data["validation"][1], data["validation"][2])
        assert np.array_equal(pipeline.predict(data["validation"][0]), prediction)
        assert record["metrics"] == validation_metrics(data["validation"][1], prediction, 3)
        assert metadata["fit_seconds"] >= 0 and metadata["prediction_seconds"] >= 0
    before = {str(p): (sha256_file(p), p.stat().st_mtime_ns) for p in folder.rglob("*") if p.is_file()}
    monkeypatch.setattr(training.joblib, "load", lambda *a, **k: pytest.fail("Completed reuse must not unpickle"))
    monkeypatch.setattr(training, "build_pipeline", lambda *a, **k: pytest.fail("Completed reuse must not refit"))
    reused = list(train_models(config, identity, data, output, progress=lambda _: None))
    assert all(r["status"] == "reused" for r in reused)
    assert before == {str(p): (sha256_file(p), p.stat().st_mtime_ns) for p in folder.rglob("*") if p.is_file()}
    table = save_comparison(reused, output, identity)
    figures = validation_figures(reused, output, identity, data, inputs)
    assert len(figures) == 3 and all(p.is_file() and p.stat().st_size > 1000 for _, _, p in figures)
    handoff = save_handoff(reused, figures, output, identity, {"runtime": "synthetic unit fixture"}, table)
    assert handoff["phase4_ready"] and not handoff["test_payload_opened"]
    assert set(MODEL_NAMES) == {m["model"] for m in handoff["models"]}
    import matplotlib.pyplot as plt
    for _, fig, _ in figures:
        plt.close(fig)


def test_bad_identity_and_checksum_never_deserialize_or_overwrite(store, monkeypatch):
    output, config = store
    inputs = verify_training_inputs(output, config["expected_phase2"])
    data = load_training_data(output, inputs)
    identity = experiment_identity(ROOT, config, inputs)
    model_root = output.models_dir / "phase3" / identity["experiment_id"]
    run_model("bernoulli_nb", config, identity, data, model_root, progress=lambda _: None)
    folder = model_root / "bernoulli_nb"
    other = deepcopy(identity)
    other["versions"]["sklearn"] = "different-version"
    monkeypatch.setattr(training.joblib, "load", lambda *a, **k: pytest.fail("Mismatch must stop before deserialization"))
    with pytest.raises(ValueError, match="library version"):
        load_fitted_checkpoint(folder, other, trusted=True)
    model = folder / "pipeline.joblib"
    model.write_bytes(b"corrupted-model")
    with pytest.raises(ValueError, match="Checksum"):
        load_fitted_checkpoint(folder, identity, trusted=True)
    assert model.read_bytes() == b"corrupted-model"


def test_prediction_failure_preserves_fitted_pipeline_then_resumes(store, monkeypatch):
    output, config = store
    inputs = verify_training_inputs(output, config["expected_phase2"])
    data = load_training_data(output, inputs)
    identity = experiment_identity(ROOT, config, inputs)
    model_root = output.models_dir / "phase3" / identity["experiment_id"]
    original_predict = training._predict
    def fail(*a, **k):
        raise MemoryError("synthetic resource limit")
    monkeypatch.setattr(training, "_predict", fail)
    with pytest.raises(MemoryError):
        run_model("bernoulli_nb", config, identity, data, model_root, progress=lambda _: None)
    folder = model_root / "bernoulli_nb"
    assert (folder / "fit.json").is_file() and (folder / "pipeline.joblib").is_file()
    assert not (folder / "metadata.json").exists()
    before = sha256_file(folder / "pipeline.joblib")
    monkeypatch.setattr(training, "_predict", original_predict)
    result = run_model("bernoulli_nb", config, identity, data, model_root, trust_own_checkpoints=True, progress=lambda _: None)
    assert result["status"] == "completed" and sha256_file(folder / "pipeline.joblib") == before


def test_failure_rows_have_no_fake_metrics_and_completed_models_survive(store, monkeypatch):
    output, config = store
    inputs = verify_training_inputs(output, config["expected_phase2"])
    data = load_training_data(output, inputs)
    identity = experiment_identity(ROOT, config, inputs)
    original = training.build_pipeline
    def sometimes_fail(name, config):
        if name == "knn":
            raise MemoryError("synthetic OOM")
        return original(name, config)
    monkeypatch.setattr(training, "build_pipeline", sometimes_fail)
    records = list(train_models(config, identity, data, output, progress=lambda _: None))
    table = comparison_table(records)
    assert table.loc[table.model.eq("knn"), "macro_f1"].isna().all()
    assert len([r for r in records if r["status"] == "completed"]) == 4
    root = output.models_dir / "phase3" / identity["experiment_id"]
    assert (root / "knn.failure.json").is_file()
    assert (root / "logistic_regression/metadata.json").is_file()


def test_notebook_compiles_and_refuses_local_before_project_imports(monkeypatch):
    import platform
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    notebook = json.loads((ROOT / "notebooks/03_model_training.ipynb").read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    cells = ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]
    for source in cells:
        compile(source, "phase3-notebook-cell", "exec")
    from src.data.colab_runtime import bootstrap_runtime
    with pytest.raises(RuntimeError, match="Colab"):
        bootstrap_runtime(ROOT)
    assert not any("test.csv.gz" in source for source in cells)


def test_notebook_uses_shared_bootstrap_and_no_working_directory_search():
    notebook = json.loads((ROOT / "notebooks/03_model_training.ipynb").read_text(encoding="utf-8"))
    cells = ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]
    assert "bootstrap_runtime" in cells[0] and len(cells[0].splitlines()) <= 12
    assert "ColabTraining.open(RUNTIME)" in cells[1]
    assert not any("colab-session" in source or "source_manifest.json" in source for source in cells)
    assert not any("project_root(" in source or "resolve_paths(" in source or "configs/phase1.json" in source for source in cells)


def test_notebook_shows_five_estimators_and_explicit_train_fit_calls():
    import ast
    notebook = json.loads((ROOT / "notebooks/03_model_training.ipynb").read_text(encoding="utf-8"))
    sources = ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]
    model_cells = [source for source in sources if "session.train_model(" in source]
    assert len(model_cells) == 5
    for source, name, estimator in zip(model_cells, MODEL_NAMES, (
        "LogisticRegression", "RandomForestClassifier", "LinearSVC", "KNeighborsClassifier", "BernoulliNB")):
        calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)]
        assert any(isinstance(call.func, ast.Name) and call.func.id == estimator for call in calls)
        assert any(isinstance(call.func, ast.Attribute) and call.func.attr == "train_model"
                   and isinstance(call.args[0], ast.Constant) and call.args[0].value == name for call in calls)
        fits = [call for call in calls if isinstance(call.func, ast.Attribute) and call.func.attr == "fit"]
        assert len(fits) == 1 and [arg.id for arg in fits[0].args] == ["X_train", "y_train"]


def _prepare_project_folder(root, point, config, scratch):
    import shutil
    shutil.copytree(ROOT / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"), dirs_exist_ok=True)
    (root / "configs").mkdir(parents=True, exist_ok=True)
    settings = json.loads((ROOT / "configs/runtime.json").read_text(encoding="utf-8"))
    settings["colab"].update(drive_mount=str(point), cache_dir=str(scratch / "cache"), ephemeral_root=str(scratch))
    (root / "configs/runtime.json").write_text(json.dumps(settings), encoding="utf-8")
    (root / "configs/phase3.json").write_text(json.dumps(config), encoding="utf-8")


def test_one_drive_folder_wins_over_all_old_path_overrides(tmp_path, monkeypatch):
    point = tmp_path / "drive"
    root = point / "MyDrive/Another Student/custom project"
    _prepare_project_folder(root, point, read_training_config(ROOT), tmp_path / "content")
    for name in ("DISEASE_PROJECT_ROOT", "DISEASE_STORAGE_ROOT", "DISEASE_OUTPUT_DIR", "DISEASE_CACHE_DIR", "DISEASE_PATH_CONFIG"):
        monkeypatch.setenv(name, str(tmp_path / "wrong-old-folder"))
    monkeypatch.setenv("DISEASE_RUNTIME", "local")
    paths = colab_project_paths(root, drive_mount=point)
    assert paths.project_root == paths.storage_root == paths.output_root == root.resolve()
    assert paths.runtime == "colab" and paths.cache_dir.is_relative_to(tmp_path / "content")
    assert not (root / "configs/phase1.json").exists()


@pytest.mark.parametrize("value", ["https://drive.google.com/drive/folders/example", "relative/project", ""])
def test_drive_setting_rejects_url_or_relative_path(value, tmp_path):
    with pytest.raises(ValueError, match="DRIVE_PROJECT_DIR"):
        colab_project_paths(value, drive_mount=tmp_path / "drive")


def test_data_only_drive_folder_has_an_actionable_missing_source_error(tmp_path):
    point = tmp_path / "drive"
    root = point / "MyDrive/data-only"
    (root / "data/processed").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="src/models/notebook.py"):
        colab_project_paths(root, drive_mount=point)


def test_shared_session_can_open_and_load_without_model_fitting(store, tmp_path, monkeypatch):
    from src.models import notebook as ui
    output, config = store
    point = tmp_path / "drive"
    _prepare_project_folder(output.root, point, config, tmp_path / "content")
    paths = colab_project_paths(output.root, drive_mount=point)
    manifest_path = output.root / "artifacts/metadata/phase2/dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    (paths.project_root / "configs/phase2_integrity.json").write_text(json.dumps({
        "version": 1, "approved_manifest_sha256": [sha256_file(manifest_path)],
        "processed": manifest["processed"], "files": manifest["files"]}), encoding="utf-8")
    shared = SimpleNamespace(paths=paths, inputs=None, source_fingerprint="unit-fixture-only",
                             environment={"runtime": "Windows unit fixture", "drive_read_write_verified": False},
                             stages={"A": "not a real Colab check", "B": "fixture source"})
    monkeypatch.setattr(ui, "display", lambda value: None)
    monkeypatch.setattr(ui, "run_model_safely", lambda *a, **k: pytest.fail("Infrastructure check must not fit models"))
    session = ui.ColabTraining.open(shared)
    session.load_data()
    assert shared.stages["C"] == "PASS" and set(session.data) == {"train", "validation"}
    assert session.identity is None and session.records == []
    assert not list(paths.cache_dir.rglob("test.csv.gz"))


def test_compact_notebook_interface_runs_complete_workflow(store, tmp_path, monkeypatch):
    import src
    from src.models import notebook as ui
    output, config = store
    point = tmp_path / "drive"
    _prepare_project_folder(output.root, point, config, tmp_path / "content")
    paths = colab_project_paths(output.root, drive_mount=point)
    monkeypatch.setattr(src, "__file__", str(output.root / "src/__init__.py"))
    monkeypatch.setattr(runtime, "detect_capabilities", lambda: SimpleNamespace(colab_runtime_detected=True))
    monkeypatch.setattr(runtime.platform, "system", lambda: "Linux")
    shown = []
    monkeypatch.setattr(ui, "display", shown.append)
    before = {relative: sha256_file(output.root / relative) for relative in TRAINING_FILES}
    environment, inputs = colab_preflight(paths, config)
    manifest_path = output.root / "artifacts/metadata/phase2/dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    (paths.project_root / "configs/phase2_integrity.json").write_text(json.dumps({
        "version": 1, "approved_manifest_sha256": [sha256_file(manifest_path)],
        "processed": manifest["processed"], "files": manifest["files"]}), encoding="utf-8")
    shared = SimpleNamespace(paths=paths, environment=environment, inputs=inputs, source_fingerprint="synthetic", stages={"A": "PASS", "B": "PASS"})
    session = ui.ColabTraining.open(shared)
    with pytest.raises(RuntimeError, match="load_data"):
        session.train()
    # Execute the actual data, common pipeline, five model and results notebook cells.
    notebook = json.loads((ROOT / "notebooks/03_model_training.ipynb").read_text(encoding="utf-8"))
    cells = ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]
    import IPython.display
    monkeypatch.setattr(IPython.display, "display", shown.append)
    namespace = {"session": session}
    for source in cells[2:]:
        exec(compile(source, "actual-visible-model-cell", "exec"), namespace)
    handoff = namespace["handoff"]
    assert handoff["phase4_ready"] and len(handoff["figures"]) == 3
    assert len(session.records) == 5 and shown
    assert before == {relative: sha256_file(output.root / relative) for relative in TRAINING_FILES}
    assert not list(session.paths.cache_dir.rglob("test.csv.gz"))


def test_visible_fit_callback_is_executed_once_and_mismatch_stops_reuse(store):
    output, config = store
    inputs = verify_training_inputs(output, config["expected_phase2"])
    data = load_training_data(output, inputs)
    identity = experiment_identity(ROOT, config, inputs)
    root = output.models_dir / "phase3" / identity["experiment_id"]
    calls = []
    def visible_fit(model):
        calls.append(model)
        return model.fit(data["train"][0], data["train"][1])
    first = run_model("bernoulli_nb", config, identity, data, root,
                      pipeline=build_pipeline("bernoulli_nb", config), fit=visible_fit, progress=lambda _: None)
    reused = run_model("bernoulli_nb", config, identity, data, root,
                       pipeline=build_pipeline("bernoulli_nb", config), fit=visible_fit, progress=lambda _: None)
    assert first["status"] == "completed" and reused["status"] == "reused" and len(calls) == 1
    checkpoint = root / "bernoulli_nb/pipeline.joblib"
    before = sha256_file(checkpoint)
    changed = build_pipeline("bernoulli_nb", config).set_params(estimator__alpha=5.0)
    with pytest.raises(ValueError, match="configs/phase3.json"):
        run_model("bernoulli_nb", config, identity, data, root, pipeline=changed,
                  fit=visible_fit, progress=lambda _: None)
    assert sha256_file(checkpoint) == before and len(calls) == 1


def test_source_bundle_contains_phase3_without_data_models_or_environments(tmp_path, monkeypatch):
    import zipfile
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from package_colab import build_bundle
    archive = tmp_path / "source.zip"
    build_bundle(ROOT, archive)
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        prefix = "disease-prediction-ml/"
        required = ["notebooks/03_model_training.ipynb", "configs/phase3.json", "requirements-training.txt",
                    "src/models/runtime.py", "src/models/training.py", "src/models/reporting.py", "src/models/notebook.py"]
        assert all(prefix + name in names for name in required)
        assert not any("/data/processed/" in name or "/.venv/" in name or name.endswith(".joblib") for name in names)
        notebook = json.loads(bundle.read(prefix + "notebooks/03_model_training.ipynb"))
        assert all(not c.get("outputs") for c in notebook["cells"] if c["cell_type"] == "code")
