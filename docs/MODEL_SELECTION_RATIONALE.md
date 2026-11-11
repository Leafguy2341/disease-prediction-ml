# ML và quyết định chọn mô hình — đường dẫn tương thích

Nội dung hiện hành: [ML và quyết định chọn mô hình](ML_EXPERIMENTS.md). Không dùng bản lịch sử để suy trạng thái hiện tại.

Bản chi tiết trước hợp nhất: [MODEL_SELECTION_RATIONALE.md](archive/ml/MODEL_SELECTION_RATIONALE.md). Trang này giữ các anchors cũ để notebook, scripts và reports không cần sửa.

<a id="phân-tích-mô-hình-và-cơ-sở-lựa-chọn"></a>
<a id="decision-record-lựa-chọn-ml"></a>
<a id="bài-toán-dữ-liệu-và-căn-cứ"></a>
<a id="cấu-hình-và-tác-động-tuning"></a>
<a id="ensemble-trước-và-sau-tuning"></a>
<a id="bất-định-và-chi-phí-đã-đo"></a>
<a id="đề-xuất-phê-duyệt-và-giới-hạn"></a>
<a id="dữ-liệu-và-giao-thức-giữ-nguyên"></a>
<a id="giả-định-lợi-ích-giới-hạn-và-tài-nguyên"></a>
<a id="vì-sao-chọn-bernoullinb-và-phân-biệt-các-biến-thể"></a>
<a id="voting-và-các-phương-án-ngoài-phạm-vi-ban-đầu"></a>
<a id="hai-trực-quan-hóa-dự-kiến-sau-huấn-luyện"></a>
<a id="hyperparameter-tuning-có-kiểm-soát"></a>
<a id="search-space-chốt-trước-khi-chạy"></a>
<a id="cv-scoring-và-selection"></a>
<a id="tài-nguyên-và-resume"></a>
<a id="namespace-và-bảo-toàn-baseline"></a>
<a id="chạy-trên-colab-trong-vs-code"></a>
<a id="bằng-chứng-hiện-có-và-giới-hạn"></a>
<a id="phân-tích-học-thuật-và-lựa-chọn-hiện-tại"></a>
<a id="bằng-chứng-phạm-vi-và-trạng-thái-lựa-chọn"></a>
<a id="giao-thức-và-cách-đọc-kết-quả"></a>
<a id="cấu-hình-baseline-chính-xác"></a>
<a id="chất-lượng-năm-baseline-trên-cùng-validation"></a>
<a id="fit-dự-đoán-và-bộ-nhớ-baseline"></a>
<a id="logistic-regression-baseline-tuyến-tính-xác-suất"></a>
<a id="linearsvc-đối-chứng-tuyến-tính-theo-margin"></a>
<a id="random-forest-đối-chứng-phi-tuyến-có-giới-hạn-tài-nguyên"></a>
<a id="knn-tham-chiếu-hình-học-của-vector-nhị-phân"></a>
<a id="bernoullinb-tham-chiếu-xác-suất-sinh-cho-indicator"></a>
<a id="timing-một-mẫu-sau-load-bằng-chứng-riêng"></a>
<a id="phân-tích-tuning-theo-từng-họ-mô-hình"></a>
<a id="ensemble-baseline-kết-quả-và-cơ-chế-giải-thích"></a>
<a id="ensemble-tuned-kết-quả-đã-kiểm-và-giới-hạn-giải-thích"></a>
<a id="so-sánh-đa-tiêu-chí-cho-apichatbot"></a>
<a id="bất-định-hình-minh-họa-và-điều-kiện-chốt-lựa-chọn"></a>
<a id="bằng-chứng-bổ-sung-ml-gaps-và-đề-xuất-để-nhóm-duyệt"></a>
<a id="final-locked-test-protocol-2026-10-30"></a>
<a id="ba-ứng-viên-và-bốn-pipeline-đã-fit"></a>
<a id="identity-test-và-scoring-trước-khi-truy-cập-payload"></a>
<a id="phân-tích-mô-tả-đã-định-trước"></a>
<a id="gate-publication-và-giới-hạn"></a>


## Quyết định ứng dụng hiện hành — 2026-11-11

Các bảng khoa học, bốn thí nghiệm và giải thích lựa chọn được gom tại [ML_EXPERIMENTS](ML_EXPERIMENTS.md). LR tunedC2 vẫn là default đã duyệt trước final test; hard tunedLR+SVC+KNN vẫn best observed validation Macro F1. Website có ba registry IDs nhưng chỉ bật model đủ điều kiện runtime. Không dùng test để chọn lại model. Xem [hợp đồng triển khai](DEPLOYMENT_GUIDE.md#three-model-website) cho trạng thái qualification; không lặp lại bảng metrics ở trang redirect này.
