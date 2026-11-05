> ARCHIVE — Bản tại thời điểm trước hợp nhất tài liệu. Các trạng thái và lệnh cũ không phải hướng dẫn hiện hành. Xem [chỉ mục hiện hành](../../README.md) và [triển khai](../../DEPLOYMENT_GUIDE.md). Đường dẫn trong code block vẫn tính từ project root.

# Prediction API local — approved LR tuned C=2

Tài liệu này mô tả riêng `/api/v1/predict` nhận feature tiếng Anh có cấu trúc, không gọi Gemini.
Server nay có thêm `/api/v1/chat` và web local qua [LOCAL_WEB_MVP](LOCAL_WEB_MVP.md).
Endpoint predict
không train/calibrate hoặc đọc raw/processed CSV. Source nằm `app/backend/`, tái sử dụng
`Catalog.load`, frozen checkpoint identity và `load_fitted_checkpoint` hiện có.

**Trạng thái cập nhật 2026-10-30:** 7 artifact local và source pins đã verify; actual LR tuned đã load/predict
trong process riêng Windows3.13.17 với đúng các ML dependencies. **Runtime/API qualification PASS**:
checksum reference do owner gửi khớp file local,8×587 probabilities/exact labels/Top3 và identity PASS.
Actual TestClient và Uvicorn HTTP localhost trả health200/REAL CHECKPOINT VERIFIED, predict200.
Xem [LR_WINDOWS_COMPATIBILITY](LR_WINDOWS_COMPATIBILITY.md) để lấy reference và xem điều kiện duyệt.

## Môi trường và artifact tối thiểu

Identity training giữ chính xác Python **3.13.18**, scikit-learn **1.6.1**, NumPy **2.1.3**,
SciPy **1.16.3**, joblib **1.6.0**. Allowlist thêm riêng Windows CPython3.13.17/AMD64 với đúng các
ML versions và checkpoint SHA/selected identity đã qualification. Không có flag bỏ qua guard hoặc fallback baseline.
Loader cũng kiểm tám source pins gốc, C=2, schema375/order587, variance/CSR function và fitted coefficients.

Từ canonical Drive đã được owner cấp quyền, tải riêng các file sau về một root artifact local,
giữ nguyên relative paths. API không cần dataset CSV, validation predictions hoặc các model khác:

```text
<LOCAL_ARTIFACT_ROOT>/
├── artifacts/metadata/phase2/
│   ├── dataset_manifest.json
│   ├── feature_schema.json
│   └── label_mapping.json
├── artifacts/metadata/tuning/tuning-v1-9c4dd013abbba14a/manifest.json
└── artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/logistic_regression/
    ├── pipeline.joblib
    ├── fit.json
    └── metadata.json
```

Bảy file này là bản export chỉ đọc của artifacts đã duyệt, không thay canonical Drive.
Giữ manifest Phase2 `50308d25…e80b8fe9` gắn với model; không thay bằng variant local `ca20a551…`.
Pipeline SHA-256: `4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6`.
Tuning manifest SHA-256: `4a10ddd5deba5fff7927f84ea334196a3f6d127b9777ced2b127f5b5e9389355`.
Selected checkpoint identity: `tuned-v1-b8a5602679b3dc5c`.

Mount Drive trong Colab không làm `/content/drive` truy cập được từ terminal Windows.
API local cần root local/Drive desktop thực sự truy cập được bằng interpreter Windows đang chạy server.
Không tải cả test split để phục vụ API hoặc chỉnh metadata để vượt checks.

## Chạy trên Windows

Mở PowerShell tại project source. Các lệnh này yêu cầu interpreter đã được duyệt, không thay bộ
thư viện Phase1 trong Python3.11 hiện có. `.venv-web`3.13.17 đã được qualification và real API smoke PASS.
Dừng server cũ bằng Ctrl+C trước khi mở lại port8000 bằng interpreter mới.

```powershell
$ApiPython = (Resolve-Path -LiteralPath '.\.venv-web\Scripts\python.exe').Path
& $ApiPython --version
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
& $ApiPython -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Lệnh pip là thao tác cài dependency chủ động, không được API tự chạy. Không tự download weights.
Mỗi process load model đúng một lần khi startup; không dùng reload/workers nhiều khi smoke.
Loader thất bại thì server vẫn có health chẩn đoán, `/predict` trả503 và không dùng baseline.

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/health'
$body = @{ present_features = @('fever', 'cough') } | ConvertTo-Json
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/predict' -Method Post -ContentType 'application/json' -Body $body
```

`fever` và `cough` đã đối chiếu có trong schema. Đây là input giả lập không có ground truth;
không gán bệnh kỳ vọng. OpenAPI: `/openapi.json`; giao diện tài liệu: `/docs`.

## Contract

`POST /api/v1/predict` nhận `{"present_features":["fever","cough"]}`.
Danh sách phải không rỗng, duy nhất, tối đa375 chuỗi exact schema; không fuzzy-map, ép kiểu hoặc nhận model ID từ client.
Service dựng uint8 DataFrame1×375 theo feature ordering đã khóa, zero-fill phần chưa ghi nhận hiện diện.
Số0 không đồng nghĩa triệu chứng vắng mặt về lâm sàng.

Response có identity/hash, schema, `calibrated:false`, `score_label:"Điểm mô hình (%)"` và đúng3 entries
`rank`, `class_id`, `label`, `score_percent`. Score = fitted `predict_proba()` trên đủ587 lớp ×100;
không chuẩn hóa riêng Top3, không đổi tên nhãn và không gọi là xác suất mắc bệnh.
Tie score dùng thứ tự class Phase2 cố định. Output NaN/sai shape/sai normalization không được trả Top3.

HTTP200 health chỉ khi model đã load và verify; `checkpoint_status="REAL CHECKPOINT VERIFIED"`.
HTTP503 khi thiếu config/weights hoặc sai checksum/env; HTTP422 cho JSON/feature invalid;
HTTP500 khi model không trả output hợp lệ. Lỗi có envelope `error.code/message/details`, không trả traceback hoặc input thô.

Đây là endpoint structured research, contract chỉ yêu cầu ít nhất1 feature để kiểm schema.
Nó chưa thực thi quality gate hội thoại. Khi nối Phase5B, caller vẫn phải qua guard/validator,
subject/time/conflict/urgent checks và policy min2 **provisional**, không gửi thẳng extraction chưa hợp lệ.
Port `LRPredictionService.predict(frame, schema_sha256=...)` đã khớp interface có sẵn;
được dùng trong Chat API qua forward_ready; Gemini/session/frontend nay đã nối ở local MVP,
nhưng real checkpoint/Gemini live vẫn cần kiểm riêng theo hướng dẫn web.

## Kiểm thử và real smoke

```powershell
python -B -m pytest -q -p no:cacheprovider tests/test_prediction_api.py
```

Đây là TestClient/synthetic tests; không tải hoặc fit model. Khi đã có7 file và môi trường đúng,
chạy server và hai HTTP requests trên. Chỉ sau health200/REAL CHECKPOINT VERIFIED và predict200
với375/587/đúng hash mới ghi nhận real local smoke PASS. Lưu kết quả kiểm riêng; không sửa artifact gốc.
Không dùng metric final test để đổi model, C, threshold hoặc calibration.

Tài liệu tham khảo: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
[TestClient lifespan](https://fastapi.tiangolo.com/advanced/testing-events/),
[Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/),
[scikit-learn model persistence](https://scikit-learn.org/stable/model_persistence.html).
