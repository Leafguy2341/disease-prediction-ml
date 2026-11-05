"""Read-only post-training audit, run inside the existing project/Colab session.

No bootstrap, fitting, tuning, test payload, checkpoint writes, figures or benchmarks.
Upload this single helper to /content; use audit_phase3(session) after session setup.
"""
from collections import Counter
from contextlib import contextmanager, ExitStack
import base64
import gc
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import sys
from unittest.mock import patch
import warnings


REFERENCE = {
    "logistic_regression": (.83709, .78781, .83668, 91.59420, 2.15747, 6),
    "random_forest": (.70053, .49200, .69931, 15.10077, 20.68390, 3),
    "linear_svc": (.83080, .78422, .82987, 80.59617, 1.82650, 5),
    "knn": (.78314, .73103, .78680, 1.09042, 294.22415, 31),
    "bernoulli_nb": (.81486, .59934, .80525, 1.83618, 5.74700, 2),
}
RTOL, ATOL = 1e-10, 1e-12


class AuditFitForbidden(BaseException):
    """Abort the entire audit before a fit body; never swallowed by model handlers."""


@contextmanager
def read_only_audit(storage):
    """Temporary guard; restored even on failure. Metrics may encode labels internally."""
    import builtins
    storage = Path(storage).resolve()
    counters = {"model_or_feature_fit_attempts": 0, "test_payload_open_attempts": 0,
                "persistent_write_attempts": 0, "metric_label_encoding_calls": 0}
    old_profile, old_bytecode = sys.getprofile(), sys.dont_write_bytecode

    def protected(path):
        return isinstance(path, (str, os.PathLike)) and Path(path).resolve().is_relative_to(storage)

    def guarded_open(original):
        def call(path, mode="r", *args, **kwargs):
            if isinstance(path, (str, os.PathLike)) and Path(path).name == "test.csv.gz":
                counters["test_payload_open_attempts"] += 1
                raise RuntimeError("AUDIT GUARD: test payload access is forbidden")
            if protected(path) and any(c in str(mode) for c in "wax+"):
                counters["persistent_write_attempts"] += 1
                raise RuntimeError(f"AUDIT GUARD: persistent write is forbidden: {path}")
            return original(path, mode, *args, **kwargs)
        return call

    def guarded_mutation(original):
        def call(*args, **kwargs):
            if any(protected(p) for p in args[:2]):
                counters["persistent_write_attempts"] += 1
                raise RuntimeError("AUDIT GUARD: persistent filesystem mutation is forbidden")
            return original(*args, **kwargs)
        return call

    def profile(frame, event, arg):
        module = frame.f_globals.get("__name__", "")
        if event != "call" or not module.startswith("sklearn.") or frame.f_code.co_name not in {"fit", "fit_transform", "partial_fit"}:
            return
        if module == "sklearn.preprocessing._label" and type(frame.f_locals.get("self")).__name__ == "LabelEncoder":
            parent = frame.f_back
            while parent is not None:
                if parent.f_globals.get("__name__") == "sklearn.metrics._classification":
                    counters["metric_label_encoding_calls"] += 1
                    return
                parent = parent.f_back
        counters["model_or_feature_fit_attempts"] += 1
        raise AuditFitForbidden("AUDIT GUARD: model/feature-transformer fitting is forbidden")

    with ExitStack() as stack:
        stack.enter_context(patch.object(builtins, "open", guarded_open(builtins.open)))
        stack.enter_context(patch.object(io, "open", guarded_open(io.open)))
        for name in ("rename", "replace", "remove", "unlink", "mkdir", "rmdir"):
            stack.enter_context(patch.object(os, name, guarded_mutation(getattr(os, name))))
        sys.dont_write_bytecode = True
        sys.setprofile(profile)
        try:
            yield counters
        finally:
            sys.setprofile(old_profile)
            sys.dont_write_bytecode = old_bytecode


