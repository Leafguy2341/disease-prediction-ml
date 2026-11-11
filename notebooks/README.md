# Chỉ mục notebook — thí nghiệm và kiểm chứng

Thư mục này lưu các bước khảo sát dữ liệu, bốn thí nghiệm Machine Learning và bằng chứng kiểm chứng đã thực hiện. Website/API chạy bằng Python bên ngoài Jupyter theo [hướng dẫn triển khai](../docs/DEPLOYMENT_GUIDE.md).

**Để đọc hoặc trình bày đồ án, xem Markdown, bảng, hình và outputs đã lưu; không cần Run All.** Outputs và execution counts là bằng chứng lịch sử, không chứng minh môi trường hiện tại đã chạy thành công. Một notebook có thể chứa cả kết quả thành công lẫn chẩn đoán lỗi; chỉ kết luận theo evidence tương ứng đã xác minh.

## Danh sách đầy đủ

| Notebook | Mục tiêu và vai trò | Đầu vào | Kết quả và trạng thái bằng chứng |
|---|---|---|---|
| [00_dataset_audit.ipynb](00_dataset_audit.ipynb) | Audit nguồn dữ liệu, schema, chất lượng, mẫu trùng và nhãn xung đột | Raw CSV và cấu hình nguồn/runtime | Có outputs audit đã thực thi; bảng và fingerprint phục vụ provenance. Không huấn luyện model. |
| [01_eda.ipynb](01_eda.ipynb) | EDA phân bố nhãn, support, triệu chứng và mức dư thừa | Raw CSV và cấu hình audit/EDA | Có bảng, biểu đồ đã lưu; đây là mô tả dữ liệu, không phải đánh giá model. |
| [02_preprocessing.ipynb](02_preprocessing.ipynb) | Giải thích tiền xử lý, chia nhóm và bộ dữ liệu Phase 2 đã khóa | Cấu hình Phase 2 và metadata/split finalized; phụ lục lịch sử dùng raw | Có outputs đối chiếu; giữ schema 375 feature, mapping 587 lớp và identity. Không tái tạo split để xem báo cáo. |
| [03_model_training.ipynb](03_model_training.ipynb) | **Thí nghiệm 1:** năm baseline; **Thí nghiệm 3:** tuning train-only bằng group-aware CV | Train/validation, schema/mapping Phase 2, cấu hình và checkpoint | Có outputs baseline/tuning và phần tổng hợp học thuật, đối chiếu audit/manifests. Cell model có thể fit nếu thiếu checkpoint. |
| [04_ensemble.ipynb](04_ensemble.ipynb) | **Thí nghiệm 2:** baseline ensemble; **Thí nghiệm 4:** tuned ensemble | Checkpoint/predictions baseline và tuned, validation, ensemble policy/manifests | Có bảng so sánh, phân tích lỗi và phần tổng hợp đã lưu. Dùng model đã fit; không chọn tổ hợp bằng final test. |
| [05_structured_inference_check.ipynb](05_structured_inference_check.ipynb) | Structured inference của **năm baseline Phase 3**, cầu nối kỹ thuật tới ứng dụng | Checkpoint baseline, schema/mapping, ca validation chọn có chủ đích và vector giả lập | Có outputs và evidence inference đã xác minh: input 1 × 375, Top 1/Top 3 khi hỗ trợ, độ nhạy và timing. Ví dụ không phải metric tổng thể; ca giả lập không có ground truth. |
| [06_final_model_evaluation.ipynb](06_final_model_evaluation.ipynb) | Viewer closeout của final evaluation đã hoàn tất; **không lựa chọn lại model** | Frozen protocol, checkpoint identities và completed evidence bundle | Có kết quả ba ứng viên đã lưu: LR baseline, LR tuned C=2, Hard tuned LR+SVC+KNN. Luồng hiện tại kiểm checksum rồi dùng `read_completed(completed_folder)`; không chạy lại evaluation. |
| [07_vietnamese_symptom_extraction.ipynb](07_vietnamese_symptom_extraction.ipynb) | Nghiên cứu NLP riêng: Rule-based so với Semantic/Hybrid candidates; không phải thí nghiệm disease classification thứ năm | Catalog Việt 375 feature, 86 development fixtures và 32 reserved synthetic cases; embedding snapshot tùy chọn | Chạy tự động source → dependencies → embedding → extraction → metrics/figures; kết quả mới tách khỏi snapshot lịch sử. Semantic candidates có bảng retrieval riêng; không tự bật lên website. |
| [colab_smoke_test.ipynb](colab_smoke_test.ipynb) | Kiểm môi trường, shared bootstrap, imports, scripts và session/integrity độc lập | Source payload đã publish, Drive đã mount, train/validation/metadata Phase 2 | Có outputs kiểm tra lịch sử; PASS phải xét từng bước trong kernel đang dùng. Không load checkpoint, fit, gọi LLM hoặc mở CSV test; không thay thế kiểm chứng runtime mới. |

