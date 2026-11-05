"""Create teaching notebooks. Refuse to overwrite existing notebooks unless explicit."""
from pathlib import Path
import argparse
import inspect
import json
import sys
import textwrap
import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.data.paths import DriveUnavailableError, RuntimeCapabilities, detect_capabilities, mount_drive_at, project_root
from src.data.bootstrap import bootstrap_project, resolve_source_archive, unpack_source_archive


def md(text):
    return nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())


def code(text):
    return nbf.v4.new_code_cell(textwrap.dedent(text).strip())


BOOTSTRAP = r'''
from pathlib import Path
import os
import sys
import json
import hashlib
import importlib
import importlib.util
import zipfile
from pathlib import PurePosixPath
from dataclasses import dataclass

# Đường dẫn phải thuộc máy/runtime đang chạy kernel. Xem README về upload mã nguồn.
PROJECT_ROOT = None  # Hoặc DISEASE_PROJECT_ROOT; thư mục có configs/ và src/.
PATH_CONFIG = None   # Hoặc DISEASE_PATH_CONFIG; mặc định configs/runtime.json.
MOUNT_DRIVE = False  # Tùy chọn; không mount tự động, không bật trong local Python.
SOURCE_ARCHIVE = None  # ZIP source đã upload lên Drive/runtime; không phải ZIP dữ liệu.
SOURCE_DIRECTORY = None  # Mặc định tạo disease-prediction-ml/ trong CWD; không ghi đè source cũ.
''' + "\n# Defaults sinh từ configs/runtime.json; sửa ở config rồi rebuild, hoặc dùng env override.\nBOOTSTRAP_DEFAULTS = " + repr(json.loads((ROOT / "configs/runtime.json").read_text(encoding="utf-8"))["colab"]) + "\n\n" + "\n\n".join(inspect.getsource(f) for f in [DriveUnavailableError, RuntimeCapabilities, detect_capabilities, mount_drive_at, project_root, resolve_source_archive, unpack_source_archive, bootstrap_project]) + r'''

ROOT = bootstrap_project(BOOTSTRAP_DEFAULTS, root_override=PROJECT_ROOT, mount_requested=MOUNT_DRIVE,
                         source_archive=SOURCE_ARCHIVE, source_directory=SOURCE_DIRECTORY)
if not (ROOT / "src/data/audit.py").is_file():
    raise FileNotFoundError(
        f"Đã tìm thấy config tại {ROOT}, nhưng thiếu src/data/audit.py. "
        "Cần cả thư mục dự án (configs/, src/, notebooks/), không chỉ file .ipynb."
    )
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print(f"Project root: {ROOT}")
from src.data.paths import resolve_paths
runtime_paths = resolve_paths(ROOT, config_file=PATH_CONFIG)
'''

SETUP = BOOTSTRAP + r'''
import numpy as np
import pandas as pd
from IPython.display import display, Markdown
from src.data.io import read_config, save_json
from src.data.loader import dataset_path, load_dataset, prepare_dataset, sha256_file
from src.data.audit import audit_dataset
config = read_config(ROOT)
np.random.seed(config["seed"])
source_path = dataset_path(runtime_paths, config)
path = prepare_dataset(runtime_paths, source_path)
df = load_dataset(path, config["target"])
OUTPUT = runtime_paths.new_run()
save_json(OUTPUT.metadata_dir / "runtime.json", {
    **runtime_paths.as_dict(), "source_csv": str(source_path), "read_csv": str(path),
    "source_sha256": sha256_file(source_path), "run_id": OUTPUT.run_id,
})
print(f"Runtime: {runtime_paths.runtime}; CSV nguồn: {source_path}")
print(f"Run ID: {OUTPUT.run_id}")
print(f"Báo cáo mới: {OUTPUT.reports_dir}; metadata: {OUTPUT.metadata_dir}")
print(f"Đọc toàn bộ {len(df):,} dòng, {df.shape[1]} cột từ {path.name}. Raw chỉ được đọc.")
'''


