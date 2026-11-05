"""Offline HTTP/loader mechanics with synthetic artifacts and a prediction double.

No estimator is fitted or serialized. Opaque fixture bytes are never deserialized.
These tests do not verify actual project weights or clinical prediction quality.
"""
from copy import deepcopy
import io
import json
from pathlib import Path
import socket

from fastapi.testclient import TestClient
import numpy as np
import pandas as pd
import pytest

from app.backend import prediction as service_module
from app.backend.main import create_app
from app.backend.prediction import LRPredictionService, ModelLoadError, PredictionError
from app.backend.schemas import PredictRequest, PredictResponse
from src.models.ensemble import phase4_guard
from src.models.training import json_bytes


PROJECT = Path(__file__).resolve().parents[1]


def test_qualified_windows_runtime_and_original_runtime(monkeypatch):
    checkpoint = service_module.protocol()["checkpoints"]["lr_tuned_c2"]
    original = deepcopy(checkpoint["identity"]["versions"])
    candidate = {**original, "python": "3.13.17"}
    monkeypatch.setattr(service_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(service_module.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(service_module.platform, "python_implementation", lambda: "CPython")
    assert service_module._runtime_compatible(checkpoint, original)
    assert service_module._runtime_compatible(checkpoint, candidate)
    assert checkpoint["identity"]["versions"] == original  # Never rewrite training provenance.
    monkeypatch.setattr(service_module.platform, "system", lambda: "Linux")
    assert service_module._runtime_compatible(checkpoint, original)
    assert not service_module._runtime_compatible(checkpoint, candidate)


@pytest.mark.parametrize("fault", [
    "python", "sklearn", "numpy", "scipy", "joblib", "extra_version", "system",
    "machine", "implementation", "checkpoint_hash", "selected_identity", "trained_identity",
])
def test_runtime_exception_is_scoped_to_qualified_identity(monkeypatch, fault):
    checkpoint = service_module.protocol()["checkpoints"]["lr_tuned_c2"]
    candidate = {**checkpoint["identity"]["versions"], "python": "3.13.17"}
    monkeypatch.setattr(service_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(service_module.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(service_module.platform, "python_implementation", lambda: "CPython")
    if fault in candidate:
        candidate[fault] = "unqualified-version"
    if fault == "extra_version": candidate["extra"] = "1.0"
    if fault == "system": monkeypatch.setattr(service_module.platform, "system", lambda: "Darwin")
    if fault == "machine": monkeypatch.setattr(service_module.platform, "machine", lambda: "ARM64")
    if fault == "implementation": monkeypatch.setattr(service_module.platform, "python_implementation", lambda: "PyPy")
    if fault == "checkpoint_hash": checkpoint["files"]["pipeline.joblib"]["sha256"] = "0" * 64
    if fault == "selected_identity": checkpoint["identity"]["experiment_id"] = "another-checkpoint"
    if fault == "trained_identity": checkpoint["identity"]["versions"]["python"] = "3.13.16"
    assert not service_module._runtime_compatible(checkpoint, candidate)


@pytest.fixture(autouse=True)
def no_network_fit_or_test(monkeypatch):
    def reject(*a, **kw):
        raise AssertionError("API tests cannot call external services")
    monkeypatch.setattr(socket, "create_connection", reject)
    original = Path.stat
    def no_test_stat(path, *a, **kw):
        assert path.name != "test.csv.gz", "API must not even stat the locked test"
        return original(path, *a, **kw)
    monkeypatch.setattr(Path, "stat", no_test_stat)
    with phase4_guard(PROJECT) as counts:
        yield
    assert not any(counts.values()), counts


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    root = tmp_path / "synthetic-deployment"
    frozen = service_module.protocol()
    def write(name, value):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        return {"sha256": service_module.sha256_file(path), "bytes": path.stat().st_size}
    schema = json.loads((PROJECT / "artifacts/metadata/phase2/feature_schema.json").read_text())
    labels = json.loads((PROJECT / "artifacts/metadata/phase2/label_mapping.json").read_text())
    for name in ("feature_schema.json", "label_mapping.json"):
        original = PROJECT / "artifacts/metadata/phase2" / name
        write("artifacts/metadata/phase2/" + name, original.read_bytes())
    phase = {"status": "finalized", "test_locked": True, "processed": frozen["processed"], "files": frozen["phase2_files"]}
    frozen["phase2_manifest_sha256"] = write("artifacts/metadata/phase2/dataset_manifest.json", json_bytes(phase))["sha256"]
    cp = frozen["checkpoints"]["lr_tuned_c2"]
    identity = cp["identity"]
    # Preserve exact source pins, IDs and selected config; only fixture artifact hashes differ.
    identity["versions"] = service_module.versions()
    identity["phase2_manifest_sha256"] = frozen["phase2_manifest_sha256"]
    prefix = cp["folder"] + "/"
    pipeline = write(prefix + "pipeline.joblib", b"SYNTHETIC OPAQUE BYTES; NOT A MODEL")
    cp["files"] = {"pipeline.joblib": pipeline}
    fit = {"status": "fitted", "identity": identity, "model": "logistic_regression", "n_input_features": 375,
           "n_retained_features": 318, "pipeline_sha256": pipeline["sha256"]}
    fit_entry = write(prefix + "fit.json", json_bytes(fit))
    meta = {**fit, "status": "completed", "fit_metadata_sha256": fit_entry["sha256"], "predictions_sha256": "0" * 64}
    meta_entry = write(prefix + "metadata.json", json_bytes(meta))
    manifest = {"status": "completed", "experiment_id": frozen["tuning"]["experiment_id"], "identity": identity,
                "files": {prefix + "pipeline.joblib": pipeline, prefix + "fit.json": fit_entry,
                          prefix + "metadata.json": meta_entry, prefix + "validation_predictions.npz": {"sha256": "0" * 64, "bytes": 0}}}
    frozen["tuning"]["manifest_sha256"] = write("artifacts/metadata/tuning/" + frozen["tuning"]["experiment_id"] + "/manifest.json", json_bytes(manifest))["sha256"]
    monkeypatch.setattr(service_module, "protocol", lambda: deepcopy(frozen))
    class PredictionDouble:
        def __init__(self):
            self.feature_names_in_ = np.asarray(schema["features"])
            self.classes_ = np.arange(587)
            self.steps = service_module.build_pipeline("logistic_regression", identity["config"]).steps
            self.named_steps = dict(self.steps)
            estimator = self.named_steps["estimator"]
            estimator.coef_ = np.zeros((587, 318))
            estimator.intercept_ = np.zeros(587)
            estimator.classes_ = self.classes_
            estimator.n_features_in_ = 318
            self.calls = []
            self.output = np.zeros((1, 587))
            self.output[0, :6] = [.4, .3, .1, .08, .07, .05]
        def predict_proba(self, frame):
            self.calls.append(frame.copy(deep=True))
            return self.output.copy()
    model = PredictionDouble()
    loads = []
    def loader(folder, identity, *, trusted):
        assert folder == root / cp["folder"] and trusted
        loads.append(folder)
        return model
    monkeypatch.setattr(service_module, "load_fitted_checkpoint", loader)
    return root, frozen, model, loads


def get_service(deployment):
    root, _, _, _ = deployment
    service = LRPredictionService.load(root)
    service.verification = "NOT VERIFIED (synthetic fixture)"
    return service


def test_http_top3_keeps_real_double_scores_and_loads_once(deployment):
    service = get_service(deployment)
    starts = []
    def start():
        starts.append(1)
        return service
    with TestClient(create_app(service_loader=start)) as client:
        assert client.get("/health").status_code == 200
        assert "synthetic" in client.get("/health").json()["checkpoint_status"]
        for _ in range(2):
            response = client.post("/api/v1/predict", json={"present_features": list(service.catalog.features[:2])})
            assert response.status_code == 200, response.text
            body = response.json()
            assert [r["score_percent"] for r in body["top3"]] == [40, 30, 10]
            assert sum(r["score_percent"] for r in body["top3"]) == 80
            assert [r["label"] for r in body["top3"]] == list(service.catalog.classes[:3])
            assert body["score_label"] == "Điểm mô hình (%)" and not body["calibrated"]
            assert PredictResponse.model_validate(body)
        assert {"/health", "/api/v1/predict"} <= set(client.get("/openapi.json").json()["paths"])
        assert client.get("/docs").status_code == 200
    assert len(starts) == len(deployment[3]) == 1
    assert len(deployment[2].calls) == 2


@pytest.mark.parametrize("payload", [None, {}, {"present_features": []}, {"present_features": "cough"},
    {"present_features": [1]}, {"present_features": [True]}, {"present_features": [None]},
    {"present_features": ["", "cough"]}, {"present_features": ["cough", "cough"]},
    {"present_features": ["cough"], "model": "baseline"}, {"present_features": ["x"] * 376}])
def test_strict_request_rejects_invalid_json_contract_before_model(deployment, payload):
    service = get_service(deployment)
    with TestClient(create_app(service_loader=lambda: service)) as client:
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422 and response.json()["error"]["code"] == "input_validation_error"
    assert not deployment[2].calls


def test_unknown_feature_and_malformed_json_are_json_errors(deployment):
    service = get_service(deployment)
    with TestClient(create_app(service_loader=lambda: service)) as client:
        r = client.post("/api/v1/predict", json={"present_features": ["NOT_A_FEATURE"]})
        assert r.status_code == 422 and r.json()["error"]["code"] == "unknown_features"
        r = client.post("/api/v1/predict", content="{broken", headers={"Content-Type": "application/json"})
        assert r.status_code == 422 and "error" in r.json()
        assert client.get("/does-not-exist").json()["error"]["code"] == "http_error"
    assert not deployment[2].calls


def test_frame_order_binary_shape_and_schema_checks_precede_prediction(deployment):
    service = get_service(deployment)
    frame = service.frame_from_features(list(reversed(service.catalog.features[:2])))
    assert frame.columns.tolist() == list(service.catalog.features)
    assert frame.shape == (1, 375) and frame.iloc[0, :2].tolist() == [1, 1]
    assert frame.to_numpy().dtype == np.uint8
    for bad in (frame[frame.columns[::-1]], frame.iloc[:, :-1], pd.concat([frame, frame]), frame.astype(float)):
        with pytest.raises(PredictionError):
            service.predict(bad, schema_sha256=service.catalog.schema_id)
    bad = frame.copy(); bad.iloc[0, 0] = 2
    with pytest.raises(PredictionError):
        service.predict(bad, schema_sha256=service.catalog.schema_id)
    with pytest.raises(PredictionError):
        service.predict(frame, schema_sha256="wrong")
    assert not deployment[2].calls


@pytest.mark.parametrize("fault", ["nan", "wrong_shape", "unnormalized", "negative"])
def test_invalid_probability_never_returns_top3(deployment, fault):
    service = get_service(deployment)
    output = deployment[2].output
    if fault == "nan": output[0, 0] = np.nan
    if fault == "wrong_shape": deployment[2].output = output[:, :-1]
    if fault == "unnormalized": output[0, 0] = .5
    if fault == "negative": output[0, 0] = -.1
    with TestClient(create_app(service_loader=lambda: service)) as client:
        r = client.post("/api/v1/predict", json={"present_features": [service.catalog.features[0]]})
        assert r.status_code == 500 and r.json()["error"]["code"] == "prediction_failed"
        assert "top3" not in r.json()


@pytest.mark.parametrize("fault", ["environment", "weights", "schema", "class_order", "parameters", "csr"])
def test_loader_fails_closed_before_ready_and_never_uses_baseline(deployment, monkeypatch, fault):
    root, frozen, model, loads = deployment
    if fault == "environment": monkeypatch.setattr(service_module, "versions", lambda: {})
    if fault == "weights": (root / frozen["checkpoints"]["lr_tuned_c2"]["folder"] / "pipeline.joblib").write_bytes(b"CORRUPT SYNTHETIC")
    if fault == "schema": (root / "artifacts/metadata/phase2/feature_schema.json").write_bytes(b"{}")
    if fault == "class_order": model.classes_ = model.classes_[::-1]
    if fault == "parameters": model.named_steps["estimator"].C = 1
    if fault == "csr": model.named_steps["csr"].func = lambda x: x
    with TestClient(create_app(service_loader=lambda: LRPredictionService.load(root))) as client:
        r = client.get("/health")
        assert r.status_code == 503 and r.json()["checkpoint_status"] == "NOT VERIFIED"
        assert client.post("/api/v1/predict", json={"present_features": ["cough"]}).status_code == 503
    assert all(str(p).endswith("logistic_regression") for p in loads)
    assert len(loads) <= 1 and not model.calls


def test_missing_tuned_weights_and_unconfigured_storage_have_no_fallback(tmp_path, monkeypatch):
    with pytest.raises(ModelLoadError):
        LRPredictionService.load(tmp_path / "absent")
    monkeypatch.delenv("DISEASE_API_STORAGE_ROOT", raising=False)
    with TestClient(create_app()) as client:
        r = client.get("/health")
        assert r.status_code == 503 and r.json()["error"]["code"] == "storage_not_configured"


def test_tie_uses_fixed_class_order(deployment):
    service = get_service(deployment)
    deployment[2].output[0, :6] = [.3, .3, .1, .1, .1, .1]
    result = service.predict(service.frame_from_features([service.catalog.features[0]]), schema_sha256=service.catalog.schema_id)
    assert [v["class_id"] for v in result["top3"]] == [0, 1, 2]
