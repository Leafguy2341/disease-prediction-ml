"""Read-only diagnostics for one frozen LR-vs-hard comparison, not inference serving.

Use the existing Colab session and scripts/audit_post_tuning.py API. No bootstrap,
cache, file export, cleanup, fit, calibration, network or application-model change.
Results are emitted in memory; actual artifacts remain on Drive.
"""
from __future__ import annotations

from collections import Counter
import base64
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
import warnings

import numpy as np
import psutil
from sklearn import config_context
from threadpoolctl import threadpool_limits

from src.data.integrity import read_baseline, verify_training_inputs
from src.data.loader import sha256_file
from src.data.paths import OutputPaths
from src.models.ensemble import (HARD, IntegrityError, class_predictions, hard_vote,
                                 require, validate_probabilities)
from src.models.runtime import load_training_data, runtime_snapshot
from src.models.training import (build_pipeline, json_bytes, load_fitted_checkpoint,
                                 read_completed_checkpoint, sampled_memory)
from src.models.tuning import _paths, read_tuning_result

EXPERIMENT = "tuning-v1-9c4dd013abbba14a"
ENSEMBLE_RUN = "tuned-ensemble-20261029T041701354242Z-6c84dbfe"
TUNING_SHA = "4a10ddd5deba5fff7927f84ea334196a3f6d127b9777ced2b127f5b5e9389355"
ENSEMBLE_SHA = "858893c442f1966eb8c7508a74cf6318b820004278342a1b958942151c049060"
MEMBERS = HARD["hard_lr_svc_knn"]
BOOTSTRAP_PLAN = {
    "seed": 20261029, "replicates": 2000, "classes": 587,
    "metric": "Macro F1; labels=0..586; zero_division=0",
    "sampling": "G groups uniformly with replacement; all rows of a group share its multiplicity; paired candidates",
    "interval": "percentile 2.5/97.5; numpy quantile method=linear",
    "selection": "frozen LR tuned vs hard_lr_svc_knn; no further search",
}
BENCHMARK_PLAN = {
    "panel_seed": 20261029, "distinct_groups": 64, "rounds": 3,
    "warmup_calls_per_operation": 3, "batch_size": 1,
    "condition_order": ["lr_tuned", "hard_lr_svc_knn"],
    "blas_threads": 1, "working_memory_mb": 128,
    "ram_sampling_seconds": 0.5,
    "load": "fresh objects per condition after integrity reads; OS/Drive cache not cold",
}


def weighted_scores(y, prediction, weights, n_classes):
    """Exact class-count equivalent of fixed-label F1(sample_weight=weights)."""
    y = class_predictions(y, len(y), n_classes)
    prediction = class_predictions(prediction, len(y), n_classes)
    weights = np.asarray(weights, dtype=np.float64)
    require(weights.shape == y.shape and np.isfinite(weights).all()
            and (weights >= 0).all() and weights.sum() > 0, "Invalid bootstrap multiplicities.")
    support = np.bincount(y, weights=weights, minlength=n_classes)
    predicted = np.bincount(prediction, weights=weights, minlength=n_classes)
    correct = prediction == y
    tp = np.bincount(y[correct], weights=weights[correct], minlength=n_classes)
    f1 = np.divide(2 * tp, support + predicted, out=np.zeros(n_classes), where=(support + predicted) > 0)
    return float(f1.mean()), float(weights[correct].sum() / weights.sum()), support == 0


