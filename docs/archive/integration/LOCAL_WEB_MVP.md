> ARCHIVE — Bản tại thời điểm trước hợp nhất tài liệu. Các trạng thái và lệnh cũ không phải hướng dẫn hiện hành. Xem [chỉ mục hiện hành](../../README.md) và [triển khai](../../DEPLOYMENT_GUIDE.md). Đường dẫn trong code block vẫn tính từ project root.

# Local web MVP — Lắng nghe

Ngày kiểm **2026-10-30**. Chat API và website đã kiểm với mock LLM/model; browser Chromium thật
đã chạy desktop1200px/mobile390px. **Real checkpoint/API PASS trên Windows3.13.17; Gemini live NOT VERIFIED**.
Không có production mock mode: thiếu model/key thì giao diện báo chưa sẵn sàng và không bịa Top3.

## 1. Bảy artifacts từ Drive, không chép dataset

Canonical Drive vẫn là `/content/drive/MyDrive/ML_Projects/disease-prediction-ml` trên Colab,
hoặc `MyDrive/ML_Projects/disease-prediction-ml` trong Drive web.
Copy/download **chỉ7 file**, giữ nguyên relative paths dưới root local, ví dụ `D:\ML_Artifacts\disease-prediction-ml`:

```text
artifacts/metadata/phase2/dataset_manifest.json
artifacts/metadata/phase2/feature_schema.json
artifacts/metadata/phase2/label_mapping.json
artifacts/metadata/tuning/tuning-v1-9c4dd013abbba14a/manifest.json
artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/logistic_regression/pipeline.joblib
artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/logistic_regression/fit.json
artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/logistic_regression/metadata.json
```

