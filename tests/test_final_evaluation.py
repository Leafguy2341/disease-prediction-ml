"""Synthetic fixtures ONLY: never use project data payloads, joblib models or APIs."""
import ast
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import f1_score

from src.models import final_evaluation as final


PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    """Independent temp storage; only schema/label names come from project METADATA.

    There are no real serialized estimators: joblib bytes are deliberately fake,
    deserialization is mocked, and predict is a deterministic fixture function.
    """
    frozen = final.protocol()
    root = tmp_path / "synthetic-storage"
    root.mkdir()
    schema = json.loads((PROJECT / "artifacts/metadata/phase2/feature_schema.json").read_text())
    labels = json.loads((PROJECT / "artifacts/metadata/phase2/label_mapping.json").read_text())
    features = schema["features"]
    def write(relative, payload):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return {"sha256": final.sha256_file(path), "bytes": path.stat().st_size}
    def js(value):
        return final.json_bytes(value)
    phase_files = {}
    assignments = []
    for split, ids, groups in [("train", [0], [10]), ("validation", [1], [20]), ("test", [0, 1, 1, 2, 2], [30, 31, 31, 32, 33])]:
        frame = pd.DataFrame(np.zeros((len(ids), 375), dtype="uint8"), columns=features)
        frame.iloc[:, 0] = np.arange(len(ids)) % 2
        frame[schema["target"]] = [labels["classes"][i] for i in ids]
        path = root / f"data/processed/{split}.csv.gz"
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False, compression="gzip")
        phase_files[path.relative_to(root).as_posix()] = {"sha256": final.sha256_file(path), "bytes": path.stat().st_size}
        assignments += [{"split": split, "split_row_0based": i, "group_id": g} for i, g in enumerate(groups)]
    assignment_path = root / "artifacts/metadata/phase2/split_assignments.csv.gz"
    assignment_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(assignments).to_csv(assignment_path, index=False, compression="gzip")
    phase_files[assignment_path.relative_to(root).as_posix()] = {"sha256": final.sha256_file(assignment_path), "bytes": assignment_path.stat().st_size}
    policy = {"seed": 42, "minimum_unique_vectors_per_class": 10, "drop_features": ["regurgitation", "regurgitation.1"]}
    splits = {"seed": 42, "splits": [{"split": "test", "dedup_records": 5, "groups": 4, "classes": 587}]}
    for name, value in [("feature_schema.json", schema), ("label_mapping.json", labels), ("preprocessing_policy.json", policy), ("split_metadata.json", splits)]:
        relative = "artifacts/metadata/phase2/" + name
        phase_files[relative] = write(relative, js(value))
    manifest = {"status": "finalized", "test_locked": True, "processed": frozen["processed"], "files": phase_files}
    phase_sha = write("artifacts/metadata/phase2/dataset_manifest.json", js(manifest))["sha256"]
    frozen.update(phase2_manifest_sha256=phase_sha, phase2_files=phase_files)
    frozen["test"].update(records=5, groups=4, **phase_files["data/processed/test.csv.gz"])
    for cp in frozen["checkpoints"].values():
        cp["identity"]["versions"] = final.versions()
        cp["identity"]["phase2_manifest_sha256"] = phase_sha
        cp["identity"]["feature_schema_identity"] = phase_files["artifacts/metadata/phase2/feature_schema.json"]["sha256"]
        cp["identity"]["label_mapping_identity"] = phase_files["artifacts/metadata/phase2/label_mapping.json"]["sha256"]
        cp["identity"]["training_data_fingerprint"] = phase_files["data/processed/train.csv.gz"]["sha256"]
        cp["identity"]["validation_data_fingerprint"] = phase_files["data/processed/validation.csv.gz"]["sha256"]
    tuned_identity = deepcopy(frozen["checkpoints"]["lr_tuned_c2"]["identity"])
    for key, cp in frozen["checkpoints"].items():
        prefix = cp["folder"] + "/"
        pipeline_entry = write(prefix + "pipeline.joblib", ("FAKE SYNTHETIC " + key).encode())
        fit = {"status": "fitted", "identity": cp["identity"], "model": cp["model"], "pipeline_sha256": pipeline_entry["sha256"],
               "n_input_features": 375, "n_retained_features": 318}
        fit_entry = write(prefix + "fit.json", js(fit))
        prediction_entry = write(prefix + "validation_predictions.npz", b"FAKE SYNTHETIC VALIDATION")
        meta = {**fit, "status": "completed", "fit_metadata_sha256": fit_entry["sha256"], "predictions_sha256": prediction_entry["sha256"]}
        meta_entry = write(prefix + "metadata.json", js(meta))
        cp["files"] = {"pipeline.joblib": pipeline_entry, "fit.json": fit_entry, "metadata.json": meta_entry,
                       "validation_predictions.npz": prediction_entry}
    ti, ei = frozen["tuning"], frozen["ensemble"]
    tuned = {"identity": tuned_identity}
    ti["manifest_sha256"] = write(f"artifacts/metadata/tuning/{ti['experiment_id']}/manifest.json", js(tuned))["sha256"]
    ensemble = {"run_id": ei["run_id"], "tuning_experiment": ti["experiment_id"], "tuning_manifest_sha256": ti["manifest_sha256"],
                "selected_identity": tuned_identity, "hard": {ei["key"]: ei["members"]}, "hard_tie_priority": ei["priority"], "files": {}}
    for relative in [f"artifacts/metadata/runs/{ei['run_id']}/tuned_ensemble_predictions.npz",
                     f"artifacts/metadata/runs/{ei['run_id']}/tuned_results.json",
                     f"reports/runs/{ei['run_id']}/tables/tuned_validation_comparison.csv",
                     f"reports/runs/{ei['run_id']}/tuned_ensemble_validation.md"]:
        ensemble["files"][relative] = write(relative, b"FAKE SYNTHETIC ENSEMBLE")
    ei["manifest_sha256"] = write(f"artifacts/metadata/runs/{ei['run_id']}/tuned_ensemble_manifest.json", js(ensemble))["sha256"]
    baseline = {"version": 1, "approved_manifest_sha256": [phase_sha], "files": phase_files, "processed": frozen["processed"]}
    monkeypatch.setattr(final, "FROZEN_PROTOCOL", frozen)
    monkeypatch.setattr(final, "read_baseline", lambda path: baseline)
    monkeypatch.setattr(final, "read_tuning_result", lambda *args: tuned)
    monkeypatch.setattr(final, "_figure", lambda tables: b"SYNTHETIC FIGURE; NOT A REAL EVALUATION")
    class FakePipeline:
        def __init__(self, cp):
            self.feature_names_in_ = np.asarray(features)
            self.classes_ = np.arange(587)
            self.steps = final.build_pipeline(cp["model"], cp["identity"]["config"]).steps
        def predict(self, frame):
            return np.arange(len(frame), dtype="int64") % 3
    monkeypatch.setattr(final, "load_fitted_checkpoint", lambda folder, identity, trusted: FakePipeline(
        next(cp for cp in frozen["checkpoints"].values() if (root / cp["folder"]) == folder)))
    session = SimpleNamespace(paths=SimpleNamespace(storage_root=root, project_root=PROJECT),
                              inputs={"schema": schema, "labels": labels})
    return session


