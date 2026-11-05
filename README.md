# Disease Prediction ML — Lắng nghe

Nguyên mẫu nghiên cứu offline: lời kể tiếng Việt → rule-based extraction/dialogue → Python validator/quality gate → LR tuned C=2 → Top 3 và template tiếng Việt. Dữ liệu synthetic; không phải công cụ chẩn đoán đã xác thực lâm sàng. LLM là lựa chọn riêng, không cần API key cho bản demo offline.

## Bộ bàn giao hai ZIP

Giải nén cả hai gói vào cùng một thư mục cha: `project-code.zip` tạo `disease-prediction-ml/`; `project-data.zip` tạo `disease-prediction-ml-data/`. Không copy `.venv`, không trộn source cũ từ Drive vào code mới. Dữ liệu/checkpoint nằm ở folder data riêng; relative paths bên trong không đổi. Inventory SHA từng file nằm trong mỗi ZIP; SHA ZIP, CRC và kết quả clean-runtime kiểm theo receipt bên ngoài gói, không theo các release lịch sử trong `dist/`.

Từ folder code, trên Windows CPython3.13.17/AMD64 đã kiểm đúng phiên bản:

```powershell
py -3.13 --version
py -3.13 -m venv .venv-web
& '.\.venv-web\Scripts\python.exe' -m pip install -r requirements-api.txt
$env:DISEASE_API_STORAGE_ROOT = (Resolve-Path -LiteralPath '..\disease-prediction-ml-data').Path
$env:DISEASE_CHAT_MODE = 'offline'
& '.\.venv-web\Scripts\python.exe' -B -m scripts.smoke_local_mvp --ml
& '.\.venv-web\Scripts\python.exe' -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Chỉ tạo môi trường nếu chưa có; không dùng Python3.11/sklearn1.8 để load checkpoint. Mở http://127.0.0.1:8000. [Hướng dẫn bàn giao](docs/HANDOVER_GUIDE.md) giải thích source/data, tests và notebook06 chỉ đọc completed evidence. Bản offline giữ135/375feature active; không chạy notebook training hoặc final evaluation để mở web.

## Trạng thái hiện hành

- **LR tuned C=2 đã được duyệt trước final test**. Test Macro F1: LR baseline0.7958306745796887, LR tuned0.808163486172862, hard tuned0.8059813671672197; không chọn lại model từ test. Hard tuned vẫn best observed validation Macro F1.
- **REAL CHECKPOINT / Prediction API Windows PASS** cho CPython3.13.17/AMD64 và exact dependency/checkpoint identity. Schema375/mapping587; Top3 scores thật, chưa calibration, không normalize lại.
- **Gemini live NOT VERIFIED**: từng HTTP400 serving-schema complexity, HTTP503 high demand và timeout. Wire schema giữ đủ375; chưa có live extraction thành công. Web/mock PASS không là end-to-end live PASS.
- Các release117files trong `dist` và receipts20261030 là lịch sử. Bộ bàn giao hiện hành dùng hai ZIP ở thư mục cha và receipt final sau kiểm cả code/data đã giải nén. Cloud/Colab thật không được coi là đã nghiệm thu chỉ từ kiểm local; [packing trên Colab](docs/HANDOVER_GUIDE.md#7-tạo-lại-code-zip-và-đóng-data-zip-trên-colab) là quy trình riêng khi cần phục hồi Drive. Không cleanup.

## Đọc tài liệu

Bắt đầu từ [docs/README.md](docs/README.md), có inventory/mapping archive và phạm vi kiểm chứng.

| Tài liệu | Nội dung |
|---|---|
| [SYSTEM_ARCHITECTURE](docs/SYSTEM_ARCHITECTURE.md) | Thành phần, luồng và hợp đồng dữ liệu |
| [ML_EXPERIMENTS](docs/ML_EXPERIMENTS.md) | Audit/EDA, split, baseline/tuned/ensemble, bootstrap, benchmark, final test |
| [DEVELOPMENT_LOG](docs/DEVELOPMENT_LOG.md) | 11 giai đoạn kỹ thuật, kết quả/hạn chế/bằng chứng |
| [DEPLOYMENT_GUIDE](docs/DEPLOYMENT_GUIDE.md) | Windows/pins/7artifacts, FastAPI/web/Gemini, Colab và troubleshooting |
| [HANDOVER_GUIDE](docs/HANDOVER_GUIDE.md) | Hai ZIP, source publish, notebook safety và nghiệm thu |
| [Phase5 specification](docs/phase5_llm_integration_design.md) | Contract v2, evidence/context, provisional gate, evaluation/telemetry |

## Mở web local

Từ project root đã có `.venv-web`3.13.17 và đủ7artifacts đúng checksum, xem [prerequisites](docs/DEPLOYMENT_GUIDE.md). Không dùng đường dẫn python.exe placeholder hoặc Python3.11 để deserialize checkpoint.

```powershell
$ApiPython = (Resolve-Path -LiteralPath '.\.venv-web\Scripts\python.exe').Path
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
& $ApiPython -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Mở http://127.0.0.1:8000/; `/health`, `/docs`, `/openapi.json`; structured predict ở `/api/v1/predict`, chat ở `/api/v1/chat`. Startup không gọi Gemini. Key/live opt-in phải ở cùng terminal khi chủ động kiểm live; [hướng dẫn](docs/DEPLOYMENT_GUIDE.md#4-gemini-và-chẩn-đoán-live). Không suy UI configured là provider sẵn sàng.

## Notebooks và bảo toàn thực nghiệm

Notebook00/01 audit/EDA,02 preprocessing,03 baseline+tuning,04ensemble,05structured inference,06final evaluation và colab_smoke_test. Dùng shared [Colab workflow](docs/DEPLOYMENT_GUIDE.md#colab-runtime), không upload .py riêng.

**Không Run All03/04/05/06 chỉ để setup**. Switch03/04 True có chủ đích. Working copy06 hiện gateTrue/authorization của execution cũ; final evaluation đã đóng hồ sơ, chỉ đọc read_completed, không mở lại test/xóa marker. Nhiệm vụ docs không thay notebook/output. [Điểm dừng cụ thể](docs/HANDOVER_GUIDE.md#notebook-safety).

Raw CSV, Phase2/schema/mapping, source pins, checkpoints, manifests, saved predictions/reports/evidence được giữ nguyên. Báo cáo gốc: [audit](reports/dataset_audit.md), [EDA](reports/eda_summary.md), [Phase2](reports/preprocessing_decision_review.md), [Phase3](reports/phase3_post_training_audit.md), [final closeout](reports/final_model_evaluation_closeout.md). Các trạng thái cũ trong report không thay thế trạng thái hiện hành tại chỉ mục docs.
