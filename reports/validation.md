# Xác minh Phase 1 — 21/10/2026

## Thực thi

- Python 3.11.9; dependency trực tiếp được khóa trong `requirements.txt` và phiên bản thực tế được ghi trong manifest.
- `python -m pytest -q`: **11 passed**. Các fixture kiểm tra trùng vector/nhãn, byte cuối khi pack bit, dữ liệu hỗn hợp/thiếu, nhãn thiếu, schema lỗi, đường dẫn thiếu, bảo toàn giá trị 256/-1 và overflow khi đếm đồng xuất hiện. Phi được đối chiếu với `pandas.DataFrame.corr()`.
- `python scripts/run_phase1.py`: hai notebook chạy từ đầu tới cuối, **15 code cells**, **0 error outputs**, **0 stderr streams**; notebook EDA nhúng **8 hình PNG**.
- `python scripts/validate_deliverables.py`: **PASS**; **26 bảng CSV**, **8 PNG và 8 SVG**. Số liệu mẫu trùng được đối chiếu độc lập bằng `pandas.DataFrame.duplicated()` trên CSV thật, tách biệt với cách pack bit của tiện ích audit.
- Đã đối chiếu tổng dòng giữa bảng lớp, bảng vector, bảng vector–nhãn và ánh xạ từng dòng; đường chéo ma trận đồng xuất hiện bằng tần suất; tổng số triệu chứng bằng tổng có trọng số từ phân bố số triệu chứng/dòng; ma trận phi đối xứng.

Chi tiết máy đọc được: `artifacts/metadata/validation.json`; thông tin từng lần thực thi: `artifacts/metadata/execution_all.json`.

## Kiểm tra trực quan

Đã mở và kiểm tra cả tám PNG xuất từ Matplotlib:

1. `01_class_distribution`: histogram và đường hạng toàn bộ lớp, trục log có nhãn rõ.
2. `02_class_extremes`: chỉ 15 lớp ở mỗi đầu; tên đọc được, không chồng nhãn.
3. `03_symptom_frequency`: nhóm phổ biến và nhóm hiếm có xuất hiện được ghi rõ; hai trục tần suất riêng.
4. `04_active_symptoms`: cột số triệu chứng mỗi dòng có tiêu đề, nhãn trục và miền giá trị rõ.
5. `05_symptom_relationships`: 15 triệu chứng, tên được xuống dòng/xoay; Jaccard và phi có thang màu riêng, bỏ đường chéo để tập trung quan hệ giữa cột.
6. `06_selected_disease_profiles`: tối đa 6 lớp, 20 triệu chứng; có support và chú giải tỷ lệ.
7. `07_similar_disease_profiles`: 12 cặp, tên dài xuống dòng; tiêu đề ghi ngưỡng support và trục cosine.
8. `08_redundancy`: hai biểu đồ với trục log và giải thích màu cho nhóm xung đột.

Không phát hiện lỗi font tiếng Việt, tiêu đề bị cắt hoặc hàng trăm nhãn chồng lên nhau. SVG được xuất từ cùng đối tượng figure; validator kiểm tra định dạng và sự hiện diện của cả hai phiên bản. Nhận xét về độ đọc được là kiểm tra thủ công; kiểm tra định dạng/tính nhất quán là tự động.

## Bảo toàn và phạm vi

CSV gốc giữ nguyên vị trí và SHA-256 trước/sau:

`8de90603ebada467fc2703db2ee4292856e52d64e94982ef926df22fa0c21320`

Notebook có sẵn `seminar_chapter6_model_evaluation.ipynb` giữ nguyên SHA-256:

`5ec3bb9ebdfbdb7373f5cc82726610e337e0f35a57ae4336f95023d3b5d1c569`

Không tạo dataset processed, final test hoặc artifact mô hình. Các thư mục dành cho giai đoạn sau chỉ có file giữ thư mục/package. Notebook 02–06 được hoãn. Không triển khai chatbot.
