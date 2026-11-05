# EDA và Dataset Suitability Assessment

## Phạm vi và tính tái lập

Kết quả mô tả tính trên toàn bộ **246,945 dòng × 377 triệu chứng**, nhãn `diseases` với **773 lớp**. Không huấn luyện, lựa chọn đặc trưng, impute, scale, PCA hoặc chia train/test trong Phase 1.
Các bảng đầy đủ ở `reports/tables/`; 8 hình PNG/SVG ở `reports/figures/`. Tham số và seed nằm trong `configs/phase1.json`, fingerprint và phiên bản package nằm trong `artifacts/metadata/dataset_manifest.json`.

Nguồn ứng viên: [Disease and symptoms dataset 2023, Mendeley Data v1](https://data.mendeley.com/datasets/2cxccsxydc/1), DOI `10.17632/2cxccsxydc.1`, contributor Bran Stark, công bố 03/03/2025, CC BY 4.0 (tra cứu 21/10/2026).
Nhà xuất bản mô tả dữ liệu sinh nhân tạo. Tệp cục bộ khớp tên, schema và số lớp/đặc trưng; chưa có checksum nhà xuất bản/lịch sử tải để chứng minh danh tính bản gốc.
Không có bằng chứng độc lập về tính đại diện bệnh nhân, tỷ lệ mắc bệnh hoặc độ nặng. Không diễn giải tần suất trong CSV thành dịch tễ học.

## A. Phân bố nhãn và support

Mỗi lớp có tối thiểu **1**, tối đa **1,219**, trung vị **168** dòng; tỷ lệ max/min = **1,219:1**.
Lớp nhiều dòng nhất là `cystitis` (1,219 dòng). Tỷ trọng lớp lớn nhất = **0.49%**, 20 lớp lớn nhất = **9.83%**; không nên đánh giá mất cân bằng chỉ từ tỷ lệ max/min.
Có **52** lớp dưới 5 dòng, **115** lớp dưới 5 vector độc lập và **46** lớp chỉ một vector. Nhân bản thêm dòng không tạo thêm thông tin để đánh giá các lớp này.

| quantile | samples |
| --- | --- |
| 0.0 | 1.0 |
| 0.01 | 1.0 |
| 0.05 | 3.0 |
| 0.25 | 30.0 |
| 0.5 | 168.0 |
| 0.75 | 505.0 |
| 0.95 | 913.0 |
| 0.99 | 1215.0 |
| 1.0 | 1219.0 |

Một số lớp ít dòng (bảng đầy đủ: `audit_class_distribution.csv`):

| disease | samples |
| --- | --- |
| chronic ulcer | 1 |
| diabetes | 1 |
| foreign body in the nose | 1 |
| gas gangrene | 1 |
| heat stroke | 1 |
| high blood pressure | 1 |
| huntington disease | 1 |
| hypergammaglobulinemia | 1 |
| kaposi sarcoma | 1 |
| myocarditis | 1 |
| open wound due to trauma | 1 |
| open wound of the cheek | 1 |
| open wound of the chest | 1 |
| open wound of the head | 1 |
| open wound of the knee | 1 |

**Hình 01–02:** histogram, đường hạng với trục log và hai nhóm 15 nhãn tránh chồng hàng trăm nhãn. Chúng cho thấy cả chênh lệch kích thước lẫn đuôi lớp hiếm, chưa chứng minh kỹ thuật cân bằng nào sẽ cải thiện điểm.

## B. Triệu chứng, đồng xuất hiện và dư thừa cột

Cả 377 đặc trưng quan sát được đều là 0/1; **0** ô thiếu và **0** ô ngoài miền nhị phân.
Có **49** triệu chứng luôn vắng, **0** triệu chứng luôn có; **227** cột có giá trị trội ≥99%, gồm 49 cột hằng.
Cột hiếm có thể liên quan lớp hiếm; không tự xóa tất cả cột gần hằng. Dữ liệu không có từ điển đủ để suy ra cách xác nhận âm tính hoặc thiếu triệu chứng.

Triệu chứng phổ biến (tần suất chỉ mô tả tập sinh nhân tạo):

| feature | present_count | present_fraction |
| --- | --- | --- |
| sharp abdominal pain | 32307 | 0.13082670230213206 |
| vomiting | 27874 | 0.11287533661341595 |
| headache | 24719 | 0.10009921237522525 |
| cough | 24296 | 0.098386280345826 |
| sharp chest pain | 24016 | 0.09725242462896597 |
| nausea | 23687 | 0.09592014416165542 |
| back pain | 21809 | 0.08831521188928709 |
| shortness of breath | 21346 | 0.08644030047176497 |
| fever | 20394 | 0.08258519103444087 |
| dizziness | 17272 | 0.06994269979145154 |

Triệu chứng hiếm **có xuất hiện** (cột bằng 0 được liệt kê riêng trong audit):

| feature | present_count |
| --- | --- |
| feeling hot | 1 |
| skin pain | 1 |
| thirst | 1 |
| itching of scrotum | 4 |
| wrist weakness | 4 |
| low back weakness | 5 |
| incontinence of stool | 9 |
| scanty menstrual flow | 12 |
| ankle weakness | 18 |
| pelvic pressure | 20 |

Số triệu chứng hoạt động: trung bình **5.33**, trung vị **5**, min/max **1/12**; có **443** dòng chỉ một triệu chứng và **0** dòng toàn 0.

**Hình 03–05:** tần suất, số triệu chứng/dòng và quan hệ của 15 triệu chứng phổ biến nhất. Jaccard đo chồng lấp khi xuất hiện; phi là Pearson cho biến nhị phân. Phi không xác định cho cột hằng, được lưu NA thay vì gán 0. Không suy ra nhân quả hoặc diễn giải mức độ nặng từ đồng xuất hiện.
Có **0** cặp có |phi| ≥0,8; **0** trong số đó có ít nhất 10 dòng đồng xuất hiện. Những cặp hiếm vẫn có thể cho tương quan cao; bảng kèm `joint_rows` để xem support.
`regurgitation` và `regurgitation.1` được kiểm tra trong bảng alias; hậu tố tên không đủ làm cơ sở gộp tự động.

## C. Quan hệ triệu chứng–bệnh và khả năng phân tách

**Hình 06:** chọn bốn lớp nhiều dòng nhất cộng cặp profile gần nhất có mỗi lớp ≥20 dòng, ≥5 vector; chỉ minh họa tối đa 6 lớp và 20 triệu chứng. Bảng `eda_class_profiles.csv` chứa toàn bộ tỷ lệ P(symptom=1 | disease).
**Hình 07:** cosine của profile trung bình. Hai lớp có profile gần nhau có thể vẫn phân biệt bằng tương tác; các lớp thưa có profile ước lượng thiếu ổn định. Đây là thống kê mô tả, không phải đánh giá mô hình.

| disease_a | disease_b | cosine_similarity | rows_a | patterns_a | rows_b | patterns_b |
| --- | --- | --- | --- | --- | --- | --- |
| corneal disorder | dry eye of unknown cause | 0.9421168300646681 | 676 | 524 | 861 | 787 |
| skin disorder | skin polyp | 0.93508403685418 | 676 | 520 | 897 | 807 |
| infectious gastroenteritis | noninfectious gastroenteritis | 0.9202757963314326 | 1212 | 1212 | 1206 | 1206 |
| depression | post-traumatic stress disorder (ptsd) | 0.9168163839281822 | 912 | 830 | 607 | 492 |
| psychotic disorder | schizophrenia | 0.9159034364469727 | 902 | 802 | 890 | 811 |
| skin pigmentation disorder | skin polyp | 0.9105815552783861 | 909 | 805 | 897 | 807 |
| seborrheic keratosis | skin polyp | 0.9046569438022488 | 870 | 782 | 897 | 807 |
| seborrheic keratosis | skin pigmentation disorder | 0.9043236746940798 | 870 | 782 | 909 | 805 |

Có **40** triệu chứng chỉ xuất hiện trong một lớp, **35** trong số đó có ≥5 dòng. Tính đặc hiệu trên tệp không đồng nghĩa triệu chứng đủ độ nhạy, không chứng minh tính đặc hiệu lâm sàng hoặc khả năng tổng quát hóa. Xem `eda_single_class_features.csv` và `eda_class_always_symptoms.csv`.
Mẫu rất đặc hiệu, số triệu chứng ít và việc lặp có thể tạo shortcut từ cơ chế sinh dữ liệu. Đây là dấu hiệu cần điều tra; chưa có thí nghiệm để kết luận mô hình sẽ đạt điểm cao.

## D. Mẫu lặp, xung đột và giới hạn thông tin

Có **169,888** vector khác nhau; **77,057 (31.20%)** dòng dư nếu giữ một dòng/vector. Tổng số dòng thuộc các nhóm vector lặp, tính cả dòng đầu, là **121,344 (49.14%)**.
Nếu xét cả nhãn thì có **57,298** dòng dư. Có **12,634** vector mang nhiều nhãn, liên quan **39,728 (16.09%)** dòng.

**Hình 08:** số dòng và số vector theo lớp khác nhau, cho thấy kích thước hiệu dụng không thể đo chỉ bằng số dòng.
Giới hạn ghi nhớ thực nghiệm của bộ phân loại tất định chỉ dùng triệu chứng, với trọng số mỗi dòng trên đúng tệp này, là **91.62%**: tổng số dòng của nhãn đông nhất mỗi vector chia tổng số dòng.
Đây **không** phải test accuracy, kỳ vọng hiệu năng hay giới hạn cho dữ liệu mới. Việc lọc xung đột hoặc thay đổi trọng số sẽ thay đổi con số này.
Các xung đột có thể phản ánh triệu chứng chưa đủ phân biệt nhiều bệnh hoặc nhiễu sinh dữ liệu; không thể tự quyết nhãn nào đúng.

| pattern_id | active_symptoms | rows | distinct_labels |
| --- | --- | --- | --- |
| 4260 | sharp abdominal pain | 27 | 26 |
| 14853 | shortness of breath \| sharp chest pain | 30 | 24 |
| 4087 | sharp abdominal pain \| nausea | 30 | 22 |
| 27759 | vomiting \| nausea | 21 | 21 |
| 9789 | cough \| nasal congestion | 22 | 20 |

## E. Dataset Suitability Assessment: **CONDITIONAL GO**

**Phạm vi được hỗ trợ:** nghiên cứu học phần về phân loại trên bộ triệu chứng nhị phân sinh nhân tạo, sau khi chốt cách xử lý xung đột, lớp ít group và chia nhóm. Cấu trúc có nhãn, miền giá trị hợp lệ và 169,888 vector cho phép tiếp tục thí nghiệm dưới các điều kiện này.

**Điều kiện phải giải quyết:**

1. Xác minh xuất xứ, giấy phép và cơ chế sinh nếu lấy được tài liệu gốc; phân biệt phát hiện từ file và mô tả nhà xuất bản.
2. Định nghĩa chính sách cho 12,634 vector xung đột: giữ và báo cáo giới hạn thông tin, cách ly, hoặc đổi bài toán có lý do. Không tự chọn nhãn bằng thông tin toàn bộ test.
3. Quyết định phạm vi đánh giá cho 46 lớp chỉ một vector và lớp dưới số group cần thiết; không thể yêu cầu train/test độc lập cho mọi lớp hiện tại. Muốn giữ đầy đủ 773 lớp có đánh giá độc lập cần bổ sung dữ liệu/vector phù hợp hoặc chấp nhận lớp không có test độc lập và báo cáo rõ.
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