def test_disabled_gate_has_zero_io(monkeypatch):
    monkeypatch.setattr(final, "preflight", lambda *args: pytest.fail("No preflight or IO when disabled"))
    assert final.evaluate(None) is None


def test_bad_authorization_stops_before_preflight(monkeypatch):
    monkeypatch.setattr(final, "preflight", lambda *args: pytest.fail("Authorization first"))
    with pytest.raises(ValueError, match="authorization"):
        final.evaluate(None, enabled=True, owner_authorization="yes")


def test_full_preflight_never_opens_or_hashes_test(synthetic, monkeypatch):
    original = final.sha256_file
    def guarded_hash(path):
        assert Path(path).name != "test.csv.gz"
        return original(path)
    monkeypatch.setattr(final, "sha256_file", guarded_hash)
    original_stat = Path.stat
    def guarded_stat(path, *args, **kwargs):
        assert path.name != "test.csv.gz", "Even test stat is unnecessary in preflight"
        return original_stat(path, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", guarded_stat)
    monkeypatch.setattr(final, "load_final_split", lambda *args: pytest.fail("Preflight may not load test"))
    monkeypatch.setattr(final, "load_fitted_checkpoint", lambda *args, **kw: pytest.fail("Preflight does not deserialize"))
    result = final.preflight(synthetic)  # Existing phase4_guard also intercepts open/io.open.
    assert result["status"] == "PASS"
    assert result["test_payload_opened"] is False
    assert not any(result["guards"].values())
    assert not final.namespace(synthetic.paths.storage_root).exists()


@pytest.mark.parametrize("corruption", ["features", "classes", "estimator"])
def test_reload_mismatch_blocks_before_test_or_execution_marker(synthetic, monkeypatch, corruption):
    prepared = final.preflight(synthetic)
    original = final.load_fitted_checkpoint
    def load(*args, **kwargs):
        model = original(*args, **kwargs)
        if corruption == "features":
            model.feature_names_in_ = model.feature_names_in_[::-1]
        elif corruption == "classes":
            model.classes_ = np.arange(586)
        else:
            estimator = model.steps[-1][1]
            estimator.set_params(**({"C": 9} if "C" in estimator.get_params() else {"n_neighbors": 9}))
        return model
    monkeypatch.setattr(final, "load_fitted_checkpoint", load)
    monkeypatch.setattr(final, "load_final_split", lambda *a: pytest.fail("Bad reloaded object must not reach test"))
    with pytest.raises(ValueError, match="Reloaded"):
        final.evaluate(synthetic, enabled=True, owner_authorization=final.authorization_text(), prepared=prepared)
    assert not final.namespace(synthetic.paths.storage_root).exists()


@pytest.mark.parametrize("kind", ["pipeline", "source", "environment", "ensemble_manifest", "mapping", "data_manifest"])
def test_preflight_rejects_tampering(synthetic, monkeypatch, kind):
    frozen = final.FROZEN_PROTOCOL
    if kind == "pipeline":
        (synthetic.paths.storage_root / frozen["checkpoints"]["lr_baseline"]["folder"] / "pipeline.joblib").write_bytes(b"TAMPER")
    elif kind == "source":
        frozen["checkpoints"]["lr_baseline"]["identity"]["source_sha256"]["src/models/training.py"] = "0" * 64
    elif kind == "environment":
        monkeypatch.setattr(final, "versions", lambda: {})
    elif kind == "mapping":
        (synthetic.paths.storage_root / "artifacts/metadata/phase2/label_mapping.json").write_text("{}")
    elif kind == "data_manifest":
        frozen["phase2_manifest_sha256"] = "0" * 64
    else:
        frozen["ensemble"]["manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        final.preflight(synthetic)


def test_authorized_synthetic_execution_is_one_time_and_report_replay_has_no_test(synthetic, monkeypatch):
    prepared = final.preflight(synthetic)
    original = final.load_final_split
    calls = []
    def load(output, name):
        calls.append(name)
        return original(output, name)
    monkeypatch.setattr(final, "load_final_split", load)
    result = final.evaluate(synthetic, enabled=True, owner_authorization=final.authorization_text(), prepared=prepared, progress=lambda s: None)
    assert calls == ["test"]  # Only the temp SYNTHETIC CSV.
    assert result["records"] == 5 and result["labels"] == 587 and result["models_fitted"] == 0
    folder = Path(result["folder"])
    final.read_completed(folder)
    with np.load(folder / "test_predictions.npz", allow_pickle=False) as saved:
        assert set(saved.files) == {"y_true", "group_id", "row_0based", *final.protocol()["candidates"]}
    with pytest.raises(ValueError):
        final.evaluate(synthetic, enabled=True, owner_authorization=final.authorization_text(), prepared=prepared)
    assert calls == ["test"]
    (folder / "comparison.csv").write_bytes(b"TAMPER")
    with pytest.raises(ValueError, match="Checksum"):
        final.read_completed(folder)


def test_test_checksum_failure_leaves_partial_marker_and_blocks_rerun(synthetic):
    prepared = final.preflight(synthetic)
    (synthetic.paths.storage_root / "data/processed/test.csv.gz").write_bytes(b"CORRUPTED SYNTHETIC")
    with pytest.raises(ValueError):
        final.evaluate(synthetic, enabled=True, owner_authorization=final.authorization_text(), prepared=prepared)
    dest = final.namespace(synthetic.paths.storage_root)
    assert (dest / "execution.json").exists() and (dest / "failure.json").exists()
    assert not (dest / "manifest.json").exists()
    assert "PARTIAL" in final.preflight(synthetic)["execution_status"]
    with pytest.raises(ValueError):
        final.evaluate(synthetic, enabled=True, owner_authorization=final.authorization_text(), prepared=prepared)


def test_source_change_after_preflight_blocks_before_load(synthetic, monkeypatch):
    prepared = final.preflight(synthetic)
    monkeypatch.setattr(final, "_code_identity", lambda session: {"changed": "yes"})
    monkeypatch.setattr(final, "load_final_split", lambda *args: pytest.fail("No payload after stale preflight"))
    with pytest.raises(ValueError, match="prepared"):
        final.evaluate(synthetic, enabled=True, owner_authorization=final.authorization_text(), prepared=prepared)


def test_orphaned_output_is_not_reused(synthetic):
    folder = final.namespace(synthetic.paths.storage_root)
    folder.mkdir(parents=True)
    (folder / "results.json").write_text("{}")
    prepared = final.preflight(synthetic)
    assert "ORPHANED" in prepared["execution_status"]
    with pytest.raises(ValueError, match="already"):
        final.evaluate(synthetic, enabled=True, owner_authorization=final.authorization_text(), prepared=prepared)


def test_fixed_labels_group_weighting_and_conflicting_labels():
    y = np.array([0, 1, 1, 2])
    predictions = {"lr_baseline": np.array([0, 0, 0, 2]), "lr_tuned_c2": np.array([0, 1, 0, 2]),
                   "hard_tuned_lr_svc_knn": np.array([1, 1, 1, 2])}
    groups = np.array([10, 10, 10, 20])  # Conflicting disease labels in one symptom group.
    classes = [str(i) for i in range(587)]
    tables = final.analyze(y, predictions, groups, classes, {k: {} for k in predictions})
    test = tables["comparison"].query("split == 'test'").set_index("candidate")
    assert test.loc["lr_tuned_c2", "macro_f1"] == pytest.approx(f1_score(y, predictions["lr_tuned_c2"], labels=np.arange(587), average="macro", zero_division=0))
    transition = tables["transitions"].iloc[0]
    assert transition.rescues == 1 and transition.new_errors == 0
    assert transition.equal_group_delta == pytest.approx(1/6)
    assert tables["per_class"].shape[0] == 587
    assert tables["per_class"].iloc[1].test_independent_groups == 1
    assert tables["group_differences"].shape[0] == 2


def test_reuses_original_tie_policy():
    members = {"logistic_regression": np.array([9]), "linear_svc": np.array([2]), "knn": np.array([3])}
    prediction, ties = final.hard_vote(members, final.HARD["hard_lr_svc_knn"], 587)
    assert prediction.tolist() == [9] and ties == 1


def test_fit_guard_blocks_before_synthetic_method_body():
    scope = {"__name__": "sklearn.synthetic_guard_fixture"}
    exec("def fit():\n    raise AssertionError('fit body must never execute')", scope)
    with final._no_learning(), pytest.raises(RuntimeError, match="forbids fitting"):
        scope["fit"]()  # No sklearn estimator or data, just a synthetic call-frame fixture.


def test_exclusive_writer_never_overwrites(tmp_path):
    path = tmp_path / "synthetic-execution.json"
    final._create(path, b"original")
    with pytest.raises(FileExistsError):
        final._create(path, b"replacement")
    assert path.read_bytes() == b"original"


def test_protocol_evidence_and_notebook_gate_are_frozen():
    frozen = final.protocol()
    assert frozen["test"]["records"] == 28066
    assert frozen["test"]["classes"] == 587 and frozen["test"]["features"] == 375
    assert frozen["checkpoints"]["lr_tuned_c2"]["identity"]["config"]["models"]["logistic_regression"]["C"] == 2
    assert final.digest(frozen) == "049ee0aa3c2907985c3d3a03ed222b1d6e1efb5921bbbc2d04ec0dea9baa8947"
    for relative, expected in frozen["evidence_sha256"].items():
        assert final.sha256_file(PROJECT / relative) == expected
    nb = json.loads((PROJECT / "notebooks/06_final_model_evaluation.ipynb").read_text(encoding="utf-8"))
    sources = "\n".join("".join(c.get("source", [])) for c in nb["cells"] if c["cell_type"] == "code")
    assert "RUN_FINAL_LOCKED_TEST = False" in sources and 'OWNER_AUTHORIZATION = ""' in sources
    assert "colab-session" not in sources and ".pyz" not in sources and ".zip" not in sources
    # Notebook is now a closeout viewer; executed outputs are historical evidence.
    # Circulating source must disable execution even when those outputs are kept.
    assert "read_completed(completed_folder)" in sources
    notebook_calls = [getattr(n.func, "attr", getattr(n.func, "id", ""))
                      for n in ast.walk(ast.parse(sources)) if isinstance(n, ast.Call)]
    assert "evaluate" not in notebook_calls
    assert not set(notebook_calls) & {"fit", "fit_transform", "predict", "predict_proba",
                                      "load_fitted_checkpoint", "load_final_split", "copy2"}
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]))
    tree = ast.parse((PROJECT / "src/models/final_evaluation.py").read_text(encoding="utf-8"))
    forbidden = {"fit", "fit_transform", "partial_fit", "run_tuning", "train_model", "predict_proba"}
    assert not any(isinstance(n, ast.Call) and getattr(n.func, "attr", getattr(n.func, "id", "")) in forbidden for n in ast.walk(tree))


