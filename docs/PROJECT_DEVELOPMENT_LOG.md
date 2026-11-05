# Nhật ký kỹ thuật — đường dẫn tương thích

Nội dung hiện hành: [Nhật ký kỹ thuật](DEVELOPMENT_LOG.md). Không dùng bản lịch sử để suy trạng thái hiện tại.

Bản chi tiết trước hợp nhất: [PROJECT_DEVELOPMENT_LOG.md](archive/planning/PROJECT_DEVELOPMENT_LOG.md). Trang này giữ các anchors cũ để notebook, scripts và reports không cần sửa.

Nhật ký gốc trong archive được giữ nguyên byte, kể cả liên kết lịch sử; cách tra cứu được ghi trong [inventory](README.md#archive-integrity).

<a id="nhật-ký-phát-triển-dự-án"></a>
<a id="cách-đọc-và-cập-nhật"></a>
<a id="trạng-thái-tại-lần-rà-soát-2026-10-28"></a>
<a id="1-phase-1--dataset-audit-lịch-sử-tái-dựng"></a>
<a id="2-phase-1--eda-và-tính-phù-hợp-lịch-sử-tái-dựng"></a>
<a id="3-portability-ban-đầu--localremote-và-import-source-lịch-sử-tái-dựng"></a>
<a id="4-phase-2--inspection-và-hai-cột-regurgitation-lịch-sử-tái-dựng"></a>
<a id="5-phase-2--rà-soát-lớp-hiếm-chọn-ngưỡng-10-lịch-sử-tái-dựng"></a>
<a id="6-phase-2--pipeline-chia-group-và-khóa-artifact-lịch-sử-tái-dựng"></a>
<a id="7-colabdrive--các-lỗi-đồng-bộ-và-output-lịch-sử-tái-dựng"></a>
<a id="8-canonical-drive-runtime--đã-kiểm-smoke-thật-mốc-ghi-nhận-2026-10-27"></a>
<a id="9-phase-3--sẵn-sàng-code-năm-baseline-lịch-sử-tái-dựng-training-chờ-xác-minh"></a>
<a id="10-2026-10-28--điều-chỉnh-tài-liệu-theo-phản-hồi-giảng-viên"></a>
<a id="11-2026-10-28--kiểm-tra-thay-đổi-tài-liệu"></a>
<a id="12-2026-10-28--preflight-notebook03-không-training"></a>
<a id="13-2026-10-28--post-training-audit-chờ-artifact-thực-của-colab"></a>
<a id="14-2026-10-28--chuẩn-bị-kiểm-artifact-trực-tiếp-trong-colab"></a>
<a id="15-2026-10-28--hoàn-tất-post-training-audit-từ-bằng-chứng-colab"></a>
<a id="16-2026-10-28--triển-khai-phase-4-từ-checkpoint-chờ-validation-colab"></a>
<a id="17-2026-10-28--hoàn-tất-phase-4-từ-kết-quả-colab"></a>
<a id="18-2026-10-28--chốt-biện-luận-phase4-và-thiết-kế-phase5-llm-api"></a>
<a id="19-2026-10-28--hoàn-thiện-ca-nhiều-lượt-quality-gate-và-kế-hoạch-đo-api"></a>
<a id="20-2026-10-28--kiểm-inference-có-cấu-trúc-trước-phase5a-chờ-thực-thi-colab"></a>
<a id="21-2026-10-29--hoàn-tất-structured-inference-từ-bằng-chứng-colab"></a>
<a id="ca-validation-có-nhãn-thật"></a>
<a id="ca-giả-lập-không-có-ground-truth"></a>
<a id="probability--top3-và-vấn-đề-trình-bày"></a>
<a id="thời-gian-một-mẫu-sau-load"></a>
<a id="22-2026-10-29--phase5b-external-provider-adapter-guard-và-hội-thoại-offline"></a>
<a id="23-2026-10-29--tuning-train-only-trong-notebook0304-chưa-chạy-thí-nghiệm-thật"></a>
<a id="24-2026-10-29--post-tuning--phase5b-source-audit-chờ-bằng-chứng-drive"></a>
<a id="25-2026-10-29--phân-tích-học-thuật-và-lựa-chọn-sau-post-tuning-audit-colab"></a>
<a id="26-2026-10-29--final-ml-evidence-gaps-và-kế-hoạch-bàn-giao-workspace"></a>
<a id="27-2026-10-29--ml-selection-decision-record-và-chuẩn-bị-bàn-giao"></a>
<a id="28-2026-10-30--khóa-final-test-protocol-và-chuẩn-bị-notebook06"></a>
<a id="29-2026-10-30--audit-local-code--drive-data-và-hợp-đồng-hai-zip"></a>
<a id="30-2026-10-30--implement-packaging-an-toàn-và-unified-runtime"></a>
<a id="31-2026-10-30--clean-runtime-smoke-cho-release-hiện-có-chưa-có-bằng-chứng-colab"></a>
<a id="311-2026-10-30--hai-lỗi-thiếu-source-trên-kernel-chờ-chẩn-đoán-chỉ-đọc"></a>
<a id="312-2026-10-30--đã-thấy-seed-trên-vm-drive-chưa-mount"></a>
<a id="32-2026-10-30--sửa-smoke06-prerequisite-rõ-ràng-session-độc-lập-gate-test-tắt"></a>
<a id="bảng-lỗi-và-bằng-chứng-trước-sửa"></a>
<a id="bản-sửa-hiện-hành"></a>
<a id="kiểm-chứng"></a>
<a id="bằng-chứng-tiếp-theo--stop"></a>
<a id="321-2026-10-30--colab-đã-mount-bootstrap-drive-không-khớp-api-release"></a>
<a id="33-2026-10-30--final-evaluation-closeout-và-prediction-api-local"></a>
<a id="quyết-định-và-bằng-chứng-final-evaluation"></a>
<a id="notebook06-lưu-hành"></a>
<a id="prediction-api"></a>
<a id="kiểm-thử-và-blocker"></a>
<a id="34-2026-10-30--local-web-mvp-phase5b-chat-adapter-và-smoke-live-tách-biệt"></a>
<a id="điều-kiện-thực-và-kết-quả-theo-từng-giai-đoạn"></a>
<a id="code-ứng-dụng-và-bảo-toàn-kiến-trúc"></a>
<a id="tests-và-regression-review"></a>
<a id="phạm-vi-dừng"></a>
<a id="35-2026-10-30--sửa-hướng-dẫn-interpreter-cho-gemini-smoke-python3119"></a>
<a id="36-2026-10-30--qualification-windows-python31317-cho-lr-tuned-chờ-reference"></a>
<a id="37-2026-10-30--đối-chiếu-reference-lr-colab31318-chờ-checksum-phía-colab"></a>
<a id="38-2026-10-30--windows31317-approved-real-lr-tuned-prediction-api-pass"></a>
<a id="39-2026-10-30--gemini-chat-debug-actual-timeout20-bổ-sung-chẩn-đoán-http-an-toàn"></a>
<a id="cập-nhật-bằng-chứng-timeout60-và-transport-trace"></a>
<a id="root-cause-xác-minh-từ-request-thứ3-serving-schema-state-explosion"></a>
<a id="owner-cho-phép-kiểm-mitigation-thêm-một-request"></a>
<a id="mitigation-minimum-không-pass-wire-code-catalog-giữ-đủ375"></a>
<a id="wire-codes-live-timeout20-và-http503-high-demand-chưa-pass"></a>
