"""Final evaluation preparation. No locked payload access before the explicit gate.

Reuse Phase 2 loading, fitted Phase 3 pipelines, fixed-label metrics and Phase 4
hard_vote. No training entry point, calibration, model selection or source sync.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import warnings

import joblib
import numpy as np
import pandas as pd
import psutil
import scipy
import sklearn
from sklearn import config_context
from sklearn.metrics import precision_recall_fscore_support
from threadpoolctl import threadpool_limits

from src.data.integrity import read_baseline, verify_training_inputs
from src.data.loader import sha256_file
from src.data.paths import OutputPaths
from src.data.preprocessing import load_final_split
from src.models.ensemble import (HARD, PRIORITY, class_predictions, hard_vote,
                                 phase4_guard, require, score_prediction)
from src.models.final_evaluation_protocol import FROZEN_PROTOCOL
from src.models.training import build_pipeline, json_bytes, load_fitted_checkpoint
from src.models.tuning import read_tuning_result


def protocol():
    """An independent copy, never silently updated from a Drive manifest."""
    return json.loads(json_bytes(FROZEN_PROTOCOL))


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def authorization_text():
    return f"AUTHORIZE ONE-TIME LOCKED TEST {protocol()['protocol_id']} {digest(protocol())}"


def versions():
    return {"python": platform.python_version(), "sklearn": sklearn.__version__,
            "numpy": np.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__}


def namespace(root):
    return Path(root) / "artifacts/metadata/final_evaluation" / digest(protocol())[:16]


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _verify_file(root, relative, entry):
    path = (root / relative).resolve()
    require(path.is_relative_to(root) and path.is_file(), f"Missing/outside artifact: {relative}")
    require(path.stat().st_size == entry["bytes"] and sha256_file(path) == entry["sha256"],
            f"Checksum/size mismatch: {relative}")


def _code_identity(session):
    root = session.paths.project_root
    return {name: sha256_file(root / name) for name in (
        "src/models/final_evaluation.py", "src/models/final_evaluation_protocol.py",
        "src/models/ensemble.py", "src/data/colab_runtime.py")}


def preflight(session):
    """READ ONLY, no deserialization or test CSV open/hash/stat/read.

    The existing Phase 4 guard rejects any accidental test CSV open, even hashing.
    Test identity/counts below come from already locked manifests, not payloads.
    """
    root = session.paths.storage_root.resolve()
    frozen = protocol()
    with phase4_guard(root) as guard:
        baseline = read_baseline(session.paths.project_root / "configs/phase2_integrity.json")
        inputs = verify_training_inputs(OutputPaths(root), baseline=baseline)
        require(inputs["manifest_sha256"] == frozen["phase2_manifest_sha256"],
                "Phase 2 manifest differs from the checkpoint-bound Drive variant; do not replace it.")
        require(inputs["manifest"]["files"] == frozen["phase2_files"]
                and inputs["manifest"]["processed"] == frozen["processed"], "Phase 2 identity differs.")
        test = frozen["test"]
        row = next(r for r in inputs["splits"]["splits"] if r["split"] == "test")
        require(row["dedup_records"] == test["records"] and row["groups"] == test["groups"]
                and row["classes"] == test["classes"], "Locked test metadata differs.")
        require(len(inputs["schema"]["features"]) == test["features"]
                and len(inputs["labels"]["classes"]) == test["classes"], "Schema/mapping dimensions differ.")
        ti = frozen["tuning"]
        tm = root / "artifacts/metadata/tuning" / ti["experiment_id"] / "manifest.json"
        require(sha256_file(tm) == ti["manifest_sha256"], "Tuning manifest is not the frozen audited run.")
        tuned = read_tuning_result(root, ti["experiment_id"])
        ei = frozen["ensemble"]
        em = root / "artifacts/metadata/runs" / ei["run_id"] / "tuned_ensemble_manifest.json"
        require(sha256_file(em) == ei["manifest_sha256"], "Tuned ensemble manifest differs.")
        ensemble = _read(em)
        require(ensemble["run_id"] == ei["run_id"] and ensemble["tuning_experiment"] == ti["experiment_id"]
                and ensemble["tuning_manifest_sha256"] == ti["manifest_sha256"]
                and ensemble["selected_identity"] == tuned["identity"], "Ensemble provenance differs.")
        require(list(HARD[ei["key"]]) == ensemble["hard"][ei["key"]] == ei["members"]
                and list(PRIORITY) == ensemble["hard_tie_priority"] == ei["priority"]
                and sha256_file(session.paths.project_root / "src/models/ensemble.py") == ei["engine_source_sha256"],
                "Hard voting engine/members/tie priority differs.")
        expected_ensemble_files = {
            f"artifacts/metadata/runs/{ei['run_id']}/tuned_ensemble_predictions.npz",
            f"artifacts/metadata/runs/{ei['run_id']}/tuned_results.json",
            f"reports/runs/{ei['run_id']}/tables/tuned_validation_comparison.csv",
            f"reports/runs/{ei['run_id']}/tuned_ensemble_validation.md"}
        require(set(ensemble["files"]) == expected_ensemble_files, "Unexpected ensemble bundle inventory.")
        for relative, entry in ensemble["files"].items():
            _verify_file(root, relative, entry)
        rows = []
        for key, cp in frozen["checkpoints"].items():
            folder, identity = root / cp["folder"], cp["identity"]
            require(identity["versions"] == versions(), "Checkpoint environment differs: " + json.dumps(identity["versions"]))
            require(identity["phase2_manifest_sha256"] == inputs["manifest_sha256"]
                    and identity["processed_fingerprint"] == inputs["manifest"]["processed"]["sha256"]
                    and identity["training_data_fingerprint"] == inputs["manifest"]["files"]["data/processed/train.csv.gz"]["sha256"]
                    and identity["validation_data_fingerprint"] == inputs["manifest"]["files"]["data/processed/validation.csv.gz"]["sha256"]
                    and identity["feature_schema_identity"] == inputs["manifest"]["files"]["artifacts/metadata/phase2/feature_schema.json"]["sha256"]
                    and identity["label_mapping_identity"] == inputs["manifest"]["files"]["artifacts/metadata/phase2/label_mapping.json"]["sha256"],
                    "Checkpoint data/schema/mapping identity differs.")
            if key != "lr_baseline":
                require(identity == tuned["identity"], "Selected checkpoint identity differs from freeze.")
            for relative, expected in identity["source_sha256"].items():
                require(sha256_file(session.paths.project_root / relative) == expected, "Original model source differs: " + relative)
            for name, entry in cp["files"].items():
                _verify_file(root, cp["folder"] + "/" + name, entry)
            fit, meta = _read(folder / "fit.json"), _read(folder / "metadata.json")
            require(fit["status"] == "fitted" and meta["status"] == "completed"
                    and fit["identity"] == meta["identity"] == identity
                    and fit["model"] == meta["model"] == cp["model"]
                    and fit["pipeline_sha256"] == cp["files"]["pipeline.joblib"]["sha256"]
                    and meta["fit_metadata_sha256"] == sha256_file(folder / "fit.json")
                    and fit["n_input_features"] == test["features"]
                    and meta["predictions_sha256"] == sha256_file(folder / "validation_predictions.npz"),
                    "Fitted/completed checkpoint metadata differs.")
            rows.append({"checkpoint": key, "status": "PASS", "experiment_id": identity["experiment_id"],
                         "pipeline_sha256": fit["pipeline_sha256"], "features": fit["n_input_features"]})
        code = _code_identity(session)
        status = "NOT STARTED"
        dest = namespace(root)
        if (dest / "execution.json").exists():
            status = "COMPLETED; DO NOT RERUN" if (dest / "manifest.json").is_file() else "STARTED/PARTIAL; OWNER REVIEW REQUIRED"
        elif dest.exists() and any(dest.iterdir()):
            status = "ORPHANED OUTPUT; OWNER REVIEW REQUIRED"
        result = {"status": "PASS", "protocol_sha256": digest(frozen), "code_sha256": code,
                  "storage_root": str(root), "checkpoints": rows, "execution_status": status,
                  "test_identity_from_metadata_only": test, "test_payload_opened": False,
                  "guards": dict(guard)}
    return result


@contextmanager
def _no_learning():
    """Same profiling rule as Phase4, allowing only metrics' temporary LabelEncoder."""
    previous = sys.getprofile()
    def profile(frame, event, arg):
        module = frame.f_globals.get("__name__", "")
        if event != "call" or not module.startswith("sklearn.") or frame.f_code.co_name not in {"fit", "fit_transform", "partial_fit"}:
            return
        if module == "sklearn.preprocessing._label" and type(frame.f_locals.get("self")).__name__ == "LabelEncoder":
            parent = frame.f_back
            while parent:
                if parent.f_globals.get("__name__") == "sklearn.metrics._classification":
                    return
                parent = parent.f_back
        raise RuntimeError("Final evaluation forbids fitting models, preprocessing and calibrators.")
    sys.setprofile(profile)
    try:
        yield
    finally:
        sys.setprofile(previous)


