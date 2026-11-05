"""Read-only audit primitives; synthetic artifacts, no model fitting or inference."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import socket
from types import SimpleNamespace

import numpy as np
import pytest

from src.models.ensemble import IntegrityError, phase4_guard
from src.models.runtime import read_training_config
from src.models.training import experiment_identity

ROOT = Path(__file__).resolve().parents[1]
API = runpy.run_path(str(ROOT / "scripts/audit_post_tuning.py"))


@pytest.fixture(autouse=True)
def no_learning_or_locked_test():
    with phase4_guard(ROOT) as guards:
        yield
    assert not any(guards.values())


def test_actual_class_counts_use_saved_groups_and_keep_missing_classes():
    y = np.array([0, 1, 0, 2, 0, 1, 2])
    groups = np.arange(7)
    folds = np.array([0, 0, 1, 1, 2, 2, 2], dtype=np.int8)
    result = API["cv_inventory"](y, groups, folds, 3)
    assert [r["missing_train_classes"] for r in result] == [[], [], []]
    assert [r["missing_holdout_classes"] for r in result] == [[2], [1], []]
    assert [3 - len(r["missing_holdout_classes"]) for r in result] == [2, 2, 3]


@pytest.mark.parametrize("damage", ["leakage", "alignment", "fold_count"])
def test_invalid_cv_is_blocked(damage):
    y = np.array([0, 1, 0, 2, 0, 1, 2]); groups = np.arange(7)
    folds = np.array([0, 0, 1, 1, 2, 2, 2], dtype=np.int8)
    if damage == "leakage": groups[-1] = groups[0]
    elif damage == "alignment": groups = groups[:-1]
    else: folds[-1] = 3
    with pytest.raises(IntegrityError): API["cv_inventory"](y, groups, folds, 3)


def test_read_only_guard_blocks_writes_and_network(tmp_path):
    with API["read_only"](tmp_path) as guards:
        with pytest.raises(IntegrityError, match="writes"):
            (tmp_path / "must-not-exist").write_text("not allowed")
        with pytest.raises(IntegrityError, match="network"):
            socket.create_connection(("example.invalid", 443))
    assert guards["read_only_write_attempts"] == guards["network_attempts"] == 1
    assert not (tmp_path / "must-not-exist").exists()


def test_bundle_hashes_are_checked_and_unexpected_test_path_rejected(tmp_path):
    p = tmp_path / "unit.json"; p.write_bytes(b'{}')
    manifest = {"files": {"unit.json": {"bytes": 2, "sha256": hashlib.sha256(b'{}').hexdigest()}}}
    API["verify_bundle"](tmp_path, manifest, {"unit.json"})
    p.write_bytes(b'[]')
    with pytest.raises(IntegrityError, match="checksum"):
        API["verify_bundle"](tmp_path, manifest, {"unit.json"})
    bad = {"files": {"data/processed/test.csv.gz": {"bytes": 0, "sha256": "0" * 64}}}
    with pytest.raises(IntegrityError, match="artifact paths"):
        API["verify_bundle"](tmp_path, bad, {"unit.json"})


def test_trial_warning_failure_and_resume_evidence_are_truthful():
    trials = [{"model": "unit", "candidate": 0, "parameters": {}, "attempts": [
        {"fold": 0, "status": "interrupted", "error_type": "KeyboardInterrupt", "elapsed_seconds": .1, "warnings": []},
        {"fold": 0, "status": "completed", "elapsed_seconds": .2, "warnings": ["ConvergenceWarning: unit-only"]},
        {"fold": 1, "status": "failed", "error_type": "ValueError", "error": "unit-only", "elapsed_seconds": .3, "warnings": []}]}]
    result = API["trial_summary"](trials)
    assert result["convergence_warning_count"] == 1
    assert len(result["failed_attempts"]) == len(result["interrupted_attempts"]) == 1
    assert result["candidates"][0]["attempt_count"] == 3
    assert result["candidates"][0]["elapsed_seconds"] == pytest.approx(.6)


def test_emit_packet_is_memory_only_and_round_trips(capsys):
    import base64, gzip
    API["emit_packet"]({"status": "NOT VERIFIED", "unit": True})
    lines = capsys.readouterr().out.splitlines()
    raw = gzip.decompress(base64.b64decode(lines[1].split("=", 1)[1]))
    assert hashlib.sha256(raw).hexdigest() == lines[0].split("=", 1)[1]
    assert json.loads(raw) == {"status": "NOT VERIFIED", "unit": True}


def test_audit_never_calls_training_prediction_export_or_new_runtime():
    tree = ast.parse((ROOT / "scripts/audit_post_tuning.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            assert name not in {"fit", "fit_transform", "partial_fit", "predict", "predict_proba", "run_tuning",
                                "train", "train_model", "save_phase4", "evaluate_tuned_ensemble", "bootstrap_runtime"}


def test_checkpoint_identity_rejects_changed_hyperparameters_before_any_load():
    manifest_path = ROOT / "artifacts/metadata/phase2/dataset_manifest.json"
    inputs = {"manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
              "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
    config = read_training_config(ROOT)
    identity = experiment_identity(ROOT, config, inputs)
    API["_check_identity"](identity, config, inputs, ROOT)
    changed = deepcopy(identity)
    changed["config"]["models"]["logistic_regression"]["C"] = 999
    with pytest.raises(IntegrityError, match="identity digest"):
        API["_check_identity"](changed, config, inputs, ROOT)


def test_missing_drive_artifacts_return_not_verified_without_creating_anything(tmp_path):
    session = SimpleNamespace(paths=SimpleNamespace(storage_root=tmp_path, project_root=ROOT))
    result = API["audit_post_tuning"](session)
    assert result["status"] == "NOT VERIFIED"
    assert not any(result["guards"].values())
    assert list(tmp_path.iterdir()) == []
