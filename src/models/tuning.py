"""Opt-in, train-only grouped CV. Baseline files and the locked test stay untouched."""
from __future__ import annotations

from copy import deepcopy
import gc
import hashlib
import io
import json
from pathlib import Path
import re
import time
import warnings

import numpy as np
import pandas as pd
import psutil
from sklearn import config_context
from sklearn.model_selection import StratifiedGroupKFold
from threadpoolctl import threadpool_limits

from src.data.loader import sha256_file
from src.models.ensemble import Phase4, require
from src.models.runtime import MODEL_NAMES
from src.models.training import (atomic_bytes, build_pipeline, experiment_identity,
                                 json_bytes, read_completed_checkpoint, run_model,
                                 sampled_memory, validation_metrics, _predict)

# Declared before observing CV/validation. Other baseline parameters stay fixed.
SEARCH = {
    "logistic_regression": ("C", (1.0, 0.5, 2.0)),
    "random_forest": ("max_depth", (24, 16, 32)),
    "linear_svc": ("C", (1.0, 0.5, 2.0)),
    "knn": ("n_neighbors", (5, 3, 7)),
    "bernoulli_nb": ("alpha", (1.0, 0.5, 2.0)),
}
SOURCE_FILES = ("src/models/tuning.py", "src/models/tuned_ensemble.py")
SCORING = "mean fold macro_f1 over ALL saved class IDs; absent classes F1=0; zero_division=0"


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def search_plan(config):
    """Small fixed plan; never accepts validation scores or dynamically expands grids."""
    require(tuple(config["models"]) == MODEL_NAMES and config["seed"] == 42, "Sai baseline config/seed.")
    resources = deepcopy(config["resources"])
    for key, cap in (("max_workers", 2), ("blas_threads", 1),
                     ("working_memory_mb", 128), ("prediction_batch_size", 64)):
        resources[key] = min(resources[key], cap)
        require(resources[key] > 0, "Giới hạn tài nguyên phải dương.")
    resources["min_available_ram_gb"] = max(2.0, resources["min_available_ram_gb"])
    candidates = {}
    for name, (parameter, values) in SEARCH.items():
        baseline = deepcopy(config["models"][name])
        # Baseline first also defines the stable tie-break. Avoid duplicate candidates.
        candidates[name] = [baseline]
        for value in values:
            candidate = {**baseline, parameter: value}
            if candidate not in candidates[name]:
                candidates[name].append(candidate)
        require(len(candidates[name]) <= 4, "Không mở rộng search vượt giới hạn cố định.")
    return {"version": 1, "seed": 42, "folds": 3, "splitter": "StratifiedGroupKFold",
            "shuffle": True, "scoring": SCORING, "candidates": candidates,
            "resources": resources, "max_search_seconds_per_invocation": 21600,
            "selection": "highest mean completed-fold macro_f1; exact ties -> earlier candidate (baseline first)"}


def plan_table(config):
    plan = search_plan(config)
    return pd.DataFrame([{"model": name, "candidate": i, "baseline": i == 0,
                          "parameters": json.dumps(params, sort_keys=True)}
                         for name, items in plan["candidates"].items() for i, params in enumerate(items)])


