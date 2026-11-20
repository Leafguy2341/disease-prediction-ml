# Báo cáo Dataset Audit

Kết quả tính trên toàn bộ `Disease and symptoms dataset.csv`; không lấy mẫu. SHA-256: `8de90603ebada467fc2703db2ee4292856e52d64e94982ef926df22fa0c21320`.
Số dòng dữ liệu trong bảng ánh xạ là 1-based, không tính header CSV. `pattern_id` chỉ có ý nghĩa kèm fingerprint và thứ tự cột của tệp này.

## Nguồn và phạm vi xác minh

Nguồn ứng viên: [Disease and symptoms dataset 2023](https://data.mendeley.com/datasets/2cxccsxydc/1), DOI `10.17632/2cxccsxydc.1`, contributor Bran Stark, version 1, công bố 2025-03-03, giấy phép CC BY 4.0; tra cứu ngày 2026-10-21.
Tên tệp, schema và số lớp/đặc trưng khớp mô tả. Chưa có checksum nhà xuất bản hoặc lịch sử tải xuống để xác nhận đây là bản gốc không chỉnh sửa.
Nhà xuất bản mô tả dữ liệu sinh nhân tạo. Không có căn cứ xem mỗi dòng là một bệnh nhân thật; tuyên bố về tỷ lệ mắc bệnh và độ nặng chưa được kiểm chứng độc lập.
Trang nguồn không cung cấp quy trình kiểm định lâm sàng hoặc mã sinh dữ liệu đủ để tái tạo trong nội dung đã xem.

## Kết quả cấu trúc và chất lượng

| Chỉ số | Giá trị |
| --- | --- |
| rows | 246945 |
| columns | 378 |
| features | 377 |
| target | diseases |
| classes | 773 |
| missing_cells | 0 |
| missing_target_rows | 0 |
| blank_target_rows | 0 |
| invalid_binary_cells | 0 |
| binary_complete | True |
| constant_features | 49 |
| near_constant_features_including_constant | 227 |
| exact_duplicate_excess_rows | 57298 |
| rows_in_exact_duplicate_groups | 94067 |
| unique_feature_vectors | 169888 |
| repeated_pattern_groups | 44287 |
| rows_in_repeated_patterns | 121344 |
| repeated_pattern_excess_rows | 77057 |
| conflicting_pattern_groups | 12634 |
| rows_in_conflicting_patterns | 39728 |
| min_class_samples | 1 |
| max_class_samples | 1219 |
| median_class_samples | 168.0 |
| classes_with_lt5_rows | 52 |
| classes_with_lt5_patterns | 115 |
| classes_with_one_pattern | 46 |
| name_leakage_candidates | [] |
| normalized_label_collisions | 0 |
| empirical_pattern_majority_ceiling | 0.9162080625240439 |
| recommendation | CONDITIONAL GO |

`exact_duplicate_excess_rows` = số dòng dư sau khi giữ một dòng cho mỗi cặp (vector, nhãn).
`repeated_pattern_excess_rows` = số dòng dư sau khi giữ một dòng cho mỗi vector, bỏ qua nhãn.
`rows_in_repeated_patterns` tính tất cả dòng thuộc nhóm vector có kích thước >1, gồm cả bản đầu tiên.
`near_constant_features_including_constant` dùng tần suất giá trị chiếm ưu thế ≥99%; đây chỉ là cờ mô tả, chưa loại cột.

## Nhãn, ý nghĩa đặc trưng và leakage

Nhãn `diseases` được tách khỏi X khi phân tích vector triệu chứng. Bảng `audit_features.csv` chứa tên, dtype gốc, miền giá trị, tỷ lệ thiếu, tần suất, cờ hằng và gần hằng của từng cột.
Từ điển chuyên môn chưa được xác minh: tên cột tiếng Anh gợi ý triệu chứng, không chứng minh độ tin cậy y khoa.
Các cột nghi vấn do tên: []. Không có cờ theo tên không đồng nghĩa không có leakage.
`audit_alias_candidates.csv` kiểm tra hậu tố như `.1`; không tự gộp các tên giống nhau. `audit_duplicate_columns.csv` chỉ báo các cột có vector giá trị giống hệt, gồm nhóm cột hằng.
Không có patient ID, thời gian hay cơ sở khám để kiểm tra trùng bệnh nhân hoặc chia theo bệnh viện/thời gian. Quan hệ đặc trưng–nhãn quá đặc hiệu cần xét cùng cơ chế sinh nhân tạo, chưa thể kết luận leakage nhân quả.

## Đánh giá ban đầu: CONDITIONAL GO

Có cấu trúc phân loại có giám sát với 773 lớp. Tính đại diện phải đánh giá bằng **số vector độc lập theo lớp**, không chỉ số dòng.
Có 12,634 vector mang nhiều nhãn và 115 lớp có dưới 5 vector.
Mức majority theo vector trên toàn bộ tệp = 0.9162080625240439; đây là giới hạn ghi nhớ thực nghiệm của bộ phân loại tất định trên chính các dòng đã quan sát, không phải độ chính xác kiểm định hoặc giới hạn quần thể.
Kết luận ban đầu dành cho nghiên cứu học phần; các điều kiện cụ thể và phân tích phân tách sẽ được cập nhật trong EDA. Không suy rộng sang chẩn đoán lâm sàng.

## Ngăn leakage và hướng xử lý tiếp theo

Không chia ngẫu nhiên theo dòng khi vector lặp. Giữ mọi dòng có cùng vector trong cùng một group cho mọi phép chia và CV, kể cả khi khác nhãn.
Kiểm tra số group của từng lớp trước khi đề xuất số fold. Lớp có một group không thể đồng thời có train và test độc lập; không tự nhân bản, bỏ lớp hoặc hợp nhất bệnh.
Chưa chọn quy tắc cho xung đột nhãn; cần quyết định trên tập phát triển và tài liệu nguồn, báo cáo ảnh hưởng nếu loại/gộp.
Imputation, scaling, feature selection và PCA sau này chỉ được fit trên train/CV training fold. Test cuối khóa riêng, không dùng chọn siêu tham số.

## Giao diện tiếng Việt

Chưa có ánh xạ Việt–Anh, kiểm định từ đồng nghĩa/phủ định hay dữ liệu hội thoại. Giá trị 0 không chứng minh triệu chứng đã được hỏi và phủ nhận; không tự mã hóa mọi thông tin chưa nhắc đến thành âm tính.
Các cặp gần nghĩa và hậu tố `.1` cần được rà soát trước khi xây từ điển. ML sẽ dự đoán nhãn; LLM chỉ hỗ trợ hiểu tiếng Việt, hỏi rõ và giải thích. Phase 1 chưa triển khai giao diện hoặc chatbot.