def paired_group_bootstrap(y, lr, hard, groups, *, seed=20261029, replicates=2000, n_classes=587):
    """Only saved predictions; no estimator is passed to this function."""
    y, groups = np.asarray(y), np.asarray(groups)
    require(y.ndim == groups.ndim == 1 and len(y) == len(groups) and len(y) > 0,
            "Groups/predictions must have identical row alignment.")
    require(isinstance(replicates, int) and replicates >= 2, "Need >=2 bootstrap replicates.")
    _, inverse = np.unique(groups, return_inverse=True)
    g = int(inverse.max()) + 1
    rng = np.random.default_rng(seed)
    differences = np.empty((replicates, 2)); missing = np.empty(replicates, dtype=int)
    absent_frequency = np.zeros(n_classes, dtype=int)
    observed = [weighted_scores(y, p, np.ones(len(y)), n_classes)[:2] for p in (lr, hard)]
    for b in range(replicates):
        multiplicity = np.bincount(rng.integers(0, g, size=g), minlength=g)
        weights = multiplicity[inverse]
        left, right = (weighted_scores(y, p, weights, n_classes) for p in (lr, hard))
        differences[b] = np.asarray(right[:2]) - np.asarray(left[:2])
        require(np.array_equal(left[2], right[2]), "Paired sample mismatch.")
        missing[b] = int(left[2].sum()); absent_frequency += left[2]
    result = {"seed": seed, "replicates": replicates, "groups": g,
              "n_rows": len(y), "n_classes": n_classes, "observed_lr": observed[0], "observed_hard": observed[1]}
    for i, metric in enumerate(("macro_f1", "accuracy")):
        result[metric] = {"observed_delta_hard_minus_lr": observed[1][i] - observed[0][i],
            "bootstrap_mean_delta": float(differences[:, i].mean()),
            "percentile95": np.quantile(differences[:, i], [.025, .975], method="linear").tolist(),
            "fraction_positive_not_p_value": float((differences[:, i] > 0).mean())}
    result["missing_classes"] = {"quantiles_min_p05_p50_p95_max": np.quantile(missing, [0, .05, .5, .95, 1]).tolist(),
        "replicates_with_any_missing": int((missing > 0).sum()),
        "absent_replicates_per_class_id": absent_frequency.tolist()}
    result["limits"] = "Conditional descriptive cluster bootstrap, not a p-value/posterior, final-test estimate or clinical validation. Rare-class F1 is discontinuous; absent classes stay in denominator587; repeated validation selection bias remains."
    return result


def panel_indices(groups, count=64, seed=20261029):
    """Select groups without labels/predictions; one first row per sampled group."""
    groups = np.asarray(groups)
    require(groups.ndim == 1 and len(groups) > 0, "Invalid validation groups.")
    _, first = np.unique(groups, return_index=True)
    require(len(first) >= count, "Too few independent groups for the frozen benchmark panel.")
    return first[np.random.default_rng(seed).choice(len(first), size=count, replace=False)]


def latency_summary(seconds):
    values = np.asarray(seconds, dtype=float)
    require(values.size > 0 and np.isfinite(values).all() and (values >= 0).all(), "Invalid timings.")
    return {"calls": int(values.size), "p50_ms": float(np.quantile(values, .5) * 1000),
            "p95_ms": float(np.quantile(values, .95) * 1000), "min_ms": float(values.min() * 1000),
            "max_ms": float(values.max() * 1000)}