## Bốn thí nghiệm và quyết định mô hình

Đọc phần tổng hợp cuối notebook 03 cho baseline và tuning; notebook 04 cho baseline ensemble và tuned ensemble. Hình/bảng dùng saved metrics và evidence đã kiểm; xem [ML_EXPERIMENTS](../docs/ML_EXPERIMENTS.md) và [figure manifest](../reports/academic_review_20261111/figure_manifest.json) ghi nguồn/checksum.

Hard tuned LR+SVC+KNN là ứng viên có validation Macro F1 cao nhất đã quan sát. **LR tuned C=2 được owner chọn làm model ứng dụng trước final test**, phù hợp API nghiên cứu cần Top 3 và chi phí inference thấp. Final test đánh giá ba ứng viên định trước, không dùng để chọn lại tham số, voting policy hoặc model triển khai. Xem [decision record](../docs/MODEL_SELECTION_RATIONALE.md).

Notebook 05 kiểm năm baseline, không phải năm tuned và không phải API deployment. LR/RF/KNN/BernoulliNB dùng `predict_proba()` thật; LinearSVC không có probability/Top 3 giả. Điểm model chưa calibration không phải xác suất mắc bệnh. Timing ví dụ không phải cam kết latency website.

## Thứ tự đọc và execution gates

Thứ tự nghiên cứu: **00 → 01 → 02 → 03 → 04 → 05 → 06**. Khi chỉ kiểm setup Colab, mở `colab_smoke_test.ipynb` độc lập; không chạy training trước để lấy biến `session`.

Đọc 07 sau khi hiểu extraction contract. Chọn Colab kernel rồi chạy các cell theo thứ tự; notebook tự lấy source GitHub nếu chưa có, cài requirements-nlp-research.txt trong runtime Colab và chuẩn bị embedding public đúng revision/checksum. Kết quả/biểu đồ được ghi vào reports/nlp_research_<timestamp>/ và hiển thị từ cùng run. Không cần mount Drive hay upload từng module. Python local dùng môi trường NLP riêng có requirements tương ứng; không cài vào API LR. Đặt RUN_RESEARCH=False nếu chỉ xem snapshot lịch sử. Reserved NLP v1 đã được quan sát, nên rerun không phải đánh giá độc lập mới.

| Notebook / gate | Giá trị hiện có trong source | Ý nghĩa và điểm dừng |
|---|---|---|
| 02: `RUN_HISTORICAL_INSPECTION` | `False` | Phụ lục lịch sử tắt; không bật để tái tạo Phase 2 khi đọc kết quả. |
| 03: `RUN_HYPERPARAMETER_TUNING` | `True` | Owner đã bật có chủ đích, được bảo toàn. Không chạy cell tuning để xem bảng. Gate tuning False cũng không ngăn baseline fit khi thiếu checkpoint. |
| 04: `RUN_TUNED_ENSEMBLE` | `False` | Không bật chỉ để xem outputs. Các cell ensemble có thể tạo prediction validation và run artifacts nếu thực thi. |
| 06: `RUN_FINAL_LOCKED_TEST` / `OWNER_AUTHORIZATION` | `False` / chuỗi rỗng | Viewer từ chối gate True; chỉ đọc completed results. Không cấp authorization, xóa execution marker hoặc gọi lại evaluation. |
| 07: `RUN_RESEARCH` / `RUN_SEMANTIC` | `True` / `True` | Chạy extraction NLP; Colab tự chuẩn bị source/dependencies và embedding public đúng revision. Bảng/hình đọc run vừa hoàn tất. Không fit disease classifier. |

