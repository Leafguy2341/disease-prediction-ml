> ARCHIVE — Bản tại thời điểm trước hợp nhất tài liệu. Các trạng thái và lệnh cũ không phải hướng dẫn hiện hành. Xem [chỉ mục hiện hành](../../README.md) và [triển khai](../../DEPLOYMENT_GUIDE.md). Đường dẫn trong code block vẫn tính từ project root.

# Colab + Google Drive — hướng dẫn duy nhất cho notebook 00–03

## Chẩn đoán và cơ chế đã bỏ

Bootstrap cũ so nhiều bản source/receipt ở local, Drive và `colab-session`, rồi kiểm dữ liệu Phase 2 trước cả audit/EDA. Hai manifest có dữ liệu giống nhau nhưng provenance khác làm hỏng bước khởi động. Upload nhầm/cũ một file cũng khiến receipt không đồng bộ.

Luồng hiện tại chỉ có **source canonical trên Drive → workspace tạm → import**. Không dùng `colab-session`, ZIP, `.pyz`, `source_manifest.json` hoặc `-DriveAudit` để khởi động. Các file/package cũ được giữ làm lịch sử và hoàn toàn bị bỏ qua. Không xóa chúng để sửa lỗi.

## Đường dẫn

Nguồn cấu hình runtime duy nhất: `configs/runtime.json`, phần `colab`.

| Vai trò | Mặc định |
|---|---|
| Drive mount | `/content/drive` |
| Canonical project root | `/content/drive/MyDrive/ML_Projects/disease-prediction-ml` |
| Source thực thi/import | `/content/disease-prediction-ml-runtime/` |
| Cache dữ liệu | `/content/disease-prediction-ml-cache/` |

Root = `drive_mount / project_relative`. Mọi raw/output path tính từ root này. Workspace và cache là tạm, không nằm trong Drive; không lưu dữ liệu hoặc kết quả quan trọng tại đó. Khi VM reset, setup tự tạo lại từ Drive, không upload thêm package.

```text
<Drive root>/
├── src/{data,models,...}/
├── configs/
│   ├── runtime.json                  đường dẫn/runtime
│   ├── phase1.json, phase2.json, phase3.json
│   └── phase2_integrity.json         baseline dữ liệu độc lập, không phải runtime config
├── requirements-{notebooks,training}.txt
├── data/raw/                        CSV thực tế, không đổi tên
├── data/processed/{train,validation,test}.csv.gz
├── artifacts/metadata/phase2/       bộ manifest/schema/mapping/policy/assignment khóa
├── artifacts/models/phase3/         output training về sau
└── reports/{figures,tables}/         output persistent
```

Setup notebook có một dòng `DRIVE_ROOT` làm locator để đọc bootstrap trước khi có thể import project. Locator mặc định được template lấy từ `runtime.json`; bootstrap đọc config trên Drive và kiểm hai đường dẫn khớp. Nếu chuyển toàn bộ project sang folder/shortcut khác, sửa vị trí trong config và locator cho cùng một root. Không tạo file cấu hình runtime thứ hai, không dùng đường dẫn Windows trên kernel Colab. Các override `DISEASE_*` cũ không chọn data/output cho các notebook này.

## Workflow

