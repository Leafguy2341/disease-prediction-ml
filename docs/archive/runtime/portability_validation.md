> ARCHIVE — Bản tại thời điểm trước hợp nhất tài liệu. Các trạng thái và lệnh cũ không phải hướng dẫn hiện hành. Xem [chỉ mục hiện hành](../../README.md) và [triển khai](../../DEPLOYMENT_GUIDE.md). Đường dẫn trong code block vẫn tính từ project root.

# Xác minh kiến trúc Colab trực tiếp từ Drive — 2026-10-27

Luồng hiện hành: [hướng dẫn duy nhất](phase3_colab.md). Không dùng ZIP/.pyz/source receipt/colab-session. Phần deployment cũ dưới đây chỉ là lịch sử.

## Kết quả hiện tại

- **120 passed, 13 deselected** trên Python Windows có sẵn. Không tạo/dùng `.venv`, không fit model.
- 11 bài có fit model và 2 bài embedded/updater ZIP cũ không được chọn. Không chạy `tests/test_data_regression.py` (tái tính dữ liệu thật/đọc test) hoặc `tests/test_phase2_notebook.py` (kiểm builder ZIP cũ, phụ thuộc nbformat chưa có trên interpreter kiểm tra). Đây không phải tuyên bố đã chạy toàn bộ suite.
- Unit fixtures kiểm canonical root, local kernel bị từ chối, Drive/source thiếu, cú pháp source hỏng, copy/import từ workspace mới, source đổi giữa hai phiên, module cũ còn trong kernel, source-only upload không cần dữ liệu, và bảo toàn file người dùng/archive cũ.
- Fixture subprocess có mock cổng nhận diện Colab để kiểm độc lập Stage A/B/C. A/B PASS khi manifest Phase 2 thiếu và C FAIL; 00 khởi động khi thiếu config/artifact Phase 2/3. Đây là unit test trên Windows, không phải Colab integration PASS.
- Data integrity kiểm manifest với baseline được duyệt riêng; checksum lỗi báo file/expected/actual. Tests loader từ chối feature order hoặc nhãn lệch mapping. Không mở CSV test trong preflight.
- Data-loading check trên dữ liệu dự án thật ở Windows đạt train **131248 × 375 / 587 nhãn / 117211 group** và validation **28120 × 375 / 587 nhãn / 25127 group**. Cache tạm được xóa, không model fitting. Manifest local SHA vẫn `ca20a551b1bf773c3dac59af40a56efa6552919e84136d44dd7117c39d038e02`.
- SHA-256, size và mtime của **125 file được bảo vệ không đổi**: raw/processed/metadata Phase 2/report, config phase2/3, code transformations, training.py và model reporting.py. Sáu archive ZIP/.pyz lịch sử giữ nguyên SHA/mtime.
- Tất cả notebook giữ cell IDs, metadata và outputs. 00/01/02 chỉ đổi cell setup; 03 chỉ đổi giới thiệu/setup, mọi cell data/pipeline/model/results còn nguyên; smoke đổi runtime/three-stage checks. Không chạy notebook phân tích hoặc model cells để sinh lại output.
- Interface session 03 được kiểm tra mở/nạp train-validation trên fixture mà không gọi fit; thiết kế model và checkpoint không đổi.
- Folder source-only chuẩn bị có 31 file, `-CheckOnly` đạt; không có receipt/data/model/session package. Folder colab-session cũ được giữ nguyên và không tham gia luồng mới.

Lệnh kiểm thử đã chạy:

```powershell
python -m pytest -q --ignore=tests/test_phase2_notebook.py --ignore=tests/test_data_regression.py -k "not embedded_bootstrap_works_before_src_import_is_possible and not updater_preserves_user_mount_and_path_settings and not each_pipeline and not real_synthetic_fits and not bad_identity and not prediction_failure and not failure_rows and not compact_notebook_interface and not visible_fit_callback"
```

## File thay đổi trong lần đơn giản hóa