def warning_rows(fit, complete):
    """Recover stages from the saved prefix; do not infer categories from counts."""
    first, all_messages = fit.get("warnings"), complete.get("warnings")
    if not isinstance(first, list) or not isinstance(all_messages, list):
        return {"status": "NOT VERIFIED", "reason": "Missing warning lists"}
    prefix = all_messages[:len(first)] == first
    entries = [("fit", message) for message in first]
    if prefix:
        entries += [("validation_predict", message) for message in all_messages[len(first):]]
    else:
        entries = [("unknown_stage", message) for message in all_messages]
    rows = []
    for (stage, original), count in Counter(entries).items():
        category, separator, message = str(original).partition(": ")
        category = category if separator else "UnknownWarning"
        message = message if separator else str(original)
        severity, action = "REVIEW", "Review the original message and verified outputs; no automatic repair."
        if category == "ConvergenceWarning":
            severity, action = "BLOCKER", "Resolve convergence credibility before comparison; do not retrain without approval."
        elif category in {"FutureWarning", "DeprecationWarning", "PendingDeprecationWarning"}:
            severity, action = "INFO", "Compatibility notice; preserve it and review the affected API."
        elif category == "InconsistentVersionWarning":
            severity, action = "BLOCKER", "Use the supported saved-library environment before model reuse."
        elif category == "UndefinedMetricWarning":
            action = "Review support/unpredicted classes and zero_division; do not suppress meaningful warnings."
        rows.append({"step": stage, "category": category, "message": message,
                     "occurrences": count, "severity": severity, "recommended_response": action})
    return {"status": "PASS" if prefix else "REVIEW", "recorded_total": len(all_messages),
            "fit_prefix_matches": prefix, "rows": rows,
            "limitation": "Only saved fit/predict capture; serialization/metrics/reporting warnings may be absent."}


def choose_experiment(root, names, requested=None):
    folder = root / "artifacts/models/phase3"
    if requested:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", requested):
            raise ValueError("experiment_id must be one folder name")
        result = folder / requested
        if not result.is_dir():
            raise FileNotFoundError(f"Missing experiment: {result}")
        return result
    choices = sorted(p for p in folder.iterdir() if p.is_dir() and any((p / n / "fit.json").is_file() for n in names)) if folder.is_dir() else []
    if len(choices) != 1:
        raise ValueError(f"Set experiment_id explicitly; candidates={[p.name for p in choices]}")
    return choices[0]


def audit_phase3(session, *, experiment_id=None, compare_reloaded=True):
    """Inspect trusted project checkpoints only. Returns JSON-safe evidence; writes no report."""
    with read_only_audit(session.paths.storage_root) as guards:
        result = _audit(session, experiment_id, compare_reloaded)
        result["guards"] = dict(guards)
    if any(guards[k] for k in ("model_or_feature_fit_attempts", "test_payload_open_attempts", "persistent_write_attempts")):
        result["readiness"] = "BLOCKER"
    return result


