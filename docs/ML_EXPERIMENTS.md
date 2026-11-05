# Thực nghiệm ML và quyết định lựa chọn

## Quyết định hiện hành

**LR tuned C=2 được duyệt làm model ứng dụng trước final test**. Hard tuned LR+SVC+KNN là best observed validation Macro F1 comparator; LR baseline là mốc gốc. Final test đã hoàn tất, không dùng để chọn lại model, hyperparameters, thành viên, tie policy, thresholds hoặc calibration. PENDING trong archive là trạng thái trước phê duyệt.

## Dữ liệu và giao thức

Raw `Disease and symptoms dataset.csv`: 246.945 dòng, 377 triệu chứng, 773 lớp. [Audit](../reports/dataset_audit.md) và [EDA](../reports/eda_summary.md) ghi synthetic-source caveat, duplicate/conflicting vectors. Bỏ regurgitation/regurgitation.1 vì không ánh xạ tin cậy từ input, không phải vì nhìn model score. Dedup vector còn lại+label, tính lại unique vectors/lớp, giữ ≥10: **187.434 dòng, 375 feature, 587 lớp**. Giữ các disease khác nhau của cùng vector.

| Split | Records | Groups | Classes |
|---|---:|---:|---:|
| Train | 131248 | 117211 | 587 |
| Validation | 28120 | 25127 | 587 |
| Test đã khóa | 28066 | 25128 | 587 |

Group-disjoint theo symptom vector, gần 70/15/15, seed42; overlap vector/group=0, duplicate vector+label=0. [Phase2 report](../reports/preprocessing_decision_review.md) và [metadata](../../disease-prediction-ml-data/artifacts/metadata/phase2) là nguồn chi tiết. Validation/test có 33/41 lớp chỉ một vector; không coi presence đủ lớp là metric ổn định.

Metric chính **Macro F1 đủ 587 labels/zero_division=0**; secondary Accuracy, Macro Precision/Recall, Weighted F1, predicted coverage/F1=0. Pipeline chung VarianceThreshold(0)→CSR→estimator fit train hoặc CV-training fold; 375 input, 318 feature sau fitted variance trong checkpoints. Không PCA/feature selection từ validation/test. 0 nghĩa chưa ghi nhận hiện diện, không đồng nghĩa clinically absent.

## Năm thuật toán và tuning

LR học biên tuyến tính có điều chuẩn, dùng probability scores cho Top3; LinearSVC là đối chứng margin/OvR, không có calibrated probability. RF kiểm khả năng biểu diễn phi tuyến với capacity giới hạn. KNN kiểm so khớp lân cận Manhattan cho binary input, fit rẻ nhưng predict đắt. BernoulliNB mô hình hóa cả 0/1 với conditional-independence assumption; không coi các triệu chứng độc lập về y khoa. Đây là năm họ đã chọn cho so sánh, không chứng minh loại trừ boosting/MLP/kernel SVM.

Cấu hình gốc từ [phase3.json](../configs/phase3.json); tuned selection từ [audit](../artifacts/metadata/post_tuning_audit/colab_evidence.json), không sửa baseline thành tuned:

| Model | Baseline | Tuned: thay đổi được chọn |
|---|---|---|
| LR | saga, C1, max_iter200, tol0.001 | C2 |
| LinearSVC | C1, dual auto, max_iter3000, tol0.001 | C2 |
| RF | 100 cây, depth24, leaf cap512, min_leaf2, sqrt | depth32 |
| KNN | k5, distance weights, brute, Manhattan | k7 |
| BernoulliNB | alpha1, binarize=None | alpha0.5 |

SGKF3 shuffle/seed42 chỉ trên train groups. 15 candidates, 45 attempts completed, không failed/interrupted/ConvergenceWarning trong state; search capture 415 DeprecationWarning/36 ResourceWarning. **Train class coverage 587/587/587; holdout 586/586/587**: fold0 thiếu ID112 colorectal cancer, fold1 thiếu ID275 idiopathic infrequent menstruation. Scorer vẫn đủ 587 nhãn. Không dùng counts local sklearn1.8 thay run Colab1.6.1. Fold predictions không persist; selection arithmetic/assignment đã kiểm, không giả nhận tính lại fold F1 độc lập.

### Validation của năm baseline và năm tuned

Số dưới đây được trích từ packets đã audit, chỉ làm tròn khi trình bày; precision gốc giữ trong JSON. Không chạy prediction mới.

| Model | Baseline Macro F1 | Tuned Macro F1 | Baseline Accuracy | Tuned Accuracy |
|---|---:|---:|---:|---:|
| Logistic Regression | 0.78780814 | 0.79315438 | 0.83709104 | 0.83766003 |
| LinearSVC | 0.78422186 | 0.78636758 | 0.83079659 | 0.83111664 |
| Random Forest | 0.49199733 | 0.51090813 | 0.70053343 | 0.74206970 |
| KNN | 0.73103438 | 0.74567902 | 0.78314367 | 0.79032717 |
| BernoulliNB | 0.59934053 | 0.67213832 | 0.81486486 | 0.82727596 |

