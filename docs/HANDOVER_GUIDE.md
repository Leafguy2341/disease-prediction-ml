# Hướng dẫn bàn giao dự án

## Bàn giao cuối — hai nguồn và hai root ZIP, 2026-11-05

Code lấy từ Windows source hiện hành đã freeze; scientific data/model lấy từ bản tải Drive độc lập. Không đổi tên hoặc xóa hai nguồn gốc. Tên folder `(data)` chỉ là vị trí download của máy xây gói, không phải tên trong ZIP. Sau giải nén cùng thư mục cha:

```text
ML/
├── disease-prediction-ml/       # project-code.zip
└── disease-prediction-ml-data/  # project-data.zip
```

Code có source/app/config/notebooks/tests/docs và22fixture/evidence đã pin; không có `.venv`, cache, .git, .env, dataset lớn hoặc model binary. Data có raw/processed, schema/mapping,5baseline/5tuned checkpoints, ensemble definitions/manifests, predictions và scientific reports. Sáu audit packets chỉ được pin ở source provenance được bổ sung nguyên byte vào data bundle theo data requirements; không dùng repo để bù dataset/weights. Các đường dẫn trùng giữa hai package chỉ là shared evidence/configuration contracts đã xác minh cùng SHA, không phải hai model khác nhau.

Mỗi ZIP có inventory nội bộ nằm trong root tương ứng. Receipt/CSV kiểm kê ngoài nguồn trong folder release cạnh hai ZIP ghi root provenance, exclusions/conflicts, SHA/CRC và clean-extraction runtime. Chỉ receipt `HANDOVER_READY` sau kiểm cả hai ZIP mới là kết quả nghiệm thu; không dùng dòng trạng thái/ZIP lịch sử để thay thế. Không có publish Drive hoặc retrain trong quá trình đóng gói.

Từ folder code, dùng CPython3.13.17/AMD64 và requirements-api.txt với exact ML pins. Sau khi đã kiểm `py -3.13 --version`, nếu chưa có môi trường:

