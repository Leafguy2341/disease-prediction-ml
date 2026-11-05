# Phase 3 — Post-training audit cuối, 2026-10-28

**Kết luận: có thể chuyển sang Phase 4 với các giới hạn được ghi nhận (REVIEW); không phát hiện BLOCKER trong bằng chứng đã kiểm.** Chưa triển khai ensemble, tuning hoặc training mới.

**Ghi chú cập nhật 2026-10-29:** kết luận và số liệu audit baseline trong báo cáo này giữ nguyên tại mốc kiểm.
Notebook03 có Section5 tuning ở namespace riêng; người dùng đã chủ động chạy và lưu output, không thay năm checkpoint/metrics baseline.
**Post-Tuning Audit đã nhận: checkpoint/metrics PASS trên Colab**, theo [packet mới](../artifacts/metadata/post_tuning_audit/colab_evidence.json)
SHA `70849a69a0d2cd571e2d93a938b98a9167b9d46ceb0db9d6cb1859f6a2e415e8`.
[Giao thức và phân tích sau tuning](../docs/MODEL_SELECTION_RATIONALE.md#phân-tích-tuning-theo-từng-họ-mô-hình) không thay kết quả baseline dưới đây hoặc tự đổi LR mặc định.

Run: `baseline-v1-f8a5bfdb7b4c12cd`. Người dùng đã chạy script audit trên Colab có Drive và gửi packet; agent giải mã, xác minh SHA-256 rồi đối chiếu nội dung. Đây là bằng chứng thực thi Colab do người dùng cung cấp, không phải agent trực tiếp điều khiển kernel hoặc tải các model về local.

[JSON evidence nguyên byte](../artifacts/metadata/phase3_audit/colab_evidence.json), SHA-256:

`41a4ad3b0c3b8c783382b807688fd0958b00666b6e46bb84c3d3fe1e8c16fb48`

Trạng thái NOT VERIFIED ban đầu do thiếu artifact local đã được giải quyết bằng packet Colab. Lịch sử đó giữ trong [nhật ký chung](../docs/PROJECT_DEVELOPMENT_LOG.md), mục 13–14. Ngày trên là ngày ghi nhận audit, không suy thành thời điểm training gốc.

## A. Warnings thực tế

**D — DeprecationWarning:** message rút gọn trung thành: `datetime.datetime.utcnow() is deprecated ... Use timezone-aware objects ... datetime.datetime.now(datetime.UTC).` Toàn bộ message gốc nằm trong JSON evidence. Python đã deprecate API này từ 3.12; đây là vấn đề tương thích API thời gian, không phải cảnh báo optimizer. [Python datetime](https://docs.python.org/3.13/library/datetime.html#datetime.datetime.utcnow).

**R — ResourceWarning:** `Unclosed socket <zmq.Socket(zmq.PUSH) at 0x...>`. PyZMQ mô tả warning này khi socket chưa được đóng rõ ràng và được thu gom sau đó. Cần theo dõi vòng đời tài nguyên/runtime; không thể xác định module tạo socket từ chuỗi warning vì không có filename/lineno. [PyZMQ Socket.close](https://pyzmq.readthedocs.io/en/stable/api/zmq.html#zmq.Socket.close).

| Model | Trong fit | Trong predict validation | Tổng gốc | Severity và tác động |
|---|---|---|---:|---|
| Logistic Regression | 3D + 1R | 2D | 6 | INFO (D); REVIEW (R) |
| Random Forest | 0 | 3D | 3 | INFO: tương thích API |
| LinearSVC | 2D + 1R | 2D | 5 | INFO (D); REVIEW (R) |
| KNN | 0 | 30D + 1R | 31 | INFO (D); REVIEW (R) |
| BernoulliNB | 0 | 2D | 2 | INFO: tương thích API |

Có **44 D và 3 R** trong bản ghi gốc; count 6/3/5/31/2 khớp bảng người dùng. Ba socket có địa chỉ lần lượt LR `0x7b47685decf0`, LinearSVC `0x7b47685dfe70`, KNN `0x7b47685dfd20`. KNN có 30 D + 1 R; không phải 31 cảnh báo khoảng cách, prediction lỗi hoặc không hội tụ.

Không có `ConvergenceWarning`, `UndefinedMetricWarning`, cảnh báo numerical/schema hoặc version mismatch trong các bản ghi đã gửi. LR/LinearSVC hoàn tất và không có vấn đề hội tụ được ghi nhận; không suy thành bảo đảm tối ưu tuyệt đối. F1=0 của một số lớp vẫn được tính đúng theo zero_division=0.

Warnings mới trong lần reload/inference được tách riêng: chỉ D, số lần LR/RF/LinearSVC/KNN/NB = **2/3/2/21/2**. Không có R mới trong capture reload này; không kết luận việc quản lý socket đã được sửa. Tất cả prediction sau reload vẫn khớp.

**Xử lý đề xuất:** giữ warning, không suppress hoặc retrain chỉ để làm sạch output. Source dự án hiện dùng `datetime.now(timezone.utc)`, không tìm thấy lời gọi `utcnow()` hoặc tạo socket zmq trong `src/`; nguồn dependency/runtime là khả năng suy luận, chưa xác định component cụ thể. Nếu warning tái diễn kèm gián đoạn tài nguyên, thu filename/lineno/stack và sửa đúng component trong nhiệm vụ riêng; chưa có bản sửa được thực hiện.

**Giới hạn capture:** bản ghi gốc lưu loại/message ở fit và predict; không lưu filename/lineno, không bao phủ toàn bộ serialization, metrics hoặc reporting. “Không có warning được lưu” không đồng nghĩa đã kiểm mọi warning trong lịch sử phiên. Các warning quan sát được không cho thấy output model không hợp lệ; R giữ REVIEW về tài nguyên.

## B. Checkpoint và reload

Root checkpoint thực: `/content/drive/MyDrive/ML_Projects/disease-prediction-ml/artifacts/models/phase3/baseline-v1-f8a5bfdb7b4c12cd/`.

Mỗi folder model_key có đủ `pipeline.joblib`, `fit.json`, `metadata.json`, `validation_predictions.npz`: **20 file tồn tại**. SHA model/fit/predictions khớp bản ghi; metadata identity/nội dung nhất quán. SHA quan sát và size từng file, gồm metadata.json, được giữ trong JSON evidence.

| model_key | pipeline.joblib (byte) | Integrity / fitted / reload | Sai khác predictions |
|---|---:|---|---:|
| `logistic_regression` | 1438385 | PASS | 0 |
| `random_forest` | 14420893 | PASS | 0 |
| `linear_svc` | 1463693 | PASS | 0 |
| `knn` | 652535 | PASS | 0 |
| `bernoulli_nb` | 102624 | PASS | 0 |

Cả năm checkpoint thuộc cùng experiment và đúng fingerprint train/validation, feature schema, label mapping và config được duyệt. Source differences và library-version differences đều rỗng. Chỉ load checkpoint của dự án sau kiểm integrity, dùng `load_fitted_checkpoint(..., trusted=True)`; classifier và transformer được kiểm fitted. Không ghi lại checkpoint.

**Reload PASS 5/5:** dự đoán validation chia batch 64, so toàn bộ 28.120 hàng với predictions đã lưu, không có sai khác. Không dùng thời gian lần audit làm benchmark mới. Ba hình đã có cũng PASS checksum; không tạo hình mới.

## C. Metrics xác minh từ predictions validation

Chung validation đã khóa: **28.120 dòng, 375 input feature, đủ 587 nhãn** theo mapping Phase 2. `read_completed_checkpoint` kiểm checksum, y_true, group_id, row order và tính lại metrics; comparison CSV và run_summary đều PASS đối chiếu.

| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 | Weighted F1 |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.83709104 | 0.82741979 | 0.77918852 | 0.78780814 | 0.83667539 |
| Random Forest | 0.70053343 | 0.65965116 | 0.44122978 | 0.49199733 | 0.69931066 |
| LinearSVC | 0.83079659 | 0.81520597 | 0.78139866 | 0.78422186 | 0.82986599 |
| KNN | 0.78314367 | 0.78361997 | 0.73192046 | 0.73103438 | 0.78680402 |
| BernoulliNB | 0.81486486 | 0.67229708 | 0.57387513 | 0.59934053 | 0.80525048 |

Policy **zero_division=0**, scores xét toàn bộ label mapping. Tolerance audit CSV/summary: `rtol=1e-10, atol=1e-12`; project checkpoint reader còn kiểm equality chính xác với metrics lưu. Bảng tham chiếu 5 chữ số và thời gian gốc khớp trong `atol=5e-6+1e-12`; warning counts khớp chính xác. Không có discrepancy cần thay lịch sử metrics.

## D. Pipeline, mask và hành vi theo lớp

**PASS 5/5:** pipeline giữ đủ đầu vào 375 feature đúng thứ tự, `VarianceThreshold(0)` fitted, CSR dùng đúng custom function `src.models.training.to_csr`, estimator fitted và classes khớp 587 mã nhãn. Không có scaler học riêng theo model. Cả năm giữ **318 feature**, bỏ 57 feature hằng trong train, mask giống nhau; SHA mask uint8:

`75b92ddca48748d807ff5ba7cf127504e5d6867980ce1a6f7a9c8b92b4fa8373`

Variances/mask lưu khớp thống kê chỉ từ X_train; source/notebook chỉ truyền train vào fit. Đây là bằng chứng nhất quán với train-only preprocessing, không có dấu lệch mask hoặc leakage được phát hiện. Không phải chứng minh tuyệt đối mọi thao tác ngoài log trong lịch sử kernel; Phase 1 đã EDA toàn CSV trước khi khóa test vẫn là giới hạn đã công bố.

Phase 2 Drive manifest SHA `50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9`; processed fingerprint `afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3`. Input schema/inference tiếp tục là **375**, không đổi schema Phase 2 thành 318.

| Model | Số lớp được dự đoán | Chưa từng dự đoán | Lớp F1=0 | Weighted−Macro F1 |
|---|---:|---:|---:|---:|
| Logistic Regression | 560 | 27 | 28 | 0.04887 |
| Random Forest | 430 | 157 | 157 | 0.20731 |
| LinearSVC | 564 | 23 | 24 | 0.04564 |
| KNN | 560 | 27 | 34 | 0.05577 |
| BernoulliNB | 444 | 143 | 144 | 0.20591 |

Validation support: **min 1, median 25, max 215**; **33 lớp support 1, 68 lớp ≤2, 132 lớp ≤5**. Support là số vector phân biệt theo lớp sau dedup, không chứng minh độc lập bệnh nhân. Không diễn giải F1 của vài vector là ổn định.

RF/NB có độ phủ dự đoán thấp và gap Weighted–Macro khoảng 0,2073/0,2059, cần xem giới hạn theo lớp khi chọn thành viên ensemble. Vấn đề không chỉ ở lớp rất hiếm: ví dụ F1=0 có RF `acute glaucoma` (n=17), `alcohol intoxication` (n=22), và NB `bladder disorder` (n=44). Không có bằng chứng đủ để gán nguyên nhân cho underfit, giả định độc lập hoặc chọn siêu tham số. Lớp từng được dự đoán vẫn có thể F1=0 nếu không có true positive.

## E. Tài nguyên đo trong training gốc

Colab/Linux, **Python 3.13.18, sklearn 1.6.1, NumPy 2.1.3, pandas 2.2.3, SciPy 1.16.3, joblib 1.6.0**. CPU Intel Xeon 2,20 GHz, 2 logical CPU, RAM tổng 12,671 GiB; không phát hiện GPU, estimator không dùng GPU. Môi trường training và audit khớp ở các phiên bản được kiểm. Đây không phải môi trường Windows hoặc phiên smoke Colab cũ.

| Model | Fit s | Predict validation s | Peak RSS fit mẫu (MiB) | Peak RSS validation mẫu (MiB) |
|---|---:|---:|---:|---:|
| Logistic Regression | 91.59420 | 2.15747 | 1167.64 | 371.05 |
| Random Forest | 15.10077 | 20.68390 | 1169.13 | 839.46 |
| LinearSVC | 80.59617 | 1.82650 | 1313.38 | 468.77 |
| KNN | 1.09042 | 294.22415 | 1266.73 | 469.09 |
| BernoulliNB | 1.83618 | 5.74700 | 1569.34 | 469.15 |

Thời gian là bản ghi gốc đã đối chiếu, không thay bằng lần inference audit. RSS là peak lấy mẫu của process và child process trong từng stage, không phải bộ nhớ riêng của estimator hoặc peak chính xác tuyệt đối; trạng thái process giữa model khác nhau. Không kết luận NB “nặng nhất” chỉ vì RSS fit ghi cao. Model size nén và RAM khi chạy là hai đại lượng khác nhau.

LR/SVC là ứng viên mạnh theo Macro F1; chênh lệch nhỏ không chứng minh ý nghĩa thống kê. KNN fit rẻ nhưng inference toàn validation 294,22415s, chậm hơn LR/SVC rõ rệt; đây không phải latency một người dùng. RF nhanh khi fit nhưng điểm Macro F1/coverage yếu; NB checkpoint nhỏ và predict nhanh hơn KNN nhưng nhiều lớp không được dự đoán. Chưa chọn trọng số/thành viên Voting từ những số này.

## F. Quyết định trước Phase 4

| Mức | Kết luận |
|---|---|
| PASS | Checkpoint/checksum/identity, fitted pipeline, feature order/mask, mapping, metrics, CSV/summary và reload predictions của cả 5 model. |
| INFO | DeprecationWarning về utcnow; chưa cần sửa model hoặc train lại. |
| REVIEW | Socket lifecycle warning, capture không đầy đủ mọi stage, support lớp nhỏ, coverage RF/NB và chi phí KNN. Các điểm này cần được ghi khi thiết kế ensemble. |
| BLOCKER | Không có trong packet và các đối chiếu đã thực hiện. |

**Khuyến nghị chuyên môn: tiếp tục Phase 4 với giới hạn được ghi nhận, sau khi người dùng xem audit và giao nhiệm vụ tiếp theo.** Cờ phase4_ready trong run summary là true; quyết định này còn dựa trên integrity/reload/metrics và warning audit, không dựa riêng cờ completed. Chưa chứng minh LR/SVC có lỗi đủ khác nhau để Voting cải thiện; phân tích lỗi validation từng cặp là công việc tương lai, chưa chạy ở đây. Không mặc định dùng cả 5 hoặc loại RF/NB chỉ do điểm thấp.

Không có defect đã xác nhận đòi đổi model/hyperparameter/preprocessing. Chưa thực hiện sửa dependency/runtime để xử lý warning vì chưa xác định call site; không suppress warnings. Đã hoàn tất audit và dừng trước ensemble.

## Kiểm tra và bảo toàn

Packet SHA-256 khớp; kiểm nội bộ 5 model đều PASS, mỗi model 0 prediction mismatch, reference values khớp, 15 SHA có giá trị expected khớp và 20 file tồn tại. Guard Colab ghi **0 model/feature fit attempt, 0 test payload access, 0 persistent write attempt**; 15 lần LabelEncoder tạm của hàm metrics được đếm riêng, không thay label mapping.

Agent chỉ đọc evidence local và nguồn code để viết báo cáo; không tự fit/predict/benchmark thêm. Model, tham số, notebook, bootstrap, dataset và Phase 2 giữ nguyên. Chỉ lưu evidence, cập nhật báo cáo này và thêm mục nhật ký. [Script audit](../scripts/audit_phase3_results.py) cùng [7 unit test local đã kiểm trước](../tests/test_post_training_audit.py) là công cụ hỗ trợ; PASS Colab trong báo cáo dựa trên packet người dùng, không dựa trên fixture unit.


## Liên hệ với phân tích học thuật sau tuning

Cập nhật tài liệu 2026-10-29, không sửa kết quả audit tại các mụcA–F.
[Phân tích học thuật chung](../docs/MODEL_SELECTION_RATIONALE.md#phân-tích-học-thuật-và-lựa-chọn-hiện-tại)
đối chiếu nguyên lý/giả định của cả5 model với toàn bộ metrics, coverage, F1=0, warning, fit/predict và byte/RSS trong packet này.
Nó bổ sung timing một mẫu từ packet structured inference như một phép đo riêng, không gán hardware training vào phép đo đó.

LR có Macro F1 baseline cao nhất; SVC có coverage cao hơn và ít lớp F1=0 hơn, nên không diễn giải LR trội ở mọi tiêu chí.
RF/NB cần đọc khoảng cách Macro–Weighted F1 cùng coverage; KNN fit ngắn nhưng predict toàn validation đắt.
Captured warning0 về convergence không chứng minh mọi stage không có warning hoặc tối ưu đã hội tụ hoàn toàn.
Đây là các kết luận mô tả baseline đã audit, không là kết luận y khoa hay nguyên nhân nhân quả của sai số.

**Bổ sung từ Post-Tuning Audit Colab ngày2026-10-29:** năm selected checkpoint checksum/feature order375/class order587,
parameters và train-only variance mask/reload PASS; seed42 tái tạo đúng CV assignment.
Cả3 train fold đủ587 lớp; holdout586/586/587, scorer giữ587 nhãn/zero_division0.
Có15 candidate/45 fold attempts completed, không failed/interrupted/ConvergenceWarning trong state;
warnings search415 DeprecationWarning/36 ResourceWarning. Không gọi model predict/fit trong audit.

LR tuned có Accuracy0.83766003, Macro Precision0.82386664, Macro Recall0.79248487,
Macro F1 = 0.79315438, Weighted F1 = 0.83843972; coverage566/F1zero23.
Macro F1 năm selected lần lượt LR0.79315438,SVC0.78636758,RF0.51090813,KNN0.74567902,NB0.67213832;
cả5 tăng so baseline trong space đã thử. Selected configs/CV/chi phí và trade-off nằm trong rationale chung,
không dùng CV score như validation score hoặc suy ưu thế y khoa.

**MODEL SELECTION PENDING:** best validation Macro F1 là hard tuned LR+SVC+KNN0.79651707,
nhưng LR tuned có Accuracy/Weighted F1 cao hơn. Chưa có measured deployment latency/RAM,
group uncertainty. Supplement `4ccfa85a…` đã cung cấp đủ15 candidate CV/warnings, paired errors/diversity và587 per-class scores;
SHA và arithmetic local khớp. Hard sửa173/làm sai194 dự đoán LR tuned,115 lớp tăng/128 giảm F1;
93.82% net gain Macro F1 đến từ support≤5. Hai lớp zero→positive chỉ1 mẫu/lớp, cần thận trọng với độ ổn định.
Giữ baseline mặc định; không suy LR tuned hoặc ensemble tự động thắng.
Đây là đối chiếu packet do người dùng chạy trên Colab; agent không trực tiếp rehash Drive weights.
Guards packet đều0 fit/predict/test/write/network; không chạy lại notebook để cập nhật tài liệu.
Toàn bộ source/checkpoint/schema/mapping/split/notebook và evidence cũ giữ nguyên trong vòng viết tài liệu này.