def _audit(session, requested, compare_reloaded):
    import numpy as np
    import pandas as pd
    import psutil
    from sklearn import config_context
    from sklearn.metrics import precision_recall_fscore_support
    from sklearn.utils.validation import check_is_fitted
    from threadpoolctl import threadpool_limits
    from src.data.integrity import META, read_baseline, verify_training_inputs
    from src.data.loader import sha256_file
    from src.data.paths import OutputPaths
    from src.models.runtime import MODEL_NAMES, cache_training_inputs, load_training_data
    from src.models.training import (build_pipeline, experiment_identity, json_bytes, load_fitted_checkpoint,
                                     read_completed_checkpoint, validation_metrics, _predict, to_csr)

    root, source = Path(session.paths.storage_root), Path(session.paths.project_root)
    output = OutputPaths(root)
    baseline = read_baseline(source / "configs/phase2_integrity.json")
    inputs = verify_training_inputs(output, baseline=baseline)
    current = experiment_identity(source, session.config, inputs)
    if any(inputs["manifest"]["processed"].get(k) != v for k, v in session.config["expected_phase2"].items()):
        raise ValueError("Phase 2 differs from the approved Phase 3 config")
    preferred = requested or (session.identity or {}).get("experiment_id")
    run = choose_experiment(root, MODEL_NAMES, preferred)
    cached = cache_training_inputs(output, Path(session.paths.cache_dir), inputs)
    data = load_training_data(cached, inputs)
    x_train, _, _ = data["train"]
    x_val, y, groups = data["validation"]
    features, classes = inputs["schema"]["features"], inputs["labels"]["classes"]
    counts = x_train.to_numpy().sum(axis=0, dtype=np.uint64)
    expected_mask = (counts > 0) & (counts < len(x_train))
    probability = counts / len(x_train)
    expected_variance = probability * (1 - probability)
    support = np.bincount(y, minlength=len(classes))
    result = {"audit_version": 1, "experiment_id": run.name, "storage_root": str(root),
              "execution_environment": {"runtime": session.paths.runtime, "platform": platform.system(), **current["versions"]},
              "phase2": {"status": "PASS", "manifest_sha256": inputs["manifest_sha256"],
                         "processed": inputs["manifest"]["processed"], "n_train": len(x_train), "n_validation": len(y),
                         "variable_train_features": int(expected_mask.sum()), "fit_performed": False},
              "support": {"minimum": int(support.min()), "median": float(np.median(support)), "maximum": int(support.max()),
                          "classes_eq_1": int((support == 1).sum()), "classes_le_2": int((support <= 2).sum()),
                          "classes_le_5": int((support <= 5).sum())}, "models": {}, "findings": []}

    def finding(severity, message, model=None):
        result["findings"].append({"severity": severity, "model": model, "message": message})

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def close_metrics(a, b):
        return set(a) == set(b) and all(np.isfinite(float(a[k])) and np.isfinite(float(b[k]))
                                       and np.isclose(a[k], b[k], rtol=RTOL, atol=ATOL) for k in a)

    if (support <= 5).any():
        finding("REVIEW", f"Validation has {int((support == 1).sum())} classes with support 1 and {int((support <= 5).sum())} with support <=5; per-class scores are unstable.")
    masks = []
    common_identity = None
    for name in MODEL_NAMES:
        print(f"AUDIT {name}: saved metadata/checksums", flush=True)
        folder = run / name
        record = {"checkpoint_dir": str(folder), "status": "NOT VERIFIED", "files": {}, "reload": "NOT VERIFIED"}
        result["models"][name] = record
        pipeline = None
        try:
            for filename in ("pipeline.joblib", "fit.json", "metadata.json", "validation_predictions.npz"):
                path = folder / filename
                record["files"][filename] = {"exists": path.is_file(), "bytes": path.stat().st_size if path.is_file() else None}
            require(all(record["files"][n]["exists"] for n in ("pipeline.joblib", "fit.json", "metadata.json")), "Missing checkpoint/fit/completion metadata")
            fit = json.loads((folder / "fit.json").read_text(encoding="utf-8"))
            metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
            record["warnings"] = warning_rows(fit, metadata)
            record["original_resources"] = {k: metadata.get(k) for k in ("fit_seconds", "prediction_seconds", "sampled_peak_rss_mb", "validation_sampled_peak_rss_mb", "environment", "prediction_batch_size", "n_retained_features")}
            for row in record["warnings"].get("rows", []):
                if row["severity"] != "INFO":
                    finding(row["severity"], row["category"] + ": " + row["message"], name)
            if record["warnings"]["status"] != "PASS":
                finding("REVIEW", "Warning records or fit/predict stage attribution are incomplete", name)
            identity = fit["identity"]
            require(fit["status"] == "fitted" and metadata["status"] == "completed"
                    and fit["model"] == metadata["model"] == name, "Wrong checkpoint status/model")
            for key in ("pipeline_sha256", "fit_seconds", "n_input_features", "n_retained_features", "parameters", "environment", "sampled_peak_rss_mb"):
                require(fit[key] == metadata[key], "Fit/completion metadata differ: " + key)
            require(fit["n_input_features"] == len(features) and fit["variance_threshold"] == metadata["variance_threshold"] == 0, "Wrong input/preprocessing policy")
            for filename, expected_sha in (("pipeline.joblib", fit["pipeline_sha256"]),
                                           ("fit.json", metadata["fit_metadata_sha256"])):
                actual_sha = sha256_file(folder / filename)
                record["files"][filename].update(sha256=actual_sha, expected_sha256=expected_sha)
                require(actual_sha == expected_sha, "Checkpoint checksum mismatch: " + filename)
            record["files"]["metadata.json"]["sha256"] = sha256_file(folder / "metadata.json")
            require(metadata["identity"] == identity and identity["experiment_id"] == run.name, "Experiment identity mismatch")
            digest_identity = {k: v for k, v in identity.items() if k != "experiment_id"}
            require(identity["experiment_id"] == identity["config"]["run_tag"] + "-" + hashlib.sha256(json_bytes(digest_identity)).hexdigest()[:16], "Invalid experiment ID digest")
            if common_identity is None:
                common_identity = identity
            require(identity == common_identity, "Models do not share one experiment identity")
            require(identity["config"] == session.config, "Saved config differs from current Phase 3 config")
            for key in ("processed_fingerprint", "training_data_fingerprint", "validation_data_fingerprint", "feature_schema_identity", "label_mapping_identity"):
                require(identity[key] == current[key], "Wrong dataset/schema/mapping: " + key)
            require(identity["phase2_manifest_sha256"] in baseline["approved_manifest_sha256"], "Unapproved original Phase 2 manifest")
            # This strict project reader verifies all checksums, row alignment and stored metrics.
            persisted = None
            if record["files"]["validation_predictions.npz"]["exists"]:
                verified, persisted = read_completed_checkpoint(folder, identity, y, groups)
                require(verified["metrics"] == metadata["metrics"], "Changed completion metadata")
                record["saved_predictions_integrity"] = "PASS"
                record["files"]["validation_predictions.npz"].update(sha256=metadata["predictions_sha256"],
                                                                      expected_sha256=metadata["predictions_sha256"])
            else:
                record["saved_predictions_integrity"] = "NOT VERIFIED: payload missing"
                finding("REVIEW", "Missing saved predictions; validation-only inference may recover metrics without writing a new payload", name)

            differences = {k: {"saved": identity["versions"].get(k), "current": v} for k, v in current["versions"].items() if identity["versions"].get(k) != v}
            changed_source = [n for n, digest in identity["source_sha256"].items() if not (source / n).is_file() or sha256_file(source / n) != digest]
            record["reload_environment_differences"], record["source_differences"] = differences, changed_source
            reload_ok = not differences and not changed_source
            if not reload_ok:
                finding("REVIEW", "Reload not attempted: source/library versions differ from the saved environment", name)
            elif psutil.virtual_memory().available / 2**30 < session.config["resources"]["min_available_ram_gb"]:
                reload_ok = False
                finding("REVIEW", "Reload not attempted: insufficient available RAM", name)
            if reload_ok:
                print(f"AUDIT {name}: load trusted project checkpoint", flush=True)
                with warnings.catch_warnings(record=True) as new_warnings:
                    warnings.simplefilter("always")
                    pipeline = load_fitted_checkpoint(folder, identity, trusted=True)
                    expected = build_pipeline(name, session.config)
                    require([k for k, _ in pipeline.steps] == [k for k, _ in expected.steps], "Unexpected preprocessing steps")
                    for (key, step), (_, reference) in zip(pipeline.steps, expected.steps):
                        require(type(step) is type(reference), "Wrong pipeline class")
                        observed, approved = step.get_params(deep=False), reference.get_params(deep=False)
                        if key == "estimator":
                            require(observed == fit["parameters"], "Estimator parameters differ from saved fit metadata")
                            # RF n_jobs was capped by the CPU count of the original VM.
                            # A smaller original CPU does not change the learned classifier.
                            observed, approved = dict(observed), dict(approved)
                            observed.pop("n_jobs", None)
                            approved.pop("n_jobs", None)
                        require(observed == approved, "Wrong pipeline parameters")
                    variance, estimator = pipeline.named_steps["variance"], pipeline.named_steps["estimator"]
                    check_is_fitted(variance)
                    check_is_fitted(estimator)
                    require(pipeline.n_features_in_ == len(features) and list(variance.feature_names_in_) == features, "Wrong feature count/order")
                    require(np.array_equal(pipeline.classes_, np.arange(len(classes))), "Wrong classifier label mapping")
                    require(pipeline.named_steps["csr"].func is to_csr, "Unexpected custom transformer function")
                    mask = variance.get_support()
                    require(np.array_equal(mask, expected_mask) and np.allclose(variance.variances_, expected_variance, rtol=RTOL, atol=ATOL), "Fitted mask/variances differ from train")
                    require(int(mask.sum()) == fit["n_retained_features"] == metadata["n_retained_features"] == 318, "Retained feature count mismatch")
                    require(estimator.n_features_in_ == int(mask.sum()), "Estimator input dimension mismatch")
                    record["feature_pipeline"] = {"status": "PASS", "input_features": len(features), "retained_features": int(mask.sum()),
                                                  "mask_sha256": hashlib.sha256(mask.astype(np.uint8).tobytes()).hexdigest(),
                                                  "provenance_limit": "Variances match train; this is not proof of unobserved notebook execution history."}
                    masks.append(record["feature_pipeline"]["mask_sha256"])
                    record["reload"] = "PASS"
                    if compare_reloaded or persisted is None:
                        print(f"AUDIT {name}: validation-only prediction comparison; no benchmark/fit", flush=True)
                        resources = session.config["resources"]
                        with threadpool_limits(limits=resources["blas_threads"]), config_context(working_memory=resources["working_memory_mb"]):
                            predicted, _ = _predict(pipeline, x_val, resources["prediction_batch_size"], print)
                        if persisted is not None:
                            record["reloaded_predictions_match"] = bool(np.array_equal(predicted, persisted))
                            record["prediction_mismatches"] = int((predicted != persisted).sum())
                            require(record["reloaded_predictions_match"], "Reloaded predictions differ from saved validation predictions")
                        else:
                            persisted = predicted
                            record["reloaded_predictions_match"] = "NOT VERIFIED: no historical predictions"
                record["audit_reload_warnings"] = [{"category": w.category.__name__, "message": str(w.message)} for w in new_warnings]
                if new_warnings:
                    finding("REVIEW", "New reload/inference warnings were recorded separately from original training warnings", name)
            if persisted is not None:
                scores = validation_metrics(y, persisted, len(classes))
                require(close_metrics(scores, metadata["metrics"]), "Metrics do not match validation predictions")
                record["metrics"], record["metrics_verified"] = scores, "PASS"
                _, _, f1, _ = precision_recall_fscore_support(y, persisted, labels=np.arange(len(classes)), zero_division=0)
                predicted_counts = np.bincount(persisted, minlength=len(classes))
                worst = np.argsort(f1, kind="stable")[:12]
                record["per_class"] = {"predicted_classes": int((predicted_counts > 0).sum()), "never_predicted_classes": int((predicted_counts == 0).sum()),
                                       "classes_f1_zero": int((f1 == 0).sum()), "weighted_minus_macro_f1": scores["weighted_f1"] - scores["macro_f1"],
                                       "lowest_f1_examples": [{"disease": classes[i], "support": int(support[i]), "f1": float(f1[i])} for i in worst]}
                ref = REFERENCE[name]
                values = [scores["accuracy"], scores["macro_f1"], scores["weighted_f1"], metadata["fit_seconds"], metadata["prediction_seconds"]]
                record["reference_rounded_matches"] = {key: bool(abs(float(actual) - wanted) <= 5e-6 + ATOL) for key, actual, wanted in zip(("accuracy", "macro_f1", "weighted_f1", "fit_seconds", "prediction_seconds"), values, ref)}
                record["reference_warning_count_matches"] = record["warnings"].get("recorded_total") == ref[5]
                if not all(record["reference_rounded_matches"].values()) or not record["reference_warning_count_matches"]:
                    finding("REVIEW", "Saved results differ from the user reference table; historical values were not replaced", name)
            record["status"] = "PASS" if record.get("metrics_verified") == "PASS" and record["reload"] == "PASS" and record.get("reloaded_predictions_match") is True else "NOT VERIFIED"
        except Exception as exc:
            record["status"], record["error"] = "BLOCKER", f"{type(exc).__name__}: {exc}"
            finding("BLOCKER", record["error"], name)
        finally:
            del pipeline
            gc.collect()

    result["feature_masks_identical"] = "PASS" if len(masks) == len(MODEL_NAMES) and len(set(masks)) == 1 else "NOT VERIFIED"
    summary_path = root / "artifacts/metadata/phase3" / run.name / "run_summary.json"
    comparison_path = root / "reports/tables" / f"phase3_{run.name}_validation_comparison.csv"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        require(summary["identity"] == common_identity, "Run summary identity differs")
        require(sha256_file(comparison_path) == summary["comparison_sha256"], "Comparison CSV checksum mismatch")
        table = pd.read_csv(comparison_path)
        require(set(table["model"]) == set(MODEL_NAMES) and len(table) == len(MODEL_NAMES), "Comparison model inventory differs")
        require(len(summary["models"]) == len(MODEL_NAMES) and {m["model"] for m in summary["models"]} == set(MODEL_NAMES), "Run summary model inventory differs")
        for name in MODEL_NAMES:
            model = result["models"][name]
            require(model.get("metrics_verified") == "PASS", "Missing verified metrics for comparison: " + name)
            csv_row = table.loc[table["model"].eq(name)].iloc[0]
            require(close_metrics(model["metrics"], {k: csv_row[k] for k in model["metrics"]}), "Comparison CSV metrics differ: " + name)
            for key in ("fit_seconds", "prediction_seconds", "n_retained_features", "sampled_peak_rss_mb"):
                require(np.isclose(csv_row[key], model["original_resources"][key], rtol=RTOL, atol=ATOL), "Comparison CSV resource/feature value differs: " + name + "/" + key)
            require(int(csv_row["warnings"]) == model["warnings"].get("recorded_total"), "Comparison CSV warning count differs: " + name)
            handoff = next(m for m in summary["models"] if m["model"] == name)
            require(close_metrics(model["metrics"], handoff["metrics"]), "Run summary metrics differ: " + name)
        result["comparison_csv_and_summary"] = "PASS"
        result["saved_phase4_ready_flag"] = summary.get("phase4_ready")
        result["existing_figures"] = []
        for figure in summary.get("figures", []):
            path = Path(figure["path"])
            valid = path.resolve().is_relative_to(root.resolve()) and path.is_file() and sha256_file(path) == figure["sha256"]
            result["existing_figures"].append({"name": figure["name"], "path": str(path), "checksum": "PASS" if valid else "NOT VERIFIED"})
            if not valid:
                finding("REVIEW", "Existing figure missing or checksum mismatch: " + figure["name"])
    except Exception as exc:
        result["comparison_csv_and_summary"] = f"NOT VERIFIED: {type(exc).__name__}: {exc}"
        finding("REVIEW" if isinstance(exc, FileNotFoundError) else "BLOCKER", result["comparison_csv_and_summary"])
    if any(f["severity"] == "BLOCKER" for f in result["findings"]):
        result["readiness"] = "BLOCKER"
    elif any(m["status"] != "PASS" for m in result["models"].values()):
        result["readiness"] = "NOT VERIFIED"
    else:
        result["readiness"] = "REVIEW" if result["findings"] else "PASS"
    result["no_test_payload_loaded"], result["no_model_fitted"] = True, True
    return result


def emit_packet(result):
    """Compact evidence for Copy Cell Output; never write credentials or Drive files."""
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    print("AUDIT_SHA256=" + hashlib.sha256(raw).hexdigest())
    print("AUDIT_GZIP_BASE64=" + base64.b64encode(gzip.compress(raw, mtime=0)).decode("ascii"))
    print("AUDIT_READINESS=" + result["readiness"])