def _load_models(session, frozen):
    models = {}
    with phase4_guard(session.paths.storage_root):
        for key, cp in frozen["checkpoints"].items():
            require(psutil.virtual_memory().available / 2**30 >= 2, "Insufficient free RAM before model load.")
            model = load_fitted_checkpoint(session.paths.storage_root / cp["folder"], cp["identity"], trusted=True)
            expected = build_pipeline(cp["model"], cp["identity"]["config"])
            require(model.feature_names_in_.tolist() == session.inputs["schema"]["features"]
                    and np.array_equal(model.classes_, np.arange(frozen["test"]["classes"]))
                    and [k for k, _ in model.steps] == [k for k, _ in expected.steps]
                    and all(type(a) is type(b) and a.get_params(deep=False) == b.get_params(deep=False)
                            for (_, a), (_, b) in zip(model.steps, expected.steps)),
                    "Reloaded feature/class order, transformer or estimator config differs.")
            models[key] = model
    return models


def _predict_batches(model, frame, n_classes, progress):
    blocks = []
    for start in range(0, len(frame), 64):
        blocks.append(class_predictions(model.predict(frame.iloc[start:start + 64]),
                                        min(64, len(frame) - start), n_classes))
        if start % 4096 == 0 or start + 64 >= len(frame):
            progress(f"  Test: {min(start + 64, len(frame)):,}/{len(frame):,}")
    return np.concatenate(blocks)


