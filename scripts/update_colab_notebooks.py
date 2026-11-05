"""Migrate runtime cells only; retain cell IDs, analytical code and every saved output."""
from pathlib import Path
import json
import uuid

ROOT = Path(__file__).resolve().parents[1]
NOTE = "\n\nRuntime chung Colab/Drive: [hướng dẫn duy nhất](../docs/phase3_colab.md). " \
       "Cấu hình ở `configs/runtime.json`; source từ Drive, thực thi trong `/content`. " \
       "Outputs đã lưu là lịch sử, không phải bằng chứng đã chạy trên Colab."
TRAINING_INTRO = """# 03 — Huấn luyện trên Colab, lưu vào Google Drive

## 1. Runtime dùng chung với notebook 00–02

Đồng bộ source vào canonical Drive root, chọn kernel Colab và mount Drive theo
[hướng dẫn chung](../docs/phase3_colab.md). Không upload session package vào runtime.
Cell đầu chỉ kiểm môi trường/source và chuẩn bị workspace tạm; cell tiếp theo mới kiểm dữ liệu.
Đường dẫn tập trung ở `configs/runtime.json`; dòng locator dưới chỉ chỉ tới source trên Drive.
Khi source đổi, đồng bộ Drive rồi Restart Kernel. Không tự cài package hoặc tái tạo Phase 2.
Chạy riêng hai phần đầu để preflight/nạp dữ liệu; các cell mô hình chỉ chạy khi chủ động huấn luyện.
"""


def entry_source(phase):
    settings = json.loads((ROOT / "configs/runtime.json").read_text(encoding="utf-8"))
    colab = settings["colab"]
    drive_root = str(Path(colab["drive_mount"]) / colab["project_relative"]).replace("\\", "/")
    return ("import runpy, platform\n"
            "from pathlib import Path\n"
            "if platform.system() != 'Linux' or not Path('/content').is_dir():\n"
            "    raise RuntimeError('Chọn Google Colab kernel; /content phải là ổ tạm của runtime.')\n"
            f"DRIVE_ROOT = Path({drive_root!r})  # Locator sinh từ configs/runtime.json\n"
            "entry = DRIVE_ROOT / 'src/data/colab_runtime.py'\n"
            "if not entry.is_file():\n"
            "    raise FileNotFoundError(f'Không thấy {entry}. Mount Drive và Publish source bằng prepare_colab_source.ps1; không upload script riêng.')\n"
            "EXPECTED_RUNTIME_PAYLOAD = globals().get('EXPECTED_RUNTIME_PAYLOAD') or input('Paste RUNTIME_PAYLOAD_SHA256 from local Publish: ').strip()\n"
            f"RUNTIME = runpy.run_path(str(entry))['bootstrap_runtime'](DRIVE_ROOT, phase={phase}, expected_payload_sha256=EXPECTED_RUNTIME_PAYLOAD)\n"
            "ROOT, runtime_paths = RUNTIME.paths.project_root, RUNTIME.paths\n")


def replace_source(cell, source):
    cell["source"] = source.strip().splitlines(keepends=True)


def migrate(name, notebook):
    cells = notebook["cells"]
    # The reviewed smoke flow has explicit prerequisites/statuses. This legacy
    # migration must not replace it with the old positional, load-data smoke.
    if notebook.get("metadata", {}).get("runtime_setup") == "verified-drive-preflight-v1":
        for index, cell in enumerate(cells):
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), f"{name}:{index}", "exec")
        return notebook
    if name in ("00_dataset_audit.ipynb", "01_eda.ipynb"):
        setup = cells[1]
        if "bootstrap_runtime" not in "".join(setup["source"]):
            old = "".join(setup["source"])
            tail = old[old.index("import numpy as np"):]
            replace_source(setup, tail)
            cells.insert(1, {"cell_type": "code", "id": uuid.uuid4().hex[:8], "metadata": {},
                             "execution_count": None, "outputs": [], "source": entry_source(1).strip().splitlines(keepends=True)})
        else:
            replace_source(setup, entry_source(1))
        replace_source(cells[0], "".join(cells[0]["source"]).split("\n\nRuntime chung Colab/Drive:", 1)[0] + NOTE)
    elif name == "02_preprocessing.ipynb":
        replace_source(cells[0], "".join(cells[0]["source"]).split("## 1.", 1)[0]
                       + "## 1. Runtime dùng chung Colab/Drive" + NOTE)
        replace_source(cells[1], entry_source(2) + "RUN_HISTORICAL_INSPECTION = False\n")
        old = "".join(cells[3]["source"])
        if "bootstrap" in old:
            old = old[old.index("try:\n    import numpy as np"):]
        replace_source(cells[3], "import json\nimport sys\n" + old.lstrip() if not old.startswith("import json") else old)
    elif name == "03_model_training.ipynb":
        replace_source(cells[0], TRAINING_INTRO)
        replace_source(cells[1], entry_source(3))
        replace_source(cells[2], "from src.models.notebook import ColabTraining\nsession = ColabTraining.open(RUNTIME)")
    elif name == "colab_smoke_test.ipynb":
        # VS Code can insert a user Drive-mount cell before setup; preserve it.
        # Identify the existing shared cells by their purpose, not their offset.
        setup = next((c for c in cells if c["cell_type"] == "code" and "bootstrap_runtime" in "".join(c["source"])), cells[1])
        preflight = next((c for c in cells if c["cell_type"] == "code" and "phase2_inputs = phase2_preflight(RUNTIME)" in "".join(c["source"])), cells[2])
        smoke = next((c for c in cells if c["cell_type"] == "code" and "smoke_result = smoke_test(RUNTIME)" in "".join(c["source"])), cells[3])
        replace_source(cells[0], "# Smoke test Colab/Drive — ba stage độc lập\n\n"
                       "**A:** Colab, mount, root và quyền ghi/đọc. **B:** copy/import source từ Drive. "
                       "**C:** baseline dữ liệu, manifest, checksum, schema/encoding và nạp train/validation. "
                       "A/B vẫn báo PASS nếu C thất bại. Không fit model hoặc mở CSV test." + NOTE)
        replace_source(setup, entry_source(3))
        replace_source(preflight, "from src.data.colab_runtime import phase2_preflight, smoke_test\nphase2_inputs = phase2_preflight(RUNTIME)")
        replace_source(smoke, "smoke_result = smoke_test(RUNTIME)")
    for index, cell in enumerate(cells):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"{name}:{index}", "exec")
    return notebook


def main():
    for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        migrate(path.name, notebook)
        path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("Runtime cells updated; historical outputs retained:", path.name)


if __name__ == "__main__":
    main()
