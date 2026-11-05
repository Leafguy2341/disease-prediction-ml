"""Persist evidence, provenance and Vietnamese interpretations for Phase 1."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path

import pandas as pd

from .io import markdown_table, save_json, save_table, sha256_file
from .paths import OutputPaths, output_paths


def _package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None  # nbclient/nbformat are not needed by an interactive EDA runtime.


def export_audit(root: Path, path: Path, config: dict, frame: pd.DataFrame, audit: dict, *, output: OutputPaths | None = None) -> dict:
    destination = output if output is not None else output_paths(root)
    source = json.loads((root / config["source_metadata"]).read_text(encoding="utf-8"))
    manifest = {
        "dataset_name": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path),
        "created_utc": datetime.now(timezone.utc).isoformat(), "seed": config["seed"],
        "source": source, "configuration": config,
        "runtime_packages": {name: _package_version(name) for name in
                             ["numpy", "pandas", "matplotlib", "seaborn", "nbformat", "nbclient", "ipykernel"]},
        "column_order": list(frame.columns),
        "scope": "Descriptive audit/EDA only; no split, fitted transform, classifier or chatbot.",
    }
    original_notebook = root.parent / "seminar_chapter6_model_evaluation.ipynb"
    if original_notebook.is_file():
        manifest["preserved_existing_notebook"] = {"name": original_notebook.name, "sha256": sha256_file(original_notebook)}
    save_json(destination.metadata_dir / "dataset_manifest.json", manifest)
    save_json(destination.reports_dir / "dataset_audit.json", audit["summary"])
    for name in ["features", "missing", "pattern_groups", "pattern_labels", "class_distribution", "class_patterns",
                 "duplicate_columns", "alias_candidates", "label_collisions"]:
        save_table(destination, "audit_" + name, audit[name])
    save_table(destination, "audit_row_pattern_ids", pd.DataFrame({
        "data_row_1based": range(1, len(frame) + 1), "pattern_id": audit["pattern_ids"],
        "disease": frame[config["target"]],
    }))
    summary = audit["summary"]
    report = f"""# Báo cáo Dataset Audit

Kết quả tính trên toàn bộ `{path.name}`; không lấy mẫu. SHA-256: `{manifest['sha256']}`.
Số dòng dữ liệu trong bảng ánh xạ là 1-based, không tính header CSV. `pattern_id` chỉ có ý nghĩa kèm fingerprint và thứ tự cột của tệp này.

## Nguồn và phạm vi xác minh

Nguồn ứng viên: [{source['title']}]({source['url']}), DOI `{source['doi']}`, contributor {source['contributor']}, version {source['version']}, công bố {source['published']}, giấy phép {source['license']}; tra cứu ngày {source['accessed']}.
Tên tệp, schema và số lớp/đặc trưng khớp mô tả. Chưa có checksum nhà xuất bản hoặc lịch sử tải xuống để xác nhận đây là bản gốc không chỉnh sửa.
Nhà xuất bản mô tả dữ liệu sinh nhân tạo. Không có căn cứ xem mỗi dòng là một bệnh nhân thật; tuyên bố về tỷ lệ mắc bệnh và độ nặng chưa được kiểm chứng độc lập.
Trang nguồn không cung cấp quy trình kiểm định lâm sàng hoặc mã sinh dữ liệu đủ để tái tạo trong nội dung đã xem.

## Kết quả cấu trúc và chất lượng

{markdown_table(pd.DataFrame([{'Chỉ số': k, 'Giá trị': v} for k, v in summary.items()]), limit=60)}

`exact_duplicate_excess_rows` = số dòng dư sau khi giữ một dòng cho mỗi cặp (vector, nhãn).
`repeated_pattern_excess_rows` = số dòng dư sau khi giữ một dòng cho mỗi vector, bỏ qua nhãn.
`rows_in_repeated_patterns` tính tất cả dòng thuộc nhóm vector có kích thước >1, gồm cả bản đầu tiên.
`near_constant_features_including_constant` dùng tần suất giá trị chiếm ưu thế ≥{config['near_constant_threshold']:.0%}; đây chỉ là cờ mô tả, chưa loại cột.