```powershell
py -3.13 -m venv .venv-web
& '.\.venv-web\Scripts\python.exe' -m pip install -r requirements-api.txt
$env:DISEASE_API_STORAGE_ROOT = (Resolve-Path -LiteralPath '..\disease-prediction-ml-data').Path
$env:DISEASE_CHAT_MODE = 'offline'
& '.\.venv-web\Scripts\python.exe' -B -m scripts.smoke_local_mvp --ml
& '.\.venv-web\Scripts\python.exe' -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Mở http://127.0.0.1:8000; không cần LLM key. `configs/runtime.local.example.json` dùng sibling data root cho utilities; API vẫn nhận `DISEASE_API_STORAGE_ROOT` bằng cơ chế hiện có. Thiếu/sai7deploymentartifacts hoặc environment mismatch phải dừng; không fallback LR baseline.

Để kiểm local mà không train/evaluate: chạy ML smoke ở trên, kiểm OpenAPI/health và hội thoại synthetic/batch/preview. Các unit tests lịch sử đọc metadata mặc định ở project root: trước khi chạy nhóm đó, bố trí bản sao byte-identical của `feature_schema.json`/`label_mapping.json` tại `artifacts/metadata/phase2/` của code root và kiểm hash theo phase2_integrity.json; đây chỉ là small test metadata, không copy weights/dataset vào code ZIP. Không chạy cả notebook/full suite với opt-in training/data regression khi chỉ muốn demo. Tests notebook06 dùng synthetic fixtures, không chạy final evaluation thật.

Notebooks Colab vẫn dùng canonical `/content/drive/MyDrive/ML_Projects/disease-prediction-ml`. Khi phục hồi Drive, dùng **nội dung bên trong** folder `disease-prediction-ml-data/` cho root canonical; không thêm một cấp wrapper vào paths artifact. Publish runtime source bằng helper hiện có từ local code và dùng digest mới. Các mount/source pins trong notebook cần được nhập theo runtime mới; chúng không thể trỏ trực tiếp ổ Windows. Notebook06 chỉ replay completed evidence đúng manifest, gateFalse/authorizationrỗng; không rerun final test. Quy trình này không cần gọi LLM hoặc chạy notebook03/04 để mở web.

## Handover blockers đã đóng — 2026-11-05

Notebook06 hiện chỉ đọc completed evidence đã kiểmSHA; không có execution path evaluate/predict hoặc copy lênDrive. GateFalse và authorizationrỗng luôn giữ mặc định; bật gate sẽ bị chặn ngay. Outputs/counts lịch sử giữ nguyên. Xem [báo cáo bảo trì](../reports/handover_blocker_fix.md) cho targetedtests và giới hạn xác minh.

Allowlist bổ sung đúng22file trong [policy portable](../configs/handover_code_supplements.json); không sửa chúng sau freeze. CodeZIP vẫn loại dataset/checkpoint, .env, cache, .venv và git. Khi nhận cả data-side, chuẩn bị7deploymentartifacts theo hướng dẫn hiện có; không lấy checkpoint khác làm fallback. **Code handover READY; chưa có ZIP mới, dataZIP/Drive chưa được xác minh trong vòng này.** Các mục BLOCKER ngày04 bên dưới là lịch sử đã được đính chính ở đây. Khi publish source sau bảo trì, lấy digest mới từ helper hiện có; không tái sử dụng pin source cũ hoặc upload module riêng.

## Freeze cuối 2026-11-04

Giữ **135/375 active**, không kích hoạt thêm alias. [Final release gate](../reports/final_release_gate.md) phân biệt local offline website đã kiểm checkpoint/HTTP thật PASS với **BLOCKER bàn giao toàn dự án**: notebook06 thiếu closeout-viewer contract và packaging allowlist thiếu test/evidence supplements. Notebook06 gate đã tắt, authorization source rỗng, output lịch sử giữ nguyên; không Run All để đánh giá lại test.

[Manifest đóng gói dự kiến](../reports/release_final_gate/packaging_artifact_manifest.json) ghi SHA từng source/config và đúng7artifact deployment, cùng supplements bắt buộc. Đây là inventory/freeze, **không phải ZIP đã hoàn tất**. Danh sách data-side chỉ lấy từ identity đã khóa, chưa kiểm Drive trong vòng này. Không phát hành ZIP từ allowlist cũ rồi coi là đầy đủ tests. Không tiếp tục script activation cũ: cả127ứng viên đã không đạt kiểm ngữ cảnh cuối. Local demo cần đúng môi trường ML đã duyệt và artifact root; không cần LLM key trong offline mode.

## Packet semantic review375 hiện hành

Dùng [bảng375](../reports/terminology/symptom_dictionary_review.csv), [changes](../reports/terminology/symptom_dictionary_changes.csv) và [collisions](../reports/terminology/symptom_dictionary_collisions.csv) để gửi ChatGPT/người duyệt. Full CSV hiện có SHA40aa98c794817ad7b2eaa56e39060fecd96d5231928e3737da0f9628a65b63dc; thay thế packet proposal trước, không phải thay model/manifest. Có266READY nhưng145trong đó cònpending; không tự bật chúng từ nhãn READY. Actual activation135/240không đổi, các alias mới chỉ ở proposed_aliases_vi, không được runtime đọc.

Ưu tiên27AMBIGUOUS/26HIGH_RISK_COLLISION: cần publisher giải thích các cột trùng/gần nghĩa, không gộp schema hoặc tự đặt bản dịch khác nhau để giả vờ phân biệt. Hai nhãn AMBIGUOUS và12HIGH_RISK đã active từ lịch sử cần quyết định riêng; chưa tự tắt hoặc thay chúng. Confidence là đánh giá ngôn ngữ, mọi mục vẫn cần human review và không được tự nhận bác sĩ thẩm định. 86synthetic cases nằm trong data/evaluation/vietnamese_symptom_semantic_cases.jsonl. Không đổi weights, dữ liệu, source pins, runtime, Drive hay ZIP. Xem hướng dẫn triển khai mới nhất để đọc đúng count/nguồn/giới hạn.

## Bàn giao continuity và review packet375 — hiện hành

Xem mục đầu [DEPLOYMENT_GUIDE](DEPLOYMENT_GUIDE.md) cho nút hỏi thêm/bổ sung/preview, budget2vòng/24lượt và cách chạy lại server. Preview một triệu chứng chỉ do user chủ động, vẫn chặn mơ hồ/uncertain/urgent và giữ checkpoint integrity. Không cần key hoặc chạy notebook để dùng offline.

Gửi [CSV375feature](../reports/terminology/symptom_dictionary_review.csv) lên ChatGPT để rà soát trước khi bật các alias mới. Có375đề xuất nhưng135feature có alias Việt active;240pending, trong đó17AMBIGUOUS và nhiều near-collision cần định nghĩa nguồn. Không tự đổi canonical feature, gộp nhãn gần nghĩa hoặc kích hoạt pending chỉ để đạt coverage100%. File generated này được tạo từ script báo cáo hiện có; chưa tạo ZIP bàn giao mới.

UI dùng “Điểm tự tin dự đoán” kèm “Accuracy trên tập test:84,4082%” một lần, nếu đúng frozen closeout evidence/checkpoint. Đây không phải độ chính xác mỗi gợi ý hoặc xác suất bệnh. Metadata optional `artifacts/metadata/final_evaluation_audit/colab_evidence.json` trong code project giúp hiển thị benchmark; SHA phải đúng packet đã khóa. Không cần thêm nó vào7artifact loader bắt buộc, không lấy test CSV để tạo lại. Thiếu packet thì benchmark NOT VERIFIED, không invent hoặc fallback metric. Raw API score_label giữ tương thích, score không đổi. Xem nhật ký cho file sửa/tests; weights/schema/mapping/manifests/source pins không đổi.

## Cập nhật bàn giao Offline V2 — 2026-11-04

Source local hiện có giao diện mới, batch questions và registry chỉ LR tuned; ZIP lịch sử chưa tự chứa bản cập nhật này. Không tạo ZIP mới trong nhiệm vụ V2. Xem mục Offline V2 đầu [triển khai](DEPLOYMENT_GUIDE.md) để chạy `.venv-web`, explicit offline và cổng8000. Không chạy notebook/training/final test để mở web. Không cần key hoặc nguồn trên Drive cho phiên web khi 7 artifact approved đã có local.

Bàn giao thêm thay đổi ở src/agent/offline.py, extraction.py, conversation.py; app/backend/chat.py, schemas.py, main.py; app/frontend; configs/synonyms.json, disease_names_vi.json, phase5b.json; script báo cáo thuật ngữ và regression/browser tests. Không thay pinned ML source, checkpoints, schema/mapping hoặc manifests. Model khác không được chọn chỉ vì có checkpoint. Online/key UI chưa kết nối và không lưu/gửi secret; không coi UI provider selection là live qualification.

Giới hạn cần người tiếp nhận biết: 136/375 symptom features có alias Việt, 43 feature được dùng cho hỏi chủ động; nhóm ngữ cảnh và policy dừng là heuristic. Hai tên bệnh có đối chiếu nguồn thuật ngữ, 581 draft và4 ambiguous; không phải bác sĩ thẩm định. Bộ parser theo số có cú pháp giới hạn và cần batch_id; câu trả lời mơ hồ không được suy diễn. Giữ disclaimer, canonical labels, score gốc và states unknown/denied riêng biệt.

## 1. Đọc và nhận đúng thành phần

Đọc [chỉ mục](README.md) → [kiến trúc](SYSTEM_ARCHITECTURE.md) → [thực nghiệm/quyết định ML](ML_EXPERIMENTS.md) → [triển khai](DEPLOYMENT_GUIDE.md). [Nhật ký kỹ thuật](DEVELOPMENT_LOG.md) ghi các giới hạn và bằng chứng; archive chỉ để truy xuất lịch sử.

LR tuned C=2 đã được duyệt trước final test. Final evaluation đã đóng hồ sơ, không chạy lại để onboarding. Gemini/Groq live vẫn NOT VERIFIED; web/mock và ML API PASS không đồng nghĩa chatbot live PASS.

Hai ZIP có ownership khác nhau:

| Thành phần | Nơi giải nén/vai trò | Nội dung |
|---|---|---|
| project-code.zip | Local Windows, VS Code Open Folder disease-prediction-ml | src/app/notebooks/scripts/tests/configs công khai/docs/README/requirements/setup |
| project-data.zip v2 | Giải nén tại MyDrive/ML_Projects/; ZIP tự chứa disease-prediction-ml/ | raw/processed, metadata/schema/mapping/manifests, baseline/tuned checkpoints, predictions/evidence/reports |
| Small runtime payload | Bản publish sinh từ code local, lưu canonical Drive | Chỉ source/config/requirements/audit scripts cần trên VM |
| Runtime/cache | /content/disease-prediction-ml-runtime và /content/disease-prediction-ml-cache | Tạm; reset VM có thể mất, không lưu kết quả quan trọng ở đây |

Không upload code ZIP/full workspace lên Drive. dist/drive-source không phải source bàn giao đầy đủ: không có toàn bộ notebooks/docs/tests/app. Không chuyển data ZIP vào code tree để sửa links. Mount Drive trong notebook không làm Windows truy cập /content/drive.

## 2. ZIP và integrity trước giải nén

Release lịch sử handover_manifest (../dist/handover/release-20261030-e5936121/handover_manifest.json, historical release) ghi code ZIP117files,1.609.487bytes, SHA256 **5ce88547e28166808c21c701e1263a2928b81de35987995c8bc77e52e7f69d09**; đây là bản cũ, không chứa các thay đổi sau lúc tạo. File dist được loại khỏi code ZIP mới; link lịch sử này chỉ tồn tại trong workspace gốc. Không dùng checksum cũ cho ZIP mới.

Đợt final packaging được owner cho phép riêng: `project-code.zip` mới được tạo **ngoài repository**, cạnh folder source Windows; thông số chính xác nằm ở `handover-final-20261030/handover_manifest.json` cạnh ZIP, kèm `cleanup-candidates.json` và kết quả import offline. Inventory SHA từng file nằm trong ZIP tại `disease-prediction-ml/handover_code_inventory.json`. Không ghi checksum ZIP vào chính nội dung ZIP vì sẽ tạo vòng tự tham chiếu.

Data ZIP **NOT VERIFIED**; không có checksum hoàn tất để công bố. Không gọi local ZIP thiếu checkpoints là bản data hoàn chỉnh. Trước bàn giao cuối phải kiểm đủ inventory bằng packager hiện có trên canonical Drive, trong nhiệm vụ được cho phép riêng.

Trước extract, so Get-FileHash với checksum release tin cậy, không lấy expected từ chính archive chưa xác minh:

```powershell
Get-FileHash -LiteralPath '<actual path to project-code.zip>' -Algorithm SHA256
```

Code ZIP chứa folder disease-prediction-ml; giải nén vào parent Windows tùy chọn. **Data ZIP v2 mới** chứa disease-prediction-ml/data, artifacts, reports và inventory ở gốc ZIP; giải nén tại **MyDrive/ML_Projects**, không giải nén vào canonical root thêm lần nữa. Archive v1 lịch sử có layout khác; dùng inventory/archive_prefix để phân biệt. Helper extract kiểm path traversal/inventory, skip identical và dừng khi file cũ khác bytes:

```powershell
python -B scripts/package_handover.py extract --archive '<verified project-data.zip>' --output '<mounted MyDrive/ML_Projects parent>' --expected-sha256 '<approved data ZIP checksum>' --allow-locked-bytes
```

Đây là lệnh hướng dẫn sau khi data release được VERIFIED, không phải yêu cầu chạy bây giờ. allow-locked-bytes chỉ cho opaque copy/hash, không cấp quyền parse/evaluate test. Không overwrite manifest variants hoặc xóa bản Drive đã giải nén.

## 3. Source và artifacts cần bảo toàn

```text
disease-prediction-ml/
  src/data/             audit, preprocessing, integrity, Colab bootstrap
  src/models/           training, ensemble, tuning, final evaluation
  src/agent/            provider, extraction, conversation
  app/backend/          FastAPI, LR service, chat adapter, schemas
  app/frontend/         HTML/CSS/JS local
  configs/              public config và protected identity baselines
  notebooks/            00..06 và colab_smoke_test
  scripts/              publisher, packager, audits, smoke
  tests/                offline/synthetic và integration tests có prerequisites
  docs/                 tài liệu hiện hành, stubs và archive
  data/evaluation/      ca synthetic development có annotation nháp
