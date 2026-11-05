"""Code-only/offline acceptance tests. No project dataset/checkpoint/LLM access."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
API = runpy.run_path(str(ROOT / "scripts/package_handover.py"))


@pytest.fixture
def code_tree(tmp_path):
    root = tmp_path / "local-code"
    for name, source in API["code_files"](ROOT).items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return root


def test_allowlist_has_no_original_artifacts_and_has_all_runtime_dependencies():
    files = API["code_files"](ROOT)
    assert "notebooks/03_model_training.ipynb" in files
    assert "scripts/audit_final_ml_gaps.py" in files
    assert "app/frontend/.gitkeep" in files and "app/backend/.gitkeep" in files
    assert "configs/phase5b.json" in files
    assert not any(n.startswith(("artifacts/models/", "dist/", ".venv/", ".venv-web/")) for n in files)
    assert "artifacts/metadata/runtime_compatibility/lr-31318-synthetic-reference.json" in files
    assert "configs/runtime.local.example.json" in files
    assert all(n.endswith(".json") for n in files if n.startswith("artifacts/"))
    supplements = API["code_supplements"](ROOT)
    assert set(supplements) <= set(files)
    assert all(n.endswith(".md") or n in supplements for n in files if n.startswith("reports/"))
    assert not any(n.endswith((".csv", ".gz", ".joblib", ".pyc", ".env")) for n in files if n not in supplements)
    assert all(API["entry"](files[n]) == expected for n, expected in supplements.items())
    payloads, publication = API["runtime_api"](ROOT)["make_publication"](ROOT)
    assert set(payloads) == set(publication["files"]) | {"configs/runtime.json"}
    assert all({"sha256": hashlib.sha256(payloads[name]).hexdigest(), "bytes": len(payloads[name])} == expected
               for name, expected in publication["files"].items())
    assert json.loads(payloads["configs/runtime.json"])["runtime_publication"] == publication
    assert "configs/phase5b.json" in payloads and "scripts/audit_post_tuning.py" in payloads
    assert not any(n.startswith(("data/", "artifacts/", "reports/")) for n in payloads)
    assert len(publication["sha256"]) == 64


def test_secret_scanner_blocks_actual_key_shape_without_echoing_value():
    fake_key = ("AIza" + "x" * 35).encode()
    with pytest.raises(ValueError, match="credential") as error:
        API["secret_check"]("configs/synthetic.json", fake_key)
    assert fake_key.decode() not in str(error.value)


def test_supplement_policy_matches_the_approved_release_digest():
    policy = API["read"](ROOT / "configs/handover_code_supplements.json")
    supplements = API["code_supplements"](ROOT)
    # The original release inventory is an external control receipt, not a new
    # runtime/test dependency. The pinned policy carries its exact approved list.
    assert policy["approved_inventory_sha256"] == "b500d305e0d7c9645ca118254d83ada559e7eccf04d9201dcc562e38eaa541fb"
    assert supplements == policy["files"]


def test_supplement_tamper_blocks_and_unreviewed_data_stays_excluded(code_tree):
    files = API["code_files"](code_tree)
    for name in ("reports/terminology/unreviewed.csv", "data/raw/unreviewed.csv", "artifacts/models/unreviewed.joblib", ".env"):
        target = code_tree / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"UNAPPROVED SYNTHETIC FILE")
    assert set(API["code_files"](code_tree)) == set(files)
    target = code_tree / "reports/terminology/symptom_dictionary_review.csv"
    target.write_bytes(target.read_bytes() + b"\nTAMPERED SYNTHETIC FIXTURE\n")
    with pytest.raises(ValueError, match="Code supplement identity mismatch"):
        API["code_files"](code_tree)


def test_supplement_policy_tamper_fails_before_selection(code_tree):
    policy = code_tree / "configs/handover_code_supplements.json"
    policy.write_bytes(policy.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Code supplement contract changed"):
        API["code_files"](code_tree)


def test_stage_is_immutable_and_source_only(code_tree):
    first = API["stage"](code_tree)
    second = API["stage"](code_tree, check_only=True)
    assert first["runtime_payload_sha256"] == second["runtime_payload_sha256"]
    target = Path(first["folder"])
    assert not (target / "data").exists() and not (target / "artifacts").exists()
    (target / "scripts/audit_post_tuning.py").write_bytes(b"TAMPERED SYNTHETIC")
    with pytest.raises(ValueError, match="Immutable"):
        API["stage"](code_tree)


def test_partial_publication_and_wrong_local_digest_fail_closed(code_tree):
    staged = API["stage"](code_tree)
    api = API["runtime_api"](code_tree)
    dest = Path(staged["folder"])
    with pytest.raises(ValueError, match="STALE"):
        api["read_source"](dest, 3, expected_payload_sha256="0" * 64)
    (dest / "scripts/audit_final_ml_gaps.py").write_bytes(b"# mixed source\n")
    with pytest.raises(ValueError, match="MISMATCH"):
        api["read_source"](dest, 3, expected_payload_sha256=staged["runtime_payload_sha256"])


def test_publication_does_not_touch_data_or_locked_manifest(code_tree, tmp_path):
    drive = tmp_path / "Drive-desktop/MyDrive/ML_Projects/disease-prediction-ml"
    metadata = drive / "artifacts/metadata/phase2/dataset_manifest.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_bytes(b"SYNTHETIC APPROVED METADATA")
    baseline = json.loads((code_tree / "configs/phase2_integrity.json").read_text())
    baseline["approved_manifest_sha256"] = [API["sha"](metadata)]
    (code_tree / "configs/phase2_integrity.json").write_bytes(API["encoded"](baseline))
    protected = drive / "data/processed/test.csv.gz"
    protected.parent.mkdir(parents=True)
    protected.write_bytes(b"SYNTHETIC LOCKED BYTES; NEVER OPEN DURING PUBLISH")
    before = metadata.read_bytes(), metadata.stat().st_mtime_ns, protected.stat().st_mtime_ns
    original_open = Path.open
    def guarded_open(path, *args, **kwargs):
        assert path.name != "test.csv.gz", "Publisher must not open any locked payload"
        return original_open(path, *args, **kwargs)
    from unittest.mock import patch
    with patch.object(Path, "open", guarded_open):
        result = API["publish"](code_tree, drive)
    assert result["cloud_verified"] is False
    assert "CLOUD_ACK_PENDING" in result["status"]
    assert (metadata.read_bytes(), metadata.stat().st_mtime_ns, protected.stat().st_mtime_ns) == before
    assert (drive / "scripts/audit_post_tuning.py").read_bytes() == (code_tree / "scripts/audit_post_tuning.py").read_bytes()


def test_wrong_destination_has_zero_writes(code_tree, tmp_path):
    target = tmp_path / "wrong-root"
    target.mkdir()
    with pytest.raises(ValueError):
        API["publish"](code_tree, target)
    assert list(target.iterdir()) == []


@pytest.mark.parametrize("missing", [None, "", "abc"])
def test_extraction_requires_trusted_archive_digest_before_io(missing, tmp_path):
    with pytest.raises(ValueError, match="trusted"):
        API["extract"](tmp_path / "nonexistent.zip", tmp_path / "output", missing)
    assert not (tmp_path / "output").exists()


def test_code_zip_exact_roundtrip_and_imports(code_tree, tmp_path):
    result = API["package_code"](code_tree, tmp_path / "release")
    folder = Path(result["code"]["extraction_check"])
    verified = API["verify_archive"](result["code"]["path"], expected_sha256=result["code"]["sha256"])
    assert verified["kind"] == "code"
    for name in ("03_model_training", "04_ensemble", "05_structured_inference_check"):
        relative = f"notebooks/{name}.ipynb"
        assert (folder / relative).read_bytes() == (code_tree / relative).read_bytes()
    process = subprocess.run([sys.executable, "-B", "-c", "import src.data.colab_runtime,src.models.notebook,src.agent.extraction; print('IMPORTS ONLY PASS')"],
                             cwd=folder, text=True, capture_output=True)
    assert process.returncode == 0, process.stderr
    assert "IMPORTS ONLY PASS" in process.stdout
    assert not (folder / "artifacts/models").exists()


@pytest.mark.parametrize("bad", ["../outside", "/absolute", "C:/absolute", "x\\y", "a/../b", "a//b"])
def test_unsafe_archive_paths_fail_before_writes(bad, tmp_path):
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(bad, "SYNTHETIC")
    with pytest.raises(ValueError):
        API["extract"](archive_path, tmp_path / "output", API["sha"](archive_path))
    assert not (tmp_path / "output").exists()


def test_extraction_never_overwrites_different_existing_file(code_tree, tmp_path):
    result = API["package_code"](code_tree, tmp_path / "release")
    output = tmp_path / "extract"
    conflict = output / "disease-prediction-ml/README.md"
    conflict.parent.mkdir(parents=True)
    conflict.write_bytes(b"USER FILE MUST SURVIVE")
    with pytest.raises(ValueError, match="NOT overwritten"):
        API["extract"](result["code"]["path"], output, result["code"]["sha256"])
    assert conflict.read_bytes() == b"USER FILE MUST SURVIVE"
    assert not (conflict.parent / "src").exists()


def test_data_plan_never_opens_test_and_incomplete_data_cannot_create_archive(tmp_path):
    output = tmp_path / "plan.json"
    result = API["data_plan"](ROOT, tmp_path / "absent-Drive", output)
    assert result["status"] == "NOT VERIFIED" and not result["data_zip_created"]
    with pytest.raises(ValueError):
        API["package_data"](ROOT, tmp_path / "absent-Drive", tmp_path / "release", allow_locked_bytes=True)
    assert not (tmp_path / "release").exists()
    with pytest.raises(ValueError, match="allow-locked"):
        API["package_data"](ROOT, ROOT)


def test_fresh_runtime_imports_scripts_and_recreates_session_without_fit(code_tree, tmp_path):
    content = tmp_path / "content"
    drive = content / "drive/MyDrive/ML_Projects/disease-prediction-ml"
    settings_file = code_tree / "configs/runtime.json"
    settings = json.loads(settings_file.read_text())
    settings["colab"].update(drive_mount=str(content / "drive"), ephemeral_root=str(content),
                             runtime_workspace=str(content / "workspace"), cache_dir=str(content / "cache"))
    settings_file.write_bytes(API["encoded"](settings))
    payloads, pub = API["runtime_api"](code_tree)["make_publication"](code_tree)
    for name, payload in payloads.items():
        target = drive / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    source = f'''import runpy,sys,json
from pathlib import Path
from unittest.mock import patch
root=Path({str(drive)!r})
api=runpy.run_path(str(root/'src/data/colab_runtime.py'))
api['bootstrap_runtime'].__globals__['is_colab']=lambda: True
r=api['bootstrap_runtime'](root,phase=3,expected_payload_sha256={pub['sha256']!r})
assert r.inputs is None and r.paths.storage_root==root
assert (r.paths.project_root/'scripts/audit_post_tuning.py').is_file()
from src.models.notebook import ColabTraining
import src.models.notebook as n
config=json.loads((r.paths.project_root/'configs/phase3.json').read_text())
fixture={{'manifest':{{'processed':config['expected_phase2']}}}}
env={{'ram_available_gb':8,'cpu':'SYNTHETIC','gpu':[],'sklearn':'SYNTHETIC'}}
with patch.object(n,'phase2_preflight',return_value=fixture),patch.object(n,'phase3_resources',return_value=env),patch.object(n,'display'),patch.object(ColabTraining,'train',side_effect=AssertionError('FIT FORBIDDEN')):
 s=ColabTraining.open(r)
 assert s.data is None and s.identity is None
assert not (root/'data').exists()
print('FRESH SESSION PASS; MOCK ONLY')
'''
    for _ in range(2):  # Separate processes model a restarted kernel, no persisted Python session.
        process = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", source], cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
        assert process.returncode == 0, process.stderr
        assert "FRESH SESSION PASS" in process.stdout


def synthetic_data_tree(tmp_path):
    """Opaque dummy bytes, NOT serialized/fitted models and never project artifacts."""
    root, storage = tmp_path / "synthetic-code", tmp_path / "synthetic-Drive"
    def write(name, payload):
        path = storage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return API["entry"](path)
    ids = {"phase3": {"fixture": "baseline"}, "tuning": {"fixture": "tuned"}}
    baseline_files = {}
    for kind, experiment in [("phase3", "baseline-fixture"), ("tuning", "tuned-fixture")]:
        prefix = f"artifacts/models/{kind}/{experiment}/logistic_regression/"
        pipeline = write(prefix + "pipeline.joblib", b"SYNTHETIC OPAQUE BYTES; NOT A MODEL")
        fitted = {"status": "fitted", "identity": ids[kind], "pipeline_sha256": pipeline["sha256"]}
        fit_entry = write(prefix + "fit.json", API["encoded"](fitted))
        predictions = write(prefix + "validation_predictions.npz", b"SYNTHETIC; NOT AN ARRAY")
        meta = {"status": "completed", "identity": ids[kind], "fit_metadata_sha256": fit_entry["sha256"], "predictions_sha256": predictions["sha256"]}
        metadata = write(prefix + "metadata.json", API["encoded"](meta))
        if kind == "phase3":
            baseline_files = {prefix + name: value for name, value in [("pipeline.joblib", pipeline), ("fit.json", fit_entry),
                             ("metadata.json", metadata), ("validation_predictions.npz", predictions)]}
    test = write("data/processed/test.csv.gz", b"SYNTHETIC OPAQUE LOCKED BYTES; MUST NOT PARSE")
    manifest = {"status": "finalized", "test_locked": True, "processed": {"synthetic": True}, "files": {"data/processed/test.csv.gz": test}}
    phase2 = write("artifacts/metadata/phase2/dataset_manifest.json", API["encoded"](manifest))
    raw = write("data/raw/fixture.csv", b"SYNTHETIC RAW; MUST NOT PARSE")
    ev = write("artifacts/metadata/fixture_evidence.json", b'{"synthetic":true}\n')
    bundle = {"files": baseline_files}
    bundle_path = "artifacts/metadata/fixture_bundle.json"
    be = write(bundle_path, API["encoded"](bundle))
    req = {"phase2_manifest_sha256": phase2["sha256"], "phase2_files": manifest["files"], "processed": manifest["processed"],
           "raw": {**raw, "filename": "fixture.csv"}, "baseline_files": baseline_files, "baseline_id": "baseline-fixture",
           "tuning_id": "tuned-fixture", "baseline_identity": ids["phase3"], "tuned_identity": ids["tuning"],
           "model_names": ["logistic_regression"], "evidence_files": {"artifacts/metadata/fixture_evidence.json": ev},
           "manifests": {bundle_path: be["sha256"]}}
    (root / "configs").mkdir(parents=True)
    (root / "configs/handover_data_requirements.json").write_bytes(API["encoded"](req))
    return root, storage


def test_complete_synthetic_data_zip_preserves_bytes_and_requires_extraction_gate(tmp_path, monkeypatch):
    monkeypatch.setitem(API["package_data"].__globals__, "_requirements", lambda root: API["read"](Path(root) / "configs/handover_data_requirements.json"))
    root, storage = synthetic_data_tree(tmp_path)
    before = {p.relative_to(storage).as_posix(): API["entry"](p) for p in storage.rglob('*') if p.is_file()}
    result = API["package_data"](root, storage, tmp_path / "release", allow_locked_bytes=True)
    assert result["status"] == "VERIFIED" and result["test_evaluated"] is False
    with pytest.raises(ValueError, match="allow-locked"):
        API["extract"](result["path"], tmp_path / "unpack", result["sha256"])
    API["extract"](result["path"], tmp_path / "unpack", result["sha256"], allow_locked_bytes=True)
    for name, expected in before.items():
        assert API["entry"](tmp_path / "unpack" / name) == expected
        assert API["entry"](storage / name) == expected


def test_data_variant_or_checkpoint_tamper_blocks_archive_creation(tmp_path, monkeypatch):
    monkeypatch.setitem(API["package_data"].__globals__, "_requirements", lambda root: API["read"](Path(root) / "configs/handover_data_requirements.json"))
    root, storage = synthetic_data_tree(tmp_path)
    (storage / "artifacts/metadata/phase2/dataset_manifest.json").write_bytes(b"DIFFERENT VARIANT")
    with pytest.raises(ValueError, match="mismatch"):
        API["package_data"](root, storage, tmp_path / "release", allow_locked_bytes=True)
    assert not (tmp_path / "release").exists()


def test_external_code_deliverable_is_verified_and_never_silently_replaced(code_tree, tmp_path):
    archive = tmp_path / "project-code.zip"
    first = API["package_code"](code_tree, tmp_path / "receipt1", archive_destination=archive)
    original = archive.read_bytes()
    again = API["package_code"](code_tree, tmp_path / "receipt2", archive_destination=archive)
    assert first["code"]["sha256"] == again["code"]["sha256"]
    (code_tree / "README.md").write_bytes(b"Changed source after previous release")
    with pytest.raises(ValueError, match="Existing deliverable differs"):
        API["package_code"](code_tree, tmp_path / "receipt3", archive_destination=archive)
    assert archive.read_bytes() == original


def test_drive_inventory_only_stats_never_opens_locked_payload(tmp_path, monkeypatch):
    storage = tmp_path / "Drive"
    payload = storage / "data/processed/test.csv.gz"
    payload.parent.mkdir(parents=True)
    payload.write_bytes(b"OPAQUE SYNTHETIC")
    original = Path.open
    def guarded(path, *args, **kwargs):
        assert path != payload, "Inventory cannot open locked bytes"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded)
    result = API["drive_inventory"](storage)
    assert not result["payloads_opened"] and result["file_count"] == 1


def prepare_synthetic_release(tmp_path, monkeypatch):
    globals_ = API["prepare_data_release"].__globals__
    monkeypatch.setitem(globals_, "_requirements", lambda root: API["read"](Path(root) / "configs/handover_data_requirements.json"))
    monkeypatch.setitem(globals_, "_verify_current_final_bundle", lambda root, files: {"fixture_only": True})
    root, storage = synthetic_data_tree(tmp_path)
    plan = tmp_path / "reviewed-include.json"
    result = API["prepare_data_release"](root, storage, plan, allow_locked_bytes=True)
    return root, storage, plan, result


def test_reviewed_data_pack_has_project_prefix_full_checksums_and_clean_extraction(tmp_path, monkeypatch):
    root, storage, plan, prepared = prepare_synthetic_release(tmp_path, monkeypatch)
    assert not prepared["data_zip_created"]
    assert all(v["archive_member"].startswith("disease-prediction-ml/") for v in prepared["include"].values())
    result = API["pack_data_release"](plan, tmp_path / "handover", expected_plan_sha256=API["sha"](plan),
        confirmed_drive_free_bytes=prepared["archive_space_upper_bound"], allow_locked_bytes=True)
    assert result["status"] == "VERIFIED" and result["source_integrity"] == "PASS"
    assert not result["test_evaluated"] and not result["cloud_quota_independently_verified"]
    unpack = Path(result["extraction_check"]) / "disease-prediction-ml"
    for name, info in prepared["include"].items():
        assert API["entry"](unpack / name) == API["entry"](storage / name)


@pytest.mark.parametrize("failure", ["digest", "source_changed", "quota", "existing_output"])
def test_data_pack_fails_closed_without_new_archive(tmp_path, monkeypatch, failure):
    root, storage, plan, prepared = prepare_synthetic_release(tmp_path, monkeypatch)
    expected = API["sha"](plan)
    out = tmp_path / "handover"
    quota = prepared["archive_space_upper_bound"]
    if failure == "digest": expected = "0" * 64
    if failure == "source_changed": (storage / "data/raw/fixture.csv").write_bytes(b"CHANGED")
    if failure == "quota": quota = 0
    if failure == "existing_output": out.mkdir()
    with pytest.raises(ValueError):
        API["pack_data_release"](plan, out, expected_plan_sha256=expected,
            confirmed_drive_free_bytes=quota, allow_locked_bytes=True)
    assert not (out / "project-data.zip").exists()


def test_real_final_manifest_is_required_for_new_data_release(tmp_path, monkeypatch):
    monkeypatch.setitem(API["prepare_data_release"].__globals__, "_requirements",
        lambda root: API["read"](Path(root) / "configs/handover_data_requirements.json"))
    root, storage = synthetic_data_tree(tmp_path)
    with pytest.raises(ValueError, match="final evaluation"):
        API["prepare_data_release"](root, storage, tmp_path / "plan.json", allow_locked_bytes=True)
    assert not (tmp_path / "plan.json").exists()
