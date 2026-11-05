"""Five sequential CPU baselines, validation-only evaluation and small Drive checkpoints."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import tempfile
import threading
import time
import traceback
import warnings

import joblib
import numpy as np
import psutil
import scipy
from scipy import sparse
import sklearn
from sklearn import config_context
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import VarianceThreshold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.naive_bayes import BernoulliNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.svm import LinearSVC
from threadpoolctl import threadpool_limits

from src.data.loader import sha256_file
from src.models.runtime import META, MODEL_NAMES, runtime_snapshot


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".phase3-", delete=False) as stream:
        pending = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if hashlib.sha256(pending.read_bytes()).digest() != hashlib.sha256(payload).digest():
            raise IOError(f"Checksum temporary file failed: {path}")
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def to_csr(x):
    """Binary symptoms already share [0,1] scale; preserve sparsity, never center."""
    return sparse.csr_matrix(x, dtype=np.float64)


def build_pipeline(name: str, config: dict) -> Pipeline:
    if name not in MODEL_NAMES:
        raise ValueError("Chỉ được dùng 5 mô hình Phase 3 đã duyệt.")
    seed, params = config["seed"], dict(config["models"][name])
    workers = max(1, min(int(config["resources"]["max_workers"]), os.cpu_count() or 1))
    factories = {
        "logistic_regression": lambda: LogisticRegression(random_state=seed, **params),
        "random_forest": lambda: RandomForestClassifier(random_state=seed, n_jobs=workers, **params),
        "linear_svc": lambda: LinearSVC(random_state=seed, **params),
        "knn": lambda: KNeighborsClassifier(n_jobs=1, **params),
        "bernoulli_nb": lambda: BernoulliNB(**params),
    }
    return Pipeline([("variance", VarianceThreshold(threshold=0)),
                     ("csr", FunctionTransformer(to_csr, validate=False, feature_names_out="one-to-one")),
                     ("estimator", factories[name]())])


def experiment_identity(root: Path, config: dict, inputs: dict) -> dict:
    files = inputs["manifest"]["files"]
    identity = {
        "phase": 3, "config": config,
        "processed_fingerprint": inputs["manifest"]["processed"]["sha256"],
        "phase2_manifest_sha256": inputs["manifest_sha256"],
        "training_data_fingerprint": files["data/processed/train.csv.gz"]["sha256"],
        "validation_data_fingerprint": files["data/processed/validation.csv.gz"]["sha256"],
        "feature_schema_identity": files[f"{META}/feature_schema.json"]["sha256"],
        "label_mapping_identity": files[f"{META}/label_mapping.json"]["sha256"],
        "versions": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                     "numpy": np.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__},
        "source_sha256": {name: sha256_file(root / name) for name in (
            "src/models/training.py", "src/models/runtime.py", "src/data/preprocessing.py",
            "src/data/loader.py", "src/data/paths.py", "src/data/audit.py")},
    }
    identity["experiment_id"] = config["run_tag"] + "-" + hashlib.sha256(json_bytes(identity)).hexdigest()[:16]
    return identity


def validation_metrics(y, prediction, n_classes: int) -> dict:
    labels = np.arange(n_classes)
    precision, recall, f1, support = precision_recall_fscore_support(y, prediction, labels=labels, zero_division=0)
    return {"accuracy": float(accuracy_score(y, prediction)), "macro_precision": float(precision.mean()),
            "macro_recall": float(recall.mean()), "macro_f1": float(f1.mean()),
            "weighted_f1": float(np.average(f1, weights=support))}


@contextmanager
def sampled_memory(progress=None, stage="fit"):
    stop, values = threading.Event(), {"sampled_peak_rss_mb": 0.0}
    process = psutil.Process()
    def sample():
        started = last_log = time.perf_counter()
        while True:
            try:
                rss = process.memory_info().rss
                rss += sum(p.memory_info().rss for p in process.children(recursive=True) if p.is_running())
                values["sampled_peak_rss_mb"] = max(values["sampled_peak_rss_mb"], rss / 2**20)
            except psutil.Error:
                pass
            now = time.perf_counter()
            if progress is not None and now - last_log >= 30:
                progress(f"RUNNING {stage}: {now - started:.0f}s | peak RSS lấy mẫu {values['sampled_peak_rss_mb']:.1f} MiB "
                         f"| RAM khả dụng {psutil.virtual_memory().available / 2**30:.2f} GiB")
                last_log = now
            if stop.wait(.5):
                return
    worker = threading.Thread(target=sample, daemon=True)
    worker.start()
    try:
        yield values
    finally:
        stop.set()
        worker.join(timeout=2)


def _fit_metadata(pipeline, name, identity, fit_seconds, caught, memory) -> dict:
    estimator = pipeline.named_steps["estimator"]
    return {"status": "fitted", "model": name, "identity": identity,
            "created_utc": datetime.now(timezone.utc).isoformat(), "seed": identity["config"]["seed"],
            "parameters": estimator.get_params(deep=False), "variance_threshold": 0,
            "representation": "CSR float64, binary values already on the same scale; no centering",
            "n_input_features": int(pipeline.n_features_in_),
            "n_retained_features": int(pipeline.named_steps["variance"].get_support().sum()),
            "fit_seconds": fit_seconds, "warnings": caught, **memory,
            "environment": runtime_snapshot(), "supports_predict_proba": hasattr(pipeline, "predict_proba")}


def _save_fitted(pipeline: Pipeline, folder: Path, metadata: dict) -> dict:
    """Publish one verified directory. A fitted pipeline survives validation failures."""
    if folder.exists():
        raise FileExistsError(f"Checkpoint đã tồn tại, không ghi đè: {folder}")
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="phase3-fit-") as local:
        model = Path(local) / "pipeline.joblib"
        joblib.dump(pipeline, model, compress=3)
        metadata = {**metadata, "pipeline_sha256": sha256_file(model), "artifact_path": str(folder / "pipeline.joblib")}
        with tempfile.TemporaryDirectory(dir=folder.parent, prefix=f".{folder.name}-pending-") as pending_dir:
            pending = Path(pending_dir)
            shutil.copyfile(model, pending / "pipeline.joblib")
            if sha256_file(pending / "pipeline.joblib") != metadata["pipeline_sha256"]:
                raise IOError("Checksum pipeline khi copy lên persistent storage không khớp.")
            (pending / "fit.json").write_bytes(json_bytes(metadata))
            if folder.exists():
                raise FileExistsError(f"Checkpoint xuất hiện trong lúc publish: {folder}")
            os.rename(pending, folder)
    return metadata


def _verify_fitted(folder: Path, identity: dict) -> dict:
    metadata = json.loads((folder / "fit.json").read_text(encoding="utf-8"))
    if metadata["status"] != "fitted" or metadata["identity"] != identity or metadata["model"] != folder.name:
        raise ValueError("Checkpoint khác config/data/source/library version; không tái sử dụng.")
    if sha256_file(folder / "pipeline.joblib") != metadata["pipeline_sha256"]:
        raise ValueError("Checksum pipeline không khớp; không deserialize hoặc ghi đè.")
    return metadata


def load_fitted_checkpoint(folder: Path, identity: dict, *, trusted: bool = False) -> Pipeline:
    """Only deserialize checkpoints explicitly trusted by their owner, after all checks."""
    metadata = _verify_fitted(folder, identity)
    if not trusted:
        raise ValueError("Chỉ load joblib do chính bạn tạo và tin cậy; đặt trusted=True cho checkpoint của bạn.")
    pipeline = joblib.load(folder / "pipeline.joblib")
    if (not isinstance(pipeline, Pipeline) or pipeline.n_features_in_ != metadata["n_input_features"]
            or int(pipeline.named_steps["variance"].get_support().sum()) != metadata["n_retained_features"]):
        raise ValueError("Pipeline đã lưu không khớp metadata.")
    return pipeline


def _predict(pipeline, x, batch_size: int, progress) -> tuple[np.ndarray, float]:
    started, last_log, blocks = time.perf_counter(), 0.0, []
    for start in range(0, len(x), batch_size):
        blocks.append(np.asarray(pipeline.predict(x.iloc[start:start + batch_size]), dtype=np.int64))
        now = time.perf_counter()
        if now - last_log >= 15 or start + batch_size >= len(x):
            progress(f"  Validation: đã dự đoán {min(start + batch_size, len(x)):,}/{len(x):,} dòng")
            last_log = now
    return np.concatenate(blocks), time.perf_counter() - started


def read_completed_checkpoint(folder: Path, identity: dict, y, groups) -> tuple[dict, np.ndarray]:
    fitted = _verify_fitted(folder, identity)
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if (metadata["status"] != "completed" or metadata["identity"] != identity
            or metadata["fit_metadata_sha256"] != sha256_file(folder / "fit.json")
            or metadata["pipeline_sha256"] != fitted["pipeline_sha256"]
            or metadata["predictions_sha256"] != sha256_file(folder / "validation_predictions.npz")):
        raise ValueError("Metadata/checksum kết quả validation không khớp.")
    with np.load(folder / "validation_predictions.npz", allow_pickle=False) as saved:
        if (not np.array_equal(saved["y_true"], y) or not np.array_equal(saved["group_id"], groups)
                or not np.array_equal(saved["row_0based"], np.arange(len(y)))):
            raise ValueError("Thứ tự validation predictions không khớp dữ liệu đã khóa.")
        prediction = saved["y_pred"].copy()
    n_classes = len(set(np.asarray(y).tolist()))
    if prediction.shape != np.asarray(y).shape or not np.isin(prediction, np.arange(n_classes)).all():
        raise ValueError("Predictions không thuộc label mapping.")
    actual = validation_metrics(y, prediction, n_classes)
    if actual != metadata["metrics"]:
        raise ValueError("Metrics không khớp predictions thực.")
    return metadata, prediction


def run_model(name: str, config: dict, identity: dict, data: dict, model_root: Path,
              *, trust_own_checkpoints=False, progress=print, pipeline=None, fit=None) -> dict:
    if name not in MODEL_NAMES:
        raise ValueError("Chỉ được dùng 5 mô hình Phase 3 đã duyệt.")
    folder = model_root / name
    x_train, y_train, _ = data["train"]
    x_val, y_val, groups_val = data["validation"]
    if pipeline is not None:
        expected = build_pipeline(name, config)
        if (not isinstance(pipeline, Pipeline)
                or [key for key, _ in pipeline.steps] != [key for key, _ in expected.steps]
                or any(type(actual) is not type(reference) or actual.get_params(deep=False) != reference.get_params(deep=False)
                       for (_, actual), (_, reference) in zip(pipeline.steps, expected.steps))):
            raise ValueError("Pipeline trong notebook khác configs/phase3.json; cập nhật cấu hình tương ứng trước khi chạy/reuse.")
    if (folder / "metadata.json").is_file():
        metadata, _ = read_completed_checkpoint(folder, identity, y_val, groups_val)
        progress(f"REUSED {name}: checkpoint và predictions đã kiểm chứng; không fit lại.")
        return {**metadata, "status": "reused", "checkpoint_dir": str(folder)}
    resource = config["resources"]
    if psutil.virtual_memory().available / 2**30 < resource["min_available_ram_gb"]:
        raise MemoryError("RAM khả dụng thấp; giữ kết quả đã hoàn tất, không bắt đầu mô hình tiếp theo.")
    with threadpool_limits(limits=resource["blas_threads"]), config_context(working_memory=resource["working_memory_mb"]):
        if folder.exists():
            metadata = _verify_fitted(folder, identity)
            pipeline = load_fitted_checkpoint(folder, identity, trusted=trust_own_checkpoints)
            progress(f"RESUME {name}: pipeline đã fit; tiếp tục validation.")
        else:
            pipeline = pipeline if pipeline is not None else build_pipeline(name, config)
            progress(f"START {name}: fit {len(x_train):,} dòng train; RAM khả dụng {psutil.virtual_memory().available / 2**30:.2f} GiB")
            started = time.perf_counter()
            with warnings.catch_warnings(record=True) as caught, sampled_memory(progress, f"{name} fit") as memory:
                warnings.simplefilter("always")
                if fit is None:
                    pipeline.fit(x_train, y_train)
                else:
                    fit(pipeline)  # The explicit .fit(X_train, y_train) shown in the notebook.
            fit_seconds = time.perf_counter() - started
            messages = [f"{w.category.__name__}: {w.message}" for w in caught]
            metadata = _save_fitted(pipeline, folder, _fit_metadata(pipeline, name, identity, fit_seconds, messages, memory))
            progress(f"FITTED {name}: {fit_seconds:.3f}s | features {metadata['n_input_features']} → {metadata['n_retained_features']} | đã lưu Drive checkpoint")
            for message in messages:
                progress("  WARNING " + message)
        with warnings.catch_warnings(record=True) as prediction_warnings, sampled_memory(progress, f"{name} validation") as memory:
            warnings.simplefilter("always")
            prediction, prediction_seconds = _predict(pipeline, x_val, resource["prediction_batch_size"], progress)
        scores = validation_metrics(y_val, prediction, len(pipeline.classes_))
        for warning in prediction_warnings:
            progress(f"  WARNING {warning.category.__name__}: {warning.message}")
        stream = io.BytesIO()
        np.savez_compressed(stream, y_true=y_val, y_pred=prediction, group_id=groups_val, row_0based=np.arange(len(y_val)))
        atomic_bytes(folder / "validation_predictions.npz", stream.getvalue())
        complete = {**metadata, "status": "completed", "metrics": scores,
                    "prediction_seconds": prediction_seconds,
                    "prediction_batch_size": resource["prediction_batch_size"],
                    "validation_sampled_peak_rss_mb": memory["sampled_peak_rss_mb"],
                    "warnings": metadata["warnings"] + [f"{w.category.__name__}: {w.message}" for w in prediction_warnings],
                    "fit_metadata_sha256": sha256_file(folder / "fit.json"),
                    "predictions_sha256": sha256_file(folder / "validation_predictions.npz"),
                    "validation_only": True, "test_payload_opened": False}
        atomic_bytes(folder / "metadata.json", json_bytes(complete))
        progress(f"FINISHED {name}: predict {prediction_seconds:.3f}s | validation macro F1={scores['macro_f1']:.5f}")
        del pipeline
    return {**complete, "checkpoint_dir": str(folder)}


def run_model_safely(name, config, identity, data, model_root, *, trust_own_checkpoints=False,
                     progress=print, pipeline=None, fit=None) -> dict:
    """Shared failure/persistence handling for a visible model cell or the batch API."""
    if name not in MODEL_NAMES:
        raise ValueError("Chỉ được dùng 5 mô hình Phase 3 đã duyệt.")
    try:
        return run_model(name, config, identity, data, model_root,
                         trust_own_checkpoints=trust_own_checkpoints, progress=progress, pipeline=pipeline, fit=fit)
    except (Exception, KeyboardInterrupt) as exc:
        record = {"model": name, "status": "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                  "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc(limit=8),
                  "environment": runtime_snapshot(), "identity": identity,
                  "occurred_utc": datetime.now(timezone.utc).isoformat()}
        fitted_folder = model_root / name
        if (fitted_folder / "fit.json").is_file():
            try:
                fitted = _verify_fitted(fitted_folder, identity)
                record.update({key: fitted[key] for key in (
                    "fit_seconds", "n_retained_features", "sampled_peak_rss_mb", "warnings")})
                record["checkpoint_dir"] = str(fitted_folder)
            except (ValueError, KeyError, OSError):
                pass
        atomic_bytes(model_root / f"{name}.failure.json", json_bytes(record))
        progress(f"FAILED {name}: {record['error_type']}: {exc}")
        if isinstance(exc, KeyboardInterrupt):
            raise
        return record
    finally:
        gc.collect()


def train_models(config: dict, identity: dict, data: dict, output, *, trust_own_checkpoints=False, progress=print):
    """Yield one truthful result at a time so reports survive later failures."""
    model_root = output.models_dir / "phase3" / identity["experiment_id"]
    for name in MODEL_NAMES:
        yield run_model_safely(name, config, identity, data, model_root,
                               trust_own_checkpoints=trust_own_checkpoints, progress=progress)
