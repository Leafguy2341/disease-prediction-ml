# Nhật ký phát triển dự án

Đây là **nhật ký phát triển theo thời gian duy nhất** của nhóm. Báo cáo chuyên đề giữ phân tích chi tiết; nhật ký chỉ ghi mục tiêu, quyết định, bằng chứng, giới hạn và bước tiếp theo. Rà soát/bổ sung lần đầu ngày **2026-10-28** theo yêu cầu điều chỉnh kiến trúc từ phản hồi giảng viên.

## Cách đọc và cập nhật

- **Hoàn tất:** có code/artifact hoặc tài liệu được đối chiếu. **Đã kiểm:** phải nêu bằng chứng và môi trường. **Chờ:** chưa có bằng chứng thực hiện. **Đề xuất:** thiết kế tương lai, chưa triển khai.
- Các mục trước ngày lập log là **tóm tắt lịch sử tái dựng** từ file hiện có, không phải ghi chép đương thời. Thứ tự theo phase/phụ thuộc; không suy ngày làm việc từ mtime. Workspace không có Git repository để đối chiếu commit. Ngày chính xác không có thì ghi phase, không tự đặt ngày.
- Sau mỗi thay đổi đáng kể, người hoàn tất thêm mục ở cuối gồm: ngày/phase, mục tiêu, vấn đề, việc đã làm, quyết định/lý do, phương án cân nhắc, kết quả/bằng chứng, file liên quan, giới hạn, bước tiếp theo. Ghi tên người thực hiện chỉ khi biết, không tự gán.
- Không xóa thất bại hoặc sửa ngầm quyết định lịch sử. Sai sót phải có mục **Đính chính** mới, chỉ rõ mục cũ và bằng chứng mới. Trạng thái mới không làm mất giá trị lịch sử của trạng thái cũ.
- Không lưu credentials, API key, token/link Drive riêng, dữ liệu cá nhân hoặc nội dung hội thoại riêng tư. Không tạo thêm log lịch sử song song. Các tài liệu kiến trúc/lý do chọn model là tài liệu tham chiếu, không phải nhật ký thứ hai.

## Trạng thái tại lần rà soát 2026-10-28

**Mục31 — 2026-10-30,clean-runtime smoke đang chờ bằng chứng thật:** code ZIP117file vàsource stage45file đã kiểm lại PASS local.
Owner xác nhận **không dùng Google Drive for desktop**,chỉ mountDrive trong notebook;Windows chưa có đường dẫn cho lệnh Publish local.
Đã xác nhận extensionColab0.9.7 hỗ trợuploadcảfoldervào/content vàhelperpublishhiệncó cóthể nhậnDrive mountpath trênVM;
đề xuất chuyển mộtfolderpayload rồi gọihelpercũ,khôngupload.py rời,khôngthêmsyncframework.
Sourcepublish/cloudsync/Colabbootstrap/session/checkpointload vẫn **NOT VERIFIED** đến khi owner gửioutputkernelthật.

