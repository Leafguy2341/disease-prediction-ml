# Dữ liệu raw

CSV hiện có là `Disease and symptoms dataset.csv` trong thư mục này; nội dung được giữ nguyên.
`src/data/loader.py` phát hiện CSV thực tế theo runtime config, vẫn hỗ trợ layout cũ ở thư mục cha trong local. Không tự di chuyển, sửa hoặc đổi tên file gốc.

Để dùng file khác, đặt `raw_dataset` trong runtime config hoặc biến môi trường `DISEASE_DATA_PATH`. Colab mặc định tìm dưới `MyDrive/ML_Projects/disease-prediction-ml/data/raw/` sau khi Drive đã mount. Xem `docs/portable_runtime.md`.
Fingerprint, kích thước và nguồn ứng viên nằm trong `artifacts/metadata/dataset_manifest.json` sau khi chạy audit.
Chưa xác minh danh tính tệp với checksum nhà xuất bản; xem `configs/dataset_source.json`.

## Phân phối Git LFS và attribution

CSV raw được giữ nguyên190.786.867byte, SHA256 `8de90603ebada467fc2703db2ee4292856e52d64e94982ef926df22fa0c21320`. GitHub phân phối qua Git LFS; sau clone chạy `git lfs pull`, rồi `python -B -m scripts.verify_repository_data --allow-locked-bytes`. Không dùng LFS pointer như một CSV thật.

Nguồn ứng viên: Bran Stark, *Disease and symptoms dataset 2023*, version1, Mendeley Data, DOI [10.17632/2cxccsxydc.1](https://data.mendeley.com/datasets/2cxccsxydc/1), giấy phép **CC BY4.0** theo trang publisher. Dữ liệu được publisher mô tả là sinh nhân tạo. Bản local có schema/counts phù hợp nhưng không có publisher checksum hoặc lịch sử download gốc để xác nhận binding tuyệt đối; không coi đây là dữ liệu bệnh nhân được kiểm định. Những khẳng định về prevalence/severity của nguồn không được xác nhận độc lập.

Processed splits là dẫn xuất theo chính sách được ghi trong `reports/preprocessing_decision_review.md` và `artifacts/metadata/phase2/dataset_manifest.json`: bỏ hai feature chưa rõ nghĩa, dedup, lọc lớp và group-disjoint split. Raw không được sửa nội dung. Audit theo run được giữ trong `artifacts/metadata/runs/`; manifest Phase2 là identity hiện hành cho raw/processed. Attribution này đi cùng việc phân phối lại trong repository, không thay source/license của mô hình khác.