def benchmark_condition(name, folder, identity, frames, features, classes, variable_mask):
    """Use existing checkpoint loader and hard_vote; no new serving abstraction."""
    members = ("logistic_regression",) if name == "lr_tuned" else MEMBERS
    require(name in BENCHMARK_PLAN["condition_order"], "Unapproved benchmark condition.")
    process = psutil.Process(); models = {}; loads = {}; warmups = {}; timings = {}; examples = {}
    gc.collect(); rss_before = process.memory_info().rss / 2**20
    with sampled_memory(stage=name) as memory:
        try:
            for member in members:
                require(psutil.virtual_memory().available / 2**30 >= 2, "Insufficient RAM before checkpoint load.")
                started = time.perf_counter()
                model = load_fitted_checkpoint(folder / member, identity, trusted=True)
                models[member] = model
                reference = build_pipeline(member, identity["config"])
                require(model.feature_names_in_.tolist() == features
                        and np.array_equal(model.classes_, np.arange(len(classes)))
                        and np.array_equal(model.named_steps["variance"].get_support(), variable_mask), "Reload ordering/mask mismatch.")
                require([n for n, _ in model.steps] == [n for n, _ in reference.steps]
                        and all(type(x) is type(z) and x.get_params(deep=False) == z.get_params(deep=False)
                                for (_, x), (_, z) in zip(model.steps, reference.steps)), "Reload parameters mismatch.")
                loads[member] = time.perf_counter() - started
                del model, reference

            def top1(frame):
                predictions = {m: models[m].predict(frame) for m in members}
                return predictions[members[0]] if len(members) == 1 else hard_vote(predictions, members, len(classes))[0]

            def top3(frame):
                probability = models["logistic_regression"].predict_proba(frame)
                return probability, np.argsort(-probability[0], kind="stable")[:3]

            operations = {"predict_top1": top1}
            if name == "lr_tuned":
                operations["predict_proba_and_top3"] = top3
            for operation, call in operations.items():
                warmups[operation] = []
                for _ in range(BENCHMARK_PLAN["warmup_calls_per_operation"]):
                    start = time.perf_counter(); call(frames[0]); warmups[operation].append(time.perf_counter() - start)
                elapsed = []
                for _ in range(BENCHMARK_PLAN["rounds"]):
                    for frame in frames:
                        start = time.perf_counter(); value = call(frame); elapsed.append(time.perf_counter() - start)
                        if operation == "predict_top1":
                            class_predictions(value, 1, len(classes))
                        else:
                            validate_probabilities(value[0], 1, models["logistic_regression"].classes_, len(classes))
                timings[operation] = latency_summary(elapsed)
                if operation == "predict_proba_and_top3":
                    probability, order = value
                    examples[operation] = {"row": "last_panel_row", "label_ids": order.tolist(),
                        "model_scores_uncalibrated": probability[0, order].tolist(), "clinical_probability": False}
            rss_loaded = process.memory_info().rss / 2**20
        finally:
            models.clear(); gc.collect()  # RAM references only; never delete files.
    return {"status": "PASS", "member_verified_load_seconds": loads,
        "verified_load_seconds_total": sum(loads.values()), "warmup_seconds": warmups,
        "batch1": timings, "rss_before_mib": rss_before, "rss_after_calls_mib": rss_loaded,
        "sampled_process_and_children_peak_mib": max(memory["sampled_peak_rss_mb"], rss_before, rss_loaded),
        "top3": examples if name == "lr_tuned" else "UNAVAILABLE: hard labels/votes are not calibrated class probabilities; no Top1-hard/Top3-LR hybrid",
        "limits": "Single process, fixed LR-then-hard order, allocator/cache effects, sampled RSS every0.5s can miss peaks. Timed transform/predict/vote; validation checks outside timer; no API/concurrency/LLM/network or SLA. Data resident in RAM; verified load is not cold Drive startup."}


def inventory_drive(root):
    """Metadata-only inventory: stat sizes; never open any payload, including test."""
    root = Path(root).resolve(); groups = {}; largest = []; total = 0; count = 0; skipped = []; errors = []
    require(root.is_dir(), "Missing canonical Drive directory.")
    for folder, dirs, names in os.walk(root, followlinks=False):
        for directory in list(dirs):
            path = Path(folder) / directory
            if path.is_symlink():
                skipped.append(path.relative_to(root).as_posix())
        dirs[:] = [d for d in dirs if not (Path(folder) / d).is_symlink()]
        for name in names:
            path = Path(folder) / name
            if path.is_symlink():
                skipped.append(path.relative_to(root).as_posix()); continue
            relative = path.relative_to(root).as_posix()
            try:
                size = path.stat().st_size
            except OSError as exc:
                errors.append({"path": relative, "error": type(exc).__name__}); continue
            group = relative.split("/", 1)[0]
            row = groups.setdefault(group, {"files": 0, "bytes": 0}); row["files"] += 1; row["bytes"] += size
            total += size; count += 1; largest.append({"path": relative, "bytes": size})
            largest = sorted(largest, key=lambda r: -r["bytes"])[:20]
    return {"root": str(root), "files": count, "bytes": total, "groups": groups, "largest": largest,
            "symlinks_skipped": skipped, "errors": errors, "content_checksums": "NOT VERIFIED by stat inventory; separate ML manifest checks below", "test_payload_opened": False}