- `src/data/colab_runtime.py`: một bootstrap trực tiếp từ Drive, workspace cố định, kiểm stage A/B và stale imports; stage C gọi riêng.
- `src/data/integrity.py` (mới): checksum/schema/mapping Phase 2 độc lập source deployment.
- `src/models/runtime.py`, `src/models/notebook.py`: dùng integrity chung và tách resource check; không đổi estimator, fit, metric hay checkpoint logic.
- `configs/runtime.json`: runtime workspace; `configs/phase2_integrity.json` (mới): approved data baseline, không tự sinh khi deploy.
- `scripts/prepare_colab_source.ps1`: chỉ một folder source/config; `scripts/update_colab_notebooks.py`: cùng setup ngắn cho năm notebook.
- `notebooks/00_dataset_audit.ipynb`, `01_eda.ipynb`, `02_preprocessing.ipynb`, `03_model_training.ipynb`, `colab_smoke_test.ipynb`: setup thống nhất và stage độc lập, giữ analysis/output.
- `tests/test_canonical_colab_runtime.py`, `tests/test_manifest_deployment.py`, `tests/test_phase3_training.py`: thay các kiểm tra receipt cũ và bổ sung alignment.
- `README.md`, `notebooks/README.md`, `docs/phase3_colab.md`, `docs/portability_validation.md`: một workflow, lưu bằng chứng cũ.

## Colab thật

**Đã có kết quả smoke mới trên Colab thật do người dùng chạy và gửi lại ngày 2026-10-27.** Agent không trực tiếp điều khiển kernel. Output xác nhận:

```text
Stage A PASS | Colab Python 3.13.16 | Drive=/content/drive/MyDrive/ML_Projects/disease-prediction-ml
Stage B PASS | imports=/content/disease-prediction-ml-runtime
source fingerprint=95b01d6ea67d68f9bbc48b647ca15b3c38219baac15639ae78637f184806bd61
Stage C PASS | manifest=50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9
7 train/validation/metadata checksums OK
```

| Tập | Records | Features | Classes | Groups |
|---|---:|---:|---:|---:|
| Train | 131248 | 375 | 587 | 117211 |
| Validation | 28120 | 375 | 587 | 25127 |

`schema_order_and_encoding=true`; `drive_write_read_checksum_delete=true`; `test_payload_opened=false`; `models_trained=0`.
Kết quả này được lưu dưới dạng bằng chứng người dùng cung cấp, không chèn output giả vào notebook hoặc gán execution count. Không chạy notebook 03/fit model để xác minh.

<details>
<summary>Lịch sử portability/deployment trước khi bỏ dual-package — không dùng làm hướng dẫn hiện tại</summary>

# Xác minh tích hợp runtime Colab/Drive — 2026-10-27

**COLAB NOT YET VERIFIED.** Không có kết nối kernel Colab/Drive thật từ môi trường agent. Không mô phỏng một lần tích hợp Colab thành công. Các bằng chứng dưới đây là unit test Windows và nạp dữ liệu thật trên Windows; thao tác OAuth, mount, upload và smoke trên Colab vẫn cần người dùng thực hiện theo [hướng dẫn duy nhất](phase3_colab.md).

## Kết quả lần tích hợp này

- **120 passed, 13 deselected** bằng Python có sẵn trên máy, không tạo/dùng `.venv`.
- Hai file không chạy: `test_phase2_notebook.py` kiểm template ZIP cũ và cần nbformat chưa có trên interpreter kiểm tra; `test_data_regression.py` tái tính bộ dữ liệu thật/đọc test nên nằm ngoài nhiệm vụ hạ tầng. Hai test embedded ZIP/updater cũ và 11 bài có fit model được bỏ chọn.
- Không có mô hình nào được fit trong lần kiểm tra này, kể cả fixture. Các test preprocessing chạy dữ liệu tổng hợp trong tmp, không tái tạo artifact Phase 2 của dự án.
- Unit test: derive paths từ một config, từ chối kernel local, báo thiếu mount/source/manifest, phát hiện checksum/source receipt cũ, pin SHA manifest Phase 2, cache source theo fingerprint, yêu cầu restart khi module cũ còn trong kernel, bỏ qua đường dẫn env cũ, setup ngắn và updater idempotent.
- Import `src.data.loader`, `src.data.preprocessing_inspection`, `src.models.notebook` từ đúng cache source trong một tiến trình Python Windows mới đã đạt. Không gắn nhãn lần import này là Colab.
- Probe ghi/đọc/SHA-256/xóa đã kiểm bằng filesystem fixture local. Chưa xác minh quyền ghi hoặc I/O trên Drive thật.

Lệnh kiểm thử đã chạy:

```powershell
python -m pytest -q --ignore=tests/test_phase2_notebook.py --ignore=tests/test_data_regression.py -k "not embedded_bootstrap_works_before_src_import_is_possible and not updater_preserves_user_mount_and_path_settings and not each_pipeline and not real_synthetic_fits and not bad_identity and not prediction_failure and not failure_rows and not compact_notebook_interface and not visible_fit_callback"
```

