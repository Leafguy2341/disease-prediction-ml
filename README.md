# Disease Prediction ML — Lắng nghe

Đồ án nghiên cứu: lời kể tiếng Việt → bộ trích xuất offline → validator/quality gate → checkpoint ML đã fit → phản hồi tiếng Việt. Dữ liệu có tính tổng hợp; gợi ý không phải chẩn đoán lâm sàng.

## Chạy website trên Windows

Code và dữ liệu ở hai thư mục cạnh nhau:

```text
ML/
├── disease-prediction-ml/       # mở trong VS Code
└── disease-prediction-ml-data/  # dataset, checkpoint và manifests
```

Cần **CPython 3.13.17/AMD64**, scikit-learn1.6.1, NumPy2.1.3, SciPy1.16.3, joblib1.6.0. Không dùng Python3.11/sklearn1.8 để load model. Trên máy mới, chỉ khi chưa có môi trường:

```powershell
py -3.13 --version
py -3.13 -m venv .venv-web
& '.\.venv-web\Scripts\python.exe' -m pip install -r requirements-api.txt
```

Tại thư mục code, trong **cùng terminal**:

```powershell
$env:DISEASE_API_STORAGE_ROOT = (Resolve-Path -LiteralPath '..\disease-prediction-ml-data').Path
$env:DISEASE_CHAT_MODE = 'offline'
& '.\.venv-web\Scripts\python.exe' -B run_api.py
```

Mở http://127.0.0.1:8000/; OpenAPI tại http://127.0.0.1:8000/docs. Không cần Jupyter hoặc API key. Nếu8000 đã được dùng, dừng đúng server cũ bằng Ctrl+C hoặc thêm `--port 8001`. Nếu đổi environment, phải khởi động lại server. `/health`503 với `storage_not_configured` nghĩa là biến storage chưa được đặt trong process server; không phải bằng chứng checkpoint hỏng.

## Ba lựa chọn mô hình

| ID trong API | Vai trò | Windows3.13.17 hiện tại | Kết quả |
|---|---|---|---|
| `lr_tuned_c2` | Default đã duyệt trước final test | ENABLED khi artifact/env PASS | Top3 predict_proba thật |
| `lr_baseline` | Đối chứng Phase3 gốc | BLOCKED: thiếu reference Windows độc lập | Top3 khi được qualify |
| `hard_tuned_lr_svc_knn` | Best observed validation Macro F1 | BLOCKED: thiếu reference độc lập cho SVC/KNN | Nhãn và phiếu bầu, không Top3 probability |

Selector lấy trạng thái thực từ `/api/v1/models`. Chỉ model đủ điều kiện mới chọn được; không fallback khi lỗi. Đổi model tạo phiên mới. LR hiển thị **Điểm mô hình (%)**,4chữ số thập phân, không chuẩn hóa lại ba score. Scores chưa calibration, không phải Accuracy hoặc xác suất mắc bệnh. Hard vote không biểu diễn phiếu như xác suất.

Endpoints: `GET /health`, `GET /api/v1/models`, `POST /api/v1/predict`, `POST /api/v1/chat`. Bỏ `model_id` giữ hành vi cũ là LR tuned. Ví dụ input có cấu trúc:

```json
{"model_id":"lr_tuned_c2","present_features":["cough","fever"]}
```

## Tài liệu và thực nghiệm

| Tài liệu | Nội dung |
|---|---|
| [Chỉ mục](docs/README.md) | Thứ tự đọc, archive và provenance |
| [Kiến trúc](docs/SYSTEM_ARCHITECTURE.md) | Source, data, runtime, hợp đồng chatbot |
| [ML experiments](docs/ML_EXPERIMENTS.md) | Bốn thí nghiệm, metrics, bootstrap và quyết định chọn model |
| [Deployment](docs/DEPLOYMENT_GUIDE.md) | Môi trường, artifact identities, API và troubleshooting |
| [Handover](docs/HANDOVER_GUIDE.md) | HaiZIP, integrity, notebook safety và rollback |
| [Development log](docs/DEVELOPMENT_LOG.md) | Bằng chứng, các thay đổi và giới hạn |
| [NLP contract](docs/phase5_llm_integration_design.md) | Evidence/context/quality gate và LLM tùy chọn |

