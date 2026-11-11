"""Standard-library code/data packaging and source-only staging/publication.

No model deserialization, fitting, prediction, API calls or original-file deletion.
Data packaging alone may stream opaque locked-test bytes after its explicit flag.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import runpy
import shutil
import stat
import sys
import uuid
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
DATA_REQUIREMENTS_SHA256 = "66a2c43728b44aef7f59917079fdcdd9a5297d8f2b43b4ae21a676f5b6a85f65"
CODE_SUPPLEMENTS_SHA256 = "0c0bf4e6d7255ffab55cfabf5e9c33fa48f950ef25d1a7b5ee6d3315d11e2a0b"
PUBLIC_CONFIGS = ("runtime.json", "phase1.json", "phase2.json", "phase3.json", "phase5b.json", "synonyms.json", "disease_names_vi.json",
                  "dataset_source.json", "phase2_integrity.json", "handover_data_requirements.json",
                  "runtime.local.example.json", "runtime.colab.example.json", "handover_code_supplements.json", "external_data_release.json")
ROOT_FILES = ("README.md", "run_api.py", ".gitignore", ".gitattributes", "pyproject.toml", "setup.ps1", "requirements.txt",
              "requirements-dev.txt", "requirements-notebooks.txt", "requirements-training.txt", "requirements-api.txt")
SOURCE_EXCEPTIONS = ("data/raw/README.md", "data/evaluation/vietnamese_symptom_cases.jsonl")
SOURCE_IDENTITY_FIXTURES = ("artifacts/metadata/phase2/feature_schema.json",
                            "artifacts/metadata/phase2/label_mapping.json")
# Small read-only provenance, also usable as a supplemental evidence root on Colab.
# Scientific datasets/checkpoints and complete result bundles still belong to data ZIP.
CODE_EVIDENCE = ("phase3_audit", "phase4_audit", "post_tuning_audit", "model_analysis",
                 "final_ml_gaps", "final_evaluation_audit", "structured_inference",
                 "runtime_compatibility", "gemini_debug")
CODE_EXT = {".py", ".ps1", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".ipynb",
            ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".svg", ".png", ".ico", ".mmd"}
BLOCKED_PARTS = {".venv", ".venv-web", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
                 ".ipynb_checkpoints", ".git", "node_modules", "dist", ".cache"}
DATA_PREFIXES = ("data/raw/", "data/interim/", "data/processed/", "artifacts/metadata/", "artifacts/models/", "reports/")
DATA_EXT = {".csv", ".gz", ".npz", ".json", ".joblib", ".md", ".png", ".svg", ".txt", ".ipynb"}
SECRET_PATTERNS = (rb"AIza[0-9A-Za-z_-]{35}", rb"sk-[A-Za-z0-9_-]{24,}", rb"AKIA[0-9A-Z]{16}",
                   rb"gsk_[A-Za-z0-9_-]{32,}",
                   rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
                   rb"https://drive\.google\.com/(?:file/d/|drive/folders/)[A-Za-z0-9_-]{12,}")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _requirements(root):
    path = Path(root) / "configs/handover_data_requirements.json"
    require(sha(path) == DATA_REQUIREMENTS_SHA256, "Data packaging contract changed; NOT VERIFIED. Use the approved code release, never weaken requirements to publish a partial data ZIP.")
    return read(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def entry(path):
    return {"bytes": Path(path).stat().st_size, "sha256": sha(path)}


def relative_name(name):
    require(isinstance(name, str) and "\\" not in name and "\x00" not in name and ":" not in name,
            "Invalid archive/publication relative path")
    p = PurePosixPath(name)
    require(not p.is_absolute() and name == p.as_posix() and p.parts and not any(x in {"..", "."} for x in p.parts),
            "Unsafe relative path: " + name)
    return name


def no_links(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.exists():
            info = item.lstat()
            require(not item.is_symlink() and not (getattr(info, "st_file_attributes", 0) & 0x400),
                    "Symlink/reparse path is not allowed: " + str(item))
    return path.resolve()


def exclusive(path, payload):
    path = Path(path)
    no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def secret_check(name, payload):
    require(not any(s in Path(name).name.lower() for s in (".env", "private", "credential", "secret")),
            "Private file excluded: " + name)
    require(not any(re.search(pattern, payload) for pattern in SECRET_PATTERNS),
            "Possible credential/private Drive link; packaging stopped at " + name)


def code_supplements(root):
    """Exact owner-approved fixture paths/bytes; never glob datasets or reports."""
    path = no_links(Path(root) / "configs/handover_code_supplements.json")
    require(sha(path) == CODE_SUPPLEMENTS_SHA256, "Code supplement contract changed")
    policy = read(path)
    require(policy["version"] == 1 and isinstance(policy["files"], dict), "Invalid code supplement policy")
    for name, expected in policy["files"].items():
        relative_name(name)
        require(name.startswith(("reports/terminology/", "reports/release_final_gate/", "data/evaluation/"))
                and Path(name).suffix in {".json", ".jsonl", ".csv", ".txt"}, "Non-fixture code supplement")
        require(0 < expected["bytes"] <= 2 * 1024**2, "Oversized code supplement")
    require(sum(v["bytes"] for v in policy["files"].values()) <= 8 * 1024**2, "Oversized supplement bundle")
    return policy["files"]


def code_files(root):
    root = no_links(root)
    supplements = code_supplements(root)
    names = (set(ROOT_FILES) | {"configs/" + n for n in PUBLIC_CONFIGS} | set(SOURCE_EXCEPTIONS)
             | set(SOURCE_IDENTITY_FIXTURES) | set(supplements))
    for folder in CODE_EVIDENCE:
        for p in (root / "artifacts/metadata" / folder).rglob("*.json"):
            if not any(x in BLOCKED_PARTS for x in p.relative_to(root).parts):
                require(p.stat().st_size <= 2 * 1024**2, "Oversized code-side evidence; review ownership: " + str(p))
                names.add(p.relative_to(root).as_posix())
    # Concise existing research reports are useful without Drive access. Large
    # figures/tables and all reports remain included in the data-side inventory.
    names.update(p.relative_to(root).as_posix() for p in (root / "reports").glob("*.md"))
    for folder in ("src", "app", "notebooks", "scripts", "tests", "docs"):
        for p in (root / folder).rglob("*"):
            if any(part in BLOCKED_PARTS for part in p.relative_to(root).parts):
                continue
            if p.is_file() and (p.suffix in CODE_EXT or p.name == ".gitkeep"):
                name = p.relative_to(root).as_posix()
                if any(x in p.name.lower() for x in (".env", "private", "credential", "secret")):
                    continue
                names.add(name)
    files = {}
    for name in sorted(names):
        p = no_links(root / relative_name(name))
        require(p.is_relative_to(root) and p.is_file(), "Missing handover source: " + name)
        require(p.stat().st_size <= 32 * 1024**2, "Oversized code file: " + name)
        if name in supplements:
            require(entry(p) == supplements[name], "Code supplement identity mismatch: " + name)
        secret_check(name, p.read_bytes())
        files[name] = p
    for n in ("00_dataset_audit", "01_eda", "02_preprocessing", "03_model_training", "04_ensemble",
              "05_structured_inference_check", "06_final_model_evaluation", "colab_smoke_test"):
        require(f"notebooks/{n}.ipynb" in files, "Missing required notebook: " + n)
    return files


def cleanup_inventory(root, code_archive, output):
    """Itemized review only. Never remove/rename/move anything, including caches."""
    root = no_links(root)
    packaged = verify_archive(code_archive)["inventory"]["files"]
    reference_files = {n: p for n, p in code_files(root).items() if p.suffix in {".py", ".md", ".json", ".ipynb", ".ps1", ".toml"}}
    texts = {n: p.read_text(encoding="utf-8-sig", errors="replace") for n, p in reference_files.items()}
    candidates = []
    for parent, dirs, names in os.walk(root, followlinks=False):
        base = Path(parent)
        for name in list(dirs):
            path = base / name
            if name.startswith(".venv") or name == "venv":
                dirs.remove(name)
                candidates.append(("C", path, "REVIEW", "Reproducible environment but currently used by real API; not a cache"))
            elif name in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints"}:
                dirs.remove(name)
                candidates.append(("A", path, "REMOVE-LATER", "Generated cache; can regenerate; preserve until explicit approval"))
        for name in names:
            if name.lower().endswith((".zip", ".pyz")):
                candidates.append(("B", base / name, "REVIEW", "Historical archive/export; compare contents/identity before any removal"))
    for path in (root / "dist/drive-source").glob("*"):
        if path.is_dir():
            candidates.append(("C", path, "REVIEW", "Generated immutable runtime release; may still be the published/rollback source"))
    for name in ("data/raw", "data/processed", "artifacts/models", "artifacts/metadata", "reports"):
        if (root / name).exists():
            candidates.append(("D", root / name, "KEEP", "Protected original research, identities, checkpoints, evidence or reports"))
    rows = []
    for group, path, action, why in candidates:
        relative = path.relative_to(root).as_posix()
        contents = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
        references = [n for n, text in texts.items() if relative in text or relative.replace("/", "\\") in text]
        covered = [p for p in contents if p.relative_to(root).as_posix() in packaged
                   and entry(p) == packaged[p.relative_to(root).as_posix()]]
        if group == "B":
            archive_sha = sha(path)
            references += [n for n, text in texts.items() if archive_sha in text]
        else:
            archive_sha = None
        rows.append({"group": group, "path": str(path.resolve()), "bytes": sum(p.stat().st_size for p in contents),
                     "files": len(contents), "reason": why, "action": action, "explicit_path_or_digest_references": sorted(set(references)),
                     "reference_scope": "code/docs/notebooks/public config and code-side evidence; cloud references NOT VERIFIED",
                     "verified_code_archive_files": len(covered), "all_contents_in_verified_code_archive": len(covered) == len(contents),
                     "drive_copy_verified": False, "archive_sha256": archive_sha,
                     "risk": "Scientific/provenance loss or broken runtime" if group in {"C", "D"} else
                             "Cache regeneration/recomputation" if group == "A" else "Loss of historical release/rollback evidence"})
    result = {"status": "PLAN ONLY; NO CLEANUP AUTHORIZED", "items": rows,
              "regenerable_cache_bytes": sum(r["bytes"] for r in rows if r["group"] == "A"),
              "archive_review_bytes_not_confirmed_redundant": sum(r["bytes"] for r in rows if r["group"] == "B"),
              "confirmed_redundant_archive_bytes": 0, "bytes_deleted": 0, "drive_inventory": "NOT VERIFIED"}
    exclusive(output, encoded(result))
    return result


def runtime_api(root):
    return runpy.run_path(str(Path(root) / "src/data/colab_runtime.py"))


def validate_pins(root):
    """Only source/config hashes; never look for or load a checkpoint."""
    root = Path(root)
    frozen = runpy.run_path(str(root / "src/models/final_evaluation_protocol.py"))["FROZEN_PROTOCOL"]
    for cp in frozen["checkpoints"].values():
        for name, expected in cp["identity"]["source_sha256"].items():
            require(sha(root / name) == expected, "Pinned ML source changed: " + name)
    require(sha(root / "src/models/ensemble.py") == frozen["ensemble"]["engine_source_sha256"], "Hard-vote engine changed")
    require(read(root / "configs/phase3.json") == frozen["checkpoints"]["lr_baseline"]["identity"]["config"], "Original Phase3 config changed")


def stage(root, *, check_only=False):
    root = no_links(root)
    validate_pins(root)
    api = runtime_api(root)
    payloads, publication = api["make_publication"](root)
    destination = no_links(root / "dist/drive-source" / publication["sha256"])
    if check_only:
        require(destination.is_dir(), "No staged current release; run prepare_colab_source.ps1 first")
    # All current and legacy staging files are retained. No Refresh deletion.
    for name, payload in payloads.items():
        target = destination / relative_name(name)
        if target.exists():
            require(target.read_bytes() == payload, "Immutable staging release differs: " + name)
        elif check_only:
            raise FileNotFoundError("Incomplete stage: " + name)
        else:
            exclusive(target, payload)
    api["read_source"](destination, 3, expected_payload_sha256=publication["sha256"])
    return {"status": "STAGED", "folder": str(destination), "runtime_payload_sha256": publication["sha256"],
            "files": len(payloads), "bytes": sum(map(len, payloads.values())), "cloud_verified": False}


def publish(root, drive_project):
    root = no_links(root)
    requested = Path(drive_project).expanduser()
    require(requested.is_absolute() and requested.is_dir(), "DriveProjectPath must be an existing absolute Drive-desktop project directory")
    destination = no_links(requested)
    require(destination != root and not destination.is_relative_to(root) and not root.is_relative_to(destination),
            "Drive destination must be separate from the authoritative local source")
    settings = read(root / "configs/runtime.json")
    tail = PurePosixPath(settings["colab"]["project_relative"]).parts[1:]
    require(tuple(x.lower() for x in destination.parts[-len(tail):]) == tuple(x.lower() for x in tail),
            "Drive-desktop path does not end with the canonical project suffix")
    metadata = destination / "artifacts/metadata/phase2/dataset_manifest.json"
    approved = read(root / "configs/phase2_integrity.json")["approved_manifest_sha256"]
    require(metadata.is_file() and sha(metadata) in approved, "Destination has no approved Phase2 manifest. Do not create a fake Drive root or overwrite a variant.")
    result = stage(root)
    source = Path(result["folder"])
    api = runtime_api(root)
    payloads, _ = api["make_publication"](root)
    targets = []
    for name in payloads:
        relative_name(name)
        require(name.startswith(("src/", "configs/")) or name in api["RUNTIME_SCRIPTS"] or name in api["REQUIREMENTS"], "Non-source publication path")
        target = no_links(destination / name)
        require(target.is_relative_to(destination), "Publication escapes project")
        require(not target.exists() or target.is_file(), "Publication target is not a file")
        targets.append(name)
    # No target is touched until EVERY path and provenance check has passed.
    # Only generated source is replaceable. Never rename/delete data or artifacts.
    for name in sorted(targets, key=lambda n: n == "configs/runtime.json"):
        target = destination / name
        payload = (source / name).read_bytes()
        if target.exists() and target.read_bytes() == payload:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    api["read_source"](destination, 3, expected_payload_sha256=result["runtime_payload_sha256"])
    return {**result, "status": "LOCAL_DRIVE_COPY_VERIFIED; CLOUD_ACK_PENDING", "destination": str(destination),
            "drive_desktop_mapping": "USER_SUPPLIED; provider/cloud identity NOT VERIFIED", "cloud_verified": False}


def _zip_write(archive, name, path):
    info = zipfile.ZipInfo(relative_name(name), (2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    with archive.open(info, "w", force_zip64=True) as target, Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            target.write(block)


def verify_archive(path, *, expected_sha256=None):
    if expected_sha256:
        require(sha(path) == expected_sha256, "Archive SHA-256 mismatch")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [relative_name(i.filename) for i in infos]
        require(len(names) == len(set(n.casefold() for n in names)), "Duplicate/case-colliding ZIP entries")
        require(all(not stat.S_ISLNK(i.external_attr >> 16) and not i.is_dir() for i in infos), "ZIP symlink/directory entry rejected")
        manifests = [n for n in names if n in {"disease-prediction-ml/handover_code_inventory.json", "handover_data_inventory.json",
                                               "disease-prediction-ml-data/handover_data_inventory.json"}]
        require(len(manifests) == 1, "Missing/ambiguous handover inventory")
        inventory = json.loads(archive.read(manifests[0]))
        prefix = inventory.get("archive_prefix", "disease-prediction-ml/" if inventory["kind"] == "code" else "")
        expected_names = {prefix + n for n in inventory["files"]}
        require(set(names) == expected_names | set(manifests), "ZIP file inventory differs")
        for name, wanted in inventory["files"].items():
            relative_name(name)
            info = archive.getinfo(prefix + name)
            require(info.file_size == wanted["bytes"], "ZIP entry size mismatch: " + name)
            h = hashlib.sha256()
            with archive.open(info) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(block)
            require(h.hexdigest() == wanted["sha256"], "ZIP entry checksum mismatch: " + name)
    return {"kind": inventory["kind"], "files": len(names), "uncompressed_bytes": sum(i.file_size for i in infos), "inventory": inventory}


def extract(path, destination, expected_sha256, *, allow_locked_bytes=False):
    require(isinstance(expected_sha256, str) and re.fullmatch(r"[0-9a-f]{64}", expected_sha256), "A trusted 64-character archive SHA-256 is required before extraction")
    verified = verify_archive(path, expected_sha256=expected_sha256)
    require(verified["kind"] == "code" or allow_locked_bytes, "Data extraction requires --allow-locked-bytes (opaque archive copy only, no evaluation)")
    destination = no_links(destination)
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            target = no_links(destination / relative_name(info.filename))
            require(target.is_relative_to(destination), "Extraction escapes destination")
            if target.exists():
                require(target.is_file(), "Existing extraction target is not a file")
                with archive.open(info) as stream:
                    h = hashlib.sha256()
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        h.update(block)
                require(sha(target) == h.hexdigest(), "Different existing file; NOT overwritten: " + info.filename)
        for info in archive.infolist():
            target = destination / info.filename
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream, archive.open(info) as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    stream.write(block)
    return verified


def _new_output(root, output, *, forbidden_root=None):
    result = Path(output) if output else Path(root) / "dist/handover" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    result = no_links(result)
    root = Path(root).resolve()
    require(result != root and not any(result.is_relative_to(root / n) for n in
            ("data", "artifacts", "src", "configs", "notebooks", "reports", "docs", "tests", "scripts", "app")),
            "Release output must not be inside original source/data/artifact directories")
    require(forbidden_root is None or not result.is_relative_to(Path(forbidden_root).resolve()), "Release output must be outside canonical storage")
    require(not result.exists(), "Output folder already exists; use a fresh release directory (nothing removed)")
    result.mkdir(parents=True, exist_ok=False)
    return result


def package_code(root, output=None, *, archive_destination=None):
    root = no_links(root)
    validate_pins(root)
    files = code_files(root)
    payloads, publication = runtime_api(root)["make_publication"](root)
    inventory = {"version": 1, "kind": "code", "runtime_payload_sha256": publication["sha256"],
                 "files": {n: entry(p) for n, p in files.items()}}
    out = _new_output(root, output)
    archive_path = no_links(archive_destination) if archive_destination else out / "project-code.zip"
    if archive_destination:
        require(archive_path.is_absolute() and not archive_path.is_relative_to(root), "Final code ZIP must be outside repository")
        require(archive_path.parent.is_dir(), "Archive parent must exist")
    if archive_path.exists():
        old = verify_archive(archive_path)
        require(old["inventory"] == inventory, "Existing deliverable differs; preserved untouched. Archive the old deliverable explicitly before replacing it.")
    else:
        with archive_path.open("xb") as stream, zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, path in files.items():
                _zip_write(archive, "disease-prediction-ml/" + name, path)
            archive.writestr("disease-prediction-ml/handover_code_inventory.json", encoded(inventory))
    digest = sha(archive_path)
    verified = extract(archive_path, out / "code-extraction-check", digest)
    unpacked = out / "code-extraction-check/disease-prediction-ml"
    for name, wanted in inventory["files"].items():
        require(entry(unpacked / name) == wanted and entry(root / name) == wanted, "Source/extraction changed: " + name)
    manifest = {"version": 1, "code": {"status": "VERIFIED", "path": str(archive_path), "sha256": digest,
        "bytes": archive_path.stat().st_size, "files": verified["files"], "uncompressed_bytes": verified["uncompressed_bytes"],
        "extraction_check": str(unpacked), "source_bytes_preserved": True},
        "runtime": {"payload_sha256": publication["sha256"], "files": len(payloads), "cloud_verified": False},
        "data": {"status": "NOT VERIFIED", "reason": "Canonical Drive artifacts must be checked separately; no partial data ZIP produced"}}
    manifest["code"].update(crc_and_member_sha256="PASS", archive_root="disease-prediction-ml/",
                            notebook_outputs_preserved=True, credentials_scan="PASS (known patterns + allowlist)")
    exclusive(out / "handover_manifest.json", encoded(manifest))
    return manifest


def data_plan(root, storage, output):
    requirements = _requirements(root)
    required = set(requirements["baseline_files"]) | set(requirements["phase2_files"]) | set(requirements["manifests"]) | set(requirements["evidence_files"])
    for name in requirements["model_names"]:
        required.update(f"artifacts/models/tuning/{requirements['tuning_id']}/{name}/{n}" for n in ("pipeline.joblib", "fit.json", "metadata.json", "validation_predictions.npz"))
    required.add("data/raw/" + requirements["raw"]["filename"])
    required.add("artifacts/metadata/phase2/dataset_manifest.json")
    result = {"status": "NOT VERIFIED", "canonical_project_relative": requirements["canonical_project_relative"],
              "storage_root_requested": str(storage), "requirements": requirements, "required_paths": sorted(required),
              "locked_test_payload_opened": False, "data_zip_created": False,
              "instructions": "Run data on the canonical Drive with --allow-locked-bytes; never use local incomplete models as a release."}
    exclusive(Path(output), encoded(result))
    return result


def verify_data(root, storage, *, evidence_root=None, allow_locked_bytes=False):
    """Packaging checks stream opaque bytes, NEVER parse CSV/NPZ/joblib payloads."""
    require(allow_locked_bytes, "Opaque packaging access requires --allow-locked-bytes; no evaluation is allowed")
    storage = no_links(storage)
    require(storage.is_dir(), "Canonical Drive unavailable; data ZIP NOT VERIFIED")
    req = _requirements(root)
    files = {}
    for prefix in DATA_PREFIXES:
        for p in (storage / prefix).rglob("*"):
            if any(part in BLOCKED_PARTS | {"backups"} for part in p.relative_to(storage).parts):
                continue
            if p.is_file() and p.name != ".gitkeep" and p.suffix in DATA_EXT:
                name = p.relative_to(storage).as_posix()
                if name in SOURCE_EXCEPTIONS:
                    continue
                require(no_links(p).is_relative_to(storage), "Linked data artifact")
                require(not any(x in p.name.lower() for x in (".env", "private", "credential", "secret")), "Private artifact rejected")
                files[name] = p
    def check(name, wanted=None):
        relative_name(name)
        require(name in files, "Missing data artifact; NOT VERIFIED: " + name)
        actual = entry(files[name])
        if isinstance(wanted, str):
            require(actual["sha256"] == wanted, "Data manifest mismatch: " + name)
        elif wanted:
            require(actual == wanted, "Data identity/size mismatch: " + name)
        return actual
    mp = "artifacts/metadata/phase2/dataset_manifest.json"
    check(mp, req["phase2_manifest_sha256"])
    manifest = read(files[mp])
    require(manifest["status"] == "finalized" and manifest["test_locked"] and manifest["files"] == req["phase2_files"]
            and manifest["processed"] == req["processed"], "Locked Phase2 structure differs; do not replace its variant")
    for name, wanted in req["phase2_files"].items():
        check(name, wanted)
    check("data/raw/" + req["raw"]["filename"], {k: req["raw"][k] for k in ("bytes", "sha256")})
    for name, wanted in req["baseline_files"].items():
        check(name, wanted)
    for name, wanted in req["evidence_files"].items():
        if evidence_root:
            extra = Path(evidence_root) / name
            if extra.is_file():
                require(entry(extra) == wanted, "Supplemental evidence differs: " + name)
                if name in files:
                    require(entry(files[name]) == wanted, "Same-path conflicting evidence; NOT overwritten")
                else:
                    files[name] = no_links(extra)
        check(name, wanted)
    for name, wanted in req["manifests"].items():
        check(name, wanted)
        bundle = read(files[name])
        for relative, expectation in bundle.get("files", bundle.get("artifact_files", {})).items():
            check(relative, expectation)
    for kind, experiment, identity in (("phase3", req["baseline_id"], req["baseline_identity"]), ("tuning", req["tuning_id"], req["tuned_identity"])):
        for name in req["model_names"]:
            prefix = f"artifacts/models/{kind}/{experiment}/{name}/"
            fit, meta = read(files[prefix + "fit.json"]), read(files[prefix + "metadata.json"])
            require(fit["identity"] == meta["identity"] == identity and fit["status"] == "fitted" and meta["status"] == "completed", "Checkpoint identity/status differs")
            check(prefix + "pipeline.joblib", fit["pipeline_sha256"])
            check(prefix + "fit.json", meta["fit_metadata_sha256"])
            check(prefix + "validation_predictions.npz", meta["predictions_sha256"])
    return files, req


def package_data(root, storage, output=None, *, allow_locked_bytes=False, evidence_root=None):
    require(allow_locked_bytes, "Explicit --allow-locked-bytes required for opaque data packaging, NOT evaluation")
    files, req = verify_data(root, storage, evidence_root=evidence_root, allow_locked_bytes=True)
    inventory = {"version": 1, "kind": "data", "phase2_manifest_sha256": req["phase2_manifest_sha256"],
                 "files": {n: entry(p) for n, p in sorted(files.items())}, "models_fitted": 0,
                 "locked_bytes_packaging_only": True, "test_evaluated": False}
    out = _new_output(root, output, forbidden_root=storage)
    archive_path = out / "project-data.zip"
    with archive_path.open("xb") as stream, zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in sorted(files.items()):
            _zip_write(archive, name, path)
        archive.writestr("handover_data_inventory.json", encoded(inventory))
    digest = sha(archive_path)
    verified = verify_archive(archive_path, expected_sha256=digest)
    result = {"status": "VERIFIED", "path": str(archive_path), "sha256": digest,
              "bytes": archive_path.stat().st_size, "files": verified["files"],
              "uncompressed_bytes": verified["uncompressed_bytes"], "models_fitted": 0, "test_evaluated": False}
    exclusive(out / "data_handover_manifest.json", encoded(result))
    return result


def drive_inventory(storage):
    """Read directory entries/sizes only. No file payload, writes, API or imports."""
    storage = no_links(storage)
    require(storage.is_dir(), "Actual mounted Drive project unavailable; NOT VERIFIED")
    entries, skipped = {}, []
    for parent, dirs, names in os.walk(storage, followlinks=False):
        base = Path(parent)
        for name in list(dirs):
            path = base / name
            if name in BLOCKED_PARTS or name.startswith(".venv") or path.is_symlink():
                dirs.remove(name)
                skipped.append(path.relative_to(storage).as_posix())
        for name in names:
            path = base / name
            relative = path.relative_to(storage).as_posix()
            require(no_links(path).is_relative_to(storage), "Linked Drive file rejected")
            entries[relative] = {"bytes": path.stat().st_size}
    return {"storage_root": str(storage), "files": entries, "skipped_directories": skipped,
            "file_count": len(entries), "bytes": sum(v["bytes"] for v in entries.values()),
            "payloads_opened": False, "cloud_quota": "NOT VERIFIED; mounted disk free is not account quota"}


def _verify_current_final_bundle(root, files):
    """Verify published final evidence as opaque bytes; never evaluate predictions."""
    prefix = "artifacts/metadata/final_evaluation/049ee0aa3c290798/"
    require(prefix + "manifest.json" in files, "Missing completed final evaluation manifest")
    require(sha(files[prefix + "manifest.json"]) ==
            "f1ad195e1e46154d7a29a421e80387bfa76e494f4df771cede240f882d0b754a",
            "Final evaluation manifest identity differs; do not replace its variant")
    manifest = read(files[prefix + "manifest.json"])
    expected = {"execution.json", "protocol.json", "preflight.json", "test_predictions.npz", "comparison.csv",
                "per_class.csv", "transitions.csv", "group_differences.csv", "comparison.png", "results.json", "report.md"}
    require(manifest["status"] == "completed" and set(manifest["files"]) == expected,
            "Final evaluation incomplete; execution marker must be retained")
    for name, wanted in manifest["files"].items():
        require(prefix + name in files and entry(files[prefix + name]) == wanted, "Final bundle checksum mismatch: " + name)
    frozen = runpy.run_path(str(Path(root) / "src/models/final_evaluation_protocol.py"))["FROZEN_PROTOCOL"]
    require(read(files[prefix + "protocol.json"]) == frozen, "Final protocol differs from frozen source")
    return {"manifest_sha256": sha(files[prefix + "manifest.json"]), "files": len(expected) + 1,
            "payloads_parsed": False, "test_evaluated": False}


def prepare_data_release(root, storage, output, *, allow_locked_bytes=False):
    """Inventory actual Drive first, then pin an explicit immutable INCLUDE plan.

    Source CSV/joblib/NPZ bytes are streamed solely for packaging integrity. Local
    small provenance may supplement a missing Drive path, never replace a variant.
    """
    require(allow_locked_bytes, "Explicit --allow-locked-bytes required for opaque packaging hashes")
    root, storage = no_links(root), no_links(storage)
    require(not Path(output).resolve().is_relative_to(storage), "Plan output must be outside original storage")
    actual = drive_inventory(storage)
    files, req = verify_data(root, storage, evidence_root=root, allow_locked_bytes=True)
    supplemental = {}
    for folder in CODE_EVIDENCE:
        supplemental.update({p.relative_to(root).as_posix(): p for p in (root / "artifacts/metadata" / folder).rglob("*.json")})
    supplemental.update({p.relative_to(root).as_posix(): p for p in (root / "reports").glob("*.md")})
    for name, path in supplemental.items():
        require(no_links(path).is_relative_to(root), "Linked supplemental evidence rejected")
        if not name.startswith(("artifacts/metadata/", "reports/")):
            continue
        if name in files:
            require(entry(files[name]) == entry(path), "Same-path local/Drive provenance conflict; never merged: " + name)
        else:
            files[name] = path
    final = _verify_current_final_bundle(root, files)
    includes = {}
    duplicates = {}
    for name, path in sorted(files.items()):
        if path.suffix in {".json", ".md", ".txt", ".ipynb"}:
            secret_check(name, path.read_bytes())
        info = entry(path)
        includes[name] = {**info, "source": str(path), "archive_member": "disease-prediction-ml/" + name,
                          "origin": "canonical_drive" if path.is_relative_to(storage) else "code_provenance"}
        duplicates.setdefault((info["sha256"], info["bytes"]), []).append(name)
    total = sum(v["bytes"] for v in includes.values())
    excluded = {n: {**v, "reason": "Outside data allowlist, cache/archive/export or requires review; original retained"}
                for n, v in actual["files"].items() if n not in includes}
    result = {"version": 2, "kind": "data_include_plan", "status": "READY FOR OWNER REVIEW; NOT PACKED",
              "storage_root": str(storage), "code_root": str(root), "inventory": actual,
              "include": includes, "excluded": excluded, "file_count": len(includes), "uncompressed_bytes": total,
              "archive_size_estimate": "Compression unknown; conservative required space below",
              "archive_space_upper_bound": total + len(includes) * 4096 + 4 * 1024**2,
              "temporary_extraction_required_bytes": total + 4 * 1024**2,
              "identical_content_paths_preserved": [v for (_, size), v in duplicates.items() if size > 1024**2 and len(v) > 1],
              "duplicate_policy": "Preserve existing path contracts; ZIP has no portable hard links. No extra model copies created.",
              "phase2_manifest_sha256": req["phase2_manifest_sha256"], "final_evaluation": final,
              "models_fitted": 0, "test_evaluated": False, "data_zip_created": False}
    exclusive(output, encoded(result))
    return result


def pack_data_release(plan_path, output, *, expected_plan_sha256, confirmed_drive_free_bytes,
                      allow_locked_bytes=False):
    """Consume exactly the reviewed plan; new sibling output and clean VM extract only."""
    require(allow_locked_bytes, "Explicit --allow-locked-bytes required")
    require(sha(plan_path) == expected_plan_sha256, "Reviewed INCLUDE plan SHA mismatch")
    plan = read(plan_path)
    require(plan.get("kind") == "data_include_plan" and plan.get("version") == 2, "Invalid INCLUDE plan")
    root, storage = Path(plan["code_root"]), Path(plan["storage_root"])
    files = {}
    for name, wanted in plan["include"].items():
        relative_name(name)
        source = no_links(wanted["source"])
        base = storage if wanted["origin"] == "canonical_drive" else root
        require(source == (base / name).resolve() and source.is_relative_to(base.resolve()), "INCLUDE source path mismatch")
        require(wanted["archive_member"] == "disease-prediction-ml/" + name, "INCLUDE member mismatch")
        require(entry(source) == {k: wanted[k] for k in ("bytes", "sha256")}, "Source changed since INCLUDE review: " + name)
        files[name] = source
    require(confirmed_drive_free_bytes is not None and confirmed_drive_free_bytes >= plan["archive_space_upper_bound"],
            "Confirm sufficient Drive account quota (bytes) from Drive storage UI; filesystem free is not quota")
    import tempfile
    temp_parent = Path(tempfile.gettempdir())
    require(shutil.disk_usage(temp_parent).free >= plan["temporary_extraction_required_bytes"], "Insufficient VM extraction space")
    out = _new_output(root, output, forbidden_root=storage)
    archive_path = out / "project-data.zip"
    inventory = {"version": 2, "kind": "data", "archive_prefix": "disease-prediction-ml/",
                 "files": {n: {k: w[k] for k in ("bytes", "sha256")} for n, w in plan["include"].items()},
                 "include_plan_sha256": expected_plan_sha256, "models_fitted": 0, "test_evaluated": False}
    # All outputs created exclusively. On interruption leave partial archive for
    # review; no VERIFIED receipt is written and nothing is deleted/replaced.
    with archive_path.open("xb") as stream, zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, source in files.items():
            _zip_write(archive, "disease-prediction-ml/" + name, source)
        archive.writestr("handover_data_inventory.json", encoded(inventory))
    digest = sha(archive_path)
    verified = verify_archive(archive_path, expected_sha256=digest)
    # Retain the clean extraction for inspection, per no-cleanup instruction.
    temporary = Path(tempfile.mkdtemp(prefix="handover-data-extraction-"))
    extract(archive_path, temporary, digest, allow_locked_bytes=True)
    for name, wanted in inventory["files"].items():
        require(entry(files[name]) == wanted and entry(temporary / "disease-prediction-ml" / name) == wanted,
                "Original/extracted bytes changed: " + name)
    result = {"status": "VERIFIED", "path": str(archive_path), "bytes": archive_path.stat().st_size,
              "sha256": digest, "files": verified["files"], "crc_and_member_sha256": "PASS",
              "source_integrity": "PASS", "extraction_check": str(temporary), "include_plan_sha256": expected_plan_sha256,
              "operator_confirmed_drive_free_bytes": confirmed_drive_free_bytes, "cloud_quota_independently_verified": False,
              "models_fitted": 0, "test_evaluated": False, "runtime_end_to_end": "NOT VERIFIED"}
    exclusive(out / "data_handover_manifest.json", encoded(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("code", "stage", "publish", "data-plan", "data", "extract", "data-inventory", "data-prepare", "data-pack", "cleanup-inventory"))
    parser.add_argument("--project-root", default=str(PROJECT))
    parser.add_argument("--output")
    parser.add_argument("--storage-root")
    parser.add_argument("--drive-project-path")
    parser.add_argument("--evidence-root")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--allow-locked-bytes", action="store_true")
    parser.add_argument("--archive")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--archive-destination")
    parser.add_argument("--plan")
    parser.add_argument("--confirmed-drive-free-bytes", type=int)
    args = parser.parse_args()
    if args.action == "code":
        result = package_code(args.project_root, args.output, archive_destination=args.archive_destination)
    elif args.action == "stage":
        result = stage(args.project_root, check_only=args.check_only)
    elif args.action == "publish":
        require(args.drive_project_path is not None, "--drive-project-path required")
        result = publish(args.project_root, args.drive_project_path)
    elif args.action == "data-plan":
        require(args.output and args.storage_root, "--output and --storage-root required")
        result = data_plan(args.project_root, args.storage_root, args.output)
        result = {k: v for k, v in result.items() if k not in {"requirements", "required_paths"}}
    elif args.action == "data-inventory":
        require(args.storage_root and args.output, "--storage-root and --output required")
        require(not Path(args.output).resolve().is_relative_to(Path(args.storage_root).resolve()), "Inventory output must be outside originals")
        result = drive_inventory(args.storage_root)
        exclusive(args.output, encoded(result))
    elif args.action == "cleanup-inventory":
        require(args.archive and args.output, "--archive and --output required")
        result = cleanup_inventory(args.project_root, args.archive, args.output)
        result = {k: v for k, v in result.items() if k != "items"}
    elif args.action == "data-prepare":
        require(args.storage_root and args.output, "--storage-root and --output required")
        plan = prepare_data_release(args.project_root, args.storage_root, args.output, allow_locked_bytes=args.allow_locked_bytes)
        result = {k: v for k, v in plan.items() if k not in {"include", "excluded", "inventory"}}
        result.update(plan_path=args.output, plan_sha256=sha(args.output))
    elif args.action == "data-pack":
        require(args.plan and args.output and args.expected_sha256, "--plan, --output and --expected-sha256 required")
        result = pack_data_release(args.plan, args.output, expected_plan_sha256=args.expected_sha256,
                                  confirmed_drive_free_bytes=args.confirmed_drive_free_bytes, allow_locked_bytes=args.allow_locked_bytes)
    elif args.action == "data":
        require(args.storage_root, "--storage-root required")
        result = package_data(args.project_root, args.storage_root, args.output,
                              allow_locked_bytes=args.allow_locked_bytes, evidence_root=args.evidence_root)
    else:
        require(args.archive and args.output and args.expected_sha256, "extract requires --archive, --output and --expected-sha256")
        result = extract(args.archive, args.output, args.expected_sha256, allow_locked_bytes=args.allow_locked_bytes)
        result = {k: v for k, v in result.items() if k != "inventory"}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if "runtime_payload_sha256" in result:
        print("RUNTIME_PAYLOAD_SHA256=" + result["runtime_payload_sha256"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print("STOP / NOT VERIFIED: " + str(exc), file=sys.stderr)
        sys.exit(2)
