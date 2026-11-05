"""Phase 4: verified predictions and prefitted voting; never fit or open test data."""
from __future__ import annotations

from contextlib import contextmanager
import base64
import builtins
import gc
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch
import warnings

import numpy as np
import pandas as pd
import psutil
from sklearn import config_context
from sklearn.metrics import precision_recall_fscore_support
from threadpoolctl import threadpool_limits

from src.data.integrity import read_baseline, verify_training_inputs
from src.data.loader import sha256_file
from src.data.paths import OutputPaths
from src.models.runtime import MODEL_NAMES, cache_training_inputs, load_training_data
from src.models.training import (atomic_bytes, experiment_identity, json_bytes,
                                 load_fitted_checkpoint, read_completed_checkpoint, validation_metrics)

EXPERIMENT = "baseline-v1-f8a5bfdb7b4c12cd"
PRIORITY = ("logistic_regression", "linear_svc", "knn", "bernoulli_nb", "random_forest")
HARD = {
    "hard_lr_svc_knn": ("logistic_regression", "linear_svc", "knn"),
    "hard_lr_svc_nb": ("logistic_regression", "linear_svc", "bernoulli_nb"),
    "hard_lr_svc_rf": ("logistic_regression", "linear_svc", "random_forest"),
}
SOFT = {
    "soft_lr_nb_rf": ("logistic_regression", "bernoulli_nb", "random_forest"),
    "soft_lr_knn_nb": ("logistic_regression", "knn", "bernoulli_nb"),
}
BASELINE = "single_logistic_regression"
RTOL, ATOL = 1e-10, 1e-12


class IntegrityError(ValueError):
    pass


class ProbabilityUnavailable(RuntimeError):
    """An operational limitation, not permission to fabricate probabilities."""


class FitForbidden(BaseException):
    pass


@contextmanager
def phase4_guard(root):
    """Scoped safety checks; leave the notebook's kernel settings intact on exit."""
    root = Path(root).resolve()
    previous = sys.getprofile()
    counts = {"model_or_feature_fit_attempts": 0, "test_payload_access": 0, "protected_write_attempts": 0}
    protected = [root / p for p in ("data", "src", "configs", "artifacts/models/phase3", "artifacts/metadata/phase2", "artifacts/metadata/phase3")]

    def forbidden_write(value):
        if not isinstance(value, (str, os.PathLike)):
            return False
        path = Path(value).resolve()
        return any(path.is_relative_to(p) for p in protected) or (path.is_relative_to(root / "reports") and path.name.startswith("phase3_"))

    def guarded_open(original):
        def call(file, mode="r", *args, **kwargs):
            if isinstance(file, (str, os.PathLike)) and Path(file).name == "test.csv.gz":
                counts["test_payload_access"] += 1
                raise IntegrityError("Phase 4 không được mở CSV test, kể cả để băm checksum.")
            if any(c in str(mode) for c in "wax+") and forbidden_write(file):
                counts["protected_write_attempts"] += 1
                raise IntegrityError(f"Không được sửa dữ liệu/source/Phase 3: {file}")
            return original(file, mode, *args, **kwargs)
        return call

    def mutation(original):
        def call(*args, **kwargs):
            if any(forbidden_write(a) for a in args[:2]):
                counts["protected_write_attempts"] += 1
                raise IntegrityError("Không được di chuyển/xóa/ghi đè artifact được bảo vệ.")
            return original(*args, **kwargs)
        return call

    def profile(frame, event, arg):
        module = frame.f_globals.get("__name__", "")
        if event != "call" or not module.startswith("sklearn.") or frame.f_code.co_name not in {"fit", "fit_transform", "partial_fit"}:
            return
        if module == "sklearn.preprocessing._label" and type(frame.f_locals.get("self")).__name__ == "LabelEncoder":
            parent = frame.f_back
            while parent:
                if parent.f_globals.get("__name__") == "sklearn.metrics._classification":
                    return  # Temporary internal metric encoding, never the project mapping.
                parent = parent.f_back
        counts["model_or_feature_fit_attempts"] += 1
        raise FitForbidden("Phase 4 cấm fit model, transformer hoặc calibrator.")

    from contextlib import ExitStack
    with ExitStack() as stack:
        stack.enter_context(patch.object(builtins, "open", guarded_open(builtins.open)))
        stack.enter_context(patch.object(io, "open", guarded_open(io.open)))
        for name in ("rename", "replace", "remove", "unlink", "mkdir", "rmdir"):
            stack.enter_context(patch.object(os, name, mutation(getattr(os, name))))
        sys.setprofile(profile)
        try:
            yield counts
        finally:
            sys.setprofile(previous)