def grouped_folds(y, groups, n_classes, plan):
    """Only train labels/groups enter this function; persist row-to-fold assignment."""
    y, groups = np.asarray(y), np.asarray(groups)
    require(y.ndim == groups.ndim == 1 and len(y) == len(groups), "Train group/label alignment sai.")
    require(set(y.tolist()) == set(range(n_classes)), "Train không phủ saved label mapping.")
    n_groups = len(set(groups.tolist()))
    require(n_groups >= plan["folds"], "Không đủ group cho CV.")
    # SGKF constructs a dense group × class count matrix (117k × 587 here).
    # Reserve two such matrices plus the baseline free-RAM floor; not a peak-RSS guarantee.
    required_gib = plan["resources"]["min_available_ram_gb"] + 2 * n_groups * n_classes * 8 / 2**30
    if psutil.virtual_memory().available / 2**30 < required_gib:
        raise MemoryError(f"Grouped CV cần RAM khả dụng ít nhất {required_gib:.2f} GiB trước allocation; chọn runtime nhiều RAM hơn.")
    cv = StratifiedGroupKFold(n_splits=plan["folds"], shuffle=plan["shuffle"], random_state=plan["seed"])
    assignment = np.full(len(y), -1, dtype=np.int8)
    inventory, folds = [], []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for index, (train, holdout) in enumerate(cv.split(np.zeros((len(y), 1), dtype=np.uint8), y, groups)):
            require(len(train) > 0 and len(holdout) > 0, "CV tạo fold rỗng.")
            require(not set(groups[train].tolist()) & set(groups[holdout].tolist()), "CV group leakage.")
            require((assignment[holdout] == -1).all(), "CV holdout row bị lặp.")
            assignment[holdout] = index
            inventory.append({"fold": index, "train_rows": len(train), "holdout_rows": len(holdout),
                "train_groups": len(set(groups[train].tolist())), "holdout_groups": len(set(groups[holdout].tolist())),
                "missing_train_classes": sorted(set(range(n_classes)) - set(y[train].tolist())),
                "missing_holdout_classes": sorted(set(range(n_classes)) - set(y[holdout].tolist()))})
            folds.append((train, holdout))
    require((assignment >= 0).all(), "CV chưa phủ mọi train row.")
    return folds, assignment, inventory, [f"{w.category.__name__}: {w.message}" for w in caught]


def _fold_score(name, params, config, train, holdout, n_classes, progress):
    """A fresh complete pipeline for EVERY fold; no validation data or prefit variance."""
    resource = config["resources"]
    if psutil.virtual_memory().available / 2**30 < resource["min_available_ram_gb"]:
        raise MemoryError("RAM khả dụng dưới giới hạn; không bắt đầu fold.")
    candidate_config = deepcopy(config)
    candidate_config["models"][name] = params
    pipeline = build_pipeline(name, candidate_config)
    try:
        with threadpool_limits(limits=resource["blas_threads"]), config_context(working_memory=resource["working_memory_mb"]):
            pipeline.fit(*train)
            prediction, prediction_seconds = _predict(pipeline, holdout[0], resource["prediction_batch_size"], progress)
        return {"macro_f1": validation_metrics(holdout[1], prediction, n_classes)["macro_f1"],
                "prediction_seconds": prediction_seconds}
    finally:
        del pipeline
        gc.collect()


def _read_state(path, experiment):
    if not path.is_file():
        return []
    state = json.loads(path.read_text(encoding="utf-8"))
    require(state["experiment"] == experiment and state["sha256"] == digest(state["trials"]), "CV state checksum/identity sai.")
    return state["trials"]


def _write_state(path, experiment, trials):
    atomic_bytes(path, json_bytes({"experiment": experiment, "trials": trials, "sha256": digest(trials)}))


