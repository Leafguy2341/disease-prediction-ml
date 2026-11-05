"""Create the optional runtime smoke test, with no installs, downloads or implicit mounts."""
from build_notebooks import BOOTSTRAP, md, code, write_notebook

cells = [
    md('''
    # Smoke test — Local / VS Code Colab / Colab browser

    Mục tiêu: kiểm tra source imports, runtime config, Drive đã truy cập được, CSV thực tế và ghi/đọc metadata tại storage lưu lâu dài. Không chạy EDA, preprocessing hoặc training.

    Trước khi chạy: đưa cả mã nguồn lên runtime và cài dependencies theo README nếu thiếu. Chọn `configs/runtime.colab.example.json` bằng `DISEASE_PATH_CONFIG` khi dùng Colab. Drive không được mount tự động; dùng lệnh của extension/browser hoặc bật `MOUNT_DRIVE` trong cell sau chỉ khi runtime hỗ trợ.
    Không có Colab thật thì kết quả smoke ở local không chứng minh đã xác minh Colab. `/content` và bản cache là tạm thời.
    '''), code(BOOTSTRAP),
    code('''
    from dataclasses import asdict
    import pandas as pd
    from src.data.paths import detect_capabilities
    from src.data.loader import dataset_path, prepare_dataset, sha256_file, load_dataset
    from src.data.io import read_config, save_json
    from src.data.audit import audit_dataset
    from src.data.eda import analyze_eda

    config = read_config(ROOT)
    source_path = dataset_path(runtime_paths, config)
    read_path = prepare_dataset(runtime_paths, source_path)
    sample = pd.read_csv(read_path, nrows=5)
    assert config["target"] in sample.columns
    assert callable(audit_dataset) and callable(analyze_eda) and callable(load_dataset)
    assert sha256_file(source_path) == sha256_file(read_path)
    print("Capabilities (API có mặt chưa đảm bảo mount/OAuth được hỗ trợ):", asdict(detect_capabilities()))
    print(runtime_paths.as_dict())
    print("CSV thực tế:", source_path.name, "; sample shape:", sample.shape)
    '''),
    code('''
    import json
    OUTPUT = runtime_paths.new_run("smoke")
    marker = OUTPUT.metadata_dir / "smoke.json"
    payload = {"runtime": runtime_paths.runtime, "source_sha256": sha256_file(source_path),
               "imports": "PASS", "csv_header": "PASS", "persistent_write_read": "PASS"}
    save_json(marker, payload)
    assert json.loads(marker.read_text(encoding="utf-8")) == payload
    print(f"Run ID: {OUTPUT.run_id}")
    print("SMOKE PASS tại runtime này; metadata:", marker)
    print("Chưa xác minh khả năng tồn tại sau reset runtime: kiểm tra lại marker từ phiên tiếp theo.")
    '''),
]

if __name__ == "__main__":
    write_notebook("colab_smoke_test.ipynb", cells)