Notebook03 chứa baseline+tuning;04 chứa ensemble baseline/tuned;05 kiểm structured inference;06 chỉ đọc completed final evaluation. **Không Run All để mở web hoặc xem kết quả.** Switch tuning03 vẫn True do owner chạy trước đây;04False;06False/authorizationrỗng. Code, outputs, execution counts và scientific evidence được bảo toàn.

Giữ375feature/318retained/587labels và135active aliases. LR tunedC2 được chọn trước final test; hard tuned giữ best observed validation Macro F1. Final test đã hoàn tất, không dùng để tối ưu lại. Metrics đầy đủ nằm trong tài liệu ML, không sao chép bảng kết quả vào README.

## Bàn giao và kiểm thử

HaiZIP đã giao ngày05 được giữ nguyên; chúng chưa chứa source cập nhật ngày11. Không trộn source cũ từ Drive vào local. Thay đổi source/config cần release inventory mới trước khi đóng gói; không tự rebuild ZIP lịch sử.

Offline tests dùng synthetic fixtures, tách khỏi qualification checkpoint thật. Không cần chạy training notebook. Xem lệnh và kết quả tại deployment guide. LLM live vẫn NOT VERIFIED; không gọi provider trong demo offline.


## PC → GitHub → laptop

Repository chung: https://github.com/Leafguy2341/disease-prediction-ml, default branch `main`. Source PC mới được đưa lên branch review `sync/pc-latest`; **chưa tự merge vào main**. Xem branch đó để review, chỉ pull main sau khi owner đã merge.

PC hiện có checkout Git riêng tại sibling `disease-prediction-ml-git-sync`. Mở folder này trong VS Code để tiếp tục commit/pull/push. Folder PC cũ chưa git init và vẫn giữ một số evidence/local files bị ignore; sửa tiếp ở đó sẽ không tự lên GitHub.

Laptop đã có repository: kiểm `git status --short`, `git branch --show-current`, `git log --oneline '@{u}..HEAD'` trước khi pull. Nếu có thay đổi local hoặc commit chưa push, backup/commit chúng vào branch riêng trước; không reset/clean cưỡng bức. Sau owner merge và laptop đang sạch:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
```

Nếu cần review trước merge: `git fetch origin`, rồi tạo checkout branch `git switch --track origin/sync/pc-latest` nếu branch local này chưa tồn tại. Không tự merge. Trên cả hai máy: pull trước khi làm, dùng branch riêng, test → commit → push; review/merge trên GitHub. Giữ tác giả Git của chính bạn, không chia sẻ token hoặc .venv.

Máy mới: `git clone https://github.com/Leafguy2341/disease-prediction-ml.git`, nhận `project-data.zip` và quyền Drive từ owner, kiểm SHA trong [external_data_release.json](configs/external_data_release.json), giải nén thành sibling `disease-prediction-ml-data`, sau đó làm theo phần chạy website ở trên. File ZIP/data/checkpoint không nằm trong GitHub. Đường tải Drive cụ thể chưa được xác minh trong vòng này; không có link giả hoặc token trong repo.


### Byte check sau khi pull tren Windows

Existing laptop checkouts can keep CRLF in unchanged files even after pulling .gitattributes. After a clean fast-forward, run this read-only standard-library check (any Python3.11+ is sufficient; it does not load models):

```powershell
python -B -m scripts.verify_checkout_bytes
```

If every reported difference is EOL_ONLY and there are no local/staged content edits, repair to the exact reviewed HEAD bytes with a new external backup directory:

```powershell
python -B -m scripts.verify_checkout_bytes --repair-eol --backup-root ..\git-eol-backup-20261111
```

The backup path must not already exist. CONTENT_CHANGE or missing files require manual review; the tool refuses them and never uses reset/clean/renormalize. Alternatively clone to a new sibling folder and keep the old laptop repository intact. This step protects source/fixture/notebook checksums without changing scientific outputs.