## Nhãn, ý nghĩa đặc trưng và leakage

Nhãn `{config['target']}` được tách khỏi X khi phân tích vector triệu chứng. Bảng `audit_features.csv` chứa tên, dtype gốc, miền giá trị, tỷ lệ thiếu, tần suất, cờ hằng và gần hằng của từng cột.
Từ điển chuyên môn chưa được xác minh: tên cột tiếng Anh gợi ý triệu chứng, không chứng minh độ tin cậy y khoa.
Các cột nghi vấn do tên: {summary['name_leakage_candidates']}. Không có cờ theo tên không đồng nghĩa không có leakage.
`audit_alias_candidates.csv` kiểm tra hậu tố như `.1`; không tự gộp các tên giống nhau. `audit_duplicate_columns.csv` chỉ báo các cột có vector giá trị giống hệt, gồm nhóm cột hằng.
Không có patient ID, thời gian hay cơ sở khám để kiểm tra trùng bệnh nhân hoặc chia theo bệnh viện/thời gian. Quan hệ đặc trưng–nhãn quá đặc hiệu cần xét cùng cơ chế sinh nhân tạo, chưa thể kết luận leakage nhân quả.

## Đánh giá ban đầu: {summary['recommendation']}

Có cấu trúc phân loại có giám sát với {summary['classes']} lớp. Tính đại diện phải đánh giá bằng **số vector độc lập theo lớp**, không chỉ số dòng.
Có {summary['conflicting_pattern_groups']:,} vector mang nhiều nhãn và {summary['classes_with_lt5_patterns']} lớp có dưới 5 vector.
Mức majority theo vector trên toàn bộ tệp = {summary['empirical_pattern_majority_ceiling']}; đây là giới hạn ghi nhớ thực nghiệm của bộ phân loại tất định trên chính các dòng đã quan sát, không phải độ chính xác kiểm định hoặc giới hạn quần thể.
Kết luận ban đầu dành cho nghiên cứu học phần; các điều kiện cụ thể và phân tích phân tách sẽ được cập nhật trong EDA. Không suy rộng sang chẩn đoán lâm sàng.

## Ngăn leakage và hướng xử lý tiếp theo

Không chia ngẫu nhiên theo dòng khi vector lặp. Giữ mọi dòng có cùng vector trong cùng một group cho mọi phép chia và CV, kể cả khi khác nhãn.
Kiểm tra số group của từng lớp trước khi đề xuất số fold. Lớp có một group không thể đồng thời có train và test độc lập; không tự nhân bản, bỏ lớp hoặc hợp nhất bệnh.
Chưa chọn quy tắc cho xung đột nhãn; cần quyết định trên tập phát triển và tài liệu nguồn, báo cáo ảnh hưởng nếu loại/gộp.
Imputation, scaling, feature selection và PCA sau này chỉ được fit trên train/CV training fold. Test cuối khóa riêng, không dùng chọn siêu tham số.

## Giao diện tiếng Việt

Chưa có ánh xạ Việt–Anh, kiểm định từ đồng nghĩa/phủ định hay dữ liệu hội thoại. Giá trị 0 không chứng minh triệu chứng đã được hỏi và phủ nhận; không tự mã hóa mọi thông tin chưa nhắc đến thành âm tính.
Các cặp gần nghĩa và hậu tố `.1` cần được rà soát trước khi xây từ điển. ML sẽ dự đoán nhãn; LLM chỉ hỗ trợ hiểu tiếng Việt, hỏi rõ và giải thích. Phase 1 chưa triển khai giao diện hoặc chatbot.
"""
    (destination.reports_dir / "dataset_audit.md").write_text(report, encoding="utf-8")
    return manifest