def audit_cells():
    return [
        md('''
        # 00 — Dataset Audit

        **Mục tiêu:** kiểm tra tính hợp lệ của nguồn, schema, chất lượng và khả năng dùng cho phân loại bệnh.
        **Câu hỏi:** dữ liệu là gì, có bao nhiêu lớp, bao nhiêu mẫu độc lập, có mẫu trùng/xung đột hoặc nguy cơ leakage không?

        Chỉ Phase 1; không tiền xử lý để huấn luyện, không fit mô hình. Toàn bộ kết quả bên dưới tính từ CSV cấu hình.
        Nếu dữ liệu thiếu/sai schema, chương trình dừng kèm chỉ dẫn thay vì tạo dữ liệu giả.
        '''), code(SETUP),
        md('''
        ## 1. Nguồn, cấu trúc và phạm vi xác minh
        Nguồn ứng viên Mendeley và giới hạn xác minh được lưu trong `configs/dataset_source.json`.
        Tách nhãn khỏi đặc trưng; kiểm tra giá trị trước khi tối ưu dtype trong RAM. Không thay đổi tệp raw.
        '''),
        code('''
        import json
        source = json.loads((ROOT / config["source_metadata"]).read_text(encoding="utf-8"))
        display(Markdown(f"Nguồn ứng viên: [{source['title']}]({source['url']}), DOI `{source['doi']}`; version {source['version']}."))
        display(pd.DataFrame({"thuộc tính": list(source), "giá trị": [str(v) for v in source.values()]}))
        display(df.head(5).iloc[:, :10])
        audit = audit_dataset(df, config)
        s = audit["summary"]
        display(pd.DataFrame([{"chỉ số": k, "giá trị": v} for k, v in s.items()]))
        '''),
        md('''
        ## 2. Kiểu dữ liệu, giá trị thiếu, hằng và miền hợp lệ
        Ngưỡng gần hằng xét tỷ lệ giá trị phổ biến ≥99%; cột hằng là tập con.
        Phân biệt dấu hiệu nhị phân quan sát được với cách mã hóa đã được xác minh về lâm sàng.
        '''),
        code('''
        display(audit["missing"].sort_values("missing_count", ascending=False).head(15))
        display(audit["features"].head(15))
        display(audit["features"].query("constant or invalid_binary_count > 0"))
        display(audit["alias_candidates"])
        display(audit["duplicate_columns"])
        display(audit["label_collisions"])
        display(Markdown(f"Có **{s['missing_cells']:,}** ô thiếu, **{s['invalid_binary_cells']:,}** ô ngoài miền 0/1 và **{s['constant_features']}** cột hằng. Cờ này chưa quyết định loại cột; danh sách đầy đủ sẽ được lưu."))
        '''),
        md('''
        ## 3. Mẫu trùng và nhãn xung đột
        Vector nhị phân được pack lossless rồi so sánh byte bằng nhau; không dùng hash xác suất để kết luận trùng.
        “Dòng dư” bỏ bản đầu; “dòng thuộc nhóm lặp” tính cả bản đầu. Nhóm đặc trưng bỏ qua nhãn để phát hiện xung đột.
        '''),
        code('''
        groups = audit["pattern_groups"]
        display(groups.sort_values(["distinct_labels", "rows"], ascending=False).head(15))
        conflict_ids = groups.loc[groups["distinct_labels"] > 1, "pattern_id"].head(5)
        display(audit["pattern_labels"].query("pattern_id in @conflict_ids"))
        display(audit["class_patterns"].sort_values(["unique_patterns", "total_rows"]).head(20))
        display(Markdown(f"Có **{s['unique_feature_vectors']:,}** vector khác nhau từ **{s['rows']:,}** dòng; **{s['exact_duplicate_excess_rows']:,}** dòng dư nếu xét cả nhãn; **{s['conflicting_pattern_groups']:,}** nhóm có nhiều nhãn. Chia theo dòng có thể đưa cùng triệu chứng sang cả train và test."))
        '''),
        md('''
        ## 4. Rò rỉ nhãn và tính phù hợp ban đầu
        Kiểm tra tên cột chỉ là sàng lọc. Feature đặc hiệu không tự chứng minh leakage hay tính đúng lâm sàng.
        Cơ chế sinh dữ liệu, các cột đồng nghĩa, mã bệnh lẫn trong đặc trưng và trùng bệnh nhân cần tài liệu nguồn.
        Nhãn có đủ dòng chưa chắc có đủ vector độc lập để đánh giá.
        '''),
        code('''
        display(audit["class_distribution"].head(15))
        display(Markdown(f"**Đánh giá ban đầu: {s['recommendation']}**. Có {s['classes_with_lt5_rows']} lớp dưới 5 dòng và {s['classes_with_lt5_patterns']} lớp dưới 5 vector. EDA tiếp theo sẽ xét phân bố, quan hệ triệu chứng và điều kiện chia group."))
        print("Ứng viên leakage theo tên:", s["name_leakage_candidates"])
        '''),
        md('''
        ## 5. Xuất báo cáo và fingerprint
        Báo cáo ghi nguồn ứng viên, giới hạn xác minh, từng định nghĩa mẫu trùng và khuyến nghị ban đầu.
        CSV đầu vào được băm trước/sau; bảng pattern_id phục vụ thiết kế chia nhóm ở giai đoạn sau, chưa chia dữ liệu.
        '''),
        code('''
        from src.data.reporting import export_audit
        from src.data.io import sha256_file
        manifest = export_audit(ROOT, path, config, df, audit, output=OUTPUT)
        assert sha256_file(path) == manifest["sha256"], "Raw thay đổi trong lúc audit!"
        display(Markdown((OUTPUT.reports_dir / "dataset_audit.md").read_text(encoding="utf-8")))
        print(f"Báo cáo: {OUTPUT.reports_dir}; fingerprint: {OUTPUT.metadata_dir}")
        '''),
    ]


def write_notebook(name, cells, overwrite=False):
    path = ROOT / "notebooks" / name
    if path.exists() and not overwrite:
        raise FileExistsError(f"Không ghi đè {path}; chỉ dùng --overwrite với notebook do dự án sinh.")
    path.parent.mkdir(parents=True, exist_ok=True)
    notebook = nbf.v4.new_notebook(cells=cells)
    from scripts.update_colab_notebooks import migrate
    migrate(name, notebook)  # Never emit an archive-era runtime again.
    notebook.metadata = {"kernelspec": {"display_name": "Python 3 (Disease ML)", "language": "python", "name": "python3"},
                         "language_info": {"name": "python", "version": "3.11"}}
    nbf.validate(notebook)
    nbf.write(notebook, path)
    print(path.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    write_notebook("00_dataset_audit.ipynb", audit_cells(), args.overwrite)
