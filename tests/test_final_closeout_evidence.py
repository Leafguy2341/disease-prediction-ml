"""Verify the received read-only Colab evidence, never the test CSV or models."""
import hashlib
import json
from pathlib import Path

from src.models.final_evaluation import digest, protocol


PROJECT = Path(__file__).resolve().parents[1]


def test_closeout_packet_is_bound_to_frozen_protocol_checkpoints_and_original_metrics():
    path = PROJECT / "artifacts/metadata/final_evaluation_audit/colab_evidence.json"
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "102845056236bfe3855962cd1717ece4402a958cc6ce593540ab1ccab4f34131"
    packet, frozen = json.loads(raw), protocol()
    assert packet["status"] == "PASS" and not any(packet["guards"].values())
    assert not packet["test_csv_opened"] and not packet["prediction_called"] and packet["models_fitted"] == 0
    assert packet["manifest_sha256"] == "f1ad195e1e46154d7a29a421e80387bfa76e494f4df771cede240f882d0b754a"
    manifest, results = packet["manifest"], packet["results"]
    assert manifest["status"] == "completed" and manifest["protocol_sha256"] == digest(frozen)
    assert results["metrics"] == manifest["metrics"]
    assert results["records"] == 28066 and results["groups"] == 25128 and results["labels"] == 587
    assert results["missing_label_ids"] == [] and results["test_loader_calls"] == 1
    assert results["deployment_candidate"] == "lr_tuned_c2" and not results["model_selection_from_test"]
    assert set(packet["recalculated"]) == set(frozen["candidates"])
    for key, cp in frozen["checkpoints"].items():
        assert packet["checkpoints"][key] == cp["files"]
        assert manifest["versions"] == cp["identity"]["versions"]
    for row in results["metrics"]:
        if row["split"] == "test":
            assert all(row[k] == value for k, value in packet["recalculated"][row["candidate"]].items())


def test_source_handover_allowlist_includes_local_api_and_requirements_without_building_archive():
    import runpy
    api = runpy.run_path(str(PROJECT / "scripts/package_handover.py"))
    files = api["code_files"](PROJECT)
    assert {"requirements-api.txt", "app/backend/main.py", "app/backend/prediction.py", "app/backend/schemas.py"} <= set(files)