```

Dataset: data/raw giữ nguyên filename thực; data/processed/{train,validation,test}.csv.gz. Metadata khóa: artifacts/metadata/phase2. Baseline checkpoints: artifacts/models/phase3/baseline-v1-f8a5bfdb7b4c12cd. Tuned: artifacts/models/tuning/tuning-v1-9c4dd013abbba14a, metadata tuning cùng experiment. Ensemble run phase4-20261028T091711786379Z-c1c66643 và tuned-ensemble-20261029T041701354242Z-6c84dbfe; definitions, manifests, predictions và linked reports phải giữ cùng nhau.

Final bundle: artifacts/metadata/final_evaluation/049ee0aa3c290798 trên Drive, giữ marker/manifest/predictions/report. Các packets audit nằm artifacts/metadata/{phase3_audit,phase4_audit,post_tuning_audit,model_analysis,final_ml_gaps,final_evaluation_audit}; không thay weights bằng packets. Bảy file local cho LR và runtime qualification nằm trong [deployment guide](DEPLOYMENT_GUIDE.md#2-bảy-artifact-local-bắt-buộc).

Local hiện có LR deployment subset và evidence; **không suy toàn bộ năm baseline/năm tuned/full reports đã local**. Quyền Drive phải được cấp riêng, không có private link/key trong tài liệu. Inventory Drive cũ là snapshot, không chứng minh bản cloud hôm nay đồng bộ. [Inventory chi tiết lịch sử](archive/planning/WORKSPACE_HANDOVER_PLAN.md), [runtime audit/plan lịch sử](archive/planning/RUNTIME_DISTRIBUTION_PLAN.md).

<a id="source-publish"></a>
## 4. Publish source khi code thay đổi

Tại project local, dùng helper hiện có; không thêm sync framework/Git hosting bắt buộc. Stage/check-only không gửi dữ liệu lên cloud:

```powershell
python -B scripts/package_handover.py stage --check-only
```

Nếu current stage không khớp source, chủ động chạy cùng command bỏ --check-only, giữ output folder/dòng RUNTIME_PAYLOAD_SHA256. Không chạy -Refresh chỉ vì sửa docs. Publisher không copy dataset/checkpoint từ Windows, chỉ allowlisted runtime source/config/scripts; source pins và approved Phase2 manifest phải hợp lệ.

Có Drive for desktop: lấy **đường dẫn thật** trong Explorer, không giả định ổ G:. Windows source và destination phải là hai folder riêng:

```powershell
.\scripts\prepare_colab_source.ps1 -Publish -DriveProjectPath '<actual Drive desktop project path>'
```

Nếu cần, -PythonExe chọn interpreter có sẵn. Lệnh tương đương: `python -B scripts/package_handover.py publish --drive-project-path '<actual Drive desktop project path>'`. Output LOCAL_DRIVE_COPY_VERIFIED/CLOUD_ACK_PENDING chỉ xác nhận copy local, **không xác nhận cloud sync**; đợi client sync, rồi so digest trên Colab VM mới.

<a id="không-có-drive-for-desktop"></a>
### Không có Drive for desktop

Workflow hiện tại dùng mount notebook. Sau stage, VS Code Upload to Colab **nguyên folder** dist/drive-source/<digest> vào /content, không từng .py/code ZIP. Mount Drive bằng extension trước; VM phải có seed/scripts/package_handover.py và canonical metadata Phase2 thực. Publish là bước ghi source có chủ đích, **không đặt vào smoke/06**:

```python
import runpy
from pathlib import Path
expected = '<RUNTIME_PAYLOAD_SHA256 từ stage local>'
seed = Path('/content') / expected
drive = Path('/content/drive/MyDrive/ML_Projects/disease-prediction-ml')
if not Path('/content/drive/MyDrive').is_dir():
    raise FileNotFoundError('Mount đúng Drive trước; không tạo thư mục giả.')