def analyze(y, predictions, groups, classes, validation_reference):
    """Fixed-label descriptive comparisons; no ranking/selection or thresholds."""
    c = len(classes)
    y = class_predictions(y, len(y), c)
    groups = np.asarray(groups)
    require(groups.shape == y.shape, "Group alignment differs.")
    _, inverse = np.unique(groups, return_inverse=True)
    size = np.bincount(inverse)
    per_class = pd.DataFrame({"class_id": np.arange(c), "disease": classes,
                              "test_support": np.bincount(y, minlength=c)})
    per_class["test_independent_groups"] = [len(np.unique(groups[y == k])) for k in range(c)]
    per_class["support_bin"] = pd.cut(per_class["test_support"], [-1, 0, 1, 5, 20, np.inf],
                                      labels=["0", "1", "2-5", "6-20", ">20"]).astype(str)
    comparison, transitions, means = [], [], {}
    group_table = pd.DataFrame({"group_id": np.unique(groups), "rows": size})
    for key in protocol()["candidates"]:
        pred = class_predictions(predictions[key], len(y), c)
        scores = score_prediction(y, pred, c)
        for split, metrics in (("validation", validation_reference[key]), ("test", scores)):
            comparison.append({"candidate": key, "split": split,
                               **{k: v for k, v in metrics.items() if k in scores}})
        precision, recall, f1, _ = precision_recall_fscore_support(y, pred, labels=np.arange(c), zero_division=0)
        for label, values in (("precision", precision), ("recall", recall), ("f1", f1)):
            per_class[key + "_" + label] = values
        means[key] = np.bincount(inverse, weights=(pred == y), minlength=len(size)) / size
        group_table[key + "_correct_fraction"] = means[key]
    for left, right in protocol()["analysis"]["pairs"]:
        a, b = predictions[left] == y, predictions[right] == y
        delta = means[right] - means[left]
        group_table[right + "_minus_" + left] = delta
        transitions.append({"reference": left, "candidate": right, "both_correct": int((a & b).sum()),
            "both_wrong": int((~a & ~b).sum()), "rescues": int((~a & b).sum()), "new_errors": int((a & ~b).sum()),
            "equal_group_accuracy_reference": float(means[left].mean()),
            "equal_group_accuracy_candidate": float(means[right].mean()), "equal_group_delta": float(delta.mean()),
            "groups_improved": int((delta > 0).sum()), "groups_worsened": int((delta < 0).sum()),
            "groups_equal": int((delta == 0).sum())})
    return {"comparison": pd.DataFrame(comparison), "per_class": per_class,
            "transitions": pd.DataFrame(transitions), "group_differences": group_table}


