"""Explicitly package only public project source; never include CSVs, credentials or outputs."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build_bundle(root: Path, destination: Path) -> dict:
    """Package current source to an explicit NEW file; never replace an old bundle."""
    files = set()
    for folder, suffixes in [("src", {".py"}), ("scripts", {".py"}), ("tests", {".py"}),
                              ("configs", {".json"}), ("notebooks", {".ipynb", ".md"}), ("docs", {".md"})]:
        files.update(p for p in (root / folder).rglob("*") if p.suffix in suffixes and "__pycache__" not in p.parts)
    files.update(root / name for name in ["README.md", "requirements.txt", "requirements-notebooks.txt", "requirements-training.txt", "requirements-dev.txt", "pyproject.toml", ".gitignore", "setup.ps1", "data/raw/README.md"])
    # Runtime configuration allowlist: personal configuration is never bundled.
    files = {p for p in files if p.parent.name != "configs" or p.name in
             {"phase1.json", "phase2.json", "phase3.json", "dataset_source.json", "runtime.json", "runtime.local.example.json", "runtime.colab.example.json"}}
    destination.parent.mkdir(parents=True, exist_ok=True)
    hashes = {}
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            if not path.is_file():
                continue
            data = path.read_bytes()
            if path.suffix == ".ipynb":
                notebook = json.loads(data)
                for cell in notebook["cells"]:
                    if cell["cell_type"] == "code":
                        cell["outputs"] = []
                        cell["execution_count"] = None
                data = json.dumps(notebook, ensure_ascii=False, indent=1).encode("utf-8")
            relative = path.relative_to(root).as_posix()
            archive.writestr("disease-prediction-ml/" + relative, data)
            hashes[relative] = hashlib.sha256(data).hexdigest()
        archive.writestr("disease-prediction-ml/bundle_manifest.json", json.dumps(hashes, indent=2))
        if destination.suffix == ".pyz":
            # A stdlib zipapp: the same source archive can repair a mounted Drive project.
            archive.writestr("__main__.py", (root / "scripts/install_colab_source.py").read_bytes())
    return {"path": str(destination), "files": len(hashes), "bytes": destination.stat().st_size}


def main():
    print("DEPRECATED for startup. Use scripts/prepare_colab_source.ps1 and docs/phase3_colab.md. Historical packaging only.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--installer", action="store_true", help="Build one-file Colab source repair (.pyz).")
    args = parser.parse_args()
    if args.installer:
        destination = ROOT / "dist/disease-prediction-ml-colab-setup.pyz"
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        destination = ROOT / "dist" / f"disease-prediction-ml-source-{stamp}.zip"
    result = build_bundle(ROOT, destination)
    print(f"Source bundle: {destination}")
    print(f"{result['files']} files; {result['bytes']:,} bytes; no data/outputs/credentials. Original notebooks unchanged.")


if __name__ == "__main__":
    main()
