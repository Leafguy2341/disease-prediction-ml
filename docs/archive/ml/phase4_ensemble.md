> ARCHIVE — Bản tại thời điểm trước hợp nhất tài liệu. Các trạng thái và lệnh cũ không phải hướng dẫn hiện hành. Xem [chỉ mục hiện hành](../../README.md) và [triển khai](../../DEPLOYMENT_GUIDE.md). Đường dẫn trong code block vẫn tính từ project root.

# Phase 4 — Báo cáo validation và lựa chọn mô hình

Notebook duy nhất: [04_ensemble.ipynb](../../../notebooks/04_ensemble.ipynb). Dùng shared runtime Colab/Drive hiện có, fixed run `baseline-v1-f8a5bfdb7b4c12cd`; không fit baseline/calibrator, tune trọng số, mở test hoặc triển khai chatbot.

**Cập nhật 2026-10-29 — MODEL SELECTION PENDING:** section cuối notebook dùng selected checkpoints
từ tuning notebook03; người dùng đã chủ động bật switch và lưu output. **Đã nhận packet Post-Tuning Audit Colab PASS cho integrity/checkpoints/metrics**; phần quyết định model vẫn chờ nhóm duyệt.
Toàn bộ kết quả baseline dưới đây giữ nguyên; chưa chọn model sau tuning hoặc đổi LR mặc định.
Xem [search spaces, train-only group CV, resource limits và cách bật hai switch](MODEL_SELECTION_RATIONALE.md#hyperparameter-tuning-có-kiểm-soát).
Helper tái sử dụng voting/probability policies hiện có; không fit, không thay trọng số, không ghi đè run Phase4 cũ.

## Chạy trên Colab thật

Các bước sau mô tả cách chạy thí nghiệm; không phải yêu cầu chạy lại notebook để phân tích tài liệu.
Phần phân tích hiện tại chỉ đọc evidence đã có, giữ switch/output người dùng.

1. Source Phase 4 đã được chuẩn bị trong `dist/drive-source/` bằng [script chuẩn](../../../scripts/prepare_colab_source.ps1). Đồng bộ **nội dung** folder đó vào `MyDrive/ML_Projects/disease-prediction-ml/`, hợp nhất `src/`/`configs/`, giữ `data/`, `artifacts/`, `reports/`. File mới cần có trên Drive là `src/models/ensemble.py`. Không cần upload source vào `/content` hoặc dùng script audit Phase 3 để chạy Phase 4.
2. Mở notebook04 local, chọn đúng kernel/server Colab, mount Drive bằng lệnh extension. **Restart Kernel sau cập nhật source**; khi VM/server đổi cần mount lại Drive. Cấu hình vẫn ở `configs/runtime.json` và locator chung. [Hướng dẫn runtime](../runtime/phase3_colab.md).
3. Run All **notebook04**, không chạy lại các cell model notebook03. Cell setup04 gọi `bootstrap_runtime(..., phase=3)` hiện có để dùng source/dependencies Phase 3; không thêm bootstrap hoặc loader.
4. Theo dõi bảng verify, heatmap, hard vote, probability source, soft vote, bảng/chart, một-vector smoke và đường dẫn output Drive. KNN predict_proba toàn validation có thể mất vài phút. Không có package install/download tự động.
5. Cuối cell export dùng Copy Cell Output lấy hai dòng `PHASE4_SHA256=...` và `PHASE4_GZIP_BASE64=...`; gửi lại để cập nhật nhật ký bằng kết quả thật. Nếu lỗi, gửi traceback đầu tiên; không thay checkpoint/checksum để vượt cổng kiểm tra.

Agent chưa có quyền truy cập kernel/Drive trực tiếp. **Đã nhận và kiểm packet Colab thật do người dùng chạy notebook04 ngày 2026-10-28**; đây là bằng chứng thực thi, tách biệt với unit tests local.

## Kết quả validation đã nhận

Run `phase4-20261028T091711786379Z-c1c66643`, cùng **28.120 mẫu, 375 feature, 587 lớp**. Cả ba Hard Voting và hai Soft Voting đều hoàn tất; không có tổ hợp vượt LR. LR Macro F1 **0,78780814**; ensemble cao nhất LR+SVC+KNN **0,78733399**, thấp hơn 0,00047415. LR/SVC bất đồng 7,6387% nhưng cùng sai 14,4488%; các hard vote đều làm sai thêm nhiều hàng hơn số hàng sửa được cho LR. **Đề xuất giữ LR đơn**: một pipeline nén 1,372 MiB, tránh thêm chi phí KNN mà không cải thiện metric trên split này. Chênh lệch không chứng minh ý nghĩa thống kê hoặc hiệu quả ngoài bộ dữ liệu.

Xác suất thật được sinh từ bốn checkpoint LR/RF/KNN/NB đã fit, mỗi ma trận 28.120×587 và cùng class order, không calibrate. Lần sinh probability này mất LR 10,747s / RF 34,849s / KNN 300,938s / NB 12,704s; đây là thời gian validation theo batch gồm kiểm tra, không phải latency một request. Kiểm inference một vector375 của candidate LR **PASS**, khớp hàng validation0. Guard ghi **0 fit, 0 truy cập test, 0 ghi vào vùng được bảo vệ**.

- [Bảng metrics đầy đủ, diversity, trade-off và giới hạn trong nhật ký](../planning/PROJECT_DEVELOPMENT_LOG.md#17-2026-10-28--hoàn-tất-phase-4-từ-kết-quả-colab).
- [Packet nguyên byte lưu local](../../../artifacts/metadata/phase4_audit/colab_validation_evidence.json), SHA-256 `42cf30dc39547656c572cf5ca4bb6a0eae3a6d31f0a923e6518e8618e835dd44`; source module trong packet khớp local/staging (`ee3121f04b187845fbff937add77a527d2761df14e035e94f48100b1d647443c`).
- Trên **Drive**, report của lần chạy: `reports/runs/phase4-20261028T091711786379Z-c1c66643/phase4_validation.md`; definitions: `artifacts/models/phase4/phase4-20261028T091711786379Z-c1c66643/definitions.json`.
- Manifest Drive: `artifacts/metadata/runs/phase4-20261028T091711786379Z-c1c66643/phase4_manifest.json`; SHA do Colab báo `d9d45b1972bb3f880f11db12a74b5258c1cc0e350075012e30dc9b42e5867281`. Agent đã kiểm tính nhất quán packet, chưa tải lại từng artifact Drive để băm độc lập. Không cần chạy lại notebook chỉ để cập nhật tài liệu.

Dừng sau validation/documentation Phase4. LR được chọn làm model inference mặc định trong thiết kế Phase5; **chưa đánh giá locked test** và chưa triển khai chatbot. Report do Colab sinh trong run đã khóa vẫn giữ nguyên cùng manifest; phần biện luận được cập nhật tại tài liệu hiện có này, không ghi lại artifact Drive.

## Biện luận lựa chọn mô hình

Kết quả quan sát trên cùng validation, không phải hiệu năng lâm sàng hay test:

| Mô hình/tổ hợp | Macro F1 | Chênh lệch so LR |
|---|---:|---:|
| **Logistic Regression** | **0,78780814** | 0 |
| Hard LR + SVC + KNN | 0,78733399 | −0,00047415 |
| Hard LR + SVC + NB | 0,78478926 | −0,00301888 |
| Hard LR + SVC + RF | 0,78405303 | −0,00375511 |
| Soft LR + NB + RF | 0,72469398 | −0,06311416 |
| Soft LR + KNN + NB | 0,76324258 | −0,02456556 |

**Chọn LR làm mặc định:** điểm chính cao nhất trong các phương án đã thử, dự đoán 560/587 lớp với 28 lớp F1=0; ensemble tốt nhất chỉ dự đoán559 lớp và có29 lớp F1=0. LR dùng một pipeline nhỏ thay vì ba model và không cần chi phí tìm láng giềng KNN. Đây là quyết định theo giao thức hiện có, không khẳng định LR tối ưu cho mọi dataset, tham số hoặc quần thể. Chênh lệch LR–hard tốt nhất rất nhỏ, chưa kiểm ý nghĩa thống kê.

**Vì sao Voting chưa cải thiện:** bằng chứng trực tiếp là số hàng được cứu/làm sai và Macro F1, không chỉ mức bất đồng. Hard LR+SVC+KNN cứu152 nhưng làm sai170 hàng; hai tổ hợp hard còn lại lần lượt160/187 và153/199. Soft LR+NB+RF là559/887, Soft LR+KNN+NB là917/1.201. Chất lượng từng thành viên và việc sửa đúng lỗi của nhau đều quan trọng: một model chọn nhãn khác LR có thể cũng sai. LR/SVC cùng sai4.063 hàng; khác họ thuật toán không tự tạo khả năng bổ sung hữu ích.

**Ảnh hưởng của tie:** ba nhãn khác nhau chọn LR theo quy tắc đã định, ở1.000/659/1.263 hàng của ba hard vote. Vì vậy Voting giữ lại nhiều quyết định LR và chỉ thay khi hai model còn lại đồng thuận; quy tắc bất đối xứng này phải đi cùng mọi kết luận. Nếu cả LR/SVC sai, model thứ ba đúng vẫn không cứu được: hoặc hai phiếu sai trùng nhau thắng, hoặc hòa ba nhãn trả nhãn LR sai. Không thử tie rule khác sau khi xem metric.

**Soft Voting và giả thuyết:** đã xác minh probability thật, căn đúng lớp/hàng và hợp lệ số học; chưa đo calibration. Trung bình đều vẫn có thể bị thành viên xác suất quá tập trung hoặc kém phân biệt kéo lệch. Đây là **giả thuyết giải thích**, chưa có reliability curve hoặc phân tích sai số để kết luận calibration là nguyên nhân làm giảm F1. Việc RF/NB yếu hơn LR ở Macro F1 đơn lẻ đã được quan sát trong audit Phase3; nó không chứng minh bỏ một thành viên hay tune trọng số sẽ tốt hơn. Không fit calibrator hoặc làm thí nghiệm bổ sung. [Calibration của scikit-learn](https://scikit-learn.org/stable/modules/calibration.html).

**Vì sao Macro F1 là chính:** lấy trung bình F1 của từng lớp trong đủ587 lớp, mỗi lớp có trọng số bằng nhau, nên lớp phổ biến không che toàn bộ chất lượng lớp hiếm. F1 từng lớp kết hợp precision và recall; Macro F1 không phải harmonic mean của Macro Precision và Macro Recall. Với support thấp, metric vẫn có phương sai lớn; validation có33 lớp chỉ một mẫu, không thể diễn giải điểm từng bệnh như ước lượng ổn định. [Định nghĩa metric](https://scikit-learn.org/1.6/modules/model_evaluation.html#multiclass-and-multilabel-classification).

| Metric bổ sung | Câu hỏi mà nó giúp trả lời | Giới hạn |
|---|---|---|
| Accuracy | Bao nhiêu hàng được phân loại đúng? LR:0,83709104. | Các lớp nhiều mẫu có ảnh hưởng lớn. |
| Weighted F1 | F1 theo support của lớp; LR:0,83667539. | Có thể che chất lượng kém ở lớp hiếm. |
| Macro Precision | Trung bình độ chính xác khi gọi từng lớp; LR:0,82741979. | Đọc cùng coverage, không tự bảo đảm recall. |
| Macro Recall | Trung bình tỷ lệ tìm lại mỗi lớp; LR:0,77918852. | Không phản ánh riêng số lần gọi nhầm lớp. |

**Giới hạn ngoại suy:** dữ liệu được mô tả là tổng hợp, thiếu xác thực nguồn ở mức checksum nhà xuất bản và đánh giá trên người bệnh độc lập. Kết quả chỉ đo khả năng khớp nhãn của dataset; không xác lập độ tin cậy chẩn đoán, tỷ lệ mắc bệnh thực, hay tính phù hợp với lời kể tiếng Việt. Sai lệch do trích xuất, phủ định, thiếu triệu chứng và dịch thuật chưa được đo. Phase1 từng EDA toàn CSV, nên không gọi test khóa sau đó là hoàn toàn chưa từng được xem. **LR chưa qua final locked-test evaluation.**

Mặc định ứng dụng nghiên cứu sẽ dùng LR; demo tùy chọn chỉ so LR với hard tốt nhất LR+SVC+KNN và soft tốt nhất LR+KNN+NB trên cùng vector đã kiểm. Không trình bày năm baseline như các lựa chọn chẩn đoán tương đương cho người dùng. [Thiết kế Phase5 và kế hoạch đánh giá](../integration/phase5_llm_integration_design.md).

## Giao thức cố định

| Loại | Các tổ hợp, mỗi model một trọng số |
|---|---|
| Hard | LR + SVC + KNN; LR + SVC + NB; LR + SVC + RF |
| Soft | LR + NB + RF; LR + KNN + NB |

Không thử tổ hợp khác hoặc chọn trọng số bằng validation. Hard chọn nhãn có nhiều phiếu; khi các nhãn thắng hòa, ưu tiên dự đoán model theo thứ tự **LR → SVC → KNN → NB → RF**, không dựa ID nhãn. Với ba model đang xét, hòa ba nhãn khác nhau chọn LR. Soft dùng trung bình xác suất float64; hòa chính xác chọn xác suất LR lớn hơn trong các nhãn đang hòa, sau đó tên nhãn tiếng Anh theo Unicode.

Không dùng `VotingClassifier.fit` vì API đó fit clone các estimator. [VotingClassifier](https://scikit-learn.org/1.6/modules/generated/sklearn.ensemble.VotingClassifier.html). Mọi inference dùng pipeline đã fit và loader checkpoint hiện có. `PrefittedVoting` không có phương thức fit.

Soft chỉ nhận probability trong payload Phase 3 đã kiểm SHA, kèm `class_ids` và `probability_method=predict_proba`; nếu không có, gọi `predict_proba` của model tin cậy theo batch64. Kiểm đúng số hàng, thứ tự 587 lớp, finite, nonnegative, miền [0,1], tổng hàng trong atol1e-6 của1, và argmax khớp hard predictions Phase3. Không tạo probability từ hard labels/decision scores hoặc calibrate LinearSVC. Class order hay checksum sai dừng rõ ràng; thiếu môi trường/source/RAM hỗ trợ thì ghi limitation và không tạo metric cho soft combination thiếu input.

Xác suất ở cache tạm runtime bằng memmap, không ghi ma trận lớn về Drive. Cache được dọn cuối notebook; mất VM có thể cần tính lại probability từ model đã fit. Xác suất hợp lệ về cấu trúc không đồng nghĩa được calibration tốt. [Probability calibration](https://scikit-learn.org/stable/modules/calibration.html).

## Diễn giải và giới hạn

Heatmap duy nhất5×5 ghi D=prediction disagreement, J=joint error, màu theo J. Bảng directed rescue A sai/B đúng dùng cùng28.120 mẫu, không phải tỷ lệ điều kiện trên mẫu A sai. Hai model chọn khác nhãn có thể đều sai.

Với hard vote3 model và tie ưu tiên LR, model thứ ba không cứu được trường hợp cả LR/SVC sai: hai phiếu sai hoặc ba nhãn hòa vẫn cho nhãn sai. Vì vậy notebook báo số hàng sửa lỗi LR và số hàng làm sai thêm, cùng metrics, thay vì dùng “khác họ học” làm bằng chứng cải thiện.

Macro F1 primary; accuracy, Macro Precision/Recall, Weighted F1, coverage và số lớp F1=0 đi kèm. LR được tái kiểm ở0,78780814 trong tolerance làm tròn8 chữ số. Chọn ứng viên bằng Macro F1; nếu hòa chính xác ưu tiên ít model rồi ID ổn định. Không gọi cải thiện nhỏ là có ý nghĩa thống kê. Support thấp, dữ liệu tổng hợp, Phase1 từng EDA toàn CSV và việc dùng lại validation để chọn tổ hợp vẫn hạn chế kết luận.

Giữ riêng chi phí sinh probability validation mới và thời gian baseline gốc. Tổng thời gian predict gốc của các model chỉ là tham chiếu, không phải thời gian ensemble đo mới hoặc latency người dùng. File model nén không bằng peak RAM. Notebook kiểm đúng một input375 feature với pipeline gốc, không benchmark latency. Không có chatbot/LLM ở bước này.

## Output và inference

Mỗi export dùng `RuntimePaths.new_run('phase4')` hiện có, không ghi đè Phase2/3:

- `reports/runs/<phase4-run>/`: một CSV so sánh, đúng2 PNG, một report ngắn.
- `artifacts/metadata/runs/<phase4-run>/`: predictions validation ensemble, results JSON và manifest ghi cuối với SHA/size output.
- `artifacts/models/phase4/<phase4-run>/definitions.json`: tổ hợp, uniform weights, tie policy, source checkpoint identity/SHA, feature order và classes. Không chứa bản sao weight/pipeline.

Load definition đã kiểm SHA, chỉ checkpoint của dự án và đúng phiên bản môi trường đã train:

```python
from src.models.ensemble import load_voting_definition

voter = load_voting_definition(
    runtime_paths.storage_root / phase4_result["definition_relative"],
    runtime_paths.storage_root,
    trusted=True,
)
# future_X phải có đúng375 cột theo feature_schema, nhị phân và không NaN.
# prediction_ids = voter.predict(future_X)
voter.close()
```

Nếu LR vẫn tốt nhất, candidate definition tham chiếu đúng một model LR; không cố chọn ensemble. Final model/test-set evaluation chờ người dùng duyệt sau kết quả validation.

## Kiểm tra local và trạng thái

[test_ensemble.py](../../../tests/test_ensemble.py): majority và tie độc lập mã nhãn, soft mean/tie, probability sai, diversity/rescue, guard, trường hợp thiếu probability, single-vector wrapper và export/definition checksum không sửa Phase3. Fixtures dùng doubles/array nhỏ, không training baseline hoặc tạo hình hiệu năng dự án giả.

Bộ gộp lần kiểm tra đầu: **48 passed, 1 failed**. Failure có sẵn ở `test_notebooks_have_one_short_direct_drive_setup_and_keep_model_cells`: smoke notebook đã chèn cell mount, còn utility cập nhật dùng index cố định nên không idempotent. Sửa tối thiểu trong `scripts/update_colab_notebooks.py` để tìm setup/preflight/smoke theo nội dung, thêm test giữ nguyên mount cell/output; không chạy updater trên file người dùng, không sửa bootstrap.

**Kiểm tra cuối: 50 passed**, gồm 15 test Phase4 và các test preflight/audit/runtime/deployment liên quan, không training baseline. Không tuyên bố toàn bộ suite có model fitting đã chạy. Lệnh:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_ensemble.py tests/test_phase3_preflight.py tests/test_post_training_audit.py tests/test_canonical_colab_runtime.py tests/test_manifest_deployment.py
```

Source-only staging hiện có **32 file**, `-CheckOnly` PASS; source fingerprint `fc45ec50a18222aa4bc1ab71e55081becb478df406f7ea4c46bbd74edec3298b`. Fingerprint tổng source đổi do thêm module ensemble; sáu file source được identity Phase3 tham chiếu và mọi model/dataset không đổi. Bộ 50 test liên quan được chạy lại sau nhận packet: **50 passed trong 20,80s**. Đã đối chiếu SHA packet/source, schema/counts, năm tổ hợp cố định, baseline metrics, delta/số hàng sửa/làm sai, ma trận diversity và SHA bốn pipeline probability với evidence audit Phase3; tất cả khớp. Các phép đối chiếu local không fit model hoặc đọc test. Kết quả Colab ở phần trên là output người dùng cung cấp, không phải agent trực tiếp điều khiển kernel.


## Bổ sung phân tích ensemble sau tuning

Xem [phân tích học thuật chung](MODEL_SELECTION_RATIONALE.md#phân-tích-học-thuật-và-lựa-chọn-hiện-tại)
cho bảng đa tiêu chí và tách bằng chứng khỏi giả thuyết. Các metrics, tie counts, rescue/loss và diversity **baseline** trong report này
vẫn dựa trên packet42cf30dc đã kiểm. Kết quả baseline LR+SVC+KNN sửa152 nhưng làm sai170 hàng,
net−18, khớp chênh Accuracy; Macro F1 cũng thấp hơn LR. Các tỷ lệ joint error không phải tỷ lệ cùng chọn một nhãn sai.

Với3 hard vote ưu tiên LR khi hòa, nhãn LR chỉ đổi khi hai thành viên kia đồng ý nhãn khác.
Vì vậy KNN đúng trong một hàng mà cả LR/SVC đều sai vẫn không cứu được hàng đó.
Hard tuned có điểm tăng đã kiểm, nhưng nguyên nhân phải được phân tích bằng member predictions và transition/per-class changes,
không gán tự động cho “đa dạng thuật toán” hoặc “tuning tạo độc lập lỗi”.

[Packet Post-Tuning đã nhận](../../../artifacts/metadata/post_tuning_audit/colab_evidence.json) có SHA
`70849a69a0d2cd571e2d93a938b98a9167b9d46ceb0db9d6cb1859f6a2e415e8`.
Colab audit kiểm manifest `858893c442f1966eb8c7508a74cf6318b820004278342a1b958942151c049060`,
run `tuned-ensemble-20261029T041701354242Z-6c84dbfe`, linked tuning `tuning-v1-9c4dd013abbba14a`;
checksum4 ensemble files, saved predictions alignment/metrics và hard voting từ member predictions PASS.
Configs selected: LR C2,SVC C2,KNN k7,RF depth32,NB alpha0.5; tham số khác giữ baseline.

| Phương án tuned | Macro F1 | Accuracy | Weighted F1 | Coverage /F1zero |
|---|---:|---:|---:|---:|
| LR đơn | 0.79315438 | 0.83766003 | 0.83843972 | 566 /23 |
| Hard LR+SVC+KNN | 0.79651707 | 0.83691323 | 0.83768176 | 567 /21 |
| Hard LR+SVC+NB | 0.78725551 | 0.83709104 | 0.83755198 | 564 /25 |
| Hard LR+SVC+RF | 0.78769267 | 0.83573969 | 0.83626975 | 564 /25 |
| Soft LR+NB+RF | 0.76487052 | 0.83268137 | 0.83084513 | 548 /41 |
| Soft LR+KNN+NB | 0.77043797 | 0.82972973 | 0.82975403 | 550 /38 |

Hard LR+SVC+KNN dẫn Macro F1 trong11 phương án baseline LR/5 selected/5 ensemble:
+0.00336269 so LR tuned, nhưng Accuracy giảm0.00074680 (net−21 hàng đúng), Weighted F1 giảm0.00075796.
Đây là accounting từ metrics trên cùng28.120 hàng, **không phải gross số sửa/làm sai**.
Coverage tăng1, F1zero giảm2 không tự chứng minh2 lớp cũ được cứu hoặc lợi ích riêng cho lớp hiếm.
**Supplement Colab đã nhận và kiểm SHA**
`4ccfa85ac4639778ffae6d11a435fb78af825bb4e1c294792356bec7236b4d28`,
lưu tại [model_analysis/colab_supplement.json](../../../artifacts/metadata/model_analysis/colab_supplement.json),
cùng tuning/ensemble manifest SHA với audit chính. Nó hoàn tất paired-error summary:

| Tuned ensemble | Sửa LR tuned sai | Làm sai LR tuned đúng | Net correct | Tie rows |
|---|---:|---:|---:|---:|
| Hard LR+SVC+KNN | 173 | 194 | −21 | 963 |
| Hard LR+SVC+NB | 185 | 201 | −16 | 679 |
| Hard LR+SVC+RF | 204 | 258 | −54 | 1245 |
| Soft LR+NB+RF | 464 | 604 | −140 | 0 |
| Soft LR+KNN+NB | 743 | 966 | −223 | 0 |

Hard tốt nhất: cảhai đúng23.361/cảhai sai4.392,115 lớp tăng F1/128 giảm/344 không đổi.
Hai lớp0→positive,0 positive→0; cảhai lớp được cứu chỉsupport1.
Nhóm≤5 (132 lớp/363 hàng) đóng góp93.82% net Macro F1 gain, trong khi nhóm>20 đóng góp âm.
Đó là bằng chứng cải thiện quan sát tập trung ở tail và có thể nhạy với ít mẫu, không chứng minh clinical benefit hoặc stability.

LR/SVC tuned joint error14.2176% giảm so baseline14.4488%; LR/KNN và SVC/KNN tăng nhẹ.
Không kết luận tuning làm mọi thành viên độc lập hơn. Chi tiết ma trận, full candidate scores,
class-support decomposition và [một hình hai panel](../../../../disease-prediction-ml-data/reports/figures/model_selection_tuned_error_analysis.png)
ở [rationale chung](MODEL_SELECTION_RATIONALE.md#ensemble-tuned-kết-quả-đã-kiểm-và-giới-hạn-giải-thích).
Không tính CI hoặc causal explanation từ aggregate.
Mọi chuyển trạng thái tuned phải so LR tuned; đối chiếu LR baseline được ghi riêng.

Tổng checkpoint bytes hard3.554.419, LR tuned1.438.563; saved validation-predict sums300.793s và2.115s.
Đó là proxy từ records có thể khác phiên, không measured latency/RAM một request.
Soft metrics từ saved labels PASS nhưng probability memmap không persist;
audit không tính lại mean probabilities và không chạy predict_proba mới.
Source/schema/identity/reload được audit trên Colab; agent local chỉ kiểm packet/source SHA và arithmetic,
không tự tải lại Drive artifacts. Không fit/predict/test/write/network trong audit.

Hard voting có thể đứng đầu Macro F1 và vẫn chưa phù hợp API cần Top3 probability: vote share không là posterior bệnh,
SVC không có predict_proba, và ghép Top1 ensemble với Top3 của LR là policy mới chưa được đánh giá.
Chi phí3 pipeline/KNN, measured RAM/p95 và tính ổn định cần cùng môi trường; không coi tổng prediction time trên validation là latency request.
Không tự chọn LR tuned thay ensemble hoặc ngược lại. **MODEL SELECTION PENDING** tới khi có evidence đầy đủ và nhóm duyệt.
