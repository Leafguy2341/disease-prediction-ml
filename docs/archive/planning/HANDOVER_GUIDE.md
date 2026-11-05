> ARCHIVE — Bản tại thời điểm trước hợp nhất tài liệu. Các trạng thái và lệnh cũ không phải hướng dẫn hiện hành. Xem [chỉ mục hiện hành](../../README.md) và [triển khai](../../DEPLOYMENT_GUIDE.md). Đường dẫn trong code block vẫn tính từ project root.

# Hướng dẫn nhận bàn giao disease-prediction-ml

## Cập nhật local web MVP

Xem [LOCAL_WEB_MVP.md](../integration/LOCAL_WEB_MVP.md) để mở **http://127.0.0.1:8000/** trên Windows.
Giữ cấu trúc hiện hành: backend `app/backend/`, HTML/CSS/JS `app/frontend/`, Phase5B trong `src/agent/`.
`POST /api/v1/chat` đã nối guard/extraction/validator → quality gate → `forward_ready` → approved LR tuned.
Không có public hosting, mock production, Gemini diagnosis hoặc xác suất lâm sàng.

1. Copy đúng7 deployment files từ canonical Drive về root local theo guide, không dataset/test split.
2. Dùng `.venv-web` Windows CPython3.13.17/AMD64 đã qualification, exact ML dependencies từ
   `requirements-api.txt`; hoặc original3.13.18 identity. Không đổi môi trường3.11 toàn cục.
   Xem [runtime approval](../integration/LR_WINDOWS_COMPATIBILITY.md); chỉ đúng audited LR tuned checkpoint được nhận ngoại lệ.
3. Chạy `python -B -m scripts.smoke_local_mvp --ml` bằng interpreter đó: cần PASS/REAL CHECKPOINT VERIFIED.
4. Nhập GEMINI_API_KEY qua environment của terminal server, bật DISEASE_GEMINI_LIVE=1 khi muốn live;
   chạy `--gemini-live` riêng (tối đa6 requests synthetic), kiểm schema375 và actual usage.
5. Chạy uvicorn localhost/one worker; mở URL trên. New chat chỉ reset phiên RAM, không reset provider budget.

**Đã kiểm:** Chat API/mock và Chromium thật desktop/mobile; real LR tuned trên Windows3.13.17,
full8×587 comparison với reference Colab/checksum PASS, actual TestClient/Uvicorn HTTP health200/predict200.
**Gemini live NOT VERIFIED**; không gọi generation trong runtime qualification/ML smoke.
Không lấy model/API hoặc mock UI PASS thành end-to-end live chat PASS.
Budget app20requests/process,6/phút,output2048/request,byte/token admission; không auto retry hoặc schema fallback.
Actual quota/Free Tier của tài khoản cần owner kiểm AI Studio. Giữ nguyên ML pins và375/587.

## Workflow hiện hành 2026-10-30

**Cập nhật closeout/API:** final test đã hoàn tất, được đối chiếu qua packet Colab SHA
`102845056236bfe3855962cd1717ece4402a958cc6ce593540ab1ccab4f34131`;
xem [báo cáo](../../../reports/final_model_evaluation_closeout.md). Notebook06 giữ executed outputs,
source lưu hành gate False/authorization trống và chỉ đọc completed bundle bằng `read_completed()`.
Không Run All bản06 cũ đang True, không xóa execution marker hoặc chạy lại test.
FastAPI mới tại `app/backend/` chỉ dùng approved LR tuned C=2; [setup Windows/API](../integration/LOCAL_PREDICTION_API.md).
Real API local checkpoint smoke vẫn NOT VERIFIED do thiếu weights local và môi trường khớp;
không dùng fixture HTTP PASS thay bằng chứng actual checkpoint.

Local code là authoritative source;Drive là authoritative data/models;Colab chỉ compute tạm.
Chỉ có hai ZIP bàn giao: **code giải nén local**, **data giải nén Drive**.
Runtime publication nhỏ dùng source/config/scripts từ code local,không đưa code ZIP hoặc full workspace lên Drive.
Trong phiên triển khai này code ZIP được tạo/verify thật;data ZIP/cloud sync/checkpoint reload trên Colab vẫn **NOT VERIFIED**.
SHA/kích thước của release code thực tế nằm trong `dist/handover/<release>/handover_manifest.json` và báo cáo bàn giao.

### 1. Giải nén đúng nơi

- Kiểm SHA-256 ZIP theo handover manifest/owner release. Code ZIP có một folder `disease-prediction-ml/`;
  giải nén vào parent local tùy chọn rồi VS Code Open Folder chính project đó.
- Data ZIP có entries phẳng `data/`,`artifacts/`,`reports/` và `handover_data_inventory.json`;
  extract **bên trong** `MyDrive/ML_Projects/disease-prediction-ml/`,không thêm folder lồng.
- Tool non-overwrite có thể dùng local Drive desktop path để extract;ví dụ:

```powershell
python -B scripts/package_handover.py extract --archive '<project-data.zip>' --output '<actual Drive desktop project path>' --expected-sha256 '<owner SHA-256>' --allow-locked-bytes
```

Tool kiểm ZIP hash/inventory/path traversal trước ghi;skip file đã khớp,dừng nếu file cũ khác bytes.
Không thay manifest variant5030… gắn checkpoint bằng localca20…;không xóa bản data đã giải nén.
`--allow-locked-bytes` chỉ cho phép opaque archive copy/hash;không parse CSV hoặc evaluate test.
Có thể chạy cùng script trên Colab với output là canonical mount path;khi chưa có source/session thì extract qua công cụ owner đã duyệt,
sau đó publish theo bước2. Không giả định Drive browser tự giải nén ZIP.

### 2. Thiết lập Drive desktop và publish source

