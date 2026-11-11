"""Frozen fitted-checkpoint adapter using the existing catalog and loader.

Only metadata and the explicitly selected checkpoint are needed. No raw/processed CSV,
saved test predictions or other estimator weights are opened by this adapter.
"""
from __future__ import annotations

import json
from pathlib import Path
import platform
import sys
from threading import RLock

import numpy as np
import pandas as pd
from sklearn.utils.validation import check_is_fitted
from threadpoolctl import threadpool_limits

from src.agent.extraction import Catalog
from src.data.loader import sha256_file
from src.models.ensemble import validate_probabilities
from src.models.final_evaluation import protocol, versions
from src.models.training import build_pipeline, load_fitted_checkpoint


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_ID = "lr_tuned_c2"
SCORE_LABEL = "Điểm mô hình (%)"
SCORE_NOTE = "Điểm mô hình chưa calibration; không phải xác suất mắc bệnh hoặc chẩn đoán."

# Qualification lr-windows31317-synthetic-v1: all 8x587 synthetic probabilities,
# exact labels/Top3 and artifact/source identities passed the frozen tolerances.
# Colab reference SHA-256 (confirmed by owner):
# 5fe06a3637c471403d46cdb87b2e5cce2a742e8fff1c99aa4a6cb7caef53d0dc
# This allowlist does not modify the checkpoint's original trained identity.
APPROVED_DEPLOYMENT_RUNTIMES = ({
    "system": "Windows", "machine": "AMD64", "implementation": "CPython",
    "versions": {"python": "3.13.17", "sklearn": "1.6.1", "numpy": "2.1.3",
                 "scipy": "1.16.3", "joblib": "1.6.0"},
    "trained_versions": {"python": "3.13.18", "sklearn": "1.6.1", "numpy": "2.1.3",
                         "scipy": "1.16.3", "joblib": "1.6.0"},
    "selected_identity": "tuned-v1-b8a5602679b3dc5c",
    "checkpoint_sha256": "4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6",
},)


def _runtime_compatible(checkpoint, current):
    identity = checkpoint["identity"]
    if current == identity["versions"]:
        return True  # Preserve the original, exact trained-environment path.
    return any(
        current == rule["versions"] and identity["versions"] == rule["trained_versions"]
        and identity["experiment_id"] == rule["selected_identity"]
        and checkpoint["files"]["pipeline.joblib"]["sha256"] == rule["checkpoint_sha256"]
        and platform.system() == rule["system"] and platform.machine() == rule["machine"]
        and platform.python_implementation() == rule["implementation"]
        for rule in APPROVED_DEPLOYMENT_RUNTIMES
    )


class PredictionError(ValueError):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


class ModelLoadError(PredictionError):
    pass


def _read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _check(condition, code, message):
    if not condition:
        raise ModelLoadError(code, message)


def _file(root, relative, expected=None):
    path = (root / relative).resolve()
    _check(path.is_relative_to(root), "artifact_path_invalid", "Artifact phải nằm trong storage root.")
    _check(path.is_file(), "artifact_missing", f"Thiếu artifact: {relative}")
    if expected is not None:
        _check(sha256_file(path) == expected["sha256"] and
               ("bytes" not in expected or path.stat().st_size == expected["bytes"]),
               "artifact_checksum_mismatch", f"Checksum/size sai: {relative}")
    return path