def require(condition, message):
    if not condition:
        raise IntegrityError(message)


def class_predictions(value, n_rows, n_classes):
    value = np.asarray(value)
    require(value.shape == (n_rows,) and np.issubdtype(value.dtype, np.integer), "Prediction shape/dtype không hợp lệ.")
    require(np.isin(value, np.arange(n_classes)).all(), "Prediction ngoài label mapping.")
    return value


def hard_vote(predictions, members, n_classes):
    """Majority; tied labels prefer LR, SVC, KNN, NB, RF, never the smallest ID."""
    require(len(set(members)) == len(members) and set(members) <= set(PRIORITY), "Danh sách model vote không hợp lệ.")
    ordered = [name for name in PRIORITY if name in members]
    require(bool(ordered), "Cần model để vote.")
    n = len(predictions[ordered[0]])
    votes = np.column_stack([class_predictions(predictions[m], n, n_classes) for m in ordered])
    counts = (votes[:, :, None] == votes[:, None, :]).sum(axis=2)
    position = counts.argmax(axis=1)  # First *model priority*, not first class ID.
    return _hard_result(votes, counts, position)


def _hard_result(votes, counts, position):
    # Count ties between distinct winning labels, not repeated votes for one label.
    tied = (counts == counts.max(axis=1, keepdims=True))
    multiple = np.any(tied & (votes != votes[np.arange(len(votes)), position, None]), axis=1)
    return votes[np.arange(len(votes)), position], int(multiple.sum())


def validate_probabilities(probability, n_rows, class_ids, n_classes):
    require(np.array_equal(np.asarray(class_ids), np.arange(n_classes)), "Probability class order khác mapping đã khóa.")
    require(probability.shape == (n_rows, n_classes), "Probability shape sai.")
    require(np.isfinite(probability).all() and (probability >= 0).all() and (probability <= 1).all(), "Probability có NaN/Inf hoặc ngoài [0,1].")
    require(np.allclose(probability.sum(axis=1), 1, rtol=0, atol=1e-6), "Tổng probability mỗi hàng không gần 1.")


def soft_vote(probabilities, members, classes, *, batch_size=64):
    """Equal mean; exact ties prefer LR probability, then English label order."""
    require("linear_svc" not in members and "logistic_regression" in members, "Soft Voting không nhận LinearSVC hoặc thiếu LR phá hòa.")
    require(len(set(members)) == len(members), "Model lặp trong soft vote.")
    n, c = probabilities[members[0]].shape
    require(c == len(classes) and len(set(classes)) == c, "Class names sai.")
    require(all(probabilities[m].shape == (n, c) for m in members), "Probability row/column alignment sai.")
    lexical = np.argsort(np.asarray(classes), kind="stable")
    prediction = np.empty(n, dtype=np.int64)
    tie_rows = 0
    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        blocks = [np.asarray(probabilities[m][start:end], dtype=np.float64) for m in members]
        for block in blocks:
            validate_probabilities(block, end - start, np.arange(c), c)
        average = sum(blocks) / len(blocks)
        tied = average == average.max(axis=1, keepdims=True)
        tie_rows += int((tied.sum(axis=1) > 1).sum())
        lr = np.asarray(probabilities["logistic_regression"][start:end])
        secondary = np.where(tied, lr, -np.inf)
        tied &= secondary == secondary.max(axis=1, keepdims=True)
        prediction[start:end] = lexical[tied[:, lexical].argmax(axis=1)]
    return prediction, tie_rows


def error_diversity(predictions, y, names=MODEL_NAMES, *, n_classes=None):
    y = np.asarray(y)
    if n_classes is None:
        n_classes = int(max(y.max(), *(np.asarray(predictions[n]).max() for n in names))) + 1
    p = np.stack([class_predictions(predictions[n], len(y), n_classes) for n in names])
    error = p != y
    disagreement = (p[:, None, :] != p[None, :, :]).mean(axis=2)
    joint_error = (error[:, None, :] & error[None, :, :]).mean(axis=2)
    rescue = (error[:, None, :] & ~error[None, :, :]).mean(axis=2)
    return {"names": list(names), "n_validation": len(y), "disagreement": disagreement,
            "joint_error": joint_error, "a_wrong_b_correct": rescue}


def score_prediction(y, prediction, n_classes):
    prediction = class_predictions(prediction, len(y), n_classes)
    scores = validation_metrics(y, prediction, n_classes)
    _, _, f1, _ = precision_recall_fscore_support(y, prediction, labels=np.arange(n_classes), zero_division=0)
    return {**scores, "predicted_classes": len(np.unique(prediction)), "classes_f1_zero": int((f1 == 0).sum())}