Dùng Python3.11+ có sẵn;packing/staging/data tool chỉ dùng standard library,không tạo `.venv` hoặc tự cài gói.
Đăng nhập Google Drive for desktop đúng tài khoản,có quyền ghi vào project đã extractdata.
Lấy **đường dẫn thật trong File Explorer**;không giả định driveletterG:.
Windows local code phải ở folder riêng với Drive transport folder.

```powershell
.\scripts\prepare_colab_source.ps1 -Publish -DriveProjectPath '<actual Drive desktop project path>'
```

Nếu cần chọn interpreter,thêm `-PythonExe '<path to installed python.exe>'`.
Nếu PowerShell policy chặn script,có thể gọi cùng implementation trực tiếp:

```powershell
python -B scripts/package_handover.py publish --drive-project-path '<actual Drive desktop project path>'
```

Publisher kiểm suffix `ML_Projects/disease-prediction-ml`,approved Phase2manifest,path links và source pins trước ghi.
Chỉ publish45file:31src,8publicconfig,2requirements,4scripts (3audit+package_handover).
Không copy dataset/checkpoint/report từ Windows. Bản stage sinh tại `dist/drive-source/<digest>/`;
mọi revision/staging cũ được giữ,`-Refresh` không xóa folder nữa.
`-CheckOnly` kiểm revision hiện tại;không Publish network.

Output `LOCAL_DRIVE_COPY_VERIFIED; CLOUD_ACK_PENDING` **không** chứng minh Google cloud/Colab đã nhận file.
Chờ client báo sync xong,lưu dòng `RUNTIME_PAYLOAD_SHA256=...`.
Phiên này chưa có Drive desktop path/tài khoản được xác minh;không có publish thật lên Drive.

### Không có Drive for desktop

Owner hiện dùng cách này. Windows `D:` không xuất hiện trên Colab VM. Cần vận chuyển
**một folder payload nhỏ** bằng chức năng Upload to Colab của extension, rồi chủ động
gọi publisher hiện có một lần. Không upload code ZIP, toàn workspace hoặc từng `.py`.
Đây là bước chuẩn bị source riêng; smoke/06 không tự publish hoặc sửa source trên Drive.

1. Tại project local, kiểm staging hiện có:

   ```powershell
   python -B scripts/package_handover.py stage --check-only
   ```

   Nếu chưa stage đúng source hiện tại, chạy cùng lệnh bỏ `--check-only`.
   Giữ dòng `RUNTIME_PAYLOAD_SHA256=...` từ **Windows** và folder output tương ứng.
2. Chọn Colab server trong VS Code. Explorer → Upload to Colab **nguyên folder**
   `dist/drive-source/<digest>/`. Chờ upload xong; VM phải có
   `/content/<digest>/scripts/package_handover.py`. Folder này là tạm, chưa phải source Drive.
   Nếu folder đúng digest đã có trên VM, bỏ bước upload; bước `read_source` bên dưới vẫn phải PASS.
3. Chạy `Colab: Mount Google Drive to Server...`, chạy cell xác thực extension tạo.
   `/content/drive/MyDrive` và project canonical có metadata Phase 2 phải tồn tại.
   Không tạo root giả hoặc copy metadata local để vượt kiểm tra.
4. Chỉ khi cần publish, thực hiện thao tác **thủ công riêng** sau đây trên kernel Colab
   đã mount (không thêm vào smoke/06). Đây là gọi tool có sẵn, có ghi allowlisted source;
   không phải cell smoke hoặc bằng chứng runtime sạch:

   ```python
   import runpy
   from pathlib import Path

   expected = "<RUNTIME_PAYLOAD_SHA256 từ Windows>"
   seed = Path('/content') / expected
   drive = Path('/content/drive/MyDrive/ML_Projects/disease-prediction-ml')
   if not Path('/content/drive/MyDrive').is_dir():
       raise FileNotFoundError('Mount đúng Drive trước; không tạo thư mục Drive giả.')
   if not (seed / 'scripts/package_handover.py').is_file():
       raise FileNotFoundError(f'Chờ upload đủ folder payload: {seed}')
   source = runpy.run_path(str(seed / 'src/data/colab_runtime.py'))
   source['read_source'](seed, 3, expected_payload_sha256=expected)
   publisher = runpy.run_path(str(seed / 'scripts/package_handover.py'))
   publication = publisher['publish'](seed, drive)
   print(publication)
   ```

   Publisher kiểm approved manifest trước ghi; không thay data/model/metadata lịch sử.
   Giữ nguyên label `CLOUD_ACK_PENDING` của tool; same-VM copy không chứng minh VM khác đọc được.
5. Sau publish, tạo **Colab server/VM mới**, mount lại Drive, không upload seed nữa.
   Mở notebook local đã sửa, điền digest Windows vào `EXPECTED_RUNTIME_PAYLOAD`.
   Chạy `colab_smoke_test.ipynb` theo mục dưới. Chỉ bootstrap trên VM mới từ Drive thành công
   mới cung cấp bằng chứng persistence cho release này.

Source đã publish đúng thì reset runtime chỉ cần mount + setup, không upload lại payload.
Code runtime đổi thì stage/publish đúng revision; sửa riêng docs/notebook không nhất thiết đổi runtime digest.

### 3. VS Code + Colab và session sau reset

1. Mở notebook local,chọn `Select Kernel > Colab`,đăng nhập/chọn runtime.
2. Dùng extension command `Colab: Mount Google Drive to Server...` và chạy snippet được hỗ trợ.
   Kết nối kernel chưa có nghĩa Drive đã mount;browser Colab dùng cơ chế mount phù hợp của browser.
3. Chạy cell shared setup. Với smoke/06, điền **digest local stage/Publish** vào
   `EXPECTED_RUNTIME_PAYLOAD` trong cell setup; các notebook cũ hỏi digest khi chạy.
   Không lấy expected digest từ file Drive hoặc tái sử dụng biến cũ trong kernel.
   Kernel so publication hash của toàn source/config/scripts trước copy/import;stale/mixed/missing payload phải fail.