def run_final_ml_gaps(session, *, audit_api, benchmark=False, trusted=False):
    """Call explicitly on Colab; no Stage A/B setup or session.load_data/cache writes."""
    root, source = session.paths.storage_root.resolve(), session.paths.project_root.resolve()
    with audit_api["read_only"](root) as guards:
        try:
            start = time.perf_counter(); print("GAPS: checking pinned manifests and train/validation inputs", flush=True)
            result = read_tuning_result(root, EXPERIMENT); meta, models, _ = _paths(root, EXPERIMENT)
            require(sha256_file(meta / "manifest.json") == TUNING_SHA, "Different tuning manifest; stop, no auto-selection.")
            inputs = verify_training_inputs(OutputPaths(root), baseline=read_baseline(source / "configs/phase2_integrity.json"))
            data = load_training_data(OutputPaths(root), inputs)  # Existing loader; only train/validation, no copies.
            x, y, groups = data["validation"]; features, classes = inputs["schema"]["features"], inputs["labels"]["classes"]
            require(len(features) == 375 and len(classes) == 587, "Unexpected locked schema.")
            current = audit_api["_check_identity"](result["identity"], result["identity"]["config"], inputs, source)
            predictions = {m: read_completed_checkpoint(models / m, result["identity"], y, groups)[1]
                           for m in result["identity"]["config"]["models"]}
            # Reuse the existing audit to recheck the ensemble manifest, four checksums and hard-vote/tie policy.
            ensemble = audit_api["_ensemble"](root, result, predictions, y, groups, classes, ensemble_run_id=ENSEMBLE_RUN)
            require(ensemble["status"] == "PASS" and ensemble["manifest_sha256"] == ENSEMBLE_SHA, "Ensemble provenance mismatch.")
            hard = hard_vote(predictions, MEMBERS, len(classes))[0]
            integrity_seconds = time.perf_counter() - start
            print("GAPS: paired group bootstrap; frozen seed20261029 / B2000", flush=True)
            bootstrap = paired_group_bootstrap(y, predictions["logistic_regression"], hard, groups,
                seed=BOOTSTRAP_PLAN["seed"], replicates=BOOTSTRAP_PLAN["replicates"], n_classes=BOOTSTRAP_PLAN["classes"])
            bootstrap["missing_classes"]["class_names_by_id"] = classes
            measured = {"status": "NOT RUN", "reason": "benchmark=False"}
            if benchmark:
                changed = [n for n, h in result["identity"]["source_sha256"].items()
                           if not (source / n).is_file() or sha256_file(source / n) != h]
                if not trusted or result["identity"]["versions"] != current["versions"] or changed:
                    measured = {"status": "NOT VERIFIED", "reason": "Untrusted checkpoint, changed pinned source or incompatible versions; bootstrap retained, no model load/predict.",
                                "changed_sources": changed, "saved_versions": result["identity"]["versions"], "current_versions": current["versions"]}
                    benchmark = False
            if benchmark:
                panel = panel_indices(groups); frames = [x.iloc[[int(i)]] for i in panel]
                train_x = data["train"][0]; mask = train_x.max(axis=0).to_numpy() != train_x.min(axis=0).to_numpy()
                with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=1), config_context(working_memory=128):
                    warnings.simplefilter("always")
                    measured = {"status": "PASS", "rows_0based": panel.tolist(), "group_ids": groups[panel].tolist(),
                                "feature_count": len(features), "conditions": {}}
                    for name in BENCHMARK_PLAN["condition_order"]:
                        print("GAPS: benchmark " + name + " (no fit)", flush=True)
                        measured["conditions"][name] = benchmark_condition(name, models, result["identity"], frames, features, classes, mask)
                measured["warnings_by_category"] = dict(Counter(w.category.__name__ for w in caught))
            return {"status": "REVIEW", "selection_status": "MODEL SELECTION PENDING",
                "experiment_id": EXPERIMENT, "ensemble_run_id": ENSEMBLE_RUN,
                "tuning_manifest_sha256": TUNING_SHA, "ensemble_manifest_sha256": ENSEMBLE_SHA,
                "script_sha256": sha256_file(Path(__file__)), "environment": runtime_snapshot(),
                "bootstrap_plan": BOOTSTRAP_PLAN, "benchmark_plan": BENCHMARK_PLAN,
                "integrity_seconds": integrity_seconds, "bootstrap": bootstrap, "benchmark": measured,
                "drive_inventory": inventory_drive(root), "guards": guards,
                "models_fitted": 0, "test_payload_opened": False, "persistent_files_written": 0,
                "prediction_called": bool(benchmark), "default_changed": False}
        except (FileNotFoundError, MemoryError, OSError) as exc:
            return {"status": "NOT VERIFIED", "reason": str(exc), "guards": guards}
        except (IntegrityError, ValueError, KeyError, TypeError) as exc:
            return {"status": "BLOCKER", "reason": str(exc), "guards": guards}


def emit_packet(result):
    payload = json_bytes(result)
    print("ML_GAPS_SHA256=" + hashlib.sha256(payload).hexdigest())
    print("ML_GAPS_GZIP_BASE64=" + base64.b64encode(gzip.compress(payload, mtime=0)).decode())
    print("ML_GAPS_STATUS=" + result["status"])