class Phase4:
    """A validation workflow over existing Phase 3 artifacts, using existing loaders."""
    def __init__(self, session, *, experiment=EXPERIMENT):
        self.session, self.paths, self.config = session, session.paths, session.config
        self.output = OutputPaths(self.paths.storage_root)
        self.experiment = experiment
        self.run = self.output.models_dir / "phase3" / experiment
        self.records, self.ensemble_predictions = {}, {}
        self.probabilities, self.probability_sources, self.limitations = {}, {}, []
        self.guards = {"model_or_feature_fit_attempts": 0, "test_payload_access": 0, "protected_write_attempts": 0}
        self._temporary = None

    @contextmanager
    def guard(self):
        with phase4_guard(self.output.root) as counts:
            try:
                yield
            finally:
                for k, v in counts.items():
                    self.guards[k] += v

    def verify(self):
        with self.guard():
            self.inputs = verify_training_inputs(self.output, baseline=read_baseline(self.paths.project_root / "configs/phase2_integrity.json"))
            require(self.inputs["manifest"]["processed"] == self.session.inputs["manifest"]["processed"], "Phase 2 input mismatch.")
            cached = cache_training_inputs(self.output, self.paths.cache_dir, self.inputs)
            data = load_training_data(cached, self.inputs)
            self.x, self.y, self.groups = data["validation"]
            self.features, self.classes = self.inputs["schema"]["features"], self.inputs["labels"]["classes"]
            require(len(self.y) == 28120 and len(self.features) == 375 and len(self.classes) == 587, "Sai kích thước Phase 2 đã duyệt.")
            self.current = experiment_identity(self.paths.project_root, self.config, self.inputs)
            self.predictions, self.metadata, self.identities = {}, {}, {}
            rows = []
            common = None
            for name in MODEL_NAMES:
                folder = self.run / name
                require((folder / "metadata.json").is_file(), f"Thiếu completed checkpoint: {folder}; không fit bù.")
                saved = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
                identity = saved["identity"]
                require(identity["experiment_id"] == self.experiment, "Sai experiment Phase 3.")
                original = {k: v for k, v in identity.items() if k != "experiment_id"}
                require(identity["experiment_id"] == identity["config"]["run_tag"] + "-" + hashlib.sha256(json_bytes(original)).hexdigest()[:16], "Experiment ID digest sai.")
                require(identity["config"] == self.config, "Config Phase 3 khác run đã duyệt.")
                for key in ("processed_fingerprint", "training_data_fingerprint", "validation_data_fingerprint", "feature_schema_identity", "label_mapping_identity"):
                    require(identity[key] == self.current[key], "Identity khác dữ liệu/schema/mapping: " + key)
                if common is None:
                    common = identity
                require(common == identity, "Các model khác experiment identity.")
                verified, prediction = read_completed_checkpoint(folder, identity, self.y, self.groups)
                fit = json.loads((folder / "fit.json").read_text(encoding="utf-8"))
                require(verified["model"] == fit["model"] == name, "Model key khác checkpoint.")
                require(verified["n_input_features"] == fit["n_input_features"] == 375
                        and verified["n_retained_features"] == fit["n_retained_features"] == 318
                        and fit["variance_threshold"] == verified["variance_threshold"] == 0, "Sai feature pipeline Phase 3.")
                prediction = class_predictions(prediction, len(self.y), len(self.classes))
                self.predictions[name], self.metadata[name], self.identities[name] = prediction, verified, identity
                rows.append({"model": name, "integrity": "PASS", "rows": len(prediction), "input_features": verified["n_input_features"],
                             "retained_features": verified["n_retained_features"], "pipeline_bytes": (folder / "pipeline.joblib").stat().st_size,
                             "macro_f1": verified["metrics"]["macro_f1"], "original_predict_seconds": verified["prediction_seconds"]})
            require(abs(self.metadata["logistic_regression"]["metrics"]["macro_f1"] - .78780814) <= 5e-9 + ATOL, "LR baseline khác audit đã duyệt.")
            self.identity = common
            self.diversity = error_diversity(self.predictions, self.y, n_classes=len(self.classes))
            self.records[BASELINE] = {"id": BASELINE, "mode": "single", "members": ["logistic_regression"], "status": "completed", "tie_rows": 0,
                                      **score_prediction(self.y, self.predictions["logistic_regression"], len(self.classes))}
            return pd.DataFrame(rows)

    def evaluate_hard(self):
        with self.guard():
            for key, members in HARD.items():
                prediction, ties = hard_vote(self.predictions, members, len(self.classes))
                self.ensemble_predictions[key] = prediction
                self.records[key] = {"id": key, "mode": "hard", "members": list(members), "status": "completed", "tie_rows": ties,
                                     "corrects_lr_rows": int(((prediction == self.y) & (self.predictions["logistic_regression"] != self.y)).sum()),
                                     "loses_lr_rows": int(((prediction != self.y) & (self.predictions["logistic_regression"] == self.y)).sum()),
                                     **score_prediction(self.y, prediction, len(self.classes))}
        return self.table()

    def _load(self, name, *, trusted):
        require(trusted, "Chỉ load checkpoint do chính dự án tạo; truyền trusted=True.")
        identity = self.identities[name]
        if identity["versions"] != self.current["versions"]:
            raise ProbabilityUnavailable(f"{name}: thư viện/Python khác môi trường đã train: {identity['versions']}")
        changed = [n for n, h in identity["source_sha256"].items() if sha256_file(self.paths.project_root / n) != h]
        if changed:
            raise ProbabilityUnavailable(f"{name}: source gốc thay đổi: {changed}")
        if psutil.virtual_memory().available / 2**30 < self.config["resources"]["min_available_ram_gb"]:
            raise ProbabilityUnavailable(f"{name}: RAM khả dụng thấp; không tạo xác suất giả.")
        model = load_fitted_checkpoint(self.run / name, identity, trusted=True)
        require(np.array_equal(model.classes_, np.arange(len(self.classes))), f"{name}: class order sai.")
        require(model.n_features_in_ == len(self.features), f"{name}: input feature count sai.")
        return model

    def prepare_probabilities(self, *, trusted=False):
        """Use authenticated saved probabilities or batched inference; ephemeral memmaps."""
        names = tuple(n for n in MODEL_NAMES if n != "linear_svc")
        self.paths.cache_dir.mkdir(parents=True, exist_ok=True)
        if self._temporary is None:
            self._temporary = tempfile.TemporaryDirectory(prefix="phase4-probabilities-", dir=self.paths.cache_dir)
        with self.guard():
            for name in names:
                if name in self.probabilities:
                    continue
                model, probability = None, None
                try:
                    metadata = self.metadata[name]
                    path = self.run / name / "validation_predictions.npz"
                    require(sha256_file(path) == metadata["predictions_sha256"], "Probability source payload checksum sai.")
                    saved = None
                    # Only a checksum-verified Phase 3 payload with explicit probability provenance.
                    with np.load(path, allow_pickle=False) as payload:
                        if "y_proba" in payload.files and "class_ids" in payload.files and metadata.get("probability_method") == "predict_proba":
                            saved, class_ids = payload["y_proba"], payload["class_ids"]
                            validate_probabilities(saved, len(self.y), class_ids, len(self.classes))
                    target = Path(self._temporary.name) / f"{name}.npy"
                    probability = np.lib.format.open_memmap(target, mode="w+", dtype=np.float64, shape=(len(self.y), len(self.classes)))
                    started, last_log = time.perf_counter(), 0.0
                    caught_messages = []
                    if saved is not None:
                        probability[:] = saved
                        method = "persisted_y_proba_in_verified_phase3_payload"
                    else:
                        model = self._load(name, trusted=trusted)
                        if not hasattr(model, "predict_proba"):
                            raise ProbabilityUnavailable(f"{name}: không hỗ trợ predict_proba.")
                        method = "trusted_fitted_pipeline.predict_proba"
                        print(f"{name}: chưa có persisted probability hợp lệ; chạy predict_proba validation theo batch.", flush=True)
                        resources = self.config["resources"]
                        with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=resources["blas_threads"]), config_context(working_memory=resources["working_memory_mb"]):
                            warnings.simplefilter("always")
                            for start in range(0, len(self.y), resources["prediction_batch_size"]):
                                end = min(start + resources["prediction_batch_size"], len(self.y))
                                block = model.predict_proba(self.x.iloc[start:end])
                                validate_probabilities(block, end - start, model.classes_, len(self.classes))
                                probability[start:end] = block
                                now = time.perf_counter()
                                if now - last_log >= 15 or end == len(self.y):
                                    print(f"{name}: probability {end:,}/{len(self.y):,}", flush=True)
                                    last_log = now
                        caught_messages = [f"{w.category.__name__}: {w.message}" for w in caught]
                    probability.flush()
                    require(np.array_equal(probability.argmax(axis=1), self.predictions[name]), f"{name}: argmax probability không khớp predictions Phase 3.")
                    self.probabilities[name] = probability
                    self.probability_sources[name] = {"method": method, "shape": list(probability.shape), "dtype": str(probability.dtype),
                        "class_ids": list(range(len(self.classes))), "payload_sha256": sha256_file(target),
                        "source_pipeline_sha256": metadata["pipeline_sha256"], "validation_input_sha256": self.identity["validation_data_fingerprint"],
                        "validation_seconds": time.perf_counter() - started, "warnings": caught_messages, "persistent_probability_written": False}
                except (ProbabilityUnavailable, MemoryError) as exc:
                    self.limitations.append(str(exc))
                    print("SOFT INPUT NOT AVAILABLE:", exc, flush=True)
                finally:
                    if probability is not None and name not in self.probabilities:
                        probability._mmap.close()
                    del model
                    gc.collect()
        return pd.DataFrame([{"model": n, "available": n in self.probabilities, "method": self.probability_sources.get(n, {}).get("method", "NOT AVAILABLE"),
                              "validation_seconds": self.probability_sources.get(n, {}).get("validation_seconds")} for n in names])

    def evaluate_soft(self):
        with self.guard():
            for key, members in SOFT.items():
                missing = [m for m in members if m not in self.probabilities]
                if missing:
                    self.records[key] = {"id": key, "mode": "soft", "members": list(members), "status": "not_available", "reason": "Missing verified probabilities: " + ", ".join(missing)}
                    continue
                prediction, ties = soft_vote(self.probabilities, members, self.classes)
                self.ensemble_predictions[key] = prediction
                self.records[key] = {"id": key, "mode": "soft", "members": list(members), "status": "completed", "tie_rows": ties,
                                     "corrects_lr_rows": int(((prediction == self.y) & (self.predictions["logistic_regression"] != self.y)).sum()),
                                     "loses_lr_rows": int(((prediction != self.y) & (self.predictions["logistic_regression"] == self.y)).sum()),
                                     **score_prediction(self.y, prediction, len(self.classes))}
        return self.table()

    def table(self):
        rows = []
        baseline = self.records[BASELINE]["macro_f1"]
        for record in self.records.values():
            rows.append({"combination": record["id"], "mode": record["mode"], "status": record["status"], "base_models": len(record["members"]),
                         **{k: record.get(k) for k in ("accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1", "predicted_classes", "classes_f1_zero", "tie_rows")},
                         "delta_macro_f1_vs_lr": record["macro_f1"] - baseline if "macro_f1" in record else None,
                         "pipeline_bytes": sum((self.run / n / "pipeline.joblib").stat().st_size for n in record["members"]),
                         "original_base_predict_seconds_sum": sum(self.metadata[n]["prediction_seconds"] for n in record["members"]), "reason": record.get("reason", "")})
        return pd.DataFrame(rows)

    def best(self):
        ready = [r for r in self.records.values() if r["status"] == "completed"]
        return sorted(ready, key=lambda r: (-r["macro_f1"], len(r["members"]), r["id"]))[0]

    def definition(self, key):
        record = self.records[key]
        require(record["status"] == "completed", "Không xuất wrapper cho combination chưa evaluate.")
        return {"version": 1, "id": key, "mode": record["mode"], "members": record["members"],
                "phase3_experiment": self.experiment, "phase3_identity": self.identity,
                "feature_schema_sha256": self.identity["feature_schema_identity"], "label_mapping_sha256": self.identity["label_mapping_identity"],
                "features": self.features, "classes": self.classes, "class_ids": list(range(len(self.classes))),
                "pipeline_sha256": {n: self.metadata[n]["pipeline_sha256"] for n in record["members"]},
                "hard_tie_priority": list(PRIORITY), "soft_tie_rule": "exact mean tie -> LR probability -> English label Unicode order",
                "weights": "uniform", "resources": self.config["resources"]}

    def single_input_check(self, *, trusted=False):
        candidate = self.best()
        model = PrefittedVoting(self.definition(candidate["id"]), self.output.root, trusted=trusted)
        expected = self.predictions["logistic_regression"] if candidate["id"] == BASELINE else self.ensemble_predictions[candidate["id"]]
        try:
            with self.guard():
                prediction = model.predict(self.x.iloc[:1])
                require(np.array_equal(prediction, expected[:1]), "Single-input inference khác evaluation.")
                self.single_input = {"status": "PASS", "input_features": self.x.shape[1], "matches_validation_row_0": True}
        except ProbabilityUnavailable as exc:
            self.single_input = {"status": "NOT VERIFIED", "reason": str(exc)}
            self.limitations.append(str(exc))
        finally:
            model.close()
        return self.single_input

    def close(self):
        for probability in self.probabilities.values():
            if isinstance(probability, np.memmap):
                probability._mmap.close()
        self.probabilities.clear()
        if self._temporary:
            self._temporary.cleanup()
            self._temporary = None


