"""Check preservation, executed copies and image pixels after the portability migration."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

import matplotlib.image as mpimg
import nbformat
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.loader import sha256_file
from src.data.paths import OutputPaths, resolve_paths
from src.data.io import save_json


def main():
    backups = sorted((ROOT / "artifacts/backups").glob("portability-*/baseline.json"))
    if not backups:
        raise FileNotFoundError("Cần baseline snapshot từ trước khi sửa portability; không tự tạo baseline sau thay đổi.")
    baseline_file = backups[-1]
    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    protected = 0
    for relative, digest in baseline.items():
        path = ROOT / relative
        if path.suffix == ".ipynb":
            old = json.loads((baseline_file.parent / path.name).read_text(encoding="utf-8"))
            new = json.loads(path.read_text(encoding="utf-8"))
            assert old["metadata"] == new["metadata"]
            assert len(old["cells"]) == len(new["cells"])
            for before, after in zip(old["cells"], new["cells"]):
                if before["cell_type"] == "markdown":
                    assert before == after
                else:
                    assert {k: v for k, v in before.items() if k != "source"} == {k: v for k, v in after.items() if k != "source"}
        else:
            assert sha256_file(path) == digest, f"Protected file changed: {relative}"
            protected += 1
    paths = resolve_paths(ROOT)
    executions = sorted((paths.output_root / "artifacts/metadata/runs").glob("execution-*/execution.json"))
    records = [(p, json.loads(p.read_text(encoding="utf-8"))) for p in executions]
    phase1_file, phase1 = next((p, r) for p, r in reversed(records) if {n["notebook"] for n in r["notebooks"]} == {"00_dataset_audit.ipynb", "01_eda.ipynb"})
    smoke_file, smoke = next((p, r) for p, r in reversed(records) if {n["notebook"] for n in r["notebooks"]} == {"colab_smoke_test.ipynb"})
    for execution in [phase1, smoke]:
        assert execution["raw_sha256_before"] == execution["raw_sha256_after"]
        for record in execution["notebooks"]:
            assert record["error_outputs"] == 0
            notebook = nbformat.read(record["executed_copy"], as_version=4)
            nbformat.validate(notebook)
            assert all(c.execution_count is not None for c in notebook.cells if c.cell_type == "code")
            assert not [o for c in notebook.cells for o in c.get("outputs", []) if o.output_type == "error" or o.output_type == "stream" and o.get("name") == "stderr"]
    eda_run = next(n["analysis_run_id"] for n in phase1["notebooks"] if n["notebook"] == "01_eda.ipynb")
    new_figures = OutputPaths(paths.output_root, eda_run).figures_dir
    compared = []
    for old in sorted((ROOT / "reports/figures").glob("*.png")):
        assert np.array_equal(mpimg.imread(old), mpimg.imread(new_figures / old.name)), old.name
        compared.append(old.name)
    assert len(compared) == 8
    test_reports = sorted((ROOT / "artifacts/metadata").glob("portability-tests-*.xml"), key=lambda p: p.stat().st_mtime)
    if not test_reports:
        raise FileNotFoundError("Cần pytest JUnit XML portability-tests-*.xml, có bật data regression.")
    test_tree = ET.parse(test_reports[-1]).getroot()
    suites = test_tree.findall(".//testsuite")
    counts = {key: sum(int(s.attrib.get(key, 0)) for s in suites) for key in ["tests", "failures", "errors", "skipped"]}
    assert counts["tests"] > 0 and not any(counts[key] for key in ["failures", "errors", "skipped"])
    assert any(c.attrib.get("name") == "test_actual_source_csv_reproduces_all_historical_metrics_and_tables" for c in test_tree.findall(".//testcase"))
    output = paths.new_run("portability-validation")
    result = {"status": "PASS", "protected_files_unchanged": protected,
              "original_notebook_outputs_and_markdown_preserved": True,
              "test_results": counts, "actual_csv_regression": "All metrics and 26 CSV tables match historical Phase 1 evidence",
              "local_phase1_execution": str(phase1_file.relative_to(ROOT)),
              "local_smoke_execution": str(smoke_file.relative_to(ROOT)),
              "png_pixel_equality": compared,
              "genuine_colab_runtime_tested": False,
              "colab_filesystem_and_capabilities_simulated_in_tests": True}
    save_json(output.metadata_dir / "portability_validation.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Validation record: {output.metadata_dir}")


if __name__ == "__main__":
    main()