4. Bootstrap tạo `ROOT=/content/disease-prediction-ml-runtime`,cache riêng ở `/content/disease-prediction-ml-cache`;
   datasets/checkpoints/output vẫn dùng `/content/drive/MyDrive/ML_Projects/disease-prediction-ml`.
5. Với03–06,chạy cell `session = ColabTraining.open(RUNTIME)`. Session mở không train,không cần chạy cellbaseline/tuning.
   Smoke mới tự mở session;00–02 có workflow audit/EDA/preprocessing,không Run All chúng để sửa thiếu checkpoint.
6. Audit script gọi qua `runpy.run_path(str(ROOT / 'scripts/audit_post_tuning.py'))`;
   ML_GAPS có cảhai helper ở ROOT/scripts.03 đã sửa các appendices,không cần upload file riêng.
7. Sau VMreset:connect,mount,sharedsetup vàsession.open lại,dùng cùng digest nếu code chưa đổi.
   Biến session/api/audit_result không tồn tại qua reset;chạy lại cell phụ thuộc tương ứng,không Run All training.
8. Source thay đổi:Publish một lệnh,chờ cloud sync,Restart Kernel,paste digest mới. Không hot-reload pickle modules.

Notebook03/04 switches là lựa chọn người dùng,không bị reset trong packaging.
Notebook06 `RUN_FINAL_LOCKED_TEST=False`,authorization trống;vẫn cần owner ủy quyền riêng trước evaluation.
Source/environment/schema mismatch không phải lý do retrain hoặc sửa checksum theo file sai.

### Chạy smoke và notebook 06 an toàn

- **Smoke:** sau mount, điền digest rồi Run All. Chín cell chỉ bootstrap/import configs,
  nạp định nghĩa bốn script từ `ROOT/scripts/`, import Phase 5B và mở session mới.
  Integrity bảy file train/validation/metadata được kiểm mà không parse CSV; không reload model.
  Cuối notebook có bảng PASS/FAIL/SKIPPED và JSON `smoke_result`; checkpoint reload/Gemini live vẫn NOT VERIFIED.
- **06 (closeout hiện hành):** sau mount, điền digest rồi Run All với `RUN_FINAL_LOCKED_TEST=False`,
  `OWNER_AUTHORIZATION=""`. Notebook tự mở session, hiện protocol/identity bốn fitted members
  cho đúng ba candidates, rồi kiểm checksum/source/environment và đọc completed bundle đã audit.
  Bản closeout không còn gọi evaluate; bật gate bị chặn. Hash checkpoint lớn có thể mất thời gian.
  Không deserialize, predict hoặc mở/băm/stat test payload trong preflight. Số test rows/groups chỉ từ metadata.
  Nếu bundle hợp lệ thì hiển thị bảng/figure/report và SHA manifest completed gốc.
  Nếu chưa đọc được thì in NOT VERIFIED; không xem đó là lý do chạy lại test.
- Setup mới luôn xóa **biến phiên** cũ bằng gán `None`, không xóa file. Khi một bước FAIL,
  bước phụ thuộc SKIPPED; không giữ session/preflight cũ để chạy tiếp. Chạy lại từ setup sau khi sửa prerequisite.
- Final evaluation gốc đã hoàn tất trên Colab theo outputs/packet owner gửi. Môi trường checkpoint vẫn phải khớp
  chính xác version đã freeze; gặp mismatch thì dừng, không giả version, sửa pins hoặc retrain.
- Bản source closeout mới (gate off/read-only replay) chưa được chạy live bởi agent: **COLAB NOT VERIFIED cho bản sửa này**.
  Packet read-only của kết quả cũ đã verify riêng; không suy ra real API PASS từ packet hoặc fixture Windows.
  Giữ nguyên output notebook 03/04/05 và không Run All chúng.

### Bàn giao Prediction API local

- Source cần bàn giao: `app/__init__.py`, `app/backend/{__init__,main,prediction,schemas}.py`,
  `requirements-api.txt`, API tests và [LOCAL_PREDICTION_API.md](../integration/LOCAL_PREDICTION_API.md), cùng source/config gốc.
  Existing packager allowlist đã thêm requirements-api; **không tạo ZIP mới** trong bước này.
- Bảy deployment artifacts tải chỉ đọc từ Drive theo relative paths trong hướng dẫn API; không cần raw/train/validation/test CSV,
  saved test predictions hoặc weights RF/NB/SVC/KNN cho server LR. Drive vẫn là authoritative artifact storage.
- API terminal Windows dùng interpreter/version riêng khớp identity và `DISEASE_API_STORAGE_ROOT` là đường dẫn local thật;
  Colab mount không cấp đường dẫn đó cho Windows. Không tạo `.venv` hoặc tự download/install khi startup.
- `/health`200 với REAL CHECKPOINT VERIFIED và `/api/v1/predict`200 từ input synthetic mới đủ real API smoke.
  HTTP/synthetic tests đã PASS nhưng local weights reload/predict vẫn NOT VERIFIED.
  Startup fail trả503, không baseline fallback; không gửi Top3 khi input hoặc model output invalid.
- API không yêu cầu sửa bootstrap/publish. File packager allowlist có thay đổi local, do đó khi chủ động publish source ở lần sau
  phải stage lấy digest mới và verify đủ payload; không áp digest cũ cho revision mới. Chưa publish hoặc thay Drive trong nhiệm vụ này.
- `ConversationEngine.forward_ready` nay đã nối trong Chat API, giữ provisional gate/abstention.
  Web/mock tests PASS; real checkpoint/Gemini smokes còn chờ prerequisites như mục local MVP ở đầu tài liệu.

### 4. Tạo hai gói và kiểm tra

```powershell
python -B scripts/package_handover.py code
python -B scripts/package_handover.py data-plan --storage-root '<canonical mounted/desktop Drive project>' --output '<fresh data-packaging-plan.json>'
```