def _run_preparation_notebook(name, session, tmp_path, monkeypatch, *, fault=None):
    """Run every CODE cell with isolated globals and synthetic Drive artifacts.

    The mount/bootstrap result is a fixture here; real bootstrap/restart tests
    live in test_canonical_colab_runtime/test_distribution. Final preflight and
    its file checks run for real against the synthetic storage above.
    """
    import builtins
    import io
    import platform
    import runpy
    from src.models.notebook import ColabTraining

    content = tmp_path / "synthetic-content"
    mount = content / "drive/MyDrive"
    content.mkdir()
    if fault != "mount":
        mount.mkdir(parents=True)
    root = session.paths.storage_root
    entry = root / "src/data/colab_runtime.py"
    if fault != "source":
        entry.parent.mkdir(parents=True)
        entry.write_text("# SYNTHETIC entry marker; never executed\n")
    runtime = SimpleNamespace(paths=session.paths, payload_sha256="a" * 64)
    session.inputs = final.verify_training_inputs(
        final.OutputPaths(root), baseline=final.read_baseline(PROJECT / "configs/phase2_integrity.json"))
    session.data = session.identity = None
    forbidden_calls, test_accesses = [], []

    def forbidden(*args, **kwargs):
        forbidden_calls.append("evaluation/training/prediction")
        raise AssertionError("Preparation must not evaluate/train/predict")

    monkeypatch.setattr(final, "evaluate", forbidden)
    monkeypatch.setattr(final, "load_final_split", forbidden)
    monkeypatch.setattr(final, "load_fitted_checkpoint", forbidden)
    monkeypatch.setattr(final, "_predict_batches", forbidden)
    for method in ("train", "train_model", "load_data"):
        monkeypatch.setattr(ColabTraining, method, forbidden)
    monkeypatch.setattr(ColabTraining, "open", lambda runtime: session)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    original_run = runpy.run_path

    def bootstrap(root, *, phase, expected_payload_sha256):
        assert phase == 3
        if expected_payload_sha256 != "a" * 64:
            raise ValueError("Paste the 64-character RUNTIME_PAYLOAD_SHA256 printed by local Publish")
        return runtime

    def run_path(path, *args, **kwargs):
        if Path(path) == entry:
            return {"bootstrap_runtime": bootstrap}
        assert Path(path).parent == PROJECT / "scripts", "No individually uploaded scripts"
        return original_run(path, *args, **kwargs)  # Real script definitions, no business calls.

    monkeypatch.setattr(runpy, "run_path", run_path)
    if fault == "checkpoint":
        frozen = final.protocol()
        # Point only this fixture at an absent folder; retain all real verifier logic.
        frozen["checkpoints"]["lr_baseline"]["folder"] += "-missing-fixture"
        monkeypatch.setattr(final, "FROZEN_PROTOCOL", frozen)
    elif fault == "environment":
        monkeypatch.setattr(final, "versions", lambda: {"python": "INCOMPATIBLE FIXTURE"})

    def protect(original):
        def guarded(path, *args, **kwargs):
            if isinstance(path, (str, Path)) and Path(path).name == "test.csv.gz":
                test_accesses.append(str(path))
                raise AssertionError("LOCKED TEST SENTINEL")
            return original(path, *args, **kwargs)
        return guarded

    monkeypatch.setattr(builtins, "open", protect(builtins.open))
    monkeypatch.setattr(io, "open", protect(io.open))
    monkeypatch.setattr(Path, "stat", protect(Path.stat))
    before = {p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
              for p in root.rglob("*") if p.name != "test.csv.gz" and p.is_file()}
    nb = json.loads((PROJECT / "notebooks" / name).read_text(encoding="utf-8"))
    scope = {"__name__": "__notebook__", "session": object(), "prepared": {"STALE": True},
             "RUNTIME": object(), "final_result": {"STALE": True}}
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        source = source.replace("Path('/content')", f"Path({str(content)!r})")
        source = source.replace("Path('/content/drive/MyDrive')", f"Path({str(mount)!r})")
        source = source.replace("Path('/content/drive/MyDrive/ML_Projects/disease-prediction-ml')", f"Path({str(root)!r})")
        if fault != "digest":
            source = source.replace('EXPECTED_RUNTIME_PAYLOAD = ""', 'EXPECTED_RUNTIME_PAYLOAD = "' + "a" * 64 + '"')
            # An operator may have saved the valid real release pin in the notebook.
            import re
            source = re.sub(r'EXPECTED_RUNTIME_PAYLOAD = "[0-9a-f]{64}"',
                            'EXPECTED_RUNTIME_PAYLOAD = "' + "a" * 64 + '"', source)
        else:
            import re
            source = re.sub(r'EXPECTED_RUNTIME_PAYLOAD = "[0-9a-f]{64}"', 'EXPECTED_RUNTIME_PAYLOAD = ""', source)
        fixture_manifest = final.namespace(root) / "manifest.json"
        if fixture_manifest.is_file():
            source = source.replace('EXPECTED_COMPLETED_MANIFEST_SHA256 = "f1ad195e1e46154d7a29a421e80387bfa76e494f4df771cede240f882d0b754a"',
                                    'EXPECTED_COMPLETED_MANIFEST_SHA256 = "' + final.sha256_file(fixture_manifest) + '"')
        exec(compile(source, f"{name}:cell{i+1}", "exec"), scope)
    after = {p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
             for p in root.rglob("*") if p.name != "test.csv.gz" and p.is_file()}
    assert after == before, "Notebook preparation must leave synthetic storage unchanged"
    assert not forbidden_calls and not test_accesses
    return scope


