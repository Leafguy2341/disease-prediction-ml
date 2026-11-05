# Dữ liệu raw

CSV hiện có là `Disease and symptoms dataset.csv` trong thư mục này; nội dung được giữ nguyên.
`src/data/loader.py` phát hiện CSV thực tế theo runtime config, vẫn hỗ trợ layout cũ ở thư mục cha trong local. Không tự di chuyển, sửa hoặc đổi tên file gốc.

Để dùng file khác, đặt `raw_dataset` trong runtime config hoặc biến môi trường `DISEASE_DATA_PATH`. Colab mặc định tìm dưới `MyDrive/ML_Projects/disease-prediction-ml/data/raw/` sau khi Drive đã mount. Xem `docs/portable_runtime.md`.
Fingerprint, kích thước và nguồn ứng viên nằm trong `artifacts/metadata/dataset_manifest.json` sau khi chạy audit.
Chưa xác minh danh tính tệp với checksum nhà xuất bản; xem `configs/dataset_source.json`.
