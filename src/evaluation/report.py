"""Evidence-based Vietnamese suitability assessment and future research protocol."""
from src.data.io import markdown_table
from src.data.paths import output_paths


def write_eda_report(root, audit, eda):
    a, e = audit["summary"], eda["summary"]
    counts = audit["class_distribution"]
    freq = eda["symptom_frequency"]
    positive = freq[freq["present_count"] > 0]
    common = counts.iloc[0]
    rare = counts.sort_values(["samples", "disease"]).head(15)
    ceiling = a["empirical_pattern_majority_ceiling"]
    recommendation = a["recommendation"]
    note = f"""# EDA và Dataset Suitability Assessment

## Phạm vi và tính tái lập

Kết quả mô tả tính trên toàn bộ **{a['rows']:,} dòng × {a['features']} triệu chứng**, nhãn `{a['target']}` với **{a['classes']} lớp**. Không huấn luyện, lựa chọn đặc trưng, impute, scale, PCA hoặc chia train/test trong Phase 1.
Các bảng đầy đủ ở `reports/tables/`; 8 hình PNG/SVG ở `reports/figures/`. Tham số và seed nằm trong `configs/phase1.json`, fingerprint và phiên bản package nằm trong `artifacts/metadata/dataset_manifest.json`.

Nguồn ứng viên: [Disease and symptoms dataset 2023, Mendeley Data v1](https://data.mendeley.com/datasets/2cxccsxydc/1), DOI `10.17632/2cxccsxydc.1`, contributor Bran Stark, công bố 03/03/2025, CC BY 4.0 (tra cứu 21/10/2026).
Nhà xuất bản mô tả dữ liệu sinh nhân tạo. Tệp cục bộ khớp tên, schema và số lớp/đặc trưng; chưa có checksum nhà xuất bản/lịch sử tải để chứng minh danh tính bản gốc.
Không có bằng chứng độc lập về tính đại diện bệnh nhân, tỷ lệ mắc bệnh hoặc độ nặng. Không diễn giải tần suất trong CSV thành dịch tễ học.

## A. Phân bố nhãn và support

Mỗi lớp có tối thiểu **{a['min_class_samples']}**, tối đa **{a['max_class_samples']:,}**, trung vị **{a['median_class_samples']:g}** dòng; tỷ lệ max/min = **{e['imbalance_max_min_ratio']:,.0f}:1**.
Lớp nhiều dòng nhất là `{common['disease']}` ({int(common['samples']):,} dòng). Tỷ trọng lớp lớn nhất = **{e['majority_class_fraction']:.2%}**, 20 lớp lớn nhất = **{e['top20_class_fraction']:.2%}**; không nên đánh giá mất cân bằng chỉ từ tỷ lệ max/min.
Có **{a['classes_with_lt5_rows']}** lớp dưới 5 dòng, **{a['classes_with_lt5_patterns']}** lớp dưới 5 vector độc lập và **{a['classes_with_one_pattern']}** lớp chỉ một vector. Nhân bản thêm dòng không tạo thêm thông tin để đánh giá các lớp này.

{markdown_table(eda['class_quantiles'])}

Một số lớp ít dòng (bảng đầy đủ: `audit_class_distribution.csv`):

{markdown_table(rare[['disease', 'samples']])}

**Hình 01–02:** histogram, đường hạng với trục log và hai nhóm 15 nhãn tránh chồng hàng trăm nhãn. Chúng cho thấy cả chênh lệch kích thước lẫn đuôi lớp hiếm, chưa chứng minh kỹ thuật cân bằng nào sẽ cải thiện điểm.

## B. Triệu chứng, đồng xuất hiện và dư thừa cột

Cả {a['features']} đặc trưng quan sát được đều là 0/1; **{a['missing_cells']}** ô thiếu và **{a['invalid_binary_cells']}** ô ngoài miền nhị phân.
Có **{e['always_absent_symptoms']}** triệu chứng luôn vắng, **{e['always_present_symptoms']}** triệu chứng luôn có; **{a['near_constant_features_including_constant']}** cột có giá trị trội ≥99%, gồm {a['constant_features']} cột hằng.
Cột hiếm có thể liên quan lớp hiếm; không tự xóa tất cả cột gần hằng. Dữ liệu không có từ điển đủ để suy ra cách xác nhận âm tính hoặc thiếu triệu chứng.

Triệu chứng phổ biến (tần suất chỉ mô tả tập sinh nhân tạo):

{markdown_table(freq[['feature', 'present_count', 'present_fraction']].head(10))}

Triệu chứng hiếm **có xuất hiện** (cột bằng 0 được liệt kê riêng trong audit):

{markdown_table(positive.sort_values(['present_count', 'feature'])[['feature', 'present_count']].head(10))}

Số triệu chứng hoạt động: trung bình **{e['active_symptoms_mean']:.2f}**, trung vị **{e['active_symptoms_quantiles']['0.5']:g}**, min/max **{e['active_symptoms_quantiles']['0.0']:g}/{e['active_symptoms_quantiles']['1.0']:g}**; có **{e['single_symptom_rows']:,}** dòng chỉ một triệu chứng và **{e['all_zero_rows']:,}** dòng toàn 0.

**Hình 03–05:** tần suất, số triệu chứng/dòng và quan hệ của 15 triệu chứng phổ biến nhất. Jaccard đo chồng lấp khi xuất hiện; phi là Pearson cho biến nhị phân. Phi không xác định cho cột hằng, được lưu NA thay vì gán 0. Không suy ra nhân quả hoặc diễn giải mức độ nặng từ đồng xuất hiện.
Có **{e['high_absolute_correlation_pairs']}** cặp có |phi| ≥0,8; **{e['high_correlation_pairs_joint_ge10']}** trong số đó có ít nhất 10 dòng đồng xuất hiện. Những cặp hiếm vẫn có thể cho tương quan cao; bảng kèm `joint_rows` để xem support.
`regurgitation` và `regurgitation.1` được kiểm tra trong bảng alias; hậu tố tên không đủ làm cơ sở gộp tự động.

## C. Quan hệ triệu chứng–bệnh và khả năng phân tách

**Hình 06:** chọn bốn lớp nhiều dòng nhất cộng cặp profile gần nhất có mỗi lớp ≥20 dòng, ≥5 vector; chỉ minh họa tối đa 6 lớp và 20 triệu chứng. Bảng `eda_class_profiles.csv` chứa toàn bộ tỷ lệ P(symptom=1 | disease).
**Hình 07:** cosine của profile trung bình. Hai lớp có profile gần nhau có thể vẫn phân biệt bằng tương tác; các lớp thưa có profile ước lượng thiếu ổn định. Đây là thống kê mô tả, không phải đánh giá mô hình.

{markdown_table(eda['supported_similar_diseases'].head(8))}

Có **{e['single_class_symptoms']}** triệu chứng chỉ xuất hiện trong một lớp, **{e['single_class_symptoms_support_ge5']}** trong số đó có ≥5 dòng. Tính đặc hiệu trên tệp không đồng nghĩa triệu chứng đủ độ nhạy, không chứng minh tính đặc hiệu lâm sàng hoặc khả năng tổng quát hóa. Xem `eda_single_class_features.csv` và `eda_class_always_symptoms.csv`.
Mẫu rất đặc hiệu, số triệu chứng ít và việc lặp có thể tạo shortcut từ cơ chế sinh dữ liệu. Đây là dấu hiệu cần điều tra; chưa có thí nghiệm để kết luận mô hình sẽ đạt điểm cao.

## D. Mẫu lặp, xung đột và giới hạn thông tin

Có **{a['unique_feature_vectors']:,}** vector khác nhau; **{a['repeated_pattern_excess_rows']:,} ({e['excess_repeated_patterns_fraction']:.2%})** dòng dư nếu giữ một dòng/vector. Tổng số dòng thuộc các nhóm vector lặp, tính cả dòng đầu, là **{a['rows_in_repeated_patterns']:,} ({e['rows_in_repeated_patterns_fraction']:.2%})**.
Nếu xét cả nhãn thì có **{a['exact_duplicate_excess_rows']:,}** dòng dư. Có **{a['conflicting_pattern_groups']:,}** vector mang nhiều nhãn, liên quan **{a['rows_in_conflicting_patterns']:,} ({e['conflicting_rows_fraction']:.2%})** dòng.

**Hình 08:** số dòng và số vector theo lớp khác nhau, cho thấy kích thước hiệu dụng không thể đo chỉ bằng số dòng.
Giới hạn ghi nhớ thực nghiệm của bộ phân loại tất định chỉ dùng triệu chứng, với trọng số mỗi dòng trên đúng tệp này, là **{ceiling:.2%}**: tổng số dòng của nhãn đông nhất mỗi vector chia tổng số dòng.
Đây **không** phải test accuracy, kỳ vọng hiệu năng hay giới hạn cho dữ liệu mới. Việc lọc xung đột hoặc thay đổi trọng số sẽ thay đổi con số này.
Các xung đột có thể phản ánh triệu chứng chưa đủ phân biệt nhiều bệnh hoặc nhiễu sinh dữ liệu; không thể tự quyết nhãn nào đúng.

{markdown_table(eda['conflict_examples'][['pattern_id', 'active_symptoms', 'rows', 'distinct_labels']].head(5))}

## E. Dataset Suitability Assessment: **{recommendation}**

**Phạm vi được hỗ trợ:** nghiên cứu học phần về phân loại trên bộ triệu chứng nhị phân sinh nhân tạo, sau khi chốt cách xử lý xung đột, lớp ít group và chia nhóm. Cấu trúc có nhãn, miền giá trị hợp lệ và {a['unique_feature_vectors']:,} vector cho phép tiếp tục thí nghiệm dưới các điều kiện này.

**Điều kiện phải giải quyết:**

1. Xác minh xuất xứ, giấy phép và cơ chế sinh nếu lấy được tài liệu gốc; phân biệt phát hiện từ file và mô tả nhà xuất bản.
2. Định nghĩa chính sách cho {a['conflicting_pattern_groups']:,} vector xung đột: giữ và báo cáo giới hạn thông tin, cách ly, hoặc đổi bài toán có lý do. Không tự chọn nhãn bằng thông tin toàn bộ test.
3. Quyết định phạm vi đánh giá cho {a['classes_with_one_pattern']} lớp chỉ một vector và lớp dưới số group cần thiết; không thể yêu cầu train/test độc lập cho mọi lớp hiện tại. Muốn giữ đầy đủ {a['classes']} lớp có đánh giá độc lập cần bổ sung dữ liệu/vector phù hợp hoặc chấp nhận lớp không có test độc lập và báo cáo rõ.
4. Tất cả dòng có cùng vector phải nằm trong cùng group ở mọi phép chia, kể cả khác nhãn. Kiểm tra không giao group sau khi chia; không áp dụng phép chia phân tầng theo dòng như đánh giá chính.
5. Chưa thể dùng để khẳng định hiệu quả chẩn đoán thực tế. Không có đoàn hệ bệnh nhân xác minh, biến thời gian/cơ sở, lịch sử bệnh hay kiểm định ngoài.

## F. Ưu tiên cho Phase 2 — chỉ khuyến nghị, chưa triển khai

1. **Chốt dữ liệu và tiêu chí loại/giữ:** fingerprint, nguồn, định nghĩa nhãn, alias, quy tắc xung đột và danh sách lớp đủ support theo group. Lưu mọi thay đổi ở interim/processed, không sửa raw.
2. **Thiết kế chia nhóm trước huấn luyện:** chọn test group độc lập với mục tiêu gần 20% khi khả thi, nhưng độ bao phủ lớp/group quan trọng hơn ép tỷ lệ. StratifiedGroupKFold hoặc chiến lược group có ràng buộc chỉ được dùng sau khi kiểm tra lớp/group thực tế; không mặc định 5-fold. Tính số group mỗi lớp trên train để chọn số fold khả thi.
3. **Khóa giao thức đánh giá:** chưa tồn tại final test trong Phase 1. EDA hiện đã xem thống kê toàn bộ CSV nên không gọi một phần của nó là dữ liệu chưa từng được quan sát. Sau khi cố định quy tắc, khóa test group và ngừng dùng nó để chọn đặc trưng, trọng số voting hay tham số. Đánh giá hoàn toàn mù cần dữ liệu ngoài chưa thăm dò.
4. **Pipeline trong train/CV:** xét cột hằng, gần hằng và tương quan trong từng training fold; imputation/scaling/feature selection/PCA đều fit ở train. So sánh original với reduced bằng cùng chia group. Không loại cột hiếm theo tần suất toàn bộ CSV chỉ vì gần hằng.
5. **Baseline khi được duyệt:** majority DummyClassifier làm mốc; BernoulliNB phù hợp biểu diễn nhị phân; LogisticRegression có điều chuẩn và DecisionTree giới hạn độ sâu là các ứng viên. Chưa có kết quả để xếp hạng hoặc khẳng định lựa chọn đặc trưng/voting giúp tăng điểm.
6. **Mất cân bằng và metric:** cần ít nhất macro-F1, weighted-F1, balanced accuracy, accuracy và support/điểm theo lớp cùng độ bao phủ lớp của test. Xem thêm top-k nếu mục tiêu giao diện là gợi ý nhiều lớp. So sánh class_weight trong CV nếu mô hình hỗ trợ; mọi resampling chỉ trong train fold, không nhân bản test. Không mặc định SMOTE cho dữ liệu nhị phân/lớp cực ít group.
7. **Độ bất định và độ bền:** báo cáo kết quả theo nhóm độc lập, lặp group split/CV khi khả thi, dùng bootstrap theo group nếu tính khoảng tin cậy. Phân tích lỗi xung đột, lớp hiếm và thiếu triệu chứng; dùng kiểm định độc lập trước bất kỳ kết luận ứng dụng thật.
8. **Chuẩn bị giao diện tiếng Việt:** xây từ điển Việt–Anh có rà soát, phủ định, mức không chắc chắn và câu hỏi bổ sung. Phân biệt “không được nhắc” với “được phủ nhận”; xác minh quy ước 0 trước mã hóa. ML dự đoán, LLM chỉ hiểu ngôn ngữ/giải thích. Chưa triển khai chatbot.

**Dừng ở Phase 1.** Chỉ tiến hành preprocessing, training, ensemble hoặc chatbot sau khi người dùng duyệt.
"""
    path = output_paths(root).reports_dir / "eda_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(note, encoding="utf-8")
    return path