def _create(path, payload):
    """Exclusive creation only. Never replace existing or partial artifacts."""
    with Path(path).open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _figure(tables):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    comparison = tables["comparison"].pivot(index="candidate", columns="split", values="macro_f1")
    comparison = comparison.reindex(protocol()["candidates"])
    comparison.plot.bar(ax=axes[0], ylim=(0, 1), rot=18, ylabel="Macro F1 / 587 labels", title="Frozen candidates; no model reselection")
    per_class = tables["per_class"]
    for key in protocol()["candidates"]:
        means = per_class.groupby("support_bin", observed=True)[key + "_f1"].mean()
        means.reindex(protocol()["analysis"]["support_bins"]).plot(ax=axes[1], marker="o", label=key)
    axes[1].set(xlabel="Test support bin (descriptive)", ylabel="Mean class F1", ylim=(0, 1))
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    stream = io.BytesIO()
    fig.savefig(stream, format="png", dpi=140)
    plt.close(fig)
    return stream.getvalue()


def evaluate(session, *, enabled=False, owner_authorization="", prepared=None, progress=print):
    """Only a subsequent owner-authorized execution may pass BOTH gate inputs.

    An exclusive execution marker consumes the one-time slot BEFORE loading test.
    Started/failed runs never auto-resume or silently become a second test run.
    """
    if not enabled:
        progress("SKIPPED: RUN_FINAL_LOCKED_TEST=False. No test payload access or predictions.")
        return None
    require(owner_authorization == authorization_text(), "Separate explicit owner authorization required for this exact protocol.")
    fresh = preflight(session)
    require(prepared is not None and fresh == prepared, "Run read-only preflight again; prepared identity/source/root/status differs.")
    require(fresh["execution_status"] == "NOT STARTED", "Evaluation already started/completed. No automatic rerun/resume.")
    frozen = protocol()
    models = _load_models(session, frozen)  # Check fitted object configs BEFORE consuming any test data.
    root = session.paths.storage_root.resolve()
    dest = namespace(root)
    dest.mkdir(parents=True, exist_ok=True)
    execution = {"status": "started", "started_utc": datetime.now(timezone.utc).isoformat(),
                 "protocol_sha256": digest(frozen), "code_sha256": fresh["code_sha256"],
                 "owner_authorization": owner_authorization, "deployment_candidate": frozen["deployment_candidate"]}
    _create(dest / "execution.json", json_bytes(execution))
    try:
        with _no_learning(), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            require(sha256_file(root / "artifacts/metadata/phase2/dataset_manifest.json") == frozen["phase2_manifest_sha256"],
                    "Phase 2 manifest changed after preflight; slot consumed, owner review required.")
            # ONE loader invocation; it internally checks SHA then parses CSV. No test cache/copy.
            x, y, groups = load_final_split(OutputPaths(root), "test")
            require(x.shape == (frozen["test"]["records"], frozen["test"]["features"])
                    and x.columns.tolist() == session.inputs["schema"]["features"]
                    and np.isin(x.to_numpy(), [0, 1]).all()
                    and len(np.unique(groups)) == frozen["test"]["groups"], "Loaded test dimensions/schema/binary/groups differ.")
            class_predictions(y, len(x), frozen["test"]["classes"])
            assignments = pd.read_csv(root / "artifacts/metadata/phase2/split_assignments.csv.gz")
            other = assignments.loc[assignments["split"].isin(["train", "validation"]), "group_id"]
            require(not set(groups.tolist()) & set(other.tolist()), "Test groups overlap train/validation.")
            predictions, members = {}, {}
            with threadpool_limits(limits=1), config_context(working_memory=128):
                for key in ("lr_baseline", "lr_tuned_c2", "svc_tuned", "knn_tuned"):
                    progress("Predict fitted checkpoint: " + key)
                    value = _predict_batches(models[key], x, frozen["test"]["classes"], progress)
                    if key in ("lr_baseline", "lr_tuned_c2"):
                        predictions[key] = value
                    if key != "lr_baseline":
                        members[frozen["checkpoints"][key]["model"]] = value
                predictions["hard_tuned_lr_svc_knn"], ties = hard_vote(members, HARD[frozen["ensemble"]["key"]], frozen["test"]["classes"])
            tables = analyze(y, predictions, groups, session.inputs["labels"]["classes"], frozen["validation_reference"])
            files = {}
            def save(name, payload):
                path = dest / name
                _create(path, payload)
                files[name] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
            save("protocol.json", json_bytes(frozen))
            save("preflight.json", json_bytes(fresh))
            stream = io.BytesIO()
            np.savez_compressed(stream, y_true=y, group_id=groups, row_0based=np.arange(len(y)), **predictions)
            save("test_predictions.npz", stream.getvalue())
            for name, table in tables.items():
                save(name + ".csv", table.to_csv(index=False, lineterminator="\n").encode("utf-8"))
            save("comparison.png", _figure(tables))
            summary = {"status": "completed", "protocol_sha256": digest(frozen),
                "deployment_candidate": frozen["deployment_candidate"], "model_selection_from_test": False,
                "models_fitted": 0, "test_loader_calls": 1, "records": len(y), "groups": len(np.unique(groups)),
                "labels": frozen["test"]["classes"], "missing_label_ids": np.flatnonzero(np.bincount(y, minlength=frozen["test"]["classes"]) == 0).tolist(),
                "hard_tie_rows": ties, "metrics": tables["comparison"].to_dict("records"),
                "warnings": [f"{w.category.__name__}: {w.message}" for w in caught]}
            save("results.json", json_bytes(summary))
            report = ("# Final locked-test evaluation\n\nDeployment fixed BEFORE test: LR tuned C=2. No selection from test.\n\n"
                + tables["comparison"].to_csv(index=False)
                + "\nPaired transitions (candidate vs reference):\n" + tables["transitions"].to_csv(index=False)
                + "\nEqual-group differences are descriptive, not significance tests. Synthetic dataset; conflicting labels may share symptom vectors. "
                + "Phase1 inspected the whole raw CSV. Held out from fitting/tuning, not a pristine blind external test. "
                + "No clinical validation, calibrated probabilities or measured LLM-input generalization. "
                + "Deployment remains LR tuned C=2 regardless of scores.\n")
            save("report.md", report.encode("utf-8"))
            files["execution.json"] = {"bytes": (dest / "execution.json").stat().st_size, "sha256": sha256_file(dest / "execution.json")}
            manifest = {**summary, "finished_utc": datetime.now(timezone.utc).isoformat(),
                        "execution": execution, "source_sha256": fresh["code_sha256"], "versions": versions(), "files": files}
            _create(dest / "manifest.json", json_bytes(manifest))  # Completion marker LAST.
        progress("COMPLETED final evaluation: " + str(dest))
        return {"folder": str(dest), "manifest_sha256": sha256_file(dest / "manifest.json"), **summary}
    except BaseException as exc:
        _create(dest / "failure.json", json_bytes({"status": "partial_requires_owner_review", "error": type(exc).__name__ + ": " + str(exc),
                                                   "protocol_sha256": digest(frozen)}))
        raise