Cả năm cải thiện validation Macro F1 trong search space đã thử. NB tăng nhiều nhất nhưng chưa dẫn nhóm; LR/SVC tăng nhỏ; RF/KNN tăng không xóa chi phí/rare-class limitations. Không diễn giải tuning là bằng chứng causal hoặc clinical benefit. Candidate0 của năm search trùng config baseline; CV score không phải validation score.

<a id="ensemble"></a>
## Ensemble trước và sau tuning

Uniform hard majority, tie priority LR→SVC→KNN→NB→RF lọc theo members; reuse nguyên hard_vote đã khóa. Soft là mean probability, exact tie theo LR probability rồi English-label Unicode order. Không calibration SVC hoặc tìm weights sau khi nhìn validation.

| Tổ hợp | Baseline Macro F1 | Tuned Macro F1 | Baseline cứu/làm sai LR | Tuned cứu/làm sai LR |
|---|---:|---:|---:|---:|
| hard_lr_svc_knn | 0.78733399 | 0.79651707 | 152/170 | 173/194 |
| hard_lr_svc_nb | 0.78478926 | 0.78725551 | 160/187 | 185/201 |
| hard_lr_svc_rf | 0.78405303 | 0.78769267 | 153/199 | 204/258 |
| soft_lr_knn_nb | 0.76324258 | 0.77043797 | 917/1201 | 743/966 |
| soft_lr_nb_rf | 0.72469398 | 0.76487052 | 559/887 | 464/604 |

Rescue/loss so với LR **cùng giai đoạn**. Baseline hard tốt nhất sửa152/làm sai170 (net−18), không vượt LR0.78780814. LR/SVC có nhiều lỗi chung; đa số không bảo đảm tốt hơn classifier tốt nhất.

Tuned hard LR+SVC+KNN đạt0.7965170720239344, cao hơn LR tuned0.7931543818638241 nhưng Accuracy/Weighted F1 thấp hơn: sửa173/làm sai194, net−21. 115 lớp tăng F1/128 giảm/344 không đổi; 93,82% net gain Macro F1 từ support≤5. Hai lớp 0→positive chỉ một mẫu/lớp. Đây là mô tả paired predictions, không chứng minh mọi lỗi độc lập hơn hoặc KNN là nguyên nhân duy nhất.

