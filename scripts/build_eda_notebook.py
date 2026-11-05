"""Build notebook 01 after the audit has been executed and inspected."""
from build_notebooks import ROOT, SETUP, md, code, write_notebook

cells = [
    md('''
    # 01 — Exploratory Data Analysis

    **Mục tiêu:** mô tả phân bố bệnh, đặc điểm triệu chứng, mức dư thừa và khả năng phân biệt trên dữ liệu quan sát.
    **Câu hỏi nghiên cứu:** bao nhiêu lớp đủ support độc lập? Triệu chứng nào phổ biến/hiếm/hằng? Có dấu hiệu shortcut, profile tương tự và vector xung đột không? Điều đó ảnh hưởng thiết kế thí nghiệm thế nào?

    Đọc toàn bộ CSV. Đây là EDA mô tả; không fit phép biến đổi, không chọn tập đặc trưng để huấn luyện, không thử mô hình. Hình chỉ hiện các tập con có tiêu chí chọn rõ; bảng CSV lưu đầy đủ.
    '''), code(SETUP),
    code('''
    import matplotlib.pyplot as plt
    from src.data.eda import analyze_eda, export_eda
    from src.evaluation import plots
    from src.evaluation.report import write_eda_report
    from src.data.io import sha256_file
    before = sha256_file(path)
    audit = audit_dataset(df, config)
    eda = analyze_eda(df, audit, config)
    s, e = audit["summary"], eda["summary"]
    plots.configure_plots()
    def show(fig):
        display(fig)
        plt.close(fig)
    '''),
    md('''
    ## A. Phân bố nhãn
    Histogram và đường hạng mô tả toàn bộ lớp mà không gắn hàng trăm nhãn. Hai biểu đồ ngang hiển thị 15 lớp ở mỗi đầu; những lớp bằng tần suất được xếp theo tên.
    '''),
    code('''
    display(eda["class_quantiles"])
    show(plots.class_distribution(OUTPUT, audit))
    display(Markdown(f"Mỗi lớp có {s['min_class_samples']}–{s['max_class_samples']:,} dòng, trung vị {s['median_class_samples']:g}; tỷ lệ max/min {e['imbalance_max_min_ratio']:,.0f}:1. Lớp lớn nhất chỉ chiếm {e['majority_class_fraction']:.2%}, vì vậy cần xem đồng thời đuôi lớp hiếm và macro metric."))
    show(plots.extremes(OUTPUT, audit["class_distribution"], "disease", "samples", "02_class_extremes", ("15 lớp có nhiều dòng nhất", "15 lớp có ít dòng nhất")))
    display(Markdown(f"Có {s['classes_with_lt5_rows']} lớp dưới 5 dòng nhưng {s['classes_with_lt5_patterns']} lớp dưới 5 vector. Số dòng có thể thổi phồng support; chưa lựa chọn kỹ thuật cân bằng."))
    '''),
    md('''
    ## B. Đặc điểm triệu chứng
    Xếp tần suất trên toàn bộ dữ liệu; nhóm hiếm trên hình chỉ xét cột có xuất hiện để tách khỏi cột luôn vắng. Bảng audit vẫn chứa mọi cột.
    '''),
    code('''
    display(eda["symptom_frequency"].head(15))
    show(plots.extremes(OUTPUT, eda["symptom_frequency"], "feature", "present_count", "03_symptom_frequency", ("15 triệu chứng phổ biến nhất", "15 triệu chứng hiếm có xuất hiện"), nonzero=True))
    display(Markdown(f"Có {e['always_absent_symptoms']} triệu chứng luôn vắng và {e['always_present_symptoms']} triệu chứng luôn có; {s['near_constant_features_including_constant']} cột có giá trị trội ≥99% (gồm cột hằng). Tần suất thấp có thể vẫn hữu ích cho lớp hiếm, nên đây chưa phải quyết định loại cột."))
    '''),
    code('''
    show(plots.active_symptoms(OUTPUT, eda))
    display(eda["active_distribution"])
    display(Markdown(f"Trung bình {e['active_symptoms_mean']:.2f}, trung vị {e['active_symptoms_quantiles']['0.5']:g} triệu chứng/dòng; có {e['single_symptom_rows']:,} dòng chỉ một triệu chứng và {e['all_zero_rows']:,} dòng toàn 0. Số triệu chứng ít có thể hạn chế phân biệt bệnh; chưa suy ra độ nặng hoặc tính hợp lý lâm sàng."))
    '''),
    md('''
    ### Đồng xuất hiện và tương quan
    Jaccard xét phần giao/hiệp các dòng có triệu chứng; phi là Pearson cho hai biến nhị phân. Hình chỉ chọn 15 triệu chứng phổ biến nhất; các ma trận và cặp mạnh được lưu đầy đủ. Cột hằng có phi không xác định.
    '''),
    code('''
    show(plots.symptom_relationships(OUTPUT, eda))
    display(eda["symptom_pairs"].head(10))
    display(eda["strong_correlations"].head(15))
    display(Markdown(f"Có {e['high_absolute_correlation_pairs']} cặp |phi| ≥0,8, trong đó {e['high_correlation_pairs_joint_ge10']} cặp có ≥10 dòng đồng xuất hiện. Cần xem support trước diễn giải; tương quan không chứng minh đồng nghĩa hoặc nhân quả. Không tự gộp cột."))
    '''),
    md('''
    ## C. Triệu chứng–bệnh và profile tương tự
    Hình profile chọn bốn bệnh nhiều dòng nhất cộng cặp gần nhau có mỗi bệnh ≥20 dòng, ≥5 vector; tối đa 6 bệnh. Chọn 20 triệu chứng có tỷ lệ cao nhất trong các bệnh này. Cosine được tính từ profile trung bình của mọi bệnh, không dùng bộ phân loại.
    '''),
    code('''
    show(plots.selected_diseases(OUTPUT, audit, eda))
    display(Markdown(f"Có {e['single_class_symptoms']} triệu chứng chỉ xuất hiện ở một lớp ({e['single_class_symptoms_support_ge5']} có ≥5 dòng). Điều đó chỉ thể hiện tính đặc hiệu trong file, không chứng minh độ nhạy hoặc tính đúng lâm sàng; có thể liên quan cơ chế sinh dữ liệu."))
    display(eda["single_class_features"].head(15))
    show(plots.similar_diseases(OUTPUT, eda))
    display(eda["supported_similar_diseases"].head(10))
    display(Markdown("Cosine cao cho thấy tỷ lệ triệu chứng trung bình gần nhau, chưa chứng minh hai lớp không thể phân biệt bằng tương tác. Các cặp có support quá ít được lưu riêng và không đưa vào hình này."))
    '''),
    md('''
    ## D. Dư thừa dữ liệu và tổ hợp mơ hồ
    So sánh support theo dòng với vector độc lập. Đỏ/cam trên scatter đánh dấu lớp có dòng thuộc vector nhiều nhãn. Chỉ số trùng được tính bằng equality chính xác.
    '''),
    code('''
    show(plots.redundancy(OUTPUT, audit))
    display(eda["conflict_examples"].head(8))
    display(audit["class_patterns"].sort_values(["unique_patterns", "total_rows"]).head(20))
    display(Markdown(f"Có {s['unique_feature_vectors']:,} vector khác nhau; {e['rows_in_repeated_patterns_fraction']:.2%} dòng thuộc nhóm lặp và {s['conflicting_pattern_groups']:,} vector nhiều nhãn ({e['conflicting_rows_fraction']:.2%} dòng). Giới hạn majority theo vector trên chính file là {s['empirical_pattern_majority_ceiling']:.2%}; đây không phải kết quả test. Có {s['classes_with_one_pattern']} lớp chỉ một vector nên không thể có train/test độc lập cho mọi lớp hiện tại."))
    '''),
    md('''
    ## E. Hàm ý nghiên cứu và xuất kết quả
    Các bước sau đây chỉ xuất thống kê và khuyến nghị. Mọi phép biến đổi fit từ dữ liệu phải nằm trong train/CV ở giai đoạn sau. Toàn bộ file đã được mô tả trong EDA; chưa có test cuối được khóa.
    '''),
    code('''
    export_eda(OUTPUT, eda)
    report = write_eda_report(OUTPUT, audit, eda)
    assert sha256_file(path) == before, "Raw thay đổi trong lúc EDA!"
    display(Markdown(report.read_text(encoding="utf-8")))
    print("Đã lưu báo cáo, bảng và 8 hình PNG/SVG. Dừng ở Phase 1.")
    '''),
]

if __name__ == "__main__":
    write_notebook("01_eda.ipynb", cells)