class PrefittedVoting:
    """Single/vector inference using referenced immutable pipelines; no fit method."""
    def __init__(self, definition, storage_root, *, trusted=False):
        self.definition, self.root, self.trusted = definition, Path(storage_root).resolve(), trusted
        self.models = {}
        require(definition["version"] == 1 and definition["weights"] == "uniform", "Unsupported ensemble definition.")
        allowed = {BASELINE: ("single", ("logistic_regression",)), **{k: ("hard", v) for k, v in HARD.items()}, **{k: ("soft", v) for k, v in SOFT.items()}}
        require((definition["mode"], tuple(definition["members"])) == allowed.get(definition["id"]), "Unapproved combination.")
        require(definition["hard_tie_priority"] == list(PRIORITY), "Tie rule khác định nghĩa đã duyệt.")
        require(definition["phase3_experiment"] == definition["phase3_identity"]["experiment_id"], "Sai checkpoint reference.")
        require(Path(definition["phase3_experiment"]).name == definition["phase3_experiment"] and ".." not in definition["phase3_experiment"], "Checkpoint reference không hợp lệ.")
        meta = self.root / "artifacts/metadata/phase2"
        for name, key in (("feature_schema.json", "feature_schema_sha256"), ("label_mapping.json", "label_mapping_sha256")):
            require(sha256_file(meta / name) == definition[key], "Inference schema/mapping checksum sai.")
        schema = json.loads((meta / "feature_schema.json").read_text(encoding="utf-8"))
        labels = json.loads((meta / "label_mapping.json").read_text(encoding="utf-8"))
        require(schema["features"] == definition["features"] and labels["classes"] == definition["classes"], "Inference ordering mismatch.")
        require(definition["class_ids"] == list(range(len(labels["classes"]))), "Inference class order sai.")

    def _input(self, x):
        features = self.definition["features"]
        if isinstance(x, pd.DataFrame):
            require(x.columns.tolist() == features, "Cần đúng tên và thứ tự 375 feature.")
            frame = x
        else:
            array = np.asarray(x)
            if array.ndim == 1:
                array = array.reshape(1, -1)
            require(array.ndim == 2 and array.shape[1] == len(features), "Input vector không đúng số feature.")
            frame = pd.DataFrame(array, columns=features)
        require(len(frame) > 0 and frame.isin([0, 1]).all().all(), "Input phải nhị phân, không thiếu/NaN.")
        return frame

    def predict(self, x):
        x = self._input(x)
        d = self.definition
        with phase4_guard(self.root):
            from src.models import training
            import joblib, scipy, sklearn
            import platform
            versions = {"python": platform.python_version(), "sklearn": sklearn.__version__, "numpy": np.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__}
            if versions != d["phase3_identity"]["versions"]:
                raise ProbabilityUnavailable("Inference cần môi trường phiên bản đã train.")
            source = Path(training.__file__).resolve().parents[2]
            if any(not (source / n).is_file() or sha256_file(source / n) != h for n, h in d["phase3_identity"]["source_sha256"].items()):
                raise ProbabilityUnavailable("Source pipeline gốc đã đổi; chưa reload để inference.")
            require(self.trusted, "Chỉ load checkpoint của chính dự án, truyền trusted=True.")
            for name in d["members"]:
                folder = self.root / "artifacts/models/phase3" / d["phase3_experiment"] / name
                if name not in self.models:
                    if psutil.virtual_memory().available / 2**30 < d["resources"]["min_available_ram_gb"]:
                        raise ProbabilityUnavailable("Không đủ RAM để load thêm pipeline.")
                    require(sha256_file(folder / "pipeline.joblib") == d["pipeline_sha256"][name], "Pipeline checksum khác definition.")
                    self.models[name] = training.load_fitted_checkpoint(folder, d["phase3_identity"], trusted=True)
                    require(np.array_equal(self.models[name].classes_, np.arange(len(d["classes"]))), "Loaded class order sai.")
            batch = d["resources"]["prediction_batch_size"]
            if len(x) > batch:
                return np.concatenate([self.predict(x.iloc[i:i+batch]) for i in range(0, len(x), batch)])
            with threadpool_limits(limits=d["resources"]["blas_threads"]), config_context(working_memory=d["resources"]["working_memory_mb"]):
                if d["mode"] == "single":
                    return self.models[d["members"][0]].predict(x)
                if d["mode"] == "hard":
                    return hard_vote({n: self.models[n].predict(x) for n in d["members"]}, d["members"], len(d["classes"]))[0]
                p = {n: self.models[n].predict_proba(x) for n in d["members"]}
                return soft_vote(p, d["members"], d["classes"])[0]

    def close(self):
        self.models.clear()
        gc.collect()


