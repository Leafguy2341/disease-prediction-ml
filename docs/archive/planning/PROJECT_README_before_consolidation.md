> ARCHIVE — README trước hợp nhất; không dùng lệnh/trạng thái cũ để khởi động. Xem [README hiện hành](../../../README.md).

# Disease Prediction ML — Colab + Google Drive

## Local web MVP — hiện hành

Giao diện chat tiếng Việt tại **http://127.0.0.1:8000/**, route mới `POST /api/v1/chat`;
tái sử dụng Phase5B và LR tuned C=2. Có hỏi làm rõ, session/reset, urgent guard và Top3 raw model scores.
Chat API/web đã kiểm bằng mock; Chromium desktop/mobile PASS. **Real checkpoint/Prediction API PASS**
trên Windows CPython3.13.17/AMD64 trong `.venv-web`, đúng các ML versions và audited checkpoint.
Reference Colab3.13.18, checksum và8×587 probabilities/labels/Top3 PASS;
[qualification](../integration/LR_WINDOWS_COMPATIBILITY.md). **Gemini live vẫn NOT VERIFIED**.

[Làm theo hướng dẫn local MVP](../integration/LOCAL_WEB_MVP.md): copy7 artifacts read-only từ Drive,
dùng interpreter/dependency khớp identity, cấu hình key qua environment rồi chạy smokes riêng.
Không chép dataset, sửa cấu trúc Drive hoặc chạy lại notebook06.