## Data-loading preflight thật trên Windows

Dùng `verify_training_inputs` → `cache_training_inputs` trong thư mục tạm → `load_training_data`, tức hợp đồng `load_final_split` hiện có. Đặt guard tại `Path.open` để mọi truy cập `test.csv.gz` đều thất bại; guard không bị kích hoạt. Cache tạm được xóa khi hoàn tất.

| Tập | Bản ghi | Feature | Nhãn | Group |
|---|---:|---:|---:|---:|
| Train | 131248 | 375 | 587 | 117211 |
| Validation | 28120 | 375 | 587 | 25127 |

Checksum, thứ tự feature, encoding nhãn, alignment group và không giao group train/validation đều đạt. Không nạp raw, test hoặc fit model trong data-loading preflight này. Toàn bộ tập đã khóa vẫn là **187434 dòng / 587 lớp / 375 feature**; số test lấy từ manifest có sẵn, không nạp để đánh giá.

## Bảo toàn dữ liệu và notebook

120 file raw/processed/metadata Phase 2/report/cấu hình phase2 được đối chiếu trước–sau: **SHA-256, kích thước và mtime không đổi**. Mọi checksum được ghi trong dataset manifest đều khớp; không sửa manifest để chấp nhận thay đổi. Việc kiểm bất biến hạ tầng có băm byte của file test nén theo yêu cầu kiểm SHA trước–sau; không giải nén/nạp/evaluate test. Bootstrap/smoke/training không mở payload đó.

Manifest Phase 2 SHA-256:
`ca20a551b1bf773c3dac59af40a56efa6552919e84136d44dd7117c39d038e02`

Source fingerprint bàn giao:
`447c039fa1e2ce0050dfcd2639a99b85d576b415377ce8b165a926a0f640f0ea`

29 source/config file trong staging đã được xác minh bằng cùng manifest trên PowerShell/Python; packet khớp từng byte với bootstrap/config canonical. Chưa upload lên Drive.

Toàn bộ cell ID, notebook metadata và output đã lưu của 00–03/smoke được giữ. Chỉ thay runtime/setup/giới thiệu; 00/01 tách setup chung thành một cell mới. Các cell audit/EDA, chính sách/split/kiểm chứng Phase 2, phụ lục lịch sử và năm cell estimator của 03 không đổi. Không chạy lại notebook 00/01/02 hoặc ghi đè report lịch sử.

## Nhóm file thay đổi

- `src/data/colab_runtime.py`, `src/data/loader.py`, `src/models/runtime.py`, `src/models/notebook.py`: bootstrap chung, import cache, data/output paths và interface session.
- `configs/runtime.json`, `configs/runtime.colab.example.json`: đánh dấu cấu hình canonical và phạm vi cấu hình legacy; giữ nguyên `configs/phase2.json`.
- Notebook 00–03 và smoke: setup chung, giữ output và phân tích.
- `scripts/prepare_colab_source.ps1`, `scripts/update_colab_notebooks.py`, các builder/updater liên quan: chuẩn bị source-only folder, cập nhật runtime cell mà không phục hồi ZIP bootstrap.
- Archive bootstrap/packager cũ: đánh dấu deprecated, giữ file lịch sử.
- Tests runtime/Phase 3 và `.gitignore`; README, notebooks/README và tài liệu: một hướng dẫn hiện hành; các trang hướng dẫn cũ chỉ chuyển đến đó.

Phần cần làm trên máy người dùng: upload nội dung `dist/drive-source/` vào đúng root Drive, chọn/mount kernel Colab chính thức, Upload to Colab folder `dist/colab-session/`, Restart Kernel rồi chạy smoke và phần 1–2 notebook 03. Dừng trước training.

<details>
<summary>Bằng chứng portability cũ — chỉ lịch sử, không phải hướng dẫn runtime hiện tại</summary>

# Kết quả kiểm tra portability — 21/10/2026

## Phạm vi đã hoàn tất

Chỉ thay đổi cấu hình, bootstrap/import, vị trí đọc CSV, vị trí xuất kết quả và công cụ chạy/kiểm tra notebook. Không triển khai preprocessing, huấn luyện, ensemble hoặc chatbot.