def search_train_only(train, config, plan, folds, n_classes, state_path, experiment, *, progress=print):
    """Persist tiny scores after every fold. No intermediate fold pipelines are saved."""
    x, y, _ = train
    trials = _read_state(state_path, experiment)
    expected = {(name, i) for name in MODEL_NAMES for i in range(len(plan["candidates"][name]))}
    require(len({(r["model"], r["candidate"]) for r in trials}) == len(trials)
            and {(r["model"], r["candidate"]) for r in trials} <= expected, "CV state có trial thừa/lặp.")
    started = time.perf_counter()
    for name in MODEL_NAMES:
        for candidate, params in enumerate(plan["candidates"][name]):
            record = next((r for r in trials if (r["model"], r["candidate"]) == (name, candidate)), None)
            if record is None:
                record = {"model": name, "candidate": candidate, "parameters": params, "attempts": []}
                trials.append(record)
            require(record["parameters"] == params, "CV state parameters khác plan.")
            for fold, (fit_rows, score_rows) in enumerate(folds):
                attempts = [a for a in record["attempts"] if a["fold"] == fold]
                if attempts and attempts[-1]["status"] in {"completed", "failed"}:
                    continue
                if time.perf_counter() - started >= plan["max_search_seconds_per_invocation"]:
                    _write_state(state_path, experiment, trials)
                    raise TimeoutError("Dừng lên lịch fold sau budget 6 giờ; chạy lại để resume. Không chọn từ search chưa hoàn tất.")
                progress(f"CV {name} | candidate {candidate + 1}/{len(plan['candidates'][name])} {params} | fold {fold + 1}/{len(folds)}")
                tick = time.perf_counter()
                result = {"fold": fold}
                interrupted = None
                with warnings.catch_warnings(record=True) as caught, sampled_memory(progress, f"CV {name}/{candidate}/{fold}") as memory:
                    warnings.simplefilter("always")
                    try:
                        result.update(_fold_score(name, params, config,
                            (x.iloc[fit_rows], np.asarray(y)[fit_rows]),
                            (x.iloc[score_rows], np.asarray(y)[score_rows]), n_classes, progress))
                        require(np.isfinite(result["macro_f1"]) and 0 <= result["macro_f1"] <= 1, "CV score không hợp lệ.")
                        result["status"] = "completed"
                    except KeyboardInterrupt as exc:
                        result = {"fold": fold, "status": "interrupted", "error_type": type(exc).__name__, "error": str(exc)}
                        interrupted = exc
                    except Exception as exc:
                        result = {"fold": fold, "status": "failed", "error_type": type(exc).__name__, "error": str(exc)}
                result.update(elapsed_seconds=time.perf_counter() - tick,
                              warnings=[f"{w.category.__name__}: {w.message}" for w in caught], **memory)
                record["attempts"].append(result)
                _write_state(state_path, experiment, trials)
                progress(f"  {result['status'].upper()} | {result['elapsed_seconds']:.2f}s | F1={result.get('macro_f1', 'NA')} | warnings={len(caught)}")
                if interrupted is not None:
                    raise interrupted
    return trials


def select_configurations(trials, plan):
    """No validation scores are accepted. All three folds must have succeeded."""
    selected = {}
    for name in MODEL_NAMES:
        candidates = []
        for i, params in enumerate(plan["candidates"][name]):
            record = next((r for r in trials if (r["model"], r["candidate"]) == (name, i)), None)
            require(record is not None and record["parameters"] == params, "Search chưa hoàn tất/khác plan.")
            last = {attempt["fold"]: attempt for attempt in record["attempts"]}
            require(set(last) == set(range(plan["folds"]))
                    and all(a["status"] in {"completed", "failed"} for a in last.values()), "Search chưa hoàn tất; không chọn từ kết quả từng phần.")
            if all(a["status"] == "completed" for a in last.values()):
                scores = [last[k]["macro_f1"] for k in range(plan["folds"])]
                require(all(np.isfinite(s) and 0 <= s <= 1 for s in scores), "CV score invalid.")
                candidates.append({"candidate": i, "parameters": params, "fold_scores": scores,
                                   "mean_macro_f1": float(np.mean(scores)), "std_macro_f1": float(np.std(scores))})
        require(candidates, f"{name}: mọi candidate lỗi; dừng, không thay model hoặc threshold.")
        selected[name] = sorted(candidates, key=lambda r: (-r["mean_macro_f1"], r["candidate"]))[0]
    return selected


def _experiment_id(value):
    require(isinstance(value, str) and re.fullmatch(r"tuning-v1-[0-9a-f]{16}", value), "Tuning experiment ID không hợp lệ.")
    return value


def _paths(root, experiment):
    experiment = _experiment_id(experiment)
    return (root / "artifacts/metadata/tuning" / experiment,
            root / "artifacts/models/tuning" / experiment,
            root / "reports/tuning" / experiment)


def _expected_files(experiment):
    meta, models, reports = _paths(Path(), experiment)
    names = [meta / n for n in ("experiment.json", "trials.json", "selection.json", "cv_assignments.npz")]
    names += [models / name / n for name in MODEL_NAMES
              for n in ("pipeline.joblib", "fit.json", "metadata.json", "validation_predictions.npz")]
    names += [reports / "baseline_vs_tuned.csv", reports / "baseline_vs_tuned.png"]
    return {p.as_posix() for p in names}