```powershell
$ApiPython = (Resolve-Path -LiteralPath '.\.venv-web\Scripts\python.exe').Path
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
& $ApiPython -B -m scripts.smoke_local_mvp --ml
& $ApiPython -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Không bật Gemini nếu chưa muốn gửi request live. Key không nằm trong frontend/source/log;
app tối đa20 requests/process, smoke Gemini tối đa6, không retry. Xem hướng dẫn để đọc quota/usage thật.
Lệnh trên chạy tại root project hiện có7artifacts; máy nhận bàn giao cần chuẩn bị venv/pins và storage root thật.
Dừng server cũ bằng Ctrl+C trước khi mở bằng interpreter mới. Kiểm **riêng Gemini** trên Python3.11.9: dùng
`py -3.11 -B -m scripts.smoke_local_mvp --gemini-live` trong terminal đã cấu hình key/live opt-in
và metadata root đúng; xem mục3 của hướng dẫn MVP. Đây chưa phải real LR compatibility smoke.
Khi chưa đủ điều kiện, web vẫn mở nhưng báo chưa sẵn sàng và không tạo Top3.
Xem UI với môi trường đang có: `python -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1`;
health503 vẫn giữ nguyên khi thiếu/sai model. `202` API/agent tests và Chromium/mock UI PASS;
regression mở rộng có13 notebook FAIL/REVIEW theo [phạm vi kiểm thử](../integration/LOCAL_WEB_MVP.md#5-kiểm-thử-và-phạm-vi-đã-xác-minh).
Hai notebook operator được giữ nguyên; không Run All06 để khởi động web.

## Hiện hành — final evaluation closeout và Prediction API local

Final test ba ứng viên đã hoàn tất, được đối chiếu read-only từ saved predictions/metrics/manifest trên Colab:
Macro F1 test LR baseline0.7958306745796887, LR tuned C=2 **0.808163486172862**,
hard tuned0.8059813671672197. Owner đã chọn LR tuned trước test; không chọn lại từ các điểm này.
Xem [closeout report](../../../reports/final_model_evaluation_closeout.md) và [decision record](../ml/MODEL_SELECTION_RATIONALE.md).
Notebook06 giữ executed outputs, gate False/authorization trống; dùng `read_completed()` để xem lại, không chạy lại test.

FastAPI local có `GET /health`, `POST /api/v1/predict`, `/docs` và `/openapi.json`.
Chỉ load approved LR tuned C=2, checksum/env/schema375/classes587 phải hợp lệ;
không fallback baseline. Top3 dùng `predict_proba` thật ×100 với nhãn **Điểm mô hình (%)**, không chuẩn hóa Top3.
[Hướng dẫn Windows và7 artifact cần có](../integration/LOCAL_PREDICTION_API.md).
**Real checkpoint/API Windows3.13.17 PASS**: TestClient và Uvicorn HTTP health200/predict200,
Top3 đúng reference, không normalize scores. Exact training identity3.13.18 vẫn giữ nguyên,
3.11.9 không được chấp nhận cho ML. Frontend/chat local đã có; Gemini live chưa được xác minh.
Không train hoặc mở lại locked test.

Các phần packaging/lịch sử bên dưới giữ trạng thái tại thời điểm thực hiện;
ZIP cũ chưa chứa API mới, không tạo release ZIP hoặc publish source lên Drive trong bước closeout này.

## Bàn giao đang áp dụng — code local, data/model trên Drive

**2026-10-30:** đã triển khai packaging/source publication;chưa xác minh live Colab/Drive.
`project-code.zip` giải nén local Windows,mở folder `disease-prediction-ml` trong VS Code.
Chỉ `project-data.zip` giải nén bên trong `MyDrive/ML_Projects/disease-prediction-ml/`.
Code Windows không tự xuất hiện trên VM;publish payload nhỏ bằng helper hiện có,không upload từng script hoặc code ZIP.

```powershell
python -B scripts/package_handover.py code
.\scripts\prepare_colab_source.ps1 -Publish -DriveProjectPath '<actual Drive-for-desktop project path>'
```

Lệnh code tạo release mới trong `dist/handover/`,gồm ZIP,inventory,`handover_manifest.json` và bản giải nén kiểm tra.
Lệnh Publish chỉ ghi source/config/scripts;in `RUNTIME_PAYLOAD_SHA256` và `CLOUD_ACK_PENDING`.
Chờ Drive desktop sync,chọn Colab kernel,mount Drive,chạy setup notebook và paste digest vừa in.
`ROOT/scripts/` có sẵn audit helpers;không upload `.py` riêng.
Đọc [hướng dẫn từng bước](HANDOVER_GUIDE.md) và [trạng thái triển khai](RUNTIME_DISTRIBUTION_PLAN.md).

**Data ZIP hiện NOT VERIFIED:** dùng tool `data-plan`/`data` với canonical Drive đầy đủ;
không đóng gói local thiếu checkpoints. Không Run All03/04/05 để setup;06 vẫn gateFalse.
LR tuned C=2 đã được duyệt cho deployment nghiên cứu;hard tuned best observed validation Macro F1;
default code/checkpoint không bị đổi bởi packaging. Không fit,test evaluation,Gemini hoặc API trong bước bàn giao này.

<details>
<summary>Tài liệu lịch sử các Phase và hướng dẫn trước publisher — không dùng upload script rời</summary>

**Cập nhật 2026-10-30:** owner đã duyệt LR tuned C=2 cho deployment nghiên cứu trước test;
PENDING bên dưới là lịch sử2026-10-29, default code chưa đổi.
[Notebook06 — final evaluation](../../../notebooks/06_final_model_evaluation.ipynb) đã chuẩn bị,
`RUN_FINAL_LOCKED_TEST=False`; cần ủy quyền riêng trước khi đọc test.
[Protocol ba ứng viên đã khóa](../ml/MODEL_SELECTION_RATIONALE.md#final-locked-test-protocol-2026-10-30).

**Bắt đầu bàn giao:** [HANDOVER_GUIDE.md](HANDOVER_GUIDE.md) → [decision record ML](../ml/MODEL_SELECTION_RATIONALE.md#decision-record-lựa-chọn-ml).
**MODEL SELECTION PENDING:** hard tuned LR+SVC+KNN có best observed validation Macro F1 **0,79651707**;
LR tuned (**0,79315438**) là preferred deployment candidate cho API nghiên cứu cần Top3; LR baseline vẫn là default.
Đây là đề xuất chờ nhóm duyệt, không thay checkpoint/config. ML_GAPS đã có bootstrap/diagnostic benchmark thật;
chưa final evaluation, Gemini live hoặc Prediction API. Không Run All notebook03/04/05 khi chỉ nhận bàn giao.

**Lịch sử Phase4 baseline trước tuning:** Phase 4 đã hoàn tất validation trên Colab theo packet kết quả người dùng cung cấp và đã kiểm SHA-256. **Logistic Regression vẫn tốt nhất: Macro F1 0,78780814**; cả 3 Hard Voting và 2 Soft Voting đều thấp hơn trong nhóm baseline này. [Kết quả, giới hạn và khuyến nghị](PROJECT_DEVELOPMENT_LOG.md#17-2026-10-28--hoàn-tất-phase-4-từ-kết-quả-colab), [notebook ensemble](../../../notebooks/04_ensemble.ipynb), [hướng dẫn chạy](../ml/phase4_ensemble.md). Không retrain baseline hoặc mở test; dừng trước final test và chatbot.

Mục tiêu đồ án: **LLM hiểu lời kể tiếng Việt → trích xuất/chuẩn hóa triệu chứng → Python tạo vector đúng schema → ML dự đoán nhãn bệnh tiếng Anh → LLM giải thích bằng tiếng Việt**. Đây là nguyên mẫu học thuật, chưa được xác thực chẩn đoán lâm sàng. **Phase5B đã có guard/adapter Gemini/validator/mapper và hội thoại in-memory, kiểm offline; LIVE NOT VERIFIED.** Phase5A Prediction API chưa tồn tại, chưa làm frontend hoặc chatbot hoàn chỉnh.

- [Kiến trúc và hợp đồng LLM–Python–ML](../integration/SYSTEM_ARCHITECTURE.md): trách nhiệm, schema/label mapping, phủ định/chưa chắc và hỏi rõ/abstention.
- [Lý do chọn năm mô hình và BernoulliNB](../ml/MODEL_SELECTION_RATIONALE.md): giả định, tài nguyên, Voting và hai trực quan hóa dự kiến từ kết quả thật.
- [Nhật ký phát triển duy nhất của nhóm](PROJECT_DEVELOPMENT_LOG.md): lịch sử có bằng chứng, trạng thái hoàn tất/chờ/đề xuất; thêm mục khi hoàn tất thay đổi đáng kể.
- [Phase5B: code, cấu hình và cách chạy](../integration/phase5_llm_integration_design.md#8-phase5b-đã-triển-khai--cách-chạy-và-ranh-giới): live mặc định tắt, key chỉ từ môi trường,30 ca phát triển hư cấu chờ duyệt, kiểm offline205 test và port tích hợp prediction; không có endpoint mới. Config ở [phase5b.json](../../../configs/phase5b.json).

Notebook 00–05 và smoke test dùng một bootstrap trực tiếp từ source canonical trên Drive. Không cần ZIP, `.pyz`, receipt, `colab-session`, `.venv`, Conda hoặc Python Windows để chạy notebook.

[Hướng dẫn duy nhất](../runtime/phase3_colab.md). Root mặc định `/content/drive/MyDrive/ML_Projects/disease-prediction-ml`; cấu hình runtime ở `configs/runtime.json`, source chạy trong `/content/disease-prediction-ml-runtime/`, output quan trọng lưu về Drive.

1. Khi source/config đổi, chuẩn bị `dist/drive-source/` bằng `scripts/prepare_colab_source.ps1 -Refresh` (lệnh đầy đủ trong hướng dẫn), rồi upload **nội dung** vào canonical Drive root. Giữ data/artifacts/reports.
2. Mở notebook → chọn **Colab** kernel → **Colab: Mount Google Drive to Server...** và chạy cell mount.
3. Restart Kernel sau cập nhật source, rồi chạy notebook. Không upload package vào runtime sau mỗi restart.

Với onboarding, chỉ chạy smoke/preflight theo [điểm dừng 03/04](HANDOVER_GUIDE.md#4-setup-colabvs-code-và-điểm-dừng), không model/tuning cells.
Hai tuning switches có thể đang True do người dùng bật có chủ đích; False không tắt baseline fit cells03.
Chỉ cập nhật docs không cần `-Refresh` staging; `dist/drive-source/` không phải bộ source bàn giao đầy đủ.

Smoke phân ba stage: A môi trường/mount/quyền ghi, B source/imports, C integrity/schema/label encoding. A/B không phụ thuộc dữ liệu Phase 2. Audit/EDA không còn bị chặn bởi manifest hay cấu hình Phase 3. Dữ liệu Phase 2 được kiểm với baseline độc lập ở `configs/phase2_integrity.json`; không tự cập nhật checksum.

**Smoke test luồng mới đã PASS A/B/C trên Colab thật theo output người dùng gửi ngày 2026-10-27 (Python 3.13.16).** Chỉ xác minh runtime/source/integrity và nạp train/validation; chưa fit model hoặc evaluate test. [Bằng chứng kiểm tra](../runtime/portability_validation.md).

## Đọc kết quả

- [Dataset Audit](../../../reports/dataset_audit.md): nguồn, schema, chất lượng, mẫu trùng, leakage và đánh giá ban đầu.
- [EDA và Dataset Suitability Assessment](../../../reports/eda_summary.md): kết quả, điều kiện tiếp tục và ưu tiên cho Phase 2.
- [Notebook audit](../../../notebooks/00_dataset_audit.ipynb) và [notebook EDA](../../../notebooks/01_eda.ipynb): có Markdown, code, outputs và diễn giải.
- [Báo cáo cuối Phase 2](../../../reports/preprocessing_decision_review.md) và [notebook preprocessing](../../../notebooks/02_preprocessing.ipynb): pipeline đã duyệt, bảng kết quả và kiểm chứng ở đầu notebook; lịch sử kiểm tra ở phụ lục cuối.
- [Bảng](../../../../disease-prediction-ml-data/reports/tables), [hình PNG/SVG](../../../../disease-prediction-ml-data/reports/figures) và [metadata tái lập](../../../artifacts/metadata).

> Phạm vi lịch sử: các câu mô tả “chưa có mô hình” tại phần Audit/EDA dưới đây nói về output Phase1.
> Model/checkpoints Phase3/4 và ML_GAPS hiện đã có; xem decision record ở đầu README,không suy toàn project còn chưa train.

Kết luận cụ thể và số liệu chỉ có giá trị cho fingerprint CSV ghi trong manifest. Các notebook và bảng là kết quả mô tả toàn bộ dữ liệu, chưa có mô hình, bộ đặc trưng được chọn hoặc final test.

## Phương pháp và giới hạn

- Pack bit và so sánh equality chính xác để xác định vector; `pattern_id` phụ thuộc thứ tự file/cột và phải dùng kèm SHA-256. Phân biệt dòng dư với mọi dòng thuộc nhóm lặp, và xét nhãn riêng để tìm xung đột.
- EDA chạy toàn bộ dữ liệu, không lấy mẫu ngẫu nhiên. Seed 42 dự phòng cho thao tác ngẫu nhiên về sau. Các tổng đồng xuất hiện dùng float64 để tránh overflow uint8; phi của cột hằng là NA.
- Nguồn Mendeley là ứng viên dựa trên tên/schema/counts; chưa xác thực file với checksum của nhà xuất bản. Mô tả nguồn cho biết sinh nhân tạo. Không suy diễn tần suất thành tỷ lệ mắc bệnh thực tế.
- Trước huấn luyện phải chốt lớp hiếm, vector xung đột và cách chia group. Mọi bản sao của một vector ở cùng partition/CV fold. Mọi phép biến đổi học tham số chỉ fit trong train. Không dùng test để chọn mô hình hoặc trọng số ensemble.
- Phase 1 đã xem thống kê toàn CSV. Phase 2 nay khóa test cho đánh giá cuối, không tuyên bố test chưa từng được xem. Đánh giá mù nghiêm ngặt cần dữ liệu độc lập chưa thăm dò.

## Phase 2 — Pipeline đã duyệt và dữ liệu cuối

Quy trình Run All dưới đây giữ hướng dẫn Phase2 khi được giao kiểm lại riêng.
Khi nhận bàn giao,chỉ đọc kết quả vàkiểm bộ manifest đã khóa; không chạy lại Phase2 để chữa thiếu checkpoint hoặc lỗi integrity.

Mở [notebooks/02_preprocessing.ipynb](../../../notebooks/02_preprocessing.ipynb), chọn kernel, restart và Run All. Notebook có 5 phần: runtime/cấu hình → nạp và xác thực → pipeline đã duyệt → kiểm chứng split và biểu đồ → artifact và tổng kết. `RUN_HISTORICAL_INSPECTION=False` là mặc định; cờ này chỉ điều khiển một cell phụ lục cuối. Tóm tắt raw, bảng số lượng từng bước, số lớp/triệu chứng cuối, tỷ lệ split, coverage/overlap/duplicate, trạng thái tái sử dụng, đường dẫn và fingerprint **luôn hiển thị** ở luồng chính. Biểu đồ split chỉ hiển thị trong notebook, không ghi thêm hình ra reports.

Trước đây các kết quả chính đã độc lập với cờ, nhưng notebook dài với nhiều cell lịch sử bị bỏ qua và Markdown quyết định cũ nên dễ nhầm phần này với luồng chính. Bản rút gọn còn 12 cell, không ẩn output, có cả dòng tổng kết dạng text để đọc được các số liệu chính. Chưa tái hiện hoặc xác minh UI VS Code/Colab của người dùng; kiểm tra bằng kernel mới trên local không thay thế kiểm tra UI đó.

Đã kiểm tra Run All bằng hai kernel local mới với cờ `False` và `True`: bảng kết quả chính giống nhau, bộ split được tái sử dụng, checksum giữ nguyên. Outputs lưu trong notebook thuộc chế độ `False`. Các cấu hình Drive của người dùng được giữ lại; lần kiểm tra local dùng override tạm cho source/storage, không mount Drive trên Windows.

Output root phải có **cả** `data/processed/` và `artifacts/metadata/phase2/` đã khóa; nếu chạy trên Drive, đồng bộ bộ artifact đó tới storage được cấu hình. Notebook dừng khi thiếu manifest/file, không tạo lại dataset để phục vụ trình bày. Pipeline được tính lại trong RAM và đối chiếu với bộ đã khóa; checksum, schema, mapping, assignment và dữ liệu phải khớp. Lịch sử chi tiết vẫn ở reports/tables/figures và có thể tái hiện bằng cách bật cờ rồi Run All; các phân tích đó không thay đổi chính sách hoặc file đã khóa.

Chính sách riêng tại `configs/phase2.json`, không sửa ngưỡng Phase 1 lịch sử. Thứ tự cố định: validate raw → bỏ `regurgitation`/`regurgitation.1` vì không ánh xạ đáng tin cậy từ lời kể người dùng → dedup theo **vector còn lại + nhãn** → đếm lại vector/lớp → giữ lớp ≥10 → tạo group từ vector còn lại → chia khoảng 70/15/15, seed 42. Cùng vector dù khác nhãn phải cùng tập. Không thay nhãn đa số. Thiếu lớp, overlap hoặc sai tái lập sẽ dừng trước khi export, không tự đổi quy tắc.

Đầu ra dưới **output root đã cấu hình**:

- `data/processed/train.csv.gz`, `validation.csv.gz`, `test.csv.gz`: UTF-8/LF, 375 triệu chứng theo thứ tự schema rồi nhãn `diseases` nguyên bản; pandas đọc gzip trực tiếp. Không có group/row ID lẫn vào đặc trưng.
- `artifacts/metadata/phase2/feature_schema.json`, `label_mapping.json`, `preprocessing_policy.json`: schema trước variance removal, thứ tự cột và mapping nhãn 0-based cố định. Nhãn gốc được sắp xếp Unicode, không đổi tên/chuẩn hóa ngầm.
- `split_metadata.json`: số lượng từng split, support mỗi lớp, eligibility sau bỏ cột và các kiểm tra; `split_assignments.csv.gz`: raw data-row 1-based, group ID, split và split-row 0-based. Group ID gắn với fingerprint/thứ tự schema.
- `dataset_manifest.json`: raw/processed SHA-256, checksum từng file, môi trường/mã nguồn; được ghi sau cùng. `reports/preprocessing_decision_review.md` cập nhật kết quả cuối. Các bảng/hình kiểm tra cũ giữ nguyên làm lịch sử, không sinh thêm hình/bảng phụ.

Ghi file nén và kiểm round-trip ở ổ tạm local trước khi publish lên persistent storage. Khi bộ đã khóa tồn tại, kiểm mọi checksum, dữ liệu từng hàng, assignment, schema, policy và mapping rồi tái sử dụng nguyên file. Khác phiên bản Python/pandas/zlib giữa Windows và Colab không yêu cầu ghi lại metadata/file nén; phiên bản và checksum mã nguồn trong manifest ghi nhận **lần tạo gốc**. Nếu dữ liệu, policy hay split khác hoặc bị hỏng thì dừng, không force overwrite. Muốn tạo bộ khác, đặt `DISEASE_OUTPUT_DIR` tới output root khác trước setup, không trỏ thẳng vào `reports/`.

Đọc train/validation sau cell bootstrap bằng runtime đã cấu hình:

```python
from src.data.paths import OutputPaths
from src.data.preprocessing import load_final_split

output = OutputPaths(runtime_paths.output_root)
X_train, y_train, groups_train = load_final_split(output, "train")
X_val, y_val, groups_val = load_final_split(output, "validation")
```

Hàm hiện có kiểm checksum, trả X đúng thứ tự schema, y đã mã hóa bằng mapping cố định và group căn đúng hàng; không tạo loader khác. Trong notebook có thể dùng trực tiếp `OutputPaths(runtime_paths.output_root)`. Phase 3 dùng train để fit và validation để lựa chọn mô hình. Test chỉ dùng đánh giá cuối; không dùng để chọn đặc trưng, mô hình hoặc hyperparameter. Phase 1 đã thăm dò toàn CSV nên không tuyên bố test hoàn toàn chưa được xem. Chưa fit `VarianceThreshold(0)`; giữ cột hằng ở Phase 2. Bước này chỉ fit trong model pipeline trên train ở giai đoạn training, rồi dùng cùng pipeline cho validation/test/suy luận. Chatbot tương lai phải dùng đúng schema input trước bước variance, không tự thêm lại hai cột đã loại.

</details>