def read_completed(folder):
    """Verified report-only replay. Does NOT load models or reopen the test CSV."""
    folder = Path(folder)
    manifest = _read(folder / "manifest.json")
    require(manifest["status"] == "completed" and manifest["protocol_sha256"] == digest(protocol()), "Not a completed frozen run.")
    expected = {"execution.json", "protocol.json", "preflight.json", "test_predictions.npz", "comparison.csv",
                "per_class.csv", "transitions.csv", "group_differences.csv", "comparison.png", "results.json", "report.md"}
    require(set(manifest["files"]) == expected, "Incomplete/unexpected final result inventory.")
    for relative, entry in manifest["files"].items():
        _verify_file(folder.resolve(), relative, entry)
    require(_read(folder / "protocol.json") == protocol(), "Published protocol differs from freeze.")
    return manifest


def show_result(result):
    """Display only published results, with no inference side effects."""
    if result is None:
        print("CHƯA ĐÁNH GIÁ TEST: gate đang tắt. Không có điểm test để hiển thị.")
        return
    from IPython.display import display, Image, Markdown
    folder = Path(result["folder"])
    read_completed(folder)
    for name in ("comparison", "transitions"):
        display(pd.read_csv(folder / (name + ".csv")))
    per_class = pd.read_csv(folder / "per_class.csv")
    display(per_class.groupby("support_bin", observed=True).agg(classes=("class_id", "size"), records=("test_support", "sum")))
    display(per_class.head(12))
    display(Image(filename=str(folder / "comparison.png")))
    display(Markdown((folder / "report.md").read_text(encoding="utf-8")))
