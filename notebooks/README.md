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



## Academic review 2026-11-11 ? ??c k?t qu?, kh?ng Run All

| Notebook | Vai tr? | C?ch tr?nh b?y an to?n |
|---|---|---|
| 00 | Raw audit/duplicates/conflicts | ??c outputs v? report ?? l?u |
| 01 | EDA/support/redundancy | Gi?8nh?m h?nh ?? c? |
| 02 | Preprocessing/split/schema | ??c finalized evidence; kh?ng t?i t?o Phase2 |
| 03 | Experiment1baseline + Experiment3tuning | Markdown t?ng h?p cu?i; tuning-switch l?ch s? hi?nTrue |
| 04 | Experiment2baseline ensemble + Experiment4tuned ensemble | Markdown t?ng h?p cu?i; switchFalse, kh?ng b?t ch? ?? xem |
| 05 | Structured inference5baseline | Gi?i th?ch m?i ??u notebook; examples/timings kh?ng l? overall metrics |
| 06 | Completed final-test viewer | GateFalse, authorizationr?ng; kh?ng ch?y l?i evaluation |
| colab_smoke_test | Shared bootstrap/import/session/integrity | Kh?ng train; freshColab ch?a ch?y trong review n?y |

Snapshot nguy?n byte8notebooks,125cell ban ??u v? [b?ng ch?ng b?o to?n](../reports/academic_review_20261111/preservation_verification.json) gi? m?i code/output/count/metadata/ID/order. Ch? th?m5Markdown v?o03/04/05. [Cell candidates](../reports/academic_review_20261111/cell_candidates.json) ch?a ???c x?a/move; output diagnostic v?n l? provenance. Dynamic dependencies/magics ch? ki?m t?nh, kh?ng tuy?n b? notebook ?? ch?y l?i th?nh c?ng.

[ML_EXPERIMENTS](../docs/ML_EXPERIMENTS.md#academic-presentation-review--2026-11-11) t?p trung b?n th? nghi?m; [deployment](../docs/DEPLOYMENT_GUIDE.md#academic-review--2026-11-11-python-entrypoint) h??ng d?n ch?y API b?ng Python ngo?i Jupyter. Kh?ng d?ng final test ch?n l?i model.