if not (seed / 'scripts/package_handover.py').is_file():
    raise FileNotFoundError('Upload đủ nguyên folder payload trước.')
source = runpy.run_path(str(seed / 'src/data/colab_runtime.py'))
source['read_source'](seed, 3, expected_payload_sha256=expected)
publisher = runpy.run_path(str(seed / 'scripts/package_handover.py'))
print(publisher['publish'](seed, drive))
```

Sau publish, tạo **VM mới**, mount Drive, setup với digest từ Windows; không upload seed lần nữa. Chỉ khi VM mới bootstrap/import/session/integrity PASS mới xác nhận persistence của release đó. Cloud sync/clean-room hiện vẫn **NOT VERIFIED**. Reset VM thường chỉ mount+setup lại; không publish nếu code chưa đổi.

<a id="notebook-safety"></a>
## 5. Điểm dừng notebooks và scripts

notebooks/README có mô tả baseline/runtime lịch sử; dùng tài liệu hiện hành ở docs cho quyết định model và workflow mới, không coi index cũ là lệnh Run All để onboarding.

- colab_smoke_test: sau mount/expected digest, các cell setup/import/integrity/session được phép; không fit hoặc mở test. Read-only checkpoint reload cần artifact/environment/trust hợp lệ và kiểm riêng.
- 00/01: audit/EDA toàn raw lịch sử; không chạy để setup API.
- 02: preprocessing policy/locked artifacts; không chạy lại để chữa integrity/thiếu checkpoint.
- 03: năm baseline cells có thể fit nếu thiếu checkpoint. RUN_HYPERPARAMETER_TUNING chỉ điều khiển tuning, False **không** ngăn baseline fit. Working copy hiện True có chủ đích.
- 04: ensemble/predict validation, RUN_TUNED_ENSEMBLE hiện True có chủ đích; không Run All khi chỉ onboarding.
- 05: inference checks có predict; không phải setup-only.
- 06: final evaluation đã hoàn tất, working copy hiện RUN_FINAL_LOCKED_TEST=True/authorization có sẵn từ execution. **Không Run All**, không xóa marker; dùng read_completed cho completed bundle. Khuyến nghị bản lưu hành gate off chưa đồng nghĩa file hiện tại đã off. Nhiệm vụ docs không sửa notebook/output.

Sau reset, setup mở lại session = ColabTraining.open(RUNTIME), không cần chạy training. Scripts audit có tại ROOT/scripts: audit_phase3_results.py, audit_post_tuning.py, audit_final_ml_gaps.py và package_handover.py; final evaluation module ở ROOT/src/models. Không dùng /content/<script>.py upload rời; các đoạn đó trong archive là cách cũ.

## 6. Tests, rollback và nghiệm thu

[Deployment guide](DEPLOYMENT_GUIDE.md) là hướng dẫn duy nhất cho Python/pins, bảy artifacts, web/Gemini env và troubleshooting. Offline API/agent tests dùng mock; real ML smoke riêng; Gemini diagnostic tiêu request thật và phải giới hạn rõ. Không chạy full legacy data regression hoặc locked-test evaluation để onboarding. Distribution fixtures: `python -B -m pytest -q -p no:cacheprovider tests/test_distribution.py`, cần dependencies đã cài; PASS fixture không chứng minh cloud sync.

.gitignore bỏ .venv-web/cache/dist/.env/checkpoints/datasets khỏi repository. Source handover cần src/app/notebooks/scripts/tests/public configs/docs/README/requirements/setup và development JSONL; không credential/config private. Notebook outputs có thể lớn nhưng được giữ nguyên, không strip. Gitignore không chứng minh bản ZIP cũ đầy đủ API/docs hiện hành; dùng inventory/checksum gói thực.

Giữ tám ML source pins, hard-vote engine, Phase2/schema/mapping, fit metadata/checkpoints/tuning/final manifests/predictions/marker và reports. Không cleanup venv/cache/backup/archives/staging, không đổi canonical root. Rollback source chỉ bằng publish lại known-good release đã duyệt và Restart Kernel; không ghi đè metadata/model khác identity.

Nghiệm thu còn thiếu: data ZIP đầy đủ+checksum, clean VM bootstrap/release digest/session/scripts/checkpoint verification trên Drive thật, Gemini/Groq live acceptance/extraction và human-reviewed quality gate/evaluation. Offline archive/import/fixture PASS không là clean-room cloud/live PASS. Đợt đóng gói mới không publish source hoặc sửa dữ liệu Drive tự động.

## 7. Tạo lại code ZIP và đóng data ZIP trên Colab

Packager chỉ dùng Python standard library. Từ source Windows, lệnh dưới tạo code ZIP trực tiếp ở parent và receipt/extraction ở folder evidence mới. Nếu ZIP đã tồn tại và khác inventory, lệnh dừng, giữ nguyên ZIP cũ; cần kiểm và lưu bản cũ ở vị trí riêng trước khi owner quyết định thay. Không tự thay hoặc xóa deliverable:

```powershell
& '.\.venv-web\Scripts\python.exe' -B scripts/package_handover.py code --output '..\handover-final-20261030' --archive-destination '..\project-code.zip'
```

Code allowlist gồm src/app/scripts/tests/notebooks/docs đầy đủ archive, public config và runtime examples, requirements/setup/README, JSONL development, sáu report Markdown gọn và small JSON provenance allowlist (audit, compatibility/reference, Gemini diagnostic đã che key). Đây là code-side verification evidence bổ sung, không thay full dataset/model bundles. Notebook source/output giữ nguyên byte, kể cả gate execution lịch sử; không Run All06. Không có raw/processed payload, joblib/NPZ, virtualenv/cache/dist, secret/private config. Gói data giữ nguyên mọi path contract; trùng bytes ở hai path lịch sử vẫn giữ khi cần để manifest/import hoạt động, không nhân thêm checkpoint mới.

### Colab: kiểm kê trước, duyệt INCLUDE rồi mới đóng ZIP

Không có quyền đọc Drive từ agent Windows, nên **data ZIP NOT VERIFIED** cho tới khi owner chạy các cell sau và cung cấp receipt. Không dùng local LR subset làm data release. Không cần gọi LLM, load model hoặc chạy notebook06. Dùng kernel Colab của VS Code, mount đúng MyDrive bằng extension. Upload **project-code.zip vào Colab Runtime `/content/`**, không vào Drive; đây là gói code đã có, không tạo source ZIP thứ hai và không upload từng .py. Thư mục giải nén tạm chỉ dùng cho packing, không thay bootstrap/sync production.

Cell 1 — xác minh SHA nhận riêng từ người bàn giao, giải nén code vào thư mục mới:

```python
from pathlib import Path, PurePosixPath
import hashlib, json, runpy, stat, zipfile

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