[Hình paired errors/support hiện có](../../disease-prediction-ml-data/reports/figures/model_selection_tuned_error_analysis.png), [phân tích đầy đủ và bảng gốc](archive/ml/MODEL_SELECTION_RATIONALE.md#phân-tích-học-thuật-và-lựa-chọn-hiện-tại), [Phase4 report](archive/ml/phase4_ensemble.md) bảo toàn các bảng/hình đã có. Không tạo hình thực nghiệm mới. Soft saved labels/metrics đã kiểm; probability memmap tạm không persist nên không tái kiểm independent mean từ aggregate.

## Bất định và benchmark đã khóa

[ML_GAPS packet](../artifacts/metadata/final_ml_gaps/colab_evidence.json): paired group bootstrap seed20261029/B2000, lấy G groups đồng xác suất có hoàn lại, giữ mọi row và multiplicity của group cho cả candidates. Macro F1 đủ587/zero_division0; percentile2.5/97.5 dùng linear quantile.

Delta hard−LR tuned quan sát **+0.00336269016011026**; CI95% **[−0.000038072247733589275; +0.00622336858726049]** chứa0. Mọi replicate vắng lớp (min8/median19/max31), vẫn giữ nhãn vắng trong mẫu số587. CI chứa0 không xác nhận ưu thế ổn định hoặc tương đương; fraction-positive không là p-value/posterior. Bootstrap conditional trên validation, không xóa rare-class discontinuity/repeated-selection bias.

Benchmark cùng môi trường/input: 64 validation groups, seed20261029, ba warm-ups, ba vòng×64 batch1 calls/operation, BLAS1. Đã đo trước final test; không dùng timing baseline thay tuned.

| Condition | Verified load s | Warm-up Top1 ms, ba calls | Top1 p50/p95 ms | Proba+Top3 p50/p95 ms | Sampled process peak MiB |
|---|---:|---|---|---|---:|
| LR tuned | 0.036802 | 27.009/13.570/12.919 | 13.102/14.778 | 12.854/15.073 | 393.105 |
| Hard tuned | 0.111631 | 76.038/45.477/44.427 | 48.705/88.125 | Không probability Top3 | 393.535 |

LR proba+Top3 warm-ups14.259/13.311/12.683ms. Hard cần3 pipelines/3.554.419 compressed bytes; LR1/1.438.563 bytes. Integrity pre-read7,934s tách khỏi timings. Fixed LR→hard order, cache/allocator/RAM resident, RSS sampling0.5s có thể bỏ peak; không cold startup, concurrency, API/LLM/network hoặc SLA. Scores chưa calibration, hard votes không phải probabilities; không ghép Top1 hard/Top3LR thành policy mới.

<a id="final-locked-test-protocol-2026-10-30"></a>
## Final held-out evaluation đã hoàn tất

Protocol final-locked-test-v1 freeze trước đọc test, đúng ba candidates và bốn fitted members. Source đầy đủ ở [final_evaluation_protocol.py](../src/models/final_evaluation_protocol.py); checkpoints/configs/source/env/hash không thay đổi.

| Fitted member | Pipeline SHA-256 |
|---|---|
| LR baseline C1 | 54f124240fd2bb8fb61c39594a55663e1b67f5f5b67595faeaa350504d0376da |
| LR tuned C2 | 4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6 |
| SVC tuned C2 | 1ac35a1e68225142c6ff60332d8fcf973a57cc0f84c18be320f396830c32fe89 |
| KNN tuned k7 | 1d84f44c5d3eec025d7f9fc574fb80eba58b0e38fbb6927ed7090ebe9446b976 |

| Candidate | Validation Macro F1 | Test Macro F1 | Test Accuracy | Test Weighted F1 | Test coverage/F1=0 |
|---|---:|---:|---:|---:|---:|
| lr_baseline | 0.7878081402467481 | 0.7958306745796887 | 0.8426922254685384 | 0.8428343938933989 | 560/28 |
| lr_tuned_c2 | 0.7931543818638241 | 0.8081634861728620 | 0.8440818071688163 | 0.8449466206008978 | 567/22 |
| hard_tuned_lr_svc_knn | 0.7965170720239344 | 0.8059813671672197 | 0.8428347466685669 | 0.8436028751348400 | 567/22 |

[Closeout gốc](../reports/final_model_evaluation_closeout.md), [evidence JSON](../artifacts/metadata/final_evaluation_audit/colab_evidence.json): saved predictions đã đối chiếu results/comparison, atol1e-12; 28066 rows/25128 groups, đủ587 y_true classes. Metadata ghi test_loader_calls=1, models_fitted=0, model_selection_from_test=false. Paired correct/wrong, group và per-class support analyses nằm trong completed bundle, không chạy lại evaluation.

Namespace `artifacts/metadata/final_evaluation/049ee0aa3c290798/` trên canonical Drive; read_completed kiểm11 inventory files/manifest. Protocol SHA049ee0aa3c2907985c3d3a03ed222b1d6e1efb5921bbbc2d04ec0dea9baa8947; manifest SHAf1ad195e1e46154d7a29a421e80387bfa76e494f4df771cede240f882d0b754a. Giữ execution marker; không Run All notebook06 hoặc mở lại test CSV. Working copy có gateTrue; xem [điểm dừng notebook](HANDOVER_GUIDE.md#notebook-safety).

## Identity và giới hạn kết luận

Baseline run baseline-v1-f8a5bfdb7b4c12cd; tuning experiment tuning-v1-9c4dd013abbba14a; selected identity tuned-v1-b8a5602679b3dc5c. Tuning manifest SHA4a10ddd5deba5fff7927f84ea334196a3f6d127b9777ced2b127f5b5e9389355. Tuned ensemble run tuned-ensemble-20261029T041701354242Z-6c84dbfe, manifest SHA858893c442f1966eb8c7508a74cf6318b820004278342a1b958942151c049060.

Phase2 Drive manifest SHA50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9; processed fingerprint afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3. Local manifest variant ca20a551… là identity khác, không thay thế Drive variant gắn model.

LR tuned được chọn vì hợp đồng Top3/tài nguyên/độ đơn giản và validation, **không vì test dẫn ba candidates**. Higher observed score không chứng minh clinical usefulness/statistical superiority. Synthetic dataset, vector nhiều nhãn, thiếu clinical dictionary/patient-time-site IDs, EDA toànCSV, lớp hiếm và binary0 ambiguity đều giới hạn generalization. Probability chưa calibration; đầu vào từ LLM/tiếng Việt chưa có human-reviewed semantic evaluation hoặc live end-to-end PASS.

Bằng chứng ML Colab là packets đã kiểm checksum do kernel có quyền Drive tạo, không phải lần trực tiếp rehash toàn Drive trong nhiệm vụ tài liệu này. [Windows qualification](DEPLOYMENT_GUIDE.md#windows-runtime) là bằng chứng thực riêng cho đúng LR checkpoint, không mở rộng sang mọi pickle/model/runtime.
