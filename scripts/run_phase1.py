"""Execute notebooks using this Python environment; do not register global kernels."""
from pathlib import Path
import argparse
import json
import os
import re
import sys
import time

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpec

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.io import read_config, dataset_path, sha256_file, save_json
from src.data.paths import resolve_paths


def execute(name: str, destination, *, in_place: bool = False) -> dict:
    path = ROOT / "notebooks" / name
    if not path.is_file():
        raise FileNotFoundError(f"Notebook chưa có: {path}")
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    manager = KernelManager(kernel_name="python3")
    # Explicit environment avoids accidental execution in a global Python.
    manager._kernel_spec = KernelSpec(argv=[sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                                      display_name="Disease ML Phase 1", language="python")
    client = NotebookClient(notebook, km=manager, timeout=900, allow_errors=False,
                            resources={"metadata": {"path": str(ROOT / "notebooks")}})
    started = time.perf_counter()
    executed = path if in_place else destination.reports_dir / "notebooks" / name
    executed.parent.mkdir(parents=True, exist_ok=True)
    try:
        client.execute(env={**os.environ, "DISEASE_PROJECT_ROOT": str(ROOT), "PYTHONUTF8": "1"})
    finally:
        # Keep diagnostic cell outputs if execution fails.
        nbformat.write(notebook, executed)
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    errors = [output for cell in notebook.cells if cell.cell_type == "code"
              for output in cell.get("outputs", []) if output.output_type == "error"]
    if errors:
        raise RuntimeError(errors)
    result = {"notebook": name, "seconds": round(time.perf_counter() - started, 3),
              "executed_copy": str(executed),
              "code_cells": sum(c.cell_type == "code" for c in notebook.cells),
              "error_outputs": len(errors),
              "image_outputs": sum("image/png" in o.get("data", {}) for c in notebook.cells
                                   for o in c.get("outputs", []))}
    streams = "\n".join(o.get("text", "") for c in notebook.cells for o in c.get("outputs", []) if o.output_type == "stream")
    run = re.search(r"Run ID: ([A-Za-z0-9_-]+)", streams)
    if run:
        result["analysis_run_id"] = run.group(1)
    print(json.dumps(result), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--notebook", choices=["00_dataset_audit.ipynb", "01_eda.ipynb", "colab_smoke_test.ipynb"])
    parser.add_argument("--in-place", action="store_true", help="Explicitly replace outputs in source notebooks; default saves executed copies.")
    args = parser.parse_args()
    config = read_config(ROOT)
    paths = resolve_paths(ROOT)
    raw = dataset_path(paths, config)
    destination = paths.new_run("execution")
    before = sha256_file(raw)
    existing = ROOT.parent / "seminar_chapter6_model_evaluation.ipynb"
    previous_notebook_hash = sha256_file(existing) if existing.is_file() else None
    names = [args.notebook] if args.notebook else ["00_dataset_audit.ipynb", "01_eda.ipynb"]
    originals = {name: sha256_file(ROOT / "notebooks" / name) for name in names}
    results = [execute(name, destination, in_place=args.in_place) for name in names]
    after = sha256_file(raw)
    assert before == after, "Raw dataset changed during execution"
    assert not previous_notebook_hash or sha256_file(existing) == previous_notebook_hash, "Existing user notebook changed"
    assert args.in_place or all(sha256_file(ROOT / "notebooks" / name) == digest for name, digest in originals.items()), "Source notebooks changed"
    save_json(destination.metadata_dir / "execution.json",
              {"python": sys.version, "notebooks": results, "raw_sha256_before": before, "raw_sha256_after": after,
               "existing_notebook_sha256": previous_notebook_hash})
    print(f"Execution metadata: {destination.metadata_dir}")
