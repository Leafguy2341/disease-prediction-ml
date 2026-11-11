> ARCHIVE — Bản tại thời điểm trước hợp nhất tài liệu. Các trạng thái và lệnh cũ không phải hướng dẫn hiện hành. Xem [chỉ mục hiện hành](../../README.md) và [triển khai](../../DEPLOYMENT_GUIDE.md). Đường dẫn trong code block vẫn tính từ project root.

# Phân tích mô hình và cơ sở lựa chọn

**Quyết định hiện hành 2026-10-30:** owner đã duyệt **LR tuned C=2** cho deployment chatbot/API nghiên cứu,
trước khi mở test. Các đoạn `MODEL SELECTION PENDING` bên dưới là lịch sử đến 2026-10-29;
không xóa hoặc dùng chúng thay quyết định mới. Final test nay đã hoàn tất và được audit read-only;
Prediction API mới chỉ dùng LR tuned C=2, không thay baseline config/checkpoint lịch sử.
Giao thức ba ứng viên được khóa tại [Final locked-test protocol](#final-locked-test-protocol-2026-10-30).

**Closeout 2026-10-30:** [báo cáo final evaluation](../../../reports/final_model_evaluation_closeout.md)
ghi kết quả verified từ packet Colab SHA `102845056236bfe3855962cd1717ece4402a958cc6ce593540ab1ccab4f34131`.
Macro F1 test: LR baseline **0.7958306745796887**; LR tuned **0.808163486172862**;
hard tuned **0.8059813671672197**. Manifest gốc `f1ad195e…754a`; đủ587 labels,28.066 rows/25.128 groups.
Metrics tính lại từ saved predictions khớp JSON/CSV; closeout không mở lại test hoặc predict.
LR tuned đã được duyệt trước test; không chọn lại model từ các số này. Hard tuned giữ vị trí tốt nhất
trên validation, LR tuned cao nhất trên final test trong ba ứng viên cố định; không suy diễn thắng tổng quát hoặc lâm sàng.
Notebook06 nay chỉ replay bằng `read_completed`, gate False/authorization trống, outputs thực thi được giữ nguyên.
API/schema/HTTP tests là offline synthetic; real checkpoint local reload/inference vẫn NOT VERIFIED.
Các câu “chưa thực thi final test” ở phần protocol/lịch sử dưới đây mô tả lúc freeze, không phải trạng thái hiện hành.

## Decision record lựa chọn ML

**Ngày 2026-10-29 — MODEL SELECTION PENDING.** Đây là đề xuất trình nhóm; chưa ghi nhận phê duyệt thay model.
LR baseline vẫn là default. Tài liệu không thay config, checkpoint, notebook switches hoặc deployment.

### Bài toán, dữ liệu và căn cứ

Phân loại đa lớp nhãn disease tiếng Anh từ 375 indicator triệu chứng, 587 lớp sau Phase2.
Train 131.248 dòng, validation 28.120 dòng; group theo symptom vector, split seed42, không mở locked test.
Metric chính Macro F1 đủ587 nhãn/zero_division=0, đọc cùng Accuracy, Macro Precision/Recall, Weighted F1 và coverage.
Input vẫn375 cột đúng thứ tự; pipeline đã fit VarianceThreshold(0)→CSR→estimator, không tự bỏ57 cột hằng trước inference.
Phase1 từng EDA toàn CSV; giữ test khóa hiện nay không đồng nghĩa chưa từng thăm dò nó.
Final evaluation phải ghi giới hạn đó; đánh giá mù nghiêm ngặt cần dữ liệu độc lập chưa thăm dò.

Năm họ cho các giả thuyết so sánh: LR tuyến tính xác suất; LinearSVC tuyến tính theo margin;
RF học quan hệ phi tuyến bằng cây; KNN kiểm tính tương tự cục bộ; BernoulliNB là mốc xác suất sinh cho nhị phân.
Đây là phạm vi nghiên cứu có chủ đích, không chứng minh năm thuật toán tối ưu toàn cục.

Số dưới đây **chép lại kết quả đã audit**, không đánh giá mới. Nguồn là sáu packet Phase3, Phase4, structured inference,
Post-Tuning, model-analysis supplement và ML_GAPS, được dẫn trong
[bảng bằng chứng](#bằng-chứng-phạm-vi-và-trạng-thái-lựa-chọn) và [ML_GAPS](#bằng-chứng-bổ-sung-ml-gaps-và-đề-xuất-để-nhóm-duyệt).
Bảng đầy đủ Accuracy/MacroP/MacroR/MacroF1/WeightedF1/coverage,15 candidate CV và các hình cũ giữ nguyên
ở [baseline](#chất-lượng-năm-baseline-trên-cùng-validation), [tuning](#phân-tích-tuning-theo-từng-họ-mô-hình),
[ensemble baseline](#ensemble-baseline-kết-quả-và-cơ-chế-giải-thích) và [ensemble tuned](#ensemble-tuned-kết-quả-đã-kiểm-và-giới-hạn-giải-thích).
Tái sử dụng [hình paired errors và support](../../../../disease-prediction-ml-data/reports/figures/model_selection_tuned_error_analysis.png) cùng các hình/bảng gốc
được reports Phase3/4 dẫn lại; Baseline-vs-Tuned chart thuộc reports/tuning/<experiment>/ trên Drive.
Không tạo figure hoặc metrics mới cho decision record.

### Cấu hình và tác động tuning

| Model | Baseline trong phase3.json | Tuned đã chọn, giữ tham số khác | Macro F1 baseline | Macro F1 tuned |
|---|---|---|---|---|
| Logistic Regression | saga; C=1; max_iter=200; tol=0.001 | C=2 | 0.78780814 | 0.79315438 |
| LinearSVC | C=1; dual=auto; max_iter=3000; tol=0.001 | C=2 | 0.78422186 | 0.78636758 |
| Random Forest | 100 cây; depth=24; max_leaf_nodes=512; min_leaf=2; max_features=sqrt | depth=32 | 0.49199733 | 0.51090813 |
| KNN | k=5; weights=distance; brute; Manhattan | k=7 | 0.73103438 | 0.74567902 |
| BernoulliNB | alpha=1; binarize=None | alpha=0.5 | 0.59934053 | 0.67213832 |

LR/SVC/RF random_state42; RF tối đa2 worker, KNN1, BLAS1. Tham số đầy đủ/factory ở
[phase3.json](../../../configs/phase3.json) và [training.py](../../../src/models/training.py).
Tuned parameters lấy selection/identity riêng, **không sửa baseline config thành tuned**.

Train-only StratifiedGroupKFold3/shuffle/seed42; preprocessing fit trong train của từng fold.
15 candidate/45 fold attempts hoàn tất; selection khóa trước validation. Train folds đủ587 lớp;
holdout thực **586/586/587**, scorer vẫn587, không dùng counts local thời implementation thay run Colab.
Cả5 model tăng validation Macro F1 trong space đã thử. LR/SVC cải thiện nhỏ; RF/KNN tăng nhưng chưa dẫn nhóm;
NB tăng nhiều nhất nhưng tuned F1 vẫn thấp hơn LR/SVC/KNN. Tăng điểm không xóa rare-class failures hoặc chứng minh cơ chế nguyên nhân.
Không mở rộng space hay chọn lại seed sau khi xem validation.

### Ensemble trước và sau tuning

| Tổ hợp uniform | Macro F1 baseline | Macro F1 tuned | Baseline: cứu/làm sai LR | Tuned: cứu/làm sai LR |
|---|---|---|---|---|
| Hard LR+SVC+KNN | 0.78733399 | 0.79651707 | 152/170 | 173/194 |
| Hard LR+SVC+NB | 0.78478926 | 0.78725551 | 160/187 | 185/201 |
| Hard LR+SVC+RF | 0.78405303 | 0.78769267 | 153/199 | 204/258 |
| Soft LR+NB+RF | 0.72469398 | 0.76487052 | 559/887 | 464/604 |
| Soft LR+KNN+NB | 0.76324258 | 0.77043797 | 917/1201 | 743/966 |

Rescue/loss luôn so với **LR cùng giai đoạn**; hai reference baseline/tuned khác nhau.
Ba hard dùng majority; khi hòa ưu tiên LR→SVC→KNN→NB→RF trong thành viên.
Hai soft dùng mean probability thật; exact tie theo LR probability rồi English-label Unicode order.
Giữ các cấu hình baseline/tuned tương ứng bảng trên; không calibrate SVC hoặc tối ưu voting weights.

Baseline hard tốt nhất cứu152 nhưng làm sai170 hàng LR đúng, net−18, F1 thấp hơn LR baseline0.78780814.
LR/SVC có nhiều lỗi chung; chỉ khác họ thuật toán không bảo đảm majority sửa lỗi.
Sau tuning, hard LR+SVC+KNN đạt0.79651707 so LR tuned0.79315438.
Nó cứu173 nhưng làm sai194, net−21; Accuracy/Weighted F1 thấp hơn LR tuned.
Điểm F1 cao hơn đến từ **phân bố F1 theo lớp**:115 lớp tăng,128 giảm,344 không đổi;
93.82% net gain tập trung ở support≤5. Hai lớp từ0→positive chỉ có1 mẫu validation/lớp.
Đó là mô tả từ paired predictions; không chứng minh mọi cặp lỗi độc lập hơn hoặc KNN là nguyên nhân duy nhất.
Soft voting chưa vượt LR cùng giai đoạn; saved-label metrics đã kiểm nhưng soft memmap không persist để audit lại mean độc lập.

### Bất định và chi phí đã đo

Paired group bootstrap seed20261029/B2000, giữ mọi row/label của sampled group cho cả hai model,
labels0..586/zero_division0. Delta hard−LR tuned F1=+0.00336269,
percentile95% **[−0.00003807;+0.00622337]**; Accuracy CI cũng chứa0.
Chưa xác lập ưu thế ổn định, không chứng minh tương đương; fraction positive không là p-value/posterior.
Mọi replicate đều vắng lớp (median19); rare-class discontinuity và repeated-validation selection bias còn giới hạn.

Cùng64 group validation,3 vòng×64 batch1 calls/operation, sau3 warm-ups, cùng runtime Colab đã kiểm:

| Condition | Verified load(s) | Top1p50/p95(ms) | Proba+Top3p50/p95(ms) |
|---|---:|---|---|
| LR tuned | 0.036802 | **13.102 /14.778** | 12.854 /15.073 |
| Hard tuned LR+SVC+KNN | 0.111631 | 48.705 /88.125 | Không có probability Top3 |

Hard cần3 pipeline,3.554.419 compressed bytes; LR tuned1 pipeline,1.438.563 bytes.
Process sampled peak393.535/393.105MiB không là RAM riêng của estimator:
data/kernel/allocator đang resident, sampling0.5s có thể lỡ peak.
Integrity pre-reads, fixed LR→hard order và fit-guard profiler còn ảnh hưởng; không cold-start, concurrency hoặc API SLA.
Không dùng timing baseline để thay tuned.

### Đề xuất phê duyệt và giới hạn

| Vai trò đề xuất | Model | Trạng thái |
|---|---|---|
| Best observed validation Macro F1 | Hard tuned LR+SVC+KNN,0.79651707 | Thành tích quan sát; chưa chọn default |
| Preferred deployment candidate cho API nghiên cứu cần Top3 | LR tuned,0.79315438 | Đề xuất theo output/cost và Accuracy/Weighted F1; chờ nhóm duyệt |
| Default hiện hành | LR baseline,0.78780814 | Giữ nguyên checkpoint đang dùng |

Metric cao nhất và phù hợp API là hai tiêu chí khác nhau: hard vẫn là lựa chọn hợp lệ nếu contract hard-label và chi phí phù hợp.
LR tuned có Top3 score thật, một pipeline và batch1 thấp hơn trong protocol này; không tuyên bố nó thắng Macro F1 hoặc mọi lớp.

Dataset được mô tả là synthetic, chưa clinical validation. 0 là chưa ghi nhận hiện diện, không chắc clinically absent.
Model probability chưa calibration; vector LLM có missing/denied/uncertain/subject/time semantics khác CSV.
375 feature hợp lệ không tự cho phép inference: cần validator/quality gate, hỏi rõ/abstain/urgent và human-reviewed evaluation.
Chưa chốt default, production acceptance criteria, final locked-test protocol hoặc Gemini live/API.
Bước tiếp là nhóm duyệt đề xuất và contract, theo [hướng dẫn bàn giao](../planning/HANDOVER_GUIDE.md);
việc đồng ý làm tài liệu không được hiểu là phê duyệt đổi model.

---

Đoạn trạng thái kế tiếp giữ snapshot **trước ML_GAPS**. Trạng thái mới nhất nằm ở phần “Bổ sung sau ML_GAPS”
và [kết quả cuối tài liệu](#bằng-chứng-bổ-sung-ml-gaps-và-đề-xuất-để-nhóm-duyệt); không đọc các câu thiếu bằng chứng cũ như trạng thái hiện hành.

**Cập nhật 2026-10-29 — MODEL SELECTION PENDING.** Đã nhận và kiểm toàn vẹn packet Post-Tuning Audit Colab: năm checkpoint tuned reload PASS; metrics từ validation predictions và hard-vote policy được audit. Hard tuned LR+SVC+KNN dẫn Macro F1 0,79651707; LR tuned đạt 0,79315438 và có Accuracy/Weighted F1 cao hơn. Đã bổ sung đủ15 candidate CV và summary lỗi/per-class; chưa chọn model cuối vì còn thiếu benchmark triển khai và bất định theo group. Xem [phân tích học thuật và lựa chọn hiện tại](#phân-tích-học-thuật-và-lựa-chọn-hiện-tại). Giữ LR baseline làm mặc định hiện có và giữ các đoạn thiết kế ban đầu như lịch sử.

**Bổ sung sau ML_GAPS,2026-10-29:** đã có paired group bootstrap và diagnostic benchmark tuned thật trên Colab.
CI95% delta Macro F1 hard−LR là **[−0.00003807;0.00622337]**,chứa0; LR tuned Top1p50/p95 **13.102/14.778ms**,
hard **48.705/88.125ms** theo cùng panel/protocol. Đây không phải production SLA hoặc clinical evidence.
Đề xuất LR tuned cho hướng API nghiên cứu cần Top3 để nhóm duyệt; **MODEL SELECTION PENDING**,default không đổi.
Các câu “chưa benchmark/chưa bootstrap” trong snapshot trước được đọc cùng
[bằng chứng bổ sung ở cuối](#bằng-chứng-bổ-sung-ml-gaps-và-đề-xuất-để-nhóm-duyệt).

**Trạng thái sau Phase4 (2026-10-28):** các nhận định “chưa train/chưa đo/chưa ensemble” trong phần lý do ban đầu dưới đây là lịch sử thiết kế. Năm baseline nay đã train/audit; ba hard và hai soft đã đánh giá trên Colab theo evidence người dùng gửi. LR dẫn Macro F1 **0,78780814**, được chọn làm inference mặc định cho thiết kế Phase5, chưa final test. Xem [biện luận từ kết quả thực](phase4_ensemble.md#biện-luận-lựa-chọn-mô-hình); tài liệu này không thay thế báo cáo thực nghiệm đó.

Ngày rà soát: 2026-10-28. Giải thích thiết kế đang có trong [configs/phase3.json](../../../configs/phase3.json), [training.py](../../../src/models/training.py) và [notebook 03](../../../notebooks/03_model_training.ipynb). Đây là lý do lựa chọn, **chưa phải kết luận thực nghiệm**; không có bằng chứng năm mô hình này tối ưu toàn cục hoặc Voting sẽ cải thiện điểm.

## Dữ liệu và giao thức giữ nguyên

[Phase 2](../../../reports/preprocessing_decision_review.md) đã khóa 187.434 dòng, 375 feature nhị phân và 587 lớp. Train có 131.248 dòng, validation 28.120 dòng; test tách riêng. EDA trên schema gốc ghi nhận trung bình 5,33 triệu chứng hiện diện/dòng: biểu diễn thưa, không phải văn bản cần embedding. Lớp hiếm và vector mang nhiều nhãn vẫn là giới hạn; cùng input không thể giúp classifier tất định phân biệt mọi nhãn xung đột.

Năm họ học tạo các giả thuyết khác nhau trên cùng dữ liệu: tuyến tính xác suất, tuyến tính theo margin, cây phi tuyến, láng giềng và xác suất sinh. Lựa chọn này giới hạn phạm vi so sánh ban đầu và bao quát cách học khác nhau; chưa có benchmark để xếp hạng.

Mỗi pipeline hiện có `VarianceThreshold(0) → CSR float64 → estimator`, fit transformer chỉ trong train. Các giá trị input đã cùng thang 0/1; cấu hình hiện tại không center/scale, không PCA hoặc tạo feature mới. Macro F1 là metric chọn chính (`zero_division=0`), kèm accuracy, macro precision/recall, weighted F1. Giữ split group seed 42, cùng validation và mapping cho mọi model; không chọn model/hyperparameter bằng test.

## Giả định, lợi ích, giới hạn và tài nguyên

| Mô hình | Cơ sở và giả định | Điểm mạnh và giới hạn cần kiểm | Fit và inference |
|---|---|---|---|
| **Logistic Regression** | Baseline xác suất; logit tuyến tính có điều chuẩn, dùng được input thưa. | Dễ so sánh trọng số; không tự học tương tác phi tuyến. Không đòi các feature độc lập; xác suất chưa được bảo đảm calibration trên dữ liệu này. | Fit lặp với `saga`; cần kiểm hội tụ. Inference chủ yếu nhân ma trận với trọng số theo lớp, không cần giữ toàn train. [Tài liệu](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html). |
| **Linear SVM / LinearSVC** | Baseline tuyến tính theo margin; đa lớp one-vs-rest. | So sánh hàm mất mát khác Logistic Regression; vẫn hạn chế ở ranh giới tuyến tính và nhạy điều chuẩn/hội tụ. Margin không phải xác suất. | Fit nhiều bài toán theo lớp; hỗ trợ sparse, tránh kernel matrix toàn cục. Inference dùng trọng số tuyến tính; 587 lớp vẫn có chi phí. [Tài liệu](https://scikit-learn.org/stable/modules/generated/sklearn.svm.LinearSVC.html). |
| **Random Forest** | Tổ hợp cây chia theo feature, học tương tác và ranh giới phi tuyến. | Không yêu cầu tuyến tính/độc lập có điều kiện. Có thể overfit hoặc kém ở lớp ít dữ liệu; giới hạn độ sâu/lá có thể gây underfit. | Nhiều cây và phân bố 587 lớp tại node có thể tốn RAM/artifact; inference duyệt cây. Giới hạn cây/lá và worker nhằm kiểm soát tài nguyên, chưa chứng minh đủ RAM bằng training thật. [Tài liệu](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html). |
| **KNN** | Instance-based: vector gần nhau theo khoảng cách đã chọn được giả định có nhãn hữu ích. | Không ép ranh giới tuyến tính; Manhattan trên nhị phân đếm số vị trí khác nhau. Feature hiếm, chiều cao và vector xung đột có thể làm láng giềng kém phân biệt. | Fit chủ yếu giữ dữ liệu, model mang theo train. Brute-force inference so sánh với train, là rủi ro thời gian/RAM; batch chỉ giảm bộ nhớ đỉnh, không loại chi phí tìm kiếm. [Tài liệu](https://scikit-learn.org/stable/modules/neighbors.html). |
| **Bernoulli Naive Bayes** | Mỗi feature là Bernoulli; giả định độc lập có điều kiện theo lớp. | Khớp miền nhị phân, baseline đơn giản. Tương quan triệu chứng vi phạm giả định; dùng cả giá trị 0 nên phải xem giới hạn ngữ nghĩa bên dưới. | Ước lượng thống kê feature–lớp, thường nhẹ hơn mô hình phức tạp; inference dùng các thống kê đã fit. Chưa có số đo tài nguyên của dự án. [API](https://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.BernoulliNB.html), [giả định NB](https://scikit-learn.org/stable/modules/naive_bayes.html). |

Các nhận định chi phí trên là đặc tính thuật toán và suy luận thiết kế, không phải thời gian/RAM đã đo. Tham số hiện tại được đối chiếu trực tiếp với config:

| Model key | Thiết lập ban đầu đáng chú ý |
|---|---|
| `logistic_regression` | `solver=saga`, `C=1`, `max_iter=200`, `tol=0.001` |
| `linear_svc` | `C=1`, `dual=auto`, `max_iter=3000`, `tol=0.001` |
| `random_forest` | 100 cây, `max_depth=24`, `max_leaf_nodes=512`, `min_samples_leaf=2`, `max_features=sqrt` |
| `knn` | `k=5`, `weights=distance`, `algorithm=brute`, `metric=manhattan` |
| `bernoulli_nb` | `alpha=1`, `binarize=None` vì input đã nhị phân |

Chạy tuần tự trên CPU, tối đa 2 worker cho model có hỗ trợ, BLAS 1 thread, working memory 128 MiB, prediction batch 64 và kiểm tối thiểu 2 GiB RAM khả dụng trước bắt đầu model. Đây là giới hạn điều phối trong config, **không phải trần cứng tổng RAM**. GPU Colab không tự tăng tốc các estimator scikit-learn này. Chưa dùng runtime thật để đo fit/inference; smoke PASS chỉ kiểm hạ tầng và nạp dữ liệu.

## Vì sao chọn BernoulliNB và phân biệt các biến thể

| Biến thể | Giả định dữ liệu | Quan hệ với input dự án |
|---|---|---|
| GaussianNB | Feature liên tục, likelihood Gaussian theo lớp | Không khớp tự nhiên với indicator 0/1. |
| MultinomialNB | Số đếm/tần suất không âm | Chạy được trên 0/1 nhưng mô hình sự kiện khác indicator Bernoulli. |
| ComplementNB | Biến thể multinomial dùng thống kê phần bù lớp | Có động cơ cho mất cân bằng, không tự khắc phục ý nghĩa indicator. |
| BernoulliNB | Indicator nhị phân | Khớp trực tiếp miền input đã khóa. |

Các khác biệt phân phối trên theo [hướng dẫn Naive Bayes](https://scikit-learn.org/stable/modules/naive_bayes.html). CategoricalNB dành cho feature phân loại nhiều giá trị; cũng biểu diễn được biến hai giá trị, nhưng chưa có nhu cầu thay baseline Bernoulli chuyên cho nhị phân. [CategoricalNB](https://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.CategoricalNB.html).

BernoulliNB tính cả xác suất của trạng thái 0 và 1. Trong dataset này, 0 chỉ là “chưa ghi nhận hiện diện”, không phải âm tính lâm sàng. Vì vậy baseline học **mẫu ghi nhận trong CSV**; tính phù hợp số học không chứng minh giả định ghi nhận đúng với hội thoại thật. Cần đánh giá thiếu triệu chứng và sai lệch ánh xạ ở phase tích hợp, giữ phủ định/chưa chắc/chưa nhắc trong sidecar theo [hợp đồng kiến trúc](../integration/SYSTEM_ARCHITECTURE.md). Không đổi policy hay loại model trong nhiệm vụ tài liệu này.

`alpha=1` làm trơn các thống kê; không sửa được phụ thuộc triệu chứng, thiếu thông tin hoặc xác suất quá tự tin. Có `predict_proba` không đồng nghĩa đã có độ tin cậy được kiểm chứng. [Hướng dẫn NB](https://scikit-learn.org/stable/modules/naive_bayes.html), [BernoulliNB](https://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.BernoulliNB.html).

## Voting và các phương án ngoài phạm vi ban đầu

Khác họ học có thể tạo lỗi bổ sung cho nhau, là lý do **đề xuất** xem xét Voting sau baseline. Khác thuật toán không bảo đảm khác lỗi: mọi model dùng cùng schema/dữ liệu, Logistic Regression và LinearSVC đều tuyến tính; xung đột nhãn và triệu chứng thiếu có thể khiến nhiều model cùng sai. Cần prediction validation thực và chi phí triển khai trước khi chọn thành viên/trọng số; không mặc định ghép cả năm.

Hard voting dùng nhãn nên có thể đưa LinearSVC vào. Soft voting cần các phân bố xác suất cùng thứ tự lớp và được kiểm tra calibration phù hợp; LinearSVC hiện không có `predict_proba`, không tự chuyển margin thành xác suất. Nếu sau này cần calibration, phải thiết kế riêng trên train/group CV, không lấn test hoặc âm thầm dùng lại validation chọn ensemble. [VotingClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html). Chưa triển khai hoặc chạy ensemble.

| Phương án | Vì sao chưa thêm vào đợt đầu |
|---|---|
| Gradient boosting | Ứng viên tabular phi tuyến hợp lý; nhóm ưu tiên hoàn thành năm baseline đang có trước khi mở thêm không gian tham số, thời gian và phụ thuộc. Đây là giới hạn phạm vi, không có thí nghiệm cho thấy boosting kém hơn Random Forest. [Họ boosting](https://scikit-learn.org/stable/modules/ensemble.html#gradient-boosting). |
| MLP | Thêm kiến trúc, điều chuẩn, learning rate và kiểm hội tụ/khởi tạo; chưa cần cho input indicator để trả lời câu hỏi baseline ban đầu. Chưa có bằng chứng MLP tốt hơn/kém hơn. [MLP](https://scikit-learn.org/stable/modules/neural_networks_supervised.html). |
| Kernel SVM | Train 131.248 dòng/587 lớp khiến kernel SVC đáng lo về tài nguyên; tài liệu nêu fit tăng ít nhất bậc hai theo số mẫu. LinearSVC là đối chứng tuyến tính có sẵn; chưa benchmark kernel trên dự án. [SVC](https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVC.html). |

## Hai trực quan hóa dự kiến sau huấn luyện

1. **Validation Macro F1 so với thời gian fit/predict:** dùng `metrics.macro_f1`, `fit_seconds`, `prediction_seconds` từ checkpoint thành công; hai panel hoặc hai trục thời gian được ghi rõ. So sánh cùng validation, phần cứng/phiên bản/batch và identity; thời gian dự đoán toàn validation không được gọi là độ trễ một lượt chatbot. Model lỗi/thiếu dữ liệu để NA, không gán điểm 0 giả. Chưa tạo biểu đồ này.
2. **Độ giống lỗi validation từng cặp:** căn `row_0based`, `y_true`, `group_id` trong `validation_predictions.npz` của cùng split, đặt `e_m[i]=1` khi dự đoán sai. Đề xuất heatmap Jaccard của hai tập dòng sai (giao/hợp), kèm số cùng sai/tổng sai và F1 từng model. Cặp đều không sai thì Jaccard NA, không gán “đa dạng hoàn hảo”; chỉ báo này đo cùng vị trí sai, không đo hai model chọn cùng nhãn sai. Dòng chung group còn phụ thuộc; nếu báo khoảng tin cậy thì lấy mẫu theo group. Chưa có predictions để tính hoặc chọn ensemble.

Nguồn trường checkpoint: [training.py](../../../src/models/training.py); biểu đồ sẵn có của Phase 3 ở [reporting.py](../../../src/models/reporting.py) không đồng nghĩa hai đề xuất này đã được triển khai. Không tạo hình hiệu năng mô phỏng. Tài liệu scikit-learn được tra cứu ngày 2026-10-28 để giải thích thuật toán, không thay pin dependency/cấu hình hiện tại.

Trạng thái và bước tiếp theo xem [nhật ký phát triển](../planning/PROJECT_DEVELOPMENT_LOG.md).

## Hyperparameter tuning có kiểm soát

Cập nhật 2026-10-29: thêm **Section5** vào cuối [notebook03](../../../notebooks/03_model_training.ipynb)
và **Tuned Ensemble Evaluation** vào cuối [notebook04](../../../notebooks/04_ensemble.ipynb).
Giữ nguyên cell/output baseline. **Đã có output tuning do người dùng chạy; artifact Post-Tuning Audit chưa được xác minh độc lập**; kết luận LR mặc định từ
[Phase4 đã kiểm](phase4_ensemble.md) không đổi. Không thêm notebook06.

### Search space chốt trước khi chạy

| Model | Tham số thử (đậm là baseline) | Các tham số khác giữ nguyên |
|---|---|---|
| Logistic Regression | C = **1**, 0.5, 2 | saga, max_iter=200, tol=0.001, seed42 |
| LinearSVC | C = **1**, 0.5, 2 | dual=auto, max_iter=3000, tol=0.001, seed42 |
| Random Forest | max_depth = **24**, 16, 32 | 100 cây, max_leaf_nodes=512, min_samples_leaf=2, max_features=sqrt, seed42 |
| KNN | n_neighbors = **5**, 3, 7 | distance weights, brute, manhattan, n_jobs=1 |
| BernoulliNB | alpha = **1**, 0.5, 2 | binarize=None |

Danh sách nằm tại [tuning.py](../../../src/models/tuning.py), không mở rộng/thay sau khi xem validation.
15 candidate ×3 fold =45 fold fits, sau đó tối đa5 selected full-train fits, không có unlimited GridSearchCV.
Baseline candidate trong CV là pipeline fold mới; không gọi lại fit trên checkpoint baseline đã hoàn tất.
Nếu baseline config đổi ở thí nghiệm tương lai, helper vẫn đưa baseline vào đầu, deduplicate,
chặn quá4 candidate/model và tạo experiment ID khác; không sửa kết quả cũ.

### CV, scoring và selection

[StratifiedGroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html)
3 fold, shuffle=True, seed42, dùng **group_id thật của train đã khóa**, cùng assignment cho mọi candidate.
Chỉ train đi vào search. Mỗi fold tạo pipeline mới bằng helper Phase3: VarianceThreshold(0) → CSR → estimator.
Variance chỉ fit trên fold train; selected pipeline cuối chỉ fit trên full train.

Điểm là mean không trọng số của3 fold Macro F1, **labels=np.arange(587), zero_division=0**.
Lớp vắng vẫn nằm trong mẫu số; vắng cả true/predicted thì F1=0, không bỏ lớp hoặc resplit để nâng điểm.
Lưu missing_train_classes/missing_holdout_classes và splitter warnings.
[Chính sách labels/zero_division](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html).
Chỉ candidate có đủ3 fold thành công được chọn. Mean cao nhất thắng; hòa chính xác chọn candidate trước
(baseline đứng đầu). Không dùng validation/thời gian để chọn hyperparameter.
Search chưa hoàn tất hoặc mọi candidate của một model lỗi thì dừng rõ ràng.
**Khóa cả5 cấu hình trước bất kỳ đánh giá validation selected nào**, rồi fit selected một lần/model và đánh giá validation.

### Tài nguyên và resume

Chạy tuần tự model/candidate/fold; RF≤2 workers, KNN1, BLAS1, working_memory≤128 MiB,
prediction batch≤64, RAM khả dụng≥2 GiB trước fit. SGKF dùng ma trận group×class khá lớn:
kiểm RAM trước allocation với sàn2 GiB cộng2 lần group×class×8 byte (khoảng3,03 GiB trên train hiện tại).
Đây là ước lượng, không phải hard peak-RAM cap; working_memory không chặn mọi allocation.
[Quản lý thread của scikit-learn](https://scikit-learn.org/stable/computing/parallelism.html).

In model/parameters/candidate/fold, kết quả/thời gian/warning count và heartbeat/RSS khi lâu;
ghi đầy đủ warnings/errors vào metadata, không in hàng trăm warning.
Budget6 giờ/lần gọi search chỉ kiểm **giữa các fold**, không kill fold đang chạy hoặc cam kết hoàn tất trong6 giờ.
Interrupt có lưu attempt; restart có thể reuse score fold xong, chạy lại fold đang dở.
Không lưu fold model. Selected checkpoint/validation-resume dùng **helper Phase3 hiện có**, không cơ chế checkpoint mới.
Một writer/experiment; không dùng hai kernel ghi đồng thời hoặc đổi source/config giữa run và resume.

### Namespace và bảo toàn baseline

- `artifacts/models/tuning/<tuning-v1-id>/<model>/`: chỉ5 selected pipelines, fit metadata và validation predictions/metrics cần thiết.
- `artifacts/metadata/tuning/<id>/`: descriptor/plan, trials có digest, train row/group-to-fold assignment, selection và manifest SHA/size ghi cuối.
- `reports/tuning/<id>/`: một bảng Baseline vs Tuned và đúng một PNG từ metrics thật.
- Notebook04 xuất riêng `reports/runs/tuned-ensemble-*` và `artifacts/metadata/runs/tuned-ensemble-*`:
  bảng11 dòng, predictions ensemble, kết quả/đề xuất và manifest. Probability lớn chỉ ở cache tạm runtime.

Experiment ID bao gồm data/config/library/source/CV assignment. Run hoàn tất chỉ verify/reuse;
checksum/config/source/environment sai thì dừng. State cùng identity của run dở được cập nhật để resume.
Không ghi vào Phase2, `artifacts/models/phase3` hoặc kết quả/manifest/hình Phase4 cũ; không copy baseline model.
Không tạo ZIP/pyz/bootstrap mới hoặc `.venv`.

### Chạy trên Colab trong VS Code

1. Dùng script chuẩn `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/prepare_colab_source.ps1 -Refresh`,
   rồi `-CheckOnly`. Đồng bộ **nội dung** `dist/drive-source/` lên canonical Drive root.
   Mở notebook03/04 local đã cập nhật, chọn Colab kernel, mount Drive và Restart Kernel theo [hướng dẫn chung](../runtime/phase3_colab.md).
2. Notebook03: chạy setup, `ColabTraining.open`, `session.load_data()`; có thể bỏ qua cell fit/report baseline cũ.
   Tại Section5 xem plan, đổi `RUN_HYPERPARAMETER_TUNING = True`, chạy riêng section này.
   `trusted=True` chỉ dùng với checkpoint do dự án tạo và tin cậy. Ghi lại `tuning_result['experiment_id']`.
3. Khi đủ5 selected/manifest, xem bảng/hình thật. Mất VM: setup/load_data lại, giữ cùng source/config và bật switch để resume;
   budget6 giờ tính lại cho lần gọi search mới.
4. Notebook04: chạy shared setup và cell mở session/verify baseline, có thể bỏ qua các cell export baseline cũ.
   Đổi `RUN_TUNED_ENSEMBLE = True`. Một run hoàn tất: giữ `TUNING_EXPERIMENT_ID=None`;
   nhiều run: điền ID cụ thể. Không tự chọn run tốt nhất theo validation.
5. Thiếu tuned run/artifact: **SKIPPED** ở section mới. Artifact có nhưng checksum/schema/source/environment sai: dừng rõ ràng,
   không refit bù hoặc sửa checksum. Baseline inspection không phụ thuộc tuning.

[tuned_ensemble.py](../../../src/models/tuned_ensemble.py) dùng lại Phase4 loader/guard, hard_vote/soft_vote,
probability batching/memmap và tie policies. Load selected tuần tự, kiểm checksum/identity,375 feature names/order,
587 class IDs và pipeline parameters; hard predictions kiểm row_0based/y_true/group_id.
Soft dùng predict_proba thật theo batch nếu thiếu payload hợp lệ, kiểm class order/finite/[0,1]/tổng hàng/argmax;
không softmax/calibrate LinearSVC. Giữ nguyên3 hard +2 soft, uniform weights. Không có fit trong notebook04.

So baseline LR,5 selected model và5 ensemble. Đề xuất theo validation Macro F1; hòa **chính xác** xét ít pipeline,
không KNN, ít compressed bytes, ID ổn định làm proxy chi phí. Không dùng epsilon để bỏ một metric cao hơn.
Proxy không chứng minh latency; saved prediction-time sums có thể khác phiên/phần cứng, không benchmark ngang hàng hoặc SLA.
Không tự thay model ứng dụng hoặc chọn model cuối trên locked test.

### Bằng chứng hiện có và giới hạn

**POST-TUNING AUDIT COLAB PASS; MODEL SELECTION PENDING.** Packet đã nhận có SHA-256 `70849a69a0d2cd571e2d93a938b98a9167b9d46ceb0db9d6cb1859f6a2e415e8`; [kết quả thực bên dưới](#phân-tích-tuning-theo-từng-họ-mô-hình) thay trạng thái thiếu bằng chứng cho checkpoints/metrics. Các số kiểm local tiếp theo giữ như lịch sử implementation; **không dùng chúng để mô tả CV run Colab**.
Unit tests dùng synthetic fixtures/test doubles, không fit sklearn estimator thật và không tạo metrics dự án từ mocks.
Kiểm loader/integrity và tạo CV trên train thật:131.248 dòng,117.211 group,375 feature/587 lớp;
holdout43.750/43.749/43.749 dòng và39.071/39.073/39.067 group, không giao group.
Cả3 fold phủ đủ587 lớp ở hai phía, không splitter warning; guard0 fit/0 test access/0 protected write.
Đây chỉ là kiểm input/CV, **chưa có CV model score hoặc tuned validation metric**.
Số test/kết quả local ghi tại [mục23 nhật ký](../planning/PROJECT_DEVELOPMENT_LOG.md).

> **Đính chính phạm vi:** đoạn local implementation phía trên,bao gồm “cả3 fold phủ đủ587”,là phép kiểm local sklearn1.8 thời điểm đó.
> Run Colab đã khóa thực tế train587/587/587,holdout **586/586/587**,vẫn scorer đủ587 nhãn/zero_division0.
> Xem [fold inventory đã audit](#phân-tích-tuning-theo-từng-họ-mô-hình). Không dùng số43750/43749/43749 local để mô tả holdout Colab43842/43752/43654.

Validation đã được dùng nhiều lần; điểm selected/ensemble mới không phải unbiased final-test estimate.
Audit mới xác nhận selected checkpoint reload và không có ConvergenceWarning được ghi; RAM/latency triển khai và phép cộng soft probabilities vẫn có giới hạn riêng bên dưới.
LR mặc định giữ nguyên; không cần chạy lại notebook hay thay hai switch để cập nhật báo cáo.


## Phân tích học thuật và lựa chọn hiện tại

### Bằng chứng, phạm vi và trạng thái lựa chọn

Phân tích cập nhật ngày2026-10-29. **MODEL SELECTION PENDING** cho lựa chọn sau tuning.
Không dùng số nhìn thấy trong notebook để thay cho manifest/checksum/predictions đã kiểm.
Năm packet bên dưới được đối chiếu SHA với bằng chứng đã nhận, kiểm nhất quán metrics/reference,
pipeline hashes giữa packet, selection arithmetic, transition accounting và diversity có sẵn. Đây là bằng chứng Colab do người dùng cung cấp;
agent không tải lại mọi checkpoint Drive trong nhiệm vụ tài liệu này. SHA bảo đảm toàn vẹn truyền tải, không phải chữ ký xác thực nguồn dữ liệu.

| Nguồn | Nội dung dùng được | Giới hạn |
|---|---|---|
| [Audit Phase3](../../../artifacts/metadata/phase3_audit/colab_evidence.json) | Năm baseline, checksum/reload/predictions/metrics, support, warning và resource capture | Snapshot audit lịch sử; không đo lại hoặc fit lại hôm nay |
| [Audit Phase4](../../../artifacts/metadata/phase4_audit/colab_validation_evidence.json) | Cùng28.120 hàng,3 hard/2 soft, metrics, tie/rescue/diversity và probability provenance | Probability chưa calibration; không là final test |
| [Structured inference](../../../artifacts/metadata/structured_inference/colab_evidence.json) | Các checkpoint baseline trên input375, invalid-input checks, timing7 lần sau warm-up | Một mẫu timing; không là benchmark tuned hoặc SLA API |
| [Post-Tuning Audit](../../../artifacts/metadata/post_tuning_audit/colab_evidence.json), tuning-v1-9c4dd013abbba14a | **PASS** toàn vẹn packet; Colab báo manifest/checksums, 5 reload, CV seed42 và saved validation metrics PASS | Selected CV scores/parameters, actual fold coverage, trial completeness/warnings, 5 tuned +5 ensemble metrics; summary chi tiết được bổ sung ở packet kế tiếp |
| [Model-analysis supplement](../../../artifacts/metadata/model_analysis/colab_supplement.json), cùng tuning/ensemble manifest | **PASS** SHA và arithmetic local; xuất chỉ đọc từ runtime Colab có Drive | Đủ15 candidate scores/warnings, 5ensemble transitions/ties, member diversity và587 per-class F1/support của LR tuned/hard tốt nhất |

SHA ba packet baseline lần lượt là
`41a4ad3b0c3b8c783382b807688fd0958b00666b6e46bb84c3d3fe1e8c16fb48`,
`42cf30dc39547656c572cf5ca4bb6a0eae3a6d31f0a923e6518e8618e835dd44`,
`5dacef332521d797a74c00441bb00161ff21502078ebb12426c7dd4c4be5fd01`.
Các số quan sát chưa kiểm tại mục24 nhật ký giữ đúng nhãn đó, không được dùng như kết luận định lượng đã xác minh ở đây.

Post-Tuning packet có SHA-256 `70849a69a0d2cd571e2d93a938b98a9167b9d46ceb0db9d6cb1859f6a2e415e8`.
Auditor SHA `98cb00071f72e3f3cdb045b618ae6cfa73eae5c30c339db9d989793315603235` khớp [script local](../../../scripts/audit_post_tuning.py).
Tuning manifest: `4a10ddd5deba5fff7927f84ea334196a3f6d127b9777ced2b127f5b5e9389355`;
tuned ensemble manifest: `858893c442f1966eb8c7508a74cf6318b820004278342a1b958942151c049060`,
run `tuned-ensemble-20261029T041701354242Z-6c84dbfe`.
Auditor trên Colab đã kiểm file checksums, liên kết schema/mapping và reload tuần tự cả5 pipeline;
ở local, agent xác minh packet/source SHA và tính nhất quán nội dung, **không tự tải lại Drive weights**.
Supplement có SHA-256 `4ccfa85ac4639778ffae6d11a435fb78af825bb4e1c294792356bec7236b4d28`, cùng tuning/ensemble manifest SHA ở trên.
Summary này đọc lại checksum-verified trials và saved validation predictions, không gọi estimator; đủ15 candidate,5 transitions và587 class scores.
Local kiểm lại selection arithmetic, accuracy accounting, diversity symmetry/error identities và per-class means/support; tất cả khớp.
Counters cả hai audit đều0 cho fit, predict, test payload, persistent writes và network.
PASS integrity không đồng nghĩa chọn model cuối hoặc xác nhận chất lượng y khoa.

### Giao thức và cách đọc kết quả

Dữ liệu Phase2 có375 indicator và587 nhãn bệnh tiếng Anh; train131.248, validation28.120 hàng.
Những vector giống nhau được giữ cùng group qua split, kể cả khi chúng gắn nhãn bệnh khác nhau.
Một classifier tất định không thể phân biệt mọi nhãn xung đột khi input hoàn toàn giống nhau.
Group-disjoint split hạn chế leakage, không tự giải quyết sự mơ hồ này hoặc chứng minh khả năng khái quát sang bệnh nhân thật.
Phase1 từng EDA toàn CSV; không gọi test khóa sau đó là hoàn toàn chưa từng được nhìn thấy dữ liệu. Nhiệm vụ phân tích này không mở test.

Pipeline chung là **375 cột đúng thứ tự → VarianceThreshold(0) → CSR float64 → estimator**.
Audit xác minh cùng mask318 feature biến thiên trên train ở cả5 baseline;57 feature hằng bị loại bên trong pipeline,
không sửa schema input hoặc pre-reduce xuống318 ở API. Không scale/center, PCA, chọn feature bằng validation hoặc SMOTE.
Các baseline không đặt class_weight=balanced; Macro F1 là tiêu chí đánh giá, không có nghĩa hàm mất mát đã cân bằng lớp.

Với lớp k, F1_k = 2TP_k/(2TP_k+FP_k+FN_k); denominator0 được xử lý bằng0.
Macro Precision/Recall/F1 lấy trung bình riêng trên đủ587 lớp; **Macro F1 không phải harmonic mean của Macro Precision và Macro Recall**.
Weighted F1 dùng trọng số support lớp, Accuracy tính tỷ lệ đúng trên hàng. Các metric hiện là row-based,
không phải trung bình đồng trọng số các group. [Định nghĩa F1/labels/zero_division](https://scikit-learn.org/1.6/modules/generated/sklearn.metrics.f1_score.html).

Validation có33 lớp support1,68 lớp support≤2 và132 lớp support≤5; các nhóm này lồng nhau, không cộng lại thành233 lớp khác nhau.
Một vài quyết định có thể làm metric lớp hiếm biến động lớn. Số lớp được dự đoán chỉ đo coverage nhãn;
không bảo đảm đã dự đoán đúng lớp đó. F1=0 có thể do không bao giờ gọi nhãn hoặc có gọi nhưng không lần nào đúng.

### Cấu hình baseline chính xác

Theo configs/phase3.json và source factory gốc; random_state=42 cho LR/SVC/RF, RF n_jobs=2 trên VM đã ghi,
KNN n_jobs=1, BLAS1, working_memory128 MiB và prediction batch64. Mọi cấu hình dưới đây là baseline đã audit,
không phải suy ra từ selected tuning.

| Model | Tham số cấu hình trực tiếp |
|---|---|
| Logistic Regression | `{"solver": "saga", "C": 1.0, "max_iter": 200, "tol": 0.001}` |
| LinearSVC | `{"C": 1.0, "dual": "auto", "max_iter": 3000, "tol": 0.001}` |
| Random Forest | `{"n_estimators": 100, "max_depth": 24, "max_leaf_nodes": 512, "min_samples_leaf": 2, "max_features": "sqrt"}` |
| KNN | `{"n_neighbors": 5, "weights": "distance", "algorithm": "brute", "metric": "manhattan"}` |
| BernoulliNB | `{"alpha": 1.0, "binarize": null}` |

Các default giải thích bên dưới áp dụng cho scikit-learn1.6.1 trong packet gốc; giữ version khi reload.
Không dùng default của một phiên bản mới để diễn giải lại checkpoint cũ.

### Chất lượng năm baseline trên cùng validation

Nguồn: packet Audit Phase3 phía trên; đủ587 nhãn, zero_division=0. Các con số được làm tròn8 chữ số,
không biến chênh lệch nhỏ thành kết luận có ý nghĩa thống kê.

| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 | Weighted F1 | Nhãn được dự đoán | Lớp F1=0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.83709104 | 0.82741979 | 0.77918852 | 0.78780814 | 0.83667539 | 560 | 28 |
| LinearSVC | 0.83079659 | 0.81520597 | 0.78139866 | 0.78422186 | 0.82986599 | 564 | 24 |
| Random Forest | 0.70053343 | 0.65965116 | 0.44122978 | 0.49199733 | 0.69931066 | 430 | 157 |
| KNN | 0.78314367 | 0.78361997 | 0.73192046 | 0.73103438 | 0.78680402 | 560 | 34 |
| BernoulliNB | 0.81486486 | 0.67229708 | 0.57387513 | 0.59934053 | 0.80525048 | 444 | 144 |

LR dẫn Macro F1, Accuracy và Weighted F1 trong năm baseline đã thử. LinearSVC lại có coverage cao hơn và ít lớp F1=0 hơn LR;
vì vậy LR không trội tuyệt đối ở mọi tiêu chí. RF/NB có khoảng cách Weighted F1–Macro F1 lớn,
cho thấy tổng kết theo support thuận lợi hơn tổng kết đồng trọng số lớp, cần đọc cùng coverage thấp.
Các số này mô tả cấu hình đã chạy, không xếp hạng mọi cấu hình có thể của từng họ thuật toán.

### Fit, dự đoán và bộ nhớ baseline

Nguồn: resource capture trong Audit Phase3, CPU Xeon2,20GHz/2 logical CPU, RAM tổng12,671 GiB,
Python3.13.18/sklearn1.6.1; không dùng GPU. Predict là cả28.120 hàng theo batch64, không phải một request.
RSS là peak lấy mẫu toàn process và child process; không cô lập bộ nhớ estimator và không phải hard peak.

| Model | Fit (s) | Predict validation (s) | Pipeline bytes | Nén (MiB) | Fit RSS (MiB) | Predict RSS (MiB) | Deprecation / Resource / Convergence warnings ghi nhận |
|---|---:|---:|---:|---:|---:|---:|---|
| Logistic Regression | 91.594 | 2.157 | 1438385 | 1.372 | 1167.64 | 371.05 | 5 / 1 / 0 |
| LinearSVC | 80.596 | 1.827 | 1463693 | 1.396 | 1313.38 | 468.77 | 4 / 1 / 0 |
| Random Forest | 15.101 | 20.684 | 14420893 | 13.753 | 1169.13 | 839.46 | 3 / 0 / 0 |
| KNN | 1.090 | 294.224 | 652535 | 0.622 | 1266.73 | 469.09 | 30 / 1 / 0 |
| BernoulliNB | 1.836 | 5.747 | 102624 | 0.098 | 1569.34 | 469.15 | 2 / 0 / 0 |

Warnings ghi nhận chủ yếu là datetime.utcnow deprecated và socket zmq chưa đóng; chưa xác định tất cả call sites.
Không ghi nhận ConvergenceWarning trong capture này **không chứng minh hội tụ tối ưu hoặc không có warning ngoài cửa sổ capture**.
RSS fit của NB cao nhất trong bảng không có nghĩa NB riêng lẻ tốn RAM nhất: process đã trải qua các stage/model khác.
KNN có file nén nhỏ nhưng phải giữ dữ liệu tham chiếu; nén tốt không xóa chi phí tính khoảng cách hoặc RAM sau deserialize.

#### Logistic Regression: baseline tuyến tính xác suất

Với đa lớp, mô hình học điểm tuyến tính z_k=w_k^T x+b_k và phân bố softmax trên587 lớp.
Cấu hình saga của phiên bản gốc dùng multinomial loss, L2 mặc định; C điều khiển nghịch độ mạnh regularization.
Nó phù hợp để kiểm giả thuyết các indicator có thể kết hợp bằng trọng số cộng, dùng sparse và không giả định feature độc lập.
Một tác động triệu chứng phụ thuộc tổ hợp phức tạp chưa chắc được biểu diễn đầy đủ bằng ranh giới tuyến tính.
[LogisticRegression1.6](https://scikit-learn.org/1.6/modules/generated/sklearn.linear_model.LogisticRegression.html),
[cơ sở logistic](https://scikit-learn.org/1.6/modules/linear_model.html#logistic-regression).

Trong bảng đã kiểm, Macro F1 của LR cao nhất, nhưng27 lớp không bao giờ được gọi và28 lớp F1=0:
có ít nhất một lớp được gọi mà không có true positive. Weighted F1 cao hơn Macro F1 nên vẫn phải quan tâm lớp hiếm.
Inference không tìm lại toàn train và checkpoint nhỏ, phù hợp làm mốc triển khai nghiên cứu có thể giải thích.
Các trọng số chỉ mô tả quan hệ trong CSV; chúng không là quan hệ nhân quả hay trọng số nguy cơ y khoa.
Softmax cho phép sắp Top3 theo class order đã khóa nhưng chưa chứng minh calibration hoặc xác suất mắc bệnh.

#### LinearSVC: đối chứng tuyến tính theo margin

LinearSVC học các bộ phân biệt one-vs-rest, tối ưu margin với squared-hinge loss và L2 mặc định trong phiên bản gốc.
Chọn nó để so tác động hàm mất mát với LR trên cùng sparse features; đây không phải kernel SVC và không tạo kernel matrix toàn cục.
Cũng là tuyến tính nên không tự khắc phục mọi tương tác hoặc thiếu dữ liệu; C/max_iter/tol và khả năng hội tụ cần ghi rõ.
[LinearSVC1.6](https://scikit-learn.org/1.6/modules/generated/sklearn.svm.LinearSVC.html).

SVC có Macro Recall cao hơn LR, dự đoán564 lớp so560 và F1=0 ở24 lớp so28,
nhưng Macro Precision thấp hơn và Macro F1 thấp hơn. Không thể kết luận một model tốt hơn ở mọi bệnh chỉ từ tổng kết này.
Predict toàn validation nhanh hơn LR trong lần ghi, song chênh nhỏ không phải latency guarantee.
Decision score không phải predict_proba; giao diện cần Top3 xác suất không được lấy softmax margin để lấp chỗ trống.
Không fit calibrator hoặc đổi preprocessing ở phân tích này.

#### Random Forest: đối chứng phi tuyến có giới hạn tài nguyên

Forest ghép nhiều cây học từ bootstrap samples và feature subsets; mỗi cây chia theo feature rồi tổng hợp phân bố lớp.
Nó kiểm giả thuyết tương tác/ràng buộc phi tuyến trên indicator, không đòi Gaussian hoặc độc lập có điều kiện.
Giới hạn độ sâu, số lá và số cây là lựa chọn kiểm soát tài nguyên; bagging không bảo đảm các cây độc lập hoặc giải quyết lớp hiếm.
[RandomForestClassifier1.6](https://scikit-learn.org/1.6/modules/generated/sklearn.ensemble.RandomForestClassifier.html).

Baseline chỉ gọi430 lớp,157 lớp F1=0; Macro Recall thấp và file nén lớn nhất trong năm model.
Fit nhanh hơn LR/SVC ở lần ghi nhưng việc fit nhanh không bù cho coverage nếu mục tiêu chính là Macro F1.
Giả thuyết cần giữ riêng: max_leaf_nodes512 cùng587 lớp và phân bố lệch có thể hạn chế chia tách hữu ích;
ensemble nhiều cây vẫn có thể biểu diễn nhiều nhãn hơn một cây nên không suy từ512 lá rằng forest không thể gọi đủ587 lớp.
Chưa có ablation để quy nguyên nhân điểm thấp cho depth/leaf cap, imbalance hoặc bản thân thuật toán.

#### KNN: tham chiếu hình học của vector nhị phân

KNN giữ dữ liệu train, tìm k láng giềng gần và bỏ phiếu theo inverse-distance weights.
Trên indicator0/1, Manhattan đếm vị trí khác nhau; weights=distance là trọng số **láng giềng**, không phải trọng số triệu chứng.
Nó được chọn để kiểm độ hữu ích của tính tương tự cục bộ mà không ép ranh giới tuyến tính.
Trong nhiều chiều, feature thiếu/ít liên quan và vector xung đột nhãn có thể làm khoảng cách khó phân biệt.
[Nearest neighbors1.6](https://scikit-learn.org/1.6/modules/neighbors.html).

Fit ngắn chủ yếu phản ánh lazy learning. Brute-force predict toàn validation mất294,224s,
trong khi LR khoảng2,157s; chênh này là cost theo batch trong protocol đã ghi, không là300 giây cho một câu hỏi.
Coverage560 bằng LR nhưng F1=0 ở34 lớp; có7 lớp được gọi mà không true positive.
Macro F1 cao hơn NB trong khi Weighted F1 thấp hơn NB, thể hiện đánh đổi giữa tổng kết cân lớp và cân theo support.
KNN còn hữu ích làm thành viên nghiên cứu nếu nó sửa đúng lỗi của model tuyến tính đủ nhiều để bù chi phí;
không được suy điều đó chỉ từ việc nó là một họ học khác.

#### BernoulliNB: tham chiếu xác suất sinh cho indicator

Mô hình ước lượng P(x_j=1|y=k) và class prior, rồi kết hợp các likelihood feature với giả định độc lập có điều kiện.
Bernoulli dùng cả x_j=1 lẫn x_j=0, khác mô hình multinomial về cơ chế sinh sự kiện; alpha làm trơn thống kê lớp ít mẫu.
Đây là mốc đơn giản phù hợp miền số học nhị phân, không là khẳng định triệu chứng thực độc lập.
[BernoulliNB1.6](https://scikit-learn.org/1.6/modules/generated/sklearn.naive_bayes.BernoulliNB.html),
[giả định Naive Bayes](https://scikit-learn.org/stable/modules/naive_bayes.html#bernoulli-naive-bayes).

Checkpoint nhỏ nhất nhưng Macro F1 thấp và chỉ gọi444 lớp; Accuracy khá cao có thể che143 lớp không được gọi.
Không kết luận sai số là do duy nhất giả định độc lập: chưa có phép kiểm nguyên nhân đó.
Điểm quan trọng khi dùng cho hội thoại:0 nghĩa là chưa ghi nhận hiện diện, không nhất thiết xác nhận vắng mặt.
Bernoulli likelihood vẫn học từ pattern0 trong dataset nên có nguy cơ lệch khi mức độ kể triệu chứng thay đổi.
Alpha không khắc phục semantic shift này; probability hợp lệ cũng không chứng minh calibration.

### Timing một mẫu sau load: bằng chứng riêng

Nguồn: packet structured-inference-v1, checkpoint **baseline** tương ứng;7 lần trên cùng một mẫu sau warm-up.
Bảng ghi load có kiểm integrity, warm-up một lần, median[min;max] của predict và predict_proba, đơn vị ms ở ba cột sau.
Không trộn CPU/RAM của lần train vào lần inference này vì packet timing chỉ ghi phiên bản thư viện, không đầy đủ hardware.

| Model | Load kiểm chứng (s) | Warm-up (ms) | Predict median[min;max] (ms) | Proba median[min;max] (ms) |
|---|---:|---:|---|---|
| Logistic Regression | 0.0418 | 33.915 | 13.789 [13.465; 13.914] | 14.088 [14.001; 25.246] |
| LinearSVC | 0.0616 | 18.002 | 13.245 [13.153; 13.291] | Không có predict_proba |
| Random Forest | 1.6846 | 112.703 | 50.233 [49.326; 51.373] | 50.587 [49.459; 61.401] |
| KNN | 0.0486 | 72.718 | 21.716 [21.428; 27.205] | 39.286 [22.974; 40.086] |
| BernoulliNB | 0.0365 | 79.090 | 35.488 [33.730; 38.602] | 34.801 [34.208; 36.171] |

Một mẫu/7 lần không đủ p95/p99, concurrency, cold-start Drive hoặc SLA API; không suy latency của k7/C2 tuned từ k5/C1 baseline.
KNN chậm hơn LR ở phép đo này nhưng tỷ lệ khác rất xa tỷ lệ đo toàn validation: kích thước batch,
chi phí cố định và cách thực thi khiến không thể chia thời gian toàn tập để cam kết latency từng request.
Không có probability của SVC. Top3 của bốn model có predict_proba phải hiểu là score theo dataset labels;
tie/score0 cần policy hiển thị và quality gate, không phải ba chẩn đoán đã xác thực.


### Phân tích tuning theo từng họ mô hình

Search space được chốt trước chạy; candidate0 của cả5 họ trùng parameters baseline trong configs/phase3.json.
Random seed/worker được helper dùng chung bổ sung, không thay thuật toán hoặc refit checkpoint baseline gốc.
Mọi candidate dùng cùng train-only StratifiedGroupKFold3, shuffle=True/seed42,
group theo vector triệu chứng; VarianceThreshold(0) được fit trong train của từng fold, không trước CV.
Mean Macro F1 trên đủ587 class IDs, zero_division=0 chọn cấu hình; exact tie chọn candidate đứng trước.
Khóa cả5 cấu hình trước khi fit selected trên toàn train và so validation.
[Source tuning](../../../src/models/tuning.py),
[SGKF1.6](https://scikit-learn.org/1.6/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html).

| Họ | Space; giá trị đầu là baseline | Lý do giới hạn |
|---|---|---|
| LR | C=1,0.5,2 | So điều chuẩn mạnh/yếu hơn, giữ saga/max_iter/tol |
| LinearSVC | C=1,0.5,2 | So margin–loss trade-off trên cùng folds |
| RF | max_depth=24,16,32 | So capacity qua depth, giữ100 cây/512 lá/min_leaf2; leaf cap vẫn có thể chi phối |
| KNN | k=5,3,7 | So mức cục bộ/làm trơn, giữ Manhattan/distance/brute |
| BernoulliNB | alpha=1,0.5,2 | So smoothing; không thay class prior hoặc ý nghĩa0 |

C nhỏ hơn tăng điều chuẩn ở LR/SVC; k nhỏ có thể nhạy nhiễu, k lớn có thể làm loãng lớp hiếm.
Depth/alpha có cơ chế tác động khác; cấu hình thắng không đủ chứng minh quan hệ nhân quả hoặc độ tối ưu toàn cục.

**Fold thực của run Colab:** audit kiểm cv_assignments.npz, row/group alignment, digest và zero group overlap;
tái tạo đúng assignment bằng seed42 trong môi trường gốc PASS. Các số local sklearn1.8 trong phần lịch sử không áp cho run này.

| Fold | Train rows /groups | Holdout rows /groups | Train classes | Holdout classes | Lớp thiếu ở holdout |
|---|---|---|---|---|---|
| 0 | 87406 /78140 | 43842 /39071 | 587 | 586 | colorectal cancer |
| 1 | 87496 /78138 | 43752 /39073 | 587 | 586 | idiopathic infrequent menstruation |
| 2 | 87594 /78144 | 43654 /39067 | 587 | 587 | Không |

Cả3 train fold đủ587 lớp. Fold0 vắng ID112 colorectal cancer, fold1 vắng ID275 idiopathic infrequent menstruation ở holdout;
vẫn tính F1=0 của lớp vắng trong mẫu số587. So candidate dùng cùng folds vì vậy vẫn nhất quán;
không so điểm này với Macro F1 tự bỏ nhãn vắng. Không resplit để ép mỗi phía đủ587.

**Cấu hình được chọn và CV đã kiểm arithmetic** (std dân số, ddof=0; không phải CI):

| Model | Candidate /thay đổi so baseline | Fold0 | Fold1 | Fold2 | Mean | Std |
|---|---|---|---|---|---|---|
| Logistic Regression | 2; C=2 | 0.80014986 | 0.80147154 | 0.80009154 | 0.80057098 | 0.00063724 |
| LinearSVC | 2; C=2 | 0.79090861 | 0.79368239 | 0.79524029 | 0.79327710 | 0.00179147 |
| Random Forest | 2; max_depth=32 | 0.52125152 | 0.51095962 | 0.52541920 | 0.51921011 | 0.00607702 |
| KNN | 2; n_neighbors=7 | 0.72344929 | 0.72783679 | 0.72643659 | 0.72590755 | 0.00182984 |
| BernoulliNB | 1; alpha=0.5 | 0.61574582 | 0.62667237 | 0.62167189 | 0.62136336 | 0.00446608 |

Parameters khác giữ như baseline: LR saga/max_iter200/tol0.001; SVC dual=auto/max_iter3000/tol0.001;
RF100/sqrt/512lá/min_leaf2; KNN distance/brute/manhattan; NB binarize=None.
Mean/std được tính lại từ3 scores khớp packet. Scores đã được checksum/selection audit;
**NOT VERIFIED việc tính lại từng CV score từ predictions** vì fold models/predictions không persist.

**Đủ15 candidate,45 fold attempts completed**, mỗi candidate đúng3 attempts; không failed/interrupted attempts trong state.
Supplement đã cung cấp scores/warnings của **tất cả** candidate, cùng manifest SHA với audit chính.
Các giá trị sau là score đã lưu và được kiểm checksum/arithmetic, không phải CV model predictions được tái sinh.

| Model | Candidate /giá trị | CV fold0 /1 /2 | Mean /Std(ddof0) | Elapsed3fold(s) | D /R /C warnings |
|---|---|---|---|---|---|
| Logistic Regression | 0; C=1 | 0.78322949 /0.78895327 /0.77889594 | 0.78369290 /0.00411894 | 223.233 | 12 /3 /0 |
| Logistic Regression | 1; C=0.5 | 0.75086250 /0.74720706 /0.73750035 | 0.74518997 /0.00563845 | 171.231 | 9 /3 /0 |
| Logistic Regression | 2; C=2 (chọn) | 0.80014986 /0.80147154 /0.80009154 | 0.80057098 /0.00063724 | 290.355 | 15 /3 /0 |
| LinearSVC | 0; C=1 | 0.78929718 /0.79249567 /0.79103934 | 0.79094406 /0.00130751 | 166.520 | 9 /3 /0 |
| LinearSVC | 1; C=0.5 | 0.78346851 /0.78607858 /0.78480753 | 0.78478487 /0.00106568 | 160.449 | 9 /3 /0 |
| LinearSVC | 2; C=2 (chọn) | 0.79090861 /0.79368239 /0.79524029 | 0.79327710 /0.00179147 | 172.329 | 9 /3 /0 |
| Random Forest | 0; max_depth=24 | 0.47423587 /0.47788719 /0.48603266 | 0.47938524 /0.00493113 | 135.287 | 16 /3 /0 |
| Random Forest | 1; max_depth=16 | 0.37951797 /0.38518530 /0.37688269 | 0.38052865 /0.00346405 | 120.166 | 14 /3 /0 |
| Random Forest | 2; max_depth=32 (chọn) | 0.52125152 /0.51095962 /0.52541920 | 0.51921011 /0.00607702 | 129.970 | 15 /3 /0 |
| KNN | 0; n_neighbors=5 | 0.71201238 /0.71532289 /0.71850618 | 0.71528048 /0.00265125 | 932.370 | 96 /3 /0 |
| KNN | 1; n_neighbors=3 | 0.69289064 /0.69398770 /0.69835215 | 0.69507683 /0.00235891 | 931.225 | 96 /3 /0 |
| KNN | 2; n_neighbors=7 (chọn) | 0.72344929 /0.72783679 /0.72643659 | 0.72590755 /0.00182984 | 932.899 | 97 /3 /0 |
| BernoulliNB | 0; alpha=1 | 0.53652097 /0.54196813 /0.53916291 | 0.53921733 /0.00222413 | 26.751 | 6 /0 /0 |
| BernoulliNB | 1; alpha=0.5 (chọn) | 0.61574582 /0.62667237 /0.62167189 | 0.62136336 /0.00446608 | 26.732 | 6 /0 /0 |
| BernoulliNB | 2; alpha=2 | 0.43291594 /0.43616898 /0.43523101 | 0.43477198 /0.00136714 | 25.435 | 6 /0 /0 |

D/R/C là DeprecationWarning/ResourceWarning/ConvergenceWarning được ghi trong attempts; completed3/3 cho từng hàng.
Cấu hình baseline candidate0 được đưa vào thật; các tham số không phải cột đang search giữ nguyên.
Cả5 cấu hình thắng đều cao hơn candidate0 trong từng fold, không chỉ mean.
Gain CV mean so candidate0: LR+0.01687808; SVC+0.00233304; RF+0.03982487; KNN+0.01062707; NB+0.08214603.
Đó là so sánh within-fold của space đã chốt, không là dự báo mức tăng validation.
LR/KNN selected có std thấp hơn candidate0; SVC/RF/NB selected có std cao hơn:
tuning tăng mean không mặc nhiên giảm biến thiên. Chỉ3 folds/seed42, chưa có CI hoặc multi-seed stability.

**Validation baseline → tuned:** cùng28.120 hàng,375 input features,587 nhãn; metrics tuned được Colab tính lại từ saved predictions.
CV chọn cấu hình; validation so sánh kết quả, không mở rộng space sau khi nhìn điểm.

| Model | Accuracy | Macro P | Macro R | Macro F1 | Weighted F1 | Coverage /F1=0 |
|---|---|---|---|---|---|---|
| Logistic Regression | 0.83766003 | 0.82386664 | 0.79248487 | 0.79315438 | 0.83843972 | 566 /23 |
| LinearSVC | 0.83111664 | 0.81154666 | 0.78822428 | 0.78636758 | 0.83065113 | 566 /23 |
| Random Forest | 0.74206970 | 0.66177514 | 0.46754094 | 0.51090813 | 0.72988291 | 434 /153 |
| KNN | 0.79032717 | 0.79283927 | 0.74575164 | 0.74567902 | 0.79329712 | 562 /30 |
| BernoulliNB | 0.82727596 | 0.73923081 | 0.64699541 | 0.67213832 | 0.82279396 | 489 /99 |

| Model | Baseline F1 → tuned F1 | Delta F1 tuyệt đối | Đánh đổi quan sát |
|---|---|---|---|
| LR | 0.78780814 →0.79315438 | +0.00534624 | Accuracy tăng0.00056899; coverage560→566; F1zero28→23; Macro Precision giảm |
| LinearSVC | 0.78422186 →0.78636758 | +0.00214572 | Accuracy tăng0.00032006; coverage564→566; F1zero24→23 |
| RF | 0.49199733 →0.51090813 | +0.01891080 | Accuracy tăng0.04153627; coverage430→434 nhưng153 lớp vẫn F1=0 |
| KNN | 0.73103438 →0.74567902 | +0.01464464 | Accuracy tăng0.00718350; coverage560→562; F1zero34→30 |
| BernoulliNB | 0.59934053 →0.67213832 | +0.07279779 | Coverage444→489; F1zero144→99; vẫn kém3 model tuyến tính/láng giềng về Macro F1 |

Cả5 tăng Macro F1 validation với selection CV hiện tại. NB có mức tăng lớn nhất trong space đã thử,
không trở thành model tốt nhất và không chứng minh giả định độc lập đúng hơn.
LR/SVC chọn C2: giảm điều chuẩn phù hợp điểm của run này; chưa chứng minh C lớn hơn nữa sẽ cải thiện.
RF tăng depth nhưng còn leaf cap; việc tăng điểm không cho biết loại giới hạn nào là nguyên nhân chính.
KNN chọn k7 trong khi fit chỉ giữ dữ liệu, nên nâng điểm không xóa chi phí brute-force.
Std fold LR nhỏ hơn RF trong3 fold này, không đủ kết luận LR ổn định qua mọi seed hoặc miền triệu chứng tiếng Việt.

**Chi phí selected refit/validation đã lưu và integrity:**

| Model | Fit (s) | Predict28.120 (s) | Pipeline bytes /MiB | Deprecation /Resource /Convergence | Reload |
|---|---|---|---|---|---|
| Logistic Regression | 129.683 | 2.115 | 1438563 /1.372 | 6 /1 /0 | PASS |
| LinearSVC | 80.536 | 1.852 | 1463321 /1.396 | 4 /1 /0 | PASS |
| Random Forest | 17.358 | 20.876 | 17388724 /16.583 | 3 /0 /0 | PASS |
| KNN | 1.604 | 296.826 | 652535 /0.622 | 31 /1 /0 | PASS |
| BernoulliNB | 2.302 | 3.762 | 102840 /0.098 | 2 /0 /0 | PASS |

Reload trên Colab đúng versions/source,375 feature order,587 class order, parameters và mask variance tính từ train PASS ở cả5.
Không có predict/fit trong audit. Mỗi pipeline có SHA riêng trong packet; checkpoint baseline giữ nguyên.
Search ghi415 DeprecationWarning và36 ResourceWarning,0 ConvergenceWarning,0 failed/0 interrupted attempts.
Không suy warning về hội tụ từ tổng warning count. ResourceWarning cần xem message/handle cleanup, không tự đồng nghĩa OOM hoặc metrics sai.
Per-candidate warning counts đã có trong supplement và tổng khớp415/36; peak RSS tuned **NOT VERIFIED**, không gán RSS baseline sang selected.
No ConvergenceWarning là không có cảnh báo được ghi, không là chứng minh nghiệm tối ưu hay lịch sử kernel không phát sinh warning ngoài log.

Tổng elapsed45 CV attempts 4444.951s;
đây là tổng thời gian được lưu của attempts, không wall-clock toàn notebook, không gồm đầy đủ interruption/idle/deployment.
KNN chiếm phần lớn search/predict cost; không suy batch1 latency từ thời gian này.
Budget6 giờ được kiểm giữa folds, không hard timeout.
Resume helpers/checksum/namespace được audit; state hiện tại không ghi attempt lặp/dở, nhưng không chứng minh historical exactly-once execution.
**REVIEW:** split_warnings nằm trong experiment digest, warning noise có thể đổi ID khi resume; chưa có bằng chứng run này gặp lỗi.
Giữ nguyên source đã pin, không bỏ integrity validation hoặc thay namespace để sửa tài liệu.

### Ensemble baseline: kết quả và cơ chế giải thích

Các tổ hợp đều uniform weights. Hard gồm LR+SVC+KNN, LR+SVC+NB, LR+SVC+RF;
soft gồm LR+NB+RF và LR+KNN+NB. Ở giai đoạn baseline, từng thành viên mang đúng cấu hình ở bảng baseline phía trên.
Hard tie ưu tiên LR→SVC→KNN→NB→RF trong các thành viên đang xét; soft exact mean tie so LR probability rồi nhãn tiếng Anh Unicode.
Không VotingClassifier.fit, calibrator hoặc tối ưu weights trên validation.

Bảng này lấy từ packet Phase4 đã kiểm, cùng28.120 hàng và587 nhãn:

| Tổ hợp baseline | Accuracy | Macro F1 | Weighted F1 | Coverage | F1=0 | Sửa đúng lỗi LR | Làm sai LR đúng | Tie rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LR đơn | 0.83709104 | 0.78780814 | 0.83667539 | 560 | 28 | — | — | 0 |
| Hard LR+SVC+KNN | 0.83645092 | 0.78733399 | 0.83597865 | 559 | 29 | 152 | 170 | 1000 |
| Hard LR+SVC+NB | 0.83613087 | 0.78478926 | 0.83534646 | 558 | 30 | 160 | 187 | 659 |
| Hard LR+SVC+RF | 0.83545519 | 0.78405303 | 0.83477575 | 558 | 30 | 153 | 199 | 1263 |
| Soft LR+NB+RF | 0.82542674 | 0.72469398 | 0.82110196 | 532 | 56 | 559 | 887 | 0 |
| Soft LR+KNN+NB | 0.82699147 | 0.76324258 | 0.82700045 | 548 | 39 | 917 | 1201 | 0 |

Hard tốt nhất sửa152 hàng LR sai nhưng làm sai170 hàng LR đúng: net−18 hàng, khớp chênh Accuracy trên cùng28.120 mẫu.
Macro F1 cũng giảm và lớp F1=0 tăng28→29. Đây là bằng chứng trực tiếp baseline ensemble chưa vượt LR,
không phải kết luận Voting nói chung không hiệu quả. Hai hard khác và cả hai soft cũng mất nhiều hàng đúng hơn số sửa được.
Số net correct không tự xác định Macro F1: mỗi lớp còn phụ thuộc cả FP/FN và cách lỗi phân bố.

Với3 hard model và tie ưu tiên LR, thay nhãn LR chỉ xảy ra khi hai thành viên kia đồng ý nhãn khác LR.
KNN có nhãn đúng khi cả LR/SVC sai vẫn không cứu được: hai phiếu sai trùng nhau thắng hoặc ba nhãn khác nhau trả LR.
Do đó “KNN khác thuật toán” không đủ; cần **hai thành viên cùng đúng trên chính lỗi LR** và không cùng chọn nhãn sai khi LR đúng.
Ba nhãn hòa chọn LR ở1.000/659/1.263 hàng của ba hard tổ hợp. Quy tắc này tăng ảnh hưởng LR ở tie,
nhưng không được diễn giải thành weights đã tối ưu hoặc chứng minh ưu tiên LR là tối ưu.

Disagreement = tỷ lệ nhãn hai model khác nhau; joint error = tỷ lệ cả hai cùng sai, không yêu cầu chọn cùng nhãn sai.
Các tỷ lệ dưới tính trên toàn validation, không phải conditional probability:

| Cặp baseline | Disagreement | Joint error | A sai/B đúng | A đúng/B sai |
|---|---:|---:|---:|---:|
| LR / SVC | 7.6387% | 14.4488% | 518 | 695 |
| LR / KNN | 20.1209% | 12.4289% | 1086 | 2603 |
| SVC / KNN | 21.0242% | 12.5320% | 1234 | 2574 |

LR/SVC cùng sai4.063 hàng; disagreement7,6387% không có nghĩa số hàng này có một model đúng.
Rescue pairwise không bảo đảm một majority vote sửa được những hàng đó, vì còn cần thành viên thứ ba và tie policy.
Những đối chiếu này dựa trên ma trận aggregate đã audit, chưa phải causal explanation về nguồn gốc lỗi.

Soft Voting dùng predict_proba thật, đúng587 class order/hàng, finite, thuộc[0,1], tổng hàng≈1 và argmax khớp hard predictions.
Những điều kiện số học ấy không chứng minh probability được calibration.
Giả thuyết rằng RF/NB kém calibration hoặc phân bố quá tập trung kéo lệch mean là hợp lý để nghiên cứu,
nhưng **chưa có reliability analysis để xác nhận đó là nguyên nhân** của soft F1 thấp.
Không tạo pseudo-probability từ SVC margin, hard labels hoặc tần suất phiếu.
[Calibration và giới hạn diễn giải](https://scikit-learn.org/stable/modules/calibration.html).

### Ensemble tuned: kết quả đã kiểm và giới hạn giải thích

Cùng3 hard/2 soft, uniform weights và tie policy như baseline. Thành viên mang **selected parameters đã audit**:
LR C2; SVC C2; KNN k7; RF depth32; NB alpha0.5, các tham số khác giữ như baseline.
Run `tuned-ensemble-20261029T041701354242Z-6c84dbfe` liên kết đúng tuning manifest/identity/schema/mapping.
Colab audit xác minh saved validation metrics của cả5 tổ hợp; hard predictions tái dựng từ saved member predictions
và tie policy, không gọi model.predict. Supplement xác minh và tóm tắt predictions/trials từ cùng manifests.

| Phương án tuned | Accuracy | Macro F1 | Weighted F1 | Coverage | F1=0 | Bytes tổng | Saved predict sum(s) |
|---|---|---|---|---|---|---|---|
| LR đơn | 0.83766003 | 0.79315438 | 0.83843972 | 566 | 23 | 1438563 | 2.115 |
| hard_lr_svc_knn | 0.83691323 | 0.79651707 | 0.83768176 | 567 | 21 | 3554419 | 300.793 |
| hard_lr_svc_nb | 0.83709104 | 0.78725551 | 0.83755198 | 564 | 25 | 3004724 | 7.729 |
| hard_lr_svc_rf | 0.83573969 | 0.78769267 | 0.83626975 | 564 | 25 | 20290608 | 24.844 |
| soft_lr_knn_nb | 0.82972973 | 0.77043797 | 0.82975403 | 550 | 38 | 2193938 | 302.703 |
| soft_lr_nb_rf | 0.83268137 | 0.76487052 | 0.83084513 | 548 | 41 | 18930127 | 26.753 |

Trong11 phương án baseline LR +5 selected +5 ensemble, **Hard LR+SVC+KNN tuned đứng đầu Macro F1**0.79651707;
LR tuned đứng đầu Accuracy 0.83766003 và Weighted F1 = 0.83843972. Những tổ hợp khác đều thấp hơn LR tuned về Macro F1.
Hard tốt nhất có Macro Precision0.82271265, Macro Recall0.79813366.
So LR tuned: F1 tăng0.00336269 (0.336269 điểm phần trăm), recall tăng0.00564878, precision giảm0.00115399;
Accuracy giảm0.00074680, Weighted F1 giảm0.00075796, coverage566→567, F1zero23→21.
So LR baseline: F1 tăng0.00870893 nhưng Accuracy giảm0.00017781 (net−5 hàng đúng).
Macro F1 và Accuracy/Weighted F1 có cách cân lỗi khác nhau, nên đánh đổi này không mâu thuẫn.

**Correct/wrong transitions thật**, reference là **LR tuned**, cùng28.120 row_0based/y_true/group_id:

| Tổ hợp tuned | LR sai→ensemble đúng | LR đúng→ensemble sai | Net correct | Tie rows |
|---|---|---|---|---|
| hard_lr_svc_knn | 173 | 194 | -21 | 963 |
| hard_lr_svc_nb | 185 | 201 | -16 | 679 |
| hard_lr_svc_rf | 204 | 258 | -54 | 1245 |
| soft_lr_knn_nb | 743 | 966 | -223 | 0 |
| soft_lr_nb_rf | 464 | 604 | -140 | 0 |

Hard LR+SVC+KNN sửa173 hàng LR tuned sai nhưng làm sai194 hàng LR tuned đúng, net−21.
Cả hai đúng23.361, cả hai sai4.392; tổng28.120. Điều này khớp Accuracy delta được tính độc lập từ metrics.
So baseline hard:152 rescue/170 loss/net−18 theo **LR baseline**; tuned:173/194/net−21 theo **LR tuned**.
Hai reference khác nhau; không coi hiệu21 rescue là chính21 hàng được tuning cứu hoặc gán cải thiện F1 chỉ cho số hàng đúng.

Hard tie counts963/679/1.245 thay đổi so baseline1.000/659/1.263 không đồng nhất;
ở3 nhãn khác nhau policy trả LR, không tự suy đây là tie rule tối ưu.
Với LR+SVC+KNN, hard khác LR khi SVC và KNN cùng chọn một nhãn khác LR;173 rescue là các hàng cả hai đối tác cùng đúng trên lỗi LR,
194 loss là các hàng hai đối tác đồng ý nhãn sai trong khi LR đúng. Đây là hệ quả của vote/tie đã tái dựng,
không phải lý thuyết “KNN khác họ nên tự cứu được”.

**Disagreement/joint error tuned:** tỷ lệ trên toàn validation; số A sai/B đúng có hướng,
joint error không yêu cầu hai nhãn sai trùng nhau.

| Cặp tuned(A/B) | Disagreement | Joint error | Cùng sai(rows) | A sai/B đúng | A đúng/B sai |
|---|---|---|---|---|---|
| Logistic Regression /LinearSVC | 8.2255% | 14.2176% | 3998 | 567 | 751 |
| Logistic Regression /KNN | 18.5526% | 12.5284% | 3523 | 1042 | 2373 |
| LinearSVC /KNN | 19.7973% | 12.5533% | 3530 | 1219 | 2366 |

LR/SVC disagreement tăng7.6387%→8.2255%, joint error giảm14.4488%→14.2176% (4.063→3.998 hàng).
LR/KNN disagreement lại giảm20.1209%→18.5526%, joint error tăng12.4289%→12.5284% (3.495→3.523).
SVC/KNN joint error cũng tăng nhẹ12.5320%→12.5533% (3.524→3.530).
Vì vậy **không có bằng chứng lỗi mọi cặp đều độc lập/bổ sung hơn sau tuning**.
Cấu hình mới tạo tập predictions khác và vote có kết quả khác đã được kiểm;
nguyên nhân chung có thể liên quan cách phân bố FP/FN theo lớp, nhưng không khẳng định cơ chế nhân quả chỉ từ các aggregate này.

**Per-class LR tuned → hard tốt nhất:** trong587 lớp,115 lớp tăng F1,128 giảm và344 không đổi.
Có2 lớp từ F1=0→positive,0 lớp positive→0,21 lớp vẫn0. Nhiều lớp giảm hơn tăng nhưng tổng biên độ cải thiện lớn hơn:
Macro F1 là mean của F1 từng lớp, không tỷ lệ số lớp thắng.

| Support validation | Số lớp | F1 tăng | F1 giảm | Không đổi | Mean F1: LR→hard | Đóng góp delta Macro F1(pp) |
|---|---|---|---|---|---|---|
| 1 | 33 | 2 | 1 | 30 | 0.545455→0.565657 | 0.113572 |
| 2-5 | 99 | 5 | 2 | 92 | 0.725127→0.737099 | 0.201902 |
| 6-20 | 139 | 15 | 17 | 107 | 0.802356→0.804376 | 0.047825 |
| >20 | 316 | 93 | 108 | 115 | 0.836286→0.835784 | -0.027030 |

Đóng góp mỗi bin = tổng(F1_hard−F1_LR) trong bin/587, đổi sang điểm phần trăm; tổng đúng+0.336269pp.
Bốn bin rời nhau theo support đã khóa, không search bin để tối ưu metric.
Nhóm support≤5 có132 lớp nhưng chỉ363/28.120 hàng; đóng góp+0.00315474 Macro F1,
khoảng **93.82% của net gain** trên validation này. Nhóm>20 có tổng đóng góp âm.
Do đó có bằng chứng **gain Macro F1 quan sát tập trung ở lớp support thấp**,
đồng thời gain có thể nhạy với rất ít mẫu; chưa là kết luận ổn định trên bệnh hiếm ngoài dataset.

Hai lớp zero→positive đều chỉ1 mẫu validation: ID289 injury to the abdomen, F1: 0→1/3;
ID434 polycythemia vera, F1: 0→2/3. Tên đối chiếu đúng label mapping đã khóa
(mapping SHA `d2ef711e5e04062e8b5b949ce434b1383e1ca2fef6eb31a0865acb2f470ab5b5`),
không fuzzy-map hoặc sửa nhãn. Một đúng/sai hoặc FP từ lớp khác có thể thay mạnh F1 khi support1.
Không dùng115/128 hay hai lớp được cứu để chứng minh ý nghĩa thống kê, calibration hoặc độ tin cậy y khoa.

![Phân tích lỗi ghép cặp và đóng góp Macro F1 theo support](../../../../disease-prediction-ml-data/reports/figures/model_selection_tuned_error_analysis.png)

Hình duy nhất bổ sung dùng supplement đã kiểm SHA: panelA số hàng ghép cặp, panelB đóng góp cân lớp của bốn bin.
Đây là phân tích mô tả validation, không CI, causal attribution hoặc benchmark latency.

**Soft voting:** metrics và checksum saved labels PASS. Probability sources ghi predict_proba thật,
class order/finite/range/row sums/argmax checks; probability memmap ephemeral không persist,
nên **NOT VERIFIED phép cộng soft probability được kiểm lại độc lập trong audit mới**.
Không rerun predict_proba để lấp phần thiếu; chưa có calibration/reliability analysis.
Soft tuned tốt hơn chính tổ hợp baseline nhưng vẫn thấp hơn LR tuned;
không gán nguyên nhân duy nhất cho calibration hoặc một member yếu.

### So sánh đa tiêu chí cho API/chatbot

> Bảng dưới giữ snapshot trước ML_GAPS; các ô tuned latency/RAM/Top3 “NOT VERIFIED” đã được bổ sung bằng
> [benchmark thật ở cuối](#bằng-chứng-bổ-sung-ml-gaps-và-đề-xuất-để-nhóm-duyệt).
> Không gán timing baseline sang tuned hoặc xóa lịch sử thiếu bằng chứng.

**MODEL SELECTION PENDING.** Integrity/validation ranking đã được kiểm bằng packet Colab;
lựa chọn sản phẩm còn cần uncertainty, deployment measurements và output policy.
Bảng xem đủ11 phương án ở phần trên; ba ứng viên dưới đại diện default đang có, single-model tuned tốt nhất và best-Macro-F1 ensemble.

| Tiêu chí | LR baseline | LR tuned | Hard tuned LR+SVC+KNN |
|---|---|---|---|
| Macro F1 /Accuracy /Weighted F1 | 0.78780814 /0.83709104 /0.83667539 | 0.79315438 /0.83766003 /0.83843972 | 0.79651707 /0.83691323 /0.83768176 |
| Coverage /F1=0 | 560 /28 | 566 /23 | 567 /21 |
| File nén | 1438385 bytes (1.372 MiB) | 1438563 bytes (1.372 MiB) | 3554419 bytes (3.390 MiB) |
| Predict toàn validation đã lưu | 2.157s | 2.115s | 300.793s (tổng3member) — proxy |
| Latency triển khai | Baseline median predict13.789ms,1 mẫu/7 lần; chưa p95/concurrency | NOT VERIFIED cho checkpoint tuned; không gán timing baseline | NOT VERIFIED batch1/parallelism; không coi300.793s là latency một request |
| RAM | RSS validation371.05MiB là process stage baseline | NOT VERIFIED peak RAM deployment | NOT VERIFIED3 model cùng process; không cộng peaks riêng lẻ |
| Ổn định | Một split/seed; chưa group CI | Selected CV mean0.80057098/std0.00063724 trên3fold; chưa paired CI | Chưa group CI; không có CV ensemble score để so với CV LR |
| Top3 | predict_proba có thật; chưa calibration; qua quality gate | Reload PASS, cùng estimator có predict_proba; Top3 thực và calibration của tuned chưa kiểm lại | Hard vote không cung cấp posterior587-class; vote share không probability |
| Độ phức tạp API | Một pipeline/schema/mapping, default đang có | Một pipeline; cần migration/audit và benchmark trước nâng default | Ba checkpoint, class alignment/tie/resource management, contract Top3 cần duyệt |
| Vai trò | Mốc bảo toàn; không final winner | Ứng viên cân bằng đáng benchmark; không tự chọn thắng | Ứng viên best validation Macro F1; không tự chọn mặc định |

Hard có tổng compressed bytes gấp2.471 LR tuned;
saved full-validation predict sum gấp142.2
nhưng các timing có thể khác phiên và không gồm voting/Drive/concurrency.
Tỷ lệ này mô tả records đã lưu, **không là tỷ lệ latency request hoặc RAM**.
Chênh F1 nhỏ chưa được kiểm ý nghĩa thống kê, và đánh giá nhiều phương án trên cùng validation có selection bias.

Có thể không chọn hard tuned cho chatbot dù Macro F1 cao nhất vì:

1. **Output contract:** hard labels/votes không tự cho Top3 probability. Trả Top3 của LR kèm Top1 ensemble là policy khác,
   có thể mâu thuẫn và cần đánh giá riêng; không gọi LR probability là confidence của ensemble.
2. **Vận hành:** KNN cần train representations khi predict;3 pipeline tăng load/alignment/monitoring và điểm lỗi.
   Cần benchmark selected trên cùng máy, workload và batch1 trước quyết định khả năng đáp ứng.
3. **Mục tiêu đánh giá:** hard tăng Macro F1/recall nhưng Accuracy/Weighted F1 giảm so LR tuned.
   Gain cân lớp tập trung ở support≤5 nhưng chưa có group CI; không tự coi mọi lỗi được đánh đổi có giá trị như nhau cho hội thoại.
4. **Dữ liệu và end-to-end:** missing/denied/uncertain semantics, extraction tiếng Việt và abstention chưa được human review đầy đủ;
   validation CSV không xác thực y khoa hoặc sửa sai lệch LLM.
5. **Mức độ phức tạp:** file nén nhỏ không bảo đảm RAM thấp; cần output/gate và operational acceptance criteria được nhóm chốt trước benchmark.

Các lý do ấy **không mặc định LR tuned thắng**. Hard vẫn hợp lệ nếu lợi ích đủ ổn định và đáp ứng resource/output contract được duyệt.
LR tuned là single-model có kết quả cân bằng hơn trong run này; đó là ứng viên cần đánh giá, không một thay đổi default được cấp phép.
Giữ LR baseline hiện tại là bảo toàn; đề xuất nhóm duyệt phép kiểm còn thiếu trước chốt model cuối.

### Bất định, hình minh họa và điều kiện chốt lựa chọn

> Phần đề xuất dưới đây giữ lịch sử trước khi nhận ML_GAPS. Protocol sau đó đã chốt seed20261029/B2000 trước khi tính,
> và đã nhận kết quả thật tại mục kế tiếp; những câu “chưa chạy/để chốt còn cần benchmark” là trạng thái trước lần bổ sung đó.

Chưa chạy bootstrap hoặc kiểm định mới: paired prediction arrays ở Drive đã được auditor kiểm nhưng không được gửi về local trong packet. Phương pháp đề xuất cho phép kiểm chỉ đọc sau này:
resample **validation groups** có hoàn lại, giữ mọi row/label trong group, dùng cùng sample cho mọi candidate;
chốt seed/số lần trước tính, ví dụ2.000 replicate, labels luôn đủ587/zero_division0 và báo missing-class support mỗi replicate.
Phân tích paired delta Macro F1/Accuracy và CI theo group, không row-wise bootstrap coi các nhãn chung vector là độc lập.
Sự vắng lớp hiếm khi resample làm Macro F1 không trơn và thay đổi diễn giải; phải ghi giới hạn đó.
Không chạy tiếp search hay chọn weights từ CI. Validation đã dùng nhiều lần, nên CI này là mô tả có điều kiện,
không xóa selection bias/multiple comparisons hoặc thay final locked-test protocol được duyệt.

Tái sử dụng3 hình Phase3 đã checksum PASS (validation_performance, fit_prediction_time, difficult_classes)
và2 hình Phase4 (diversity/comparison) được tham chiếu trong [report Phase3](../../../reports/phase3_post_training_audit.md)
và [report Phase4](phase4_ensemble.md). Ảnh gốc trên Drive; không dựng lại từ notebook để giả thành artifact mới đã kiểm.
Không tạo lại Baseline vs Tuned chart: file gốc reports/tuning/tuning-v1-9c4dd013abbba14a/baseline_vs_tuned.png nằm trong26 file được tuning manifest checksum-verify trên Colab; chưa tải ảnh về local để kiểm trực quan.
Chỉ thêm [một hình hai panel](../../../../disease-prediction-ml-data/reports/figures/model_selection_tuned_error_analysis.png) từ supplement thật để giải thích net−21 correct rows nhưng Macro F1 tăng và gain theo support; không tạo thêm notebook hoặc biểu đồ trang trí.

Full candidate scores/warnings và transitions/diversity/per-class summaries nay đã đủ để hoàn thiện phân tích mô tả.
Để chốt model còn cần paired uncertainty nếu muốn khẳng định chênh nhỏ và benchmark cùng môi trường cho load/warm-up,
batch1 p50/p95/concurrency và measured RAM; policy Top3/probability/abstention được duyệt.
Không đặt một ngưỡng max-probability hoặc latency acceptance tùy ý rồi gọi nó đã được kiểm chứng.
Sau đó nhóm duyệt lựa chọn và kế hoạch final test; nhiệm vụ này không mở locked test, đổi default/checkpoint,
fit/tune/calibrate, gọi Gemini hoặc triển khai API/frontend.

### Bằng chứng bổ sung ML GAPS và đề xuất để nhóm duyệt

Ngày2026-10-29 nhận [packet Colab nguyên byte](../../../artifacts/metadata/final_ml_gaps/colab_evidence.json),SHA-256
`7c2ed8e6705347a850bb90e88cdea54067d0d12ec5553588ce03fbd0a99725ac`,36.429bytes.
Script [audit_final_ml_gaps.py](../../../scripts/audit_final_ml_gaps.py) SHA
`7c925d48e02dfab7b6951303c2c3e69f52d4143658ba1e1976a079b5b4141ce1` khớp source local;
hai manifest tuning4a10ddd5…/ensemble858893c4… giữ nguyên. Agent kiểm packet/protocol/arithmetic,không trực tiếp chạy kernel/Drive.

Protocol đã chốt trước tính: seed20261029,2000 replicate,lấy25.127 group có hoàn lại mỗi replicate,
giữ mọi row/label và multiplicity cùng nhau cho hai model;28.120 validation rows,labels0..586/zero_division0.
Không đổi model/grid/seed để tìm kết quả. [Chi tiết phương pháp và inventory](../planning/WORKSPACE_HANDOVER_PLAN.md#2-protocol-chốt-trước-khi-tính).

| Delta hard−LR tuned | Quan sát | Mean bootstrap | Percentile95% |
|---|---:|---:|---|
| Macro F1 | +0.00336269 | +0.00301573 | **[−0.00003807; +0.00622337]** |
| Accuracy | −0.00074680 | −0.00074050 | **[−0.00168360; +0.00021316]** |

Cảhai interval chứa0: chưa xác lập ưu thế ổn định của hard,không phải chứng minh tương đương hoặc không có khác biệt.
Fraction deltaF1>0=0.9735 chỉ mô tả replicate,không p-value/posterior/confidence97.35%.
Cả2000 replicate vắng lớp: min8/p05=13/median19/p95=25/max31;182 lớp vắng ít nhất1 lần.
F1 vẫn tính đủ587 nhãn. Missing-class frequencies theo từngID nằm trong packet;
rare-class discontinuity,group-iid assumption và repeated-validation selection bias làm CI chỉ có ý nghĩa mô tả có điều kiện.

Benchmark cùng64 group không chọn theo nhãn/lỗi,3 vòng×64=192 batch1 calls/operation sau3 warm-ups riêng.
Colab Linux,CPU Xeon2.20GHz/2logicalCPU/RAM12.671GiB,Python3.13.18/sklearn1.6.1/NumPy2.1.3/pandas2.2.3,
BLAS1/working_memory128MiB. Load không cold vì integrity đã đọc files trước; input/data resident cùng process.

| Condition | Verified load(s) | Top1p50/p95(ms) | Top3p50/p95(ms) | Sampled process peak(MiB) |
|---|---:|---|---|---:|
| LR tuned | 0.036802 | **13.102 /14.778** | 12.854 /15.073,proba+ranking thật | 393.105 |
| Hard tuned LR+SVC+KNN | 0.111631 | **48.705 /88.125** | UNAVAILABLE,không posterior từ hard votes | 393.535 |

Warm-ups,member loads,min/max và panelIDs đầy đủ trong packet/kế hoạch; không trộn timing baseline hoặc phiên khác.
RSS gồm kernel/data/allocator,0.5s sampling có thể lỡ peak; chênh RSS nhỏ không là RAM riêng của hard.
Fit guard profiler tạo overhead trên cảhai conditions. Fixed LR→hard order,caching và workload64 inputs lặp lại còn giới hạn;
không có HTTP/concurrency/cold-start/Gemini trong đo này,không SLA.
Top3 LR có scores thật,đúng class order/range/sum nhưng chưa calibration hoặc clinical probability.

**Đề xuất có bằng chứng:** trình nhóm ưu tiên LR tuned cho API nghiên cứu cần Top3 vì single pipeline,
Accuracy/Weighted F1 cao hơn hard trong run này,Top3 khả dụng và diagnostic batch1 nhanh hơn.
Hard vẫn có Macro F1 điểm cao nhất; không loại bỏ mọi trường hợp sử dụng hard hoặc khẳng định LR thắng về mọi metric.
Nhóm cần duyệt output contract/acceptance criteria và lựa chọn cuối; **MODEL SELECTION PENDING**,LR baseline đang dùng không đổi.
Không suy clinical validity hoặc significance của LR tuned so baseline từ protocol chỉ so LR tuned/hard này.

Guards0 fit/test/write/network; chỉ predict từ checkpoint đã fit được gọi trong benchmark.
Không source/schema/mapping/checkpoint/notebook/output changes.
Kế hoạch [WORKSPACE_HANDOVER_PLAN.md](../planning/WORKSPACE_HANDOVER_PLAN.md) tách KEEP/IGNORE/REGENERATE/REVIEW/REMOVE-LATER,
các dependency/copy checks và hành động cần phê duyệt trước cleanup. Chưa xóa/di chuyển hoặc tự chốt model.

## Final locked-test protocol 2026-10-30

**PREDECLARED — TEST NOT EXECUTED.** Owner đã duyệt **LR tuned C=2** là deployment model cho chatbot/API nghiên cứu
trước khi đọc test. Đây là thay đổi trạng thái phê duyệt, không tự đổi default/config/checkpoint hiện hành.
Hard tuned LR+SVC+KNN vẫn là đối chứng có validation Macro F1 quan sát cao nhất; LR baseline là mốc gốc.
Điểm test, dù theo thứ tự nào, **không** được dùng chọn model, C, thành viên/weights/tie priority, feature,
threshold, calibration hoặc mở thêm search. Không fit lại trên train+validation.

Protocol `final-locked-test-v1` SHA-256:
`049ee0aa3c2907985c3d3a03ed222b1d6e1efb5921bbbc2d04ec0dea9baa8947`.
[Frozen protocol source](../../../src/models/final_evaluation_protocol.py) lưu đầy đủ configs, identity, source hashes,
phiên bản, file hashes và validation reference; không tự cập nhật từ artifact chưa được xác minh.
[Notebook06](../../../notebooks/06_final_model_evaluation.ipynb) là entry point riêng;
[evaluator](../../../src/models/final_evaluation.py) tái sử dụng loader/pipeline/vote hiện có.

### Ba ứng viên và bốn pipeline đã fit

| Ứng viên/checkpoint | Namespace và cấu hình cố định | Pipeline SHA-256 |
|---|---|---|
| LR baseline | `artifacts/models/phase3/baseline-v1-f8a5bfdb7b4c12cd/logistic_regression`; saga,C=1,max_iter=200,tol=0.001,seed42 | `54f124240fd2bb8fb61c39594a55663e1b67f5f5b67595faeaa350504d0376da` |
| **LR tuned — deployment approved** | `artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/logistic_regression`; saga,C=2,max_iter=200,tol=0.001,seed42 | `4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6` |
| SVC tuned — thành viên hard comparator | C=2,dual=auto,max_iter=3000,tol=0.001,seed42; cùng namespace tuning,folder `linear_svc` | `1ac35a1e68225142c6ff60332d8fcf973a57cc0f84c18be320f396830c32fe89` |
| KNN tuned — thành viên hard comparator | k=7,weights=distance,algorithm=brute,metric=manhattan,n_jobs=1; folder `knn` | `1d84f44c5d3eec025d7f9fc574fb80eba58b0e38fbb6927ed7090ebe9446b976` |

Selected tuned identity dự kiến `tuned-v1-b8a5602679b3dc5c` được tái dựng tất định từ selection đã audit,
config/source gốc và versions; phải khớp chính xác `fit.json`/tuning manifest thật trong preflight trước test.
Selection SHA `6191034dcc4a9c2393645929ea8942bc6eedc40206942b8384f30921bf727703`.
Tuning manifest SHA `4a10ddd5deba5fff7927f84ea334196a3f6d127b9777ced2b127f5b5e9389355` khóa bundle26 file,
bao gồm fit/metadata/validation_predictions của năm tuned checkpoint. Chỉ dùng ba thành viên đã định cho inference hard.
Baseline LR có đủ bốn file hash riêng trong protocol; không chỉ kiểm hash pipeline.

Hard policy/run `tuned-ensemble-20261029T041701354242Z-6c84dbfe`, manifest SHA
`858893c442f1966eb8c7508a74cf6318b820004278342a1b958942151c049060`.
Uniform majority qua **nguyên hàm** `src.models.ensemble.hard_vote`, hòa theo priority gốc LR>SVC>KNN>NB>RF,
lọc còn LR>SVC>KNN trong tổ hợp này. Không tạo voting wrapper/policy mới, không dùng số phiếu làm probability.
Hash engine, hard members, tie priority và selected identity đều phải khớp trước đọc test.

Môi trường checkpoint phải khớp: Python3.13.18,scikit-learn1.6.1,NumPy2.1.3,SciPy1.16.3,joblib1.6.0;
custom `src.models.training.to_csr` cùng source gốc. Mọi pipeline giữ input375 và preprocessing đã fit trên train;
`VarianceThreshold(0)`/CSR/estimator không được fit lại trên test. Source mới chỉ bổ sung module đánh giá,
không sửa tám file identity gốc hoặc bootstrap/staging.

### Identity test và scoring trước khi truy cập payload

- Manifest Phase2 gắn với checkpoint Drive:
  `50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9`.
  Bản local `ca20a551…` được giữ nguyên; **không** chép đè Drive manifest để vượt preflight.
- Test `data/processed/test.csv.gz`: SHA `d71a040a6ead853931cfc75452e456906e5277a3081dc97e8af5688ed4268dd0`,
  292.558 bytes; dự kiến **28.066 dòng,25.128 group,375 feature,587 lớp** từ metadata đã khóa.
  Chuẩn bị không mở/băm/stat test CSV; checksum trên được đọc từ manifest đã có.
- Schema SHA `dd07a3c73dd41558daa9c08e816e0a93d9efc4155f98b7e2b73325bffe31c5c0`;
  mapping SHA `d2ef711e5e04062e8b5b949ce434b1383e1ca2fef6eb31a0865acb2f470ab5b5`.
  Giữ đúng `features`/`classes` Phase2; scorer luôn labels0..586, `zero_division=0`, kể cả nếu payload thiếu lớp.
- Primary **Macro F1**; secondary Accuracy,Macro Precision/Recall,Weighted F1,predicted-label coverage,F1=0 count.
  Báo support và missing label IDs; không loại lớp hiếm hoặc chỉ tính labels có dự đoán.
- Validation references đã kiểm: baseline LR F1=0.78780814,LR tuned=0.79315438,hard tuned=0.79651707.
  Bảng validation–test giữ thứ tự ba ứng viên đã khai báo, không thay model theo ranking mới.

### Phân tích mô tả đã định trước

Ba cặp `(reference,candidate)`: `(LR baseline,LR tuned)`, `(LR tuned,hard tuned)`, `(LR baseline,hard tuned)`.
Báo both-correct,both-wrong,rescues,new-errors trên cùng hàng test và so với ground truth.
Với mỗi symptom group, tính tỷ lệ hàng đúng từng model và paired delta; tổng hợp cho group trọng số bằng nhau,
báo số group tăng/giảm/không đổi. Không gọi metric này là group Macro F1 hoặc CI.
Không thêm bootstrap, p-value, tổ hợp hoặc tối ưu sau khi xem test. CI validation trong ML_GAPS vẫn là lịch sử riêng.

Bảng per-class đủ587 ID/tên nguyên bản, support,unique groups,precision/recall/F1 của ba ứng viên.
Support bins cố định: 0,1,2–5,6–20,>20. Một hình hai panel: validation–test Macro F1 và mean class F1 theo support bin.
Không lọc ca test để chứng minh model mạnh hơn hoặc dùng lớp F1=0 để sửa feature/model trong lần đánh giá này.

### Gate, publication và giới hạn

Notebook mặc định `RUN_FINAL_LOCKED_TEST=False`, `OWNER_AUTHORIZATION=""`.
Owner cần **ủy quyền riêng ở bước kế tiếp** cho đúng protocol ID/SHA và ba ứng viên;
quyết định deployment ở trên không phải quyền đọc test. Chỉ sau đó mới bật switch và điền chuỗi xác nhận đúng protocol.
Preflight chỉ đọc nguồn/checksum train-validation/metadata/checkpoint; không deserialize/predict/fit/test access.
Gate bật xác minh lại preflight, environment và reload object/schema/params trước test.

Namespace mới trên canonical Drive:
`artifacts/metadata/final_evaluation/049ee0aa3c290798/`.
Tạo `execution.json` độc quyền và flush/fsync **trước** gọi loader test. Loader được gọi đúng một lần cho một lần đánh giá;
loader hiện có băm checksum rồi parse CSV, không cache/copy test. LR tuned được dùng lại khi vote, không predict hai lần.
Không ghi đè artifact cũ. Started/partial/completed/orphaned namespace đều chặn chạy lại;
không xóa marker hoặc tự resume sau disconnect. Owner phải rà soát failure/partial nếu có.

Outputs cố định (chỉ tạo khi đã được phép và chạy thật):

| File | Nội dung |
|---|---|
| `execution.json` | Thời điểm bắt đầu,authorization,protocol/code hashes; giữ nguyên như receipt |
| `protocol.json`,`preflight.json` | Frozen configs/identities và bằng chứng preflight trước mở test |
| `test_predictions.npz` | y_true,group_id,row_0based và đúng3 vector dự đoán đã định; SVC/KNN chỉ là thành viên nội bộ |
| `comparison.csv` | Validation và test metrics; không metric mô phỏng |
| `transitions.csv`,`group_differences.csv` | Ba cặp lỗi và bảng paired correctness theo group |
| `per_class.csv` | Đủ587 lớp,raw support/independent groups và metrics |
| `comparison.png` | Hai panel được sinh từ bảng kết quả thật |
| `results.json`,`report.md` | Warnings,counts,metrics và diễn giải/giới hạn |
| `manifest.json` | Marker **cuối cùng**,checksum/size toàn bộ11 file trên,code/environment/protocol và trạng thái completed |

Nếu lỗi/interruption sau marker: thêm `failure.json` nếu kernel còn hoạt động, **không** có completed manifest.
`results.json` hoặc predictions riêng lẻ không đủ chứng minh hoàn tất.
`read_completed(folder)` chỉ kiểm/đọc output đã lưu, không reopen CSV test hay gọi predict.
Outputs nằm cùng namespace mới để không lẫn reports Phase3/4; chưa có file output cuối nào được tạo trong bước chuẩn bị.

Dataset synthetic và xung đột nhiều disease cùng vector hạn chế generalization; 0 chỉ là không ghi nhận hiện diện.
Phase1 từng EDA toàn CSV nên đây là held-out-from-training/tuning, **không** phải external blind clinical test.
Probability chưa calibration; không đo chất lượng LLM extraction hoặc tính phù hợp với bệnh nhân thật bằng các metric này.
LR tuned đã được duyệt giữ nguyên vai trò deployment bất kể điểm test; chưa triển khai API/frontend/Gemini.