Code command tạo release directory mới,không ghi đè release cũ;ZIP có inventory và giữ nguyên byte notebook sau cập nhật setup,
bao gồm tất cả output03/04/05. Test extraction giữ tại `code-extraction-check/`,không cleanup.
Không chứaartifacts,reports,.venv,cache,.env,CSV dataset hoặc joblib. Hai source-owned exceptions làrawREADME và30synthetic devcases JSONL.

Owner có đủ canonical Drive artifacts có thể tạo data ZIP bằng source tool đã publish (không cần helper upload rời):

```powershell
python -B scripts/package_handover.py data --storage-root '<canonical Drive root>' --evidence-root '<existing folder containing audited evidence paths, if needed>' --output '<fresh release folder OUTSIDE canonical data root>' --allow-locked-bytes
```

Trên Colab dùng `sys.executable` và script `ROOT/scripts/package_handover.py`,cùng arguments.
Nếu output ở `/content/`,download ngay ZIP+`data_handover_manifest.json` vìVMephemeral.
Hoặc chọn một releasefolder mới trênMyDrive **ngoài** canonical project;không thay đổi canonicalpath.
Data tool kiểm approvedDrivevariant,Phase2files/raw,5baseline+5tuned,manifest-referenced reports/predictions và6evidence packets;
không deserialize/joblib,np.load,predict/fit hoặc parse test CSV.
Thiếu checkpoint/evidence hoặc khác bytes thì dừng **trước tạo archive**,không gọi gói thiếu là hoàn chỉnh.
Supplemental evidence chỉ được đọc để thêm vào ZIP nếu absent/cùnghash;không ghi đè bảnDrive.
Chỉ `data_handover_manifest.json` statusVERIFIED sau archivechecksum/inventory check mới xác nhậndata ZIP hoàn tất.
Code handover manifest giữ trạng thái data tại thời điểm đóng gói;data completion có manifest riêng,không sửa codeZIP cũ.

Offline smoke từ code ZIP đã giải nén (cần pytest và notebook dependencies có sẵn;không tự install):

```powershell
python -B -m pytest -q -p no:cacheprovider tests/test_distribution.py
```

Full legacy pytest/validators có integration dependencies vào Phase2/evidence/backups ởPROJECT/artifacts;
không coi toàn bộ suite là code-only. Đừng chạy nhánh data regression/test hoặc actual fit để onboarding.
Các relative artifact links trong tài liệu lịch sử là logical paths trên Drive,dataZIP không giải nén vào source folder để sửa links.

### 5. Chẩn đoán đúng loại lỗi

| Lỗi | Xử lý |
|---|---|
| Thiếu configs/runtime.json hoặc src/data/colab_runtime.py | Mount đúngDrive/account,Publish lại toàn smallpayload,chờsync;không uploadpy rời |
| STALE SOURCE RELEASE / SOURCE RELEASE MISMATCH | Dùng digest từlocal Publish,chờcloud nhận đủ,Restart Kernel;không bỏ check |
| NameError session/api/audit_result | Chạy setup/session.open và preceding audit cell;không train |
| Không có approved Phase2 manifest ở DriveProjectPath | Sai mapping hoặc data chưa extract;không tạo fakeRoot/overwritevariant |
| Thiếu checkpoint/bundle/evidence | Kiểm dataZIP inventory/quyềnDrive;chưa có modelartifact thì stop,không fit fallback |
| Source/version/schema mismatch | Giữ nguyên375/587/pinnedsource/versions;dùng release/môi trường đã duyệt |
| PowerShell không thấy python | Chọn PythonExe có sẵn;không tạo.venv hoặc cài package imlặng |

LR tunedC=2 đã được owner duyệt;hard tuned best observed validationMacroF1;chưa migrationdefault/API/Gemini live.
Rollback source bằng Publish lại known-good local code release rồiRestart Kernel;không xóa staging/data hoặc phục hồi đè manifest/model.

<details>
<summary>Guide trước khi có publisher — giữ làm lịch sử; không theo hướng dẫn upload script riêng</summary>