Owner hiện không dùng Drive for desktop: tải từng file qua Drive web, rồi **copy** vào đúng folder local.
Nếu dùng Drive desktop sau này, copy từ đường dẫn thực đã kiểm. Không di chuyển/xóa file Drive,
không tải raw/train/validation/test CSV, không tạo ZIP và không thay manifest `50308d25…` bằng variant local.
File local đã có nhưng khác hash thì dừng đối chiếu nguồn; không ghi đè để vượt validation.
Hash/chỉ định đầy đủ tại [LOCAL_PREDICTION_API](LOCAL_PREDICTION_API.md#môi-trường-và-artifact-tối-thiểu).

Loader kiểm protected metadata/schema375/labels587 đúng order, anchored tuning manifest,
source pins và chỉ LR tuned C=2/selected checkpoint `tuned-v1-b8a5602679b3dc5c`.
Pipeline SHA `4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6`.
Không load lại model từ client request, không baseline fallback, không preprocessing fit hoặc calibration.

## 2. Interpreter và real ML smoke

Training identity vẫn Python **3.13.18**, sklearn **1.6.1**, NumPy **2.1.3**, SciPy **1.16.3**, joblib **1.6.0**.
Cập nhật 2026-10-30: **Windows CPython3.13.17/AMD64 đã được duyệt riêng** cho đúng LR tuned checkpoint
với các ML versions trên trong `.venv-web`. Checksum Colab/local,4.696 probabilities/labels/Top3,
schema/mapping/source pins đều PASS theo [protocol](LR_WINDOWS_COMPATIBILITY.md).
Actual TestClient và Uvicorn localhost smoke health200/predict200, không gọi Gemini.
Không dùng Python3.11.9 để deserialize LR; không sửa guard hoặc chạy lại final test.
Mở PowerShell tại folder source project, không dùng kernel Colab để chạy server Windows:

```powershell
$ApiPython = (Resolve-Path -LiteralPath '.\.venv-web\Scripts\python.exe').Path
& $ApiPython --version
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
& $ApiPython -B -m scripts.smoke_local_mvp --ml
```

Cài pip là thao tác chủ động, không tự chạy bởi ứng dụng; không thay môi trường Phase1.
`.venv-web` hiện đã chuẩn bị đủ packages và được duyệt cho checkpoint này; không cần cài lại.
Nếu cần tái tạo môi trường trên máy khác, chủ động cài `requirements-api.txt` vào đúng venv3.13.17,
đặt storage root thật chứa7artifact và giữ nguyên versions/identity.
`--ml` kiểm actual startup/health và predict với input **synthetic** `cough,fever` không có ground truth.
PASS cần REAL CHECKPOINT VERIFIED và HTTP200. Thiếu/sai file hoặc môi trường → BLOCKED,
không đọc locked test hoặc fit để sửa. Script không gọi Gemini trong nhánh này.

## 3. API key và Gemini smoke độc lập

**Có thể kiểm riêng Gemini bằng Python3.11.9 hiện có.** Nhánh `--gemini-live` không load checkpoint LR,
nên không phụ thuộc môi trường ML của mục2.
Chạy tại folder `disease-prediction-ml`; lấy python.exe thực từ launcher `py -3.11`:

```powershell
$GeminiPython = (& py -3.11 -c "import sys; print(sys.executable)").Trim()
& $GeminiPython --version
```

Trên máy hiện tại, kết quả là `D:\Program Files (x86)\Python\Python311\python.exe`, version3.11.9.
Do7 artifact đã có trong chính project, trong **terminal đang ở project root** có thể đặt:

```powershell
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
```

Nếu artifacts ở folder riêng, dùng root thực chứa `artifacts/metadata/phase2/`; không giữ đường dẫn ví dụ chưa tồn tại.

Model config hiện là **`gemini-3.8-flash`**. Tài liệu chính thức xác nhận model ID và structured outputs;
pricing hiện ghi text input/output có Free Tier. **Active quota/quyền truy cập project chưa được xác minh**.
Kiểm tài khoản của bạn tại AI Studio; hạn mức tính theo project và có thể khác local limits dưới đây.

Nhập key ở **cùng PowerShell sẽ chạy server**, không đặt key trong source/.env/notebook/chat/frontend:

```powershell
$GeminiSecret = Read-Host 'Gemini API key' -AsSecureString
$env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new('', $GeminiSecret).Password
$env:DISEASE_GEMINI_LIVE = '1'
& $GeminiPython -B -m scripts.smoke_local_mvp --gemini-live
```

Nếu đã nhập key trong cùng terminal, không cần nhập lại: chỉ sửa biến interpreter và chạy dòng cuối.
PASS ở nhánh Gemini không xác nhận LR chạy được trên3.11.9; nhánh `--ml` và chatbot-to-Top3 vẫn giữ version guard.

Smoke này chỉ dùng3 lượt tiếng Việt giả lập (ho+sốt; sửa thành chưa chắc sốt; trả lời phủ định),
không predict bệnh. Tối đa **6 HTTP requests**, zero retries, output cap2048 tokens/request,
local admission budget100.000 units; request serialized cap64.000 UTF8 bytes.
Nó kiểm schema đầy đủ375 feature và Python validator, không giảm allowlist hay tự fallback JSON-only/model khác.
PASS chỉ nếu3 kết quả thực hợp lệ đúng kỳ vọng; không lấy mock tests làm live proof.
Thiếu key/opt-in/schema, hết quota hoặc schema bị provider từ chối → NOT VERIFIED, lý do và usage được in an toàn.
Không có key trong Process/User/Machine environment khi agent kiểm; lần chạy hiện tại **0 generation requests**.

Transport dùng helper hiện có: POST `https://generativelanguage.googleapis.com/v1beta/interactions`,
header key chỉ phía backend; `system_instruction`, `response_format` JSON schema, `store=false`, `stream=false`.
Đọc text từ completed `steps/model_output/content` và counters từ `usage`. Không tool calling hoặc chẩn đoán bởi Gemini.
Server acceptance của chính schema375 này **chưa live-verified**, dù Draft2020 schema check và mocked transport tests PASS.
Nếu provider trả400, dừng báo lỗi; không bỏ schema/feature để tạo PASS.

## 4. Mở website

Sau khi cấu hình env ở các bước trên:

```powershell
& $ApiPython -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Mở **http://127.0.0.1:8000/**. Tài liệu API ở `/docs`, schema ở `/openapi.json`.
Có thể mở giao diện khi thiếu model/key để thấy trạng thái chẩn đoán, nhưng chưa có chat-to-Top3 thật.
Chỉ để xem UI bằng Python hiện có đã cài dependencies, có thể chạy
`python -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1`.
Health503 là đúng trong trường hợp này; không phải cách bỏ qua model environment guard.
Không dùng nhiều workers/reload cho smoke; session và ngân sách nằm trong RAM của một process.
Không public hosting/ngrok/tunnel. Windows code và Colab Drive mount là hai môi trường khác nhau.

- `POST /api/v1/chat`: `{"message":"Tôi ho và sốt.","session_id":null}`.
  Dùng session_id server trả về cho lượt sau; `subject_id` tùy chọn self/mother/father/child.
- Reset: `{"message":"","session_id":"<current id>","reset":true}`.
  Xóa riêng phiên RAM cũ, trả phiên mới, không xóa file. Browser chỉ giữ ID trong RAM, refresh bắt đầu phiên mới.
- Flow: InputGuard → Gemini intent/extraction → existing validator/evidence/subject/time → quality gate
  → `forward_ready` → approved fitted LR. Top3 không lấy từ Gemini.
- Gate min2present vẫn **provisional**, không phải ngưỡng y khoa. Uncertain/conflict/unmapped/urgent/invalid/provider failure/expiry
  không có Top3. Urgent guard vẫn hoạt động nếu ML chưa sẵn sàng, không gọi Gemini.
- Template tiếng Việt có kiểm soát; nhãn bệnh giữ nguyên từ mapping. **Điểm mô hình (%)** là raw predict_proba×100,
  chưa calibration/không phải xác suất mắc bệnh. Giữ rank và score, không renormalize ba giá trị.

Ngân sách app mặc định:20 requests/process,6/phút,2048 output tokens/request,100.000 local budget units,
64.000 serialized bytes/request, không retry tự động. New chat không reset ngân sách.
Budget admission dựa byte reservation bảo thủ, **không phải tokenizer hoặc hóa đơn**;
usage chỉ lấy counters provider thực trả, thiếu thì null/complete=false; billed cost luôn unknown.
Timeout/quota/error có thể đã tiêu tài nguyên nhưng không trả usage: giữ reservation để chặn gọi tiếp,
không ghi zero token giả. Provider quota vẫn áp dụng dù restart local server.

## 5. Kiểm thử và phạm vi đã xác minh

### Chẩn đoán Gemini sau khi ML API đã PASS

`live_enabled=true` và `key_configured=true` trong `/health` chỉ xác nhận cấu hình local,
không xác nhận key/quota/quyền model hoặc schema được Google chấp nhận.
Trong lần debug2026-10-30, backend đang chạy tại8001: ML ready, Gemini đã bật và nhận key.
Một request synthetic mới trả backend503/provider_error với `reason=timeout` ở timeout20giây,
không có HTTP400/error body mới để phân tích. Không kết luận lỗi này giống HTTP400 trước đây.
Diagnostic do owner chạy tiếp với timeout60 cũng trả timeout sau60207.88ms, chưa có provider HTTP
status/usage, vector chưa được tạo. Do đó chưa có bằng chứng rằng chỉ tăng timeout20 là đủ.
Probe không key tại cùng host: DNS PASS6.76ms, TCP/TLS1.3 PASS118.85ms, GET endpoint nhận403
sau185.55ms. Đây là kết nối/HTTP reachability, không phải bằng chứng key có quyền hoặc request extraction PASS.

**Bằng chứng request thứ3 cuối cùng:** TLS158.57ms, gửi hết20016bytes body ở158.74ms,
Google trả **HTTP400 sau48267.61ms**. Error message đã che: “The specified schema produces a
constraint that has too many states for serving.” Response nêu các yếu tố có thể tăng state count,
gồm long enums, nested array limits và numeric minimum/maximum. Đây là lỗi serving constraint/schema,
xảy ra trước parser, extraction validator và LR. Không phải lỗi upload hoặc chỉ suy đoán từ UI.
Deadline20 có thể che các HTTP400 trả chậm như lượt này; không suy rằng tất cả timeout đều do schema.

Bản mitigation đầu bỏ hai `minimum` ở offsets đã được owner cho phép kiểm thêm1request, nhưng
vẫn timeout60197.29ms: TLS186.96ms, gửi hết19988bytes ở187.08ms rồi chờ response. Không coi bản này PASS.

**Bản hiện tại** khôi phục hai `minimum`, giữ tất cả numeric/evidence constraints và đổi riêng
wire enum từ375 tên dài sang **đủ375 mã** `f000…f374`, theo đúng thứ tự catalog đã verify.
Input Gemini có dictionary `allowed_features` chứa **mọi cặp mã→tên feature gốc**; không chọn subset.
Provider đổi mã về tên canonical trước Python validator; API/UI/ML không nhận mã ngắn.
Mã lạ, tên thay mã, catalog bị reorder/mismatch đều bị chặn, không fuzzy-map và không fallback JSON-only.
Canonical schema375, label mapping587, threshold/gate, model/endpoint và production timeout20 không đổi.
Tổng ký tự enum giảm6314→1500 (đây không phải số token hay phép đo state count của Google).
**223 tests offline PASS**, roundtrip đủ375, offsets âm vẫn bị local validator chặn; live acceptance vẫn NOT VERIFIED.

**Kết quả live mới nhất của wire codes:** actual Chat API vẫn timeout tại20.23giây (chưa đủ để đánh giá
acceptance); owner kiểm lại CLI60 nhận **HTTP503 sau1364.08ms**, message Google xác nhận
`gemini-3.8-flash is currently experiencing high demand`. TLS/send hoàn tất115.30ms, body19247bytes.
Đây là provider availability ở lượt này, không phải lỗi port/LR hoặc response validator.
HTTP503 không chứng minh schema mới đã được chấp nhận; extraction→LR live vẫn **NOT VERIFIED**.
Adapter ánh xạ503 thành `provider_unavailable`, UI trả thông báo tiếng Việt dịch vụ đang bận;
không tự retry, đổi model hoặc tạo Top3. **225 tests offline PASS**, bao gồm503 một attempt/no prediction.
Đã dùng6 attempted generation requests theo các lần owner chấp thuận; dừng gọi live để tránh lặp khi provider bận.
Evidence đầy đủ: `artifacts/metadata/gemini_debug/20261030_wire_codes_live_attempts.json`.
Tham khảo [Google troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting) về503/transient errors;
không coi raw availability của một lượt là bằng chứng outage toàn hệ thống hoặc quota/Free Tier của tài khoản.

Đã dùng **3request ban đầu +3request bổ sung được owner cho phép**. Chưa có successful live extraction cho wire codes.
Không chạy lại lệnh diagnostic bên dưới trừ khi owner cấp phép request mới. Evidence lịch sử:
`artifacts/metadata/gemini_debug/20261030_serving_schema_rejection.json`.

Adapter cũ bỏ response body khi bắt HTTPError. Bản sửa giữ HTTP status/provider status và
diagnostics đã che key/request text, giới hạn error body16KiB và message1200ký tự;
không giữ headers/URL/raw body/ErrorInfo metadata. Chat response và health không công khai
provider message; chỉ CLI synthetic diagnostic in message đã che để phân tích.
Provider model `gemini-3.8-flash`, endpoint `/v1beta/interactions`, extraction contract và375features giữ nguyên.

Đã kiểm request `system_instruction`, `generation_config.max_output_tokens`, string `input`,
`store=false`, `stream=false`, `response_format.type=text/mime_type=application/json/schema`
và parser `status/steps/model_output/content/text` theo
[Interactions REST](https://ai.google.dev/api/interactions-api).
[Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) ghi
minLength/uniqueItems không được decoder enforce; Python validator vẫn kiểm chúng.
Schema local Draft2020-12 PASS, enum đủ375, class mapping587; Google acceptance vẫn NOT VERIFIED
khi chưa nhận response thành công. Không tự xóa $defs/$ref/const hoặc feature để request PASS.

Để lấy một bằng chứng mới, Ctrl+C server trong chính terminal đã có key, rồi chạy **một dòng**:

```powershell
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path; & '.\.venv-web\Scripts\python.exe' -B -m scripts.smoke_local_mvp --gemini-diagnostic --timeout-seconds 60
```

Đây là một request synthetic cố định, retry0, output tối đa2048tokens, không load LR/fit/predict.
Timeout60 chỉ để chẩn đoán, không sửa production timeout20; trả lại usage thực hoặc unknown.
CLI kiểm Python validator/quality gate và vector1×375 nếu extraction hợp lệ. Không có Top3 từ Gemini.
`transport_trace` chỉ ghi connect/TLS, send-start/completed với số byte và response-header wait/status.
Trace chỉ gắn vào CLI, giữ nguyên HTTPSHandler/TLS verification/proxy kwargs; không in headers/body/key.
Đã kiểm trace bằng actual GET không key (403 sau182.75ms), không gọi sinh nội dung.
Không chạy kèm `--gemini-live`, không gửi thêm chat trong lúc chẩn đoán để giữ giới hạn3requests/task.
Agent đã dùng2requests qua actual chat, owner dùng4requests CLI; lượt thứ3 nhận400, lượt thứ6 nhận503 high demand.
Lỗi cú pháp PowerShell trước khi Python chạy không tiêu request.
Thiếu key/live env thì CLI NOT VERIFIED/requests0; không yêu cầu gửi key hoặc đọc key từ process khác.

Phân biệt các lớp lỗi bằng JSON output:

| Bằng chứng | Lớp cần kiểm |
| --- | --- |
| `reason=timeout`/`network_error`, chưa có provider HTTP status | Transport/timeout; chưa chứng minh key/schema đúng hoặc sai |
| HTTP400 + provider_status/message | Request/schema hoặc key không hợp lệ; phân tích message, không suy ra chỉ từ400 |
| HTTP401/403 | Authentication/access; không đổi model tự động |
| HTTP404 | Model/endpoint availability; kiểm identity đã cấu hình |
| HTTP429 | Quota/rate limit; giữ retry0 và ngân sách |
| HTTP thành công + invalid_json_or_response/missing_text_response | Response parser/envelope |
| `abstained/invalid_extraction` | Python schema/evidence/context validator; không chuyển inference |
| extraction_ready + validated_vector_1x375=true | Extraction/mapper PASS cho một synthetic case; chưa phải semantic/clinical validation |

Sau khi sửa source phải restart server để nhận adapter mới. Dùng lại port8001 nếu8000 còn server khác.
Sau mitigation chỉ kiểm lại live khi owner cấp phép request mới; không khẳng định Gemini live PASS
từ offline fixture hoặc health xanh. Lệnh `--gemini-diagnostic` không fit/predict và luôn giới hạn1request/retry0.

Để kiểm một lượt qua cả actual Chat API/validator/LR thay vì copy JSON CLI, owner có thể mở server
trong terminal có key và cho phép đúng1 synthetic POST. Startup không gọi Gemini:

```powershell
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path; & '.\.venv-web\Scripts\python.exe' -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Giữ server chạy, chưa gửi thêm chat khi agent kiểm; mở `http://127.0.0.1:8000/` sau khi kiểm thành công.
Không cần mở router/firewall để truy cập trên cùng máy. ML ready/key configured chưa chứng minh chat live PASS.

```powershell
python -B -m pytest -q -p no:cacheprovider tests/test_local_chat.py tests/test_prediction_api.py tests/test_phase5b.py
```

Kiểm browser là opt-in, cần Chrome/Edge và Python `websockets` cài sẵn:

```powershell
$env:DISEASE_BROWSER_SMOKE = '1'
python -B -m pytest -q -s -p no:cacheprovider tests/test_local_web_browser.py
```

Agent đã chạy Chromium headless với profile tạm, actual localhost server, mock provider/model;
kiểm clarification→short answer→Top3, phủ định, urgent, reset, XSS-as-text, exact scores và responsive layout.
Windows sandbox ban đầu chặn browser IPC; kiểm thử browser riêng ngoài sandbox đã PASS.
Đây là **web/mock PASS**, không phải real model/Gemini PASS. Không có production mock switch.
Regression tests cũng chặn fit, locked-test access và protected writes; code/data/model history không đổi.

**Kết quả cuối:**202 tests API/agent PASS;1 Chromium UI test PASS bằng mock.
Bộ regression mở rộng252 cases có239 PASS/13 FAIL ở các kiểm tra notebook cũ:
working copy06 hiện gateTrue, smoke có cell `google.colab` mount; hai file có cùng hash như lúc bắt đầu nhiệm vụ.
Đây là trạng thái operator ngoài phạm vi MVP, không được sửa/Run All để chạy web.
Chưa khẳng định toàn regression suite PASS. Kiểm bản notebook lưu hành/đóng gate là việc REVIEW riêng;
MVP không chạy lại final test hoặc sửa notebook outputs.

Nguồn primary kiểm ngày2026-10-30:
[model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash),
[pricing](https://ai.google.dev/gemini-api/docs/pricing),
[quota](https://ai.google.dev/gemini-api/docs/rate-limits),
[Interactions REST](https://ai.google.dev/api/interactions-api),
[structured output](https://ai.google.dev/gemini-api/docs/structured-output).
