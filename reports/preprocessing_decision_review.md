# Phase 2 — Preprocessing đã hoàn tất theo chính sách được duyệt

CSV gốc `Disease and symptoms dataset.csv` giữ nguyên, SHA-256 `8de90603ebada467fc2703db2ee4292856e52d64e94982ef926df22fa0c21320`.
Fingerprint dữ liệu sau xử lý: `afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3`.

## Chính sách và số lượng qua từng bước

Loại `regurgitation` và `regurgitation.1` vì không xác minh được cách phân biệt chúng từ lời kể người dùng; đây là quyết định schema đã được duyệt cho ML và suy luận tương lai. Việc loại làm mất một phần phân biệt vector, không phải kết luận rằng cột vô ích hay accuracy sẽ tốt hơn. Diễn giải tạm thời: 1 = ghi nhận hiện diện, 0 = chưa ghi nhận hiện diện, không chứng minh vắng mặt lâm sàng.

| step | records | classes | symptom_features |
| --- | --- | --- | --- |
| validated_raw | 246945 | 773 | 377 |
| removed_ambiguous_features | 246945 | 773 | 375 |
| exact_dedup_remaining_vector_and_label | 188161 | 773 | 375 |
| recalculated_independent_vectors_per_class | 188161 | 773 | 375 |
| eligible_classes_after_schema_and_dedup | 187434 | 587 | 375 |
| generated_remaining_vector_groups | 187434 | 587 | 375 |
| validated_final_split_total | 187434 | 587 | 375 |

Thứ tự: xác thực raw → bỏ hai cột → exact dedup theo **vector còn lại và nhãn** → đếm lại vector/lớp → giữ lớp ≥10 → group theo vector còn lại → split. Giữ mọi nhãn khác nhau của cùng vector; không bỏ phiếu đa số. Ngưỡng 10 được tính sau schema/dedup, không dùng lại support trước bỏ cột. Còn **187,434 bản ghi, 587 lớp, 375 triệu chứng**, chưa loại cột hằng.

## Split cố định, seed 42

Dùng đúng thuật toán đã kiểm tra: hoán vị group với hạn ngạch khoảng 70/15/15, sửa thiếu lớp theo support tăng dần; chỉ chuyển group khi không làm mất lớp ở tập cho, tối thiểu thay đổi sai lệch support và phá hòa theo group ID. Không đổi seed/ngưỡng để tìm kết quả tốt hơn.

| split | dedup_records | pct_records | groups | classes |
| --- | --- | --- | --- | --- |
| train | 131248 | 70.0236 | 117211 | 587 |
| validation | 28120 | 15.0026 | 25127 | 587 |
| test | 28066 | 14.9738 | 25128 | 587 |

- Lớp vắng train/validation/test: `{'train': [], 'validation': [], 'test': []}`.
- Giao group: `{'train / validation': 0, 'train / test': 0, 'validation / test': 0}`; giao vector kiểm tra độc lập bằng pack-bit equality: `{'train / validation': 0, 'train / test': 0, 'validation / test': 0}`.
- Exact duplicate (vector, nhãn) còn lại: **0**.
- Nhóm nhiều nhãn được giữ: **12,728**.
- Lớp chỉ có 1 vector validation/test: **33/41**. Đủ mặt lớp không bảo đảm metric từng bệnh ổn định.
- Tính lại assignment và support với seed 42 cho cùng dữ liệu có thứ tự: **khớp hoàn toàn**. CSV nén dùng header gzip không timestamp/filename; đọc lại sau ghi khớp dữ liệu và thứ tự cột.

## Dữ liệu và artifact tái sử dụng

`data/processed/{train,validation,test}.csv.gz` gồm đúng danh sách triệu chứng đã duyệt theo thứ tự, rồi cột `diseases` dạng nhãn gốc. Nén CSV giảm I/O Drive, đọc trực tiếp bằng pandas. Không chèn group/row ID vào đặc trưng.

`artifacts/metadata/phase2/` chứa `feature_schema.json` (thứ tự cột), `label_mapping.json` (mã 0-based theo tên nhãn nguyên bản sắp xếp Unicode), `preprocessing_policy.json`, `split_metadata.json` (support từng lớp và lớp bị loại), `split_assignments.csv.gz` (raw data-row 1-based, group, split, split-row 0-based), `dataset_manifest.json` (SHA-256 raw/processed/từng file, phiên bản môi trường và mã nguồn). ID group phụ thuộc thứ tự dữ liệu/schema và gắn với fingerprint. Hàm `load_final_split` đọc đúng X/y/groups theo các artifact này; không thay label mapping giữa các tập.

Các đường dẫn trên tính từ output root đã cấu hình, lưu persistent trên Colab/Drive; source/cache có thể ở runtime tạm. Không tự mount, cài gói hoặc tải dữ liệu. Lần kiểm tra này dùng Windows Python; chưa có thực thi Colab thật.

**Test đã khóa:** chỉ dùng đánh giá cuối, không chọn đặc trưng/hyperparameter. Phase 1 đã thăm dò toàn CSV nên không tuyên bố test chưa từng được xem. Chưa fit `VarianceThreshold`, chọn đặc trưng, PCA hay mô hình. `VarianceThreshold(0)` chỉ được fit trên train bên trong model pipeline ở giai đoạn huấn luyện sau này; giữ nguyên mọi cột hằng ở Phase 2. Mọi thay đổi schema ở train/inference sau này phải đi qua artifact/pipeline đã duyệt, không tự bịa nghĩa lâm sàng cho cột.

Các báo cáo, bảng và hình kiểm tra trước đó giữ làm lịch sử; chúng mô tả giả định trước phê duyệt, không thay thế số liệu cuối trong báo cáo này. Raw và mọi kết quả Phase 1 giữ nguyên. **Dừng sau Phase 2, chưa huấn luyện hay triển khai chatbot.**