class LRPredictionService:
    """One fitted LR (or internal hard-vote member), guarded by checkpoint identity."""

    def __init__(self, model, catalog, checkpoint, tuning_experiment, model_id=MODEL_ID):
        self._model, self.catalog = model, catalog
        self._checkpoint, self._tuning_experiment = checkpoint, tuning_experiment
        self.model_id = model_id
        self._lock = RLock()
        self.verification = "NOT VERIFIED"

    @classmethod
    def load(cls, storage_root, *, project_root=PROJECT_ROOT, model_id=MODEL_ID):
        root = Path(storage_root).expanduser()
        _check(root.is_absolute() and root.is_dir(), "storage_root_invalid",
               "DISEASE_API_STORAGE_ROOT phải là thư mục tuyệt đối có artifact đã được duyệt.")
        root, source = root.resolve(), Path(project_root).resolve()
        frozen = protocol()
        _check(model_id in frozen['checkpoints'], 'unknown_model', 'Model không thuộc frozen checkpoint registry.')
        cp, ti = frozen["checkpoints"][model_id], frozen["tuning"]
        identity = cp["identity"]
        if model_id in {'lr_tuned_c2','lr_baseline'}:
            _check(identity["config"]["models"]["logistic_regression"]["C"] == (1 if model_id == 'lr_baseline' else 2),
                   "checkpoint_identity_mismatch", "C khác LR checkpoint đã khóa.")
        # Pins were frozen BEFORE test; no model choice or requirements come from test scores.
        for relative, expected in identity["source_sha256"].items():
            _file(source, relative, {"sha256": expected})
            module = sys.modules.get(relative[:-3].replace("/", "."))
            if module is not None:
                _check(Path(module.__file__).resolve() == (source / relative).resolve(),
                       "source_import_mismatch", "Module ML được import từ source khác; khởi động lại đúng project.")
        current = versions()
        _check(_runtime_compatible(cp, current), "environment_mismatch",
               f"Checkpoint cần {identity['versions']} hoặc deployment runtime đã được duyệt riêng; môi trường hiện tại {current}.")
        phase = _read(_file(root, "artifacts/metadata/phase2/dataset_manifest.json",
                            {"sha256": frozen["phase2_manifest_sha256"]}))
        _check(phase["status"] == "finalized" and phase["test_locked"] and
               phase["processed"] == frozen["processed"] and phase["files"] == frozen["phase2_files"],
               "phase2_identity_mismatch", "Phase 2 manifest khác bản đã khóa gắn với checkpoint.")
        for name in ("feature_schema.json", "label_mapping.json"):
            relative = "artifacts/metadata/phase2/" + name
            _file(root, relative, frozen["phase2_files"][relative])
        # Catalog.load verifies the full ordered feature/mapping payloads and their locked hashes.
        catalog = Catalog.load(source, root)
        _check(catalog.schema_id == phase["processed"]["schema_sha256"] and
               len(catalog.features) == 375 and len(catalog.classes) == 587,
               "catalog_mismatch", "Schema375/class order587 không hợp lệ.")
        if model_id == 'lr_baseline':
            # All baseline deployment entries are frozen individually before final test.
            manifest = {'files': {cp['folder']+'/'+name: value for name,value in cp['files'].items()}}
        else:
            manifest = _read(_file(root, f"artifacts/metadata/tuning/{ti['experiment_id']}/manifest.json",
                               {"sha256": ti["manifest_sha256"]}))
            _check(manifest["status"] == "completed" and manifest["experiment_id"] == ti["experiment_id"]
               and manifest["identity"] == identity, "checkpoint_identity_mismatch",
               "Tuning manifest khác experiment/selected identity đã duyệt.")
        # Verify only the selected deployment subset, not all five tuned models.
        for name in ("pipeline.joblib", "fit.json", "metadata.json"):
            relative = cp["folder"] + "/" + name
            _check(relative in manifest["files"], "checkpoint_manifest_incomplete", f"Manifest thiếu {relative}.")
            if name == "pipeline.joblib":
                _check(manifest["files"][relative] == cp["files"][name], "checkpoint_identity_mismatch",
                       "Pipeline khác SHA-256 đã freeze trước test.")
            _file(root, relative, manifest["files"][relative])
        folder = root / cp["folder"]
        fit, meta = _read(folder / "fit.json"), _read(folder / "metadata.json")
        pred_entry = manifest["files"].get(cp["folder"] + "/validation_predictions.npz", {})
        _check(fit["status"] == "fitted" and meta["status"] == "completed" and
               fit["identity"] == meta["identity"] == identity and
               fit["model"] == meta["model"] == cp['model'] and
               fit["n_input_features"] == 375 and
               fit["pipeline_sha256"] == meta["pipeline_sha256"] == cp["files"]["pipeline.joblib"]["sha256"] and
               meta["fit_metadata_sha256"] == sha256_file(folder / "fit.json") and
               meta["predictions_sha256"] == pred_entry.get("sha256"),
               "checkpoint_metadata_mismatch", "Fitted/completed metadata LR không nhất quán.")
        # Existing loader checks fit metadata, file hash, fitted pipeline and variance support.
        model = load_fitted_checkpoint(folder, identity, trusted=True)
        expected = build_pipeline(cp['model'], identity["config"])
        _check(model.feature_names_in_.tolist() == list(catalog.features) and
               np.issubdtype(np.asarray(model.classes_).dtype, np.integer) and
               np.array_equal(model.classes_, np.arange(587)) and
               [k for k, _ in model.steps] == [k for k, _ in expected.steps] and
               all(type(a) is type(b) and a.get_params(deep=False) == b.get_params(deep=False)
                   for (_, a), (_, b) in zip(model.steps, expected.steps)),
               "fitted_pipeline_mismatch", "Fitted schema/classes/VarianceThreshold/to_csr/LR config không khớp.")
        estimator = model.named_steps["estimator"]
        check_is_fitted(estimator)
        _check(fit['n_retained_features'] == 318 and estimator.n_features_in_ == 318,
               'fitted_pipeline_mismatch', 'Fitted estimator phải giữ đúng 318 feature.')
        if cp['model'] in {'logistic_regression','linear_svc'}:
            _check(estimator.coef_.shape == (587, fit["n_retained_features"]) and
               estimator.intercept_.shape == (587,) and
               estimator.n_features_in_ == fit["n_retained_features"] and
               np.isfinite(estimator.coef_).all() and np.isfinite(estimator.intercept_).all(),
               "fitted_pipeline_mismatch", "Fitted LR coefficients không khớp metadata.")
        service = cls(model, catalog, cp, None if model_id == 'lr_baseline' else ti["experiment_id"], model_id)
        service.verification = "REAL CHECKPOINT VERIFIED"
        return service

    def identity(self):
        return {"model_id": self.model_id, "tuning_experiment_id": self._tuning_experiment,
                "selected_checkpoint_id": self._checkpoint["identity"]["experiment_id"],
                "checkpoint_sha256": self._checkpoint["files"]["pipeline.joblib"]["sha256"],
                "schema_sha256": self.catalog.schema_id, "features": 375, "classes": 587}

    def frame_from_features(self, present_features):
        if not isinstance(present_features, list) or not present_features:
            raise PredictionError("empty_or_invalid_features", "Cần danh sách feature hiện diện không rỗng.")
        if any(not isinstance(x, str) for x in present_features):
            raise PredictionError("invalid_feature_type", "Mỗi feature phải là chuỗi tiếng Anh đúng schema.")
        if len(present_features) != len(set(present_features)):
            raise PredictionError("duplicate_features", "Không chấp nhận feature lặp.")
        unknown = sorted(set(present_features) - set(self.catalog.features))
        if unknown:
            raise PredictionError("unknown_features", "Feature ngoài schema: " + ", ".join(unknown))
        selected = set(present_features)
        return pd.DataFrame([[int(name in selected) for name in self.catalog.features]],
                            columns=self.catalog.features, dtype="uint8")

    def predict(self, frame, *, schema_sha256):
        if (schema_sha256 != self.catalog.schema_id or not isinstance(frame, pd.DataFrame) or
                frame.shape != (1, 375) or frame.columns.tolist() != list(self.catalog.features)):
            raise PredictionError("invalid_feature_frame", "Cần DataFrame 1×375 đúng schema và thứ tự.")
        values = frame.to_numpy()
        if not np.issubdtype(values.dtype, np.integer) or not np.isin(values, [0, 1]).all() or not values.any():
            raise PredictionError("invalid_binary_values", "Giá trị phải là số nguyên 0/1 và có feature hiện diện.")
        with self._lock, threadpool_limits(limits=1):
            probability = np.asarray(self._model.predict_proba(frame), dtype=np.float64)
        validate_probabilities(probability, 1, self._model.classes_, 587)
        order = np.argsort(-probability[0], kind="stable")[:3]
        return {**self.identity(), "input_present_count": int(values.sum()),
                "score_label": SCORE_LABEL, "calibrated": False, "note": SCORE_NOTE,
                "top3": [{"rank": rank, "class_id": int(k), "label": self.catalog.classes[k],
                          "score_percent": float(probability[0, k] * 100)}
                         for rank, k in enumerate(order, 1)]}
