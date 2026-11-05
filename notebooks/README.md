# Notebook Colab/Drive

[Hướng dẫn duy nhất](../docs/phase3_colab.md): đồng bộ source canonical trên Drive khi code đổi → chọn Colab → mount Drive → restart/chạy notebook. Không có bước upload colab-session, receipt, ZIP hoặc .pyz.

- `00_dataset_audit.ipynb`: audit raw; chỉ Stage A/B và raw CSV, không cần Phase 2/3 artifact.
- `01_eda.ipynb`: EDA raw, giữ code/chart/output lịch sử; output chạy mới vào run riêng.
- `02_preprocessing.ipynb`: giữ chính sách/tính toán/đối chiếu bộ Phase 2 đã khóa; phụ lục lịch sử mặc định tắt.
- `03_model_training.ipynb`: cùng bootstrap; Stage C/resource checks trước khi nạp train/validation. Năm cell model giữ nguyên, không chạy trong nhiệm vụ hạ tầng.
- `colab_smoke_test.ipynb`: A môi trường/Drive, B source/imports, C integrity/schema/encoding. Run All an toàn: không fit model hoặc mở CSV test. A/B vẫn PASS nếu C thất bại.

Runtime config: `configs/runtime.json`; data integrity baseline: `configs/phase2_integrity.json`. Source chạy ở `/content/disease-prediction-ml-runtime/`, persistent data/output ở Drive. Outputs lưu trước đây là lịch sử, không chứng minh Colab mới đã chạy thành công.

Smoke A/B/C của luồng mới đã được người dùng xác nhận PASS trên Colab thật ngày 2026-10-27, Python 3.13.16; không train hoặc mở test. Chi tiết ở [báo cáo xác minh](../docs/portability_validation.md).
# Phase 4 — Ensemble

[04_ensemble.ipynb](04_ensemble.ipynb) dùng checkpoint Phase 3 có sẵn, shared Colab/Drive bootstrap và chỉ validation. Xem [hướng dẫn chạy](../docs/phase4_ensemble.md). Không fit baseline/calibrator hoặc mở test. Cần đồng bộ source mới lên Drive rồi Restart Kernel; source tại `src/models/ensemble.py`. Packet Colab người dùng gửi ngày 2026-10-28 đã được kiểm SHA-256: cả 5 tổ hợp hoàn tất, LR vẫn dẫn đầu Macro F1 0,78780814, kiểm input375 PASS, 0 fit/0 truy cập test. [Kết quả và khuyến nghị](../docs/PROJECT_DEVELOPMENT_LOG.md#17-2026-10-28--hoàn-tất-phase-4-từ-kết-quả-colab). Không thay outputs notebook local bằng dữ liệu mô phỏng.