Notebook 05 có thể gọi inference/benchmark khi chạy, dù không fit; không cần chạy lại để trình bày. Notebook 06 chỉ hiển thị completed bundle đúng checksum sau setup/preflight hợp lệ; thiếu hoặc partial thì dừng, không tự resume hay dựng kết quả thay thế. Một số Markdown/output và tài liệu cũ mô tả trạng thái lịch sử; bảng gate trên đối chiếu **source hiện tại**, không thay đổi outputs đó.

## Môi trường Colab / Drive

1. Theo [HANDOVER_GUIDE](../docs/HANDOVER_GUIDE.md), publish **payload source nhỏ đầy đủ** bằng helper hiện có. Code Windows không tự xuất hiện trong VM Colab; không upload từng script riêng, không cần source ZIP trên Drive.
2. Chọn Colab kernel trong VS Code và mount Drive trên đúng kernel/server. Kết nối kernel chưa đồng nghĩa đã mount Drive.
3. Storage canonical: `/content/drive/MyDrive/ML_Projects/disease-prediction-ml`. Shared bootstrap xác minh source/digest rồi thực thi từ `/content/disease-prediction-ml-runtime`; không sửa canonical path hoặc bỏ checksum để xử lý lỗi.
4. Sau runtime reset, chạy setup/import/session được chỉ định trong notebook. `ColabTraining.open(RUNTIME)` tạo session mới mà không cần chạy notebook 03 hay fit model.
5. Dùng các cell setup/import/integrity của smoke notebook để kiểm môi trường. Smoke không chứng minh checkpoint đã reload, toàn bộ notebook chạy lại thành công hoặc cloud đã đồng bộ source mới.

Cấu hình chung: [runtime.json](../configs/runtime.json), [Phase 2 integrity](../configs/phase2_integrity.json). Thiếu source, dependency, checkpoint hoặc sai identity phải xử lý đúng lỗi; không fallback baseline, thay manifest hoặc training để lấp chỗ thiếu. Runtime mới cần kiểm thực tế, không suy từ tests offline hay outputs cũ.

## Bảo toàn kết quả và tài liệu liên quan

Không sửa code cell đã chạy rồi giữ output cũ, xóa outputs/execution counts, đổi thứ tự cell phụ thuộc hoặc Run All để làm mới phần trình bày. Không mở lại locked test, train/tune, gọi LLM hay sửa checkpoint khi chỉ đọc tài liệu. [Bằng chứng bảo toàn](../reports/academic_review_20261111/preservation_verification.json) và [cell candidates](../reports/academic_review_20261111/cell_candidates.json) lưu đối chiếu lịch sử; candidate chưa phải phê duyệt xóa.

- [Kiến trúc hệ thống](../docs/SYSTEM_ARCHITECTURE.md): ranh giới notebook, API và chatbot.
- [Các thí nghiệm ML](../docs/ML_EXPERIMENTS.md): kết quả và giới hạn nghiên cứu.
- [Hướng dẫn triển khai](../docs/DEPLOYMENT_GUIDE.md): website/API local, môi trường và artifact bắt buộc.
- [Hướng dẫn bàn giao](../docs/HANDOVER_GUIDE.md): source, Drive, notebook safety và đồng bộ.
- [Nhật ký kỹ thuật](../docs/DEVELOPMENT_LOG.md): tiến trình và giới hạn kiểm chứng.

Chỉ mục đối chiếu với 9 notebook trong repository ngày 2026-11-11. Notebook 00–06 và smoke test giữ nguyên byte; 07 mới có gates tắt và không thay scientific results của disease classification.