def diversity_figure(diversity):
    import matplotlib.pyplot as plt
    short = {"logistic_regression": "LR", "random_forest": "RF", "linear_svc": "SVC", "knn": "KNN", "bernoulli_nb": "NB"}
    fig, ax = plt.subplots(figsize=(6.8, 5.5))
    image = ax.imshow(diversity["joint_error"], cmap="Blues", vmin=0)
    names = [short[n] for n in diversity["names"]]
    for i in range(len(names)):
        for j in range(len(names)):
            d, joint = diversity["disagreement"][i, j], diversity["joint_error"][i, j]
            ax.text(j, i, f"D {d:.1%}\nJ {joint:.1%}", ha="center", va="center", fontsize=9,
                    color="white" if joint > diversity["joint_error"].max() * .6 else "black")
    ax.set(xticks=np.arange(len(names)), yticks=np.arange(len(names)), xticklabels=names, yticklabels=names,
           title=f"Validation n={diversity['n_validation']:,}: disagreement D / joint error J")
    fig.colorbar(image, ax=ax, label="Joint error rate J")
    fig.text(.5, .015, "Khác dự đoán không bảo đảm một model sửa được lỗi của model kia.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, 1))
    return fig


def comparison_figure(phase):
    import matplotlib.pyplot as plt
    table = phase.table().query("status == 'completed'")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    colors = ["#374151" if key == BASELINE else "#2563a6" for key in table["combination"]]
    ax.barh(table["combination"], table["macro_f1"], color=colors)
    ax.axvline(phase.records[BASELINE]["macro_f1"], color="#d97706", linestyle="--", label="Logistic Regression baseline")
    for i, value in enumerate(table["macro_f1"]):
        ax.text(value + .005, i, f"{value:.5f}", va="center")
    ax.set(xlim=(0, 1), xlabel="Validation Macro F1, zero_division=0", title="Phase 4 — actual validation results")
    ax.invert_yaxis()
    ax.legend(loc="lower right")
    fig.tight_layout()
    return fig


def interpretation(phase):
    names = phase.diversity["names"]
    a, b = names.index("logistic_regression"), names.index("linear_svc")
    candidate, baseline = phase.best(), phase.records[BASELINE]["macro_f1"]
    delta = candidate["macro_f1"] - baseline
    changes = " ".join(f"{r['id']}: sửa {r.get('corrects_lr_rows',0)} hàng LR sai, làm sai {r.get('loses_lr_rows',0)} hàng LR đúng."
                       for r in phase.records.values() if r["mode"] == "hard" and r["status"] == "completed")
    return (f"LR/SVC: disagreement={phase.diversity['disagreement'][a,b]:.4%}; "
            f"joint error={phase.diversity['joint_error'][a,b]:.4%}; "
            f"LR sai, SVC đúng={phase.diversity['a_wrong_b_correct'][a,b]:.4%}; "
            f"SVC sai, LR đúng={phase.diversity['a_wrong_b_correct'][b,a]:.4%}.\n"
            f"{changes}\nỨng viên theo validation: {candidate['id']}, Macro F1={candidate['macro_f1']:.8f}; delta so LR={delta:+.8f}. "
            + ("Có ensemble vượt LR trên split này. " if delta > 0 else "Chưa có ensemble vượt LR trên split này. ")
            + "Chênh lệch không chứng minh ý nghĩa thống kê. Chỉ thử 3 hard/2 soft đã định, không tìm trọng số. "
            "Xác suất được kiểm đúng cấu trúc, chưa chứng minh calibration; đây là giới hạn của soft voting. "
            "Ba vote với ưu tiên LR khi hòa không cứu được hàng cả LR/SVC cùng sai, ngay cả khi model thứ ba đúng; "
            "model thứ ba chỉ đổi quyết định khi tạo đa số hoặc phá tình huống LR/SVC bất đồng. "
            "Chi phí prediction cộng của baseline chỉ là tham chiếu, không phải benchmark ensemble hoặc latency chatbot. "
            "KNN chậm trên toàn validation; số byte checkpoint nén không phải peak RAM. "
            "Support lớp nhỏ và việc dùng lại validation để lựa chọn hạn chế kết luận tổng quát hóa. Không mở test.")


def save_phase4(phase, diversity_fig, comparison_fig):
    """New namespaced run using existing OutputPaths/new_run and atomic writer."""
    require(set(phase.records) == {BASELINE, *HARD, *SOFT}, "Chạy đủ các bước hard và soft/limitations trước export.")
    with phase.guard():
        output = phase.paths.new_run("phase4")
        model_dir = phase.output.models_dir / "phase4" / output.run_id
        model_dir.mkdir(parents=True, exist_ok=False)
        table = phase.table()
        files = {}

        def save(path, payload):
            require(not path.exists(), f"Không ghi đè file đã có: {path}")
            atomic_bytes(path, payload)
            relative = path.relative_to(phase.output.root).as_posix()
            files[relative] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            return relative

        save(output.tables_dir / "validation_comparison.csv", table.to_csv(index=False, lineterminator="\n").encode("utf-8"))
        for name, fig in (("error_diversity", diversity_fig), ("macro_f1_comparison", comparison_fig)):
            stream = io.BytesIO()
            fig.savefig(stream, format="png", dpi=150, facecolor="white")
            save(output.figures_dir / f"{name}.png", stream.getvalue())
        definitions = {k: phase.definition(k) for k, r in phase.records.items() if r["status"] == "completed"}
        definition_relative = save(model_dir / "definitions.json", json_bytes({"version": 1, "candidate_id": phase.best()["id"], "definitions": definitions}))
        stream = io.BytesIO()
        np.savez_compressed(stream, y_true=phase.y, group_id=phase.groups, row_0based=np.arange(len(phase.y)),
                            **phase.ensemble_predictions)
        save(output.metadata_dir / "validation_predictions.npz", stream.getvalue())
        result = {"phase": 4, "run_id": output.run_id, "phase3_experiment": phase.experiment, "phase3_identity": phase.identity,
                  "environment": phase.current["versions"], "n_validation": len(phase.y), "features": len(phase.features), "classes": len(phase.classes),
                  "selection_metric": "macro_f1", "zero_division": 0, "candidate": phase.best(),
                  "records": list(phase.records.values()), "probability_sources": phase.probability_sources, "limitations": phase.limitations,
                  "diversity": {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in phase.diversity.items()},
                  "single_input_check": getattr(phase, "single_input", {"status": "NOT VERIFIED"}),
                  "definition_relative": definition_relative, "guards": dict(phase.guards), "test_payload_opened": False, "base_models_fitted": 0,
                  "source_sha256": sha256_file(Path(__file__)), "interpretation": interpretation(phase)}
        save(output.metadata_dir / "validation_results.json", json_bytes(result))
        report = (f"# Phase 4 — {output.run_id}\n\n{result['interpretation']}\n\n"
                  f"```text\n{table.to_string(index=False)}\n```\n\n"
                  f"Single input: {result['single_input_check']}.\n\n"
                  f"Limitations: {phase.limitations}.\n\n"
                  "Uniform voting; no training/calibration/tuning or test evaluation. "
                  "Probabilities are validated model outputs, not clinically calibrated confidence.\n")
        save(output.reports_dir / "phase4_validation.md", report.encode("utf-8"))
        result["artifact_files"] = files
        manifest = output.metadata_dir / "phase4_manifest.json"
        atomic_bytes(manifest, json_bytes(result))  # Last write marks a complete run.
        result["manifest_relative"], result["manifest_sha256"] = manifest.relative_to(phase.output.root).as_posix(), sha256_file(manifest)
        return result


def load_voting_definition(path, storage_root, *, key=None, trusted=False):
    root, path = Path(storage_root).resolve(), Path(path).resolve()
    require(path.is_relative_to(root / "artifacts/models/phase4"), "Definition phải ở namespace Phase 4.")
    manifest_path = root / "artifacts/metadata/runs" / path.parent.name / "phase4_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["artifact_files"][path.relative_to(root).as_posix()]
    require(sha256_file(path) == entry["sha256"], "Definition checksum mismatch.")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    selected = key or bundle["candidate_id"]
    return PrefittedVoting(bundle["definitions"][selected], root, trusted=trusted)


def emit_phase4_result(result):
    """Compact real results for evidence transfer; contains no probability matrix."""
    packet = {k: result[k] for k in ("run_id", "phase3_experiment", "environment", "n_validation", "features", "classes", "candidate", "records", "probability_sources", "limitations", "diversity", "single_input_check", "guards", "test_payload_opened", "base_models_fitted", "definition_relative", "manifest_relative", "manifest_sha256", "source_sha256", "interpretation")}
    raw = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    print("PHASE4_SHA256=" + hashlib.sha256(raw).hexdigest())
    print("PHASE4_GZIP_BASE64=" + base64.b64encode(gzip.compress(raw, mtime=0)).decode())