**Cập nhật hiện hành 2026-10-30:** owner đã duyệt **LR tuned C=2** cho chatbot/API nghiên cứu trước test.
Các trạng thái PENDING ngày2026-10-29 dưới đây giữ làm lịch sử; default trong code chưa đổi.
Thêm [notebook06](../../../notebooks/06_final_model_evaluation.ipynb) cho final evaluation riêng,
gate mặc định `RUN_FINAL_LOCKED_TEST=False`, `OWNER_AUTHORIZATION=""`; **chưa được phép đọc test** trong bước chuẩn bị.
Xem [hướng dẫn notebook06](#notebook06-final-evaluation-chưa-thực-thi) và
[protocol đã khóa](../ml/MODEL_SELECTION_RATIONALE.md#final-locked-test-protocol-2026-10-30).

Cập nhật **2026-10-29**. Dành cho thành viên mới nhận source và quyền đọc artifact.
**MODEL SELECTION PENDING:** hard tuned LR+SVC+KNN dẫn Macro F1 quan sát; LR tuned là preferred deployment candidate cho API nghiên cứu cần Top3;
LR baseline vẫn là default. Chưa có phê duyệt đổi default, Prediction API hoặc Gemini live.
Các lệnh dưới là hướng dẫn cho lần kiểm tra được phép sau này; **nhiệm vụ viết tài liệu này không chạy chúng**.

## 1. Đọc theo thứ tự và hiểu các Phase

1. [Decision record ML](../ml/MODEL_SELECTION_RATIONALE.md#decision-record-lựa-chọn-ml): đề xuất,20 kết quả baseline/tuned/ensemble và giới hạn.
2. [Kiến trúc](../integration/SYSTEM_ARCHITECTURE.md) và [thiết kế Phase5](../integration/phase5_llm_integration_design.md): ranh giới LLM/validator/ML/response.
3. [Colab/Drive](../runtime/phase3_colab.md): bootstrap hiện có; [inventory và kế hoạch bàn giao](WORKSPACE_HANDOVER_PLAN.md): filesystem,copy evidence và retention.
4. [Nhật ký](PROJECT_DEVELOPMENT_LOG.md): mục25–26 cho model analysis/ML_GAPS; mục27 cho lần chuẩn bị bàn giao này.
   Các câu “chưa train/chưa ensemble/chưa benchmark” ở entry cũ là trạng thái tại thời điểm đó.

| Phase | Đã có | Thứ tự đọc/thực thi khi được giao việc |
|---|---|---|
| 1 | Dataset audit/EDA,raw/report provenance | notebooks00/01 và reports/dataset_audit.md,eda_summary.md; đọc kết quả đã lưu |
| 2 | Schema375,mapping587,group split và dataset khóa | notebook02,reports/preprocessing_decision_review.md,artifacts/metadata/phase2; không rerun để sửa checksum |
| 3 |5 baseline,train-only CV tuning,5 selected checkpoints | notebook03,audit Phase3/Post-Tuning và rationale; không chạy model cells khi nhận bàn giao |
| 4 |3 hard+2 soft trước/sau tuning; validation/uncertainty/cost đã audit | notebook04,phase4_ensemble.md,ML_GAPS packet |
| Structured inference | Notebook05 kiểm5 baseline checkpoints/input375 | Đọc outputs/evidence; chạy notebook này sẽ predict mới |
| 5B | Guard/provider adapter/validator/mapper/conversation in-process,offline tests | src/agent và phase5_llm_integration_design.md; LIVE NOT VERIFIED |
| 5A | Chưa có Prediction API; PredictionService chỉ protocol/mock | Chưa FastAPI/frontend/chatbot end-to-end hoặc final locked-test evaluation |

Luồng đích giữ nguyên: LLM API → structured JSON → Python validator/mapper → fitted375-feature LR → Vietnamese response.
LLM không chọn disease label hoặc dựng model score. Default hiện tại là LR baseline; đề xuất LR tuned chưa được áp dụng.

## 2. Ba vị trí cần phân biệt

| Vị trí | Vai trò | Cần nhận |
|---|---|---|
| Local source folder hoặc repository/gói source do owner cung cấp | Nơi đọc/sửa code,notebooks,docs,tests vàscripts | Toàn bộ source handover bên dưới; workspace hiện chưa có Git repository theo nhật ký |
| Local dist/drive-source/ | **Staging tái tạo cho runtime**,38 file hiện có:29 src/*.py,7 config,2requirements | Không phải source handover đầy đủ; thiếu notebooks/docs/scripts/tests/README/evidence |
| Canonical Drive root | Persistent source runtime,datasets,checkpoints,metadata,reports | Quyền đọc của đúng tài khoản và đúng root; quyền ghi chỉ khi sau này được giao chạy tác vụ ghi |

Canonical root: **/content/drive/MyDrive/ML_Projects/disease-prediction-ml**.
Config authority: [configs/runtime.json](../../../configs/runtime.json); locator DRIVE_ROOT trong notebook phải khớp.
Source import tạm: /content/disease-prediction-ml-runtime; cache tạm: /content/disease-prediction-ml-cache.
Ổ /content mất khi VM reset; output quan trọng ở Drive.

Snapshot Drive qua ML_GAPS có167 file và **không có top-level notebooks/,docs/,scripts/,tests/**.
Folder Drive hiện tại không tự thay thế full source handover. Đây là snapshot người dùng chạy,không live filesystem của agent.
Không upload toàn bộ workspace; không đồng bộ .venv/cache/backups/archives hoặc chép local Phase2 manifest lên Drive.

## 3. Cây source bàn giao và artifact cần giữ

```text
disease-prediction-ml/
├── README.md, pyproject.toml, requirements*.txt, setup.ps1, .gitignore
├── src/{data,models,agent,evaluation,features}/
├── configs/                         baseline/runtime/Phase5B và các ví dụ public
├── notebooks/                       00–05, colab_smoke_test.ipynb, README
├── scripts/                         audit,builders,validators và staging script
├── tests/                           source tests,không pycache
├── docs/                            guide,rationale,architecture,design,log,inventory
├── data/
│   ├── evaluation/vietnamese_symptom_cases.jsonl
│   └── raw/README.md                provenance; CSV qua quyền artifact riêng
├── artifacts/metadata/phase2/       approved manifests/schema/mapping/policy/assignments
├── artifacts/metadata/{phase3_audit,phase4_audit,post_tuning_audit,
│                      structured_inference,model_analysis,final_ml_gaps}/
└── reports/                         reports/figures/tables hiện có; runs theo quyền artifact
```

**Quản lý trong repository hoặc source handover sau này:** root public files,src,public configs,notebooks có outputs,
scripts,tests,docs,synthetic evaluation JSONL,approved Phase2 metadata,sáu evidence packets và reports/figures/tables được bảo toàn.
Giữ thêm data/raw/README.md và configs/dataset_source.json cho source attribution/provenance.
Đây là danh sách cần có,không phải tuyên bố đã Git-track/commit.
[.gitignore](../../../.gitignore) loại raw/processed payloads,models/joblib,metadata/phase3,runs,backups,dist,env/cache vàsecret config;
vì vậy dữ liệu/weights/ignored history phải có quyền truy cập artifact riêng. Không đổi .gitignore hoặc tạo gói mới trong lần này.

Tất cả path dưới đây tính từ canonical Drive root; local hiện có dataset/metadata và evidence,
nhưng **artifacts/models/ chỉ có .gitkeep**:

| Artifact | Path/điều cần nhận |
|---|---|
| Raw CSV | data/raw/Disease and symptoms dataset.csv,giữ nguyên tên và contents; raw Drive copy SHA còn NOT VERIFIED |
| Processed | data/processed/{train,validation,test}.csv.gz; test khóa,không mở/copy/hash trong onboarding |
| Schema/mapping | artifacts/metadata/phase2/{feature_schema,label_mapping}.json; input375 theo features,labels587 đúng IDs/order |
| Phase2 policy/identity | cùng folder: dataset_manifest.json,preprocessing_policy.json,split_metadata.json,split_assignments.csv.gz |
| Baseline5 | artifacts/models/phase3/baseline-v1-f8a5bfdb7b4c12cd/<model>/ |
| Tuned5 | artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/<model>/ |
| Mỗi checkpoint | pipeline.joblib,fit.json,metadata.json,validation_predictions.npz; giữ cả4,không chỉ filemodel |
| Tuning run | artifacts/metadata/tuning/tuning-v1-9c4dd013abbba14a/{manifest.json,experiment.json,trials.json,selection.json,cv_assignments.npz} |
| Baseline ensemble | artifacts/models/phase4/phase4-20261028T091711786379Z-c1c66643/definitions.json và artifacts/metadata/runs/<cùng-run>/phase4_manifest.json |
| Tuned ensemble | artifacts/metadata/runs/tuned-ensemble-20261029T041701354242Z-6c84dbfe/{tuned_ensemble_manifest.json,tuned_results.json,tuned_ensemble_predictions.npz} |
| Reports theo run | reports/runs/<run-id>/ và reports/tuning/<tuning-experiment>/; giữ linked tables/figures,không thay bằng notebook screenshot |

Baseline/tuned checkpoints,tuning manifest/selection/assignments,các run Phase3/4 mới chỉ ở Drive theo evidence.
Tuned26 files/ensemble4 files được ML_GAPS kiểm checksum; baseline5 có audit lịch sử.
Drive raw/report/backup byte copies và quyền truy cập của thành viên mới chưa được xác minh.
Người nhận cần owner cấp quyền và cung cấp đúng canonical root; URL chia sẻ không thay filesystem path.
Thiếu artifact phải hỏi owner về bộ đã có,không retrain/tuning để “tạo bù”.

Sáu packet local: [Phase3](../../../artifacts/metadata/phase3_audit/colab_evidence.json),
[Phase4](../../../artifacts/metadata/phase4_audit/colab_validation_evidence.json),
[structured inference](../../../artifacts/metadata/structured_inference/colab_evidence.json),
[Post-Tuning](../../../artifacts/metadata/post_tuning_audit/colab_evidence.json),
[model analysis](../../../artifacts/metadata/model_analysis/colab_supplement.json),
[ML_GAPS](../../../artifacts/metadata/final_ml_gaps/colab_evidence.json).
Chúng là bằng chứng audit,không phải backup weights; giữ nguyên bytes và provenance.

## 4. Setup Colab/VS Code và điểm dừng

1. Nhận full source và quyền Drive; kiểm có src/data/colab_runtime.py cùng public configs/requirements ở root Drive.
   Thay đổi docs không cần Refresh staging. Khi chỉ kiểm staging hiện có,có thể dùng -CheckOnly theo script chuẩn; không -Refresh.
2. Chọn kernel Colab chính thức trong VS Code. Kết nối kernel không tự mount Drive;
   mount bằng giao diện/cell được extension hỗ trợ. Colab browser dùng cách mount của browser;
   không giả định mọi remote Jupyter hỗ trợ google.colab.drive.mount hoặc cài google.colab vào local để giả lập.
   File mở trong VS Code local không tự có trên kernel; đường dẫn Windows local không tồn tại trực tiếp trên kernel Linux.
3. Đối chiếu exact trained versions trước reload. Audit đã ghi Python3.13.18,sklearn1.6.1,NumPy2.1.3,SciPy1.16.3,joblib1.6.0;
   metadata fit.json→identity.versions của checkpoint mới là authority.
   requirements-notebooks/training có ranges để import,**không bảo đảm exact checkpoint compatibility**.
   requirements.txt là Phase1/Python3.11; requirements-dev.txt kéo file đó vào.
   **Không cài đè requirements.txt/dev vào Colab checkpoint kernel**,không tự nâng package hoặc sửa identity để qua kiểm.
   setup.ps1 cũng là setup Windows Phase1 vàcó tạo .venv; không dùng nó cho Colab onboarding hoặc docs checks.
4. Khi source đã đồng bộ đúng revision,Restart Kernel để bỏ imports cũ.
   Chạy riêng colab_smoke_test.ipynb nếu được giao kiểm hạ tầng: A runtime/mount,B source/import,C manifest/train-validation/schema.
   Smoke hiện có dùng probes vàcache tạm; không preprocessing lại,fit hoặc mở test.
5. Mở03/04 để đọc saved outputs; sử dụng điểm dừng bên dưới. Không Run All03/04/05 khi chỉ nhận bàn giao.
   Setup/import/checksum PASS chưa là checkpoint reload hoặc Gemini live PASS.

| Notebook | Có thể dùng cho preflight khi được phép | Dừng trước |
|---|---|---|
| 03,17 cells hiện tại | Cell2 setup,3 ColabTraining.open,5 load_data; xác định theo tên nếu cell numbering thay đổi | Phần3/cell8–12 gọi train_model với fit callback; cell14 show_results có thể ghi reports; cell16–17 tuning |
| 04,20 cells hiện tại | Cell2 setup,3 phase.verify đọc saved predictions/checksums; dùng cache existing | Phần probability/cell9,cell15 single_input vàcell17 save_phase4; tuned section19–20. Chúng có thể predict/ghi run mới dù không fit |
| 05 | Đọc kết quả structured inference đã lưu | Chạy code sẽ load/predict mới; không cần cho documentation handover |

**Hai switches:** RUN_HYPERPARAMETER_TUNING ở03 và RUN_TUNED_ENSEMBLE ở04 đã được người dùng bật có chủ đích.
Không giả định giá trị trong file là False,chưa sửa switches/output trong bàn giao.
False chỉ tắt section bổ sung tương ứng,**không tắt baseline fit cells03**.
True ở03 cho phép CV/refit selected; True ở04 dùng prefitted members nhưng có thể predict_proba/ghi experiment mới.
Không chạy hai section này để sửa lỗi thiếu source/checkpoint hoặc để “chỉ xem kết quả”.
Checkpoint reuse không là training-disable:03 có thể fit khi không có checkpoint phù hợp.
Sau này chỉ chạy lại khi có nhiệm vụ ML riêng,đã kiểm flags/run IDs và retention.

## 5. Tests và integrity, tách khỏi training

Các lệnh tham khảo sau chạy từ **project root**,với Python/dependencies đã chuẩn bị.
Không tạo .venv hoặc tự cài package. Nếu thiếu pytest/jsonschema/ML dependency,dừng để owner chuẩn bị môi trường phù hợp,
không cài requirements-dev vào kernel cần reload checkpoint.

```powershell
python -B -m pytest -q -p no:cacheprovider tests/test_phase5b.py tests/test_tuning.py tests/test_post_tuning_audit.py
python -B tests/test_final_ml_gaps.py
```

Đây là tests offline/mock hoặc orchestration,không actual sklearn fit/Gemini live; fixtures có thể dùng temporary files.
Không dùng mock metrics làm kết quả dự án. Không chạy pytest toàn bộ hoặc bật DISEASE_RUN_DATA_REGRESSION:
test_phase3_training.py có real synthetic fits;data regression có nhánh đọc locked split.
Lần documentation này chỉ kiểm cấu trúc/link,không chạy lại các testcommands.

Sau setup đã có RUNTIME/runtime_paths,chỉ đọc train/validation/metadata và complete tuning bundle bằng helpers hiện có:

```python
from src.data.colab_runtime import phase2_preflight
from src.models.tuning import read_tuning_result

inputs = phase2_preflight(RUNTIME)
selected = read_tuning_result(runtime_paths.storage_root, 'tuning-v1-9c4dd013abbba14a')
print(inputs['manifest_sha256'], selected['status'], selected['identity']['versions'])
```

Snippet không fit/predict/deserialize weights. Source [integrity.py](../../../src/data/integrity.py) kiểm7 inputs,
[tuning.py](../../../src/models/tuning.py) kiểm26 files vàselection linkage.
Muốn kiểm baseline saved predictions/hard-vote dùng existing phase.verify/audit_post_tuning,
không tự viết loader hoặc joblib.load bỏ checks.
Không chạy lại audit_final_ml_gaps(benchmark=True) để đọc kết quả: [packet và protocol đã có](WORKSPACE_HANDOVER_PLAN.md#2-protocol-chốt-trước-khi-tính).

## 6. Phase5B và việc chưa được phép coi là hoàn tất

[Ba module](../integration/phase5_llm_integration_design.md#8-phase5b-đã-triển-khai--cách-chạy-và-ranh-giới):
conversation.py giữ Input Guard/session/state/TTL/subject/corrections;
extraction.py kiểm JSON/evidence spans/exact375 allowlist vàmapper;
provider.py là adapter external Gemini Interactions API với error/retry/usage handling.

[phase5b.json](../../../configs/phase5b.json) có provider.live_enabled=false;
min_present_features=2 là policy **provisional_pending_human_review**,configurable,không ngưỡng y khoa.
Có2 feature vẫn bị chặn nếu urgent/invalid/conflict/uncertain hoặc session/turn cũ.
extraction_ready là frame sẵn cho port,**chưa là disease/Top3 đã dự đoán**.
Provider failure/invalid JSON/expired hoặc stale state không được đưa vector cũ vào inference.

Tests dùng mocks;30 ca JSONL synthetic vẫn pending_human_review.
Chưa kiểm Gemini thật: model/account/quota/full375 schema,semantic extraction tiếng Việt,cost/latency live,
calibration hoặc Phase5B Colab end-to-end. Tên model trong config không chứng minh account hiện tại truy cập được.
Chưa có Phase5A loader-backed Prediction API,authentication/ownership/frontend hoặc kết nối fittedLR vào port thật.
Không bật live flag hoặc đưa API key/token/private Drive URL vào source/notebook/config/log khi nhận bàn giao.

## 7. Không đổi file để chữa lỗi integrity

Giữ raw/processed/splits,Phase2 schema/mapping/order/policy/assignments/manifest,
baseline config,all checkpoint fit/metadata/predictions vàsource/module path đã pin.
Inference nhận375 feature,để fittedVarianceThreshold xử lý318 cột còn lại trong pipeline; không tự giảm vector.
Không sửa sourceSHA/version/checksum hoặc dùng LLM/fuzzy mapping sửa nhãn.
Không thêm lại regurgitation/regurgitation.1 đã được loại khỏi schema duyệt.

Local Phase2 manifestca20a551… vàvariant50308d25… gắn Drive identity lịch sử đều đã được duyệt:
[phase2_integrity.json](../../../configs/phase2_integrity.json). Chúng không là cùng bytes.
Không chép manifest local đè Drive để “đồng bộ”; packet ML_GAPS mới không xuất riêng exact current manifest variant.
Giữ cấu trúc hiện hành; .venv/cache/backups/reports/archives vàroot source_manifest.json không được dọn trong bàn giao này.
[Retention/copy checks/allowlist cần duyệt](WORKSPACE_HANDOVER_PLAN.md#8-rủi-ro-và-các-hành-động-cần-phê-duyệt-riêng).

| Triệu chứng lỗi | Kiểm trước | Không làm để vượt lỗi |
|---|---|---|
| Không thấy /content hoặc sai runtime | Kernel Colab/Linux,không local interpreter | Tạo .venv hoặc giả cài google.colab |
| Không thấy Drive/root/bootstrap | Mount đúng frontend,tài khoản/quyền,canonical folder,file src/data/colab_runtime.py | Đưa URL Drive vào Path hoặc đổi canonical root tùy ý |
| ModuleNotFoundError: src.models.tuning | Full src revision đúng,source trên Drive,imports từ workspace sau Restart | pip install src hoặc chạy lại training |
| Thiếu pipeline/metadata/manifest | Cấp quyền vànhận đủ namespace4files/checkpoint,explicit experiment ID | Bật tuning/retrain tạo bù hoặc copy model sang namespace khác |
| SHA/schema/mapping mismatch | File expected/actual vàapproved baseline,record đúng bundle | Sửa checksum,mapping,feature order hoặc rerun Phase2 |
| Version/source identity mismatch | fit.json.identity.versions và8MLsource pins của tuned run | Sửa identity hoặc nânghạ packages mù |
| Source cũ trong kernel | Source revision đúng,Restart Kernel;không reload module riêng lẻ | Sửa source trong ephemeral workspace |
| provider_error/live_disabled | Bình thường khi live tắt;đọc Phase5B offline status | Bật API chỉ để chứng minh ML/metadata chạy |

## 8. Trước final evaluation/API

Nhóm duyệt record/model vàTop3/score/abstention contract;chốt production acceptance criteria,
human-reviewed gate/extraction evaluation vàkế hoạch final-test độc lập sau validation đã dùng nhiều lần.
Phase1 từng EDA toàn CSV, nên không tuyên bố locked test chưa từng được xem; ghi rõ giới hạn hoặc dùng dữ liệu độc lập cho đánh giá mù.
Owner xác nhận quyềnDrive/full artifact access vàcung cấp các folders thiếu trong handover.
Sau đó mới có nhiệm vụ riêng cho compatible deployment/default migration,Phase5A hoặc Gemini live smoke có budget.
Giữ MODEL SELECTION PENDING đến khi có phê duyệt rõ;không phát sinh quyền cleanup/API từ tài liệu này.

## Notebook06 final evaluation chưa thực thi

Phụ lục **2026-10-30** cập nhật quyết định hiện hành, không xóa snapshot PENDING ở trên:
owner đã duyệt LR tuned C=2 cho deployment nghiên cứu trước test. Default code/checkpoint vẫn giữ nguyên;
thực thi evaluation, migration default và API là các quyền riêng biệt.

- Mở [06_final_model_evaluation.ipynb](../../../notebooks/06_final_model_evaluation.ipynb), đọc protocol đầu notebook.
  Không Run All 03/04/05 để setup hoặc tạo lại checkpoint. Hai tuning switches người dùng đã bật ở03/04 được giữ nguyên.
- Source handover bổ sung [final_evaluation.py](../../../src/models/final_evaluation.py),
  [final_evaluation_protocol.py](../../../src/models/final_evaluation_protocol.py),notebook06 và
  [test_final_evaluation.py](../../../tests/test_final_evaluation.py).
  Trên Drive chỉ cần hai module mới tại `src/models/` cùng source/config/artifact cũ đã đồng bộ.
  Dùng **cơ chế đồng bộ hiện có**; không có bootstrap/archive mới. Bước chuẩn bị không chạy staging `-Refresh`.
  `dist/drive-source/` hiện chưa được rebuild cho hai file mới; không coi staging cũ là bản source mới đủ.
- Chọn kernel Colab,mount canonical Drive,Restart Kernel sau đồng bộ, chạy riêng setup/ColabTraining.open và preflight notebook06.
  Không `session.load_data()` hoặc gọi training. Cần read permission cho bundles và write permission namespace final mới.
  Môi trường phải đúng `fit.json.identity.versions`; không tự cài/upgrade package để bỏ qua mismatch.
- Giữ `RUN_FINAL_LOCKED_TEST=False` và `OWNER_AUTHORIZATION=""` trong nhiệm vụ chuẩn bị.
  Run All với defaults không predict/read test; shared bootstrap vẫn có probes/source cache tạm như trước.
  Preflight chỉ đọc/checksum train-validation/metadata/checkpoint; counts/hash test lấy từ manifest.
- Chỉ khi owner **ủy quyền riêng** cho `final-locked-test-v1`,SHA
  `049ee0aa3c2907985c3d3a03ed222b1d6e1efb5921bbbc2d04ec0dea9baa8947`,
  mới bật gate và điền `OWNER_AUTHORIZATION` thành
  `AUTHORIZE ONE-TIME LOCKED TEST final-locked-test-v1 049ee0aa3c2907985c3d3a03ed222b1d6e1efb5921bbbc2d04ec0dea9baa8947`.
  Đây là confirmation của chủ dự án, không phải API key. Đừng tự điền khi chưa được cho phép.
- Chỉ ba ứng viên: LR baseline,LR tuned C=2,hard tuned LR+SVC+KNN theo run đã định;
  bốn pipeline có fitted preprocessing được reload và kiểm trước khi nạp test. Không fit/calibration/chọn model từ test.
- Output mới: `artifacts/metadata/final_evaluation/049ee0aa3c290798/` trên canonical Drive.
  `execution.json` chống rerun; `manifest.json` cuối cùng mới xác nhận completed.
  Nếu partial/disconnect, **không xóa marker,không Run All để thử lại**; gửi lỗi/status cho owner rà soát.
  Muốn xem lại kết quả complete chỉ dùng `read_completed(folder)`/bảng đã lưu, không mở lại CSV test.

Safe offline preparation tests dùng synthetic temp fixtures/mock pipelines, không model/data thật:

```powershell
python -B -m pytest -q -p no:cacheprovider tests/test_final_evaluation.py tests/test_tuning.py tests/test_post_tuning_audit.py
```

Chưa có điểm test hoặc reload/preflight notebook06 thật trên Colab. Fresh Drive availability/versions/checksums còn chờ preflight;
selected identity tái dựng phải khớp artifact thật, nếu không khớp thì dừng, không sửa protocol theo điểm test.
Xem [protocol và danh mục12 outputs](../ml/MODEL_SELECTION_RATIONALE.md#final-locked-test-protocol-2026-10-30).

</details>