@pytest.mark.parametrize("name", ["colab_smoke_test.ipynb", "06_final_model_evaluation.ipynb"])
def test_whole_preparation_notebook_is_independent_and_never_opens_test(synthetic, tmp_path, monkeypatch, name):
    scope = _run_preparation_notebook(name, synthetic, tmp_path, monkeypatch)
    assert all(row["status"] == "PASS" for row in scope["checks"])
    assert scope["session"] is synthetic
    if name.startswith("06"):
        assert scope["RUN_FINAL_LOCKED_TEST"] is False and scope["OWNER_AUTHORIZATION"] == ""
        assert scope["preflight_result"]["status"] == "PASS" and scope["final_result"] is None
        assert len(scope["prepared"]["checkpoints"]) == 4  # Shared members, exactly three candidates.
        assert scope["FROZEN"]["candidates"] == ["lr_baseline", "lr_tuned_c2", "hard_tuned_lr_svc_knn"]
        assert scope["FROZEN"]["ensemble"]["priority"] == list(final.PRIORITY)
    else:
        assert scope["smoke_result"]["status"] == "PASS"
        assert scope["smoke_result"]["checkpoint_reload"] == "NOT VERIFIED"


@pytest.mark.parametrize("name", ["colab_smoke_test.ipynb", "06_final_model_evaluation.ipynb"])
@pytest.mark.parametrize("fault,stage", [("mount", "Drive mount"), ("source", "Published source"),
                                       ("digest", "Source release / bootstrap")])
