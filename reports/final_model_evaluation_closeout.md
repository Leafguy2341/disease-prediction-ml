# Final ML evaluation — closeout 2026-10-30

**VERIFIED qua packet read-only từ kernel Colab của owner**, không phải agent truy cập Drive trực tiếp.
Owner đã duyệt LR tuned C=2 trước test; lựa chọn đó giữ nguyên. Hard tuned vẫn best observed
validation Macro F1. Ba ứng viên được freeze trước khi mở test; không tối ưu lại từ kết quả test.

| Ứng viên | Validation Macro F1 | Test Macro F1 | Test Accuracy | Test Weighted F1 | Predicted classes | F1=0 classes |
|---|---:|---:|---:|---:|---:|---:|
| LR baseline | 0.7878081402467481 | 0.7958306745796887 | 0.8426922254685384 | 0.8428343938933989 | 560 | 28 |
| LR tuned C=2 | 0.7931543818638241 | 0.808163486172862 | 0.8440818071688163 | 0.8449466206008978 | 567 | 22 |
| Hard tuned LR+SVC+KNN | 0.7965170720239344 | 0.8059813671672197 | 0.842834746668567 | 0.84360287513484 | 567 | 22 |

Metric chính fixed587 nhãn/zero_division=0; 28.066 test rows,25.128 groups,375features,
không thiếu nhãn trong y_true. Macro Precision/Recall và mọi metric gốc nằm trong
[evidence JSON](../artifacts/metadata/final_evaluation_audit/colab_evidence.json).
Metrics đã tính lại từ saved predictions, đối chiếu original results.json và comparison.csv với atol1e-12;
không đọc lại test CSV hoặc gọi model predict trong closeout.

Canonical Drive bundle: `artifacts/metadata/final_evaluation/049ee0aa3c290798/`.
`read_completed()` kiểm inventory11 file, từng checksum/size và protocol.
Manifest SHA-256: `f1ad195e1e46154d7a29a421e80387bfa76e494f4df771cede240f882d0b754a`.
Protocol SHA-256: `049ee0aa3c2907985c3d3a03ed222b1d6e1efb5921bbbc2d04ec0dea9baa8947`.
Packet SHA-256: `102845056236bfe3855962cd1717ece4402a958cc6ce593540ab1ccab4f34131`.
Quá trình audit kiểm bốn checkpoint members theo frozen hashes/fit identities/source pins;
guards test access/fit/protected write đều0. Packet không deserialize checkpoint.

Saved execution ghi test_loader_calls=1, models_fitted=0, model_selection_from_test=false.
Có30 DeprecationWarning cùng nội dung datetime.utcnow; không có ConvergenceWarning trong warning list này.
Các bảng per-class/transitions/group và figure đã lưu trong bundle/notebook được giữ nguyên; không tạo hình mới.
Marker thực thi giữ nguyên. Notebook06 source lưu hành tắt gate, authorization trống, chỉ replay completed bundle.

LR tuned có test Macro F1 cao nhất trong ba ứng viên, nhưng đây là kết quả mô tả held-out split,
không chứng minh ý nghĩa thống kê, calibration hoặc hiệu quả lâm sàng. Dữ liệu synthetic, nhãn xung đột
có thể chung symptom vector; Phase1 đã EDA toàn CSV. Chưa kiểm generalization với input LLM hoặc bệnh nhân thật.
Checkpoint đã được chọn trước test, không thay quyết định/hyperparameters/voting policy sau test.

Prediction API mới dùng đúng LR tuned, **real Windows checkpoint reload/predict NOT VERIFIED**:
weights chỉ có trên Drive và môi trường local hiện khác identity. Xem [hướng dẫn API](../docs/LOCAL_PREDICTION_API.md).