1. **Chỉ khi source/config đổi:** từ terminal PowerShell trong project, chuẩn bị folder upload:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\prepare_colab_source.ps1 -Refresh
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\prepare_colab_source.ps1 -CheckOnly
   ```

   Không cần Python Windows, `.venv`, Conda hoặc pip. Script chỉ làm mới `dist/drive-source/`, kiểm đường dẫn/link trước khi xóa staging sinh ra trước đó. Nếu có file người dùng ngoài danh sách source trong staging, script dừng để giữ file đó. Không đọc/đổi dataset, manifest Phase 2, model hoặc report; không tạo receipt/session/archives. Fingerprint source chỉ để đối chiếu/log.

2. Upload **nội dung bên trong `dist/drive-source/`** vào đúng root Drive: hợp nhất `src/`, `configs/`, thay file code/config cùng tên và hai requirements. Phải có `<root>/src/data/colab_runtime.py`, tránh lồng thêm `drive-source/` hay một folder project nữa. Giữ nguyên `data/`, `artifacts/`, `reports/`. Agent không tự đồng bộ Drive; đây là thao tác thủ công chỉ cần làm khi code/config đổi.
3. Mở notebook đã cập nhật trong VS Code → **Select Kernel → Colab → Auto Connect** (hoặc chọn server) và đăng nhập.
4. **Ctrl+Shift+P → Colab: Mount Google Drive to Server...**; chạy cell mount extension tạo và hoàn tất xác thực. VS Code không tự mount. [Hướng dẫn Google Colab chính thức](https://github.com/googlecolab/colab-vscode/wiki/User-Guide).
5. **Restart Kernel nếu vừa đổi source**, rồi chạy notebook. Không upload bất kỳ `colab-session` nào. Với smoke test, dùng Run All; với 03, chỉ chạy phần 1–2 khi xác minh hạ tầng, dừng trước các cell model.

Colab browser dùng cùng source trên Drive và cùng notebook: mount bằng giao diện/cell `google.colab.drive.mount`, rồi chạy setup. Không cài `google.colab` lên local để giả lập. Notebook không tự mount, cài package hoặc download file. Nếu thiếu dependency, chủ động `%pip install -r <workspace>/requirements-notebooks.txt -r <workspace>/requirements-training.txt` trên Colab khi cần, rồi Restart Kernel.

## Bootstrap và ba stage smoke test

Cả năm notebook gọi **`src/data/colab_runtime.py::bootstrap_runtime` trực tiếp từ Drive**. Đầu vào chỉ gồm root và phase, không có session/receipt.

- **Stage A:** nhận diện Colab Linux, `/content`, mount và canonical root; kiểm ghi/đọc/SHA/xóa file probe nhỏ trong runtime và `reports/` trên Drive. Không để lại marker lâu dài.
- **Stage B:** kiểm từng source/config cần thiết theo phase; kiểm cú pháp Python, copy source vào workspace cố định và import module tại đó; in root/workspace/fingerprint. Fingerprint tính từ duy nhất các `.py` trong Drive `src/`, không gồm receipt hay dữ liệu. Không so với source package độc lập. Pin revision tùy chọn `expected_source_fingerprint` chỉ dùng khi người quản lý chủ động khai báo trong runtime config; mặc định không có pin.
- **Stage C:** gọi `phase2_preflight` riêng để đọc `configs/phase2_integrity.json`, xác minh SHA byte của manifest đã được duyệt và checksum train/validation/metadata. Sau đó smoke kiểm feature order, label encoding, row/group alignment khi nạp hai tập. Lỗi chỉ rõ file, SHA expected và actual. Không mở/copy/hash CSV test.

Stage A/B có thể PASS khi C FAIL; nguồn code đổi không có nghĩa dataset hỏng. Notebook 00/01 chỉ cần Stage A/B và raw CSV, không cần artifact/config triển khai Phase 3 hay baseline Phase 2. Notebook 02 giữ nguyên tính toán/đối chiếu bộ đã khóa. Notebook 03 giữ nguyên năm cell estimator/pipeline/fit; interface mở session kiểm Stage C và tài nguyên trước khi nạp dữ liệu.

`phase2_integrity.json` là baseline dữ liệu được duyệt độc lập, không được script source sinh/cập nhật từ Drive. Nó ghi hai SHA manifest local và Drive đã xác minh trước đây (`ca20a551…` và `50308d25…`) cùng fingerprint processed và toàn bộ inventory artifact. Hai manifest chỉ khác môi trường sinh dữ liệu và SHA mã preprocessing; schema, mapping, policy, splits và file artifact giống nhau, được xác nhận bằng cell chỉ đọc trên Colab trước lần sửa này. Bootstrap mới không thay bất kỳ manifest/checksum nào để vượt cổng kiểm tra. Một manifest mới không có trong baseline vẫn bị chặn và cần đối chiếu độc lập.

Workspace chỉ chứa bản copy source/config. Nếu Drive source/config đổi khi kernel đang giữ `src.*` cũ, setup dừng yêu cầu Restart Kernel trước khi cập nhật workspace. Sau restart, workspace thuộc bootstrap được thay bằng bản copy mới. Không reload từng module và không chỉnh source trong workspace cache.

## Khắc phục lỗi

| Lỗi | Cách xử lý |
|---|---|
| Không thấy Drive/bootstrap | Chọn đúng kernel/server, mount Drive, kiểm locator trỏ đúng canonical folder và file thực sự tồn tại. |
| Root không khớp | Đối chiếu root actual/expected được in; config và locator phải cùng folder. |
| Thiếu module source | Đồng bộ lại `src/`/`configs/`; lỗi liệt kê file cần có. Không cài `src` từ pip. |
| Source/config cũ trong kernel | Đồng bộ Drive rồi Restart Kernel. Không cần upload package vào `/content`. |
| Workspace có file không thuộc cache dự án | Không ghi đè; dùng VM mới hoặc kiểm thư mục được báo trước khi dọn. |
| Manifest/artifact checksum mismatch | Giữ nguyên dữ liệu và baseline, đối chiếu file expected/actual. Không sửa checksum hoặc chạy lại preprocessing để bỏ lỗi. |

## Phạm vi xác minh

[Bằng chứng kiểm tra](portability_validation.md) ghi riêng unit test/loader local và Colab thật. Agent không có kết nối trực tiếp đến filesystem Drive/kernel. **Người dùng đã chạy smoke mới trên Colab thật và gửi output A/B/C PASS ngày 2026-10-27**, Python 3.13.16. Đây là bằng chứng thực thi do người dùng cung cấp, không phải fixture local hay tuyên bố agent đã điều khiển kernel.

Source fingerprint: `95b01d6ea67d68f9bbc48b647ca15b3c38219baac15639ae78637f184806bd61`.
Manifest Drive: `50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9`.
Train: 131248 records / 375 features / 587 classes / 117211 groups.
Validation: 28120 / 375 / 587 / 25127.
`schema_order_and_encoding=true`, `drive_write_read_checksum_delete=true`, `test_payload_opened=false`, `models_trained=0`.

Các notebook phân tích và cell model không được chạy để tạo lại output trong lần tích hợp. Chưa huấn luyện model, evaluate test, ensemble hoặc chatbot.
