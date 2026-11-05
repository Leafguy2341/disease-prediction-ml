"""Read-only Colab audit of saved tuning artifacts. No fit, predict, export or API calls.

Run with an existing project session, after uploading THIS script to /content:
api = runpy.run_path('/content/audit_post_tuning.py')
result = api['audit_post_tuning'](session, trusted=True)
api['emit_packet'](result)
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager, ExitStack
import base64
import builtins
import gc
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import socket
from unittest.mock import patch

import numpy as np
import psutil

from src.data.integrity import read_baseline, verify_training_inputs
from src.data.loader import sha256_file
from src.data.paths import OutputPaths
from src.models.ensemble import (EXPERIMENT, HARD, SOFT, PRIORITY, IntegrityError,
                                 hard_vote, phase4_guard, require, score_prediction)
from src.models.runtime import MODEL_NAMES, load_training_data
from src.models.training import (build_pipeline, experiment_identity, json_bytes,
                                 load_fitted_checkpoint, read_completed_checkpoint)
from src.models.tuning import _paths, digest, grouped_folds, read_tuning_result

EXPERIMENT_ID = "tuning-v1-9c4dd013abbba14a"


@contextmanager
def read_only(root):
    """Use the existing fit/test guard, and forbid ALL writes and network locally."""
    with phase4_guard(root) as counts, ExitStack() as stack:
        counts.update(read_only_write_attempts=0, network_attempts=0)
        def guard_open(original):
            def call(file, mode="r", *args, **kwargs):
                if any(c in str(mode) for c in "wax+"):
                    counts["read_only_write_attempts"] += 1
                    raise IntegrityError("Read-only audit forbids writes.")
                return original(file, mode, *args, **kwargs)
            return call
        def no_mutation(*args, **kwargs):
            counts["read_only_write_attempts"] += 1
            raise IntegrityError("Read-only audit forbids filesystem mutation.")
        def no_network(*args, **kwargs):
            counts["network_attempts"] += 1
            raise IntegrityError("Read-only artifact audit forbids network.")
        stack.enter_context(patch.object(builtins, "open", guard_open(builtins.open)))
        stack.enter_context(patch.object(io, "open", guard_open(io.open)))
        for name in ("rename", "replace", "remove", "unlink", "mkdir", "rmdir"):
            stack.enter_context(patch.object(os, name, no_mutation))
        stack.enter_context(patch.object(socket, "create_connection", no_network))
        yield counts


def verify_bundle(root, manifest, expected_names):
    require(set(manifest["files"]) == set(expected_names), "Unexpected/missing artifact paths in ensemble manifest.")
    for name, record in manifest["files"].items():
        path = (root / name).resolve()
        require(path.is_relative_to(root), "Artifact escapes storage root.")
        require(path.is_file() and path.stat().st_size == record["bytes"]
                and sha256_file(path) == record["sha256"], f"Artifact checksum mismatch: {name}")


def cv_inventory(y, groups, assignment, n_classes):
    y, groups, assignment = np.asarray(y), np.asarray(groups), np.asarray(assignment)
    require(y.ndim == groups.ndim == assignment.ndim == 1 and len(y) == len(groups) == len(assignment), "CV alignment mismatch.")
    require(np.issubdtype(assignment.dtype, np.integer) and set(assignment.tolist()) == {0, 1, 2}, "Expected exactly three CV folds.")
    result = []
    for k in range(3):
        a, b = assignment != k, assignment == k
        require(not set(groups[a].tolist()) & set(groups[b].tolist()), "CV group leakage.")
        result.append({"fold": k, "train_rows": int(a.sum()), "holdout_rows": int(b.sum()),
            "train_groups": len(set(groups[a].tolist())), "holdout_groups": len(set(groups[b].tolist())),
            "missing_train_classes": sorted(set(range(n_classes)) - set(y[a].tolist())),
            "missing_holdout_classes": sorted(set(range(n_classes)) - set(y[b].tolist()))})
    return result


def trial_summary(trials):
    warnings_by_category, warnings_samples = Counter(), {}
    failed, interrupted, rows = [], [], []
    for trial in trials:
        last = {a["fold"]: a for a in trial["attempts"]}
        for a in trial["attempts"]:
            for message in a.get("warnings", []):
                category = message.split(":", 1)[0]
                warnings_by_category[category] += 1
                warnings_samples.setdefault(category, message[:500])
            if a["status"] in {"failed", "interrupted"}:
                target = failed if a["status"] == "failed" else interrupted
                target.append({"model": trial["model"], "candidate": trial["candidate"], "fold": a["fold"],
                               "error_type": a.get("error_type"), "error": a.get("error", "")[:500]})
        rows.append({"model": trial["model"], "candidate": trial["candidate"], "parameters": trial["parameters"],
                     "last_fold_status": {str(k): a["status"] for k, a in last.items()},
                     "attempt_count": len(trial["attempts"]),
                     "elapsed_seconds": sum(a["elapsed_seconds"] for a in trial["attempts"])})
    return {"candidates": rows, "failed_attempts": failed, "interrupted_attempts": interrupted,
            "warning_counts": dict(warnings_by_category), "warning_samples": warnings_samples,
            "convergence_warning_count": warnings_by_category.get("ConvergenceWarning", 0),
            "resume_limit": "Repeated/interrupted attempts are evidence; absence of them cannot prove historical exactly-once execution."}


def _check_identity(identity, config, inputs, source_root):
    original = {k: v for k, v in identity.items() if k != "experiment_id"}
    require(identity["experiment_id"] == identity["config"]["run_tag"] + "-" + digest(original)[:16], "Checkpoint identity digest mismatch.")
    current = experiment_identity(source_root, config, inputs)
    for key in ("processed_fingerprint", "training_data_fingerprint", "validation_data_fingerprint",
                "feature_schema_identity", "label_mapping_identity"):
        require(identity[key] == current[key], f"Checkpoint input identity mismatch: {key}")
    return current


def _reload(folder, identity, current, features, variable_mask, *, trusted, resource):
    if not trusted:
        return {"status": "NOT VERIFIED", "reason": "trusted=False; checksum and saved predictions still audited"}
    if identity["versions"] != current["versions"]:
        return {"status": "NOT VERIFIED", "reason": "Environment differs from checkpoint", "saved": identity["versions"], "current": current["versions"]}
    changed = [n for n, h in identity["source_sha256"].items() if sha256_file(Path(current["_source_root"]) / n) != h]
    if changed:
        return {"status": "NOT VERIFIED", "reason": "Relevant checkpoint source changed", "files": changed}
    if psutil.virtual_memory().available / 2**30 < resource["min_available_ram_gb"]:
        return {"status": "NOT VERIFIED", "reason": "Insufficient free RAM for sequential reload"}
    model = load_fitted_checkpoint(folder, identity, trusted=True)
    try:
        reference = build_pipeline(folder.name, identity["config"])
        require(model.feature_names_in_.tolist() == features, "Loaded feature order mismatch.")
        require(np.array_equal(model.classes_, np.arange(len(current["_classes"]))), "Loaded class order mismatch.")
        require(np.array_equal(model.named_steps["variance"].get_support(), variable_mask), "Loaded variance mask differs from train-only mask.")
        require([n for n, _ in model.steps] == [n for n, _ in reference.steps]
                and all(type(a) is type(b) and a.get_params(deep=False) == b.get_params(deep=False)
                        for (_, a), (_, b) in zip(model.steps, reference.steps)), "Loaded pipeline/config mismatch.")
        return {"status": "PASS", "input_features": int(model.n_features_in_), "class_order": "PASS",
                "variance_mask": "PASS", "prediction_called": False}
    finally:
        del model
        gc.collect()


def _ensemble(root, result, predictions, y, groups, classes, *, ensemble_run_id=None):
    matches = []
    for path in (root / "artifacts/metadata/runs").glob("tuned-ensemble-*/tuned_ensemble_manifest.json"):
        if ensemble_run_id is not None and path.parent.name != ensemble_run_id:
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("tuning_experiment") == result["experiment_id"]:
            matches.append((path, manifest))
    if len(matches) != 1:
        return {"status": "NOT VERIFIED", "reason": "Need exactly one matching ensemble run or explicit ensemble_run_id", "runs": [p.parent.name for p, _ in matches]}
    path, manifest = matches[0]
    run = path.parent.name
    require(manifest["run_id"] == run and manifest["selected_identity"] == result["identity"], "Ensemble selected identity mismatch.")
    require(manifest["tuning_manifest_sha256"] == sha256_file(_paths(root, result["experiment_id"])[0] / "manifest.json"), "Ensemble references another tuning manifest.")
    meta, reports = path.parent, root / "reports/runs" / run
    expected = [reports / "tables/tuned_validation_comparison.csv", meta / "tuned_ensemble_predictions.npz",
                meta / "tuned_results.json", reports / "tuned_ensemble_validation.md"]
    verify_bundle(root, manifest, [p.relative_to(root).as_posix() for p in expected])
    saved_result = json.loads((meta / "tuned_results.json").read_text(encoding="utf-8"))
    require(all(manifest[k] == v for k, v in saved_result.items()), "Ensemble results differ from manifest.")
    require(manifest["base_models_fitted"] == 0 and not manifest["test_payload_opened"], "Ensemble declares forbidden fit/test access.")
    require(not any(manifest["guards"].values()), "Ensemble guard reports a forbidden operation.")
    require(manifest["hard"] == {k: list(v) for k, v in HARD.items()}
            and manifest["soft"] == {k: list(v) for k, v in SOFT.items()}, "Voting combinations changed.")
    require(manifest["hard_tie_priority"] == list(PRIORITY)
            and manifest["soft_tie_rule"] == "exact mean tie -> LR probability -> English label Unicode order", "Voting tie policies changed.")
    rows = {r["combination"]: r for r in manifest["records"]}
    evaluated = {}
    with np.load(meta / "tuned_ensemble_predictions.npz", allow_pickle=False) as payload:
        require(np.array_equal(payload["y_true"], y) and np.array_equal(payload["group_id"], groups)
                and np.array_equal(payload["row_0based"], np.arange(len(y))), "Ensemble row/group alignment mismatch.")
        for name in (*HARD, *SOFT):
            if rows[name]["status"] != "completed":
                evaluated[name] = {"status": "NOT VERIFIED", "reason": rows[name].get("reason", "not completed")}
                continue
            predicted = payload[name]
            scores = score_prediction(y, predicted, len(classes))
            require(all(np.isclose(scores[k], rows[name][k], rtol=0, atol=1e-12) for k in scores), f"Ensemble metrics mismatch: {name}")
            if name in HARD:
                voted, ties = hard_vote(predictions, HARD[name], len(classes))
                require(np.array_equal(predicted, voted) and ties == rows[name]["tie_rows"], "Saved hard vote does not reproduce original tie policy.")
            evaluated[name] = {"status": "PASS", **scores, "pipeline_bytes": rows[name]["pipeline_bytes"],
                "saved_validation_predict_seconds_sum": rows[name]["original_base_predict_seconds_sum"]}
    return {"status": "PASS", "run_id": run, "manifest_sha256": sha256_file(path), "metrics": evaluated,
            "soft_probability_recomputation": "NOT VERIFIED: ephemeral probabilities not persisted; saved prediction metrics verified, no new predict_proba run",
            "recommendation_saved": manifest["recommendation"], "probability_sources": manifest["probability_sources"]}


def audit_post_tuning(session, *, experiment_id=EXPERIMENT_ID, ensemble_run_id=None, trusted=False):
    """Only reads existing artifacts; imports/config are supplied by the existing runtime."""
    root, source_root = session.paths.storage_root.resolve(), session.paths.project_root.resolve()
    with read_only(root) as guards:
        try:
            print("AUDIT: checksums/schema/train-validation inputs", flush=True)
            result = read_tuning_result(root, experiment_id)
            meta, models, _ = _paths(root, experiment_id)
            descriptor = json.loads((meta / "experiment.json").read_text(encoding="utf-8"))
            inputs = verify_training_inputs(OutputPaths(root), baseline=read_baseline(source_root / "configs/phase2_integrity.json"))
            data = load_training_data(OutputPaths(root), inputs)  # Sole existing loader, no cache/write.
            x, y, groups = data["validation"]
            train_x, train_y, train_groups = data["train"]
            features, classes = inputs["schema"]["features"], inputs["labels"]["classes"]
            require(len(features) == 375 and len(classes) == 587, "Expected approved 375 features and 587 classes.")
            with np.load(meta / "cv_assignments.npz", allow_pickle=False) as saved:
                require(np.array_equal(saved["row_0based"], np.arange(len(train_y)))
                        and np.array_equal(saved["group_id"], train_groups), "Stored CV rows/groups differ from locked train.")
                assignment = saved["fold"].copy()
            require(hashlib.sha256(assignment.tobytes()).hexdigest() == descriptor["assignment_sha256"], "CV assignment digest mismatch.")
            inventory = cv_inventory(train_y, train_groups, assignment, len(classes))
            require(inventory == descriptor["fold_inventory"] == result["fold_inventory"], "Stored CV class coverage/counts are incorrect.")
            require(result["plan"]["seed"] == 42 and result["plan"]["folds"] == 3
                    and result["plan"]["splitter"] == "StratifiedGroupKFold" and result["plan"]["shuffle"] is True
                    and result["plan"]["scoring"].startswith("mean fold macro_f1 over ALL saved class IDs")
                    and result["selection_data"] == "train_only_group_cv" and not result["validation_used_for_search"], "Unexpected tuning selection/scoring policy.")
            require(not result["test_payload_opened"] and not result["application_model_changed"], "Tuning declares forbidden test/application-model changes.")
            require(result["identity"]["tuning_experiment"] == experiment_id
                    and result["identity"]["selection_sha256"] == sha256_file(meta / "selection.json")
                    and result["identity"]["config"]["models"] == {n: result["selection"][n]["parameters"] for n in MODEL_NAMES}, "Selected config/CV linkage mismatch.")
            state = json.loads((meta / "trials.json").read_text(encoding="utf-8"))
            trials = trial_summary(state["trials"])
            current = _check_identity(result["identity"], result["identity"]["config"], inputs, source_root)
            _check_identity(descriptor["base"], descriptor["base"]["config"], inputs, source_root)
            require(descriptor["baseline_experiment"] == result["baseline_experiment"] == EXPERIMENT,
                    "Tuning baseline reference mismatch.")
            deterministic = "NOT VERIFIED: runtime versions differ from the saved CV environment"
            if descriptor["base"]["versions"] == current["versions"]:
                print("AUDIT: reproduce train-only grouped CV assignment (no fitting)", flush=True)
                try:
                    regenerated = grouped_folds(train_y, train_groups, len(classes), descriptor["plan"])[1]
                    require(np.array_equal(regenerated, assignment), "Seed42 grouped CV assignment is not reproducible.")
                    deterministic = "PASS"
                except MemoryError:
                    deterministic = "NOT VERIFIED: insufficient RAM for SGKF reproduction; saved group assignments still checked"
            current.update(_source_root=str(source_root), _classes=classes)
            variable_mask = train_x.max(axis=0).to_numpy() != train_x.min(axis=0).to_numpy()
            predictions, checked_models, comparisons = {}, {}, []
            print("AUDIT: verify five selected pipelines and saved validation predictions", flush=True)
            for name in MODEL_NAMES:
                metadata, prediction = read_completed_checkpoint(models / name, result["identity"], y, groups)
                require(metadata["model"] == name and metadata["n_input_features"] == 375
                        and metadata["n_retained_features"] == int(variable_mask.sum()), "Selected feature metadata mismatch.")
                require(all(metadata["parameters"][k] == v for k, v in result["selection"][name]["parameters"].items()), "Saved selected hyperparameters mismatch.")
                predictions[name] = prediction
                scores = score_prediction(y, prediction, len(classes))
                reload_result = _reload(models / name, result["identity"], current, features, variable_mask,
                    trusted=trusted, resource=result["plan"]["resources"])
                checked_models[name] = {"checksum_and_saved_predictions": "PASS", "metrics": scores,
                    "pipeline_sha256": metadata["pipeline_sha256"], "pipeline_bytes": (models / name / "pipeline.joblib").stat().st_size,
                    "fit_seconds": metadata["fit_seconds"], "validation_predict_seconds": metadata["prediction_seconds"],
                    "warnings_by_category": dict(Counter(w.split(":", 1)[0] for w in metadata["warnings"])),
                    "convergence_warnings": [w[:500] for w in metadata["warnings"] if "ConvergenceWarning" in w], "reload": reload_result}
            base_folder = root / "artifacts/models/phase3" / EXPERIMENT / "logistic_regression"
            base_identity = json.loads((base_folder / "fit.json").read_text(encoding="utf-8"))["identity"]
            _check_identity(base_identity, session.config, inputs, source_root)
            require(base_identity["config"] == session.config and base_identity["experiment_id"] == EXPERIMENT, "Unexpected baseline config.")
            baseline_metadata, baseline_prediction = read_completed_checkpoint(base_folder, base_identity, y, groups)
            baseline_scores = score_prediction(y, baseline_prediction, len(classes))
            require(abs(baseline_scores["macro_f1"] - .78780814) <= 5.1e-9, "LR baseline differs from independently audited reference.")
            comparisons.append({"model": "LR baseline", **baseline_scores, "pipeline_bytes": (base_folder / "pipeline.joblib").stat().st_size,
                                "saved_validation_predict_seconds_sum": baseline_metadata["prediction_seconds"]})
            lr = checked_models["logistic_regression"]
            comparisons.append({"model": "LR tuned", **lr["metrics"], "pipeline_bytes": lr["pipeline_bytes"],
                                "saved_validation_predict_seconds_sum": lr["validation_predict_seconds"]})
            print("AUDIT: ensemble manifest, original hard-vote policy and saved metrics", flush=True)
            ensemble = _ensemble(root, result, predictions, y, groups, classes, ensemble_run_id=ensemble_run_id)
            if ensemble["status"] == "PASS" and ensemble["metrics"]["hard_lr_svc_knn"]["status"] == "PASS":
                hard = ensemble["metrics"]["hard_lr_svc_knn"]
                members = HARD["hard_lr_svc_knn"]
                require(hard["pipeline_bytes"] == sum(checked_models[n]["pipeline_bytes"] for n in members), "Hard ensemble checkpoint bytes mismatch.")
                comparisons.append({"model": "Hard tuned LR+SVC+KNN", **hard})
            report = {"status": "PASS" if ensemble["status"] == "PASS" else "REVIEW", "experiment_id": experiment_id,
                "tuning_manifest_sha256": sha256_file(meta / "manifest.json"), "selection": result["selection"],
                "schema_features": len(features), "label_classes": len(classes), "fold_inventory": inventory,
                "fold_class_counts": [{"fold": f["fold"], "train_classes": len(classes) - len(f["missing_train_classes"]),
                    "holdout_classes": len(classes) - len(f["missing_holdout_classes"]),
                    "missing_holdout_names": [classes[k] for k in f["missing_holdout_classes"]]} for f in inventory],
                "cv_seed42_reproduction": deterministic, "scoring_policy": result["plan"]["scoring"],
                "cv_fold_scores_recomputed_from_predictions": "NOT VERIFIED: fold predictions/models intentionally not persisted; checksummed scores and selection arithmetic verified",
                "trials": trials, "split_warnings": descriptor["split_warnings"], "models": checked_models,
                "resume_namespace_risk": "REVIEW: existing experiment digest includes split_warnings; unrelated warning differences can create another namespace. Pinned tuning source intentionally unchanged by this audit.",
                "ensemble": ensemble, "comparison": comparisons,
                "cost_limitation": "Saved validation-time sums, potentially different sessions; not measured single-request/ensemble latency or SLA.",
                "models_fitted": 0, "prediction_called": False, "test_payload_opened": False, "persistent_files_written": 0,
                "audit_source_sha256": sha256_file(Path(__file__)), "guards": guards}
            report["reported_rounded_reference_matches"] = {
                "lr_baseline_0.78780814": abs(baseline_scores["macro_f1"] - .78780814) <= 5.1e-9,
                "lr_tuned_0.793154": abs(lr["metrics"]["macro_f1"] - .793154) <= 5.1e-7,
                "hard_tuned_0.796517": (abs(ensemble["metrics"]["hard_lr_svc_knn"].get("macro_f1", -1) - .796517) <= 5.1e-7)
                    if ensemble["status"] == "PASS" else None}
            if any(m["reload"]["status"] != "PASS" for m in checked_models.values()) or trials["failed_attempts"] or trials["convergence_warning_count"]:
                report["status"] = "REVIEW"
            if not all(v is True for v in report["reported_rounded_reference_matches"].values()):
                report["status"] = "REVIEW"
            return report
        except FileNotFoundError as exc:
            return {"status": "NOT VERIFIED", "experiment_id": experiment_id, "reason": str(exc), "guards": guards}
        except (MemoryError, OSError) as exc:
            return {"status": "NOT VERIFIED", "experiment_id": experiment_id, "reason": str(exc), "guards": guards}
        except (IntegrityError, ValueError, KeyError, TypeError) as exc:
            return {"status": "BLOCKER", "experiment_id": experiment_id, "reason": str(exc), "guards": guards}


def emit_packet(result):
    raw = json_bytes(result)
    print("POST_TUNING_SHA256=" + hashlib.sha256(raw).hexdigest())
    print("POST_TUNING_GZIP_BASE64=" + base64.b64encode(gzip.compress(raw, mtime=0)).decode())
    print("POST_TUNING_STATUS=" + result["status"])