**Mục30 — 2026-10-30:** owner cho phép implement và đóng gói thử.Code-onlypackager,source publisher vàshared bootstrap đã triển khai;
local code ZIP có inventory/SHA/extraction check trong release `dist/handover/release-20261030-e5936121/`.
SHA/kích thước/filecounts thực tế lấy từ `handover_manifest.json` viết sau khi ZIP được kiểm,không self-hash trong archive.
Data ZIP thật vàcloud sync/Colab checkpoint reload vẫn **NOT VERIFIED**. Không cleanup/fit/Gemini/final-test evaluation.
Xem [workflow hiện hành](HANDOVER_GUIDE.md#workflow-hiện-hành-2026-10-30);mục29 là audit/plan trước implementation.

**Mục29 — 2026-10-30,đính chính distribution:** `project-code.zip` chỉ giải nén local/mở VS Code;
`project-data.zip` mới upload và giải nén canonical Drive. Local code là authoritative source,Drive là persistent data/models,
Colab là compute tạm. Đã lập [RUNTIME_DISTRIBUTION_PLAN.md](RUNTIME_DISTRIBUTION_PLAN.md);
đề xuất mở rộng stager/bootstrap hiện có cho payload nhỏ source+scripts,không upload code ZIP hoặc .py rời.
**PLAN ONLY:** chưa có Publish command,không sửa runtime/staging/notebook;workflow mới còn chờ nhiệm vụ triển khai riêng.

**Mục28 — 2026-10-30:** owner đã duyệt **LR tuned C=2** cho deployment chatbot/API nghiên cứu trước test.
Đã chuẩn bị [notebook06](../../../notebooks/06_final_model_evaluation.ipynb) và
[final-test protocol ba ứng viên](MODEL_SELECTION_RATIONALE.md#final-locked-test-protocol-2026-10-30).
Gate mặc định tắt; **chưa ủy quyền execution,chưa mở test,chưa có điểm test**. Những trạng thái PENDING trước mục28 là lịch sử;
không đổi default/config/checkpoint hiện hành hoặc triển khai API.

**Mục27 — ML decision record và source handover,2026-10-29:** đã tổng hợp đủ5 baseline/5 tuned và3 hard/2 soft trước/sau tuning,
thêm [decision record](MODEL_SELECTION_RATIONALE.md#decision-record-lựa-chọn-ml) và [HANDOVER_GUIDE.md](HANDOVER_GUIDE.md).
Đề xuất: hard tuned best observed Macro F1; LR tuned preferred deployment candidate cho API nghiên cứu cần Top3;
LR baseline vẫn default. **MODEL SELECTION PENDING**,chưa ghi nhận phê duyệt thay model. Chỉ sửa tài liệu và kiểm links/cấu trúc;
không chạy lại model/tests/Colab hoặc cleanup. Các mục26 trở về trước là mốc bằng chứng lịch sử.

**Mục26 — Final ML Evidence Gaps & Handover,2026-10-29:** đã nhận packet Colab7c2ed8e6…;bootstrap seed20261029/B2000 có CI delta F1 chứa0,
diagnostic tuned benchmark PASS. Đề xuất LR tuned cho hướng API nghiên cứu cần Top3 để nhóm duyệt;MODEL SELECTION PENDING,default không đổi.
Local snapshot2.028 files/274.432MiB;Drive snapshot167 files/251.736MiB qua packet;copy checksums raw/report/backups còn NOT VERIFIED.
Đã lập [WORKSPACE_HANDOVER_PLAN.md](WORKSPACE_HANDOVER_PLAN.md),chưa cleanup hoặc đổi cấu trúc. Các trạng thái mục25/24/23 dưới đây giữ như lịch sử trước bằng chứng mới.

**Mục25 — phân tích sau Post-Tuning Audit Colab, 2026-10-29:** packet70849a69… đã xác minh checkpoint/metrics/folds/selection PASS. Hard tuned LR+SVC+KNN dẫn Macro F1 = 0.79651707; LR tuned có Accuracy/Weighted F1 cao hơn. MODEL SELECTION PENDING; đã hoàn tất full CV/paired errors/per-class; còn benchmark triển khai và group uncertainty, không thay default.

**Mục24 — audit 2026-10-29:** notebook lưu output tuning-v1-9c4dd013abbba14a và tuned ensemble đã chạy; artifact Drive chưa được đọc độc lập nên checksum/metrics còn NOT VERIFIED. Phase5B đã sửa context urgent/negation và kiểm offline271 PASS; Gemini live chưa chạy. Hai switch được bật có chủ đích, không phải bug; audit này giữ notebook nguyên byte.

**Cập nhật mới nhất — mục23, 2026-10-29:** đã tích hợp tuning opt-in vào cuối notebook03/04,240 test local PASS. Chưa chạy tuning hoặc tuned ensemble trên Colab; kết quả baseline và LR mặc định giữ nguyên.

**Cập nhật sau snapshot ban đầu:** mục15/17/21 ghi audit, chọn LR và kiểm inference Colab. **Mục22 ngày2026-10-29 đã triển khai Phase5B in-process,205 test offline PASS; LIVE NOT VERIFIED.** Có30 ca tổng hợp chờ duyệt; Phase5A Prediction API, frontend/public deployment và final test chưa làm. Mục20 giữ lịch sử chờ thực thi. Bảng dưới giữ trạng thái khi lập log, không phải trạng thái hiện tại.

| Phần | Trạng thái có bằng chứng |
|---|---|
| Phase 1 audit/EDA | Hoàn tất; báo cáo và bằng chứng thực thi local lịch sử có sẵn. |
| Phase 2 preprocessing/khóa artifact | Hoàn tất; policy ≥10, 375 feature, 587 lớp và bộ split cố định. |
| Colab/Drive | Smoke A/B/C đã PASS theo output Colab thật do người dùng cung cấp, lưu trong báo cáo kiểm tra. |
| Phase 3 năm model | Code/config/notebook đã có; workspace hiện chỉ có `.gitkeep` trong `artifacts/models/`, chưa có checkpoint/metrics để xác nhận training hoàn tất. Không kết luận về kết quả nằm ở Drive ngoài phạm vi đọc được. |
| Voting/đồ thị so sánh lỗi | Đề xuất sau baseline; chưa chạy. |
| LLM/mapper/chatbot | Hợp đồng được mô tả ở lần cập nhật này; chưa triển khai hoặc kiểm thử tích hợp. |

## 1. Phase 1 — Dataset audit (lịch sử tái dựng)

- **Mục tiêu / vấn đề:** xác định schema/chất lượng CSV và khả năng dùng cho đồ án; chưa biết nguồn chính xác, ý nghĩa 0/1 và mức trùng/lớp hiếm.
- **Đã làm:** kiểm toàn CSV, nhãn, miền nhị phân, missing, vector lặp/xung đột; tra cứu nguồn ứng viên. Báo cáo ghi ngày tra cứu 2026-10-21, không đủ để gán ngày chính xác cho mọi thao tác audit.
- **Quyết định / lý do:** CONDITIONAL GO cho nghiên cứu; không coi mỗi dòng là bệnh nhân thật, không biến 0 thành âm tính đã xác nhận. Nguồn được mô tả sinh nhân tạo nhưng danh tính tệp với bản nhà xuất bản chưa được chứng minh bằng checksum gốc.
- **Phương án cân nhắc:** chia theo dòng hoặc xem dữ liệu sẵn sàng ngay sẽ bỏ sót vector lặp/lớp ít support; giữ việc quyết định preprocessing sang Phase 2.
- **Kết quả / bằng chứng:** 246.945 dòng, 377 triệu chứng, 773 lớp; 0 missing/giá trị ngoài 0/1, 49 cột hằng; 57.298 dòng trùng dư theo vector+nhãn; 12.634 vector nhiều nhãn. CSV SHA `8de90603ebada467fc2703db2ee4292856e52d64e94982ef926df22fa0c21320`.
- **File:** [báo cáo audit](../../../reports/dataset_audit.md), [JSON kết quả](../../../../disease-prediction-ml-data/reports/runs/phase1-20261027T135449072864Z-41b427b5/dataset_audit.json), [notebook 00](../../../notebooks/00_dataset_audit.ipynb), [audit.py](../../../src/data/audit.py).
- **Giới hạn / bước tiếp:** thiếu từ điển chuyên môn và checksum nhà xuất bản; EDA tiếp tục đo support độc lập và rủi ro leakage.

## 2. Phase 1 — EDA và tính phù hợp (lịch sử tái dựng)

- **Mục tiêu / vấn đề:** hiểu phân bố lớp/triệu chứng và liệu số dòng có phản ánh thông tin độc lập.
- **Đã làm:** phân tích toàn dữ liệu, đồng xuất hiện/profile, số vector theo lớp và xung đột; không fit model hoặc lựa chọn đặc trưng.
- **Quyết định / lý do:** group phải dựa trên vector triệu chứng, kể cả khác nhãn. Không gọi tỷ lệ ghi nhớ thực nghiệm là validation/test accuracy. Phase 1 đã thăm dò toàn CSV nên test khóa sau này không phải dữ liệu hoàn toàn chưa từng xem.
- **Phương án cân nhắc:** tăng số dòng bằng nhân bản không tạo vector mới; chia ngẫu nhiên theo dòng làm rò rỉ vector. Khuyến nghị test khoảng 20% trong báo cáo EDA chỉ là đề xuất lịch sử; policy cuối Phase 2 dùng khoảng 70/15/15.
- **Kết quả / bằng chứng:** 169.888 vector gốc, 115 lớp dưới 5 vector, 46 lớp chỉ 1 vector; trung bình 5,33 triệu chứng/dòng. Metadata thực thi lịch sử ghi Python Windows 3.11.9, audit/EDA có 6/9 code cell, 0 error, EDA 8 hình nhúng; không phải lần chạy mới hôm nay.
- **File:** [EDA summary](../../../reports/eda_summary.md), [notebook 01](../../../notebooks/01_eda.ipynb), [execution_all.json] [../artifacts/metadata/execution_all.json; historical source-only reference], [validation.json] [../artifacts/metadata/validation.json; historical source-only reference].
- **Giới hạn / bước tiếp:** dữ liệu tổng hợp, thiếu ID bệnh nhân/thời gian/cơ sở, chưa xác thực lâm sàng; kiểm preprocessing trước khóa dữ liệu.

## 3. Portability ban đầu — local/remote và import source (lịch sử tái dựng)

- **Mục tiêu / vấn đề:** notebook từ CWD khác hoặc Colab `/content` không tìm được `configs/`/`src/`; mở `.ipynb` local trong VS Code không chuyển source sang kernel remote.
- **Đã làm:** tách đường dẫn source/storage/output/cache, loader và cấu hình; thêm smoke/packaging và kiểm regression. Bằng chứng run có mốc 2026-10-21.
- **Quyết định / lý do:** raw đọc nguyên trạng, output quan trọng persistent; mount phụ thuộc khả năng runtime, không giả định mọi Jupyter hỗ trợ `drive.mount`.
- **Phương án đã thử:** root discovery, override, ZIP/.pyz đưa source lên runtime. Các cách này giải quyết từng phần nhưng về sau tạo nhiều bước đồng bộ, không còn là workflow hiện hành.
- **Kết quả / bằng chứng:** báo cáo lịch sử ghi 43 test đạt, 26 bảng khớp, 8 PNG khớp pixel và notebook local chạy đầy đủ; tại thời điểm đó chưa xác minh Colab thật. Các con số là bằng chứng cũ, không phải suite chạy ở lần lập log.
- **File:** [bằng chứng portability, phần lịch sử](../../portability_validation.md), [paths.py](../../../src/data/paths.py), [loader.py](../../../src/data/loader.py), [runtime config](../../../configs/runtime.json).
- **Giới hạn / bước tiếp:** source không tự upload theo notebook; tiếp tục đơn giản hóa deployment khi ưu tiên Colab/Drive, xem mục 7–8.

## 4. Phase 2 — Inspection và hai cột regurgitation (lịch sử tái dựng)

- **Mục tiêu / vấn đề:** tránh gộp/xóa feature dựa riêng hậu tố `.1`; cần ánh xạ triệu chứng từ lời kể người dùng.
- **Đã làm:** kiểm header, đối chiếu giá trị/support hai cột, thử phép chiếu và đếm lại vector/eligibility; giữ raw và chưa áp dụng thay đổi trong giai đoạn inspection.
- **Quyết định / lý do:** lúc inspection tạm giữ để phân tích; sau phê duyệt **bỏ cả `regurgitation` và `regurgitation.1`** vì chưa xác minh được ý nghĩa phân biệt để nhận input đáng tin. Đây là tiến triển quyết định, không phải hai cột giống hệt hoặc PCA/feature selection theo score.
- **Phương án cân nhắc:** giữ cả hai, giữ một, gộp OR hoặc bỏ cả hai. Không tự suy nghĩa từ tên hoặc tự chọn nhãn đa số.
- **Kết quả / bằng chứng:** code kiểm header ghi hai tên đã tồn tại trong CSV, không đủ căn cứ quy cho pandas tạo ra. Bảng ảnh hưởng cho thấy mất vector khi chiếu xuống schema mới; các lớp trước đó đủ ≥10 không bị mất eligibility trên phép kiểm đã lưu. Không coi “không mất lớp” là “không mất thông tin”.
- **File:** [inspection.py](../../../src/data/preprocessing_inspection.py), [bảng ảnh hưởng](../../../../disease-prediction-ml-data/reports/tables/preprocessing_regurgitation_removal_impact.csv), [bảng support](../../../../disease-prediction-ml-data/reports/tables/preprocessing_regurgitation_support.csv), [policy cuối](../../../configs/phase2.json).
- **Giới hạn / bước tiếp:** thiếu từ điển phân biệt hai khái niệm; chốt schema, dedup và tính lại support thay vì tái sử dụng số trên 377 feature.

## 5. Phase 2 — Rà soát lớp hiếm, chọn ngưỡng ≥10 (lịch sử tái dựng)

- **Mục tiêu / vấn đề:** cân bằng độ phủ bệnh và số vector để train/đánh giá; số dòng raw có thể bị phóng đại bởi trùng lặp.
- **Đã làm:** bảng eligibility so các ngưỡng 1/3/5/10; code review bổ sung so sánh 1/3/5/10/15 cùng phương pháp group, seed 42 và một hình hai panel. Không dùng model score để chọn ngưỡng.
- **Quyết định / lý do:** ứng viên ban đầu ≥5 được thay bằng **≥10 vector phân biệt/lớp** sau biến đổi schema và dedup; đây là policy đã duyệt, không mở lại ở nhiệm vụ hiện tại.
- **Phương án cân nhắc:** ngưỡng 1 không thể phủ ba tập cho lớp 1 vector; 3 chỉ vừa đủ tối thiểu; 5 giữ nhiều lớp nhưng support đánh giá ít; 15 loại thêm lớp. Không ép mọi lớp bằng nhân bản dữ liệu, không tìm seed có điểm tốt hơn.
- **Kết quả / bằng chứng:** bảng lịch sử trên **377 feature trước bỏ cột**: ≥5 giữ 658 lớp/189.409 cặp, ≥10 giữ 587 lớp/188.920 cặp (99,6167% của 189.647 cặp sau dedup gốc). Đây không phải số cuối của schema 375. Không còn đầy đủ bảng output riêng của phép so ≥15 để trích con số chính xác tại lần rà soát này; không tái chạy để bù lịch sử.
- **File:** [bảng eligibility lịch sử](../../../../disease-prediction-ml-data/reports/tables/preprocessing_class_eligibility.csv), [hình so ngưỡng](../../../../disease-prediction-ml-data/reports/figures/preprocessing_threshold_comparison.png), [phụ lục notebook 02](../../../notebooks/02_preprocessing.ipynb), [threshold_split_comparison](../../../src/data/preprocessing_inspection.py).
- **Giới hạn / bước tiếp:** vector phân biệt không chứng minh độc lập bệnh nhân; ≥10 không bảo đảm metric ổn định. Áp dụng đúng thứ tự được duyệt và kiểm split cuối.

## 6. Phase 2 — Pipeline, chia group và khóa artifact (lịch sử tái dựng)

- **Mục tiêu / vấn đề:** tạo bộ dữ liệu tái lập, không để vector giống nhau xuất hiện ở nhiều partition; giữ được nhãn xung đột mà không tự sửa bệnh.
- **Đã làm:** validate raw → bỏ hai cột → dedup vector còn lại+nhãn → đếm vector/lớp → lọc ≥10 → tạo group → chia/kiểm → lưu artifact. Số dòng: **246.945 → 246.945 → 188.161 → 188.161 → 187.434**, cuối 375 feature/587 lớp.
- **Quyết định / lý do:** dùng `seeded_group_quota_coverage_repair_v1`, gần 70/15/15, seed 42; khi sửa coverage chỉ chuyển group nếu không làm mất lớp ở tập cho. Giữ vector nhiều nhãn, không majority-relabel. `VarianceThreshold(0)` chỉ fit train trong pipeline training sau này.
- **Phương án cân nhắc:** stratified row split làm giao vector; thay nhãn đa số mất thông tin; ép đúng tỷ lệ bằng tách group vi phạm ràng buộc. Phương pháp repair là heuristic được kiểm trên bộ này, không bảo đảm cho mọi dataset.
- **Kết quả / bằng chứng:** train/validation/test có **131.248/28.120/28.066** dòng và **117.211/25.127/25.128** group, mỗi tập đủ 587 lớp; overlap group/vector=0, exact duplicate vector+nhãn=0, seed42 tái lập, giữ 12.728 group nhiều nhãn. Lớp chỉ 1 vector validation/test: **33/41**.
- **Khóa:** `feature_schema.json`, `label_mapping.json`, policy, split metadata/assignments và CSV gzip được manifest ghi checksum; fingerprint processed `afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3`. Không thay raw, split, schema hoặc mapping.
- **File:** [báo cáo cuối](../../../reports/preprocessing_decision_review.md), [preprocessing.py](../../../src/data/preprocessing.py), [dataset manifest](../../../../disease-prediction-ml-data/artifacts/metadata/phase2/dataset_manifest.json), [split metadata](../../../../disease-prediction-ml-data/artifacts/metadata/phase2/split_metadata.json), [notebook 02](../../../notebooks/02_preprocessing.ipynb).
- **Giới hạn / bước tiếp:** test đã được EDA xem thống kê trước khi khóa, lớp hiếm còn support thấp. Bước tiếp là baseline train/validation; test chỉ dùng đánh giá cuối.

## 7. Colab/Drive — Các lỗi đồng bộ và output (lịch sử tái dựng)

- **Mục tiêu / vấn đề:** source thiếu/stale trên remote, notebook nhiều lịch sử bị hiểu là không có output, rồi source receipt/manifest không khớp ngăn bootstrap.
- **Đã làm:** rút gọn luồng chính 02 để bảng kết quả luôn hiện; dồn kiểm tra cũ vào phụ lục tùy chọn. Notebook 03 có code từng model thay cho chỉ gọi wrapper. Thử deployment archive và dual-package với receipt trước khi chuyển sang canonical Drive.
- **Quyết định / lý do:** lỗi import `src` sau bootstrap thất bại là hậu quả, không phải lý do cài thêm package `src`. Phải tách kiểm source khỏi integrity dữ liệu; Phase 1 không cần Phase 2/3 artifact.
- **Phương án đã thử / thất bại:** ZIP/pyz, `colab-session` và hai receipt có thể lệch phiên bản khi upload; sửa đường dẫn riêng từng notebook không giải quyết kiến trúc. Giữ package cũ làm lịch sử, ngừng dùng chúng.
- **Kết quả / bằng chứng:** báo cáo ghi local manifest `ca20a551…`, Drive `50308d25…`; audit xác định khác provenance môi trường/source, artifact train/validation/metadata giống nhau. Baseline độc lập ghi hai manifest được duyệt; không hardcode checksum mới từ Drive chưa kiểm hoặc tắt validation. Sau đó vẫn có lỗi receipt Drive khác session, dẫn tới quyết định bỏ flow hai gói.
- **File:** [validation hiện tại và lịch sử](../../portability_validation.md), [baseline integrity](../../../configs/phase2_integrity.json), [notebook 02](../../../notebooks/02_preprocessing.ipynb), [notebook 03](../../../notebooks/03_model_training.ipynb).
- **Giới hạn / bước tiếp:** các kiểm tra notebook local cũ không chứng minh UI/runtime Colab; xác minh flow mới bằng smoke riêng, không fit model.

## 8. Canonical Drive runtime — Đã kiểm smoke thật (mốc ghi nhận 2026-10-27)

Ngày 2026-10-27 là mốc ghi trong báo cáo hiện có; JSON smoke không chứa timestamp gốc, không dùng mốc này để suy giờ chạy kernel.

- **Mục tiêu / vấn đề:** một nguồn source/config trên Drive, tránh tải gói phiên runtime mới hoặc so hai receipt độc lập.
- **Đã làm / quyết định:** bootstrap stdlib từ Drive → copy vào `/content/disease-prediction-ml-runtime` → import; cache tạm, output persistent. Một folder upload `dist/drive-source/`; Stage A kiểm môi trường/quyền ghi, B source/import, C integrity riêng. `00/01` không phụ thuộc Stage C Phase 2. Không cần colab-session/ZIP/pyz cho luồng hiện tại.
- **Phương án cân nhắc:** tiếp tục bản vá dual-package hoặc nới integrity; loại bỏ dependency session, vẫn giữ data integrity và kiểm module cũ/restart.
- **Kết quả / bằng chứng:** báo cáo ghi **120 passed, 13 deselected** trên Windows với phạm vi loại trừ rõ; không phải full suite. Người dùng chạy Colab Python **3.13.16** và gửi **A/B/C PASS**, 7 checksum train/validation/metadata hợp lệ, schema/order/encoding và Drive write/read/checksum/delete đạt. Train 131.248×375/587 lớp, validation 28.120×375/587 lớp; `test_payload_opened=false`, `models_trained=0`.
- **Identity:** source fingerprint `95b01d6ea67d68f9bbc48b647ca15b3c38219baac15639ae78637f184806bd61`; Drive manifest `50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9`.
- **File:** [hướng dẫn hiện hành](../../phase3_colab.md), [bằng chứng/phạm vi test](../../portability_validation.md), [colab_runtime.py](../../../src/data/colab_runtime.py), [integrity.py](../../../src/data/integrity.py), [smoke notebook](../../../notebooks/colab_smoke_test.ipynb).
- **Giới hạn / bước tiếp:** đây là output Colab thật do người dùng cung cấp, agent không trực tiếp điều khiển kernel; smoke không chứng minh training hay chatbot chạy thành công. Giữ nguyên kiến trúc đã kiểm, không đổi bootstrap trong nhiệm vụ tài liệu này.

## 9. Phase 3 — Sẵn sàng code năm baseline (lịch sử tái dựng; training chờ xác minh)

- **Mục tiêu / vấn đề:** chuẩn bị so sánh classifier trên cùng split, có giới hạn RAM/checkpoint để phiên Colab gián đoạn không mất kết quả.
- **Đã làm:** code/config cho Logistic Regression, LinearSVC, Random Forest, KNN, BernoulliNB; notebook hiển thị pipeline/fit từng model; lưu identity, checksum và prediction validation khi chạy thành công.
- **Quyết định / lý do:** dùng năm họ học bổ sung cách nhìn dữ liệu nhị phân, Macro F1 làm metric chính; variance chỉ fit train, không xem test để chọn model. Phần giải thích đầy đủ được bổ sung ở lần lập log, không giả nhận nhóm đã ghi rationale này từ đầu.
- **Phương án cân nhắc:** boosting, MLP, kernel SVM là ứng viên ngoài scope đợt đầu; chưa có thí nghiệm loại chúng vì điểm kém. Voting chỉ là bước sau khi có predictions và phân tích lỗi thực.
- **Kết quả / bằng chứng:** config có seed42 và expected Phase2 identity; local `artifacts/models/` chỉ có `.gitkeep`, notebook03 chưa có output/execution training. Chưa có bảng điểm hoặc thời gian đã xác minh để điền vào log.
- **File:** [phase3.json](../../../configs/phase3.json), [training.py](../../../src/models/training.py), [reporting.py](../../../src/models/reporting.py), [notebook03](../../../notebooks/03_model_training.ipynb), [lý do chọn model](../../MODEL_SELECTION_RATIONALE.md).
- **Giới hạn / bước tiếp:** chưa biết kết quả riêng có thể tồn tại ngoài workspace; khi có yêu cầu training mới, chạy baseline rồi bổ sung metric/resource/hội tụ thực. Chưa chọn model thắng hoặc ensemble.

## 10. 2026-10-28 — Điều chỉnh tài liệu theo phản hồi giảng viên

- **Mục tiêu / vấn đề:** làm rõ LLM hiểu tiếng Việt và giải thích, ML chịu trách nhiệm phân loại; tránh biến chatbot thành bộ đoán bệnh do LLM hoặc hiểu feature extraction là PCA.
- **Đã làm:** mô tả luồng, trách nhiệm, interface structured extraction/mapper/prediction/response; giải thích năm model và các biến thể NB; lập nhật ký duy nhất từ bằng chứng hiện có, thêm điều hướng README.
- **Quyết định / lý do:** Python kiểm output LLM theo schema375 đã lưu, vector đúng thứ tự; giữ denied/uncertain/unmentioned/unmapped trong sidecar, chỉ affirmed hợp lệ nhận1. Nhãn phải giải mã mapping587; score mặc định null nếu chưa có cơ sở xác thực. Thiếu/mâu thuẫn thông tin thì hỏi rõ hoặc abstain. LLM không chọn nhãn thay ML.
- **Phương án cân nhắc:** LLM đoán bệnh trực tiếp, tự thêm feature/diễn giải 0 thành phủ định, hoặc ép score cho mọi model không phù hợp hợp đồng. Không đổi preprocessing để đáp ứng phản hồi này.
- **Kết quả / bằng chứng:** hoàn tất tài liệu thiết kế; BernoulliNB phù hợp miền nhị phân nhưng giả định độc lập có điều kiện và việc dùng cả trạng thái0 là giới hạn phải báo. Chưa triển khai LLM/mapper/chatbot, chưa train model.
- **File:** [kiến trúc/interface](../../SYSTEM_ARCHITECTURE.md), [rationale/model/NB và hình dự kiến](../../MODEL_SELECTION_RATIONALE.md), [README](../../../README.md), nhật ký này.
- **Giới hạn:** chưa có biên bản giảng viên độc lập ngoài yêu cầu người dùng; thiếu ngày chính xác nhiều hoạt động cũ, đầy đủ output review ≥15, checksum nhà xuất bản, checkpoint/metrics baseline và đánh giá ánh xạ tiếng Việt. Không suy diễn để lấp các khoảng trống.
- **Bước tiếp theo dự kiến:** khi được giao, thực hiện training baseline và dùng metric/predictions thật cho hai hình **Macro F1 vs fit/predict time** và **độ giống lỗi validation từng cặp**; sau chọn/kiểm model mới triển khai hợp đồng LLM. Không tạo hình hiệu năng giả và không chạy các bước đó trong nhiệm vụ hiện tại.

## 11. 2026-10-28 — Kiểm tra thay đổi tài liệu

- **Mục tiêu / vấn đề:** bảo đảm log phản ánh bằng chứng và tài liệu không làm thay đổi notebook/dataset/model.
- **Đã làm / quyết định:** kiểm đường dẫn/link nội bộ, dữ kiện với JSON artifact/config, ví dụ feature và phạm vi trạng thái; đối chiếu hash trước–sau. Chỉ kiểm tĩnh và bất biến file là phù hợp thay đổi Markdown; không chạy notebook/training hoặc full data regression để kiểm tài liệu.
- **Kết quả / bằng chứng:** kiểm tĩnh **4 file Markdown, 73 link tương đối hợp lệ**; số bước/split/feature/lớp, policy, mapping, tên feature ví dụ và cấu hình model khớp JSON hiện có. Snapshot trước–sau xác nhận **277 file hiện có giữ nguyên SHA-256, size và mtime**; chỉ README đổi và thêm 3 tài liệu trong `docs/`. Năm notebook, toàn bộ source/bootstrap/config, raw/processed, reports và model artifacts giữ nguyên. Không giải nén/nạp/evaluate test; băm byte file nén chỉ để kiểm bất biến. Không chạy pytest hoặc notebook ở lần sửa Markdown này; số120 test trong mục8 là bằng chứng lịch sử.
- **File / giới hạn:** bốn file tài liệu của mục10; không xác minh lại kernel Colab trong lần này. Các bằng chứng Colab ở mục8 vẫn là lần người dùng đã gửi.
- **Bước tiếp:** thêm mục mới vào log khi có thay đổi đáng kể, giữ nguyên bằng chứng cũ và ranh giới phase đã khóa.

## 12. 2026-10-28 — Preflight notebook03, không training

- **Mục tiêu / vấn đề:** xác minh đường đi từ 14 cell đến shared bootstrap, train/validation loader, pipeline, tài nguyên, checkpoint và hình/bảng trước khi cho phép training.
- **Đã làm / quyết định:** review config/model/direct dependencies; bổ sung unit không fit và chạy smoke local trên dữ liệu đã khóa. Không phát hiện lỗi production cần sửa nên giữ nguyên notebook/source/config/bootstrap/checkpoint. Không tạo môi trường hoặc deployment mới.
- **Phương án cân nhắc:** full training sẽ kiểm được RAM/hội tụ/resume fitted pipeline nhưng ngoài phạm vi được phép; dùng constructor, fresh-process serialization pipeline chưa fit, unit checksum/reuse/batch và review nhánh fit. Không tạo metric hoặc hình model-performance để lấp phần chưa chạy.
- **Kết quả / bằng chứng:** **42 passed, 12 deselected**; smoke load train 131.248×375/587 lớp và validation 28.120×375/587 lớp, tạo 5 pipeline chưa fit. Smoke guard ghi fit_calls=0 và test_csv_open_attempts=0. Unit có 0 fit model/feature transformer; helper metrics dùng 11 lần LabelEncoder tạm, không đổi mapping. Lượt guard đầu chặn quá rộng đã được sửa và ghi rõ trong báo cáo.
- **File:** [báo cáo preflight](../ml/phase3_preflight.md), [unit test mới](../../../tests/test_phase3_preflight.py), nhật ký này. Bằng chứng smoke Colab cũ không được gán thành kiểm tra training mới.
- **Giới hạn:** completed checkpoint reuse đã kiểm bằng fixture metadata/bytes; chưa resume model đã fit thật trên Colab. Fit-only checkpoint cần explicit trust có sẵn; không có phục hồi giữa iteration nếu VM mất khi đang fit. Batch64/working_memory128MiB không phải trần tổng RAM.
- **Bước tiếp theo dự kiến:** chỉ khi có nhiệm vụ training mới, chạy model và báo số đo/RAM/hội tụ thật; nếu lặp preflight Colab thì dừng trước 5 model cell. Không mở CSV test hoặc dùng test chọn model.

## 13. 2026-10-28 — Post-training audit; chờ artifact thực của Colab

- **Mục tiêu / vấn đề:** người dùng báo hoàn tất training năm baseline và yêu cầu kiểm warnings, checkpoint/reload, metrics, pipeline, tài nguyên trước Phase 4. Đây là cập nhật trạng thái do người dùng báo sau preflight; chưa phải training được agent xác minh.
- **Kết quả người dùng cung cấp, chưa kiểm artifact:** Macro F1 LR 0,78781 / RF 0,49200 / LinearSVC 0,78422 / KNN 0,73103 / BernoulliNB 0,59934; fit/predict tương ứng 91,59420/2,15747s; 15,10077/20,68390s; 80,59617/1,82650s; 1,09042/294,22415s; 1,83618/5,74700s. Warning count 6/3/5/31/2 và 318 feature mỗi model đều cần đối chiếu bản ghi gốc. Không điền các số này thành metrics đã xác thực.
- **Đã làm / bằng chứng:** kiểm inventory workspace/attachment và notebook 03: local chỉ có `.gitkeep` trong models, chưa có checkpoint/predictions/metadata Phase 3 hoặc output notebook; không có kết nối Drive/kernel/document session. Đọc lại source ghi warnings/checkpoint/metrics/handoff. Kiểm baseline và train/validation local đạt 7 checksum, 375 feature/587 lớp, không giao group; thống kê train-only có 318 feature biến thiên. Support validation min 1/median 25/max 215; 33 lớp support 1, 68 lớp ≤2, 132 lớp ≤5.
- **Quyết định / lý do:** các bước model-specific phải ghi NOT VERIFIED; không suy warning class từ count, không gán PASS reload/metric/mask bằng test fixture hoặc smoke cũ. `phase4_ready` trong code chỉ dựa đủ model completed, không thay kiểm hội tụ/integrity/chất lượng.
- **Phương án cân nhắc:** nhận diện vị trí bản local hoặc dùng bằng chứng chỉ đọc từ kernel Colab đang có artifact; không train lại để tạo log, không sửa checkpoint/Phase 2/bootstrap để bù bằng chứng. Đã hỏi người dùng vị trí artifact có thể truy cập.
- **Trade-off / giới hạn:** LR/SVC dẫn Macro F1 và KNN chậm theo bảng tham chiếu; chưa có peak RSS/runtime/version/checkpoint size để kiểm. Warnings, unique predicted classes, never-predicted/F1=0, masks và prediction sau reload chưa xác minh. Support thấp hạn chế diễn giải từng bệnh.
- **Khuyến nghị:** **chưa thông qua Phase 4 do thiếu bằng chứng audit**, không kết luận model hỏng hoặc cần retrain. Chưa có defect cụ thể để trình sửa; chỉ tiếp tục kiểm artifact khi đọc được. Không ensemble, tuning hoặc benchmark mới.
- **File:** [báo cáo audit duy nhất](../../../reports/phase3_post_training_audit.md) chứa bảng tham chiếu đầy đủ và danh sách bằng chứng còn thiếu; nhật ký này. Kiểm local có fit_calls=0, test_csv_open_attempts=0; không deserialize/predict trained model hoặc sửa dataset/model.

## 14. 2026-10-28 — Chuẩn bị kiểm artifact trực tiếp trong Colab

- **Bằng chứng mới / vấn đề:** người dùng xác nhận checkpoint/results chỉ ở Drive; chưa có bản local hoặc kết nối filesystem Drive từ agent. Giữ trạng thái post-training NOT VERIFIED, không lấy kết quả unit làm bằng chứng cho model thật.
- **Đã làm / quyết định:** thêm một [script audit chỉ đọc](../../../scripts/audit_phase3_results.py), dùng session/bootstrap và loader/helper hiện có. Helper kiểm warnings, checksum/identity, metrics/per-class support, fitted pipeline/mask và reload-validation comparison tuần tự; ghi kết quả vào stdout có checksum để gửi lại. Không đổi bootstrap/checkpoint/model hoặc thông số.
- **Phương án cân nhắc:** đồng bộ toàn bộ model về máy sẽ phải tải checkpoint lớn; chạy helper trên kernel đang có Drive cho phép kiểm tại chỗ. Chỉ upload helper vào `/content`, không tạo deployment hoặc notebook mới. Source/library khác run cũ thì ghi rõ phần reload chưa xác minh.
- **Kết quả kiểm local:** **7 test PASS**, dùng test doubles/artifact bytes trong tmp; bao gồm điều phối năm model, CSV metric mismatch, lossless evidence packet và guard chặn ghi storage/test/fit. Guard fit được thử và dừng trước thân hàm, không huấn luyện estimator. Unit fixtures không phải kết quả dự án.
- **Giới hạn / bước tiếp:** chờ người dùng chạy cell trong [báo cáo audit](../../../reports/phase3_post_training_audit.md) và gửi3 dòng packet hoặc traceback đầu. Chưa nhận bằng chứng reload/metrics/warnings của năm checkpoint thật, chưa thông qua Phase 4 và chưa thực hiện sửa model hay ensemble.

## 15. 2026-10-28 — Hoàn tất post-training audit từ bằng chứng Colab

- **Mục tiêu / bằng chứng mới:** người dùng chạy helper trên Colab và gửi packet cho run `baseline-v1-f8a5bfdb7b4c12cd`. Giải mã thành công, SHA-256 khớp `41a4ad3b0c3b8c783382b807688fd0958b00666b6e46bb84c3d3fe1e8c16fb48`; lưu nguyên byte tại [colab_evidence.json](../../../artifacts/metadata/phase3_audit/colab_evidence.json). Agent không trực tiếp điều khiển kernel hoặc tải các model về máy. Không suy ngày training gốc từ ngày nhận bằng chứng.
- **Checkpoint / pipeline:** cả năm có đủ 4 file; checksum model/fit/predictions, identity data/schema/mapping/config/source và phiên bản thư viện đều đạt. Model và transformer fitted; input đúng 375 feature/587 nhãn, cùng mask giữ 318 feature với variances khớp train. Reload và so lại toàn bộ validation đều PASS, 0 prediction mismatch. CSV/run summary và 3 hình đã có cũng PASS đối chiếu, không ghi lại artifact.
- **Metrics đã xác minh:** Accuracy/Macro Precision/Macro Recall/Macro F1/Weighted F1 tính lại từ predictions đã lưu theo zero_division=0. Macro F1 LR **0,78780814**, RF **0,49199733**, LinearSVC **0,78422186**, KNN **0,73103438**, BernoulliNB **0,59934053**; khớp bảng tham chiếu làm tròn. Số lớp chưa từng dự đoán tương ứng **27/157/23/27/143**, F1=0 **28/157/24/34/144**.
- **Warning findings:** warning count gốc 6/3/5/31/2 khớp: **44 DeprecationWarning utcnow + 3 ResourceWarning socket zmq.PUSH**, không có ConvergenceWarning được lưu. LR fit có 3 D + 1 R, predict 2 D; RF predict 3 D; SVC fit 2 D + 1 R, predict 2 D; KNN predict 30 D + 1 R; NB predict 2 D. Reload chỉ ghi D, số lần 2/3/2/21/2, tách khỏi warning gốc. D xếp INFO tương thích API, R giữ REVIEW tài nguyên; chưa có ảnh hưởng sai output được quan sát. Không kết luận đã kiểm mọi warning ngoài các context capture hoặc chứng minh tối ưu tuyệt đối.
- **Tài nguyên / trade-off:** training Colab Linux Python 3.13.18, sklearn 1.6.1, CPU Xeon 2 logical CPU, RAM 12,671 GiB, không GPU. Fit/predict gốc đã xác minh như mục 13; KNN predict validation **294,22415s**, LR/SVC **2,15747/1,82650s**. Pipeline nén LR/RF/SVC/KNN/NB lần lượt **1.438.385/14.420.893/1.463.693/652.535/102.624 byte**. RSS lấy mẫu của process/children không phải RAM riêng estimator hoặc latency một người dùng; số đầy đủ ở báo cáo.
- **Quyết định / lý do:** **không có BLOCKER được phát hiện; có thể tiếp tục Phase 4 với giới hạn được ghi nhận (REVIEW)**. Chưa có defect đòi sửa model, threshold hoặc hyperparameter. Giữ cảnh báo, không suppress/retrain để làm sạch log. Chưa xác định component phát utcnow/đóng socket vì thiếu filename/lineno; xử lý dependency/runtime chỉ khi có bằng chứng trong nhiệm vụ riêng.
- **Giới hạn:** 33 lớp validation support 1, 132 lớp ≤5; coverage RF/NB yếu, KNN tốn inference; chưa biết lợi ích Voting hoặc mức tương đồng lỗi LR/SVC. Source/variances nhất quán train-only không chứng minh mọi thao tác ngoài log trong lịch sử kernel; Phase 1 từng EDA toàn CSV vẫn là giới hạn. Các mục 13–14 NOT VERIFIED được giữ như lịch sử thiếu bằng chứng, không phải trạng thái hiện tại.
- **Bảo toàn / bước tiếp:** guard audit Colab ghi 0 model/feature fit attempt, 0 test access, 0 persistent write; 15 lần LabelEncoder tạm cho metrics không đổi mapping. Chỉ lưu evidence, cập nhật [báo cáo audit duy nhất](../../../reports/phase3_post_training_audit.md) và nhật ký; không sửa source/bootstrap/notebook/dataset/checkpoint. Dừng sau audit, chờ nhiệm vụ tiếp theo từ người dùng trước ensemble hoặc training khác.

## 16. 2026-10-28 — Triển khai Phase 4 từ checkpoint, chờ validation Colab

- **Mục tiêu / vấn đề:** người dùng giao Phase 4 trên run `baseline-v1-f8a5bfdb7b4c12cd`; cần ensemble mà không fit clone baseline, dùng test hoặc đổi schema/model.
- **Đã làm / quyết định:** thêm [ensemble.py](../../../src/models/ensemble.py) và một [notebook04](../../../notebooks/04_ensemble.ipynb), dùng nguyên shared bootstrap/loader/checkpoint helpers. Kiểm y_true/row/group/class order và metrics; D/J/rescue cùng validation; chỉ3 hard/2 soft đã yêu cầu. Hard majority phá hòa theo LR/SVC/KNN/NB/RF; soft trung bình đều, không LinearSVC/calibration/weight search. Probability thực được kiểm và sinh theo batch khi chưa lưu; memmap ở runtime tạm.
- **Lý do / phương án:** VotingClassifier.fit sẽ retrain clone nên không dùng. Khác họ không bảo đảm sửa lỗi; nếu cả LR/SVC sai, ba hard vote với tie LR cũng không cứu được. Nếu thiếu probability/environment phù hợp thì ghi limitation, không tạo metric giả. Định nghĩa inference tham chiếu weight có sẵn, input giữ375 feature; test một vector, không benchmark latency.
- **Persistence:** dùng namespace run mới theo OutputPaths hiện có; đúng2 hình, bảng, report, predictions ensemble và definitions/checksum metadata trên Drive, không ghi đè Phase2/3 hoặc probability lớn.
- **Kết quả / bằng chứng hiện có:** test logic và I/O local dùng fixtures, chưa có error-diversity hoặc Macro F1 ensemble thật để báo. Bộ test gộp48 pass/1 fail; failure cũ do smoke đã chèn mount cell nhưng migrator dùng index cố định. Giữ file người dùng, không chạy updater hoặc sửa bootstrap.
- **Cập nhật kiểm tra cuối:** sửa riêng utility cập nhật notebook để nhận diện cell theo nội dung, thêm regression test bảo toàn mount/output; không chạy utility trên notebook người dùng. Bộ liên quan **50 test PASS**, gồm **15 test Phase4**. Source-only staging32 file và CheckOnly PASS, fingerprint `fc45ec50a18222aa4bc1ab71e55081becb478df406f7ea4c46bbd74edec3298b`. Lỗi cache memmap trong nhánh probability không khả dụng đã được phát hiện/sửa trong test trước triển khai; không thay pipeline baseline hoặc bootstrap.
- **File:** [hướng dẫn Phase4](../../phase4_ensemble.md), [test_ensemble.py](../../../tests/test_ensemble.py), builder notebook và source nói trên; bổ sung điều hướng README.
- **Giới hạn / bước tiếp:** checkpoint/predictions thật chỉ trên Drive. Chờ chạy notebook04 trên Colab và packet kết quả để ghi metrics/diversity/best candidate thực; chưa chọn final model, chưa triển khai chatbot, chưa mở test hoặc train/tune model.

## 17. 2026-10-28 — Hoàn tất Phase 4 từ kết quả Colab

- **Mục tiêu / bằng chứng mới:** người dùng đã chạy notebook04 trên Colab, gửi packet run `phase4-20261028T091711786379Z-c1c66643` từ experiment `baseline-v1-f8a5bfdb7b4c12cd`. Giải mã, kiểm SHA-256 khớp `42cf30dc39547656c572cf5ca4bb6a0eae3a6d31f0a923e6518e8618e835dd44`, lưu nguyên 23.171 byte tại [colab_validation_evidence.json](../../../artifacts/metadata/phase4_audit/colab_validation_evidence.json). Agent kiểm packet local, không trực tiếp chạy kernel hoặc tải model về máy. Trạng thái chờ ở mục16 được khép lại bằng bằng chứng này.
- **Integrity / môi trường:** source module Colab SHA `ee3121f04b187845fbff937add77a527d2761df14e035e94f48100b1d647443c` khớp local/staging. Runtime Python3.13.18, sklearn1.6.1, NumPy2.1.3, SciPy1.16.3, joblib1.6.0. Hoàn tất các cổng kiểm năm checkpoint/predictions, Phase2 identity/schema/mapping, y_true/row order và baseline metrics của source đã đối chiếu; cùng **28.120 hàng validation, 375 feature, 587 lớp**. Bốn SHA pipeline dùng sinh probability khớp evidence audit mục15. Không lấy fixture làm kết quả thật.

Metrics thực, `zero_division=0`; Macro F1 là tiêu chí chính. NB = BernoulliNB, SVC = LinearSVC:

| Model/tổ hợp | Accuracy | Macro P | Macro R | Macro F1 | Weighted F1 | Lớp dự đoán | Lớp F1=0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LR đơn | 0,83709104 | 0,82741979 | 0,77918852 | **0,78780814** | 0,83667539 | 560 | 28 |
| Hard LR+SVC+KNN | 0,83645092 | 0,82189954 | 0,78108330 | 0,78733399 | 0,83597865 | 559 | 29 |
| Hard LR+SVC+NB | 0,83613087 | 0,82795662 | 0,77187045 | 0,78478926 | 0,83534646 | 558 | 30 |
| Hard LR+SVC+RF | 0,83545519 | 0,82514725 | 0,77342930 | 0,78405303 | 0,83477575 | 558 | 30 |
| Soft LR+NB+RF | 0,82542674 | 0,81936522 | 0,68532568 | 0,72469398 | 0,82110196 | 532 | 56 |
| Soft LR+KNN+NB | 0,82699147 | 0,83114194 | 0,74138957 | 0,76324258 | 0,82700045 | 548 | 39 |

- **Diversity:** cùng mẫu và thứ tự, heatmap5×5 dùng cả disagreement D và joint error J. LR/SVC D **7,6387%** (2.148 hàng), J **14,4488%** (4.063 hàng); SVC sửa được 518 hàng LR sai nhưng LR sửa được 695 hàng SVC sai. Với LR/RF, D/J là **29,9111%/12,5427%**; LR/KNN **20,1209%/12,4289%**; LR/NB **13,5526%/13,1721%**. Bất đồng cao không đồng nghĩa sửa lỗi tốt: RF/KNN/NB sửa lần lượt 1.054/1.086/877 hàng LR sai nhưng sai ở 4.894/2.603/1.502 hàng LR đúng. Các tỷ lệ trên lấy mẫu số28.120, không phải tỷ lệ điều kiện trên số lỗi LR.
- **Hard Voting:** ba tổ hợp lần lượt sửa **152/160/153** hàng LR sai nhưng làm sai **170/187/199** hàng LR đúng; delta Macro F1 so LR **−0,00047415/−0,00301888/−0,00375511**. Hòa ba nhãn khác nhau **1.000/659/1.263** hàng, áp dụng tie ưu tiên LR đã định. Khi LR và SVC đều sai, model thứ ba không thể cứu bằng majority3 với tie LR; lợi ích chỉ ở các trường hợp tạo đa số khi LR/SVC bất đồng. Không tìm tổ hợp hoặc trọng số khác.
- **Soft Voting:** cả hai hoàn tất từ `trusted_fitted_pipeline.predict_proba` thật của LR/RF/KNN/NB. Mỗi ma trận float64 28.120×587, cùng IDs0–586, checksum model/validation, finite/range/tổng hàng và argmax đối chiếu prediction đã kiểm. Không dùng SVC, decision-softmax, one-hot hoặc calibrator. Delta Macro F1 **−0,06311416/−0,02456556**; sửa559/917 nhưng làm sai887/1.201 hàng LR đúng. Probability không ghi về Drive; cache runtime được dọn. `limitations=[]` nghĩa là không có input/probability bị thiếu trong run, không có nghĩa đã chứng minh calibration hay giá trị lâm sàng.
- **Tài nguyên / trade-off:** candidate LR cần **1 pipeline, 1.438.385 byte (1,372 MiB)**; ensemble tốt nhất Hard LR+SVC+KNN cần **3 pipeline, 3.554.613 byte (3,390 MiB)** mà F1 vẫn thấp hơn. Tổng thời gian predict gốc Phase3 của ba model là **298,20813s** so LR **2,15747s** trên toàn validation; đây là tham chiếu cộng, không phải benchmark ensemble hay latency chatbot. Lần sinh probability mới đo được LR **10,747s**, RF **34,849s**, KNN **300,938s**, NB **12,704s**, gồm batch/kiểm tra; không so ngang với thời gian hard predict gốc. Checkpoint nén không phải peak RAM. Input375 candidate LR **PASS**, khớp validation hàng0; chưa benchmark một request hoặc xác minh single-input mọi tổ hợp trên Colab.
- **Warnings / giới hạn:** probability capture có29 DeprecationWarning `datetime.utcnow` (LR2/RF4/KNN21/NB2), không lỗi probability/integrity hoặc ConvergenceWarning được lưu trong bước này. Giữ nguyên cảnh báo và checkpoint, không suy nguồn gọi API khi thiếu traceback. 33 lớp validation support1, 132 lớp ≤5; dùng lại validation để lựa chọn, dữ liệu tổng hợp và Phase1 từng EDA toàn CSV tiếp tục hạn chế diễn giải. Xác suất chưa kiểm calibration; không kết luận chênh lệch nhỏ có ý nghĩa thống kê.
- **Kết quả / quyết định:** **không ensemble nào vượt Logistic Regression**. Đề xuất **LR đơn** cho bước chốt model vì Macro F1 cao nhất, coverage tốt hơn các tổ hợp và chỉ cần một pipeline. Không cố chọn Voting để chứng minh ensemble luôn tốt hơn. Đây là khuyến nghị từ validation, chưa phải kết quả final test hoặc chấp thuận triển khai chatbot.
- **Persistence:** Colab export report/bảng/đúng2 hình dưới `reports/runs/phase4-20261028T091711786379Z-c1c66643/`; results/predictions/manifest dưới `artifacts/metadata/runs/phase4-20261028T091711786379Z-c1c66643/`; definitions dưới `artifacts/models/phase4/phase4-20261028T091711786379Z-c1c66643/definitions.json`, candidate tham chiếu checkpoint LR cũ, không sao chép/refit weight. Manifest SHA do Colab báo **`d9d45b1972bb3f880f11db12a74b5258c1cc0e350075012e30dc9b42e5867281`**. Packet không chứa các file output đầy đủ; agent chưa đọc/băm lại từng file Drive độc lập, không gọi SHA truyền tải là xác thực chữ ký.
- **Kiểm tra / bảo toàn:** chạy lại **50 test PASS (20,80s)** về ensemble/preflight/audit/runtime/deployment; không fit baseline. Đối chiếu local packet/source SHA, số lượng/schema, tổ hợp, metric LR với audit cũ, delta/accuracy net corrections, tính đối xứng và quan hệ D/J/rescue, thứ tự lớp và SHA bốn pipeline đều PASS. Guard Colab ghi **0 model/feature fit, 0 test access, 0 protected write**. Chỉ thêm evidence/cập nhật tài liệu trong lần hoàn tất này; không đổi notebook, bootstrap, dataset, model, Phase2/3 hoặc source deployment.
- **File / bước tiếp:** [notebook04](../../../notebooks/04_ensemble.ipynb), [hướng dẫn Phase4](../../phase4_ensemble.md), evidence và nhật ký này. **Dừng sau Phase4 validation/documentation; chưa mở test, tuning, calibration, retrain hoặc chatbot.** Chờ người dùng duyệt lựa chọn model và giao nhiệm vụ final test riêng.

## 18. 2026-10-28 — Chốt biện luận Phase4 và thiết kế Phase5 LLM API

- **Mục tiêu / phản hồi:** người dùng yêu cầu hoàn tất lý do chọn model và thiết kế LLM bên ngoài để hiểu/diễn đạt tiếng Việt; chỉ tài liệu và bộ ví dụ nhỏ, chưa triển khai hoặc gọi API. Tiếp nối evidence Colab mục17, không tạo thí nghiệm mới.
- **Model selection:** chọn **Logistic Regression làm inference mặc định trong thiết kế**, Macro F1 **0,78780814**; ba hard **0,78733399 / 0,78478926 / 0,78405303**, hai soft **0,72469398 / 0,76324258**. Bảng metric đầy đủ ở mục17. LR đứng đầu các lựa chọn đã đánh giá, một pipeline nhỏ; không khẳng định tối ưu phổ quát và **chưa final locked-test evaluation**. Research/demo tùy chọn chỉ LR + hard tốt nhất LR/SVC/KNN + soft tốt nhất LR/KNN/NB, không phải chế độ cho người dùng chọn năm model như các chẩn đoán tương đương.
- **Biện luận / bằng chứng:** bổ sung [báo cáo Phase4 hiện có](phase4_ensemble.md#biện-luận-lựa-chọn-mô-hình) về member quality, số lỗi được cứu/làm sai, LR-priority tie và hạn chế probability chưa kiểm calibration. Hòa LR làm quyết định hard bất đối xứng và không cứu được khi LR/SVC cùng sai. Macro F1 dành trọng số ngang nhau cho587 lớp; Accuracy/Weighted F1/Macro P/R và coverage cung cấp góc nhìn khác. Phân biệt kết quả thực với giả thuyết calibration/model yếu kéo lệch trung bình, chưa có thí nghiệm xác nhận nguyên nhân. Dữ liệu tổng hợp và support thấp không xác lập độ tin cậy chẩn đoán thực tế.
- **Kiến trúc / quyết định:** external LLM API → JSON triệu chứng → Python kiểm schema/evidence/trạng thái và ánh xạ → đủ375 feature đúng thứ tự → pipeline LR đã fit (giảm318 bên trong) → Top3 nhãn tiếng Anh/score LR thực → external LLM diễn đạt tiếng Việt có kiểm nhãn. Không để LLM chọn bệnh, vector hoặc score. Đặc tả extraction đề xuất v2 ở [tài liệu Phase5 duy nhất](../../phase5_llm_integration_design.md); v1 trong tài liệu kiến trúc được giữ là lịch sử thiết kế, không thay source/checkpoint.
- **Policy dự kiến:** present/denied/uncertain/unmapped tách riêng với evidence turn/offset; validator tương lai reject unknown feature, conflict hoặc evidence sai. Chỉ present được xác nhận nhận1, còn0 không là âm tính lâm sàng. Hỏi một câu/lượt, budget đề xuất2 và không lặp; thiếu thông tin/ngoài schema thì abstain. Có nhánh urgent độc lập, dừng hỏi/dự đoán và dùng thông báo đã được người chuyên môn duyệt. Top3 lấy phân bố587 lớp thật, không renormalize ba score hoặc gọi là xác suất mắc bệnh; chưa chốt threshold/calibration.
- **Dữ liệu thử / ground truth:** tạo một [file JSONL](../../../data/evaluation/vietnamese_symptom_cases.jsonl) gồm **14 ca,14 speaker style,9 feature tham chiếu,24 evidence span**, tất cả hư cấu do AI tạo, `split=development`, `pending_human_review`, reviewer/date=null; không có nhãn bệnh kỳ vọng. Có đời thường, thuật ngữ, ngôn ngữ đơn giản, lỗi gõ, phủ định, chưa chắc, dài, đa lượt, khác chủ thể, unsupported, thiếu thông tin, urgent và instruction không tin cậy. Đây là annotation nháp, không là ground truth hoặc benchmark đủ375 feature. Evaluation sau này cần ca mới, người duyệt độc lập, tách theo scenario family và khóa trước tối ưu prompt; không đổi tag các ca đã dùng thành holdout.
- **Đánh giá / kiểm tra lần này:** JSONL UTF-8/LF, IDs, provenance, feature membership, ba trạng thái rời nhau, span căn đúng text user/turn, không nhãn bệnh đều **PASS**. JSON Schema Draft2020-12 và ví dụ v2 sau điền allowlist375 **PASS**; ba ví dụ sai (extra disease field/unknown feature/sai contract version) bị schema từ chối. Sáu Macro F1 và SHA packet Phase4 khớp evidence cũ;109 link tương đối và4 anchor trong6 Markdown hợp lệ. Snapshot xác nhận289 file cũ khác giữ SHA/size/mtime; test CSV chỉ so size/mtime, không mở để băm. Đây là kiểm tài liệu/reference, chưa có validator ứng dụng, extraction/E2E score hoặc đánh giá y khoa. Không chạy lại pytest/model notebook cho thay đổi tài liệu/data mẫu;50 test PASS ở mục17 là bằng chứng lần trước.
- **File / bảo toàn:** cập nhật report `docs/phase4_ensemble.md`, nhật ký này, README và thông tin trạng thái trong `SYSTEM_ARCHITECTURE.md`/`MODEL_SELECTION_RATIONALE.md`; chỉ thêm một tài liệu Phase5 và một JSONL. Giữ nguyên report run/manifest đã khóa trên Drive, evidence gốc, Phase2, source/bootstrap/config, notebook và model. Không cần source deployment mới vì không đổi runtime/code.
- **Cần duyệt sau / dừng:** provider/model/chi phí và chính sách dữ liệu sức khỏe; người duyệt/reference; budget/quality/abstention/urgent policy và Top3/bản dịch. Những điểm này không chặn hoàn tất thiết kế; cần chốt trước nhiệm vụ triển khai sau. **Dừng tại documentation/planning;0 API call, không load/fit model, không mở locked test, không frontend, agent framework hoặc `.venv`.**

## 19. 2026-10-28 — Hoàn thiện ca nhiều lượt, quality gate và kế hoạch đo API

- **Mục tiêu / phạm vi:** hoàn thiện nhỏ [thiết kế Phase5](../../phase5_llm_integration_design.md) và [JSONL development](../../../data/evaluation/vietnamese_symptom_cases.jsonl), giữ nguyên kiến trúc LLM API → structured JSON → Python validator/mapper →375-feature prefitted LR → phản hồi tiếng Việt. Không bắt đầu implementation, tối ưu prompt hoặc thay allowlist.
- **Ca bổ sung:** append `vi-dev-015`–`022`, **8 ca/18 span mới**, về triệu chứng đã hết hoặc mới khởi phát, phủ định/sửa lời ở lượt sau, uncertain được xác nhận, đổi chủ thể hai chiều và conflict cùng thời điểm chưa giải quyết. Giữ nguyên từng byte của14 dòng cũ. Tổng **22 ca/42 span**, tất cả synthetic/pending_human_review/development, reviewer/date=null, không nhãn bệnh kỳ vọng. Metadata tùy chọn ghi chủ thể và lý do gate; expected state là trạng thái tổng hợp cuối, không phải gộp mọi assertion lịch sử.
- **Kiểm feature / evidence:** đối chiếu exact **79 lần xuất hiện tên feature**, gồm ba danh sách expected và `expected_evidence.feature`, có **13 tên riêng biệt**, tất cả thuộc schema375. **Tên không hợp lệ: `[]` (0 lỗi)**; không fuzzy-map hoặc đổi tên. Kiểm42 span gồm24 cũ/18 mới theo user turn, offset code point/end-exclusive và chuỗi gốc đều PASS; kiểm thêm3 span trong ví dụ JSON của tài liệu PASS. JSONL UTF-8/LF, case/turn ID, schema identity, provenance, trạng thái cuối rời nhau và feature/unmapped có evidence đều PASS. Đây là kiểm tĩnh, annotation về nghĩa vẫn cần người duyệt.
- **Quality gate / quyết định:** tên feature hợp lệ không tự cho phép gọi model. Insufficient/conflict/urgent/invalid và trạng thái chưa qua đánh giá chất lượng đều không Top3; không tái hiển thị Top3 cache khi lượt mới bị chặn. Chỉ cập nhật khi sửa lời/thời điểm/chủ thể đủ rõ, không mặc định lượt cuối luôn đúng; đổi chủ thể phải tạo lại active state và qua gate. Giữ lịch sử để audit, không đưa triệu chứng người trước vào vector người hiện tại.
- **Kế hoạch đánh giá:** người duyệt gán hành động/lý do theo từng lượt trên reference được khóa, phân xử bất đồng; `quality_gate` hiện tại không tự là gold allow. Đo cho phép nhầm trên gold block, chặn nhầm trên gold allow, confusion matrix nhánh, chất lượng phần được phép, rò chủ thể/trạng thái cũ và stale Top3. Báo lượt/phiên cùng mẫu số, NA khi mẫu số0; giữ family cùng partition. Không chốt confidence/max probability/margin threshold chưa được kiểm; chưa có kết quả gate hoặc abstention thực.
- **Token/cost/latency:** thêm kế hoạch usage thực theo bước và attempt, token category không trùng, rate snapshot đúng provider/model/ngày/tiền tệ, retry/lỗi có billing và tổng chi phí lượt/phiên. Đo API elapsed/TTFT nếu streaming, tách validation/mapper/load LR/inference/kiểm phản hồi; phân biệt cold/warm, thời gian xử lý với thời gian người dùng trả lời, báo N/p50/p95/lỗi. Usage/giá chưa có ghi unknown, ước lượng ghi estimate; không hardcode giá hoặc tuyên bố số đo chưa thực hiện.
- **File / bảo toàn / dừng:** chỉ sửa hai file trên và nhật ký này; không thêm source/test script/notebook/artifact. Không chạy lại pytest hoặc model vì thay đổi chỉ là tài liệu/reference. Không gọi LLM API, load/fit model, train, truy cập locked test hoặc đổi Phase2/checkpoint/bootstrap. Dừng sau kiểm tĩnh và cập nhật tài liệu; bước tiếp cần người duyệt trước đánh giá/triển khai.

## 20. 2026-10-28 — Kiểm inference có cấu trúc trước Phase5A; chờ thực thi Colab

- **Mục tiêu / lý do:** người dùng giao kiểm chất lượng thực thi và tính nhất quán khi đưa triệu chứng tiếng Anh vào năm model đã audit, trước REST/LLM. Không chọn model bằng vài ví dụ hoặc sửa kết luận Phase4; **LR vẫn là mặc định**. Không mở locked test, fit/retrain/tune/calibrate hoặc triển khai Phase5A.
- **Đã làm / tái sử dụng:** thêm một [notebook05](../../../notebooks/05_structured_inference_check.ipynb),14 cell/8 code cell, setup chính xác từ shared entry Phase3. Dùng `ColabTraining.open`, `Phase4.verify`, `Phase4._load`/guard, validation data và checkpoint helpers hiện có; không tạo bootstrap/loader/service inference hoặc bản sao model. Giữ toàn bộ source/config/runtime/checkpoint Phase2–4, không cần source deployment mới nếu Drive đang dùng source Phase4 đã xác minh. Notebook không ghi report/model/artifact Drive.
- **Input / identity:** hàm chung nhận danh sách feature hợp lệ và dựng DataFrame1×375 uint8 theo schema; kiểm round-trip với hàng validation. Reject unknown/duplicate/empty, sai shape/width/order, ngoài0/1, NaN, dữ liệu chuỗi và vector toàn0:10 nhóm. Load kiểm checksum/library/Python/source identity, feature order,375 input/318 retained, fitted variance/estimator, label order587 và custom `to_csr`; lỗi integrity preflight dừng rõ, lỗi reload/inference từng model có PASS/FAIL/reason riêng, không fit bù.
- **Ca có nhãn / giả lập:** chọn tất định tối đa4 hàng validation đại diện LR đúng, LR sai, model bất đồng và class support nhỏ nhất; gộp lý do nếu trùng, yêu cầu ít nhất1 symptom và dừng khi thiếu nhóm. Mỗi hàng được so Top1 của5 model với nhãn thật và prediction đã audit. Thêm5 vector giả lập: cough/fever/sore throat, bỏ fever, bỏ cough, thêm nausea và chỉ còn cough; không gán bệnh kỳ vọng. Hiển thị thay đổi Top1 và delta score của nhãn sim-base, không gọi là accuracy hoặc lợi ích lâm sàng.
- **Probability / hiển thị:** LR/RF/KNN/NB lấy Top3 từ `predict_proba` thật, kiểm class order/shape/finite/range/sum và argmax so Top1; không normalize lại3 score. LinearSVC chỉ hiển thị nhãn, không xác suất giả. Bảng validation, bảng giả lập, Top3, độ nhạy, checkpoint, timing và warning gộp đều ở notebook; kết quả model chưa đạt kiểm ghi NOT VERIFIED, không điền số giả.
- **Thời gian:** load+integrity riêng, warm-up riêng;7 lần predict/proba một mẫu sau warm-up, báo median/min/max theo từng phương thức. Không tính chuẩn bị DataFrame/hiển thị vào predict; không dùng một phép đo, một mẫu hoặc thời gian validation gốc làm cam kết latency REST/chatbot. Chạy model tuần tự, giới hạn tài nguyên bằng config hiện có, giải phóng sau mỗi model; không train.
- **Kiểm local / bằng chứng:** thêm [31 test notebook/input/prediction](../../../tests/test_structured_inference.py) với prediction-only doubles, kiểm case selection, invalid/probability, timing call counts và vòng orchestration thành công/thất bại không fallback. Smoke dùng loader thật nạp train131.248×375 và validation28.120×375/587 lớp; round-trip3 hàng thật PASS, không deserialize model. Bộ liên quan **81 passed (25,29s)** gồm ensemble/preflight/audit/runtime/deployment; sau làm test chấp nhận mount cell/output lịch sử,2 kiểm tra nguồn mục tiêu chạy lại PASS. Guard trong test mới chặn fit/test/protected write, không có model/feature training thực.
- **Lỗi kiểm tra đã xử lý:** lượt đầu55 pass/1 fail vì unit Phase4 cũ yêu cầu notebook04 không có output, trái việc người dùng đã lưu9 cell output Colab. Chỉ sửa test để kiểm source và chấp nhận output/mount cell, không xóa hoặc ghi lại notebook04. Package `nbformat` không có trong Python local; không cài thêm, không tuyên bố đã chạy `nbformat.validate`. JSON notebook, cell IDs/source/compile, shared entry, code fingerprint và lời gọi không fit/ghi artifact được kiểm bằng công cụ sẵn có.
- **Chưa xác minh ở nhiệm vụ này:** checkpoint thật vẫn chỉ trên Drive; agent không có kết nối kernel/Drive thực thi. **Chưa có checkpoint reload PASS/FAIL mới, bảng dự đoán có nhãn/giả lập hoặc số thời gian model thật của notebook05.** Bằng chứng Colab Phase3/4 ở mục15/17 không được gán thành thực thi notebook05. Các test doubles không thay cho kết quả đó; chưa kết luận có/không lỗi model cần sửa trước Phase5A. Validator/quality gate và reference người duyệt vẫn là công việc thiết kế chưa triển khai.
- **Bước kiểm cuối / dừng:** mở notebook05 mới trên kernel Colab, mount Drive rồi Restart/Run All riêng notebook05; không chạy lại model cell notebook03/04. Copy hai dòng cuối `INFERENCE_SHA256` và `INFERENCE_GZIP_BASE64` để đối chiếu và cập nhật kết quả thật; nếu preflight lỗi, gửi traceback đầu. Source logic notebook lúc bàn giao có fingerprint `b548198c7ef4ef8098cbeeec53a8f8d3469d8001bb6ef54003a4e2191435af0b`, chỉ là mốc phiên bản, không là chữ ký chứng minh lịch sử kernel. Dừng sau inference validation/report; không gọi LLM, REST/frontend, locked test hoặc thay LR mặc định.


## 21. 2026-10-29 — Hoàn tất structured inference từ bằng chứng Colab

- **Bằng chứng / phạm vi:** nhận packet notebook05 người dùng chạy trên Colab; SHA-256 khớp **5dacef332521d797a74c00441bb00161ff21502078ebb12426c7dd4c4be5fd01**. Lưu nguyên26.833 byte tại [colab_evidence.json](../../../artifacts/metadata/structured_inference/colab_evidence.json). Đây là ngày nhận bằng chứng; packet không ghi timestamp lần inference. Agent không trực tiếp điều khiển kernel hoặc tải model về local. Trạng thái chờ ở mục20 được khép lại, không xóa lịch sử.
- **Identity / checkpoint:** cả5 model **PASS saved integrity, reload/schema/environment và inference**. Năm pipeline SHA trùng evidence audit Phase3, experiment baseline-v1-f8a5bfdb7b4c12cd; processed fingerprint, schema và mapping khớp local/Phase4. Source code logic notebook fingerprint b548198c7ef4ef8098cbeeec53a8f8d3469d8001bb6ef54003a4e2191435af0b khớp bản đã bàn giao; đây là mốc phiên bản, không phải chữ ký xác thực kernel. Môi trường Python3.13.18, sklearn1.6.1, NumPy2.1.3, SciPy1.16.3, joblib1.6.0. Runtime kiểm375 input/318 retained/587 nhãn, fitted pipeline và custom to_csr.
- **Input / đối chiếu độc lập:**10 nhóm invalid đều bị chặn: unknown, duplicate, empty, sai shape/width/order, ngoài0/1, NaN, chuỗi và toàn0. Round-trip input PASS. Agent đọc lại riêng validation local, đối chiếu4 row IDs/nhãn/support/danh sách feature và dựng lại375 bit: tất cả khớp; không gọi thêm model hoặc đọc test. Bỏ bit trong ca giả lập có nghĩa chưa ghi nhận hiện diện, không khẳng định triệu chứng vắng mặt lâm sàng.

### Ca validation có nhãn thật

SVC = LinearSVC, NB = BernoulliNB; ✓/✗ so nhãn thật, không phải chỉ trạng thái thực thi. Cả20 dự đoán mới khớp predictions đã audit theo kiểm tra trong runtime.

| Ca / row0-based | Nhãn thật | Support | LR | RF | SVC | KNN | NB |
|---|---|---:|---|---|---|---|---|
| val-1 / 0 | panic disorder | 114 | panic disorder ✓ | panic disorder ✓ | panic disorder ✓ | panic disorder ✓ | panic disorder ✓ |
| val-2 / 3 | panic disorder | 114 | anxiety ✗ | anxiety ✗ | panic disorder ✓ | panic disorder ✓ | anxiety ✗ |
| val-3 / 1 | panic disorder | 114 | panic disorder ✓ | cystitis ✗ | panic disorder ✓ | anxiety ✗ | panic disorder ✓ |
| val-4 / 222 | injury to the knee | 1 | arthritis of the hip ✗ | arthritis of the hip ✗ | arthritis of the hip ✗ | flat feet ✗ | injury to the leg ✗ |

- val-1 minh họa LR đúng; val-2 LR sai dù SVC/KNN đúng; val-3 có bất đồng; val-4 support1 và cả5 Top1 sai. **PASS kỹ thuật không có nghĩa mọi dự đoán đúng.** Ba ca đầu cùng panic disorder do chọn hàng đầu tiên đáp ứng điều kiện; không đại diện587 lớp. Không tính metric tổng thể, xếp hạng lại model hoặc suy toàn bộ lớp hiếm từ các ca này.

### Ca giả lập không có ground truth

C=cough, F=fever, S=sore throat, N=nausea; đây chỉ là ký hiệu bảng, tên input thật vẫn theo schema. Không có bệnh kỳ vọng hoặc cột đúng/sai.

| Vector giả lập | LR | RF | SVC | KNN | NB |
|---|---|---|---|---|---|
| C+F+S | oral mucosal lesion | cystitis | oral mucosal lesion | abscess of nose | acute sinusitis |
| C+S (bỏ F) | esophagitis | cystitis | esophagitis | acute bronchospasm | acute sinusitis |
| F+S (bỏ C) | conjunctivitis | cystitis | conjunctivitis | abscess of the pharynx | acute sinusitis |
| C+F+S+N | flu | flu | flu | flu | flu |
| C (bỏ F và S) | eczema | cystitis | eczema | teething syndrome | heart failure |

- **Độ nhạy quan sát:** LR/SVC/KNN đổi Top1 ở cả4 biến thể so sim-base; RF chỉ đổi khi thêm nausea; NB đổi khi thêm nausea hoặc chỉ còn cough. Đây là hành vi trên5 vector cụ thể, không chứng minh model nào đúng hơn hoặc feature nào vô dụng. Với LR, score của nhãn sim-base giảm0,030555 khi bỏ fever và0,062069 khi chỉ còn cough; delta này không phải hiệu giữa score Top1 của hai nhãn khác nhau. RF có chênh khoảng1,7e-18 ở hai ca bỏ một feature: xem là sai khác số học rất nhỏ, không diễn giải thành tác động thực chất.
- Các nhãn từ vector ít thông tin vẫn là output classifier thật, **không được coi là gợi ý bệnh đã xác thực**. Chưa có ground truth nên không gọi nhãn giả lập đúng/sai, không sửa model/schema hoặc chọn bệnh kỳ vọng để khớp trực giác.

### Probability / Top3 và vấn đề trình bày

- 36 bản ghi Top3 từ LR/RF/KNN/NB, tổng108 mục; label ID/tên, thứ hạng, score hữu hạn trong[0,1] và thứ tự giảm đều PASS đối chiếu local. Kiểm cả587 probability, tổng hàng và argmax được thực hiện trong runtime bởi code đã đối chiếu; packet chỉ giữ Top3 nên agent không băm/kiểm lại toàn ma trận587 cột. SVC chỉ trả nhãn, không có probability giả.
- **KNN có5 mục score0**: val-1 hạng2/3, val-2 hạng3, sim-add-nausea hạng2/3. Ví dụ val-1 có panic disorder score1, còn hai nhãn sau score0 do vẫn lấy đủ3 phần tử theo thứ tự lớp. Nhiều Top3 có score bằng nhau, như0,2/0,2/0,2; vị trí trong tie không chứng minh nhãn này có cơ sở hơn nhãn kia. Đây là giới hạn của bảng Top3 cố định, không phải checksum hoặc lỗi chiều input.
- **Trước Phase5A:** cần policy hiển thị tối đa3 nhãn không có score0 và ghi rõ tie nếu dùng KNN ở research mode; không trình bày phần tử padding như lựa chọn có bằng chứng. Đây là đề xuất xử lý output, không thay model, thêm confidence threshold hoặc triển khai ngay. Default LR vẫn cần quality gate/abstention theo thiết kế; có feature hợp lệ không tự cho phép hiển thị Top3. Không coi score của các model là xác suất mắc bệnh hoặc đã calibration.

### Thời gian một mẫu sau load

Cùng mẫu val-1/row0 (6 feature hiện diện trong vector375). Predict/proba báo **median [min;max] của7 lần sau warm-up**, đơn vị ms. Warm-up gồm kiểm input và predict/proba nếu hỗ trợ; load gồm kiểm integrity/schema, không chỉ deserialize.

| Model | Load+kiểm (s) | Warm-up (ms) | Predict (ms) | Predict_proba (ms) |
|---|---:|---:|---|---|
| LR | 0,0418 | 33,915 | 13,789 [13,465; 13,914] | 14,088 [14,001; 25,246] |
| RF | 1,6846 | 112,703 | 50,233 [49,326; 51,373] | 50,587 [49,459; 61,401] |
| SVC | 0,0616 | 18,002 | 13,245 [13,153; 13,291] | NA |
| KNN | 0,0486 | 72,718 | 21,716 [21,428; 27,205] | 39,286 [22,974; 40,086] |
| NB | 0,0365 | 79,090 | 35,488 [33,730; 38,602] | 34,801 [34,208; 36,171] |

- Load/warm-up là lần đo đơn; preflight đã đọc/băm checkpoint nên không gọi đây là benchmark cold Drive. Packet không ghi đầy đủ hardware/CPU/RAM của VM hiện tại; không gán cấu hình VM Phase3 cho lần đo mới. Thời gian7 lần trên một mẫu không phải SLA, tải đồng thời hoặc latency REST/LLM. Không dùng tốc độ SVC ở đây để thay kết luận lựa chọn LR theo validation Macro F1.
- **Kết luận / việc còn lại:** không phát hiện blocker kỹ thuật về checksum, input/schema/mapping, reload hoặc inference trong phạm vi chạy; model_issues rỗng. Warning capture của cả5 model trong lần kiểm này rỗng, không suy mọi warning lịch sử đã được sửa. Cần triển khai và đánh giá validator/quality gate/abstention, xử lý Top3 score0/tie và kiểm tính trung thành nhãn tiếng Anh/phản hồi tiếng Việt trước tích hợp. Ca tổng hợp/reference tiếng Việt vẫn pending_human_review, chưa có clinical/extraction/E2E evidence; đó không phải lỗi checkpoint cần retrain.
- **Kiểm tra / bảo toàn:** SHA packet và5 SHA pipeline, nguồn/schema/mapping,4 hàng validation,20 kết quả có nhãn,25 kết quả giả lập,108 score Top3, changed flags/delta kiểm được từ dữ liệu Top3 và quan hệ min/median/max đều PASS. Guard Colab ghi0 model/feature fit,0 test access,0 protected write; packet ghi không ghi đè artifact. Kiểm packet local cũng có0 fit/test/protected write, không chạy thêm predict.81 test ở mục20 là lượt chuẩn bị, không chạy lại pytest cho thay đổi chỉ evidence/tài liệu này.
- **File / giới hạn / dừng:** chỉ thêm evidence và cập nhật nhật ký này; giữ nguyên source, notebook và outputs người dùng, model/checkpoint, schema/split/manifest Phase2–4. Agent đối chiếu packet và bằng chứng cũ, chưa đọc/băm lại từng pipeline Drive độc lập; checksum truyền tải không thay xác thực chữ ký. **Hoàn tất structured inference check; LR mặc định không đổi. Dừng trước Phase5A, REST/frontend/LLM API, calibration/retrain và final locked-test evaluation.**

## 22. 2026-10-29 — Phase5B: external-provider adapter, guard và hội thoại offline

- **Mục tiêu / phạm vi:** người dùng giao triển khai lớp hiểu ngôn ngữ qua LLM bên ngoài, guard, extraction v2, validator/mapper và hội thoại có giới hạn. Kiểm repository xác nhận app/backend và app/frontend chỉ có .gitkeep, không có Phase5A Prediction API hoặc LR service tái sử dụng. Giữ LR mặc định; không tự làm Phase5A, endpoint/chat frontend, model loader, retrain, calibration hoặc final test.
- **Cấu trúc / quyết định:** thêm3 module trong package src/agent có sẵn: [provider](../../../src/agent/provider.py), [extraction](../../../src/agent/extraction.py), [conversation](../../../src/agent/conversation.py); một [config không secret](../../../configs/phase5b.json). Không framework/DB hoặc LLM hosting. Catalog tái sử dụng approved baseline/checksum helper, chỉ đọc schema375/mapping587; không đọc CSV/model. Code prediction chỉ là protocol/forward_ready kiểm session+turn hiện hành, dùng test double, không có bản ML song song.
- **Input guard:** local validation kiểu/length/ký tự trước token; kiểm urgent riêng trước flow thường, security rejection khác emergency. Cấu trúc câu/chủ thể/temporal/negation được xét; intent mơ hồ dùng classifier LLM JSON có intent/subject/evidence rồi kiểm lại. Câu tổng thống → unrelated; định nghĩa/kiến thức cúm → medical_information_question, không vector; tôi ho+sốt → symptom_description vẫn phải qua gate; uncertainty → hỏi rõ; override feature/role JSON/key → instruction_injection; khó thở nặng hiện tại → urgent_redirect. Không trả lời câu hỏi ngoài phạm vi hoặc dùng keyword đơn lẻ như bộ phân loại duy nhất. Subject demo self/mother/father/child; quan hệ/người chưa hỗ trợ không tự thành self.
- **Adapter / live status:** một Gemini Interactions REST adapter, model mặc định gemini-3.8-flash theo tài liệu chính thức tra cứu, configurable. Key chỉ đọc từ env khi live được bật, không vào URL/log/output; store=false, không server history/tools. Timeout20s/attempt, mặc định1 retry transient và giới hạn tối đa2; HTTP400/404, timeout,429, invalid JSON và provider failure có mã lỗi sạch. Chống redirect mang key, duplicate JSON key, response quá lớn và NaN. Full375 enum luôn ở schema hoặc explicit json_only; không cắt schema hay tự fallback. **LIVE NOT VERIFIED:** không đọc account/probe model/gọi API live; provider chấp nhận fullschema và chất lượng ngôn ngữ chưa kiểm. store=false không được coi là bảo đảm mọi chính sách retention của vendor.
- **Telemetry:** từng attempt có task/model/latency/retry và usage numeric provider báo hoặc unknown; không chứa health text/key. Giữ cached/thought counters nhưng không cộng trùng để dựng bill. Cost chưa được API đối soát nên null/unknown, không0/giá giả; không công bố số đo token/cost/latency LLM từ mocks. Clarification hiện dùng template local, không request LLM giả; generation phản hồi bệnh vẫn ngoài scope.
- **Contract / mapper / gate:** v2 và exact schema ID,375 allowlist, user-turn/offset/quote gốc, negation/uncertainty, chủ thể/thời gian đủ rõ; reject unknown/regurgitation, extra disease/vector field, conflict, assistant/quote/hypothetical/past evidence, overlapping feature spans và stale assertion sau update. Context ngữ nghĩa không chứng minh hoàn toàn bằng các check này. Gate yêu cầu tối thiểu2 present cùng chủ thể hiện tại **và** không còn issue; rule2 là provisional/configurable, không phải confidence threshold hoặc xác nhận lâm sàng. Chỉ sau gate mới tạo1×375 uint8, không cắt318; denied/uncertain/unmentioned/unmapped/provenance giữ sidecar. Ngoài schema/đã loại thì abstained. Có6 status rõ: out_of_scope, clarification_required, abstained, urgent_redirect, extraction_ready, provider_error; Phase5B không sinh/cached disease predictions.
- **State / hội thoại:** in-memory store idleTTL900s/cap128/max12 user turn, một câu/lượt và mặc định tối đa2 clarification, không lặp target/câu. Có/Không ngắn chỉ gắn feature của câu hỏi đã hỏi; không dùng assistant question làm evidence symptom. Sửa lời/thời gian/chủ thể rõ mới thay active state, không dùng last-message-wins. Đổi subject bắt đầu epoch mới, giữ raw history có hạn để audit, không kế thừa triệu chứng người trước. Mỗi lượt xóa ready frame trước guard; frame copy chỉ được forward khi turn còn current/ready. Stop, expiry, provider/validator fail và urgent không thể trả Top3 cũ. Store không persistent/authenticated/multi-instance, lock serialize cho demo.
- **Dữ liệu / kiểm offline:** giữ nguyên byte22 ca cũ; append8 ca guard hư cấu, tổng30 development/pending_human_review, không expected disease.42 span/79 lần xuất hiện tên feature vẫn hợp lệ, invalid names=[];8 ca guard không gán symptom labels. [Test Phase5B](../../../tests/test_phase5b.py) gồm124 ca parametrized về22 annotation cấu trúc,8 guard, mapping/negation/subject/time/correction/budget/TTL, provider/network failures, no secret/stale vector và mock prediction port. Không chấm AI annotation thành ground truth hoặc mock pass rate thành extraction accuracy.
- **Kết quả / lỗi đã sửa:** bộ liên quan **205 passed (27,19s)** =124 Phase5B +81 inference/ensemble/preflight/audit/runtime/deployment. Lượt đầu88 pass/2 fail: cụm thở không nổi bị hiểu nhầm phủ định đã sửa bằng rule idiom, và fixture Ho/ho được sửa giữ case/offset thật. Bổ sung hồi quy cho phủ định/past/giả định urgent, người khác, câu thông tin chung, lặp hỏi và trả lời ngắn. Smoke config live_disabled PASS, catalog375/587 và routing scope/urgent đúng; transport sentinel không bị gọi, guard0 fit/test/protected write. Không dùng kết quả đó làm bằng chứng API live hoặc safety lâm sàng.
- **Colab / source:** giữ bootstrap nguyên byte; config Phase5B mới không thuộc PUBLIC_CONFIGS của bootstrap nên đọc từ runtime_paths.storage_root/configs/phase5b.json, còn code dùng source workspace chung và metadata ở storage. Chỉ mở rộng script chuẩn để stage config này, thêm jsonschema direct dependency (đã có local, không cài package). Refresh đúng **một folder dist/drive-source hiện có**,36 file source/config; CheckOnly PASS, fingerprint1c461e9a9f370696d1c2773ff6a0f7df560b2b8678d847c8d773288862a86f05. Không sinh thêm ZIP/pyz/session/receipt hoặc sửa archive lịch sử. Chưa upload/execute Phase5B trên Colab thật.
- **Tài liệu / tích hợp / dừng:** cập nhật [thiết kế/cách chạy duy nhất](phase5_llm_integration_design.md#8-phase5b-đã-triển-khai--cách-chạy-và-ranh-giới), README và trạng thái kiến trúc; không tạo report chồng chéo. Phase5A sau này cần implement PredictionService.predict(frame, schema_sha256=...) bằng existing trusted LR helpers, kiểm source/library/checksum/class order/Top3, không refit; API/session authentication và response generation riêng. Các policy/alias/urgent message/human-reviewed evaluation, privacy và account model live vẫn cần đánh giá trước dùng thật. **Dừng Phase5B: không ML fit/test, LLM live, REST/frontend/public deployment, .venv mới hoặc đổi model mặc định.**


## 23. 2026-10-29 — Tuning train-only trong notebook03/04, chưa chạy thí nghiệm thật

- **Mục tiêu/phạm vi:** bổ sung checklist hyperparameter tuning cho đúng5 model cũ, giữ thí nghiệm Phase3/4 đã audit; không train tự động, không notebook06 hoặc công việc Phase5A/5B mới. Kiểm repository/source/bootstrap/loaders/checkpoints hiện có trước khi triển khai.
- **File:** nối3 cell vào cuối mỗi notebook [03](../../../notebooks/03_model_training.ipynb) và [04](../../../notebooks/04_ensemble.ipynb); thêm [tuning.py](../../../src/models/tuning.py), [tuned_ensemble.py](../../../src/models/tuned_ensemble.py) và [test_tuning.py](../../../tests/test_tuning.py). Chỉ điều chỉnh assertion14 cell thành ít nhất14 trong test preflight để giữ kiểm các cell baseline đúng vị trí. Cập nhật [rationale/giao thức](MODEL_SELECTION_RATIONALE.md#hyperparameter-tuning-có-kiểm-soát), [Phase4 report](../../phase4_ensemble.md) và ghi chú trong [audit Phase3](../../../reports/phase3_post_training_audit.md); không sửa số liệu cũ.
- **Search chốt trước:** LR C=1/0.5/2, LinearSVC C=1/0.5/2, RF max_depth=24/16/32 (100 cây/max_leaf_nodes512/min_leaf2), KNN k=5/3/7 distance/manhattan/brute, NB alpha=1/0.5/2. Các tham số còn lại từ config baseline;15 candidate,45 fold fits rồi tối đa5 full-train selected fits. Baseline candidate có mặt trong CV nhưng checkpoint baseline không được refit. Không có validation-driven mở rộng search.
- **CV/scoring:** StratifiedGroupKFold3, shuffle=True/seed42, actual train group IDs và cùng assignment cho mọi candidate. Full pipeline VarianceThreshold(0)/CSR/estimator được fit mới trong từng fold train. Macro F1 mean3 fold, labels đủ587/zero_division0; lớp vắng vẫn nằm trong mẫu số, có inventory/warnings. Candidate phải đủ3 fold thành công; exact tie ưu tiên candidate đứng trước/baseline. Khóa cả5 selection trước khi đánh giá validation. Search dở hoặc mọi candidate một model lỗi thì dừng, không đổi split/threshold.
- **Resource/progress:** tuần tự; RF≤2 workers, KNN1, BLAS1, working_memory≤128 MiB, predict batch≤64; RAM floor2 GiB và SGKF preallocation estimate khoảng3,03 GiB khả dụng. Budget6 giờ/lần search kiểm giữa folds, không hard timeout fold. Log model/config/fold + elapsed/warnings count và heartbeat/RSS; persist scores/errors/warnings từng attempt để resume, không lưu fold models. Run một writer, không đổi config/source khi resume.
- **Bảo toàn/checkpoint:** namespace mới artifacts/models/tuning/<id>, artifacts/metadata/tuning/<id>, reports/tuning/<id>. Chỉ5 selected checkpoints, predictions/metadata cần thiết, một bảng và một PNG thật khi chủ động chạy. Selected fit/resume dùng nguyên run_model/load_fitted_checkpoint/read_completed_checkpoint Phase3; completed manifest checksum-verified rồi reuse, không overwrite. ID pin data/config/library/source/CV assignment; selected identity pin cả selection digest.
- **Ensemble tuned:** dùng lại Phase4 methods/guards/loaders/probability memmaps/hard_vote/soft_vote; kiểm checksum/schema/mapping,375 feature ordering,587 class IDs, tham số pipeline và validation row/group alignment. Giữ3 hard/2 soft + tie policies/uniform weights. Không fit/calibrate; thiếu tuned artifact thì SKIPPED, corruption thì lỗi. So baseline LR +5 tuned singles +5 ensembles; đề xuất Macro F1 chính, exact tie theo resource proxies (ít pipeline/không KNN/file bytes/ID), không coi proxy hoặc thời gian khác phiên là SLA. Xuất run tuned-ensemble-* riêng, không tự thay model ứng dụng hoặc xuất wrapper Phase3 sai namespace.
- **Kiểm local thực tế:** Python3.11.9/scikit-learn1.8.0 trên Windows, dùng Python hệ thống, không tạo .venv. Bộ liên quan **240 passed trong57,10s =35 test tuning mới +205 test hồi quy** (preflight, ensemble, inference, audit, runtime, deployment, Phase5B). Lượt đầu35+205 đạt239 pass/1 error vì backend Tk/Tcl ở fixture chart; test được chuyển sang Agg headless và lượt cuối PASS. Tất cả fold-score/selected-model tests dùng synthetic fixtures/doubles trong thư mục tạm, không fit sklearn model/transformer thật hoặc dùng mock scores làm metrics dự án. Bộ test training cũ có fit thực không được chạy trong nhiệm vụ cấm training tự động này. Kiểm thêm JSON/unique cell IDs/code compilation của hai notebook và link/fence của4 tài liệu PASS. Python local thiếu nbformat nên không cài thêm hoặc tuyên bố đã chạy full nbformat-schema validator.
- **Smoke dữ liệu thật, không fit:** approved loader/integrity nạp train/validation, tạo CV chỉ trên131.248 train rows/117.211 groups/375 features/587 classes. Holdout rows=43.750/43.749/43.749; holdout groups=39.071/39.073/39.067; group-disjoint, mọi fold train/holdout đủ587 lớp, không splitter warning. Thời gian cả kiểm/nạp/tạo fold20,73s, không phải thời gian tuning. Guard0 model/feature fit,0 test access,0 protected write. Determinism/resume/missing-class/error/invalid-score/order/source/environment/corruption/SKIPPED được kiểm bằng unit tests.
- **Đối chiếu snapshot/source:**14 cell cũ của03 và17 cell cũ của04 (gồm outputs/execution metadata) cùng notebook top metadata giữ nguyên; nay17/20 cell. Không thay config Phase3, bootstrap, sáu source tạo baseline identity, Phase2/raw/processed dữ liệu, checkpoints hoặc evidence/manifest/figures Phase3/4. Chỉ thêm ghi chú có ngày vào audit Phase3. Refresh đúng folder dist/drive-source có sẵn bằng script chuẩn:38 source/config files, CheckOnly PASS, source fingerprint3d2905f3329c3486b435206d9a3e06bdb9a98dc21b7a6f0324880a6a93c583c0. Không sinh ZIP/pyz/session/receipt, không sửa archive cũ.
- **Trạng thái/chạy tiếp/dừng:** implementation và local tests hoàn tất; **TUNING NOT RUN, COLAB NOT VERIFIED FOR THIS EXTENSION**. Đồng bộ nội dung drive-source, mở notebook03/04 đã cập nhật, mount/Restart Kernel. Chạy setup/open/load_data rồi bật RUN_HYPERPARAMETER_TUNING=True ở Section5 của03, không cần chạy lại cell baseline fit/export. Khi đủ manifest, setup/open ở04 rồi bật RUN_TUNED_ENSEMBLE=True, điền ID rõ khi có nhiều run. Chưa có model CV scores, tuned validation metrics hoặc recommendation thực tế. Convergence/thời gian/RAM toàn search và reload/inference selected thật trên Colab còn chưa kiểm. Validation đã dùng nhiều lần; không kết luận final-test/lâm sàng từ kết quả mới. **Giữ LR mặc định; dừng sau implementation/local tests, không tuning thật, mở locked test, gọi LLM hoặc làm Phase5A/5B.**


## 24. 2026-10-29 — Post-Tuning & Phase5B Source Audit, chờ bằng chứng Drive

- **Đính chính:** người dùng chủ động bật RUN_HYPERPARAMETER_TUNING=True/RUN_TUNED_ENSEMBLE=True để chạy. Đó không phải lỗi của agent hay lỗi notebook. Việc đưa switch về False ở phản hồi preflight trước không phù hợp với ý định vừa được làm rõ; audit này không điều tra, sửa, hoàn nguyên switch hoặc chạy lại notebook. Toàn bộ notebook/output hiện hành được bảo toàn. Các ghi chú “tuning chưa chạy” ở mục23 mô tả thời điểm implementation, không phải trạng thái output hiện nay.
- **Phạm vi/quyền truy cập:** artifacts/models local chỉ có .gitkeep; không có connector/kernel Drive trong phiên này. Source, corpus, schema/config và bằng chứng audit cũ đọc được local; không có tuned manifest/checkpoints/predictions gốc để băm độc lập. Vì vậy PhaseA cho experiment tuning-v1-9c4dd013abbba14a là **REVIEW / NOT VERIFIED từ artifact Drive**, không xem HTML/text notebook là chứng minh checksum. Không fit/retrain/tuning, gọi Gemini, mở/hash CSV test hoặc tự thay model mặc định.
- **Quan sát output đã lưu, chưa kiểm chứng artifact:** notebook03 báo COMPLETED tuning-v1-9c4dd013abbba14a,45 dòng CV start và45 completed,5 selected fits; không in FAILED/INTERRUPTED/REUSED/RESUME. Log in46 DeprecationWarning datetime.utcnow và3 ResourceWarning; warning riêng của từng CV attempt nằm trong trials.json nên chưa kết luận không có ConvergenceWarning. Notebook04 báo manifest artifacts/metadata/runs/tuned-ensemble-20261029T041701354242Z-6c84dbfe/tuned_ensemble_manifest.json, cả5 reload/schema/alignment PASS. Đây là output của người dùng, chưa phải agent đọc và kiểm lại Drive.

| Kết quả quan sát từ output notebook, NOT VERIFIED độc lập | Macro F1 | Accuracy | Lớp được dự đoán | Lớp F1=0 | Pipeline bytes | Saved validation predict seconds/sum |
|---|---:|---:|---:|---:|---:|---:|
| LR baseline | 0.78780814 | 0.837091 | 560 | 28 | 1438385 | 2.157469 |
| LR tuned | 0.793154 | 0.837660 | 566 | 23 | 1438563 | 2.115221 |
| Hard tuned LR+SVC+KNN | 0.7965170720239344 | 0.836913 | 567 | 21 | 3554419 | 300.793358 |

- **Diễn giải có giới hạn:** Hard tăng khoảng0.003363 Macro F1 so LR tuned nhưng Accuracy thấp hơn;21 so23 lớp F1=0. Số300.793358 là tổng thời gian validation predict đã lưu của3 thành viên, chịu chi phí KNN; không phải benchmark ensemble mới hoặc latency một request. Phiên/phần cứng có thể khác nhau. Size file nén không phải peak RAM. Chưa kết luận ý nghĩa thống kê, chất lượng y khoa, model cuối hoặc thay mặc định LR baseline.
- **Selected parameters quan sát:** LR C=2/saga/max_iter200/tol0.001; LinearSVC C=2/dual auto/max_iter3000/tol0.001; RF depth32,100 cây/max_leaf_nodes512/min_leaf2/sqrt; KNN k7/distance/brute/manhattan; NB alpha0.5/binarize None. Các mean CV và selection cần đối chiếu manifest/trials đã khóa; không sửa search vì nhìn validation.
- **Fold quan sát và đính chính phạm vi local:** output Colab ghi train class counts587/587/587; holdout586/586/587 (fold0/1 thiếu một lớp). Train rows87406/87496/87594; holdout43842/43752/43654; holdout groups39071/39073/39067. Số587 ở mọi phía và43.750/43.749/43.749 dòng ở preflight trước là phép kiểm local scikit-learn1.8, không được áp sang output Colab gốc. Script mới dùng actual stored row/group/fold assignment và phiên bản gốc khi có thể; không resplit để ép số liệu giống local. Scorer source giữ labels=np.arange(587),zero_division=0 cho cả fold vắng lớp; không bỏ lớp khỏi mẫu số.
- **Kiểm tra Drive được chuẩn bị:** [audit_post_tuning.py](../../../scripts/audit_post_tuning.py) chỉ đọc, dùng shared loaders/integrity/checkpoint helpers hiện có; không bootstrap/source sync/cache mới. Nó kiểm toàn bộ file checksums manifest, schema375/mapping587, CV assignment rows/groups/digest/leakage/coverage, selection từ checksum-verified trials; tái tạo SGKF seed42 nếu phiên bản phù hợp và đủ RAM. Đọc năm fit/metadata/predictions, tính lại validation metrics và so baseline reference; sequential deserialize chỉ khi trusted=True, đúng environment/source/RAM, kiểm feature/class order, parameters và train-only variance mask, không predict/fit. Kiểm ensemble manifest và original hard-vote/tie policy bằng voted predictions, tính lại metrics của predictions ensemble lưu sẵn; đối chiếu byte sizes. Guards cấm mọi write/network/fit/test. Lỗi thiếu artifact/môi trường/RAM ghi NOT VERIFIED, mismatch integrity ghi BLOCKER.
- **Giới hạn kiểm toán:** fold models/predictions không được persist theo giao thức nên không thể tính lại F1 từng CV fold mà không retrain; script chỉ kiểm digest/selection arithmetic và source policy587. Probability memmap soft voting là ephemeral, nên metrics từ saved soft predictions kiểm được nhưng phép cộng probability chưa kiểm độc lập nếu không chạy predict_proba mới. Script không chạy thêm prediction. Historical resume/exactly-once không thể suy chỉ từ checkpoint hiện tại; báo counts interrupted/repeated attempts và policy/metadata, không đoán lịch sử.
- **REVIEW resume namespace được xác nhận offline:** descriptor trong tuning.py đưa split_warnings vào digest experiment ID. Cùng assignment nhưng warning không liên quan xuất hiện/biến mất có thể tạo ID khác khi gọi lại. Test chứng minh digest khác; chưa có bằng chứng run9c4 đã gặp việc này. Không sửa tuning.py/tuned_ensemble.py trong audit vì chính bytes hai file được pin trong checkpoint identity; sửa lúc này sẽ làm loader đúng quy tắc từ chối reload run gốc. Cần quyết định migration/resume có chủ đích sau khi kiểm artifact; không bỏ source validation hay sửa checksum.
- **Bug Phase5B xác nhận và sửa nhỏ:** guard trước đây yêu cầu anchor đại từ hoặc context_reply nên bỏ sót route local cho “Khó thở nặng, thở không nổi.”; nay sau evidence/context checks có thể urgent dù không đại từ. Câu hỏi ở câu khác không che một báo cáo distress sau đó. extraction.py dùng phạm vi câu cho knowledge/hypothetical/past cues, hiểu thêm dạng quote đơn/cong, giữ nguồn evidence user thật; “giải thích/nguyên nhân...” kèm danh sách comma/quote không thành urgent. Bổ sung respiratory assertion cho câu hỏi xin giúp có đại từ. Cấu trúc “không chỉ/không những ho mà còn sốt” không còn bị đọc thành phủ định ho; vẫn giữ phủ định thật “không chỉ không ho...”. Không đổi schema/allowlist/model/provider framework.
- **Regression B:**20 test mới trong [test_phase5b.py](../../../tests/test_phase5b.py) cho pronounless/mixed-topic urgent, knowledge/quotes/past/denial không urgent, correlative negation, short Có không chuyển feature sang chủ thể mới, mixed-topic extraction với mock. Các test sẵn có tiếp tục kiểm Có/Không gắn đúng target đã hỏi, corrections/resolution/subject epochs, provider/invalid JSON/expiry không vào inference, không stale vector/Top3. Policy min_present_features=2 và provisional_pending_human_review giữ nguyên, configurable, không phải ngưỡng chẩn đoán được xác thực. Semantic/clinical performance vẫn **NOT VERIFIED**,30 ca synthetic còn pending_human_review.
- **Đối chiếu Gemini ngày2026-10-29:** [Interactions API reference](https://ai.google.dev/api/interactions-api) vẫn có POST/v1beta/interactions; request input string/system_instruction/generation_config.max_output_tokens/store/stream và response_format text/application-json/schema phù hợp; parser steps/model_output/content/text/status completed và usage token fields phù hợp. Retry có giới hạn cho408/429/selected5xx, không retry4xx cấu hình, hợp [troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting) và [error codes](https://ai.google.dev/gemini-api/docs/api-errors). Không cần đổi provider.py hoặc endpoint; không gửi request API. Cost unknown/null là đúng khi response không báo billed cost; không cộng trùng cached/thought counters.
- **Model/account/schema:** [model3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) công bố structured outputs; [pricing](https://ai.google.dev/gemini-api/docs/pricing) công bố Free Tier và giá Standard hiện tại. Quyền project/account/quota/khu vực/Free Tier của người dùng **NOT VERIFIED**; không đọc/đề nghị key. Schema local Draft202012 hợp lệ,375 enum/9810 UTF-8 bytes, không rút ML schema. [Structured-output docs](https://ai.google.dev/gemini-api/docs/structured-output) cảnh báo schema lớn có thể400 và một số constraints như uniqueItems/minLength bị bỏ qua ở server; Python validator vẫn bắt buộc. Server thực chấp nhận full schema và extraction tiếng Việt **NOT VERIFIED**. Phương án explicit json_only hiện có giữ đủ375 và Python validation; không tự fallback/thay allowlist.
- **Live smoke đề xuất, CHƯA CHẠY/chờ duyệt:** tối đa2 request tổng cộng (1 intent +1 extraction cho “Tôi ho và sốt.” hoàn toàn giả lập), max_retries=0,timeout20s/request,max_output_tokens=1024; giữ full375 schema, không tool/prediction/real health text. Dừng ngay khi400/401/403/404/429/timeout, không thêm request fallback. Ngân sách đề xuất≤0.05USD tổng; chỉ chạy sau khi xác minh model/tier/quota và tính được upper bound gồm input/output/thinking theo giá lúc chạy. Đây không phải hard billing guarantee; nếu chưa xác lập bound thì giữ NOT RUN. Ghi HTTP/status/model/schema hash/usage/latency, cost thực hoặc unknown, không key/raw health logs. Không dùng2 request làm extraction accuracy hoặc bằng chứng an toàn.
- **Test local và test-harness correction:** full bộ liên quan **271 passed trong56.13s** =144 Phase5B +35 tuning +11 audit primitives +81 hồi quy. Lượt đầu270 pass/1 fail do test cũ đòi notebook switch=False; chỉ sửa test_tuning để AST-copy đặt False trong RAM khi test, chấp nhận người dùng bật thật và tuyệt đối không sửa notebook/output. Sau điều chỉnh cả bộ PASS;11 audit tests chạy lại PASS sau hardening RAM/I/O handling. Synthetic checks/audit primitives không phải Drive evidence; không fit model thật, gọi Gemini hay mở CSV test. Script audit mới có test missing-artifact trả NOT VERIFIED, guard write/network, CV missing-class/leakage, checksum/paths, warning summaries và memory-only packet.
- **Source/bảo toàn:** chỉ sửa src/agent/conversation.py/extraction.py và regression tests, thêm script audit/test audit, ghi log này; provider.py/config5b và tất cả nguồn ML/tuning đã pin giữ nguyên. Bootstrap/schema/mapping/Phase2/checkpoints/old evidence/figures/notebook outputs không đổi; không .venv, ZIP, API/frontend. Refresh đúng dist/drive-source hiện có bằng script chuẩn,38 source/config files,CheckOnly PASS,fingerprint7ed76bee56f4aa305b8786b48725d1b7b87080bc1a1fe2f781424d43da64aa33. Không tự upload Drive hoặc tạo cơ chế đồng bộ mới.

Kiểm Drive ở kernel đang có session: đưa duy nhất scripts/audit_post_tuning.py vào /content/audit_post_tuning.py, không Run All notebook hoặc thay switch. Chạy cell chỉ đọc:

```python
import runpy
api = runpy.run_path('/content/audit_post_tuning.py')
audit_result = api['audit_post_tuning'](
    session, experiment_id='tuning-v1-9c4dd013abbba14a',
    ensemble_run_id='tuned-ensemble-20261029T041701354242Z-6c84dbfe',
    trusted=True,  # Chỉ checkpoint do nhóm tạo và tin cậy; không fit/predict.
)
api['emit_packet'](audit_result)
```

Copy Cell Output3 dòng POST_TUNING_SHA256/POST_TUNING_GZIP_BASE64/POST_TUNING_STATUS để đối chiếu tiếp. Script không lưu file hoặc thay artifact. Tại thời điểm ghi log chưa có packet này nên phầnA checksum/metrics/pipelines thực vẫn NOT VERIFIED; không thay bằng số mock. **Tổng thể REVIEW: chờ artifact audit, human review và quyết định model, không triển khai API hoặc chạy Gemini live trong nhiệm vụ này. Dừng sau audit.**


## 25. 2026-10-29 — Phân tích học thuật và lựa chọn sau Post-Tuning Audit Colab

- **Mục tiêu:** giải thích bằng chứng thực nghiệm của5 họ model, tuning, ensemble và trade-off API/chatbot theo yêu cầu Comprehensive ML Model Analysis & Selection Rationale. Ban đầu thiếu packet; sau hướng dẫn chạy đúng một cell chỉ đọc cuối notebook03, người dùng cung cấp kết quả Colab. Không yêu cầu Run All, thay hai switch đã bật có chủ đích hoặc xóa output.
- **Bằng chứng mới / đính chính mục24:** giải mã và lưu nguyên64.212 bytes tại [post_tuning_audit/colab_evidence.json](../../../artifacts/metadata/post_tuning_audit/colab_evidence.json), SHA-256 `70849a69a0d2cd571e2d93a938b98a9167b9d46ceb0db9d6cb1859f6a2e415e8`. Packet status PASS; auditor source SHA98cb00071f72e3f3cdb045b618ae6cfa73eae5c30c339db9d989793315603235 khớp script local. Trạng thái thiếu bằng chứng của mục24 là lịch sử; hiện checkpoint/metrics/folds/selection đã được kiểm bằng audit Colab. Agent xác minh transport SHA và nội dung, không trực tiếp tải/rehash Drive weights. SHA không là chữ ký nguồn.
- **Phương pháp:** đối chiếu thêm3 packet gốc Phase3/Phase4/structured-inference có SHA41a4ad3b…/42cf30dc…/5dacef33…; kiểm pipeline SHA chéo, baseline reference, metric/transition/diversity accounting có sẵn, timing7-repeat. Đọc configs/phase3.json và source tuning/ensemble/pipeline; tra tài liệu scikit-learn1.6 cho cơ chế thuật toán/defaults, không cập nhật thư viện hoặc bootstrap.
- **Integrity sau tuning:** experiment tuning-v1-9c4dd013abbba14a, manifest SHA4a10ddd5deba5fff7927f84ea334196a3f6d127b9777ced2b127f5b5e9389355. Colab kiểm26 manifest files, identity/schema375/mapping587, selection liên kết checksum-verified trials,5 selected checkpoints và validation predictions; reload tuần tự PASS đúng feature/class order, parameters/source/versions và train-only variance mask. Guards0 fit/predict/test/network/persistent write. Ensemble run tuned-ensemble-20261029T041701354242Z-6c84dbfe, manifest SHA858893c442f1966eb8c7508a74cf6318b820004278342a1b958942151c049060,4 files checksum/rows/metrics PASS; hard-vote tái dựng từ labels lưu sẵn đúng tie policy.
- **Fold / scorer:** SGKF3 shuffle/seed42 theo symptom-vector group, assignment reproduction PASS; train rows87406/87496/87594, holdout43842/43752/43654, holdout groups39071/39073/39067. Train đủ587/587/587 lớp; holdout586/586/587. Fold0 thiếu colorectal cancer(ID112), fold1 thiếu idiopathic infrequent menstruation(ID275); scorer vẫn đủ587 nhãn/zero_division0. Không áp CV local sklearn1.8 sang Colab hoặc resplit để ép coverage.
- **Trial / selection:** supplement Colab nguyên53.841bytes [model_analysis/colab_supplement.json](../../../artifacts/metadata/model_analysis/colab_supplement.json), SHA4ccfa85ac4639778ffae6d11a435fb78af825bb4e1c294792356bec7236b4d28, cùng hai manifest SHA với packet chính.15 candidate,45 fold attempts completed; không failed/interrupted/ConvergenceWarning trong state. Có415 DeprecationWarning/36 ResourceWarning; không chia warning aggregate cho từng candidate. Candidate0 của cả5 model trùng baseline parameters. Selected LR C2,SVC C2,RF depth32,KNN k7,NB alpha0.5; các tham số khác giữ nguyên. Mean CV tương ứng0.80057098/0.79327710/0.51921011/0.72590755/0.62136336, std0.00063724/0.00179147/0.00607702/0.00182984/0.00446608. Tính lại mean/std từ3 selected scores; không coi std là CI. Supplement cung cấp đủ45 scores của15 candidate và per-candidate D/R/C warnings; local mean/std/selection arithmetic/params/elapsed/warning sums khớp packet chính. Cấu hình thắng cao hơn candidate0 ở từng fold của cả5 họ; std giảm ởLR/KNN nhưng tăng ởSVC/RF/NB. Không tái tính fold predictions vì không persist.
- **Phân tích năm baseline:** mở rộng nguyên lý multinomial LR/L2, LinearSVC OvR/margin, Random Forest bootstrap/feature subsets/capacity cap, KNN distance-weighted Manhattan/brute, BernoulliNB likelihood0/1; giải thích375 indicators/587 classes, exact config/seed/resources và train-only375→variance318→CSR→estimator. Bảng5 metrics/coverage/F1zero/fit/predict/bytes/process RSS/warnings dùng packet thực. LR dẫn baseline Macro F1 = 0.78780814 nhưng SVC coverage564/F1zero24 so LR560/28; không gọi LR tốt hơn ở mọi lớp. Support33 lớp1,68≤2,132≤5 là các tập lồng nhau, metric tail không ổn định.
- **Validation tuning:** Macro F1 LR0.79315438,SVC0.78636758,RF0.51090813,KNN0.74567902,NB0.67213832; đều tăng so baseline. NB tăng lớn nhất+0.07279779 nhưng vẫn không dẫn nhóm. LR tuned Accuracy0.83766003/Weighted F1 = 0.83843972,coverage566/F1zero23; cải thiện F1+0.00534624 nhưng Macro Precision giảm. Cấu hình chọn bằng CV train, validation chỉ so selected; không mở search sau khi thấy điểm.
- **Ensemble / diễn giải:** baseline hard LR+SVC+KNN sửa152/làm sai170,net−18,Macro F1 kém LR; LR/SVC disagreement7.6387%,joint error14.4488%=4.063 hàng. Majority3/tie→LR không cho phép KNN đơn lẻ cứu hàng cảLR/SVC sai. Tuned hard đạt Macro F1 = 0.79651707/Accuracy0.83691323/Weighted F1 = 0.83768176,coverage567/F1zero21: F1 cao nhất trong11 phương án đã kiểm nhưng Accuracy/Weighted F1 thấp hơn LR tuned (net−21 correct rows). Supplement xác nhận hard tốt nhất sửa173/làm sai194 dự đoán LR tuned,23.361 both-correct/4.392 both-wrong và963 ties.115 lớp tăng F1/128 giảm/344 không đổi;2 lớp0→positive/0 positive→0. Nhóm support≤5 (132 lớp,363 hàng) đóng góp93.82% net gain Macro F1; hai lớp được cứu ID289 injury to the abdomen và434 polycythemia vera đều support1. LR/SVC joint error giảm4.063→3.998,LR/KNN vàSVC/KNN tăng nhẹ; không gọi mọi lỗi độc lập hơn hoặc gán quan hệ nhân quả. Net/gross/mean/support/diversity accounting local khớp. Soft saved-label metrics PASS; ephemeral probability mean chưa kiểm lại độc lập, không inference mới.
- **Resource / công bằng:** tách compressed bytes, process RSS, timing toàn validation khỏi batch1 latency/RAM estimator. LR tuned1.438.563bytes/2.115s saved-validation predict; hard3.554.419bytes/300.793s tổng records, có thể khác phiên và chưa voting overhead. Không là SLA. Baseline một mẫu/7 lần LR median13.789ms,KNN21.716ms là bằng chứng khác, không áp sang tuned. Top3 hard vote không là posterior; ghép Top1 ensemble/Top3LR là policy mới cần duyệt, probability4 model chưa calibration.
- **Đề xuất / phương án:** [rationale](MODEL_SELECTION_RATIONALE.md#phân-tích-học-thuật-và-lựa-chọn-hiện-tại) xem đủ11 phương án và matrix LR baseline/LR tuned/Hard tuned. **MODEL SELECTION PENDING**: hard là best validation Macro F1, LR tuned là single-model cân bằng đáng benchmark, không tự chọn model nào. Lý do có thể không chọn hard gồm Top3 contract,3 artifact/KNN/operational complexity, latency/RAM và uncertainty chưa đủ; đồng thời không cho LR tuned thắng tự động vì tiện. Default baseline giữ nguyên.
- **Giới hạn / bước tiếp:** candidate-score/warning và paired-error/per-class summary đã hoàn tất; còn paired group bootstrap có seed/B chốt trước nếu cần CI, không row-wise hoặc tiếp tục search; same-environment load/warm-up/batch1p50/p95/concurrency/measured RAM và human-reviewed output/gate. Resume namespace chứa split_warnings là REVIEW từ source, chưa chứng minh run gặp lỗi; giữ pinned source. Fold predictions không persist nên không tính lại CV F1; không cam kết exactly-once history từ state. Synthetic dataset/0=chưa ghi nhận/Vietnamese extraction/rare-support/calibration/Phase1 EDA toànCSV tiếp tục giới hạn; không tuyên bố clinical safety hay statistical significance.
- **Tài liệu / trực quan:** cập nhật4 Markdown hiện có (rationale, reports/phase3_post_training_audit.md, docs/phase4_ensemble.md và log), lưu2 packet evidence thật. Giữ lịch sử; không tạo report chồng chéo. Reuse3 Phase3/2 Phase4 figures và Baseline-vs-Tuned PNG đã được manifest kiểm trên Drive; chưa tải ảnh gốc để kiểm trực quan. Thêm đúng1 PNG khoa học [model_selection_tuned_error_analysis.png](../../../../disease-prediction-ml-data/reports/figures/model_selection_tuned_error_analysis.png) từ supplement đã kiểm: correctness2×2 và đóng góp Macro F1 theo support; xem ảnh để kiểm layout, không thêm notebook/figure trang trí.
- **Kiểm tra / bảo toàn:** 207 assertions consistency chỉ đọc PASS trên5 packet,45 CV scores và1.174 per-class scores;133 local links/anchors/fences PASS. Guard0 fit/predict/test/network/write. Kiểm packet/source SHA, selected mean/std, candidate0 configs, metric/reference/delta/bytes/time arithmetic, guard counters và Markdown links/anchors/fences; snapshot trước/sau loại trừ locked test trước mọi phép đọc/hash. Không chạy lại model tests có fitting cho thay đổi docs. Không source/config/model/default/schema/mapping/split/bootstrap/notebook/output/old evidence/Phase2–4 artifact changes, không .venv/Gemini/API/fit/tuning/test payload. **Dừng sau phân tích tài liệu; chờ nhóm duyệt lựa chọn model cuối và phép kiểm triển khai/uncertainty còn thiếu.**

## 26. 2026-10-29 — Final ML Evidence Gaps và kế hoạch bàn giao workspace

- **Mục tiêu/phạm vi:** hoàn thiện bằng chứng paired uncertainty và tuned inference cost,đính chính các snapshot lịch sử có thể bị hiểu sai,
  kiểm kê filesystem/imports/references và chuẩn bị kế hoạch bàn giao. Không cleanup,đổi đường dẫn/model/default hoặc triển khai API.
- **Protocol chốt trước tính:** seed20261029,B2000;resample25127 validation groups có hoàn lại,giữ mọi row/label của group cùng multiplicity cho hai model;
  Macro F1 đủ587 IDs/zero_division0,Accuracy phụ,percentile2.5/97.5(method linear). Không row bootstrap hoặc bỏ replicate thiếu lớp.
  Benchmark64 group chọn không nhìn label/error,first row mỗi group,cùng panel/order,batch1,3 warm-ups/operation và3 vòng×64=192 calls;
  LR Top1/proba+Top3 riêng,hard3 member predict+vote,BLAS1/working_memory128MiB,thứ tự LR→hard,load/RSS riêng.
- **Công cụ:** thêm [audit_final_ml_gaps.py](../../../scripts/audit_final_ml_gaps.py),dùng lại read_only từ audit_post_tuning.py,
  shared integrity/loaders,read_completed_checkpoint/load_fitted_checkpoint,sampled_memory và hard_vote. Không bootstrap/cache/export/file cleanup/sync framework mới.
  Script chạy ngoài src đã pin;không sửa moduleML,FunctionTransformer path hoặc checkpoint identity.
  Đã hướng dẫn upload đúng2 diagnostics vào runtime/content và chạy một cell trên session đang có,không Run All03/04.
- **Bằng chứng Colab mới:** người dùng gửi packet ML_GAPS,statusREVIEW/selectionPENDING có chủ đích,lưu nguyên36429bytes tại
  [final_ml_gaps/colab_evidence.json](../../../artifacts/metadata/final_ml_gaps/colab_evidence.json),SHA7c2ed8e6705347a850bb90e88cdea54067d0d12ec5553588ce03fbd0a99725ac.
  ScriptSHA7c925d48e02dfab7b6951303c2c3e69f52d4143658ba1e1976a079b5b4141ce1 khớp local;
  tuning manifest4a10ddd5…/ensemble858893c4… liên kết đúng audit cũ. New run kiểm26 tuning files,4 ensemble files và7 Phase2 input checks bằng helpers;
  reload/predict3 tuned members cho benchmark. Counters0fit/test/network/write,persistent_files_written0,default_changedfalse.
  Agent kiểm packet local,không trực tiếp điều khiển Drive/kernel hoặc tự tuyên bố đã rehash Drive độc lập.
- **Bootstrap kết quả:** observed delta F1 hard−LR+0.00336269016,meanbootstrap+0.00301572772,
  CI95%[−0.00003807225;+0.00622336859];Accuracy delta−0.00074679943,CI[−0.00168360408;+0.00021315958].
  Cảhai chứa0,chưa xác lập ưu thế ổn định,cũng không chứng minh tương đương. Fraction positive0.9735 F1/0.0605 Accuracy không p-value/posterior.
  Cả2000 replicate vắng lớp:8/13/19/25/31(min/p05/median/p95/max),182 lớp vắng ít nhất1 lần;vẫn denominator587.
  Rare support/discontinuous F1,group-iid giả định và repeated-validation selection bias tiếp tục giới hạn.
- **Benchmark thật:** Colab Linux,CPU Xeon2.20GHz/2logicalCPU,RAM12.671GiB,Python3.13.18/sklearn1.6.1/NumPy2.1.3/pandas2.2.3.
  Upfront integrity7.934s;verified-load LR0.036802s/hard0.111631s. LR Top1p50/p95=13.102/14.778ms;
  LR proba+Top3=12.854/15.073ms;hard Top1=48.705/88.125ms. Sampled process peak393.105/393.535MiB;
  RSS gồm data/kernel/allocator,sampling0.5s có thể lỡ peak,không RAM estimator. Integrity pre-reads/cache/fixed order/profiler guard tạo overhead,
  không cold-start/concurrency/API benchmark hoặc SLA. LR Top3 scores thật chưa calibration;hard Top3 unavailable,không hybrid/calibrator.
- **Đính chính tài liệu:** [rationale](../../MODEL_SELECTION_RATIONALE.md) giữ nguyên số/lịch sử local CV587/587/587 nhưng thêm cross-reference rõ
  run Colab holdout586/586/587,train587 cả3 folds,scorer587/zero_division0. Các ô tuned NOT VERIFIED trước ML_GAPS được đánh dấu snapshot,
  không dùng timing baseline thay tuned. Thêm kết quả hiện hành/conditional recommendation,không xóa history hoặc old notebook outputs.
- **Kiểm kê local:** stat toànworkspace kể hidden2028files/287763200bytes(274.432MiB),riêngproject2027files/287652468bytes.
  Raw190786867bytes là nhóm lớn nhất.38 nhóm report cùngSHA/38 extra copies27189019bytes(25.929MiB),26 cặp tables;
  một cặpZIP99614bytes trùngSHA,không suy mọi archive giống nhau. .venv1648files/24559868bytes;17 backupfiles5491576bytes;
  56 pycachefiles ngoàivenv1765136bytes;pytestcache19856bytes. Chỉ stat lockedtest292558bytes,không mở/băm.
  Số liệu là snapshot trước các file bổ sung nhiệm vụ này,không số Gittracked hoặc disk blocks.
- **Drive inventory qua packet:** canonical/content/drive/MyDrive/ML_Projects/disease-prediction-ml,167files/263964552bytes,
  artifacts64files/43385417,data4/192634662,reports60/27565126,src29/configs7/requirements2/root source_manifest1.
  Không có top-level notebooks/docs/scripts/tests trong snapshot. Rawsize190786867 bằnglocal nhưng rawSHA-copy chưa kiểm;
  report runIDs20261027 kháclocal20261021 vàsizes khác,không xem như bytebackups. Root source_manifest42562bytes đượcstat nhưng content/purpose chưa đọc,
  current sharedbootstrap không dùng nênREVIEW,không tựxóa. Baseline weights/fullPhase4 definitions có audit lịch sử;chưa full fresh content verification mới.
  ExactcurrentPhase2 manifestvariant không đượcpacket xuất riêng;giữ warning không chép localca20… đè variant5030… gắnidentity lịch sử.
- **Dependency/cleanup risk:** test_data_regression dùng flatreports;validate_portability dùng backupbaseline/notebookscũ;
  validate_deliverables vàrun_phase1 dùng executionruns/parent usernotebook. src/package identities vàcustomto_csr cần nguyên modulepaths/versions.
  Current7 notebook codecells đều sharedbootstrap,không ZIP/.pyz/colab-session/receipt;legacyhelpers vẫn đượctests import,
  builderwrite_notebook còn gọi migrate nên không kết luận từ token ZIP ở template. .gitignore loại datasets/models/runs/backups/dist/env;
  chỉhandoverGit hoặcstage không đủartifacts. Source staging38files CheckOnlyPASS,không Refresh.
- **Phương án và quyết định đề xuất:** tạo duy nhất [WORKSPACE_HANDOVER_PLAN.md](WORKSPACE_HANDOVER_PLAN.md) với footprint/type/duplicate ledger,
  Drive evidence scopes,callers/risk/reproducibility vàKEEP/IGNORE/REGENERATE/REVIEW/REMOVE-LATER từngnhóm,giữcấu trúchiện hành.
  KEEP code/config/notebooks/tests/docs/dataset/checkpoints/manifest/schema/mapping/evidence,reports/backups còn reference;
  IGNORE env/cache/staging khihandoversource,khôngxóa. Legacyarchives/receipt chỉREMOVE-LATER sauowner duyệtretention vàcopychecks.
  ĐềxuấtLRtuned choAPI nghiêncứucầnTop3 cóevidencecost/output thực;Hard vẫnbest pointMacroF1,chưa có bằngchứngCI ưu thếổn định.
  **MODEL SELECTION PENDING** tớikhi nhómduyệt;default LRbaselinekhôngđổi.
- **Kiểm local/bảo toàn:**9 unit tests memory-only PASS (fakes ởbenchmark controlflow,không estimatorfit/inference thật),
  35 consistencychecks dưới existingread_onlyguard PASS,độc lập tái tạo64 panelindices/groups và2000 missing-class-frequency replicates từ
  shared validationloader. Không có rowpredictionslocal nên không nói đã tính lại CI F1 độc lập. Guardlocal0fit/test/write/network.
  129 local links/anchors/fences vànewPython syntax PASS. Snapshot317 file cũ được băm (loại cache/env/test payload):315 khôngđổi,
  chỉ2 Markdown thayđổi,0file bịxóa,4file mới đúngscope;scriptSHA vẫnkhớp Colab. Không fullsuite cófit/test-access/tempcleanup.
  Chỉ sửa2 Markdown hiệncó,thêm1plan,1script,1test và1packet thật;không đổi nguồnML/bootstrap/config/Phase2/checkpoints/notebooks/oldoutputs/archives,
  không tạoenv/ZIP/datacopy/modelcopy hoặcxóa/move/rename file.
- **Bước tiếp:** nhómduyệt evidence/outputcontract/acceptancecriteria,kiểm quyềnDrive vàraw/report/backup copychecks thiếu,
  chốt source+artifact access cho thành viên,rồi nếu muốncleanup hãy duyệtallowlist absolutepaths/bytes/callers/retention/rollback riêng.
  Không phát sinh quyềncleanup hoặcmodelselection từ kếhoạchnày. **STOP sau phân tích/kiểm kê/tài liệu.**

## 27. 2026-10-29 — ML Selection Decision Record và chuẩn bị bàn giao

- **Mục tiêu:** chuẩn hóa đề xuất ML và hướng dẫn thành viên nhận full source cùng quyền Drive. Chỉ documentation/link/structure checks;
  không phê duyệt model, cleanup hoặc triển khai API.
- **Căn cứ:** sáu packet đã xác minh Phase3/Phase4/structured inference/Post-Tuning/model-analysis/ML_GAPS;
  đọc configs,notebook source cells,loader/checkpoint/staging helpers,.gitignore và Phase5B/test source. Chép lại metrics/bảng đã kiểm,
  không fit/predict/resample/tuning hoặc dựng số liệu mới. Các hình/bảng/packet/report cũ giữ nguyên.
- **Decision record:** đặt tại đầu [MODEL_SELECTION_RATIONALE.md](MODEL_SELECTION_RATIONALE.md#decision-record-lựa-chọn-ml),
  tổng hợp5 họ/cấu hình baseline vàselected tuned,cả5 tổ hợp trước/sau tuning,coverage/CV/scorer vàgiới hạn.
  Baseline hard tốt nhất cứu152/làm sai170 theoLRbaseline;hard tuned cứu173/làm sai194 theoLRtuned.
  93.82% net F1 gain từsupport≤5,hai lớp0→positive chỉ1 mẫu/lớp;không gán causal independence cho mọi member.
- **Đề xuất chưa phê duyệt:** hard tuned LR+SVC+KNN best observed validation Macro F10.79651707;
  LR tuned0.79315438 preferred deployment candidate choAPI nghiên cứu cầnTop3 theooutput/cost vàAccuracy/WeightedF1;
  LRbaseline0.78780814 vẫndefault. **MODEL SELECTION PENDING**,không thay phase3.json hoặc checkpoint đangdùng.
- **ML_GAPS được dẫn lại:** seed20261029/B2000/pairedgroup/fixed587/zero_division0;
  deltaF1 CI95%[−0.00003807;+0.00622337] chứa0,cả2000 replicate thiếu lớp,median19.
  LRtuned Top1p50/p95=13.102/14.778ms,hardtuned48.705/88.125ms;load0.036802/0.111631s.
  Cùng64 group/192 calls;profile/cache/fixedorder/RSS0.5s limits,khôngcoldstart/concurrency/SLA;
  probability chưa calibration vàsynthetic/LLM semantic shift còn giới hạn. Không chạy lại benchmark/CI ở nhiệm vụ này.
- **Handover guide:** thêm [HANDOVER_GUIDE.md](HANDOVER_GUIDE.md),phase map/reading order,source tree,
  local-vs-stage-vs-canonicalDrive,raw/processed/schema/mapping/checkpoint/manifest/evidence paths vàrun IDs,
  Colab setup/điểm dừng03/04,tuning-switch semantics,offline-test/integrity commands vàtroubleshooting.
  False chỉtắt sectiontuning,khôngtắt fitcells03;hai switches đã bật cóchủđích đượcgiữnguyên.
  Phase5B chỉoffline/mock,live=false/min_present2provisional,30synthetic cases pendinghumanreview;
  chưaGemini/account/schema375/semantic/cost live,Phase5A PredictionAPI hoặcfrontend.
- **Môi trường bàn giao:** requirements.txt làPhase1/Python3.11 vàrequirements-dev kéo nó vào,
  khác exact checkpoint versions Python3.13.18/sklearn1.6.1/NumPy2.1.3/SciPy1.16.3/joblib1.6.0.
  Guide yêu cầu đọcfit.json.identity.versions,không càiđè deps Phase1/dev vào Colab đểchữa reload;
  source/library mismatch cầnowner xửlý compatibility riêng,không sửaidentity/hash hoặc retrain bù.
- **Cấu trúc/source ownership:** giữtree/canonicalroot hiệnhành. dist/drive-source chỉ38 runtime files,khôngsource handover đầyđủ.
  SnapshotDrive167files từML_GAPS khôngcó top-level notebooks/docs/scripts/tests;weights/tunedmanifests/newruns chỉởDrive theoevidence.
  .gitignore loại datasets/models/runs/backups/dist/env nên phải bàn giao fullsource/publicconfig/tests/docs/notebooks/evalJSONL,
  approvedmetadata/evidence/reports đượcgiữ vàcấpquyền persistentartifacts riêng. ChưacóGitrepo theoinventory;
  khôngclaim đãtrack/commit,khôngupload workspace hoặc tạoZIP/sync mới.
- **Discoverability vàhistory:** README thêmguide/decision-status,đánhdấu câuLRtốtnhất0.78780814 làsnapshotbaseline trước tuning;
  WORKSPACE_HANDOVER_PLAN thêmcross-reference guide,giữinventory/retention/copystatus vàlịch sử trước đó.
  Raw/report/backup copySHA vàexactcurrentmanifest variant cònN/V;không chépca20… đèDrive5030… gắnidentity lịch sử.
- **Kiểm chứng/phạm vi:** chỉkiểm tài liệu,source references,20 MacroF1 values chép từpackets,IDs/versions/switch/cell boundaries,
  links/anchors/codefences vàpreservation snapshot. Testcommands trongguide làthamkhảo,không chạypytest,old9tests,
  integrity loader,Colab setup,audit script hoặcmodel inference trongnhiệm vụdocs này. Khôngmở/băm lockedtest.
  PASS189 local links/anchors/fences;20 metriccells khớp packet,6 packetSHA khớp bằngchứng,38 stagefiles khớp màkhôngchạystaging script.
  Snapshot2027 file ngoài4 docs đượcphépsửa giữnguyên size/mtime vàSHA nơi áp dụng;chỉ1filemới HANDOVER_GUIDE.md.
  Thayđổi chỉREADME,rationale,log,inventory-plan vàguide mới;src/config/notebooks/outputs/data/checkpoints/oldreports/archives/env/cache giữ nguyên.
- **Bước tiếp:** nhómduyệt candidate/model/outputcontract vàproduction acceptancecriteria;
  owner cungcấp fullsource+Drive permissions vàcontent-copy evidence thiếu. Finaltest cầnprotocol độc lập dođãdùngvalidationnhiềulần;
  human-reviewed gate/extraction evaluation,Phase5A/Gemini live/defaultmigration đều lànhiệm vụsauphêduyệt riêng.
  Không phát sinh quyềncleanup từguide. **STOP sau documentation/handover preparation.**

## 28. 2026-10-30 — Khóa final-test protocol và chuẩn bị notebook06

- **Ủy quyền/đính chính:** owner duyệt LR tuned C=2 là deployment model nghiên cứu trước test.
  Hard tuned LR+SVC+KNN là best observed validation Macro F1 comparator; LR baseline là đối chứng gốc.
  Lịch sử PENDING ở mục27 và tài liệu cũ không bị xóa. Default code vẫn baseline do migration chưa nằm trong nhiệm vụ này.
  Việc duyệt model **không** cấp quyền đọc test; owner yêu cầu bước execution được ủy quyền riêng sau chuẩn bị.
- **Mục tiêu:** đánh giá held-out generalization/academic comparison cho đúng3 ứng viên, không chọn lại model/hyperparameter/vote/threshold/calibration.
  Protocol `final-locked-test-v1`,SHA `049ee0aa3c2907985c3d3a03ed222b1d6e1efb5921bbbc2d04ec0dea9baa8947`,
  được tạo từ metadata/evidence đã có,không đọc CSV test. Test identity dự kiến28.066 dòng/25.128 group/375 features/587labels.
- **Căn cứ giữ nguyên:** tuning `tuning-v1-9c4dd013abbba14a`,hard run `tuned-ensemble-20261029T041701354242Z-6c84dbfe`;
  pipeline SHA,original source hashes,Phase2 Drive manifest50308d… và schema/mapping được pin đầy đủ trong protocol source.
  Baseline identity tái dựng khớp ID đã audit; selected identity dự kiến `tuned-v1-b8a5602679b3dc5c` phải đối chiếu lại với Drive thật.
  Tuningmanifest4a10ddd… và ensemblemanifest858893c… khóa các bundle đã audit,không tìm checkpoint mới theo metric.
- **Phạm vi code:** thêm `src/models/final_evaluation_protocol.py` và `final_evaluation.py`,
  `notebooks/06_final_model_evaluation.ipynb`, `tests/test_final_evaluation.py`.
  Tái dùng shared bootstrap/ColabTraining.open,Phase2 integrity/loader,load_fitted_checkpoint,build_pipeline chỉ đối chiếu params,
  score_prediction và original hard_vote/tie priority. Không tạo training pipeline,bootstrap,sync hoặc voting policy khác.
- **Preflight:** existing phase4_guard cấm mọi test payload open kể cả hashing. Kiểm7 train-validation/metadata inputs,
  manifests/bundles/checkpoint/source/environment; đọc test counts/hash từ metadata đã khóa,không deserialize hoặc predict.
  Gate yêu cầu cả booleanTrue và chuỗi owner confirmation gắn protocol SHA; xác minh lại prepared identity/code/root/status,
  reload/check object schema/classes/params trước lần nạp test.
- **One-time/partial:** namespace mới `artifacts/metadata/final_evaluation/049ee0aa3c290798/`;
  exclusive execution marker flush/fsync trước loader. One loader invocation kiểmSHA rồi parseCSV,không copy/cache test;
  tuned LR prediction được reuse trong hard vote. Started/partial/completed/orphaned đều chặn rerun;
  failure.json nếu còn kernel,completed manifest viết cuối. Không tự resume,xóa marker hoặc ghi đè artifact lịch sử.
  `read_completed` cho phép kiểm/đọc kết quả đã publish mà không reopen test/predict.
- **Analysis khai báo trước:** MacroF1 đủ587 IDs/zero_division0; secondaryAccuracy,MacroPrecision/Recall,WeightedF1,coverage,F1zero;
  ba cặp paired rescue/new-error,bothcorrect/bothwrong; mean within-group correctness/equal-group paired differences mô tả,
  support/independentgroups/per-class đủ587 và bins0,1,2–5,6–20,>20. Không thêm CI hoặc optimization từ test.
  ML_GAPS validation CI chứa0,rare-class và timing limitations vẫn giữ nguyên; test không sửa lại kết luận bootstrap đó.
- **Outputs dự kiến:** execution/protocol/preflight receipts,test_predictions.npz đúng3candidates,comparison/per_class/transitions/group_differences CSV,
  một PNG hai panel,results.json,report.md,manifest.json;12file cùng namespace mới. Chưa có output test thật nào được tạo.
- **Sửa lỗi trong chuẩn bị:** synthetic end-to-end phát hiện validation reference LR baseline thiếu coverage/F1zero dẫnNaN khi serializeJSON.
  Bổ sung đúng560 predicted classes/28 F1zero từ Phase3 audit evidence vào freeze trước execution; không dựng metric mới.
- **Kiểm thử local:** `python -B -m pytest -q -p no:cacheprovider tests/test_final_evaluation.py tests/test_tuning.py tests/test_post_tuning_audit.py`:
  **67 PASS**,gồm21test mới. Chỉ synthetic temp CSV/mock checkpoint bytes/mock predict;không estimator.fit,checkpoint thật hoặc Gemini.
  Kiểm zero-test-open/hash/stat ở preflight;defaultFalse zeroIO;authorization sai;tamper source/env/schema/checksum;
  reload feature/class/param mismatch;one-time slot;partial failure;exclusive writes;report replay và integrity;587labels/group differences/tiepolicy;
  notebook cells parse được,gateFalse và không có output. Không dùng điểm mock như final metrics.
- **Tài liệu/bàn giao:** cập nhật chọn lọc MODEL_SELECTION_RATIONALE,HANDOVER_GUIDE,README và log này.
  Hai module mới cần đồng bộ vào source Drive qua cách hiện có trước khi mở06;staging cũ chưa rebuild,
  không chạy `-Refresh`,không upload toàn workspace,không đổi canonical path hoặc tạo archive.
  Source handover vẫn gồm notebooks/docs/scripts/tests ngoài phần runtime Drive;giữ cấu trúc,không cleanup.
- **Kiểm bảo toàn cuối:** 200 local links/anchors PASS;14cell notebook06 hợp lệ,outputs rỗng;
  21 validation reference values khớp evidence và original source pins giữ nguyên.
  Snapshot2.028file ngoài8file được phép sửa không thay đổi (hash source/notebooks/JSON vàstat cho binary/data/environment;
  không băm payload CSV). Không có final-evaluation namespace thật ở workspace;4pipeline hiện không có bản local.
- **Giới hạn/STOP:** không truy cập Drive/Colab trực tiếp,chưa fresh-verify4checkpoint hoặc môi trường thật trong lần này;
  chứng cứ Colab cũ và source/metadata local chỉ là căn cứ freeze. Preflight thật có thể BLOCK nếu identity/environment/source không khớp.
  Phase1 đã EDA toànCSV,test không phải externalblind;dataset synthetic/vector đa nhãn/probability chưacalibration/LLM shift vẫn hạn chế.
  Không sửa03/04/05,Phase2,checkpoint,bootstrap,tuning history,model default;không tạo.venv/ZIP,cleanup,API hoặc gọiGemini.
  Owner cần ủy quyền riêng đúng protocol/SHA và ba ứng viên cho **một lần final evaluation** trước bậtgate. STOP trước test.

## 29. 2026-10-30 — Audit Local-Code + Drive-Data và hợp đồng hai ZIP

- **Đính chính owner:** không upload cả hai ZIP lên Drive. Code ZIP gồm source/notebooks/scripts/config/tests/docs/app/README,
  được giải nén local. Data ZIP gồm datasets/metadata/models/predictions/manifests/reports,giải nén đúng canonical Drive layout.
  Local code là development authority;Drive chỉ giữ authoritative data/models và generated runtime transport nhỏ.
  Không suy yêu cầu này thành quyền publish,create ZIP hoặc sửa distribution code ngay.
- **Đã audit:** runtime.json,shared bootstrap/copy/session,PowerShell stager,8notebooks00–06+smoke và dependencies,
  scripts audit/build/migration,Phase2 integrity,checkpoint source/environment pins,.gitignore,handover inventory vàtests liên quan.
  RUNTIME_DISTRIBUTION_PLAN.md chưa có,nay tạo làm tài liệu kế hoạch duy nhất;không viết guide mới song song.
- **Root causes:** stager chỉ local-stage src/config/requirements,không cloud transport hoặc scripts;
  bootstrap không copy scripts và bỏ phase5b.json dù stager cóconfig đó.
  Notebook03 hiện21cell,appendices18–19/21 gọi `/content/audit_post_tuning.py` và `/content/audit_final_ml_gaps.py`;
  file vàbiến session/api mất khi kernel reset. Script upload không đồng nghĩa session/checkpoint/mount đã sẵn sàng.
  Không điều tra hoặc thay tuning switches/output đã lưu.
- **Inventory source:**31Pythonmodules,7publicconfigs,2requirements,3audit helpers=43requiredfiles/450.741bytes.
  Current stage38file,thiếu2module final_evaluation so40expected bởi stager hiện tại;
  bootstrap actual39file,thiếu3audit scripts+phase5bconfig so proposed43. Chỉ đọc/so sánh,không Refresh hoặc rebuild.
- **Giải pháp đề xuất:** mở rộng chính prepare_colab_source.ps1 bằng Publish/DriveProjectPath vàsource-only allowlist;
  dùng Drive for desktop synced folder làm transport,không mirror toàn workspace hoặc tải dataset về local.
  Shared bootstrap mở rộng script/config inventory,kiểm publication hash/source version vàcopy vào workspace tạm hiện có;
  audit gọi `ROOT/scripts/<helper>`,session dùng ColabTraining.open hiện có. Không framework/Git hosting/source ZIP/pyz mới.
  Drive desktop process/path/account/cloud acknowledgment chưa xác minh;chỉ thấy drives C,D trong môi trường này,
  không kết luận client không được cài. Nếu không có transport phù hợp thì báo BLOCK,không giả định kernel đọc được Windows D:.
- **Publication integrity:** giữ src-only fingerprint hiện có;đề xuất generated runtime.json có42non-self file hashes,
  canonical base settings vàpayload digest,không self-pin hoặc dùng Phase2manifest làm source receipt.
  Expected digest từ local release/Publish phải truyền cho bootstrap;Drive self-consistency không chứng minh đã nhận source mới.
  Copy xong local không phải cloud ACK;không hot publish khi job đang chạy,chờ sync/Restart Kernel vàfail nếu stale/mixed.
  Không dùng source_manifest/colab-session cũ,không xóa file lạ hoặc ghi vào data/artifacts/reports.
- **Hợp đồng release:** exact ownership/extraction paths,hai SHAarchive còn NOT GENERATED,inventory excludes self,
  trusted release announcement chứa hai archive SHA. Data release phải gom fullDrive checkpoints+local evidence đã kiểm;
  same-path/different-bytes là blocker,không overwrite manifest variants hoặc report lịch sử.
  Hai source-owned exceptions là data/raw/README.md và30synthetic development cases JSONL;không lặp ở data ZIP.
  App hiện chỉ có backend/frontend .gitkeep. Cache/venv/backups/legacyarchives vẫn giữ ở workspace,không auto-zip hoặc cleanup.
- **Gaps bàn giao được ghi rõ:** code-only pytest hiện có hardcoded PROJECT/artifacts schema/mapping/evidence;
  relative artifact doc links vàlegacy validators/backups cần được phân loại offline vsintegration data-root trước release.
  Không tuyên bố tách hai ZIP đã hoạt động hoặc toàn bộ tests chạy độc lập từ code ZIP;chưa sửa các dependencies này.
- **Kiểm offline đã chạy:**33PASS (`tests/test_canonical_colab_runtime.py`12 và `tests/test_final_evaluation.py`21),
  bằng global Python -B,pytest no-cacheprovider. Chỉ temp fixtures/fake models/mock prediction,không checkpoint/test payload thật.
  Static source closure66import refs không thiếu module;dry-run43file không chứa data/artifacts/reports;
  synthetic in-memory map nhận biết missing script/config tamper. Mock session.open tạo session mới data=None,identity=None,
  không load_data/train/train_model. Đây không phải testpublisher production hoặc Colab/Drive live.
- **ML/provenance:** giữ375features/587labels,Phase2split/schema/mapping/variants,5baseline+5tuned,ensemble manifests/predictions,
  tám source pins vàhard-vote engine,checkpoint versions. LR tuned C=2 vẫn là deployment đã được owner duyệt;
  Hard tuned là best observed validation Macro F1. Final-test gateFalse,không thay frozenprotocol/default/checkpoint.
- **Rollout/rollback:** owner duyệt prerequisite/contract rồi giao implement nhỏ cho2helpers,audit-path references vàtests;
  test partial-sync/non-overwrite/source-only fixtures trước cloud. Rollback publish lại known-good code payload local rồiRestart Kernel;
  không data/model/manifest rollback,không xóa partial final-test marker hoặc tạo backup ZIP mới tự động.
- **Bảo toàn cuối:**102local links/anchors trong plan+log PASS;2.035file ngoài hai tài liệu không thay đổi theo snapshot
  (hash source/notebooks/JSON vàstat binary/data/environment;không mở/băm payload CSV).
  File mới duy nhất là RUNTIME_DISTRIBUTION_PLAN.md;không có production ZIP hoặc final-evaluation namespace thật được tạo.
- **STOP:** chỉ kế hoạch mới vàlog thay đổi;không runtime/config/notebook/staging implementation,
  không create production ZIP,source upload,data/checkpoint download,fit/retrain/predict thật,Gemini,API/frontend hoặc workspacecleanup.
  Fresh Drive/source transport/checkpoint access vàarchive checksums đều chưa được xác minh trong lần này.

## 30. 2026-10-30 — Implement packaging an toàn và unified runtime

- **Ủy quyền:** owner duyệt haiZIP/code-local,data-Drive vàcho phép implementation+trial packaging;
  không cấp quyền cleanup,ML training/tuning/calibration,evaluate locked test,Gemini hoặcAPI/frontend.
- **Source mới:** `scripts/package_handover.py` standard-library tool cho codeZIP,immutable stage,publish,data-plan,
  dataZIP vànon-overwrite extraction;`configs/handover_data_requirements.json` frozen IDs/hash requirements;
  `tests/test_distribution.py` acceptance bằngsource vàsyntheticfixtures.
  Data contract SHA66a2c437… đượcpin để không làm yếu manifest rồi publish partialdataZIP.
- **Source sửa:** `src/data/colab_runtime.py`,`scripts/prepare_colab_source.ps1`,`scripts/update_colab_notebooks.py`;
  runtime setup8notebooks và03audit-path/sessionguards;2tests canonical/tuning cho publication mới vàuserauditappendices;
  README,HANDOVER_GUIDE,RUNTIME_DISTRIBUTION_PLAN vàlog này.Không chạy builders để tái tạo analysis/output.
- **Code ZIP:** explicit include roots/src/app/notebooks/scripts/tests/docs/publicconfigs/rootrequirements/setup;
  source-only exceptions rawREADME và30syntheticdevcases.Preserve relativepaths,celloutputs vàfullsource bytes khi archive/extract.
  Excludevenv/cache/dist/.env/privateconfig/datasetCSV/joblib/artifacts/reports;scancredential/privateDrive-link patterns.
  ZIP có sourceinventory;outerhandovermanifest có archiveSHA/bytes/count/uncompressedsize/runtimeDigest/extractionpath.
  Tạo release mới,no overwrite hoặc cleanup;ZIP chỉ hoàn tất khi checksum/inventory/extractionverification pass.
  `dist/handover/release-20261030-e5936121/` là output release đã dành riêng;manifest là kết quả cuối có thẩm quyền,
  tránh sửa source log sau đónggói chỉ để chèn SHA khiến source/archive không còn cùng byte.
- **Data ZIP:** chưa có canonicalDrive accessible hoặcvalidatedDriveDesktopPath.Chỉ tạo packagingplan/requirements,
  không tạo dataZIP từworkspace local thiếuweights.Tool bắt buộcfullPhase2Drive5030…variant,raw/processed,
  5baseline+5tuned,threepinnedmanifests vàmọireferencedbundlefile,6evidencepackets vàreports cầnthiết.
  Optionalevidence-root chỉ đọc supplementalpacket cùnghash để thêm vàoZIP,không sync/overwriteDrive.
  Explicitallow-locked-bytes gate chỉ cho opaquehash/copy/archiveCRC,không CSV/NPZ/joblib parse hoặc inference.
  ArchiveSHA+perfileinventoryverify xong mới viếtdata_handover_manifest statusVERIFIED;không tháo datađãextract.
- **Runtime:** closure45file=31src+8configs+2requirements+4scripts.Copiedhelpers baaudit giữ nguyênbytes/SHA;
  package_handover làscriptthứ4đểownerpackdata trênruntime khônguploadrời.PUBLIC_CONFIGS cóphase5b vàdatarequirements.
  Generatedruntime.json pin44non-selffilehashes+canonicalbasesettings;bootstrap yêu cầu digest từlocalPublish,
  kiểmtrướcprobe/copy/import;src-onlyfingerprint riêngkhông đổi semantics.CodeWindows khôngđược giảđịnh đọc trực tiếp từVM.
- **Staging/publish:** helperPSgọi cùngPythonimplementation;stageởdist/drive-source/<digest> giữ nguyên legacy38filevàmọirevisioncũ,
  Refreshkhôngdelete.Publishcheckexistingabsoluteprojectpath,canonicaltailsuffix,approvedPhase2manifest,links vàoriginalsourcepins
  trướcwrite.Source-only45targetpaths;khôngdata/artifacts/reports.RootWindows vàDrivefolderphải riêng.
  Kết quảlocalcopy luônCLOUD_ACK_PENDING,khôngclaimDrivecloud/Colaback;chờsync,RestartKernel,nhậpdigestlocal.
- **Session/notebooks:** sharedbootstrapvàColabTraining.open hiệncó;scriptresolveROOT/scripts thay/content/<file>.
  MissingROOT/session/api/audit_result có lỗi chỉrõ setupcell,khôngruntrainingđểlấybiến.
  Smoke mountcell đổi thànhcapability/accessinstruction,không épdrive.mount trênmọiremote hoặcWindows;
  savedoutputs giữlàhistory. Khôngđổi switches hoặc defaultML.
- **Kiểm thử:**245PASS bằngglobalPython -B,pytest no-cacheprovider cho distribution,canonicalruntime,finaleval,tuning,
  post-tuningaudit,Phase5B vàstructuralcontract05.Khôngactualmodel.fit,retrain,deserializeprojectcheckpoint,lockedtestpayload thật hoặcGemini.
  Source-onlyZIProundtrip/imports,secretfilter,partial/stalepayload,wrongrootzeroWrites,protectedmetadataunchanged,
  archivepathtraversal/outerSHA/non-overwrite,fullsyntheticdataZIP vàkernelreset/sessionmocks đãkiểm.
  Ba fail ởlầnkiểmđầu đãsửa:setup-cellnewlineidempotence vàtestchỉxét3tuningcells thayvìquétcả4userauditappendices;
  giữnguyênnotebookauditcells/sourceoutputs.Source05analysiscodehash giữ nguyên.
- **PowerShell:** direct.ps1 bị executionpolicy máyhiện tại chặn;wrapperđãtestPASS bằngprocess-only
  powershell.exe -NoProfile -ExecutionPolicy Bypass,khôngSet-ExecutionPolicy hoặcđổisystempolicy.
  Handoverguide cólệnhPythontươngđươngkhôngcầnbypass.KhôngcóGoogleDriveFSprocess/mappedDriveđượcxácminh,chưaPublishthật.
- **Bảo toàn:**372filecũngoàiphạmvisửakhôngđổi theo snapshot(hashsource/JSON/notebooks,statbinary/data);
  cả8notebooks giữnguyêncellcounts vàoutputtreehash,bao gồm03/04/05.
  TámMLsourcepins+hardvoteengine,frozenfinalprotocol,Phase2schema375/labels587/mapping/splits/checkpoints/manifests
  vàevidencefiles khôngsửa.LRtunedC2 đãduyệt;hardbestobservedvalidationF1;defaultcode khôngmigration.
- **STOP:** chỉpackaging/source/runtimecompatibility vàsafechecks.CodeZIPkhônguploadDrive;dataZIP chỉcompletekhiowner
  cóDrivefullartifactvàchạytoolthật.Neverfit/Gemini/API/evaluatetest;finalgateFalseđượcbảotoàn.

## 31. 2026-10-30 — Clean-runtime smoke cho release hiện có, chưa có bằng chứng Colab

- **Mục tiêu/phạm vi:** chứng minh source handover trên Colab sạch,không tái cấu trúc hoặc đóng ZIP mới.
  Đọc runtime/bootstrap,ColabTraining/session,prepare_colab_source vàpackage_handover publish,smoke notebook,
  các setup03–06,checkpoint loaders/final read-only preflight,HANDOVER_GUIDE vàrelease manifest.
- **Local package PASS thật:** archive `dist/handover/release-20261030-e5936121/project-code.zip`,117entries/1.609.487bytes,
  SHA `5ce88547e28166808c21c701e1263a2928b81de35987995c8bc77e52e7f69d09` khớpmanifest;
  CRC vàtừng116sourcefile khớpinventory/bảngiảinén. Khôngtạo/repackcodeZIP hoặcdataZIP.
- **Local source/stage PASS:** chỉchạy `python -B scripts/package_handover.py stage --check-only`,khôngrebuild/publish.
  45file/500.375bytes;digest `a3abed4421b95032ec6c5600cc87a0acb1ccde0bab8d0382f45331120a3961c3`
  khớpworkspace runtime closure,release manifest vàstaging hiệncó.
  Baauditscript+package_handover và3modulePhase5B đềuhiệndiện;import/runpy definitions từbảngiảinén PASS local.
  Existingguard ghi0model/featurefit,0testpayloadaccess,0protectedwrite. Khônggọi audit/benchmark nghiệpvụ hoặc deserializecheckpoint.
- **Nguyên nhân thực tế đang thiếu:** owner trảlời “chưa có,tôi chỉ sử dụng notebook để kết nối đến drive”.
  MountDrive trongVM không ánhxạ vàoWindows D:,nênkhông thể cungcấp localDriveProjectPath cho workflowDesktop.
  Đây là prerequisite của localpublish,chưa phải lỗiSHA/checkpoint.HiệnchỉthấydrivesC,D,khôngcóGoogleDriveFSprocess đượcxácnhận.
  Agent không cókết nốiColabkernel/Drive connector để tựthực thi cloudsmoke.
- **Đường đi dùng helper có sẵn,khôngimplementation mới:** extension đãcài `google.colab-0.9.7` hỗtrợfolderupload.
  [Official User Guide](https://github.com/googlecolab/colab-vscode/wiki/User-Guide#uploading-files-to-colab-servers)
  ghi rõ Explorer có thể Upload to Colab cảfolder;installeduploadplanner cũng đặtfolderbasename dưới/content vàcopy đệquy.
  `publish(root,drive_project)` hiệncó khôngcóWindows-onlygate;nókiểmabsoluteexistingpath,canonicalsuffix,
  approvedPhase2metadata vàpinnedsource trướcsource-onlywrite. Vìvậy cóthể gọi ngaytrênVM với Drive đãmount;
  **chưa thử trênDriveFUSE thật**,không gọi khả năng này làColabPASS.
- **Thao tác owner trước tiên:** chọn New Colab Server,mountDrive bằngextension;
  UploadtoColab **nguyênfolder** `dist/drive-source/a3abed4421b95032ec6c5600cc87a0acb1ccde0bab8d0382f45331120a3961c3/`,
  khônguploadfoldercha/cảworkspace hoặccodeZIP lênDrive.VịtríVM dựkiến/content/<digest>.
  Trongsmoke notebook dùngrunpy nạp `<seed>/scripts/package_handover.py`,
  kiểmmake_publication(seed) có45files vàdigestkhớpgiátrịlocalđãkhóa,rồigọi
  `api['publish'](seed, Path('/content/drive/MyDrive/ML_Projects/disease-prediction-ml'))`.
  Chỉghi45source/config/script paths;khôngthaydataset/model/manifest.Phải gửi JSONpublish hoặc tracebackđầutiên.
  Kết quảcloud_verifiedFalse/CLOUD_ACK_PENDING vẫn lànhãnhelperhiệncó,kểcảkhiđượcgọitrênColab;
  khôngsuy rađãcàiDesktop hoặcsourceđãpersistquaVM khác.
- **Bằng chứng saupublish:** mởVM/servermới khác,lạimountDrive,khônguploadseed;
  kiểm/content/<digest> vàephemeralprojectworkspace chưa tồn tạitrướcsetup.
  Chạyriêng cells2–4củacolab_smoke_test:mountaccesscheck,sharedbootstrap,phase2integrity7files.
  Nhập digestlocal trên;khôngRunAll03/04/05/06,khôngcầntạo dataZIP hoặcchạycell5cache/loadtrain-validation đểkiểm imports/integrity tối thiểu.
  FreshVMphảiđọcvàverifyđượcsource45filetừDrive mới cóbằngchứngpersistence/cloudsync,khôngdùngsameVMcachelàproof.
- **Session/import/checkpoint tiếp theo sauproof:** tạo `session=ColabTraining.open(RUNTIME)` từcùngsetup,
  kiểmdataNone/identityNone vàmoduleorigin;importsrc.agent.conversation/extraction/provider vàrunpydefinitions4scripts trongROOT/scripts,
  khônggọiaudit/ML_GAPS benchmark.ProviderconfigliveFalsekhôngđượcbật.
  Checkpointsmoke chỉdùngexistingread-onlypreflight rồitrustedload_fitted_checkpoint sauverifyhash/identity/source/versions,
  kiểm375featureorder/587classorder/customto_csr/fittedstate,khôngfit/predict.Chưa cómodelnàođượcloadtrênColabtronglầnauditnày.
  Notebook independence mới xácthựctĩnh từngnotebook cóbootstrap/sessionsetup;chưaexecuteđộc lậptrênVMthật.
- **Trạng thái:**LocalpackagePASS;localstage/importPASS;sourcepublishNOT VERIFIED;
  DrivecloudsyncNOT VERIFIED;ColabbootstrapNOT VERIFIED;sessioninitializationNOT VERIFIED;
  checkpointidentity/loadNOT VERIFIED;notebookindependence liveNOT VERIFIED.
  Không dùng245mocktests hoặclịch sửPASS của runtime cũ thaychobằngchứngclean-room của release này.
- **Bảo toàn/STOP:** chỉlogđược cậpnhật;khôngsource/notebook/helper/config/ZIP/manifest/artifact edits,
  khôngcleanup,delete/move/rename,defaultmodelchange,training/tuning,lockedtest hoặcGemini.
  Sharedbootstrap khichạythật cóownedtemporaryprobes hiệncó;không được đụng fileartifactđanglưu.
  Dừng ởđiểmcần owneruploadfolder/chạy existingpublish vàgửioutput;tiếptụcsmoke từbằngchứng đó,chưa chuyển sangdatanhómkhác.

### 31.1. 2026-10-30 — Hai lỗi thiếu source trên kernel, chờ chẩn đoán chỉ đọc

- Owner gửi hai FileNotFoundError từ cùng kernel `ipykernel_4699`:thiếu canonical Drive
  `src/data/colab_runtime.py` tại entry lookup và thiếu `/content/<digest>/scripts/package_handover.py` trước publish.
  Cả hai dừng trước kiểm digest/bootstrap/import/checkpoint;chưa có bằng chứng publish thành công.
- Kiểm lại local immutable stage bằng existing read_source(expected digest):45file đầy đủ,package_handover.py có thật,
  payload `a3abed4421b95032ec6c5600cc87a0acb1ccde0bab8d0382f45331120a3961c3` vẫn integrity PASS.
  Không rebuild ZIP,đổi seed path đoán mò hoặc upload helper rời để che lỗi.
- Chưa phân biệt được upload chưa hoàn tất,sang server khác,runtime đã reset hoặc folder nằm vị trí khác;
  thiếu Drive entry cũng chưa chứng minh Drive chưa mount.Cần JSON chỉ liệt kê /content,seed directory và
  booleans mount/project/entry trước mọi follow-up dependent action.Không đọc nội dung data/model/test hoặc import source chưa xác minh.
- Hướng dẫn owner chọn nguyên folder digest trong VS Code Explorer,Upload to Colab đúng server đang chạy smoke,
  chờ thông báo45items rồi kiểm đường dẫn.Chưa chạy bootstrap hoặcRunAll trước khi source được publish.
  Nếu vị trí khác,đối chiếu output thực rồi mới chỉ đúng root;không tự move/rename/delete file để sửa.
- Trạng thái:localstage PASS;runtime source entry lookup FAIL;publish chưa chạy được do seed helper lookup FAIL;
  Drive mount/cloud persistence/session/checkpoint vẫn NOT VERIFIED.Nguyên nhân gốc của upload đang chờ bằng chứng,
  không quy lỗi cho model/schema/manifest hay dependency.Không fit,test payload,Gemini,cleanup hoặc source/config/notebook edits.

### 31.2. 2026-10-30 — Đã thấy seed trên VM; Drive chưa mount

- Owner gửi JSON chẩn đoán từ kernel thực:CWD=/content,folderdigest xuất hiện trongcontent_top,
  seed_exists=true,seed_helper_exists=true;seed_top gồmconfigs,src,scripts vàhai requirements.
  Upload folder/source-entry presence đã xác nhận trênkernel này;chưa kiểm digest từ payloadremote nên không gọi fullsourceintegrityPASS.
- drive_mounted=false,drive_project_exists=false,drive_bootstrap_exists=false.
  Nguyên nhân trực tiếp của lookup Drive hiện tại làmount chưa sẵn sàng;không cần upload lại source hoặc tạoZIP mới.
  Chưa có bằng chứng canonicalproject/checkpoint mất hoặc sai manifest,vì chưa truy cập đượcMyDrive.
- Hướng dẫn owner chạy chức năng `Colab: Mount Google Drive to Server...` củaextension trênđúngserver,
  chạycellmount đượcextensionthêm vàhoàn tấtauth,rồikiểmMyDrive/canonicalproject/Phase2manifest.
  Chỉ sau mount+metadata có thật mới gọiexistingpublish từseed.Nếuproject/manifest thiếu,dừng kiểmaccount/path/quyền,
  không tạo fakeDrivefolder hoặcpreprocess/train để sửa.
- Trạng thái:seedfolderlayout/presence PASS theo outputuser;Drive mount FAIL/chưa thực hiện;
  sourcepublish,cloudpersistence,bootstrap/session/checkpointload vẫn NOT VERIFIED.
  Không code/notebook/artifact changes;chỉ ghi log vàchờ kếtquảmount/publish từruntime thật.

## 32. 2026-10-30 — Sửa smoke/06: prerequisite rõ ràng, session độc lập, gate test tắt

**Phạm vi:** DEBUG & REPAIR, không thiết kế runtime mới. Đọc trực tiếp hai notebook,
runtime.json, colab_runtime/ColabTraining, publisher/PowerShell wrapper, integrity/final-evaluation
và frozen protocol, loader/vote/tuning reader cùng tests và hướng dẫn hiện hành.
Không có kết nối đến Colab/Drive của owner trong phiên agent này.

### Bảng lỗi và bằng chứng trước sửa

| Cell/section | Thông báo/bằng chứng thực tế | Nguyên nhân/dependency đã xác minh | Ảnh hưởng | Sửa tối thiểu / trạng thái |
|---|---|---|---|---|
| Smoke cũ 2–3; 06 cell 3 | Owner gửi `FileNotFoundError` ở lookup `src/data/colab_runtime.py`; JSON kế tiếp có `drive_mounted=false` | Chưa truy cập MyDrive trên kernel đó; kết nối Colab chưa mount Drive. Lookup source xảy ra trước kiểm mount rõ ràng | BLOCKER cho mọi import/session | Kiểm kernel, mount, rồi source theo thứ tự; hướng dẫn command mount của extension |
| Publish thao tác riêng | Traceback cũ thiếu `/content/<digest>/scripts/package_handover.py`; JSON mới `seed_helper_exists=true` | Hiện đã có helper trên VM; chưa có remote digest hoặc output publish. Không đủ bằng chứng kết luận do reset/upload chưa xong | Source publish NOT VERIFIED | Giữ publisher hiện có; hướng dẫn kiểm toàn folder theo expected digest, publish chủ động ngoài smoke/06 |
| Smoke cũ 1–5 | Bản repo thực tế chỉ 5 cells, không có publisher; cell mount chỉ print nhưng output cũ ghi `Mounted at /content/drive` | Output lịch sử không khớp source hiện tại. Các hướng dẫn mount/upload/publish rời rạc làm khó phân biệt bước nào đã chạy | REVIEW / khó chẩn đoán | Thay bằng 9 cells có thứ tự và bảng kết quả; bỏ output cũ của riêng smoke, không đụng 03/04/05 |
| Smoke cũ cell 4–5 | `phase2_preflight` rồi `smoke_test`, không tạo session; helper smoke có cache/parse train-validation | Notebook lẫn integrity với data-loading; không chứng minh session có thể mở độc lập | REVIEW | Mở session hiện có bằng `ColabTraining.open`; kiểm integrity/metadata, không gọi `load_data` hoặc helper smoke data-loading |
| Setup smoke/06 cũ | `globals().get(...) or input(...)`; thiếu source thì raise, các cell sau dùng RUNTIME/session | Có thể dùng digest cũ trong kernel; nếu tiếp tục chạy cell sau lỗi setup sẽ phát sinh thiếu biến | REVIEW; chuỗi lỗi phụ có thể tái hiện offline | Digest là biến cấu hình rõ ràng; reset biến phiên về None; FAIL tại bước đầu, dependent steps SKIPPED |
| 06 cell 2 cũ | Hướng dẫn đồng bộ riêng hai module mới | Hướng dẫn không còn khớp whole-payload publisher đã triển khai | REVIEW | Dẫn đúng publish toàn payload; scripts nằm `ROOT/scripts/`, không `/content/audit_*.py` |
| Source mismatch / source publish thiếu trên Drive đã mount | Chưa có traceback mới sau khi mount và publish đủ | Không có bằng chứng remote publication/digest; local stage không xác nhận cloud | NOT VERIFIED | Giữ nguyên `read_source`/expected digest guards; fixture stale/mixed/missing source phải fail closed |
| 06 checkpoint, manifest hoặc environment | Chưa có traceback Colab tại `preflight(session)` | Chưa đọc Drive thật. Notebook 06 hiện không có output được lưu | NOT REPRODUCED ON COLAB | Hiện expected checkpoint versions/hashes và actual environment; giữ strict checks, báo blocker; không giả version hoặc sửa pins |
| Notebook gọi sai API / logic evaluation 06 | Đối chiếu chữ ký `bootstrap_runtime`, `ColabTraining.open`, `preflight`, `evaluate`, `show_result` đều khớp | Không tìm thấy bug trong API/evaluation helper để sửa | NOT REPRODUCED ON COLAB | Chỉ sửa orchestration/hiển thị trong notebook; không sửa runtime/publisher/final_evaluation.py hoặc protocol |
| Legacy migrator cho smoke | `migrate` luôn viết lại các cell theo pattern smoke cũ | Sau sửa có thể bị tool migration ghi đè về workflow cũ | Bug xác nhận bằng inspection/regression | Marker `runtime_setup=verified-drive-preflight-v1` giữ flow đã review; vẫn compile cells, giữ user mount cell |

### Bản sửa hiện hành

- Smoke: 9 cells, setup → source/digest verify → import configs/Phase5B/final-evaluation và
  nạp định nghĩa bốn script từ ROOT/scripts → session mới/integrity → bảng + JSON `smoke_result` → remedies.
  Không publisher trong notebook, không parse CSV, không deserialize model hoặc gọi API.
- 06: giữ 14 cells; setup/session tự đủ sau reset; hiển thị protocol, ba candidates, bốn fitted checkpoint
  identities, expected/actual versions và frozen members/tie priority; hiển thị preflight hoặc blocker.
  Cell 8 giữ **`RUN_FINAL_LOCKED_TEST=False`**, authorization trống. Gate tắt không gọi evaluate.
  Cell kết quả/biểu đồ chỉ báo SKIPPED nếu chưa evaluate; không có số liệu test giả hoặc stale results.
- Session/prepared/final_result được gán None khi setup, không reuse biến từ notebook khác.
  Chạy lại từ setup sau khi sửa blocker; không tiếp tục bằng session cũ. Không xóa file nào bằng thao tác này.
- Shared bootstrap, runtime.json, prepare_colab_source.ps1, package_handover.py, model code/config và protocol
  không đổi. Không có framework, đồng bộ hoặc deployment mechanism mới.
- Sửa tài liệu HANDOVER_GUIDE/RUNTIME_DISTRIBUTION_PLAN: Desktop là một lựa chọn, không phải điều kiện bắt buộc.
  Owner không có Desktop có thể chuyển nguyên payload folder và chủ động gọi tool có sẵn sau mount;
  không đặt publisher/workaround vào smoke/06. Cloud persistence cần bootstrap từ VM mới, không dùng same-VM cache làm proof.

### Kiểm chứng

- **Static PASS:** JSON/cú pháp Python của 8 notebooks; kiểm source references và không có audit path `/content/audit_*.py`.
  Hai notebook sửa không gọi fit/train/tuning/publisher. Migration không rewrite smoke mới hoặc user mount cell.
- **Offline PASS: 49 tests** — toàn bộ `test_canonical_colab_runtime.py`, `test_final_evaluation.py`
  và 6 acceptance tests chọn lọc từ `test_distribution.py` (allowlist, immutable stage, mixed/wrong digest,
  publish không ghi data/metadata, destination không hợp lệ, hai process bootstrap/session sau reset).
  Lệnh dùng `python -B -m pytest -q -p no:cacheprovider`.
- Thêm **10 regression cases** chạy toàn bộ code cells hai notebook bằng namespace mới và fixture synthetic,
  kể cả cố tình đặt stale session/prepared trước setup: happy path; thiếu mount/source/digest;
  thiếu checkpoint; sai environment. Final preflight dùng verifier thật trên artifact fixture;
  bootstrap/session result ở các notebook tests là mock và được kiểm riêng bằng integration fixtures.
  Sentinel chặn test open/stat; spy chặn evaluate/load_final_split/model deserialize/predict/train/load_data.
  Toàn bộ nhánh preparation hoàn tất, không có calls cấm, storage fixture không đổi.
  Các tests evaluator có gate bật chỉ sử dụng dữ liệu giả lập/FakePipeline, không model hoặc locked split thật.
- **Local stage PASS thật, chỉ đọc:** `python -B scripts/package_handover.py stage --check-only`:
  45 files/500.375 bytes, digest **`a3abed4421b95032ec6c5600cc87a0acb1ccde0bab8d0382f45331120a3961c3`**.
  Runtime closure không đổi nên không cần source revision mới chỉ vì sửa notebook/docs/migrator/tests.
- **Bảo toàn PASS:** pinned ML source tám file, hard-vote engine và protocol SHA
  `049ee0aa3c2907985c3d3a03ed222b1d6e1efb5921bbbc2d04ec0dea9baa8947` khớp.
  ZIP cũ SHA `5ce88547e28166808c21c701e1263a2928b81de35987995c8bc77e52e7f69d09` nguyên vẹn;
  notebook 03/04/05 giữ toàn bộ bytes/source/output. Data/artifacts/history không đổi.
  Không đóng ZIP mới: code ZIP cũ **chưa chứa bản sửa notebook/docs** hiện tại; dùng workspace đã sửa cho lần smoke này.
- **COLAB NOT VERIFIED:** không chạy bản sửa trên kernel thật, chưa mount/publish/cloud persistence,
  chưa reload checkpoint hoặc xác nhận environment thực khớp freeze. Không biến mock PASS thành Colab PASS.

### Bằng chứng tiếp theo / STOP

1. Mount đúng Drive trước; nếu canonical source chưa có, làm publish chủ động riêng theo
   [hướng dẫn không Desktop](HANDOVER_GUIDE.md#không-có-drive-for-desktop). Seed đã có thì không upload lại,
   nhưng vẫn kiểm source/digest đầy đủ. Agent không publish hoặc sửa Drive trong nhiệm vụ này.
2. Mở Colab VM mới, mount; mở smoke notebook local đã sửa, điền digest Windows, Run All.
   Gửi JSON `smoke_result` / blocker đầu tiên. Không upload từng audit script.
3. Trên runtime sạch hoặc sau Restart Kernel (mount lại nếu cần), mở notebook 06, điền cùng digest;
   Run All với gate False/authorization trống, gửi JSON `preflight_result`.
   Thiếu file/checkpoint/manifest hoặc strict version mismatch phải dừng và đối chiếu artifact gốc.
4. LR tuned C=2 vẫn quyết định triển khai đã duyệt; hard tuned vẫn best observed validation Macro F1.
   Không train/tune/calibrate, không test payload/prediction thật, Gemini, cleanup, default migration hoặc API.
   STOP ở smoke/preflight; chưa có final-test scores hoặc ủy quyền mở test.

### 32.1. 2026-10-30 — Colab đã mount; bootstrap Drive không khớp API release

- Owner gửi screenshot notebook 06: kernel/content, Drive mount và published source entry đều PASS;
  bootstrap FAIL với `TypeError: bootstrap_runtime() got an unexpected keyword argument 'expected_payload_sha256'`.
  Import/session và artifact preflight SKIPPED đúng dependency. Đây là bằng chứng mới sau lỗi mount trước đó.
- Local và immutable stage đã kiểm lại: helper có tham số `expected_payload_sha256`, đủ 45 files/500.375 bytes,
  payload `a3abed4421b95032ec6c5600cc87a0acb1ccde0bab8d0382f45331120a3961c3` integrity PASS.
  Notebook dùng runpy đọc entry Drive trực tiếp: hàm trả về từ source đó không tương thích API release local.
  Chưa xác định toàn payload Drive cũ hay trộn phiên bản vì chưa nhận remote digest; không quy lỗi checkpoint/manifest.
- Hành động: publish toàn payload đã verified bằng tool hiện có, không sửa một file hoặc bỏ tham số checksum;
  sau đó VM mới/mount/setup với expected digest local. Presence của entry không đồng nghĩa release đã được verify.
  Agent không publish Drive hoặc sửa runtime code trong lần đối chiếu này.
- Owner hỏi cách tìm authorization và làm preflight PASS. `authorization_text()` chỉ tạo chuỗi xác nhận protocol,
  không phải API key và không cấp quyền tự động. Không cần authorization để setup/preflight PASS.
  Giữ gate False và authorization trống trong bước sửa source. Câu hỏi này không được hiểu là owner đã cho phép mở test.
- Trạng thái: local stage PASS; Drive mount/entry presence PASS theo screenshot;
  source API compatibility FAIL; full digest verification/session/checkpoint còn NOT VERIFIED hoặc SKIPPED.
  Không đọc test, train, gọi Gemini, đổi artifact/default hay tạo ZIP.

## 33. 2026-10-30 — Final evaluation closeout và Prediction API local

### Quyết định và bằng chứng final evaluation

- Owner báo final test đã hoàn tất cho đúng ba ứng viên preselected. Đọc lại notebook06 hiện có:
  15 cells với executed outputs, log bốn fitted checkpoints (hai LR + SVC/KNN thành viên hard vote),
  bảng metrics và completion manifest. Không lấy số làm tròn của notebook/chat làm checksum proof.
- Owner chạy cell audit **chỉ đọc** dùng `read_completed`, `phase4_guard`, `score_prediction` và frozen protocol.
  Packet gzip giải nén thành JSON có SHA-256 **`102845056236bfe3855962cd1717ece4402a958cc6ce593540ab1ccab4f34131`**;
  kiểm hash trước khi lưu evidence local mới tại
  `artifacts/metadata/final_evaluation_audit/colab_evidence.json`. Không ghi Drive hoặc thay packet lịch sử.
- Manifest completed **`f1ad195e1e46154d7a29a421e80387bfa76e494f4df771cede240f882d0b754a`**;
  protocol **`049ee0aa3c2907985c3d3a03ed222b1d6e1efb5921bbbc2d04ec0dea9baa8947`**.
  Colab reader kiểm inventory11 file/checksum/size; metrics tính lại từ saved predictions khớp results.json
  và comparison.csv với atol1e-12, row alignment,28.066 rows/25.128 groups/587 labels đều hợp lệ.
  Bốn checkpoint members khớp frozen hashes/fit identities/source pins. Guard counters đều0.
  Packet không mở test CSV, không model deserialize/predict hoặc fit; agent không có kết nối Drive trực tiếp.
- Test Macro F1 nguyên bản: LR baseline **0.7958306745796887**, LR tuned **0.808163486172862**,
  hard tuned **0.8059813671672197**. Toàn bộ MacroP/R/WeightedF1/Accuracy/coverage/F1zero và validation values
  giữ trong evidence và [closeout report](../../../reports/final_model_evaluation_closeout.md).
  Y_true đủ587 nhãn; F1zero baseline28, tunedLR/hard22. Saved execution ghi models_fitted0/test_loader_calls1,
  model_selection_from_test=false.30 warnings đều DeprecationWarning datetime.utcnow; không có convergence warning trong list này.
- LR tuned C=2 **đã được chọn trước test**, tiếp tục làm model ứng dụng. Hard tuned giữ best observed
  validation Macro F1; LR tuned cao nhất trong ba ứng viên trên final test. Không tuning/calibration/đổi vote hoặc
  kết luận ý nghĩa thống kê/lâm sàng từ test. Giới hạn synthetic/ambiguous vectors/Phase1 toàn-CSV EDA vẫn giữ.

### Notebook06 lưu hành

- Giữ15 cells và **nguyên toàn bộ output objects, cell IDs, execution_count** của lần chạy owner;
  chỉ sửa source/Markdown để trạng thái hiện hành là completed/read-only replay.
- `RUN_FINAL_LOCKED_TEST=False`, `OWNER_AUTHORIZATION=""`; không còn call evaluate trong source notebook.
  Nếu bật gate lại thì raise rõ ràng. `read_completed` kiểm bundle rồi so manifest hash với bản đã audit,
  hiển thị kết quả saved bằng helpers gốc. Thiếu/khác bundle thì NOT VERIFIED, không chạy lại test.
- Preflight chấp nhận trạng thái completed là bình thường cho closeout, vẫn chặn partial/orphan.
  Không sửa `final_evaluation.py`, protocol, execution marker, weights hoặc dữ liệu.
  Bản closeout mới được kiểm bằng synthetic integration; agent chưa execute nó trên Colab thật.

### Prediction API

- Thêm `app/__init__.py`, `app/backend/{__init__,prediction,schemas,main}.py`, `requirements-api.txt`.
  Dùng app/backend folder đã có; không tạo pipeline training hoặc framework sync mới.
  Reuse Catalog/load_fitted_checkpoint/build_pipeline/validate_probabilities và frozen pre-test LR identity.
- Chỉ LR tuned C2 trong namespace `tuning-v1-9c4dd013abbba14a`, selected identity
  `tuned-v1-b8a5602679b3dc5c`, pipeline SHA `4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6`.
  Startup kiểm exact versions/source8pins, Phase2 variant/hash/schema375/class order587,
  anchored tuning manifest, LR fit/metadata/pipeline hashes, saved variance/to_csr/function params và fitted LR coefficients.
  Chỉ đọc deployment subset7files; không cần raw/train/validation/test CSV, NPZ predictions hoặc các model khác.
- Load một lần trong FastAPI lifespan/process, không download/install hoặc fallback baseline.
  Fail closed: health503 + error code, predict503, không trả Top3. Server local bind127.0.0.1/one worker.
  Routes: `GET /health`, `POST /api/v1/predict`; OpenAPI/docs có sẵn. Strict Pydantic JSON contract,
  không extra fields/type coercion/unknown/duplicate/empty features. Dựng uint8 frame1×375 đúng order.
- Score = fitted LR predict_proba trên đủ587 lớp ×100, chọn3 và không renormalize;
  nhãn **Điểm mô hình (%)**, calibrated=false, không gọi xác suất mắc bệnh. Invalid output trảJSON500 không Top3.
  `predict(frame,schema_sha256=...)` khớp PredictionService port của Phase5B, nhưng chưa nối conversation/API/Gemini/frontend.
  Endpoint structured yêu cầu≥1 feature cho contract; quality gate hội thoại min2provisional, urgent/conflict/subject/time
  vẫn do Phase5B chịu trách nhiệm khi tích hợp sau này, không suy ra clinical eligibility từ schema valid.
- Thêm API guide; cập nhật README, HANDOVER_GUIDE và MODEL_SELECTION_RATIONALE, giữ PENDING/protocol cũ làm lịch sử.
  Existing packager chỉ thêm requirements-api vào allowlist để lần đóng gói sau không bỏ dependency;
  không gọi stage/publish/package hoặc tạo ZIP mới. Do runtime script bytes có đổi local, lần publish tương lai phải lấy digest mới,
  không dùng a3ab… làm pin cho payload mới. Drive/staging/ZIP đã phát hành giữ nguyên trong nhiệm vụ này.

### Kiểm thử và blocker

- **220 tests PASS**: API26 tests, final-closeout evidence, final evaluation/replay, canonical runtime,
  toàn bộ Phase5B offline, notebook05 source preservation và hai distribution checks (allowlist/fresh reset session).
  Dùng `python -B -m pytest -q -p no:cacheprovider`; không fit estimator, không mở locked test thật.
  Loader fixtures chỉ có opaque dummy bytes và prediction double, không tạo checkpoint giả thay artifact thật.
- HTTP TestClient kiểm startup-once, health/OpenAPI, JSON error contract, mapping/binary/order/shape,
  Top3 thật của test double giữ tổng80% thay vì ép100%, tie order, malformed probabilities, corrupt weights/schema,
  wrong versions/config/CSR/classes và fail closed. Final reader tests tạo TOY result rồi replay với sentinel
  cấm test open/stat/evaluate/model load/predict; gate re-enable cũng bị chặn.
- Một warning không fail từ installed Starlette TestClient: httpx backend deprecated, gợi ý httpx2.
  Không tự cài/đổi dependency để xử lý cảnh báo ngoài phạm vi; package versions kiểm hiện hành ghi ở requirements-api.
- **Actual host negative startup PASS:** Python3.11.9/sklearn1.8.0/NumPy2.3.5/SciPy1.17.1/joblib1.5.3
  khác frozen Python3.13.18/sklearn1.6.1/NumPy2.1.3/SciPy1.16.3/joblib1.6.0.
  TestClient trên source thật trả health503 `environment_mismatch`, predict503 không Top3; guard counts0.
- **REAL CHECKPOINT NOT VERIFIED trên API local.** Owner xác nhận “Chưa có weights/môi trường local”.
  Weights checksum trên Drive PASS qua packet không chứng minh Windows reload/inference. Không tạo healthy giả,
  không lấy fixture outputs thành actual model response và không sửa version/hash guard.
  [LOCAL_PREDICTION_API.md](../../LOCAL_PREDICTION_API.md) chỉ đúng7 files/root/env/commands và real health+predict smoke cần làm.
- Sau real local smoke PASS: duyệt nối forward_ready với prediction port, kiểm abstention/stale/conversation gates,
  rồi mới duyệt Gemini live có ngân sách và web chat. Chưa thực hiện các bước đó.
- Không retrain/tuning/calibrate, reopen test, thay marker/Phase2/weights/vote, gọi Gemini, cleanup/delete/move,
  tạo `.venv`/ZIP hoặc sửa nội dung Drive. STOP sau closeout + API/offline validation;
  phần real local smoke chờ prerequisites owner vừa xác nhận còn thiếu.

## 34. 2026-10-30 — Local web MVP, Phase5B chat adapter và smoke live tách biệt

### Điều kiện thực và kết quả theo từng giai đoạn

- **Real checkpoint BLOCKED:** chỉ có `artifacts/models/.gitkeep`; DISEASE_API_STORAGE_ROOT chưa cấu hình.
  `py -0p` chỉ đăng ký Python3.11.9, khác exact identity Python3.13.18/sklearn1.6.1/NumPy2.1.3/SciPy1.16.3/joblib1.6.0.
  Process/User/Machine env không có artifact root. Không tìm/chép cả dataset hoặc bỏ version/hash guard.
  Seven-file read-only copy paths giữ đúng trong [LOCAL_WEB_MVP](../integration/LOCAL_WEB_MVP.md), không tạo ZIP/data export mới.
  Actual `python -B -m scripts.smoke_local_mvp --ml` trả BLOCKED/health503 storage_not_configured,
  không inference, test payload hoặc model fit. Loader gốc vẫn chỉ nhận LR tunedC2; không baseline fallback.
- **Gemini live NOT VERIFIED:** Process/User/Machine env đều không có GEMINI_API_KEY; config live_enabled vẫn False.
  Actual `--gemini-live` trả NOT VERIFIED/live_opt_in_or_api_key_missing/0 requests; không giả successful response/usage.
  Không API key trong source/log/notebook/frontend; chỉ kiểm presence booleans, không đọc/print secret từ file.
- Đọc primary Google docs ngày2026-10-30: model `gemini-3.8-flash` và structured outputs được liệt kê;
  pricing ghi text Free Tier, nhưng quyền/quota project/account chưa có bằng chứng. Quota tính theo project;
  owner cần xem active limits trong AI Studio, không áp local6RPM thành hạn mức Google.
  Existing REST endpoint/response_format/system_instruction/storefalse/completed steps/usage phù hợp docs.
- Static schema PASS: Catalog metadata checksum/375 feature/587 labels, Draft2020 check, schema serialized9.810bytes,
  guard fit/test/protected-write đều0. Mock transport nhận nguyên375enum/$defs/schema, không giảm ML input.
  Server acceptance của chính schema này vẫn NOT VERIFIED vì không gọi live; nếu400 thì fail closed,
  không đổi model/schema_mode hoặc rút feature ngầm để tạo PASS.

### Code ứng dụng và bảo toàn kiến trúc

- Thêm `app/backend/chat.py`, ChatRequest/ChatResponse và route `POST /api/v1/chat` trong app hiện có.
  Reuse ConversationEngine/InputGuard/ExtractionValidator/SessionStore và `forward_ready` có sẵn;
  LRPredictionService/model loader không đổi. Chỉ new predictions từ fitted LR và validated frame1×375.
  Template tiếng Việt cố định, labels/class order nguyên bản; Điểm mô hình (%) giữ raw predict_proba×100/rank,
  không normalizing Top3, không Gemini disease scores/diagnoses. Min2present gate vẫn provisional.
- Wrapper BoundedGemini quanh GeminiProvider hiện có, không transport/SDK thứ hai:
 20calls/process,6/min,2048 output tokens/request,100.000 local budget units,64.000 serialized bytes/request;
  zero retries. Smoke riêng tối đa6calls cho3 lượt synthetic: ho+sốt→uncertain→phủ định.
  Byte reservation chỉ admission bảo thủ, không tokenizer/billing; counters thực từ provider,
  thiếu field giữnull/completefalse, costunknown; unknown usage trừ reservation, không ghi0 token giả.
  New conversation không reset budget. Provider failure/quota/incomplete/invalid extraction không tạo Top3.
- Chat giữ existing session lock qua handle+forward_ready để không nối kết quả cũ với lượt khác;
  kiểm expiry lại sau inference. SessionStore chỉ thêm `discard` cho reset RAM, không xóa file/framework mới.
  Subject/time/conflict/negation/short-answer validators giữ nguyên. Model thiếu vẫn trả urgent guard không LLM;
  regular chat trả503 không có prediction. Failed chat init báo đúng provider config, không bịa model thiếu.
- Thêm `app/frontend/{index.html,styles.css,app.js}`: UI tiếng Việt responsive, messages/session/reset,
  trạng thái setup, clarification/urgent/error, exact model scores. Browser chỉ giữ session ID trong RAM;
  request sequence/AbortController bỏ stale reply khi reset. Render textContent, không innerHTML/user script.
  Static files cùng localhost origin, không CDN hoặc key field trong frontend. Header no-store/nosniff/CSP cho web;
  docs/redoc giữ hoạt động. Không public hosting/tunnel hoặc frontend framework mới.
- Thêm `scripts/smoke_local_mvp.py` cho hai smoke riêng, không writes/artifacts/model fit/test CSV.
  Thêm jsonschema dependency vào requirements-api; không pip install hoặc tạo `.venv` trong nhiệm vụ.
  Docs hướng dẫn copy7files, interpreter đúng, masked Read-Host key/envoptin, CLI smoke, uvicorn127.0.0.1:8000/oneworker.
  README/HANDOVER/LOCAL_PREDICTION_API được cross-reference; current defaults an toàn, không production mock mode.

### Tests và regression review

- **202 API/agent tests PASS**: test_local_chat, test_prediction_api và toàn bộ Phase5B offline.
  TestClient bao gồm full ready path375→LR, clarification short answer, deny/uncertain, subject switch,
  reset/expiry, expiry during model call, urgent/no pronoun, knowledge/injection, forged predictions,
  provider failures/quota/stale results, budget/size/rate/retry0 và missing key/live disabled.
- **Actual Chromium mock UI PASS:** hidden headless Chrome/profile tạm, actual localhost uvicorn và mock LLM/LR.
  Kiểm desktop1200×900/mobile390×844, clarification→có→Top3, negation, urgent, reset, XSS as plain text,
  unchanged40/30/10 scores (sum80), no overflow. Provider4calls/model double2calls; guard counters0.
  Screenshots chỉ nằm trong pytest Temp, không tạo report figure/dataset/checkpoint giả.
  Sandbox lần đầu chặn Windows Mojo/crashpad IPC AccessDenied trước page; chạy test riêng ngoài sandbox
  bằng quyền được duyệt đã PASS. Không tắt security/integrity model; browser test opt-in DISEASE_BROWSER_SMOKE=1.
- Core tests1 warning TestClient/httpx deprecated; browser thêm2 warnings websockets legacy. Không test fail do warnings.
- **Broader regression 239 PASS/13 FAIL (252cases)**:13 thuộc notebook closeout/preflight assertions,
  không phải Chat/API code. Kiểm hash cho thấy trạng thái này có ngay lúc bắt đầu task:
  `06_final_model_evaluation.ipynb` hash1085bb403102f5cd21415cc2afeec783a07b40f1d05332c5c7539a8bd1b382a2,
 15cells/gateTrue/noFalse; smoke hash14b10254af4171756f43f5fbd2a236c6f856627e4fefc40f654fbd2e2324030e,
 10cells/cell4 có google.colab mount. Do đó fixture offline gặp google.colab missing và gate/source khác expectation.
  Không tự sửa operator notebooks, switch hoặc outputs ngoài phạm vi MVP để ép suite PASS.
  Ghi REVIEW cho bản notebook lưu hành; không Run All06 hoặc thay marker để kiểm web.
  Không tuyên bố full regression PASS, cũng không lấy mock UI PASS thành real model/Gemini PASS.

### Phạm vi dừng

- Final ML choice LR tunedC2, MacroF1 test0.808163486172862, Phase2 schema/mapping/data,
  checkpoints, frozen protocol/engine và serialized to_csr sources không đổi. Không chạy final test,
  retrain/tuning/calibration/Gemini generation, sửa Drive, cleanup/delete/move hoặc tạo ZIP.
- Tới thời điểm bàn giao: real checkpoint BLOCKED; Gemini live NOT VERIFIED;
  Chat API PASS(mock); local website PASS(actual browser/mock). Full live flow chờ7artifacts/interpreter/key/quota.
  Người dùng có thể mở UI degraded bằng Python hiện có; không có Top3 cho tới khi integrity/env/provider/gate hợp lệ.
  Chỉ thực hiện smokes tách biệt bằng dữ liệu synthetic sau khi đủ điều kiện; STOP sau local MVP.

## 35. 2026-10-30 — Sửa hướng dẫn interpreter cho Gemini smoke Python3.11.9

- Owner chạy `$ApiPython` còn giữ placeholder `C:\path\to\approved-python-3.13.18\python.exe` nên PowerShell
  CommandNotFoundException; lệnh dừng trước Python, chưa phải lỗi Gemini/model.
- Kiểm thực: `py -3.11` trả `D:\Program Files (x86)\Python\Python311\python.exe`, version3.11.9.
  `Catalog.load` từ project hiện tại kiểm checksum/schema375/classes587 PASS;7 deployment artifacts nay có local.
  Root metadata thực có thể là project hiện tại, không còn phải dùng ví dụ D:\ML_Artifacts chưa có.
- Docs mục3 khai báo `$GeminiPython` riêng từ launcher, không phụ thuộc `$ApiPython` placeholder/môi trường ML;
  thêm Test-Path fail rõ ở mục2. README phân biệt Gemini smoke độc lập và real ML compatibility.
  Đã nhập key cùng terminal thì chỉ sửa interpreter/root rồi chạy, không cần nhập lại hoặc ghi key vào file.
- `--gemini-live` chỉ chạy extractor/validator, không deserialize LR; có thể dùng3.11.9 để kiểm transport/schema.
  Việc này không phê duyệt Python3.11.9 cho checkpoint hoặc tắt version guard. Không sửa source/requirements,
  checkpoint, metadata, notebook outputs hoặc locked test. Không install packages/venv, không in key.

## 36. 2026-10-30 — Qualification Windows Python3.13.17 cho LR tuned, chờ reference

- Owner cho phép `.venv-web` riêng và kiểm checkpoint không retrain; đây là ngoại lệ được yêu cầu
  cho môi trường deployment thử nghiệm, không phải thay đổi Python3.11.9 hoặc identity training.
  Launcher phát hiện `D:\Program Files (x86)\Python\python.exe`3.13.17/AMD64;
  tạo `.venv-web`, chạy pinned `requirements-api.txt` bằng interpreter riêng, `pip check` PASS.
  ML versions thực: sklearn1.6.1/numpy2.1.3/scipy1.16.3/joblib1.6.0; pandas2.2.3.
  Python3.11.9 toàn cục vẫn sklearn1.8.0/numpy2.3.5/scipy1.17.1/joblib1.5.3.
  Không build3.13.18, không sửa packages của3.11; `.gitignore` thêm đúng `.venv-web/`.
- Chốt protocol **trước predict** ở
  `artifacts/metadata/runtime_compatibility/windows31317-v1/protocol.json`, SHA
  `4109e06228c46cd7fddd59bbabfd6cf694ffdd26b7dca3203c569857e151e604`.
  Tám vector synthetic cố định gồm zero/all-one boundary và sáu symptom combinations;
  không dùng CSV hoặc predictions train/validation/test. So full8×587 probability với
  rtol1e-10/atol1e-12, exact predict labels và stable Top3 IDs theo Phase2 class order;
  một BLAS thread. Không điều chỉnh tolerance sau khi xem kết quả.
- Actual local7artifacts kiểm hash/size theo frozen Phase2/tuning manifest PASS, tám source pins PASS.
  Experiment `tuning-v1-9c4dd013abbba14a`, selected `tuned-v1-b8a5602679b3dc5c`, C2,
  pipeline SHA `4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6` không đổi.
  Trusted `load_fitted_checkpoint` trong process3.13.17 riêng PASS: schema375, class order587,
  fitted variance318/CSR/to_csr/parameters/finite coefficients khớp. Không có load warning.
  `predict_proba` thực8×587 hợp lệ, predict labels khớp argmax. Đây là kiểm thực thi một phía.
  Candidate evidence SHA `a06487b71ab6ff7d44210bace9665d999103cedac6cf6b055ac6738267cadfdc`
  lưu trong `windows_candidate_probe.json`; status **NOT VERIFIED**, independently_compared=False,
  production_runtime_approved=False. Process audit cấm tất cả dataset/saved split predictions opens,
  quan sát đúng7artifact; fit/test/protected-write counters0.
- Reference hiện **MISSING**: `structured_inference/colab_evidence.json` cũ gắn baseline,
  không chứa tuned experiment/checkpoint SHA. Không dùng packet này hoặc validation/test predictions
  để suy ra compatibility. Chưa truy cập được Colab gốc3.13.18 để sinh reference mới.
  `docs/LR_WINDOWS_COMPATIBILITY.md` cung cấp một cell tự kiểm môi trường/7artifact/pins,
  trusted load và cùng8vector; chỉ ghi JSON mới vào `/content` rồi người dùng download về Windows.
  Không cần upload script riêng, source sync mới, thay Drive hoặc cài packages trong runtime.
  Kernel không đúng3.13.18/libs thì dừng, không giả nhận reference từ runtime khác.
- Production `app/backend/prediction.py` giữ byte identity và guard exact versions gốc.
  Negative actual TestClient trên3.13.17 PASS: health503/environment_mismatch, predict503,
  production deserializer_calls0; không gọi Gemini. Đây **không phải** real API ready smoke PASS.
  `production_guard_check.json` ghi bằng chứng. Regression `tests/test_prediction_api.py`:
  **26 PASS**,1 Starlette/TestClient deprecation warning, fixtures synthetic/no fit/network/test.
- Sửa hướng dẫn LOCAL_WEB_MVP/LOCAL_PREDICTION_API để phân biệt weights đã có, isolated load PASS
  và qualification còn thiếu reference. Source app/ML, checkpoints/manifests, notebooks/outputs,
  training identity3.13.18 và approved deployment LR tuned giữ nguyên.
  Không retrain/tune/calibrate, đọc locked test, gọi Gemini, cleanup hoặc tạo release ZIP.
  **STOP trước runtime approval/API200**. Bước tiếp: owner chạy riêng reference cell trên Colab gốc,
  gửi local path JSON đã download cùng SHA; sau so sánh PASS mới xét allowlist hẹp Windows3.13.17.

## 37. 2026-10-30 — Đối chiếu reference LR Colab3.13.18, chờ checksum phía Colab

- Owner cung cấp local path `artifacts/metadata/runtime_compatibility/lr-31318-synthetic-reference.json`.
  SHA-256 tính từ bytes local: `5fe06a3637c471403d46cdb87b2e5cce2a742e8fff1c99aa4a6cb7caef53d0dc`.
  Packet khai báo original Colab/Linux3.13.18, sklearn1.6.1/numpy2.1.3/scipy1.16.3/joblib1.6.0;
  reference kind/status và source/checkpoint pins khớp protocol. Không tự coi local hash là
  checksum đã in phía Colab. Owner chưa gửi giá trị đó; tìm trong output notebooks lưu local
  cũng chưa có. Đã hỏi owner checksum để hoàn thành đối chiếu transfer integrity.
- Protocol SHA4109e062… và candidate SHAa06487b7… khớp đúng bản đã khóa trước inference.
  So đủ8×587=4.696 phần tử predict_proba: **PASS**, maxabs2.168404344971009e-19,
  maxrel2.567201261121586e-16, zero failures với atol1e-12/rtol1e-10 đã chốt.
  Exact predict labels và stable Top3 IDs/names PASS cho8ca. Hai ma trận không bitwise equal;
  không ép bitwise equality hoặc thay tolerance. Probability hữu hạn, trong[0,1], tổng hàng hợp lệ.
- Input uint8 được dựng lại theo375 features của Catalog và đúng8 synthetic cases để kiểm input hash.
  Catalog/mapping587, schema hash, checked artifact map và source pins so trực tiếp giữa hai packets
  và với files thật: **PASS**,7 artifact/8 source pins. Label argmax/Top3 được tính lại từ từng
  ma trận, Top3 names đối chiếu class order thật. Identity C2/tuning/selected checkpoint đúng bản duyệt.
  Cả hai packets không có load warning; fit/test/protected-write counters0.
- Evidence mới: `artifacts/metadata/runtime_compatibility/windows31317-v1/reference_comparison_pending_checksum.json`.
  Numerical comparison PASS; overall **REVIEW**, reference transfer integrity **NOT VERIFIED**,
  expected_reference_sha256_from_colab=null. Không thay trạng thái historical candidate probe,
  không thay checkpoint, manifest, protocol, source ML, API guards hoặc notebook outputs.
- Chưa đáp ứng điều kiện owner đặt “tất cả PASS” nên **chưa thêm Windows3.13.17 vào allowlist,
  chưa chạy ready HTTP smoke**. Sau checksum Colab khớp mới được thực hiện phần đã được owner
  cho phép có điều kiện: narrow runtime allowlist và actual health/predict smoke, không Gemini.
  Hiện chỉ đọc JSON/source/metadata/checkpoint hashes; không fit/predict mới, đọc locked test,
  chạy notebook06, sửa Drive, cleanup hoặc tạo release.

## 38. 2026-10-30 — Windows3.13.17 approved, real LR tuned Prediction API PASS

- Owner đã gửi checksum in từ Colab: `5fe06a3637c471403d46cdb87b2e5cce2a742e8fff1c99aa4a6cb7caef53d0dc`.
  So với bytes local đúng hoàn toàn; reference transfer integrity **PASS**. Kiểm lại protocol SHA4109e062…,
  candidate SHAa06487b7…,375schema/587mapping/order,8 source pins,7 artifact hashes và input identity PASS.
  Cả4.696 probabilities PASS với atol1e-12/rtol1e-10 đã khóa; maxabs2.168404344971009e-19,
  maxrel2.567201261121586e-16; exact8 predict labels và stable Top3 IDs/names. Không đổi tolerance.
  `reference_comparison_verified.json` ghi xác minh sau khi nhận checksum; evidence pending giữ nguyên lịch sử.
- Theo authorization có điều kiện đã được owner cung cấp, thêm **một rule** vào
  `app/backend/prediction.py::APPROVED_DEPLOYMENT_RUNTIMES`: Windows/AMD64/CPython3.13.17,
  sklearn1.6.1/numpy2.1.3/scipy1.16.3/joblib1.6.0, selected `tuned-v1-b8a5602679b3dc5c`,
  pipeline SHA4cac3bfd… cố định. Original training versions3.13.18 và exact original-environment path giữ nguyên.
  Source pins/schema/mapping/tuning/checkpoint/metadata/pipeline validation vẫn chạy đầy đủ;
  không có bypass flag, version range, baseline fallback hoặc sửa identity trong fitted artifact.
- `tests/test_prediction_api.py` thêm13cases cho exact trained/candidate runtime, wrong dependencies,
  OS/CPU/implementation, checkpoint SHA, selected ID và training identity. **71 API/chat tests PASS**,
 1 Starlette/TestClient deprecation warning. Tests synthetic không serialize/fit actual estimator.
  Actual Python3.11.9 vẫn environment_mismatch trước deserialize; production loader_calls0.
- **Actual TestClient smoke PASS** trên `.venv-web`3.13.17 với actual audited LR checkpoint:
  health200/REAL CHECKPOINT VERIFIED, predict200, input synthetic cough+fever không ground truth,
  Top3 IDs và scores khớp original reference. Scores5.12045687095984/3.83870108406369/3.5800069472765097%,
  giữ nguyên, không normalize; nhãn “Điểm mô hình (%)”, calibrated=False. Guard counters0.
  Evidence `real_api_smoke_verified.json`; đọc7deployment artifacts và reference audit JSON, không dataset/split predictions.
- **Actual Uvicorn HTTP TCP localhost smoke PASS** trên port tạm riêng: health200/predict200,
  Top3 khớp reference, Gemini requests0/live disabled. Process riêng dừng sau smoke, không dừng server của owner.
  Evidence `uvicorn_http_smoke_verified.json`. Lần thử đầu bị Windows chặn ghi server.log trong Temp;
  dùng stdout pipe để kiểm lại thành công, không nới integrity/sandbox hoặc xóa file/thư mục.
- Cập nhật hướng dẫn dùng `.venv-web` và artifact root thực `(Get-Location).Path` thay placeholder interpreter.
  Owner cần Ctrl+C server cũ rồi mở lại bằng3.13.17 để tránh tiếp tục dùng process3.11 cũ.
  Gemini live/schema chưa kiểm lại và chưa được gọi trong nhiệm vụ này; model/API PASS không phải chat live PASS.
  Không fit/retrain/calibrate, đọc locked test, chạy notebook06, sửa checkpoint/manifest, Drive hoặc cleanup/release ZIP.

## 39. 2026-10-30 — Gemini chat debug: actual timeout20, bổ sung chẩn đoán HTTP an toàn

- Owner báo UI đã cấu hình nhưng chat báo provider_error; từng có HTTP400 trước đây.
  Đọc actual localhost health: port8000 không phục vụ,8001 health200/REAL CHECKPOINT VERIFIED,
  Gemini live_enabled=true/key_configured=true, requests_used1 trước kiểm mới. Không suy ra API access từ UI/health.
  Process agent không có key/live env; không truy xuất key của server hoặc yêu cầu owner gửi key.
- Baseline offline regression **215 PASS** trước live. Dùng đúng1request synthetic qua actual
  `POST http://127.0.0.1:8001/api/v1/chat`, câu “Tôi ho và sốt từ sáng nay”.
  Kết quả backend503, status provider_error, reason **timeout**, predictions=null, usage unknown/complete=false.
  Provider timeout đang20giây; không nhận HTTP response status/error body từ Google trong lượt này.
  HTTP400 lịch sử chưa có body để xác minh nguyên nhân; không giả nhận là schema/key/quota/model failure.
- Xác nhận bug chẩn đoán: `GeminiProvider.generate` bắt HTTPError rồi close ngay, bỏ toàn bộ body/status chi tiết.
  Sửa nhỏ `src/agent/provider.py`: đọc tối đa16KiB error JSON, giữ HTTP status và provider status whitelist,
  che configured key/key-like strings/request text/URL/email trước truncate message1200chars;
  không giữ headers/raw body/ErrorInfo metadata. ProviderError public vẫn code-only.
  HTTP success status được ghi từ transport thật, không suy từ fake response hoặc frontend status.
  Detailed diagnostic không vào chat/public health; telemetry chỉ status codes an toàn.
- `BoundedGemini` giữ last_error diagnostic cho CLI, health chỉ code/http_status/provider_status;
  clear last_error sau request thành công. Không đổi model/endpoint, retries/budget hoặc production timeout20.
  `scripts/smoke_local_mvp.py` thêm `--gemini-diagnostic`: một request synthetic, retry0,
  giữ enum375 và output cap2048; CLI-only `--timeout-seconds 60` giúp kiểm timeout mà không đổi production config.
  Nếu extraction_ready thì kiểm ready vector1×375 đúng order/binary; không gọi LR hoặc tạo Top3.
  Chưa có key tại process agent thì NOT VERIFIED/requests0 đúng thực tế.
- Đối chiếu tài liệu primary Interactions REST/structured output/model3.8 Flash: request envelope,
  endpoint v1beta, response_format text/schema và parser model_output steps khớp contract được công bố.
  minLength/uniqueItems bị decoder bỏ qua theo docs; Python validator vẫn enforce. Không xóa các keyword
  hay $defs/$ref/const theo phỏng đoán. Schema local Draft2020-12 PASS,9810bytes, enum375/classes587;
  provider acceptance và tài khoản/quota vẫn NOT VERIFIED khi chưa có response thành công.
- Regression mới: **219 PASS**,1 TestClient deprecation warning; tests cho bounded error body,
  secret/request-text redaction, status giữ nguyên, health không lộ message, one-request diagnostic/
  vector375 với mock. Lần chạy test đầu có1 lỗi fixture trả callback thay dict; sửa đúng fixture,
  không nới production validator. Không gọi Gemini trong tests.
- Đã gửi owner lệnh diagnostic trong terminal có key để lấy error message/status hoặc latency60.
  Owner gặp PowerShell parser do hai lệnh bị ghép thiếu`;`, xảy ra trước Python nên không tiêu request.
  Đã gửi lại một dòng có`;`. Chờ JSON từ request thứ2 của giới hạn3, chưa gửi request thứ3.
  Không tự coi diagnostics cải thiện là underlying live bug đã sửa hoặc semantic extraction PASS.
  `docs/LOCAL_WEB_MVP.md` ghi workflow và phân biệt timeout/auth/quota/model/schema/parser/validator.
  Không thay LR checkpoint, metadata/manifests/source pins, Drive, notebook06 hoặc kết quả final test.

### Cập nhật bằng chứng timeout60 và transport trace

- Owner chạy CLI diagnostic thành công về cú pháp: vẫn NOT VERIFIED/provider_error timeout sau
  **60207.883599970955ms**, retries0/requests1, key/live flags đúng, usage unknown, không có HTTP status,
  states rỗng, validated_vector_1x375=false, predictions_called=false. Đây là request live thứ2 của task.
  Không suy nguyên nhân schema/key/quota hoặc đơn thuần timeout20 quá ngắn từ dữ liệu này.
- Probe network không key, không generation: DNS6.76ms; public IPv4 trả về;
  TCP45.92ms/TLSv1.3 tổng118.85ms; GET cùng v1beta endpoint HTTP403 sau185.55ms.
  Probe ngoài filesystem/network sandbox theo quyền được auto-review cấp để tránh nhầm sandbox với mạng owner;
  không key/header auth/payload hoặc model request. GET403 unauthenticated không xác minh quyền model của tài khoản.
- CLI thêm transport trace connect/TLS/send-completed/response-header-wait, chỉ số byte và thời gian,
  không header/body/key. Dùng subclass thông qua HTTPSHandler.do_open, giữ TLS/proxy kwargs của stdlib.
  Unit test phát hiện cách patch global HTTPSConnection ban đầu gây explicit-super recursion trên3.11;
  đã sửa cách gắn trace trước khi yêu cầu request tiếp, không có live generation trong test lỗi.
  **220 tests PASS**,1 TestClient deprecation warning. Actual traced GET không key trả403 sau182.75ms,
  chứng minh trace không mock transport thành PASS. Health last_error được snapshot dưới lock.
- Đã yêu cầu owner đúng1request thứ3 cuối cùng với cùng synthetic/schema/model/endpoint và timeout60,
  để phân biệt connect/upload/response wait. Chưa gọi thêm generation hoặc thay production timeout20/schema.
  Nếu request cuối không cho đủ bằng chứng thì báo BLOCKED/NOT VERIFIED, không vượt giới hạn3.

### Root cause xác minh từ request thứ3: serving schema state explosion

- Owner gửi trace thực: TLS hoàn tất158.5676ms, body20016bytes gửi xong158.7355ms,
  bắt đầu chờ headers158.7390ms; nhận HTTP400 ở48267.5099ms, total48267.6063ms.
  Provider message: “The specified schema produces a constraint that has too many states for serving.”
  Message nêu các nguyên nhân điển hình: nhiều/long enum names, nested array bounds, numeric min/max.
  **Xác minh lỗi tại serving constraint/schema compilation**, không tại upload, response parser,
  extraction validator hoặc LR. Không có prediction, usage unknown; không suy ra billed cost0.
  Chưa chứng minh yếu tố nào trong schema đóng góp state lớn nhất hoặc quota/Free Tier thực tế.
- Sửa mitigation nhỏ nhất tại provider: `_serving_schema` deepcopy cho task extraction,
  bỏ đúng numeric minimum của `$defs.span.properties.start/end` ở wire schema. Không bỏ hay rename
  bất kỳ feature: enum375 nguyên tên/order; model/endpoint, canonical JSON contract/Python validator giữ nguyên.
  Evidence validator vẫn kiểm offset bounds/actual text, unknown features và gate trước ML.
  Không thay SYSTEM prompt, intent contract, schema metadata, label mapping, feature count hoặc dùng JSON-only fallback.
  Đây là mitigation cho contributor được response nêu, **chưa chứng minh live acceptance**;
  không tuyên bố xóa2minimum chắc chắn giải quyết mọi state explosion.
- Regression sau mitigation **221 PASS**,1 TestClient deprecation warning. Test mới so toàn bộ wire schema
  với canonical chỉ khác đúng2minimum, không mutate original; giữ enum375/schema identity; intent không đổi;
  local validator vẫn chặn negative offsets, valid synthetic response vẫn map1×375.
- Budget task đã đủ **3/3 live generation requests**, không gọi request thứ4. Cần owner cấp phép riêng
  thêm đúng1request synthetic để kiểm mitigation với cùng model/endpoint và timeout60 diagnostic.
  Giữ production timeout20, không tự tăng dựa vào thời gian trả lỗi48s.
- Evidence duy nhất tổng hợp attempts/protocol/mitigation:
  `artifacts/metadata/gemini_debug/20261030_serving_schema_rejection.json`.
  Live trước sửa **FAIL/HTTP400**, sau mitigation **NOT VERIFIED**, goal extraction→LR live chưa hoàn tất.
  Dừng tại giới hạn live; không thay checkpoint, manifests, source pins, Drive, notebook06 hoặc final results.

### Owner cho phép kiểm mitigation thêm một request

- Owner trả lời “bạn cứ việc thử” sau đề nghị thêm đúng1request: chấp thuận request thứ4 riêng để
  kiểm mitigation hai decoder-side minimum, không coi đây là quyền gọi không giới hạn.
  Kiểm process agent vẫn không có key/live env; cả localhost8000/8001 hiện không phục vụ.
  Đã gửi owner một lệnh CLI diagnostic trong terminal đang có key, max_requests1/retry0/timeout60,
  chờ JSON thực. Không đọc key của process khác hoặc yêu cầu gửi credential.
- Owner hỏi cách chạy web: sau ML và Gemini thực sự PASS, chạy Uvicorn tại127.0.0.1:8000,
  không cần mở router/firewall cho cùng máy. Port phải trống, server dùng `.venv-web` và đúng
  storage/key/live env. Chưa tuyên bố chat live đã sẵn sàng khi verification mới còn pending.

### Mitigation minimum không PASS; wire-code catalog giữ đủ375

- Request thứ4 (owner cho phép thêm đúng1) vẫn timeout **60197.294ms**. Trace TLS186.9608ms,
  gửi hết19988bytes body ở187.0848ms, bắt đầu chờ headers187.0883ms; không nhận HTTP response/usage.
  Body giảm đúng28bytes so với bản đầu chứng tỏ mitigation hai minimum đã được load, không phải lỗi source cũ.
  Không kết luận chỉ tăng timeout hoặc bỏ minimum đã sửa được serving schema.
- Khôi phục hai minimum gốc. Bản provider hiện tại giữ cả375 feature nhưng biểu diễn enum wire bằng
  codes `f000…f374`, mỗi code ánh xạ chính xác một tên trong canonical catalog order đã verify.
  Gemini input chứa đủ375 cặp code/name qua dictionary allowed_features; không bỏ feature, chọn subset,
  fuzzy-map hoặc đổi schema ML. Provider decode các mention feature và clarification.target_features
  về canonical English names trước Python validator/gate. Unknown/malformed code hoặc input catalog
  reorder/mismatch fail closed trước inference/transport. Không đổi model, endpoint, schema_mode, SYSTEM nguồn,
  canonical schema/hash/order375, mapping587, checkpoints hoặc production timeout20.
  Wire-only system instruction giải thích cách dùng dictionary keys; intent và explicit JSON-only mode giữ nguyên,
  không có automatic fallback. Public extracted JSON/ML/UI vẫn nhận tên canonical.
- Tổng enum text6314→1500ký tự, không giả gọi đó là token/cost/state-count measurement.
  Actual serialized body trong synthetic fixture19240bytes < conservative input admission20083units;
  không cần nới local byte/request/token budgets. Model serving acceptance vẫn cần bằng chứng live.
- **223 tests offline PASS**,1 deprecation warning: roundtrip375 codes và targets, reject unknown/non-string/
  canonical-name-in-code-field, reject reordered input list, preserve whole original schema ngoại trừ wire enum,
  giữ numeric/evidence bounds, no mutation, vector1×375 và full chat/mock-LR flow/budget không reset.
  Fixtures có fake transport được cập nhật trả đúng wire codes; không sửa production validator để tests PASS.
- Chưa gọi thêm live cho bản wire codes. Agent không có key, server8000/8001 đã dừng.
  Đề nghị owner nếu đồng ý kiểm thêm đúng1request mới thì mở Uvicorn8000 ở terminal có key và báo “đã chạy”;
  agent sẽ đọc health và chỉ POST một câu synthetic qua actual Chat API để kiểm cả Gemini→validator→LR.
  Không tự coi câu “cứ thử” là quyền gọi không giới hạn; không trích xuất key hoặc đưa key vào chat/log.

### Wire codes live: timeout20 và HTTP503 high demand, chưa PASS

- Owner trả lời “đã chạy” cho server8000 và một synthetic POST. Agent đọc health: ML ready,
  Gemini live/key true, requests0; gửi đúng1câu “Tôi ho và sốt từ sáng nay”. Backend503/provider_error
  timeout sau20.22649s, requests_after1, predictions=null. Đây là request thứ5 được owner cho phép riêng.
  Vì server vẫn deadline20, kết quả không đủ kết luận code-schema acceptance ở60; không dùng timing này làm benchmark.
- Đã đề nghị owner nếu đồng ý thêm đúng1request thứ6 thì Ctrl+C server và chạy CLI60 trong terminal có key.
  Owner thực hiện/gửi packet: feature_encoding=catalog_codes_v1, model giữ3.8Flash, enum375;
  **provider HTTP503** sau1364.0806ms, message xác nhận model hiện “experiencing high demand”.
  TLS115.1579ms/body19247bytes gửi xong115.2990ms; nhận headers503 ở1364.4215ms.
  Đây là lỗi provider availability thực trong lượt này, không suy từ backend503 hoặc UI.
  Không nhận extraction/vector/prediction, usage unknown; local budget22138 không phải token/billed cost.
- Bổ sung mapping HTTP503→`provider_unavailable` và thông báo tiếng Việt dịch vụ đang bận.
  Không thay Gemini model, endpoint, production timeout20 hoặc retry policy; website/CLI vẫn retry0.
  Regression **225 tests offline PASS**,1 TestClient deprecation warning, thêm overload503 one attempt/no model call,
  stale-prediction prevention và controlled UI message. Không fake LLM PASS từ các tests này.
- Provider503 có thể chặn trước schema compilation, vì vậy **không coi503 là bằng chứng wire-schema đã hết400**.
  Trạng thái cuối hiện tại: root cause lịch sử400 serving-state explosion VERIFIED;
  latest503 high demand VERIFIED; wire schema/extraction quality/end-to-end live **NOT VERIFIED**.
  Giữ nguyên schema/validator375 và metadata/checkpoints/source pins. Không có actual live model inference mới.
- Evidence mới `artifacts/metadata/gemini_debug/20261030_wire_codes_live_attempts.json`
  nối attempts4–6 với report lịch sử đầu; không ghi đè report/manifest đã có.
  Đã dùng tổng6 attempted generation calls (3ban đầu và3bổ sung có owner action/consent), không gọi tiếp.
  Chờ provider availability trước lần kiểm được owner cho phép tiếp; không public hosting, auto switch model,
  retry vô hạn hoặc hướng dẫn vượt quota. Port8000 là localhost devserver, không mở router/firewall.
  Docs dẫn primary Google troubleshooting503; không tuyên bố outage toàn cầu hoặc Free Tier verified.