code_zip = Path('/content/project-code.zip')
expected_code_sha = input('SHA-256 code ZIP từ handover_manifest/người bàn giao: ').strip().lower()
assert len(expected_code_sha) == 64 and sha(code_zip) == expected_code_sha
temporary_code = Path('/content/handover-code')
assert not temporary_code.exists(), 'Giữ folder cũ; chọn folder tạm mới nếu đã chạy.'
with zipfile.ZipFile(code_zip) as z:
    for info in z.infolist():
        name = info.filename
        p = PurePosixPath(name)
        assert not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name
        assert not stat.S_ISLNK(info.external_attr >> 16)
    assert z.testzip() is None
    z.extractall(temporary_code)
CODE = temporary_code / 'disease-prediction-ml'
pack = runpy.run_path(str(CODE / 'scripts/package_handover.py'))
pack['verify_archive'](code_zip, expected_sha256=expected_code_sha)
DRIVE = Path('/content/drive/MyDrive/ML_Projects/disease-prediction-ml')
assert Path('/content/drive/MyDrive').is_dir() and DRIVE.is_dir(), 'Mount Drive thực trước; không tạo folder giả.'
```

Cell 2 — inventory chỉ đọc tên/size, chưa mở payload nào; lưu báo cáo ngoài source Drive:

```python
inventory = pack['drive_inventory'](DRIVE)
pack['exclusive']('/content/drive-data-inventory.json', pack['encoded'](inventory))
print(json.dumps({k: v for k, v in inventory.items() if k != 'files'}, indent=2))
```

Cell 3 — phép băm opaque bytes được owner cho phép riêng cho đóng gói (không parse CSV/NPZ/joblib/test, không predict). Xác minh raw/Phase2, năm baseline+năm tuned, manifest ensemble/tuning, completed final bundle và source evidence. Bản cùng path khác SHA **dừng**, không thay variant. INCLUDE ghi từng source path, ZIP member, bytes/SHA và origin Drive/code_provenance; chỉ bổ sung small local evidence khi Drive thiếu, không ghi vào Drive nguồn:

```python
PLAN = Path('/content/data-handover-include.json')
plan = pack['prepare_data_release'](CODE, DRIVE, PLAN, allow_locked_bytes=True)
PLAN_SHA = sha(PLAN)
print(json.dumps({k: v for k, v in plan.items() if k not in ('include', 'excluded', 'inventory')}, indent=2))
print('INCLUDE_PLAN_SHA256=' + PLAN_SHA)
```

Mở `/content/data-handover-include.json` để duyệt INCLUDE/excluded và duplicate-path notes. Kiểm Google Drive Storage UI còn ít nhất `archive_space_upper_bound` bytes; số free từ filesystem mount **không** chứng minh quota tài khoản. VM phải còn `temporary_extraction_required_bytes` cho extract đầy đủ; script kiểm disk free. Kích thước ZIP thực chỉ biết sau nén, không đưa số giả. Thiếu artifact/ref hay conflict thì STOP, gửi lỗi; không bỏ kiểm tra để tạo ZIP thiếu.

Cell 4 — chỉ sau khi duyệt plan/dung lượng, đóng archive trong folder sibling mới, không trong canonical source:

```python
free_bytes = int(input('Số bytes còn trống đã kiểm trong Google Drive Storage UI: '))
OUTPUT = Path('/content/drive/MyDrive/ML_Projects/handover-disease-prediction-ml-20261030-final')
receipt = pack['pack_data_release'](PLAN, OUTPUT, expected_plan_sha256=PLAN_SHA,
    confirmed_drive_free_bytes=free_bytes, allow_locked_bytes=True)