def read_tuning_result(storage_root, experiment=None):
    """Only complete, checksum-verified manifests; never chooses the best validation run."""
    root = Path(storage_root).resolve()
    if experiment is None:
        manifests = sorted((root / "artifacts/metadata/tuning").glob("tuning-v1-*/manifest.json"))
        if not manifests:
            raise FileNotFoundError("SKIPPED: chưa có tuned checkpoints hoàn tất; bật tuning ở cuối notebook 03 trước.")
        require(len(manifests) == 1, "Có nhiều tuning run; đặt TUNING_EXPERIMENT_ID rõ ràng, không tự chọn theo validation.")
        experiment = manifests[0].parent.name
    meta, _, _ = _paths(root, experiment)
    path = meta / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"SKIPPED: tuned run chưa hoàn tất: {path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    require(result["experiment_id"] == experiment and result["status"] == "completed", "Tuned manifest identity/status sai.")
    require(set(result["files"]) == _expected_files(experiment), "Tuned manifest có file thiếu/thừa/ngoài namespace.")
    for relative, entry in result["files"].items():
        artifact = (root / relative).resolve()
        require(artifact.is_relative_to(root), "Artifact trỏ ngoài storage root.")
        if not artifact.is_file():
            raise FileNotFoundError(f"SKIPPED: tuned artifact chưa có/đồng bộ chưa đủ: {relative}")
        require(artifact.stat().st_size == entry["bytes"]
                and sha256_file(artifact) == entry["sha256"], f"Tuned artifact checksum sai: {relative}")
    descriptor = json.loads((meta / "experiment.json").read_text(encoding="utf-8"))
    require("tuning-v1-" + digest(descriptor)[:16] == experiment, "Tuning descriptor digest sai.")
    selection = json.loads((meta / "selection.json").read_text(encoding="utf-8"))
    require(selection == result["selection"], "Tuning selection khác manifest.")
    require(select_configurations(_read_state(meta / "trials.json", experiment), descriptor["plan"]) == selection, "Selection không khớp train-only CV.")
    return result


def comparison_table(baseline, records):
    return pd.DataFrame([{"model": name, "baseline_macro_f1": baseline.metadata[name]["metrics"]["macro_f1"],
        "tuned_macro_f1": records[name]["metrics"]["macro_f1"],
        "delta_macro_f1": records[name]["metrics"]["macro_f1"] - baseline.metadata[name]["metrics"]["macro_f1"],
        "baseline_validation_seconds": baseline.metadata[name]["prediction_seconds"],
        "tuned_validation_seconds": records[name]["prediction_seconds"]} for name in MODEL_NAMES])


def comparison_chart(table):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 4))
    table.set_index("model")[["baseline_macro_f1", "tuned_macro_f1"]].plot.bar(ax=ax, rot=20)
    ax.set(ylabel="Validation Macro F1", ylim=(0, 1), title="Baseline vs train-CV-selected tuning (validation)")
    fig.tight_layout()
    return fig


