> ARCHIVE — Bản tại thời điểm trước hợp nhất tài liệu. Các trạng thái và lệnh cũ không phải hướng dẫn hiện hành. Xem [chỉ mục hiện hành](../../README.md) và [triển khai](../../DEPLOYMENT_GUIDE.md). Đường dẫn trong code block vẫn tính từ project root.

# Kế hoạch bàn giao workspace — chưa thực hiện cleanup

**Bổ sung mục27,2026-10-29:** đã có [HANDOVER_GUIDE.md](HANDOVER_GUIDE.md) và
[decision record ML](../ml/MODEL_SELECTION_RATIONALE.md#decision-record-lựa-chọn-ml) theo yêu cầu chuẩn bị bàn giao.
Guide hướng dẫn nhận source/Drive và điểm dừng, không là phê duyệt cleanup, đổi default hoặc di chuyển cấu trúc.
Các câu chưa viết hướng dẫn cuối trong snapshot dưới đây giữ bối cảnh lúc lập kế hoạch; inventory/copy limits và retention vẫn áp dụng.

Ngày kiểm kê: **2026-10-29**. Đây là phân tích và danh sách cần duyệt, **không là quyền xóa/di chuyển**.
Giữ MODEL SELECTION PENDING, LR baseline hiện hành và toàn bộ notebook outputs.
Số liệu là logical file sizes từ filesystem local **trước khi thêm script/tests/tài liệu nhiệm vụ này**,
không là disk allocation hoặc danh sách Git tracked. Scan gồm file ẩn, không theo symlink: 0 symlink/0 lỗi truy cập.
Locked test chỉ stat kích thước, **không mở hoặc băm payload**.
Đã nhận snapshot Drive và bootstrap/benchmark thật qua packet ML_GAPS của người dùng; agent không trực tiếp điều khiển kernel/Drive.
Stat inventory, content-checksum của ML bundle và checksum bản sao raw/report/backup là các mức bằng chứng riêng.

## 1. ML: đủ và thiếu bằng chứng

[Rationale hiện hành](../ml/MODEL_SELECTION_RATIONALE.md#phân-tích-học-thuật-và-lựa-chọn-hiện-tại) đã phân tích cả 5 họ,
đủ15 candidate/45 CV scores, selected parameters, warnings và metrics, hard/soft voting, transitions/diversity/per-class.
SHA năm packet41a4ad3b…/42cf30dc…/5dacef33…/70849a69…/4ccfa85a… được đối chiếu lại; không lấy số từ mock.

| Nội dung | Trạng thái |
|---|---|
| 375 feature/587 nhãn,5 baseline/5 tuned checkpoints | PASS lịch sử Colab; local có packets, không có weights |
| CV coverage của run thật | Train587/587/587; holdout **586/586/587**, scorer cố định587/zero_division0. Fold0 thiếu ID112 colorectal cancer,fold1 thiếu ID275 idiopathic infrequent menstruation |
| Hard tuned so LR tuned | F1 0.79651707 vs0.79315438; Accuracy0.83691323 vs0.83766003; sửa173/làm sai194,net−21 |
| Per-class | 115 tăng/128 giảm/344 không đổi;93.82% net gain từ support≤5;2 lớp0→positive chỉ1 mẫu/lớp |
| Paired group uncertainty | **Đã chạy Colab**,seed 20261029/B=2000; percentile CI của delta F1 chứa0,chi tiết mục2 |
| Tuned load/batch1p50/p95/RAM/Top3 | **PASS thực thi Colab** theo protocol; LR Top3 có score thật chưa calibration,hard không có probability Top3 |
| CV-fold predictions/soft probability mean | Fold predictions và soft memmap không persist; không kiểm lại độc lập bằng aggregate, không retrain/predict thêm để tái dựng |
| Clinical validity/Gemini live/API | Chưa được xác thực/không làm trong nhiệm vụ này |

**Đề xuất để nhóm duyệt:** giữ LR baseline hiện hành cho đến khi được duyệt; đề xuất LR tuned cho hướng API nghiên cứu cần Top3,
vì nó có Accuracy/Weighted F1 cao hơn hard, Top3 thực hợp lệ và batch1 nhanh hơn trong benchmark này.
Hard vẫn là ứng viên có điểm Macro F1 cao nhất; CI hiện tại không xác lập ưu thế chắc chắn của nó và hard chưa có contract probability Top3.
Đây là đề xuất theo yêu cầu vận hành và evidence, không tự chọn winner hoặc chứng minh LR tốt hơn ở mọi lớp.
**MODEL SELECTION PENDING** cho tới khi nhóm duyệt; clinical validity,calibration và production concurrency vẫn chưa kiểm.

## 2. Protocol chốt trước khi tính

### Paired group bootstrap, chỉ saved predictions

- So duy nhất LR tuned và hard_lr_svc_knn của experiment/run đã audit; không thêm model/tổ hợp hoặc search.
- **Seed20261029; B=2000**; NumPy default_rng, percentile95%2.5/97.5, quantile method=linear.
- G=25.127 validation groups/28.120 rows. Mỗi replicate lấy G group IDs đồng xác suất, có hoàn lại;
  giữ tất cả row/label của group và multiplicity giống nhau cho hai model. Không row bootstrap hoặc stratify lại theo label.
- Macro F1 luôn labels0..586,zero_division0. Tính từ weighted TP/true-support/predicted-support,
  tương đương sklearn sample_weight; Accuracy là metric phụ chốt trước. Không fit transformer hoặc mapping.
- Báo delta=hard−LR quan sát, bootstrap mean và percentile interval.
  Fraction delta>0 chỉ là tỷ lệ mô tả, không p-value/posterior/xác suất model tốt hơn.
- Lớp vắng vẫn ở mẫu số587, F1=0. Báo số lớp vắng min/p05/p50/p95/max, số replicate có lớp vắng,
  absent-replicates của từng587 class IDs/tên. Không loại replicate thiếu lớp.
- Group-iid là giả định làm việc. Với support1, vắng lớp trong replicate rất thường gặp; F1 không trơn,
  CI có thể lệch. Đây là mô tả có điều kiện trên validation/model đã chọn, không tạo thêm bằng chứng cho bệnh hiếm,
  không xóa repeated-validation selection bias hoặc thay final-test/clinical protocol.
  Chưa khẳng định significance từ chênh0.00336269 hiện tại.

Aggregate/per-class summaries không thay được paired row predictions/group IDs.
[Script nhỏ](../../../scripts/audit_final_ml_gaps.py) dùng existing read_tuning_result/read_completed_checkpoint,
auditor ensemble và hard_vote để kiểm saved predictions cùng provenance trước bootstrap.

### Benchmark cùng checkpoint/input/môi trường

- Chỉ LR tuned và hard tuned LR+SVC+KNN; xác minh manifest,source/versions/config/schema375/class order587/train-only variance mask trước reload.
- Panel64 group khác nhau, chọn không nhìn nhãn/đúng-sai bằng seed 20261029; first row theo validation order.
  Hai điều kiện dùng cùng64 DataFrame1×375 và cùng thứ tự.
- Mỗi operation warm-up3 calls trên first panel row, báo riêng; sau đó3 vòng×64=**192 batch1 calls/operation**,
  p50/p95/min/max. Đây là64 input lặp lại, không192 quan sát độc lập.
- Đo Top1 LR; Top1 hard gồm transforms/predict của3 model và vote/tie hiện có.
  Đo riêng LR predict_proba+stable Top3 ranking. Hard không có posterior587-class;
  không ghép Top1 hard/Top3 LR. Score hợp lệ không đồng nghĩa calibrated probability hoặc clinical confidence.
- Verified-load đo checksum+deserialize+schema/config/mask checks, từng member và tổng từng condition;
  upfront integrity time riêng. Artifact đã được integrity đọc nên **không cold Drive startup**.
- Data resident cùng process; BLAS1/working_memory128MiB, thứ tự chốt LR→hard, bỏ RAM references/gc giữa conditions.
  Báo RSS trước/sau và sampled process+children peak từ helper hiện có mỗi0.5s.
  Cache/allocator/order effects còn tồn tại, sampling có thể lỡ peak, không cô lập RAM estimator.
- Không đo HTTP/LLM/concurrency, không SLA. Chưa tự đặt acceptance threshold latency/RAM.
  Khác versions/pinned source hoặc chưa trusted: benchmark NOT VERIFIED, giữ bootstrap đã tính;
  integrity mismatch BLOCKER, không bypass/cài lại/migrate model.

### Thu kết quả trên Colab, không đổi runtime architecture

Không chạy lại notebook03/04, training switches, shared bootstrap hoặc write-probe để thu bằng chứng này.
Dùng kernel đã có session/source và Drive mount; nếu session mất, dừng để xác lập lại phiên phù hợp,
không Run All model notebook. Không sửa source/config đã pin.

**Upload vào Colab Runtime /content/** đúng2 file:
scripts/audit_post_tuning.py và scripts/audit_final_ml_gaps.py.
Không upload colab-session/ZIP/.pyz hoặc refresh source staging cho thay đổi scripts/docs.

```python
import runpy
read_api = runpy.run_path('/content/audit_post_tuning.py')
gap_api = runpy.run_path('/content/audit_final_ml_gaps.py')
gaps = gap_api['run_final_ml_gaps'](
    session, audit_api=read_api, benchmark=True, trusted=True,
)
gap_api['emit_packet'](../../gaps)
```

Copy Cell Output3 dòng ML_GAPS_SHA256/ML_GAPS_GZIP_BASE64/ML_GAPS_STATUS.
REVIEW là chủ đích vì model selection cần nhóm duyệt; đọc benchmark.status bên trong.
Script dùng existing read_only guard/loaders/integrity/checkpoint loader/sampled_memory/hard_vote,
không tạo cache,export,filesystem cleanup,network hoặc đọctest. gc chỉ bỏ RAM references.
Inventory Drive trong packet là stat-only, không chứng minh cùng content.
**Lúc chốt protocol chưa có packet ML_GAPS.** Sau đó người dùng gửi kết quả thật ở mục kế tiếp; không đổi seed/B/panel/metric sau khi thấy kết quả.
Local9 unit tests memory-only PASS chỉ kiểm logic,không thay bằng chứng Colab.

### Kết quả Colab đã nhận sau khi chốt protocol

[Packet nguyên byte](../../../artifacts/metadata/final_ml_gaps/colab_evidence.json),36.429bytes,
SHA-256 **7c2ed8e6705347a850bb90e88cdea54067d0d12ec5553588ce03fbd0a99725ac**.
Script SHA **7c925d48e02dfab7b6951303c2c3e69f52d4143658ba1e1976a079b5b4141ce1** khớp bản local được upload,
linked tuning4a10ddd5…/ensemble858893c4… đúng hai manifest đã audit.
Counters0 fit/test/write/network; prediction_called=true chỉ cho benchmark được phép; default_changed=false.
Overall REVIEW/selection PENDING là chủ đích,không phải lỗi integrity.
Agent kiểm SHA/protocol/arithmetic local; không tự tải row predictions hoặc chạy lại model để băm Drive độc lập.

| Metric delta hard−LR tuned | Quan sát | Mean bootstrap | Percentile95% |
|---|---:|---:|---|
| Macro F1 | +0.00336269 | +0.00301573 | **[−0.00003807; +0.00622337]** |
| Accuracy | −0.00074680 | −0.00074050 | **[−0.00168360; +0.00021316]** |

Seed20261029/B=2000,G25127,N28120,C587 khớp protocol. CI cả hai chứa0:
không khẳng định hard có cải thiện chắc chắn, cũng không kết luận hai model tương đương.
Fraction positive0.9735 ở F1 và0.0605 ở Accuracy không được đổi thành p-value hoặc confidence.
Cả2000 replicate đều vắng lớp: min8,p05=13,median19,p95=25,max31;182 lớp vắng ít nhất1 replicate.
Các tần suất đầy đủ587 IDs/tên nằm trong packet. Đây là bằng chứng trực tiếp về độ nhạy lớp hiếm,
không phải lỗi scorer vì labels vẫn cố định587.

Môi trường: Colab Linux, Intel Xeon2.20GHz,2logical CPU, RAM12.671GiB,
Python3.13.18,sklearn1.6.1,NumPy2.1.3,pandas2.2.3; không dùngGPU.
Upfront checksum/input integrity **7.934s**,tách khỏi load/inference.

| Operation | Verified load tổng(s) | Warm-up từng call(ms) | Batch1p50(ms) | Batch1p95(ms) | Sampled process peak(MiB) |
|---|---:|---|---:|---:|---:|
| LR tuned Top1 | 0.036802 | 27.009 /13.570 /12.919 | **13.102** | **14.778** | 393.105 |
| LR tuned predict_proba+Top3 | Cùng LR đã load | 14.259 /13.311 /12.683 | 12.854 | 15.073 | Cùng condition393.105 |
| Hard tuned LR+SVC+KNN Top1 | 0.111631 | 76.038 /45.477 /44.427 | **48.705** | **88.125** | 393.535 |

Mỗi operation192 timed calls trên cùng64 group; saved panel row IDs/group IDs nằm trong packet.
Hard member-load LR0.036348s,SVC0.034844s,KNN0.040438s,tổng khớp0.111631s.
LR là load lần riêng,không lấy timing baseline hoặc ghép thời gian từ phiên khác.
Hard p50 cao khoảng3.72 lần LR ở protocol này; không suy thành tỷ lệ latency API mọi workload.
Load đã có integrity pre-reads nên không cold-start Drive. Fit guard dùng Python profiler tạo overhead trên cả hai conditions;
không extrapolate p95 được instrument sang production.

RSS trước/sau LR392.656/393.105MiB; hard393.160/393.535MiB.
Chênh process-RSS nhỏ không chứng minh estimator chỉ dùng ít MiB:
data/kernel/allocator từ phiên trước còn resident,sampling0.5s có thể lỡ peak,không process-isolated.
Không cộng stage peaks hoặc gọi memory delta là RAM hard riêng lẻ.
Top3 LR thực có class IDs508/296/212 ở last-panel-row và scores0.40744/0.37057/0.02816;
đây là model probabilities chưa calibration,không confidence y khoa.
Hard Top3=UNAVAILABLE theo contract vote; không tự tạo hybrid hoặc calibrator.
Benchmark chỉ ghi2 DeprecationWarning; không huấn luyện hoặc thay checkpoint.

Bootstrap/benchmark bổ sung đủ phép đo đã yêu cầu ở mức diagnostic; chưa có concurrency/cold-start/API end-to-end,
acceptance criteria do nhóm duyệt hoặc clinical evidence. Vì vậy vẫn MODEL SELECTION PENDING.

## 3. Kiểm kê local thực tế

Workspace: D:\Program Files (x86)\DULIEUCODE\ML. Project: disease-prediction-ml/.
Notebook người dùng seminar_chapter6_model_evaluation.ipynb ở workspace parent,110.732bytes;
reporting.py/run_phase1.py/validate_deliverables.py tham chiếu bảo toàn. KEEP ngoài project.

| Phạm vi | File | Bytes | MiB |
|---|---|---|---|
| Workspace ML, gồm notebook ngoài project | 2028 | 287763200 | 274.432 |
| Riêng disease-prediction-ml | 2027 | 287652468 | 274.327 |
| data/ | 9 | 192670771 | 183.745 |
| reports/ | 108 | 56615391 | 53.993 |
| artifacts/ | 48 | 7408254 | 7.065 |
| dist/ | 48 | 1257373 | 1.199 |
| .venv/ | 1648 | 24559868 | 23.422 |
| src/ | 57 | 898615 | 0.857 |
| tests/ | 39 | 1277019 | 1.218 |
| notebooks/ | 9 | 2294798 | 2.188 |
| scripts/ | 26 | 327757 | 0.313 |
| docs/ | 10 | 300318 | 0.286 |
| configs/ | 10 | 8073 | 0.008 |
| .pytest_cache/ | 5 | 19856 | 0.019 |

Counts gồm cache/env: src có29 .py thực/57 file; tests19 .py và scripts17 .py trước nhiệm vụ;
notebooks có7 .ipynb cùng README/.gitkeep. Không nhầm vendored pip files với project source.
.venv tồn tại từ trước:1.648 file/24.559.868bytes,không tạo/dùng/dọn trong audit.

| Loại, gồm cả .venv | File | Bytes | MiB |
|---|---|---|---|
| .csv | 59 | 243437269 | 232.160 |
| .pyc | 833 | 13690000 | 13.056 |
| .py | 871 | 10601768 | 10.111 |
| .ipynb | 26 | 8792452 | 8.385 |
| .gz | 4 | 3263533 | 3.112 |
| .exe | 21 | 2518097 | 2.401 |
| .png | 18 | 2039736 | 1.945 |
| .svg | 16 | 938532 | 0.895 |
| .json | 59 | 700889 | 0.668 |
| .zip | 5 | 623459 | 0.595 |
| .md | 21 | 381537 | 0.364 |
| .pem | 1 | 281617 | 0.269 |
| .pyz | 1 | 217381 | 0.207 |

.csv lớn chủ yếu raw/report tables; .py/.pyc gồm pip/venv.
.pem nằm trong certifi của pip vendored, không mặc nhiên là private key.
Không đọc credentials hoặc ghi token/private Drive link.

| File/nhóm lớn | Bytes | Bằng chứng |
|---|---:|---|
| data/raw/Disease and symptoms dataset.csv | 190786867 | CSV thực duy nhất trong project,giữ tên/nội dung |
| reports/tables/audit_row_pattern_ids.csv và bản run | 8004500 mỗi bản | Cùng SHA; test_data_regression đọc flat path |
| reports/tables/audit_pattern_labels.csv và bản run | 5643817 mỗi bản | Cùng SHA,Phase1 evidence |
| reports/tables/eda_symptom_pairs.csv và bản run | 4338223 mỗi bản | Cùng SHA |
| reports/tables/audit_pattern_groups.csv và bản run | 2607763 mỗi bản | Cùng SHA |
| reports/tables/eda_correlation.csv và bản run | 2402465 mỗi bản | Cùng SHA |
| artifacts/metadata/phase2/split_assignments.csv.gz | 1415738 | Group/label/split mapping khóa,KEEP |

## 4. Canonical Drive và các artifact chỉ ở Drive theo evidence

Từ configs/runtime.json,colab_runtime.canonical_paths và locator source của7 notebooks:
**/content/drive/MyDrive/ML_Projects/disease-prediction-ml**.
Import source tạm /content/disease-prediction-ml-runtime,cache /content/disease-prediction-ml-cache.
Mở notebook local không tự upload source; kết nối Colab không tự mount Drive.
Code cells cả 7 notebook dùng shared bootstrap, không SOURCE_ARCHIVE/colab-session/.pyz/source_manifest.json.

| Namespace Drive | Local | Bằng chứng và quy tắc |
|---|---|---|
| src/,configs/,requirements-* | Có;38 staging files khớp | Source/import PASS lịch sử,hiện tạiN/V. Source upload không include data/model/report |
| data/raw/Disease and symptoms dataset.csv | 190786867bytes | Drive content copy hiện tại NOT VERIFIED; không xóa local vì nghĩ đã upload |
| data/processed/{train,validation,test}.csv.gz |3 file/1847795bytes | Train/val+7 input checks PASS lịch sử; test payload không mở/băm. Giữ trọn bộ |
| artifacts/metadata/phase2/ |6 file/1664402bytes | Localmanifestca20… vs Drive5030…; cả2 approved nhưng không interchangeable byte/identity; không ghi đè Drive |
| artifacts/models/phase3/baseline-v1-f8a5bfdb7b4c12cd/ | Không có,models chỉ.gitkeep |5 pipeline/fit/metadata/predictions auditPASS,weights total18078130bytes lịch sử |
| artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/ | Không có |5 tuned pipelines total21045983bytes vàfit/metadata/predictions PASS lịch sử; không chỉ giữ LR |
| artifacts/metadata/tuning/tuning-v1-9c4dd013abbba14a/ | Không có | manifest,experiment,trials,selection,cv_assignments đã audit; không regenerate tuning |
| artifacts/models/phase4/phase4-20261028T091711786379Z-c1c66643/definitions.json | Không có | Definition tham chiếu baseline checkpoints qua namespace tương đối |
| artifacts/metadata/runs/phase4-…/ và tuned-ensemble-20261029T041701354242Z-6c84dbfe/ | Không có hai run này | manifests,predictions,results auditPASS; giữ cùng linked reports/identities |
| reports/tuning/<experiment>/ và reports/runs/<phase3/phase4/tuned run>/ | Không có các run mới | Charts/tables/reports được manifest kiểm trên Colab; không tái tạo từ notebook output thay checksum |
| artifacts/metadata/*_audit/,model_analysis/,structured_inference/ |5 packet/197683bytes | Evidence người dùng gửi,không backup weights. KEEP nguyên byte; ML_GAPS pending |

**Snapshot Drive mới từ packet ML_GAPS:**167 files/263.964.552bytes (251.736MiB),0stat errors/0symlinks.
Chỉ là inventory do người dùng chạy,không live connector của agent.

| Nhóm Drive | File | Bytes | Mức kiểm |
|---|---:|---:|---|
| data/ |4|192634662|Stat; raw190786867bytes trùng size local,**chưa so raw SHA** |
| artifacts/ |64|43385417|26 tuning files +4 ensemble files và7 Phase2 inputs được helper kiểm content; không suy mọi artifact còn lại đều đã hash mới |
| reports/ |60|27565126|Stat; một số bảng Phase1 khác run IDs/kích thước local |
| src/ |29|328620|Stat;8 ML source pins được đối chiếu trước benchmark,không full-source copy checksum |
| configs/ |7|7615|Stat; Phase2 integrity config được dùng kiểm bundle |
| requirements-notebooks.txt,requirements-training.txt |2|550|Stat |
| source_manifest.json tại root |1|42562|Có thật trong snapshot nhưng nội dung/chức năng chưa đọc; current shared read_source không sử dụng file này |

Packet mới không báo riêng actual Phase2 dataset_manifest SHA: xác nhận helper chấp nhận approved baseline,
không tuyên bố đã băm mới đúng variant5030… thay vìca20… trong báo cáo.5030… là variant gắn identity lịch sử đã audit.
Drive root snapshot **không có các top-level notebooks/,docs/,scripts/,tests/**; Drive folder hiện tại đủ runtime payload nhưng chưa đủ bàn giao toàn dự án.
data/ chỉ4 files,không được suy đã đồng bộ cả local evaluation JSONL; bản copy JSONL **NOT VERIFIED**.
Tuned26 files vàensemble4 files đã checksum mới; baseline5 checkpoints/Phase4 definitions vẫn có audit lịch sử,
không đánh dấu full fresh content verification chỉ từ số files.

**Report local và Drive không phải bản sao byte đã chứng minh:** local Phase1 runIDs20261021…,
Drive Phase1 runIDs20261027…. audit_row_pattern_ids8.004.500bytes local vs7.757.554bytes Drive;
audit_pattern_labels5.643.817 vs5.454.169; eda_symptom_pairs4.338.223 vs4.267.346.
Khác line endings là một giả thuyết,chưa kiểm content. Không xóa local report vì thấy tên tương tự ở Drive.

Chỉ ở Drive nghĩa là namespace local thiếu nhưng packet lịch sử ghi nhận trên Drive,
**không là agent trực tiếp nhìn thấy Drive**. Nay đã có stat snapshot và content verification phần tuned/ensemble/Phase2;
member permissions vàraw/report/backup/archive copy checksums vẫn NOT VERIFIED.
Localmanifestca20a551…/Drive50308d25… đã được giải thích/duyệt; preserve exact Drive variant gắn checkpoint,
không sửa mismatch bằng thay manifest. TRAINING_FILES chỉ đọc train/validation+metadata,giữ sealed test entry.

Script đối chiếu26 tuning artifacts,4 ensemble files,7 Phase2 inputs bằng helpers; stat canonical tree riêng.
Để xác minh một copy raw/report/archive trước cleanup phải so SHA ở cả hai vị trí cùng relative path,
không filename/size; việc đó **chưa chạy trên Drive**. Không hash/copy locked test để hoàn tất inventory.

## 5. Dependency và hành động theo từng nhóm

Drive verification ở mục4 phân biệt rõ phần vừa hash (tuned/ensemble/7 Phase2 inputs), phần chỉ stat và audit lịch sử.
Raw/report/backup/archive **bản sao** chưa được đối chiếu content ở hai vị trí; không gán PASS copy từ inventory.
REGENERATE là khả năng tương lai,không lệnh chạy. IGNORE là không mang vào source handover,không xóa.
REMOVE-LATER luôn cần allowlist/retention/copy evidence và phê duyệt riêng.

| Nhóm,localbytes | Tạo lại đúng bản? | Caller/rủi ro | Drive-copy evidence | Hành động |
|---|---|---|---|---|
| src/898615 gồmcache;configs/8073;root requirements/README | Source/pins phải giữ | Notebook imports,training.experiment_identity pin6 module;tuning thêm SHA;FunctionTransformer cần src.models.training.to_csr | Historical import/checkpointPASS,freshN/V | **KEEP** .py/config,IGNORE pyc |
| notebooks/2294798,7 ipynb | Không tái tạo output thật bằng builder | Cellsource/output/locator cần khớp runtime.json; builder có exclusive-create/overwrite opt-in | Copy notebooksN/V | **KEEP**,không rebuild/clear |
| scripts/327757,tests/1277019,docs/300318 trước task,gồmcache | Code/history không được tự bỏ | Legacy APIs vẫn được tests import. build_notebooks.write_notebook gọi migrate trước ghi nên token ZIP ở template không chứng minh runtime mới cũ | Source staging không include scripts/tests/docs | **KEEP**,IGNORE pyc |
| data/raw/190787684 | Không chứng minh download đúngbytesgốc | loader.dataset_path,Phase1/2;phase1.json có filename thật vàparent fallback | Raw copyN/V | **KEEP** CSV/README/source metadata |
| data/processed/1847795+phase2 metadata1664402 | Không regenerate sealed dataset | load_final_split,verify_training_inputs,checkpoint identity | Train/val và metadata được helper hash mới; test không đọc. Exact manifest variant mới chưa được packet ghi riêng | **KEEP** filenames/relative paths |
| Drive baseline+tuned weights;localmodels0bytes | Không retrain ra đúng checkpointbytes | fit.json,metadata,predictions,SHA,versions/source identity | Tuned5 checksums mới+LR/SVC/KNN reload; baseline5 audit lịch sử | **KEEP** cả 5+5 vàreferences |
| artifacts/metadata/1916678 gồmphase2/evidence/runs | Snapshot không suy từcurrentcode | Phase1 dataset_manifest khácPhase2;packets/checksums dùngaudit | Misc/backupN/V;ML lịch sửPASS | **KEEP**,không gộp manifests |
| reports/tables/26340608,figures/1651544,root reports | Có thể tái tính vàiEDA nhưng không thayhistory | test_data_regression.py:33,37 đọcflat;docs ảnhlinks;legacy reporting.output_paths còn flat | Report copyN/V | **KEEP**,duplicateREVIEW |
| reports/runs/28575238,49files | Executedoutputs/provenance không chắc tái tạo nguyênbytes | validate_deliverables --execution-run;validate_portability +metadata/runs | Local Phase1 run copiesN/V | **KEEP/REVIEW**,không gộp ngay |
| artifacts/backups/5491576,17files | Không tạo lại snapshot trướcsửa | validate_portability.py:19–32 đọcportability-*/baseline.json vànotebookscũ;protected.json giữevidence | BackupN/V | **REVIEW**,mặc địnhKEEP |
| dist/drive-source/337912,38files | Có từsource/config allowlist+2requirements | prepare_colab_source.ps1 CheckOnly;runtime không đọcdist trực tiếp | LocalCheckOnlyPASS;DrivefreshN/V | **REGENERATE** khi source đổi;IGNOREsourcehandover |
| dist/colab-session/59996,3files;dist/drive-phase2-audit.json18625 | Không cần hiện hành;receipt/provenance lịch sử không tái tạo từcode mới | Current7 notebooks/read_source khôngdùng;docs/tests giữlegacy;drive-phase2-audit giữmanifest5030…gốc | CopiesN/V | **REVIEW/REMOVE-LATER**,chỉsau retention/copycheck |
| dist/*.zip5files623459;*.pyz1file217381 | Package mới tái tạo được,source snapshotcũ không | package_colab/install_colab_source vàlegacy tests còn tạo fixtures;notebooks hiện tại không load6 archives | ArchivesN/V | **REVIEW/REMOVE-LATER**,không rebuildZIP |
| .venv/24559868,1648files | Env mới có thể tạo nhưng không chắc đúngtrainedversions | Windowsenvcũ;Colab notebook khôngfallback;VSCode settings ngoàiworkspace chưakiểm | Không cầncopyDrive,N/V | **IGNORE**,REMOVE-LATER cầnowner xácnhận |
| __pycache__/ ngoàivenv56files1765136;.pytest_cache/19856 | Có khiimport/test | Python/pytest,không authority modelresults | Khôngcầncopy,N/V | **IGNORE**,REMOVE-LATER chỉkhiduyệt |
| app/{backend,frontend}/.gitkeep;src/features/__init__.py;empty.gitkeep | Placeholders0bytes | scaffold/package shape,chưaAPI/frontend | N/V | **KEEP**,khôngcóstoragebenefit đángkể |
| Drive:/source_manifest.json,42562bytes;không có bản cùng-path local | Chưa biết nội dung/khả năng tái tạo | Current shared read_source không dùng; nội dung/chức năng riêng chưa xác minh,không suy disposable từ tên | Drive stat đã thấy;content/copyN/V | **REVIEW**,giữ nguyên trước khi đọc provenance |
| ../seminar_chapter6_model_evaluation.ipynb110732 | Useroriginal,khôngrecreate bằngbuilder | reporting.py/run_phase1.py/validate_deliverables.py bảo toàn/hash | N/V | **KEEP** ngoàiproject/cleanup |

Không thấy .cache/,.phase3-cache/,.colab-cache/ ở localsnapshot; không đề xuất xóa đườngdẫn khôngcó.
Paths /content là cấu hình,không suy đang tồn tại hoặc nằm trên Drive.
Không gọi mọi backup là disposable hoặc .pem là credential theo tên.

## 6. Duplicate đã xác minh và ràng buộc

38 nhóm report cùng SHA,mỗi nhóm2 bản;extra bytes **27189019 (25.929MiB)**:
26 cặp tables,4 summary/report,8 PNG. SVG trùngbasename nhưng không cùngbytes/hash nên không tự coi duplicate.
Đây là duplicate local,không chứng minh backupDrive.
Giữ cả2 layout đến khi reference migration được duyệt.

| Report hiện hành | Bản run cùng SHA-256 | Bytes mỗi bản |
|---|---|---|
| reports/dataset_audit.json | reports/runs/phase1-20261021T112410238224Z-204946eb/dataset_audit.json | 1012 |
| reports/dataset_audit.md | reports/runs/phase1-20261021T112410238224Z-204946eb/dataset_audit.md | 6008 |
| reports/eda_metrics.json | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/eda_metrics.json | 1074 |
| reports/eda_summary.md | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/eda_summary.md | 13673 |
| reports/figures/01_class_distribution.png | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/figures/01_class_distribution.png | 63874 |
| reports/figures/02_class_extremes.png | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/figures/02_class_extremes.png | 107434 |
| reports/figures/03_symptom_frequency.png | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/figures/03_symptom_frequency.png | 98253 |
| reports/figures/04_active_symptoms.png | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/figures/04_active_symptoms.png | 34834 |
| reports/figures/05_symptom_relationships.png | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/figures/05_symptom_relationships.png | 149548 |
| reports/figures/06_selected_disease_profiles.png | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/figures/06_selected_disease_profiles.png | 147376 |
| reports/figures/07_similar_disease_profiles.png | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/figures/07_similar_disease_profiles.png | 101753 |
| reports/figures/08_redundancy.png | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/figures/08_redundancy.png | 154386 |
| reports/tables/audit_alias_candidates.csv | reports/runs/phase1-20261021T112410238224Z-204946eb/tables/audit_alias_candidates.csv | 92 |
| reports/tables/audit_class_distribution.csv | reports/runs/phase1-20261021T112410238224Z-204946eb/tables/audit_class_distribution.csv | 35291 |
| reports/tables/audit_class_patterns.csv | reports/runs/phase1-20261021T112410238224Z-204946eb/tables/audit_class_patterns.csv | 23011 |
| reports/tables/audit_duplicate_columns.csv | reports/runs/phase1-20261021T112410238224Z-204946eb/tables/audit_duplicate_columns.csv | 1076 |
| reports/tables/audit_features.csv | reports/runs/phase1-20261021T112410238224Z-204946eb/tables/audit_features.csv | 65527 |
| reports/tables/audit_label_collisions.csv | reports/runs/phase1-20261021T112410238224Z-204946eb/tables/audit_label_collisions.csv | 31 |
| reports/tables/audit_missing.csv | reports/runs/phase1-20261021T112410238224Z-204946eb/tables/audit_missing.csv | 10969 |
| reports/tables/audit_pattern_groups.csv | reports/runs/phase1-20261021T112410238224Z-204946eb/tables/audit_pattern_groups.csv | 2607763 |
| reports/tables/audit_pattern_labels.csv | reports/runs/phase1-20261021T112410238224Z-204946eb/tables/audit_pattern_labels.csv | 5643817 |
| reports/tables/audit_row_pattern_ids.csv | reports/runs/phase1-20261021T112410238224Z-204946eb/tables/audit_row_pattern_ids.csv | 8004500 |
| reports/tables/eda_active_by_class.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_active_by_class.csv | 47988 |
| reports/tables/eda_active_distribution.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_active_distribution.csv | 381 |
| reports/tables/eda_class_always_symptoms.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_class_always_symptoms.csv | 8310 |
| reports/tables/eda_class_profiles.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_class_profiles.csv | 1261249 |
| reports/tables/eda_class_profile_counts.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_class_profile_counts.csv | 613846 |
| reports/tables/eda_class_quantiles.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_class_quantiles.csv | 121 |
| reports/tables/eda_conflict_examples.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_conflict_examples.csv | 8981 |
| reports/tables/eda_cooccurrence.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_cooccurrence.csv | 323404 |
| reports/tables/eda_correlation.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_correlation.csv | 2402465 |
| reports/tables/eda_jaccard.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_jaccard.csv | 799834 |
| reports/tables/eda_similar_diseases.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_similar_diseases.csv | 71866 |
| reports/tables/eda_single_class_features.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_single_class_features.csv | 3258 |
| reports/tables/eda_strong_correlations.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_strong_correlations.csv | 59 |
| reports/tables/eda_supported_similar_diseases.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_supported_similar_diseases.csv | 7404 |
| reports/tables/eda_symptom_frequency.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_symptom_frequency.csv | 30328 |
| reports/tables/eda_symptom_pairs.csv | reports/runs/phase1-20261021T112430124431Z-1d3f6ed8/tables/eda_symptom_pairs.csv | 4338223 |

Một cặp ZIP trùng byte: dist/disease-prediction-ml-colab-source.zip và
dist/disease-prediction-ml-source-20261021T115946556874Z.zip,
99614bytes/bản,SHA cf1fe40cfdc641bab6ea80325a9b2db241b19fcc3b883c606172ba62d518bfb9.
Chưa xóa bản nào;lợi ích~0.095MiB không đáng đổi provenance chưa rõ.

Dependency scan đọc imports/source/config,notebook source cells,src/scripts/tests/docs/README vàmetadataJSON:
Phase1 run records,Phase2 manifests,backup baselines,oldreceipt.
Literal paths và directory/glob readers đều được xét;output logs không là active caller.
Không thấy current loader cần chính6 archive filenames để loadmodels nhưng legacy APIs/tests vẫn cần source helpers.
Vắng literal reference không chứng minh external workflow không cần file;owner phải duyệt.

## 7. .gitignore, staging và cây bàn giao đề xuất

.gitignore loại .venv/venv, pyc/cache, .env, configs/runtime.private.json, artifacts/backups, dist,
raw/interim/processed payloads, artifacts/models/* và các pattern toàn cục *.joblib/*.pkl/*.pickle,
metadata/phase3, reports/runs và metadata/runs.
Ignore policy không chứng minh file đã track hoặc có backup.
**Chỉ bàn giao source/Git hoặc dist/drive-source không đủ dataset, checkpoint và report history.**
Các evidence packets không bị rule metadata/phase3 loại vì phase3_audit là tên khác.
Không sửa .gitignore hoặc commit secrets/weights trong nhiệm vụ này; quyền truy cập persistent Drive do owner quản lý.

prepare_colab_source.ps1 -CheckOnly **PASS**,38 file khớp.
Không chạy -Refresh vì nó xóa/tái tạo owned staging, ngoài phạm vi hiện tại.
Staging không chứa notebooks/scripts/tests/docs; audit scripts mới vẫn upload runtime thủ công.
Không thêm deployment/sync/receipt/ZIP/.pyz hoặc bản sao weights.

Giữ cấu trúc hiện hành; chưa có nhu cầu kỹ thuật để move root hoặc rename namespace:

```text
disease-prediction-ml/
├── README.md, pyproject.toml, requirements-*.txt, setup.ps1, .gitignore
├── configs/                         runtime.json: canonical locator
├── src/{data,models,agent,evaluation,features}/
├── notebooks/{00_*,01_*,02_*,03_*,04_*,05_*,colab_smoke_test}.ipynb
├── scripts/
├── tests/
├── docs/                            rationale/log/kế hoạch này
├── data/
│   ├── raw/Disease and symptoms dataset.csv
│   ├── interim/
│   ├── processed/{train,validation,test}.csv.gz
│   └── evaluation/vietnamese_symptom_cases.jsonl
├── artifacts/
│   ├── models/{phase3,phase4,tuning}/       Drive; local hiện chỉ.gitkeep
│   ├── metadata/{phase2,tuning,runs,*_audit,structured_inference,model_analysis,final_ml_gaps}/
│   └── backups/                     REVIEW, chưa move
├── reports/{figures,tables,runs,...} KEEP
├── app/{backend,frontend}/          placeholders
├── dist/drive-source/               tái tạo, IGNORE source handover
└── .venv/,__pycache__/,.pytest_cache/ IGNORE, không xóa hiện tại
```

Đây là logical tree kết hợp source local và persistent artifacts Drive, không khẳng định mọi folder đã có local.
Người nhận cần full source/notebooks/scripts/tests/docs, các packet local và quyền Drive tới immutable artifacts,
đúng trained versions/custom module và identities. Chưa đóng gói hoặc viết hướng dẫn bàn giao cuối khi cấu trúc chưa duyệt.

## 8. Rủi ro và các hành động cần phê duyệt riêng

1. **Dataset/checkpoint/metadata:** KEEP. Không xóa local vì nghĩ Drive có copy; không đổi feature375/labels587,
   group assignments, CSV/compression bytes, source SHA hoặc custom-module path.
   Không chép manifest localca20… đè variant5030… gắn với identity lịch sử.
   Thay byte/path có thể làm checksum/identity hoặc pickle reload bị từ chối.
2. **Cache/env:** hiện chỉ đề xuất IGNORE khi bàn giao source. Muốn xóa sau này phải có allowlist resolved absolute paths,
   owner xác nhận env không active, không symlink và snapshot trước thao tác. Chưa có quyền xóa.
3. **Legacy ZIP/.pyz/colab-session/root source_manifest.json:** owner chốt retention, nội dung cần lưu và bản copy provenance đã hash.
   Nếu thiếu bản đã kiểm thì giữ nguyên; không tạo archive backup mới trong nhiệm vụ này.
   Root source_manifest.json mới chỉ được stat, chưa được đọc nội dung để kết luận có thể bỏ.
4. **Reports/backups:** trước khi duyệt phải chọn authority layout, liệt kê từng reference cần đổi và regression strategy.
   Không xóa Phase1 history/validator hoặc rewrite Phase1 outputs chỉ để tiết kiệm khoảng26MiB.
   Reports local/Drive đang khác run IDs và size, nên không xem Drive là byte backup đã chứng minh.
5. **Drive/root:** giữ canonical root. Chia sẻ quyền cho thành viên là thao tác riêng của owner;
   không move root, rename checkpoint, copy model hoặc chỉnh notebook locator/config ở đây.
6. **Model:** đề xuất LR tuned cho API nghiên cứu cần Top3 đã có evidence, nhưng nhóm phải duyệt lựa chọn/output gate/acceptance criteria.
   LR baseline mặc định giữ nguyên; final test/Gemini/API là nhiệm vụ riêng.

Trước bất kỳ cleanup nào, đối chiếu raw copy và manifest variant bằng một cell chỉ đọc như dưới.
Đây là **phương án chưa chạy**, không phải lời yêu cầu upload dữ liệu hoặc thay file; raw hash đọc190MB qua Drive có thể mất thời gian.
Không thêm locked test vào danh sách:

```python
from src.data.loader import sha256_file
root = session.paths.storage_root
with read_api['read_only'](../../root):
    raw = sha256_file(root / 'data/raw/Disease and symptoms dataset.csv')
    phase2_manifest = sha256_file(root / 'artifacts/metadata/phase2/dataset_manifest.json')
print({
    'raw_sha256': raw,
    'raw_matches_local_snapshot': raw == '8de90603ebada467fc2703db2ee4292856e52d64e94982ef926df22fa0c21320',
    'phase2_manifest_sha256': phase2_manifest,
    'action': 'report only; preserve manifest variant and all files',
})
```

Raw local SHA ở cell là snapshot đã đọc, không là publisher checksum/clinical provenance.
Report/archive copies phải so nội dung ở hai vị trí đã chọn; đối với các reports hiện khác size đã biết chúng không là byte copy.
Không hash/copy test để hoàn tất checklist cleanup.

## 9. Ưu tiên tiếp theo và tiêu chí dừng

1. **Đã hoàn tất:** thu/kiểm ML_GAPS packet, protocol, source SHA và35 consistency checks.
   Local tái tạo đúng64 panel rows/group IDs và2.000 replicate missing-class frequencies bằng shared validation loader,
   không có row predictions local để tự tính lại CI F1 độc lập; không nói agent đã chạy Colab.
2. Nhóm đọc CI cùng rare-class/selection-bias limits và diagnostic load/warm-up/batch1/RSS/Top3;
   chốt output contract và acceptance criteria trước production benchmark tiếp theo.
   Không thay seed/grid hoặc đặt criteria sau khi nhìn kết quả để ép model thắng.
3. Kiểm quyền truy cập Drive và content-copy evidence còn thiếu (raw/report/backup/archive, exact manifest variant);
   inventory mới chỉ stat167 files, không thay copy checksums.
4. Duyệt đề xuất model và cây handover giữ cấu trúc; xác định cách cung cấp các thư mục notebooks/docs/scripts/tests
   hiện thiếu ở Drive cho thành viên. Không tự upload, đổi root hoặc đổi default trong audit này.
5. Nếu muốn cleanup sau đó, lập allowlist đường dẫn/bytes/dependencies/copy evidence/rollback để người dùng duyệt từng nhóm.
   Chỉ sau phê duyệt riêng mới thao tác; hiện không delete/move/rename.

**STOP:** đã hoàn thành inventory, kế hoạch và bằng chứng diagnostics; chưa cleanup, model selection, training, Gemini, API hoặc frontend.