def test_notebook_prerequisite_failures_report_first_blocker_without_stale_session(
        synthetic, tmp_path, monkeypatch, name, fault, stage):
    scope = _run_preparation_notebook(name, synthetic, tmp_path, monkeypatch, fault=fault)
    assert scope["session"] is None and scope["prepared"] is None and scope["final_result"] is None
    failures = [row for row in scope["checks"] if row["status"] == "FAIL"]
    assert len(failures) == 1 and failures[0]["check"] == stage
    assert any(row["status"] == "SKIPPED" for row in scope["checks"])


@pytest.mark.parametrize("fault,message", [("checkpoint", "-missing-fixture/"), ("environment", "environment differs")])
def test_notebook06_reports_checkpoint_or_environment_blocker_without_evaluating(
        synthetic, tmp_path, monkeypatch, fault, message):
    scope = _run_preparation_notebook("06_final_model_evaluation.ipynb", synthetic, tmp_path, monkeypatch, fault=fault)
    assert scope["prepared"] is None and scope["preflight_result"]["status"] == "FAIL"
    assert any(row["status"] == "FAIL" and message in row["detail"] for row in scope["checks"])


def test_notebook06_replays_completed_fixture_without_reopening_test(synthetic, tmp_path, monkeypatch):
    # Create a completed TOY evaluation with FakePipeline before the replay sentinel.
    # No actual dataset/checkpoint is used, trained or serialized by this fixture.
    result = final.evaluate(synthetic, enabled=True, owner_authorization=final.authorization_text(),
                            prepared=final.preflight(synthetic))
    monkeypatch.setattr(final, "show_result", lambda r: final.read_completed(Path(r["folder"])))
    scope = _run_preparation_notebook("06_final_model_evaluation.ipynb", synthetic, tmp_path, monkeypatch)
    assert scope["RUN_FINAL_LOCKED_TEST"] is False and scope["OWNER_AUTHORIZATION"] == ""
    assert scope["final_result"]["manifest_sha256"] == result["manifest_sha256"]
    assert scope["final_result"]["status"] == "completed"
    assert all(row["status"] == "PASS" for row in scope["checks"])