def run_tuning(session, *, enabled=False, trusted=False, progress=print):
    """Explicit opt-in only. Never writes into baseline namespaces or changes session.config."""
    if not enabled:
        progress("SKIPPED: RUN_HYPERPARAMETER_TUNING=False; không CV/fit/predict/ghi artifact.")
        return None
    require(trusted, "Chỉ dùng checkpoint baseline/tuned của chính dự án; trusted=True.")
    plan = search_plan(session.config)
    baseline = Phase4(session)
    baseline.verify()  # Existing verified baseline loader; no baseline fit.
    if session.data is None:
        session.load_data()
    train = session.data["train"]
    folds, assignment, inventory, split_warnings = grouped_folds(train[1], train[2], len(baseline.classes), plan)
    config = deepcopy(session.config)
    config["resources"] = plan["resources"]
    base = experiment_identity(session.paths.project_root, config, session.inputs)
    source = {name: sha256_file(session.paths.project_root / name) for name in SOURCE_FILES}
    descriptor = {"base": base, "baseline_experiment": baseline.experiment, "plan": plan, "source_sha256": source,
                  "assignment_sha256": hashlib.sha256(assignment.tobytes()).hexdigest(),
                  "fold_inventory": inventory, "split_warnings": split_warnings}
    experiment = "tuning-v1-" + digest(descriptor)[:16]
    root = session.paths.storage_root.resolve()
    meta, models, reports = _paths(root, experiment)
    if (meta / "manifest.json").is_file():
        progress(f"REUSED {experiment}: kiểm manifest/checkpoint, không fit lại.")
        return read_tuning_result(root, experiment)
    meta.mkdir(parents=True, exist_ok=True)
    descriptor_path = meta / "experiment.json"
    if descriptor_path.exists():
        require(json.loads(descriptor_path.read_text(encoding="utf-8")) == descriptor, "Không ghi đè experiment khác.")
    else:
        with descriptor_path.open("xb") as stream:
            stream.write(json_bytes(descriptor))
    stream = io.BytesIO()
    np.savez_compressed(stream, row_0based=np.arange(len(assignment)), group_id=train[2], fold=assignment)
    if (meta / "cv_assignments.npz").exists():
        with np.load(meta / "cv_assignments.npz", allow_pickle=False) as saved:
            require(np.array_equal(saved["row_0based"], np.arange(len(assignment)))
                    and np.array_equal(saved["group_id"], train[2]) and np.array_equal(saved["fold"], assignment), "CV assignments đã lưu khác train.")
    else:
        atomic_bytes(meta / "cv_assignments.npz", stream.getvalue())
    progress(f"Experiment {experiment}: train-only CV; {sum(map(len, plan['candidates'].values()))} candidates × {plan['folds']} folds.")
    bounded = deepcopy(config)
    trials = search_train_only(train, bounded, plan, folds, len(baseline.classes), meta / "trials.json", experiment, progress=progress)
    selection = select_configurations(trials, plan)  # Freeze ALL five before seeing validation results.
    selection_path = meta / "selection.json"
    if selection_path.exists():
        require(json.loads(selection_path.read_text(encoding="utf-8")) == selection, "Selection đã khóa khác CV; không ghi đè.")
    else:
        atomic_bytes(selection_path, json_bytes(selection))
    config["models"] = {name: selection[name]["parameters"] for name in MODEL_NAMES}
    config["run_tag"] = "tuned-v1"
    identity = experiment_identity(session.paths.project_root, config, session.inputs)
    identity.pop("experiment_id")
    identity["source_sha256"].update(source)
    identity["tuning_experiment"] = experiment
    identity["selection_sha256"] = sha256_file(selection_path)
    identity["experiment_id"] = config["run_tag"] + "-" + digest(identity)[:16]
    records = {}
    for name in MODEL_NAMES:
        # Existing durable fit-once / resume-validation / completed-reuse implementation.
        records[name] = run_model(name, config, identity, session.data, models,
                                  trust_own_checkpoints=True, progress=progress)
    table = comparison_table(baseline, records)
    reports.mkdir(parents=True, exist_ok=True)
    atomic_bytes(reports / "baseline_vs_tuned.csv", table.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    import matplotlib.pyplot as plt
    fig = comparison_chart(table)
    try:
        stream = io.BytesIO()
        fig.savefig(stream, format="png", dpi=130)
        atomic_bytes(reports / "baseline_vs_tuned.png", stream.getvalue())
    finally:
        plt.close(fig)
    files = {name: {"sha256": sha256_file(root / name), "bytes": (root / name).stat().st_size}
             for name in sorted(_expected_files(experiment))}
    result = {"status": "completed", "experiment_id": experiment, "identity": identity,
              "baseline_experiment": baseline.experiment, "plan": plan, "selection": selection,
              "fold_inventory": inventory, "split_warnings": split_warnings,
              "comparison": table.to_dict(orient="records"), "files": files,
              "selection_data": "train_only_group_cv", "validation_used_for_search": False,
              "test_payload_opened": False, "application_model_changed": False}
    atomic_bytes(meta / "manifest.json", json_bytes(result))  # Completion marker written last.
    progress(f"COMPLETED {experiment}; manifest={meta / 'manifest.json'}; model mặc định chưa thay đổi.")
    return read_tuning_result(root, experiment)
