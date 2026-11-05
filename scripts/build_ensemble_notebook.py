"""Create only notebook 04, with the existing shared entry; never overwrite outputs."""
from pathlib import Path
import json
import uuid

from update_colab_notebooks import entry_source

ROOT = Path(__file__).resolve().parents[1]


def build():
    cells = []

    def add(kind, source):
        cell = {"cell_type": kind, "id": uuid.uuid4().hex[:8], "metadata": {}, "source": source.strip().splitlines(keepends=True)}
        if kind == "code":
            compile(source.strip(), "04_ensemble", "exec")
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)

    add("markdown", """# 04 — Ensemble từ checkpoint Phase 3, Colab + Drive

Chỉ dùng validation **28.120 dòng / 375 feature / 587 lớp**, run `baseline-v1-f8a5bfdb7b4c12cd`.
Không fit baseline, calibrator, tune trọng số hoặc mở test. Notebook này chưa có output Colab được xác minh lúc tạo.

## 1. Shared runtime và kiểm checkpoint

Chọn kernel Colab, mount Drive bằng lệnh extension, đồng bộ source mới rồi Restart Kernel.
Setup dưới gọi bootstrap **hiện có**, phase=3 để dùng source/dependency/checkpoint Phase 3;
không cần bootstrap mới. Xem [cách chạy Phase 4](../docs/phase4_ensemble.md).""")
    add("code", entry_source(3))
    add("code", """import numpy as np
import pandas as pd
from IPython.display import display, Markdown
from src.models.notebook import ColabTraining
from src.models.ensemble import (
    Phase4, HARD, SOFT, BASELINE, hard_vote,
    diversity_figure, comparison_figure, interpretation, save_phase4, emit_phase4_result,
)

session = ColabTraining.open(RUNTIME)  # Chỉ preflight; không gọi session.train/train_model.
phase = Phase4(session)
verification = phase.verify()
display(verification)
print("Identity/checksum/y_true/row order/mapping/metrics đã kiểm; chỉ train/validation.")""")
    add("markdown", """## 2. Độ khác biệt lỗi — cùng 28.120 hàng

Một heatmap **5×5**: **D** = tỷ lệ hai model dự đoán khác nhau; **J** = tỷ lệ cả hai cùng sai.
Màu theo J. Đường chéo D=0; J là tỷ lệ lỗi của model. Hai nhãn dự đoán khác nhau có thể đều sai.
Bảng rescue bên dưới có hàng A sai, cột B đúng; không phải tỷ lệ điều kiện trên các hàng A sai.""")
    add("code", """diversity_fig = diversity_figure(phase.diversity)
display(diversity_fig)
display(pd.DataFrame(phase.diversity["a_wrong_b_correct"],
                     index=phase.diversity["names"], columns=phase.diversity["names"]).round(5))""")
    add("markdown", """## 3. Hard Voting — ba tổ hợp cố định

LR + SVC + KNN; LR + SVC + NB; LR + SVC + RF. Mỗi model một phiếu.
Nhãn nhiều phiếu nhất thắng; khi ba nhãn khác nhau, ưu tiên dự đoán LR.
Quy tắc tổng quát cho các nhãn đang hòa: LR → SVC → KNN → NB → RF, không chọn theo mã nhãn nhỏ nhất.
Không thử toàn bộ tổ hợp hoặc tối ưu trọng số.""")
    add("code", """display(pd.DataFrame([{"combination": key, "members": " + ".join(members)} for key, members in HARD.items()]))
hard_results = phase.evaluate_hard()
display(hard_results.round(6))

# Minh họa quá trình vote trên 8 hàng validation thực, không fit model.
members = HARD["hard_lr_svc_knn"]
voted, tie_count = hard_vote(phase.predictions, members, len(phase.classes))
example = {name: [phase.classes[i] for i in phase.predictions[name][:8]] for name in members}
example["hard_vote"] = [phase.classes[i] for i in voted[:8]]
example["y_true"] = [phase.classes[i] for i in phase.y[:8]]
display(pd.DataFrame(example))
print("Số hàng phải phá hòa của tổ hợp này:", tie_count)""")
    add("markdown", """## 4. Xác suất cho Soft Voting

Chỉ LR/NB/RF/KNN. LinearSVC không tham gia; không fit calibrator, không softmax decision scores,
không tạo one-hot từ hard predictions. Ưu tiên `y_proba` đã lưu trong payload Phase 3 được kiểm checksum,
có class_ids và metadata `probability_method=predict_proba`. Nếu không có, gọi `predict_proba` của checkpoint tin cậy.
Kiểm class order, cùng hàng validation, finite/nonnegative, tổng mỗi hàng ≈1 và argmax khớp hard prediction gốc.

Inference theo batch 64, model load tuần tự. Xác suất nằm trong cache tạm `/content`, không ghi ma trận lớn lên Drive.
KNN có thể mất vài phút. Các warning mới được ghi riêng; không có fitting. Nếu môi trường/source/RAM không hỗ trợ,
ghi lý do và bỏ qua tổ hợp thiếu probability; checksum sai thì dừng. Xác suất hợp lệ về cấu trúc chưa chứng minh calibration.""")
    add("code", """probability_summary = phase.prepare_probabilities(trusted=True)  # Chỉ checkpoint do dự án của bạn tạo.
display(probability_summary)
print("Limitations:", phase.limitations)""")
    add("markdown", """## 5. Soft Voting — hai tổ hợp cố định

LR + NB + RF; LR + KNN + NB. Lấy trung bình xác suất với trọng số đều rồi chọn nhãn có giá trị cao nhất.
Nếu bằng nhau chính xác: so xác suất LR giữa các nhãn đang hòa, rồi theo tên nhãn tiếng Anh Unicode.
Không tối ưu trọng số theo validation. Tổ hợp chưa đủ dữ liệu có metric trống, không thay bằng điểm giả.""")
    add("code", """display(pd.DataFrame([{"combination": key, "members": " + ".join(members), "weights": "uniform"} for key, members in SOFT.items()]))
soft_results = phase.evaluate_soft()
display(soft_results.round(6))""")
    add("markdown", """## 6. So sánh với Logistic Regression

Macro F1 là metric chính, zero_division=0. Baseline phải tái lập **0.78780814** trong tolerance làm tròn8 chữ số.
Ứng viên đứng đầu được chọn theo Macro F1, hòa chính xác thì ít model hơn rồi ID ổn định.
Chênh lệch nhỏ không đồng nghĩa có ý nghĩa thống kê; validation đã dùng nhiều lần để so sánh.""")
    add("code", """display(phase.table().round(6))
comparison_fig = comparison_figure(phase)
display(comparison_fig)
display(Markdown(interpretation(phase)))""")
    add("markdown", """## 7. Inference một vector và trade-off triển khai

Wrapper tham chiếu pipeline Phase 3, không sao chép hoặc fit lại model; input vẫn là375 feature trước variance.
Kiểm một hàng validation375 feature cho kết quả giống bước evaluate, không thực hiện benchmark latency.
Kích thước dưới là file nén, không phải peak RAM. Tổng thời gian baseline là tham chiếu chi phí tương đối,
không phải thời gian ensemble đo mới hoặc latency một người dùng. KNN là điểm cần cân nhắc nếu mức cải thiện nhỏ.""")
    add("code", """display(pd.DataFrame([phase.single_input_check(trusted=True)]))
display(phase.table()[["combination", "status", "base_models", "pipeline_bytes", "original_base_predict_seconds_sum", "delta_macro_f1_vs_lr"]].round(6))""")
    add("markdown", """## 8. Lưu kết quả validation về Drive

Một run mới trong reports/runs và artifacts/metadata/runs, định nghĩa trong artifacts/models/phase4.
Lưu bảng, đúng hai hình, predictions ensemble, combo definitions và manifest/checksum. Không ghi đè Phase2/3.
Định nghĩa gồm cả baseline nếu LR vẫn là lựa chọn tốt nhất. Chỉ ghi đề xuất; chưa mở test và chưa chọn model cuối thay người dùng.""")
    add("code", """phase4_result = save_phase4(phase, diversity_fig, comparison_fig)
print("Manifest Drive:", runtime_paths.storage_root / phase4_result["manifest_relative"])
print("Candidate:", phase4_result["candidate"])
print("Report:", runtime_paths.storage_root / "reports/runs" / phase4_result["run_id"] / "phase4_validation.md")
emit_phase4_result(phase4_result)  # Copy Cell Output hai dòng PHASE4_* để cập nhật log/audit.
phase.close()  # Dọn cache probability tạm; kết quả quan trọng đã lưu Drive.
print("Dừng Phase 4 validation. Chưa evaluate test hoặc triển khai chatbot.")""")
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}


if __name__ == "__main__":
    path = ROOT / "notebooks/04_ensemble.ipynb"
    if path.exists():
        raise FileExistsError(f"Giữ notebook/output hiện có: {path}")
    path.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(path)