def test_closeout_notebook_blocks_even_if_user_reenables_gate():
    nb = json.loads((PROJECT / "notebooks/06_final_model_evaluation.ipynb").read_text(encoding="utf-8"))
    gate = next("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"
                and "RUN_FINAL_LOCKED_TEST = False" in "".join(c["source"]))
    with pytest.raises(RuntimeError, match="completed results"):
        exec(gate.replace("RUN_FINAL_LOCKED_TEST = False", "RUN_FINAL_LOCKED_TEST = True"), {})


def test_notebook06_rejects_tampered_completed_evidence_without_test_access(synthetic, tmp_path, monkeypatch):
    # Completed TOY evidence only. No real checkpoint or dataset is evaluated.
    result = final.evaluate(synthetic, enabled=True, owner_authorization=final.authorization_text(),
                            prepared=final.preflight(synthetic))
    table = Path(result["folder"]) / "comparison.csv"
    table.write_bytes(table.read_bytes() + b"\nSYNTHETIC TAMPER\n")
    monkeypatch.setattr(final, "show_result", lambda r: pytest.fail("Do not display unverified results"))
    scope = _run_preparation_notebook("06_final_model_evaluation.ipynb", synthetic, tmp_path, monkeypatch)
    assert scope["final_result"] is None
    assert any(r["check"] == "Completed evidence replay" and r["status"] == "FAIL" for r in scope["checks"])