print(json.dumps(receipt, indent=2))
```

Output chính xác: `OUTPUT/project-data.zip` và `OUTPUT/data_handover_manifest.json`. Script kiểm CRC/member SHA, source trước/sau, extract đầy đủ vào folder mới ở `/tmp/handover-data-extraction-*`, giữ folder đó để kiểm; không cleanup. Chỉ ghi VERIFIED receipt cuối cùng nếu tất cả PASS. File ZIP thiếu receipt VERIFIED là incomplete/NOT VERIFIED; không ghi đè hoặc cố resume một archive dang dở. Không đọc locked test để tính metric hoặc fit model.

Tải ZIP + receipt từ Drive, kiểm SHA trên Windows. Sang Drive mới, upload data ZIP, mount, dùng pack['extract'] với **SHA nhận riêng** và output `/content/drive/MyDrive/ML_Projects`; không giải nén lồng thêm canonical folder. Giữ bản đã giải nén trên Drive. Cloud Drive hiện tại chưa được agent xác minh; phải gửi receipt/inventory nếu cần hoàn tất kiểm chứng.

## 8. Máy mới và cleanup chưa được phép

Giải nén code ZIP local, VS Code Open Folder đúng `disease-prediction-ml`; tạo `.venv-web` bằng CPython3.13.17/AMD64, cài `requirements-api.txt` theo deployment guide. Không chạy setup.ps1 cũ (Phase1/.venv) để setup API. Nhận/copy read-only đúng bảy artifacts của LR từ data Drive về một artifact root Windows; đặt `DISEASE_API_STORAGE_ROOT` tới root đó. Code ZIP không có weights nên startup chưa thể health200 nếu chưa copy đủ. Giữ exact ML pins; không fallback baseline khi thiếu tuned. Chỉ chạy smoke ML synthetic khi chủ động muốn kiểm máy mới, không final test/LLM.

Với notebook Colab, stage/publish nhỏ theo mục4; seed có audit scripts đồng bộ, bootstrap xác minh digest, `ColabTraining.open(RUNTIME)` tạo session mà không train. Fixture startup/import/restart được kiểm offline; **Colab cloud clean-room và checkpoint reload sau giải nén trên máy mới vẫn NOT VERIFIED** cho tới khi chạy thật.

`cleanup-candidates.json` cạnh receipt code là danh sách itemized A cache, B archives/exports, C môi trường/staging cần review, D scientific evidence KEEP; gồm absolute path, bytes, references, archive coverage và rủi ro. Không coi virtualenv là cache, không coi archive cũ là duplicate chỉ vì tên. Drive copy của từng mục NOT VERIFIED. Không xóa/move/rename bất kỳ mục nào; owner phải duyệt từng absolute path sau khi đủ hai ZIP và kiểm clean-room. Không dọn cả thư mục reports/artifacts/datasets hoặc execution marker.


## Chat offline — bản source cập nhật 2026-11-02

Chạy theo [Deployment guide, mục 3a](DEPLOYMENT_GUIDE.md#3a-chạy-website-offline-2026-11-02). Chỉ cần bảy artifact LR đã quy định và runtime Windows được duyệt; đặt DISEASE_CHAT_MODE=offline trước khi khởi động server. Không cần key, không publish source/Drive để chạy web Windows.

Source bàn giao cần thêm configs/synonyms.json, src/agent/offline.py, scripts/demo_offline_chat.py, scripts/build_synonyms_report.py và tests/test_offline_chat.py cùng các thay đổi backend/UI/validator. scripts/package_handover.py đã allowlist dictionary; ZIP đã tạo trước đây chưa chứa các thay đổi này và được giữ nguyên. Data/checkpoint/schema/mapping vẫn ở layout cũ. Không dùng code ZIP cũ để khẳng định có chế độ offline mới.

Dictionary là draft: 45/375 feature có alias Việt, 100% mục cần review. Terminal review report liệt kê chính xác các mục thiếu alias và collision; không tự dịch disease labels. LLM adapters vẫn giữ như tùy chọn riêng, không phải fallback offline. Không thay dataset/model để mở rộng từ vựng.


### Bổ sung health intent và display (2026-11-02)

Code handover tiếp theo cần configs/disease_names_vi.json và src/agent/presentation.py cùng source/backend/frontend/config/test cập nhật. Allowlist package đã nhận dictionary; ZIP hiện có giữ nguyên và chưa chứa bản sửa mới. Không có thay đổi data/checkpoint/Drive. Hướng dẫn health intent, formatting 4 decimals và review tên bệnh ở [Deployment guide](DEPLOYMENT_GUIDE.md). Tên Việt chỉ bật theo needs_review=false sau rà soát thật; hiện tất cả 587 entry vẫn pending review. Không dùng việc UI hiển thị được tiếng Việt để kết luận model được hiệu chuẩn hoặc xác thực lâm sàng.


### Dictionary Việt tham khảo cho phạm vi môn học

Bản source hiện hành bật ALLOW_DRAFT_TRANSLATIONS=true theo quyết định của phụ trách đồ án: 583 tên Việt/4 nhãn gốc chưa đủ rõ, không yêu cầu duyệt từng bản dịch để chạy demo. 580 mục vẫn needs_review=true và được hiển thị có cảnh báo, không gắn nhãn chuyên gia đã duyệt. Ba tên meningitis/white blood cell disease/flu đã được chấp thuận hiển thị trước đó cũng không phải xác thực y khoa. Xem mục cuối DEPLOYMENT_GUIDE về restart/refresh và cách tắt draft mode. Model artifacts, data ZIP, class IDs/label mapping587 và raw scores không đổi.


## Cleanup và website ba model — 2026-11-11

Đã thực hiện cleanup trong code root, không thay Drive/data:61file cache `.pytest_cache`/`__pycache__`,1.784.992bytes. Trước xóa đã kiểm manifest ownership, snapshot byte/SHA, rồi xóa từng path được kiểm; không recursive-delete theo wildcard. Backup ngoài project tại sibling `maintenance-20261111-three-model/source-before/` và `removed-cache/`; receipts `before.json`, `cleanup-before-delete.json`, `cleanup.json` ghi exactpaths/size/SHA. Rollback: copy đúng file tương đối từ backup, kiểmSHA trước; không chép đè source mới nếu chưa so sánh.

README được gom thành một luồng startup; không còn ba đoạn env khác nhau hoặc đoạn mất dấu. Chuyển mô tả metrics sang ML_EXPERIMENTS, runtime contract sang DEPLOYMENT_GUIDE, giữ redirect/anchors tại MODEL_SELECTION_RATIONALE. Archive, source pins, manifests, scientific evidence, notebooks/outputs, environment và dist vẫn được giữ vì có consumer hoặc lịch sử. Không xóa duplicate chỉ dựa vào SHA khi chưa chứng minh không dùng.

Website có registry3IDs theo frozen candidates; trạng thái và [hợp đồng](DEPLOYMENT_GUIDE.md#three-model-website) là nguồn hiện hành. LR tunedC2 default ENABLED, hai comparator Windows vẫn BLOCKED vì thiếu independent references. Code tích hợp thật cho baseline/engine hardvote nhưng không bypassqualification để bật option. Original allowlist LR tuned không đổi.

HaiZIPngày05 không bị ghi đè. Kiểm thư mục sạch đã dùng ZIPcũ + overlay source hiện tại có inventory: đó là test runtime, không chứng nhận một ZIPrelease mới. DataZIP được giải nén như bytes; không parse lockedCSV. Original source/data bị chặn trong subprocess, chỉ reuse dependency environment. Default realLR200, fit/LLM/outbound/original-access/test-access đều0.

Trước release mới: freeze source/config hashes sau khi qualification có quyết định, rà required presentation evidence paths và cập nhật release inventory theo source mới. Code/data allowlists gốc và22supplement pins được giữ, không ép generator dựa trên freeze05 nhận source mới. Artifacts mới của academic review/maintenance chưa mặc nhiên nằm trong ZIP cũ. Cần duyệt rõ evidence nào chuyển vào data/report release; không ship cache, backup, .venv hoặc secrets. Không có ZIP mới trong vòng này.


## Git migration PC → GitHub → laptop — 2026-11-11

Không git init folder PC gốc. Clone remote hiện có vào sibling `disease-prediction-ml-git-sync`, giữ ancestor `e94987b…`, tạo branch `sync/pc-latest`. Source PC là ưu tiên cho nội dung đã kiểm; file chỉ có trên remote được giữ nếu chưa chứng minh obsolete. `handover_code_inventory.json` ở remote là inventory release lịch sử, không dùng làm hash manifest cho HEAD mới. Không force push, không tự merge vào main.

Git giữ Python/app/notebooks/tests/docs/config công khai, fixtures chatbot, schema/mapping tối thiểu và compact audit evidence đã duyệt. Schema/mapping hai bản byte-identical trong code là read-only fixtures cho Catalog/tests, không phải dataset sao chép. API vẫn kiểm metadata/checkpoint từ external storage. `.gitignore` chặn raw/processed, weights, .venv, secrets, staging/ZIP/cache và lớn row-level reports; kiểm cả tracked files cũ trước commit.

PC cleanup đã archive295file/240.553.200bytes ngoài repo tại sibling `git-migration-20261111/archived-from-pc/`. Chỉ bỏ các checkpoint/data trùng byte và generateddist đã chứng minh tái tạo; giữ54code-only evidence, metadata còn consumer và lockedCSVlocal ignored. Không mở payload test để băm/copy; không đổi canonical external data. Inventory/backup/checksum/consumer decisions ở `git-migration-20261111/`; rollback copy đúng relativepaths sau khi so file hiện tại, không ghi đè thay đổi mới.

Data release metadata: [external_data_release.json](../configs/external_data_release.json). `project-data.zip` local SHA3e30e25b… VERIFIED theo identity gói đã nghiệm thu; cloud download/access NOT VERIFIED. Owner cấp gói qua Drive riêng, không commit gói lên Git. Trên laptop kiểm:

```powershell
$Expected = (Get-Content '.\configs\external_data_release.json' -Raw | ConvertFrom-Json).package_sha256
$Actual = (Get-FileHash -LiteralPath '..\project-data.zip' -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) { throw 'Data ZIP checksum mismatch: stop, do not mix releases.' }
```

Giải nén gói thành sibling `disease-prediction-ml-data`, không lồng thêm một root. Đặt `DISEASE_API_STORAGE_ROOT` cho API; nếu chạy CLI phân tích có chủ đích, đặt thêm `DISEASE_STORAGE_ROOT` tới cùng root thay vì tái tạo bản data trong source. Không chạy các test opt-in đọc nguyên dataset/final split trong nhiệm vụ đồng bộ. Source commitSHA và package/checkpoint hashes được bind trong external `github-sync-receipt.json` sau commit/push; cấu hình committed không chứa self-referential commit hash.

Sau khi owner merge main: laptop sạch chạy `git fetch origin`, `git switch main`, `git pull --ff-only origin main`. Nếu upstream hoặc local commits diverge thì dừng xử lý branch riêng; không reset --hard/clean -fdx. PC tiếp tục làm ở checkout-git-sync để GitHub trở thành source Git chung. `.venv-web` và data được setup riêng ở từng máy. Tham khảo [README workflow](../README.md#pc--github--laptop).


Git byte integrity: .gitattributes disables automatic text conversion so frozen SHA values survive Windows/Linux clones. Do not run blanket line-ending conversion or git add --renormalize over protected artifacts. Two historical pinned fixture logs retain original whitespace. The eight missing local report assets were restored from exact members of the verified data package without overwriting any existing data; seven immutable-log link exceptions remain documented in docs/README. This does not claim Drive cloud download access was tested.


Existing-laptop checkout caveat: a real simulation of the old main with core.autocrlf=true followed by fast-forward preserved CRLF in an unchanged training.py, although Git status was clean. Therefore the README post-pull byte check is required on old Windows checkouts. verify_checkout_bytes is read-only by default; opt-in repair accepts only line-ending-equivalent tracked text, requires external byte backup and rejects real edits. It restores exact HEAD bytes, not new checksums. No reset/clean or history changes. A fresh clone also passed exact-byte verification.