| Nhóm file | Thay đổi |
| --- | --- |
| `src/data/paths.py` | Tách project/storage/output/cache; runtime config; capability detection; mount Drive tùy chọn; output run mới |
| `src/data/loader.py` | Phát hiện/chỉ định CSV thực, read-only loading, cache theo SHA-256 giữ tên file |
| `src/data/io.py` | Giữ import cũ, analysis config và helper bảng; chuyển implementation đọc dữ liệu sang loader |
| `src/data/reporting.py`, `src/data/eda.py` | Chỉ sửa nơi xuất kết quả; package tùy chọn vắng được ghi null |
| `src/evaluation/plots.py`, `src/evaluation/report.py` | Nhận OutputPaths; giữ biểu đồ, phép tính và nội dung EDA |
| Notebook 00/01 và scripts tạo/cập nhật | Cấu hình chung, thay tham số output; giữ Markdown, cell IDs, metadata và outputs lịch sử |
| `configs/runtime*.json` | Mặc định và ví dụ local/Colab; không có credentials/Drive URL riêng |
| `requirements-notebooks.txt` | Dependency nhẹ cho notebook tương tác; giữ bộ pin Phase 1 trong requirements cũ |
| `scripts/run_phase1.py` | Dùng đúng interpreter; mặc định lưu bản thực thi vào run mới |
| `scripts/validate_deliverables.py` | Kiểm tra theo run; không ghi đè validation cũ |
| Smoke notebook, package/validation scripts | Kiểm tra runtime, đóng ZIP source có fingerprint, loại data/outputs/config riêng |
| Tests và tài liệu | Kiểm thử portability và regression CSV thật; hướng dẫn ba môi trường |

## Bằng chứng trên local Windows

- Trước thay đổi: **19 tests đạt**. Sau thay đổi, bật data regression: **43 tests đạt, 0 failed/errors/skipped**, gồm 19 tests cũ và 24 tests mới.
- Runtime giả lập bao gồm local, Colab, generic remote, thiếu Drive, API mount vắng/lỗi, config sai, CSV thiếu/nhiều ứng viên, cache hỏng và import từ CWD khác.
- Đối chiếu bằng **CSV thật cùng SHA-256**: mọi audit/EDA metrics và **26 bảng** khớp Phase 1. So sánh bảng có chuẩn hóa CSV round-trip chuỗi rỗng/NA; tolerance số thực `rtol=1e-10`, `atol=1e-12`.
- Hai notebook chạy trọn vẹn bằng Jupyter local: **15 code cells, 0 error outputs, 0 stderr**; EDA có **8 hình nhúng**.
- Tám PNG mới khớp từng pixel với hình cũ. Không thay phép tính EDA hoặc nội dung biểu đồ.
- Smoke notebook chạy local: **3 code cells, 0 errors/stderr**; kiểm tra imports, header CSV, checksum và đọc/ghi JSON vào output storage.
- Validator đầu ra theo run: **PASS**, 26 bảng, 8 PNG/SVG, notebook thực thi đầy đủ và không có trained-model artifacts.
- **51 file được bảo vệ giữ nguyên byte**, gồm raw CSV, báo cáo cũ và manifest. Hai notebook gốc giữ nguyên Markdown, outputs, IDs và metadata; chỉ thay source các cell liên quan cấu hình/output.

CSV SHA-256:

`8de90603ebada467fc2703db2ee4292856e52d64e94982ef926df22fa0c21320`

Kết quả thực thi nằm ở các bản sao, không thay outputs trong notebook gốc:

- Audit/EDA: `reports/runs/execution-20261021T112402488815Z-ff9b62c8/notebooks/`.
- Smoke local: `reports/runs/execution-20261021T112821297920Z-dcc5e6a8/notebooks/`.
- Pytest: `artifacts/metadata/portability-tests-20261021.xml`.
- Bằng chứng tự động: các run `validation-*` và `portability-validation-*` trong `artifacts/metadata/runs/`.

## Giới hạn xác minh

**Chưa có runtime Colab thật trong phiên này.** Không tuyên bố đã mount Google Drive, xác thực OAuth, chạy notebook trên Colab hoặc kiểm chứng storage sau reset Colab. Test Colab là giả lập logic filesystem và capabilities trên Windows.

Trước lần dùng thật: đưa source lên runtime, cài dependency thiếu có chủ đích, làm Drive khả dụng bằng cách runtime hỗ trợ, chọn profile Colab và chạy `notebooks/colab_smoke_test.ipynb`. Kiểm tra lại `smoke.json` từ phiên runtime sau để xác minh lưu lâu dài. Xem [quy trình chi tiết](portable_runtime.md).


</details>


</details>
