"""Build only the Phase 2 inspection notebook; never overwrite an existing notebook."""
from build_notebooks import BOOTSTRAP, code, md, write_notebook
import textwrap
import ast


PHASE2_REQUIRED_FILES = (
    "configs/phase1.json", "configs/phase2.json", "configs/runtime.json", "configs/dataset_source.json",
    "src/__init__.py", "src/data/__init__.py", "src/data/paths.py", "src/data/bootstrap.py",
    "src/data/loader.py", "src/data/io.py", "src/data/audit.py",
    "src/data/preprocessing_inspection.py", "src/data/preprocessing.py",
)


def inspection_cells():
    cells = [
        md('''
        # 02 — Preprocessing Inspection & Decision Review

        ## 1. Goals and agreed data assumptions

        Kiểm tra tính khả thi, **chưa áp dụng tiền xử lý cuối cùng**. Không huấn luyện,
        chọn đặc trưng, PCA, ensemble hoặc chatbot. Giữ nguyên raw và kết quả Phase 1.

        Giả định tạm thời: **1 = ghi nhận triệu chứng hiện diện; 0 = chưa ghi nhận hiện diện**,
        không chứng minh vắng mặt lâm sàng. Nhà xuất bản chưa định nghĩa đầy đủ; dữ liệu tổng hợp,
        không tự gán thêm ý nghĩa y khoa. Vector duy nhất là đơn vị phân biệt trong dữ liệu,
        không chứng minh độc lập bệnh nhân.

        Dùng lại bootstrap/config chung: cần cả `src/` và `configs/` trên máy chạy kernel.
        Nếu kernel ở `/content` chỉ có notebook/CSV, hãy upload/giải nén source mới theo
        `docs/portable_runtime.md`. Các biến cấu hình ở đầu cell sau:
        `PROJECT_ROOT`, `PATH_CONFIG`, `MOUNT_DRIVE`, `SOURCE_ARCHIVE`.
        Mount chỉ bật chủ động khi Colab/giao diện hỗ trợ, không bật trên local.
        Không tự cài gói hoặc tải file. Cài dependencies theo README trước khi chạy.
        Báo cáo mới dùng output root đã cấu hình (Drive persistent khi chạy Colab),
        cache CSV trên runtime chỉ khi đã bật `copy_raw_to_local`; cache là ephemeral.
        '''),
        code(BOOTSTRAP + r'''
import numpy as np
import pandas as pd
from IPython.display import display, Markdown
from src.data.io import read_config
from src.data.loader import dataset_path, prepare_dataset, load_dataset, sha256_file
from src.data.audit import audit_dataset
from src.data.paths import OutputPaths
from src.data.preprocessing_inspection import (
    inspect_header, inspect_regurgitation, class_eligibility, group_split_feasibility,
    decision_table, review_markdown, write_review,
)

config = read_config(ROOT)
source_path = dataset_path(runtime_paths, config)
source_sha = sha256_file(source_path)
read_path = prepare_dataset(runtime_paths, source_path)
assert sha256_file(read_path) == source_sha, "Cache khác CSV nguồn!"
df = load_dataset(read_path, config["target"])
audit = audit_dataset(df, config)
s = audit["summary"]
if not s["binary_complete"] or s["missing_target_rows"] or s["blank_target_rows"]:
    raise ValueError("Inspection yêu cầu nhãn đầy đủ, triệu chứng 0/1 hợp lệ; xem audit, không tự sửa dữ liệu.")
OUTPUT = OutputPaths(runtime_paths.output_root)
header = inspect_header(read_path)
metadata = json.loads((ROOT / config["source_metadata"]).read_text(encoding="utf-8"))
print(f"CSV: {source_path.name}; SHA-256: {source_sha}")
print(f"Runtime: {runtime_paths.runtime}; output: {OUTPUT.reports_dir}")
print(f"Python: {sys.version.split()[0]}; NumPy: {np.__version__}; pandas: {pd.__version__}")
print("Nguồn hiện có:", metadata["title"], "; giới hạn:", metadata["limitations"])
print("Chỉ đọc CSV; không tạo run Phase 1 hay dữ liệu processed.")
'''),
        code('''
        # Các giá trị tham chiếu từ Phase 1 chỉ để đối chiếu, không dùng thay dữ liệu thực.
        reference = {"rows": 246945, "classes": 773, "features": 377,
                     "constant_features": 49, "conflicting_pattern_groups": 12634,
                     "classes_with_lt5_patterns": 115}
        comparison = pd.DataFrame([{"metric": key, "phase1_reported": old,
                                    "observed_now": s[key], "matches": old == s[key]}
                                   for key, old in reference.items()])
        display(comparison)
        if not comparison["matches"].all():
            print("Dữ liệu khác mốc Phase 1: dùng số đếm hiện tại; cần rà soát lại mọi quyết định.")
        '''),
        md('''
        ## 2. Exact duplicate inspection

        Chính sách đã thống nhất: sau này chỉ bỏ bản sao **cùng toàn bộ vector và cùng nhãn**;
        giữ các nhãn khác nhau của cùng vector. Không dùng majority voting đổi nhãn.
        Bảng `(pattern_id, disease)` là thống kê trong RAM; mỗi cặp đại diện một dòng dự kiến
        sau dedup, không xuất bảng này thành dataset. ID dùng equality pack-bit chính xác,
        phụ thuộc thứ tự dòng/cột và SHA-256 của CSV.
        '''),
        code('''
        pairs = audit["pattern_labels"]
        projected_dedup_rows = len(pairs)
        # Đối chiếu độc lập với equality trên toàn bộ dòng, không dựa riêng ID của audit.
        assert int(df.duplicated().sum()) == s["exact_duplicate_excess_rows"]
        assert projected_dedup_rows == len(df) - s["exact_duplicate_excess_rows"]
        assert int(pairs["rows"].sum()) == len(df)
        display(pd.DataFrame([{
            "raw_rows": len(df), "exact_duplicate_excess_rows": s["exact_duplicate_excess_rows"],
            "rows_in_duplicate_groups_including_first": s["rows_in_exact_duplicate_groups"],
            "hypothetical_rows_after_dedup": projected_dedup_rows,
            "unique_full_vectors": s["unique_feature_vectors"],
            "conflicting_full_vectors": s["conflicting_pattern_groups"],
        }]))
        '''),
        md('''
        ## 3. `regurgitation` column inspection

        Đọc header thô, đối chiếu từng dòng, tính support theo bệnh ở cả raw và vector độc lập.
        Kiểm tra ba tình huống giả định: bỏ cột thứ nhất, bỏ cột thứ hai, bỏ cả hai.
        Mọi phép chiếu chỉ diễn ra trong RAM, không đổi schema đang dùng cho split.
        Metadata hiện có thiếu từ điển phân biệt hai tên; không suy ra hai định nghĩa y khoa.
        '''),
        code('''
        reg = inspect_regurgitation(df, audit, config["target"])
        print("Header nguyên văn:", header)
        display(pd.DataFrame([reg["counts"]]))
        display(reg["disease_support"])
        assert reg["counts"]["matching_rows"] + reg["counts"]["differing_rows"] == len(df)
        assert reg["counts"]["regurgitation_ones"] + reg["counts"]["regurgitation.1_ones"] == (
            2 * reg["counts"]["both_ones"] + reg["counts"]["exactly_one"])
        display(reg["projections"])
        '''),
        md('''
        `new_conflicts_from_pure` đếm nhóm chiếu mới xung đột, trong khi mọi vector gốc cấu thành
        chỉ có một nhãn. `expanded_label_sets` còn tính nhóm vốn xung đột nhưng nay có thêm nhãn.
        Tổng số nhóm xung đột có thể giảm do gộp nhóm đã xung đột, nên chênh lệch tổng không đo đủ
        tác động mới. `collapsed_original_vectors` đo lượng phân biệt vector bị mất.

        Với CSV được rà soát, hai cột khác nhau; đề xuất tạm giữ cả hai tên gốc và ghi rõ giới hạn
        ngữ nghĩa. Không tự coi `.1` là cột thừa, không tự gộp OR, không đổi tên thành nghĩa lâm sàng.
        Quyết định schema cần người dùng duyệt.
        '''),
        md('''
        ## 4. Rare disease class eligibility

        Đếm vector **đầy đủ** duy nhất mỗi bệnh; các nhãn dùng chung một vector vẫn được tính
        riêng cho mỗi bệnh. Vì vậy tổng support các bệnh có thể lớn hơn số vector toàn bộ.
        `% of dedup` dùng mẫu số toàn bộ dòng sau exact dedup, `% of raw` dùng toàn bộ dòng gốc.
        Các phân vị được nội suy theo mặc định pandas. Chưa loại lớp nào khỏi dữ liệu nguồn.
        '''),
        code('''
        eligibility, inventory = class_eligibility(pairs, len(df))
        assert inventory["unique_vectors"].sum() == projected_dedup_rows
        assert (inventory["unique_vectors"] < 5).sum() == s["classes_with_lt5_patterns"]
        display(eligibility.round(4))
        CANDIDATE_MINIMUM = 5  # Ứng viên để kiểm tra; chưa phải quyết định triển khai.
        print("Ứng viên: ≥5 vector/lớp; cân nhắc độ phủ và đánh giá, không dự đoán điểm mô hình.")
        '''),
        md('''
        ## 5. Group-aware split feasibility

        Chưa có xử lý schema mới được duyệt: dùng đủ cột triệu chứng gốc để xác định group.
        Dù khác nhãn, mọi dòng có cùng vector phải đi cùng tập. Dùng seed trong `phase1.json`.
        Một lần thử: hoán vị group, phân hạn ngạch khoảng 70/15/15; sửa lớp vắng theo support
        tăng dần, chỉ chuyển group khi mọi nhãn vẫn còn trong tập cho. Trong các chuyển hợp lệ,
        chọn thay đổi ít nhất sai lệch support lớp so với tỷ lệ mục tiêu; hòa chọn group ID nhỏ.

        Đây là heuristic khả thi, không bảo đảm stratification hay đủ lớp trên dữ liệu bất kỳ;
        báo cáo kết quả thật và kiểm tra lại giao group từ phân bổ từng cặp vector/nhãn.
        Không lưu assignment, không tạo CSV train/validation/test. Thay schema hoặc ngưỡng
        phải chạy lại; chốt và khóa test trước phát triển mô hình.
        '''),
        code('''
        split = group_split_feasibility(pairs, minimum=CANDIDATE_MINIMUM, seed=config["seed"])
        display(split["summary"].round(4))
        print("Lớp vắng ở từng tập:", json.dumps(split["missing_classes"], ensure_ascii=False))
        print("Giao group từng cặp:", split["overlaps"])
        print("Số chuyển group để bảo vệ độ phủ:", split["repairs"])
        assert not any(split["overlaps"].values())
        candidate = eligibility.loc[eligibility["min_unique_vectors"] == CANDIDATE_MINIMUM].iloc[0]
        assert split["summary"]["dedup_records"].sum() == candidate["dedup_records"]
        class_support = inventory.merge(split["class_support"].drop(columns="unique_vectors"),
                                        on="disease", how="left")
        class_support["eligible_candidate"] = class_support["unique_vectors"] >= CANDIDATE_MINIMUM
        for name in ["train", "validation", "test"]:
            class_support[name] = class_support[name].fillna(0).astype(int)
        display(class_support.head(15))
        display(split["class_support"][["train", "validation", "test"]].describe())
        print("Số lớp chỉ có 1 vector ở validation/test:", {
            name: int(split["class_support"][name].eq(1).sum()) for name in ["validation", "test"]})
        print("Đủ mặt lớp chưa chứng minh đánh giá ổn định; toàn bộ support lớp sẽ lưu dạng tổng hợp.")
        '''),
        md('''
        ## 6. Constant feature review

        Cột hằng có cùng giá trị trên mọi dòng, không phân biệt bệnh trong dữ liệu quan sát.
        Sau khi chốt split, đề xuất bước `VarianceThreshold(0)` hoặc tương đương chỉ fit trên
        train, dùng cùng mask cho validation/test. Không fit selector trên toàn CSV trong
        notebook này, không xóa cột raw. Không áp dụng loại gần hằng.
        '''),
        code('''
        constants = audit["features"].loc[audit["features"]["constant"], ["feature", "min", "max", "present_count"]]
        assert len(constants) == s["constant_features"]
        print(f"Xác nhận {len(constants)} cột hằng; các giá trị thực tế:")
        with pd.option_context("display.max_rows", None):
            display(constants)
        '''),
        md('''
        ## 7. Final recommendations and unresolved decisions

        Ưu tiên ≥5 vector/lớp: giữ gần toàn bộ dòng sau dedup, đồng thời phép thử đã kiểm tra
        độ phủ trên cả ba tập. Ngưỡng 1 có lớp không thể chia ba; ngưỡng 3 chỉ vừa đủ tối thiểu
        một vector/tập; ngưỡng 10 loại thêm lớp khi 5 đã có phép chia phủ lớp khả thi.
        Vẫn cần báo cáo support vì một số bệnh có rất ít vector đánh giá. Dữ liệu tổng hợp và
        toàn CSV đã được EDA; kết quả sau này không thay thế xác thực lâm sàng/dữ liệu độc lập.

        Chỉ ghi một báo cáo ngắn và 5 bảng tổng hợp thiết yếu vào storage persistent đã cấu hình.
        Nếu file Phase 2 đích đã có nội dung khác, dừng để giữ kết quả cũ; muốn review khác thì
        đặt `DISEASE_OUTPUT_DIR` tới output root khác. File Phase 1 không bị ghi đè.
        **Dừng ở đây và chờ duyệt**, chưa tạo processed data, split datasets hay mô hình.
        '''),
        code('''
        assert sha256_file(source_path) == source_sha, "CSV nguồn đã thay đổi trong quá trình kiểm tra!"
        report = review_markdown(source_path.name, source_sha, audit, header, reg, eligibility, split)
        report_path = write_review(OUTPUT, report, {
            "preprocessing_class_eligibility": eligibility,
            "preprocessing_regurgitation_support": reg["disease_support"],
            "preprocessing_regurgitation_projection": reg["projections"],
            "preprocessing_split_summary": split["summary"],
            "preprocessing_class_support": class_support,
        })
        display(decision_table())
        print(f"Báo cáo: {report_path}")
        print("SHA-256 CSV trước/sau khớp. Không xuất dữ liệu xử lý hoặc assignment; dừng chờ duyệt.")
        '''),
    ]
    return cleanup_phase2_cells(present_phase2_cells(finalize_phase2_cells(extend_final_decision_cells(cells))))


def extend_final_decision_cells(cells):
    """Update just setup/recommendations and insert A/B, preserving existing cell IDs.

    This also applies to the existing notebook without regenerating its earlier
    analysis, bootstrap configuration, Markdown, cell IDs or historical outputs.
    """
    if any("threshold_analysis = threshold_split_comparison" in cell.source for cell in cells):
        raise ValueError("Notebook đã có phần mở rộng A/B; không chèn lặp.")
    setup = next(cell for cell in cells if cell.cell_type == "code" and "source_path = dataset_path" in cell.source)
    setup.source += '''\n\n# Phần mở rộng đúng hai phân tích quyết định cuối, không đổi splitter đã có.
from src.data.preprocessing_inspection import (
    threshold_split_comparison, both_features_removal_impact,
    threshold_comparison_figure, final_decision_markdown,
)
'''
    legacy = next(cell for cell in cells if cell.cell_type == "code" and "CANDIDATE_MINIMUM = 5" in cell.source)
    legacy.source = legacy.source.replace("# Ứng viên để kiểm tra; chưa phải quyết định triển khai.",
                                          "# Mốc rà soát ban đầu; giữ để tái hiện 5 CSV lịch sử.")
    legacy.source = legacy.source.replace("Ứng viên: ≥5 vector/lớp; cân nhắc độ phủ và đánh giá, không dự đoán điểm mô hình.",
                                          "Mốc ban đầu: ≥5 vector/lớp; đề xuất cập nhật nằm ở mục 7 sau so sánh 1/3/5/10/15.")
    section = next(i for i, cell in enumerate(cells) if cell.cell_type == "markdown" and "## 7. Final recommendations" in cell.source)
    cells[section].source = md('''
        ## 7. Final recommendations and unresolved decisions

        Bổ sung đúng hai phân tích theo yêu cầu quyết định cuối. Các mục trên và 5 CSV đã có
        giữ mốc rà soát ban đầu (ứng viên ≥5); chúng không phải quyết định schema/ngưỡng cuối.
        Hai phần dưới dùng lại loader, grouping equality và thuật toán chia đã có, seed 42.
        Không huấn luyện, không tìm seed tốt hơn, không lưu bảng dữ liệu đã xử lý hoặc assignment.
        ''').source
    extra = [
        md('''
        ### A. So sánh ngưỡng 1, 3, 5, 10, 15 vector/lớp

        Mẫu số cố định là mọi cặp (vector đầy đủ ban đầu, nhãn) sau exact dedup giả định,
        trước lọc lớp. Group dùng đủ 377 đặc trưng hiện có, gồm hai cột regurgitation.
        Mỗi ngưỡng chia lại tập đủ điều kiện bằng cùng thuật toán/seed, không phải split lồng nhau.
        Đếm riêng lớp vắng và lớp có đúng 1 vector validation/test; đủ mặt lớp chưa bảo đảm
        đánh giá ổn định. Chỉ lưu một hình PNG hai panel, không xuất thêm CSV ngưỡng.
        '''),
        code('''
        FINAL_REVIEW_SEED = 42
        threshold_analysis = threshold_split_comparison(pairs, len(df), thresholds=(1, 3, 5, 10, 15), seed=FINAL_REVIEW_SEED)
        threshold_table = threshold_analysis["comparison"]
        columns = ["min_unique_vectors", "retained_classes", "excluded_classes", "dedup_records",
                   "pct_of_dedup_records", "singleton_validation_classes", "singleton_test_classes",
                   "missing_train_classes", "missing_validation_classes", "missing_test_classes"]
        display(threshold_table[columns].round(4))
        for minimum, probe in threshold_analysis["splits"].items():
            print(f"Ngưỡng ≥{minimum}: giao group {probe['overlaps']}; lớp vắng "
                  f"train/val/test = { {k: len(v) for k, v in probe['missing_classes'].items()} }")
            assert not any(probe["overlaps"].values())
        # Lựa chọn phân tích: cân bằng độ phủ bệnh và support độc lập, không dùng model score.
        RECOMMENDED_MINIMUM = 10
        candidate_split = threshold_analysis["splits"][RECOMMENDED_MINIMUM]
        display(candidate_split["summary"].round(4))
        print("Lớp vắng ứng viên:", candidate_split["missing_classes"])
        fig, threshold_figure_path = threshold_comparison_figure(threshold_analysis, OUTPUT, recommended=RECOMMENDED_MINIMUM)
        display(fig)
        import matplotlib.pyplot as plt
        plt.close(fig)
        print("Hình duy nhất:", threshold_figure_path)
        '''),
        md('''
        ≥10 là đề xuất thay ứng viên ≥5: giữ độ phủ lớp rộng hơn 15 nhưng giảm nhiều lớp chỉ có
        một vector đánh giá so với 5 trong phép thử này. ≥15 giảm singleton thêm nhưng loại
        nhiều bệnh hơn. Không coi lựa chọn ngưỡng hoặc một lần chia seed 42 là bảo đảm metric
        từng bệnh đáng tin cậy; thay đổi singleton còn chịu tác động chia lại group mỗi ngưỡng.

        ### B. Tác động bỏ đồng thời hai cột regurgitation

        Đơn vị so sánh: toàn bộ cặp **(vector đầy đủ gốc, nhãn)** sau exact dedup giả định,
        **chưa lọc lớp**, cùng mẫu số trước/sau. Hai cột là triệu chứng; nhãn vẫn là `diseases`.
        Chiếu bỏ hai cột trong RAM để đếm thông tin mất, nhóm xung đột mới, support từng bệnh
        và eligibility theo ứng viên mới. Không áp dụng phép chiếu lên df/CSV nguồn.
        Phân biệt số vector gốc tham gia gộp, số nhóm sau gộp và chênh lệch số vector.
        '''),
        code('''
        feature_impact = both_features_removal_impact(df, audit, config["target"], minimum=RECOMMENDED_MINIMUM)
        impact_summary = feature_impact["summary"]
        assert impact_summary["comparison_denominator_records"] == len(pairs)
        assert not impact_summary["class_filter_applied"]
        display(pd.DataFrame([{"metric": k, "value": v} for k, v in impact_summary.items()]))
        with pd.option_context("display.max_rows", None, "display.max_columns", None):
            display(feature_impact["class_impact"].round({"pct_vectors_lost": 2}))
        print("Toàn bộ tên bệnh liên quan:", feature_impact["associated_disease_names"])
        print("Lớp đủ ngưỡng trước đó nay không đủ:", feature_impact["lost_eligible_classes"])
        print("Lớp mới đủ ngưỡng:", feature_impact["gained_eligible_classes"])
        assert len(df) == s["rows"] and df.shape[1] == s["columns"]
        '''),
        md('''
        **Đề xuất schema: hoãn quyết định bỏ/giữ cho pipeline cuối**, tạm giữ nguyên hai cột
        trong inspection. Bỏ cột làm mất thông tin quan sát được; chưa huấn luyện nên không suy ra
        accuracy tăng/giảm. Giữ cột cần mapping thu nhận triệu chứng đã xác minh. Không tự bịa
        nghĩa y khoa cho `.1`, không tạo hai câu hỏi chatbot khác nghĩa hoặc mã hóa cùng lời kể
        thành cả hai bit. Cần mapping/schema nhất quán giữa train và suy luận trước tích hợp chatbot.

        Chỉ cập nhật báo cáo Phase 2 theo yêu cầu, thêm đúng một hình và một CSV compact cho B.
        Năm CSV ban đầu giữ nguyên nội dung; không thêm CSV ngưỡng, notebook phụ hay pipeline mới.
        Nếu CSV cũ khác nội dung, writer vẫn dừng để bảo vệ lịch sử. `update_report=True` chỉ cho
        cập nhật đúng Markdown review Phase 2, không cho ghi đè CSV/Phase 1.
        **Dừng chờ duyệt** ngưỡng ≥10 và schema; chưa lọc lớp, bỏ cột, lưu split hay huấn luyện.
        '''),
    ]
    export = next(cell for cell in cells[section + 1:] if cell.cell_type == "code" and "report_path = write_review" in cell.source)
    export.source = export.source.replace(
        'report = review_markdown(source_path.name, source_sha, audit, header, reg, eligibility, split)',
        'report = final_decision_markdown(source_path.name, source_sha, audit, threshold_analysis, feature_impact, recommended=RECOMMENDED_MINIMUM)')
    export.source = export.source.replace(
        '"preprocessing_class_support": class_support,',
        '"preprocessing_class_support": class_support,\n    "preprocessing_regurgitation_removal_impact": feature_impact["class_impact"],')
    export.source = export.source.replace('})\ndisplay(decision_table())', '}, update_report=True)')
    return cells[:section + 1] + extra + cells[section + 1:]


def finalize_phase2_cells(cells):
    """Preserve inspection cells as optional history and append approved execution."""
    if any("APPROVED_PHASE2_FINALIZATION" in cell.source for cell in cells):
        raise ValueError("Notebook đã có pipeline Phase 2 cuối; không chèn lặp.")
    setup = next(c for c in cells if c.cell_type == "code" and "source_path = dataset_path" in c.source)
    setup.source = setup.source.replace("config = read_config(ROOT)", '''# APPROVED_PHASE2_FINALIZATION
# Hiện bảng và hình phân tích lịch sử; không thay đổi chính sách đã duyệt.
RUN_HISTORICAL_INSPECTION = True
from src.data.preprocessing import (
    read_phase2_policy, validate_raw_frame, preprocess_dataset,
    export_preprocessed, preprocessing_report,
)
phase2_policy = read_phase2_policy(ROOT)
config = read_config(ROOT)
if config["target"] != phase2_policy["target"]:
    raise ValueError("Nhãn Phase 1/Phase 2 không khớp; dừng thay vì đổi nhãn.")''')
    begin = setup.source.index("audit = audit_dataset(df, config)")
    end = setup.source.index("OUTPUT = OutputPaths", begin)
    setup.source = setup.source[:begin] + '''validate_raw_frame(df, phase2_policy)
if RUN_HISTORICAL_INSPECTION:
    audit = audit_dataset(df, config)
    s = audit["summary"]
''' + setup.source[end:]
    setup.source = setup.source.replace("Chỉ đọc CSV; không tạo run Phase 1 hay dữ liệu processed.",
                                        "Raw chỉ được đọc; mục 8 thực thi pipeline đã duyệt và lưu split persistent.")
    for cell in cells:
        if cell.cell_type != "code" or cell is setup:
            continue
        if "report_path = write_review" in cell.source:
            cell.source = 'print("Rà soát lịch sử đã xong; báo cáo cuối được xử lý ở luồng chính, không xuất lại bảng/hình lịch sử.")'
        if "fig, threshold_figure_path = threshold_comparison_figure" in cell.source:
            start = cell.source.index("fig, threshold_figure_path = threshold_comparison_figure")
            cell.source = cell.source[:start] + '''# Dựng lại trong bộ nhớ để hiển thị cả khi runtime chưa có PNG báo cáo.
import matplotlib.pyplot as plt
import inspect, tempfile
if "save" in inspect.signature(threshold_comparison_figure).parameters:
    fig, _ = threshold_comparison_figure(threshold_analysis, OUTPUT, recommended=RECOMMENDED_MINIMUM, save=False)
else:
    # ZIP Phase 2 cũ chưa có save=False: preview ở ổ tạm local, không ghi đè báo cáo.
    with tempfile.TemporaryDirectory(prefix="phase2-preview-") as preview_root:
        fig, _ = threshold_comparison_figure(
            threshold_analysis, OutputPaths(Path(preview_root)), recommended=RECOMMENDED_MINIMUM)
display(fig)
plt.close(fig)'''
        cell.source = ("if RUN_HISTORICAL_INSPECTION:\n" + textwrap.indent(cell.source, "    ")
                       + '\nelse:\n    print("Đã tắt phân tích lịch sử. Đặt RUN_HISTORICAL_INSPECTION=True trong cell cấu hình rồi Run All để hiện bảng và hình.")')
    first = cells[0]
    first.source = first.source.replace("# 02 — Preprocessing Inspection & Decision Review", "# 02 — Preprocessing: chính sách đã duyệt và split cuối")
    first.source = first.source.replace("## 1. Goals and agreed data assumptions", '''**Trạng thái hiện tại: đã duyệt và thực thi Phase 2.** Mục 8 là pipeline cuối cùng:
bỏ hai cột mơ hồ → dedup theo vector còn lại + nhãn → ≥10 vector/lớp → group split seed 42.
Mục 1–7 giữ lịch sử phân tích trước phê duyệt; `RUN_HISTORICAL_INSPECTION=True` mặc định
để Run All hiện các bảng và hình trong notebook, không ghi lại báo cáo cũ. Không fit transformer/mô hình.

## 1. Goals and agreed data assumptions — lịch sử trước phê duyệt''')
    return cells + [
        md('''
        ## 8. Approved preprocessing pipeline — kết quả cuối

        Chính sách tập trung tại `configs/phase2.json`, tách khỏi config Phase 1 lịch sử.
        Raw được xác thực đầy đủ trước khi bỏ `regurgitation` và `regurgitation.1`.
        Hai cột bị loại vì không thể ánh xạ đáng tin cậy từ lời kể người dùng; không tự gán nghĩa y khoa.
        Sau đó mới exact dedup theo **375 triệu chứng còn lại + nhãn**, đếm lại support độc lập,
        giữ bệnh ≥10 vector, tạo group bằng equality vector còn lại và chia khoảng 70/15/15, seed 42.
        Giữ các nhãn khác nhau của cùng vector và đưa chúng vào cùng split.

        Bất kỳ thiếu lớp, overlap hay sai tính tái lập đều dừng trước khi lưu; không tự đổi quy tắc.
        Giữ mọi cột hằng ở Phase 2. `VarianceThreshold(0)` chỉ fit trên train bên trong pipeline
        ở giai đoạn huấn luyện sau này. Không chọn đặc trưng, PCA, huấn luyện hoặc chatbot ở đây.
        '''),
        code('''
        finalized = preprocess_dataset(df, phase2_policy)
        display(finalized["steps"])
        print(f"Dữ liệu cuối: {len(finalized['data']):,} bản ghi; {len(finalized['classes'])} lớp; "
              f"{len(finalized['features'])} triệu chứng trước bước variance fit trên train.")
        print("Fingerprint processed:", finalized["processed_sha256"])
        '''),
        code('''
        display(finalized["split_summary"].round(4))
        display(pd.DataFrame([{"check": k, "result": v} for k, v in finalized["validation"].items()]))
        print("Assignment và support đã được tính lại hai lần bằng cùng seed 42 và khớp hoàn toàn.")
        print("Kiểm tra group và equality vector độc lập đều không có giao giữa các tập.")
        '''),
        md('''
        Lưu 3 CSV nén dưới `data/processed/` của **output root đã cấu hình**, không phải source
        tạm trên `/content`. Artifact tái sử dụng dưới `artifacts/metadata/phase2/`; schema
        lưu thứ tự triệu chứng, label mapping riêng và group/row ID trong sidecar, không lẫn vào X.
        Tạo file tạm, đọc lại và kiểm checksum ở ổ tạm local, chỉ publish khi mọi kiểm tra đạt.
        Gzip không chứa timestamp/filename; chạy lại cùng dữ liệu/phiên bản mã tạo cùng bytes.
        File đã khóa khác nội dung sẽ báo lỗi, không ghi đè; muốn tạo bộ khác phải chọn output root khác.

        Test được khóa cho đánh giá cuối, không chọn feature/hyperparameter. Dữ liệu đã được EDA
        toàn bộ từ Phase 1 nên không tuyên bố test chưa từng được thăm dò. Cell sau chỉ kiểm toàn vẹn,
        không dùng test để lựa chọn gì. Chưa kiểm chứng runtime Colab thật; bootstrap/storage dùng chung.
        '''),
        code('''
        manifest = export_preprocessed(finalized, source_path, OUTPUT, expected_source_sha256=source_sha)
        report = preprocessing_report(finalized, manifest)
        report_path = write_review(OUTPUT, report, {}, update_report=True)
        assert sha256_file(source_path) == source_sha, "CSV raw thay đổi!"
        print("Split đã lưu:", OUTPUT.processed_dir)
        print("Artifact:", OUTPUT.metadata_dir / "phase2")
        print("Báo cáo:", report_path)
        print("Raw trước/sau cùng SHA-256; CSV nén được đọc lại khớp dữ liệu và thứ tự cột.")
        print("Phase 2 hoàn tất. DỪNG: chưa fit transformer, huấn luyện, ensemble hoặc chatbot.")
        '''),
    ]


def present_phase2_cells(cells):
    """Put the actual workflow first; make source/runtime diagnostics pre-import."""
    if any("PHASE2_PRESENTATION_V2" in c.source for c in cells):
        raise ValueError("Notebook đã có giao diện/trình tự Phase 2 mới.")
    setup = next(c for c in cells if c.cell_type == "code" and "source_path = dataset_path" in c.source)
    names = {"PROJECT_ROOT", "PATH_CONFIG", "MOUNT_DRIVE", "SOURCE_ARCHIVE", "SOURCE_DIRECTORY", "RUN_HISTORICAL_INSPECTION"}
    values = {name: None for name in names}
    values.update(MOUNT_DRIVE=False, RUN_HISTORICAL_INSPECTION=True)
    for node in ast.parse(setup.source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in names:
            values[node.targets[0].id] = ast.literal_eval(node.value)
    configuration = code(textwrap.dedent('''
        # PHASE2_PRESENTATION_V2 — Chỉ sửa cấu hình trong cell này.
        import os, sys, platform
        from pathlib import Path
    ''') + "\n" + "\n".join(f"{name} = {values[name]!r}" for name in (
        "PROJECT_ROOT", "PATH_CONFIG", "MOUNT_DRIVE", "SOURCE_ARCHIVE", "SOURCE_DIRECTORY", "RUN_HISTORICAL_INSPECTION")) + '''

print("[1/4] Kernel đang thực thi notebook", flush=True)
print("Python:", sys.version.split()[0])
print("Hệ điều hành:", platform.system())
print("Interpreter:", sys.executable)
print("Thư mục kernel:", Path.cwd())
print("Source:", PROJECT_ROOT or "tự tìm từ CWD/Drive hoặc ZIP đã chọn")
print("SOURCE_ARCHIVE:", SOURCE_ARCHIVE or "chưa chọn ZIP")
print("Mount Drive theo yêu cầu:", MOUNT_DRIVE)
print("Hiện bảng và hình phân tích lịch sử:", RUN_HISTORICAL_INSPECTION)
print("Nếu muốn chạy Colab, interpreter/thư mục phải thuộc runtime Linux từ xa, không phải ổ D: của Windows.")
''')
    # Keep the standard-library bootstrap, removing settings now owned by the first cell.
    start = BOOTSTRAP.index("# Defaults sinh")
    head = BOOTSTRAP[:BOOTSTRAP.index("# Đường dẫn")]
    bootstrap = head + BOOTSTRAP[start:]
    insertion = '''
print("[2/4] Kiểm tra runtime, Drive và mã nguồn trước khi import src...", flush=True)
capabilities = detect_capabilities()
print("Nhận diện Colab:", capabilities.colab_runtime_detected,
      "; có API Drive:", capabilities.drive_api_available)
if MOUNT_DRIVE and not capabilities.colab_runtime_detected:
    raise RuntimeError(
        "Bạn yêu cầu mount Drive nhưng kernel hiện tại chưa được nhận diện là Colab. "
        "Xem interpreter/hệ điều hành ở cell 1; chọn đúng kernel Colab từ xa trong VS Code. "
        "Với local hoặc remote Jupyter đã có storage đồng bộ, giữ MOUNT_DRIVE=False. "
        "Có google.colab không bảo đảm giao diện VS Code hỗ trợ xác thực Drive."
    )
drive_point = Path(os.environ.get("DISEASE_DRIVE_MOUNT", BOOTSTRAP_DEFAULTS["drive_mount"]))
if MOUNT_DRIVE:
    print("Mount Drive theo lựa chọn trước khi tìm ZIP/source...", flush=True)
    mount_drive_at(drive_point)
if SOURCE_ARCHIVE is not None:
    if PROJECT_ROOT is not None:
        raise ValueError("Khi dùng SOURCE_ARCHIVE mới, đặt PROJECT_ROOT=None để không chọn nhầm source cũ.")
    drive_project = Path(os.environ.get("DISEASE_DRIVE_PROJECT", BOOTSTRAP_DEFAULTS["project_relative"]))
    if not drive_project.is_absolute():
        drive_project = drive_point / drive_project
    archive_path = resolve_source_archive(
        SOURCE_ARCHIVE, drive_mount=drive_point,
        search_roots=(Path(BOOTSTRAP_DEFAULTS["ephemeral_root"]), drive_point / "MyDrive",
                      drive_project, drive_project / "dist", Path.cwd() / "dist"))
    SOURCE_ARCHIVE = archive_path
    print("ZIP source trên kernel:", archive_path, flush=True)
    if SOURCE_DIRECTORY is None:
        # Explicit archive selection opts into extraction; isolate by content, never overwrite old code.
        bundle_id = hashlib.sha256(archive_path.read_bytes()).hexdigest()[:16]
        local_base = Path(BOOTSTRAP_DEFAULTS["ephemeral_root"]) if capabilities.colab_runtime_detected else Path.cwd()
        SOURCE_DIRECTORY = local_base / ".phase2-source" / bundle_id
    print("Giải nén source được chọn vào:", SOURCE_DIRECTORY, flush=True)
PHASE2_REQUIRED_FILES = ''' + repr(PHASE2_REQUIRED_FILES) + "\n"
    bootstrap = bootstrap.replace("ROOT = bootstrap_project(", insertion + "\nROOT = bootstrap_project(", 1)
    bootstrap = bootstrap.replace("mount_requested=MOUNT_DRIVE,", "mount_requested=False,", 1)
    bootstrap = bootstrap.replace("source_archive=SOURCE_ARCHIVE, source_directory=SOURCE_DIRECTORY)",
                                  "source_archive=SOURCE_ARCHIVE, source_directory=SOURCE_DIRECTORY, required_files=PHASE2_REQUIRED_FILES)", 1)
    tail = setup.source[setup.source.index("import numpy as np"):]
    tail = tail.replace("import numpy as np\nimport pandas as pd", '''try:
    import numpy as np
    import pandas as pd
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        f"Thiếu dependency notebook: {exc.name}. Sau khi source có tại {ROOT}, cài chủ động bằng "
        f"%pip install -r {str(ROOT / 'requirements-notebooks.txt')!r}; restart kernel rồi Run All."
    ) from exc''', 1)
    tail = tail.replace("RUN_HISTORICAL_INSPECTION = True\n", "", 1)
    tail = tail.replace("source_path = dataset_path(runtime_paths, config)", '''print("Source Phase 2 đầy đủ:", ROOT, flush=True)
print("Runtime dữ liệu:", runtime_paths.runtime, "; output persistent:", runtime_paths.output_root)
source_path = dataset_path(runtime_paths, config)
print("Đọc CSV:", source_path, flush=True)''', 1)
    tail += '''
display(Markdown("### Dữ liệu đầu vào đã xác thực"))
display(pd.DataFrame([{"Bản ghi raw": len(df), "Bệnh": df[phase2_policy["target"]].nunique(),
                       "Triệu chứng raw": df.shape[1] - 1, "Seed đã duyệt": phase2_policy["seed"]}]))
print("Không có cài gói, tải CSV hay mount Drive ngầm. Source và dữ liệu có thể nằm ở hai vị trí khác nhau.")
'''
    setup.source = bootstrap + "\n" + tail
    # Show stale imported packages explicitly instead of silently using another checkout.
    setup.source = setup.source.replace("from src.data.paths import resolve_paths", '''loaded_src = sys.modules.get("src")
if loaded_src is not None and getattr(loaded_src, "__file__", None):
    if Path(loaded_src.__file__).resolve().parent != (ROOT / "src").resolve():
        raise RuntimeError("Kernel đang cache src từ source cũ. Restart kernel sau khi đổi SOURCE_ARCHIVE/PROJECT_ROOT rồi Run All.")
from src.data.paths import resolve_paths''', 1)
    cells[0].source = md('''
        # 02 — Tiền xử lý dữ liệu theo chính sách đã duyệt

        Chạy **Run All** từ trên xuống: **1. Cấu hình kernel → 2. Source và CSV →
        3. Pipeline đã duyệt → 4. Kết quả, kiểm chứng và lưu file**.
        Bảng số lượng và kết quả nằm ngay trong luồng chính. Các bảng và hình phân tích lịch sử
        ở cuối cũng hiển thị mặc định (`RUN_HISTORICAL_INSPECTION=True`).

        **VS Code dùng kernel Colab:** cả `src/` và `configs/` phải có trên runtime Linux.
        Chỉ mở file `.ipynb` trên máy Windows hoặc đặt CSV trên Drive chưa cung cấp mã nguồn.
        Nếu báo thiếu `src.data.preprocessing_inspection`, dùng ZIP source Phase 2 mới,
        không dùng ZIP cũ chỉ có Phase 1. Xem cell cấu hình và hướng dẫn ngay dưới.
        Không fit transformer, chọn đặc trưng, PCA hay huấn luyện mô hình.
        ''').source
    approved = next(c for c in cells if c.cell_type == "markdown" and "## 8. Approved preprocessing" in c.source)
    approved.source = approved.source.replace("## 8. Approved preprocessing pipeline — kết quả cuối", "## 3. Pipeline tiền xử lý đã duyệt")
    process = next(c for c in cells if c.cell_type == "code" and "finalized = preprocess_dataset" in c.source)
    process.source = code('''
        print("[3/4] Bỏ cột → exact dedup → ≥10 vector/lớp → group split seed 42...", flush=True)
        finalized = preprocess_dataset(df, phase2_policy)
        labels = {
            "validated_raw": "1. Xác thực raw",
            "removed_ambiguous_features": "2. Bỏ hai cột regurgitation",
            "exact_dedup_remaining_vector_and_label": "3. Dedup vector còn lại + nhãn",
            "recalculated_independent_vectors_per_class": "4. Đếm lại vector mỗi bệnh",
            "eligible_classes_after_schema_and_dedup": "5. Giữ bệnh ≥10 vector",
            "generated_remaining_vector_groups": "6. Tạo group theo vector còn lại",
            "validated_final_split_total": "7. Hoàn tất và kiểm chứng split",
        }
        steps_view = finalized["steps"].rename(columns={"step": "Bước", "records": "Bản ghi", "classes": "Lớp bệnh", "symptom_features": "Triệu chứng"})
        steps_view["Bước"] = steps_view["Bước"].map(labels)
        display(steps_view)
        from IPython.display import HTML
        kpis = [("Bản ghi cuối", len(finalized["data"])), ("Lớp bệnh", len(finalized["classes"])),
                ("Triệu chứng trước variance", len(finalized["features"]))]
        display(HTML('<div style="display:flex;gap:12px;flex-wrap:wrap">' + ''.join(
            f'<div style="border:1px solid #94a3b8;border-radius:8px;padding:14px 20px">'
            f'<div style="font-size:24px;font-weight:bold">{value:,}</div><div>{label}</div></div>'
            for label, value in kpis) + '</div>'))
        removed_duplicates = len(df) - int(finalized["steps"].set_index("step").loc["exact_dedup_remaining_vector_and_label", "records"])
        excluded = int((~finalized["class_inventory"]["eligible"]).sum())
        display(Markdown(f"Đã bỏ **2 cột mơ hồ**, loại **{removed_duplicates:,} bản sao dư** sau bỏ cột "
                         f"và loại **{excluded} lớp dưới ngưỡng 10**. Giữ nhãn khác nhau của cùng vector; "
                         "mọi cột hằng vẫn ở schema để xử lý chỉ trên train trong giai đoạn training."))
        print("Fingerprint processed:", finalized["processed_sha256"])
        ''').source
    validation = next(c for c in cells if c.cell_type == "code" and 'display(finalized["split_summary"]' in c.source)
    validation.source = code('''
        print("[4/4] Kết quả split và kiểm chứng", flush=True)
        summary = finalized["split_summary"].rename(columns={"split": "Tập", "dedup_records": "Bản ghi", "pct_records": "Tỷ lệ %", "groups": "Group", "classes": "Lớp bệnh"})
        display(summary.round({"Tỷ lệ %": 4}))
        v = finalized["validation"]
        checks = [{"Kiểm tra": "Exact duplicate (vector, nhãn)", "Kết quả": str(v["exact_duplicate_rows"])},
                  {"Kiểm tra": "Tái tính assignment/support với seed 42", "Kết quả": "Khớp hoàn toàn" if v["deterministic_assignment_recomputed"] else "Không đạt"}]
        checks.extend({"Kiểm tra": f"Giao vector {pair}", "Kết quả": str(count)} for pair, count in v["symptom_vector_overlaps"].items())
        checks.extend({"Kiểm tra": f"Lớp vắng ở {name}", "Kết quả": str(len(missing))} for name, missing in v["missing_classes"].items())
        display(pd.DataFrame(checks))
        display(pd.DataFrame([{"Lớp chỉ 1 vector validation": v["singleton_validation_classes"],
                               "Lớp chỉ 1 vector test": v["singleton_test_classes"],
                               "Nhóm nhiều nhãn được giữ": v["conflicting_groups_preserved"]}]))
        display(Markdown("**Giới hạn:** đủ mặt lớp không bảo đảm metric từng bệnh ổn định. "
                         "Test được khóa cho đánh giá cuối; không dùng chọn feature/hyperparameter. "
                         "Chưa fit VarianceThreshold, PCA hay mô hình."))
        ''').source
    export = next(c for c in cells if c.cell_type == "code" and "manifest = export_preprocessed" in c.source)
    export.source = code('''
        print("[4/4] Kiểm tra/lưu dữ liệu và artifact persistent...", flush=True)
        already_finalized = (OUTPUT.metadata_dir / "phase2/dataset_manifest.json").is_file()
        manifest = export_preprocessed(finalized, source_path, OUTPUT, expected_source_sha256=source_sha)
        report_path = OUTPUT.reports_dir / "preprocessing_decision_review.md"
        if not report_path.is_file():
            report_path = write_review(OUTPUT, preprocessing_report(finalized, manifest), {}, update_report=True)
        assert sha256_file(source_path) == source_sha, "CSV raw thay đổi!"
        display(Markdown("### Hoàn tất Phase 2"))
        print("Trạng thái:", "đã kiểm chứng và tái sử dụng bộ split đã khóa, không ghi đè" if already_finalized else "đã tạo bộ split cuối")
        display(pd.DataFrame([
            {"Nội dung": "Train / validation / test (CSV.gz)", "Vị trí trên runtime": str(OUTPUT.processed_dir)},
            {"Nội dung": "Schema, label mapping, policy, fingerprint, split metadata", "Vị trí trên runtime": str(OUTPUT.metadata_dir / "phase2")},
            {"Nội dung": "Báo cáo", "Vị trí trên runtime": str(report_path)},
        ]))
        print("Môi trường tạo bộ split gốc:", manifest["environment"])
        print("Kernel hiện tại:", sys.version.split()[0], "; NumPy", np.__version__, "; pandas", pd.__version__)
        print("Raw trước/sau cùng SHA-256. Dừng sau preprocessing; chưa huấn luyện hoặc triển khai chatbot.")
        ''').source
    # Retain every historical cell and its ID; move it after the visible final workflow.
    main_ids = {cells[0].id, setup.id, approved.id, process.id, validation.id, export.id}
    history = [c for c in cells if c.id not in main_ids]
    for cell in history:
        if cell.cell_type == "code":
            cell.metadata.setdefault("jupyter", {}).update(source_hidden=False, outputs_hidden=False)
            cell.metadata["collapsed"] = False
    return [cells[0], configuration, md('''
        ## 2. Chuẩn bị mã nguồn và dữ liệu trên kernel

        - Source đã đồng bộ đầy đủ: đặt `PROJECT_ROOT` tới thư mục **trên runtime** có `src/`, `configs/`; giữ `SOURCE_ARCHIVE=None`.
        - Source cũ/thiếu module: upload ZIP mới từ `scripts/package_colab.py`, đặt `SOURCE_ARCHIVE` tới đường dẫn ZIP thực trên runtime và `PROJECT_ROOT=None`. `SOURCE_DIRECTORY=None` tự giải nén vào thư mục riêng theo checksum, không ghi đè source cũ.
        - CSV trên Drive: mount bằng giao diện được hỗ trợ, hoặc bật `MOUNT_DRIVE=True` khi kernel Colab/giao diện hỗ trợ. VS Code không tự cung cấp Drive. Không bật mount trên kernel Windows.
        - ZIP trên Google Drive: `SOURCE_ARCHIVE` phải trỏ tới file dưới Drive đã kết nối (thường `/content/drive/MyDrive/...`), gồm đúng thư mục và tên ZIP. Upload lên Drive không tự tạo file `/content/<tên ZIP>`. Khi đường dẫn sai, cell dưới liệt kê ZIP nhìn thấy và trạng thái Drive; có thể tìm lại cùng tên trong các thư mục chuẩn, không tự chuyển sang ZIP khác tên.
        - Sau khi đổi source, **restart kernel rồi Run All** để không dùng module `src` cache từ bản cũ. Nếu thiếu dependency, cài chủ động theo `requirements-notebooks.txt`; notebook không tự cài/tải file.
        '''), setup, approved, process, md("## 4. Kết quả chia tập và kiểm chứng"), validation,
            md("### Lưu hoặc tái sử dụng bộ dữ liệu đã khóa\n\nCác file cũ chỉ được tái sử dụng sau kiểm checksum, schema, policy, label mapping, assignment và mọi hàng dữ liệu. Khác phiên bản Python/NumPy/pandas giữa local và Colab không tự gây ghi đè test. Output dùng storage persistent đã cấu hình; source/cache có thể ở ổ tạm."),
            export, md('''
        # Phụ lục — lịch sử kiểm tra trước phê duyệt

        Luồng chính đã hoàn tất ở trên. Các bảng và hình dưới hiển thị mặc định với
        `RUN_HISTORICAL_INSPECTION=True` trong cell 1. Nếu chỉ muốn chạy pipeline cuối,
        đặt cờ này thành `False`; mỗi cell sẽ báo rõ đã bỏ qua. Các phân tích này giữ nguyên
        các giả định/đề xuất tại thời điểm kiểm tra cũ; chính sách hiện hành là bỏ hai cột,
        ≥10 và seed 42. Hình được dựng trong bộ nhớ, không ghi đè báo cáo/hình đã lưu.
        '''), *history]


def cleanup_phase2_cells(cells):
    """Keep five visible sections and one optional history cell; preserve runtime settings."""
    if any("PHASE2_CLEANUP_V3" in c.source for c in cells):
        raise ValueError("Notebook đã được rút gọn; không chèn lặp.")
    intro = cells[0]
    configuration = next(c for c in cells if "PHASE2_PRESENTATION_V2" in c.source)
    setup = next(c for c in cells if c.cell_type == "code" and "source_path = dataset_path" in c.source)
    approved = next(c for c in cells if c.cell_type == "markdown" and "## 3. Pipeline" in c.source)
    process = next(c for c in cells if c.cell_type == "code" and "finalized = preprocess_dataset" in c.source)
    verification = next(c for c in cells if c.cell_type == "code" and 'v = finalized["validation"]' in c.source)
    artifacts = next(c for c in cells if c.cell_type == "code" and "manifest = export_preprocessed" in c.source)
    history = [c for c in cells if c.cell_type == "code" and c.source.startswith("if RUN_HISTORICAL_INSPECTION:")]
    intro.source = md('''
        # 02 — Preprocessing đã hoàn tất

        **Run All** để xem dữ liệu đầu vào, các bước xử lý, split và kiểm chứng artifact.
        Kết quả chính luôn hiển thị với `RUN_HISTORICAL_INSPECTION=False`.
        Các phân tích trước phê duyệt nằm ở phụ lục tùy chọn và báo cáo đã lưu.

        ## 1. Runtime và cấu hình

        Đường dẫn thuộc máy chạy kernel; Colab cần cả source và bộ split đã khóa trên storage
        được cấu hình. Source ZIP và CSV có thể ở hai nơi khác nhau. Xem [hướng dẫn](../README.md).
        ''').source
    configuration.source = (configuration.source.split('print("[1/4]', 1)[0]
                            .replace("RUN_HISTORICAL_INSPECTION = True", "RUN_HISTORICAL_INSPECTION = False"))
    configuration.source += '''# PHASE2_CLEANUP_V3 — cờ trên chỉ điều khiển phụ lục lịch sử.
print(f"Kernel: {platform.system()} | Python {sys.version.split()[0]} | {sys.executable}")
print("Phân tích lịch sử:", RUN_HISTORICAL_INSPECTION, "; mount Drive theo yêu cầu:", MOUNT_DRIVE)
'''
    # Leave the stable standard-library bootstrap intact; trim only its data-loading tail.
    prefix = setup.source.split("try:\n    import numpy as np", 1)[0]
    prefix = prefix.replace('[2/4]', '[2/5]')
    setup.source = prefix + code('''
        try:
            import numpy as np
            import pandas as pd
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                f"Thiếu {exc.name}. Cài chủ động: %pip install -r {str(ROOT / 'requirements-notebooks.txt')!r}; restart kernel."
            ) from exc
        from IPython.display import display, Markdown
        from src.data.io import read_config
        from src.data.loader import dataset_path, prepare_dataset, load_dataset, sha256_file
        from src.data.paths import OutputPaths
        from src.data.preprocessing import read_phase2_policy, validate_raw_frame, preprocess_dataset, export_preprocessed

        phase2_policy = read_phase2_policy(ROOT)
        config = read_config(ROOT)
        if config["target"] != phase2_policy["target"]:
            raise ValueError("Nhãn Phase 1/Phase 2 không khớp.")
        OUTPUT = OutputPaths(runtime_paths.output_root)
        manifest_path = OUTPUT.metadata_dir / "phase2/dataset_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"Không thấy bộ Phase 2 đã khóa: {manifest_path}. Kiểm tra output root/Drive và đồng bộ "
                "data/processed/ cùng artifacts/metadata/phase2/. Notebook này không tái tạo bộ dữ liệu đã khóa."
            )
        locked_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_path = dataset_path(runtime_paths, config)
        source_sha = sha256_file(source_path)
        assert source_sha == locked_manifest["raw"]["sha256"], "CSV không khớp nguồn của bộ đã khóa."
        read_path = prepare_dataset(runtime_paths, source_path)
        assert sha256_file(read_path) == source_sha, "Cache khác CSV nguồn."
        df = load_dataset(read_path, config["target"])
        validate_raw_frame(df, phase2_policy)
        print(f"CSV: {source_path.name} | runtime dữ liệu: {runtime_paths.runtime}")
        display(pd.DataFrame([{"Bản ghi raw": len(df), "Lớp bệnh raw": df[config["target"]].nunique(),
                               "Triệu chứng raw": df.shape[1] - 1}]))
        ''').source
    approved.source = md('''
        ## 3. Pipeline preprocessing đã duyệt

        Xác thực raw → bỏ `regurgitation`/`regurgitation.1` → dedup **vector còn lại + nhãn** →
        đếm vector độc lập/lớp → giữ lớp ≥10 → group split 70/15/15, seed 42.
        Hai cột bị loại vì không xác minh được cách phân biệt khi thu nhận triệu chứng.
        Giữ các nhãn khác nhau của cùng vector. Tính lại trong RAM để đối chiếu bộ đã khóa;
        giữ nguyên raw và cột hằng. `VarianceThreshold(0)` chỉ fit trên train trong Phase 3.
        ''').source
    # Reuse the existing step table; remove duplicated cards/debug summaries.
    process.source = process.source[:process.source.index("from IPython.display import HTML")]
    process.source = process.source.replace('[3/4]', '[3/5]')
    process.source += '''print(f"Kết quả: {len(finalized['data']):,} bản ghi | {len(finalized['classes'])} lớp bệnh | "
      f"{len(finalized['features'])} triệu chứng trước variance removal.")
'''
    verification.source = code('''
        summary = finalized["split_summary"].rename(columns={"split": "Tập", "dedup_records": "Bản ghi",
            "pct_records": "Tỷ lệ %", "groups": "Group", "classes": "Lớp bệnh"})
        display(summary.round({"Tỷ lệ %": 4}))
        v = finalized["validation"]
        checks = [
            {"Kiểm tra": "Exact duplicate (vector, nhãn)", "Kết quả": v["exact_duplicate_rows"]},
            {"Kiểm tra": "Giao group giữa từng cặp split", "Kết quả": str(v["group_overlaps"])},
            {"Kiểm tra": "Giao vector (equality độc lập)", "Kết quả": str(v["symptom_vector_overlaps"])},
            {"Kiểm tra": "Lớp vắng train/validation/test", "Kết quả": str({k: len(x) for k, x in v["missing_classes"].items()})},
            {"Kiểm tra": "Tái lập assignment/support seed 42", "Kết quả": v["deterministic_assignment_recomputed"]},
        ]
        display(pd.DataFrame(checks))
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.5, 2.6))
        ax.barh(summary["Tập"], summary["Tỷ lệ %"], color=["#2563a6", "#d97706", "#15803d"])
        for name, records, percentage in summary[["Tập", "Bản ghi", "Tỷ lệ %"]].itertuples(index=False, name=None):
            ax.text(percentage + 1, name, f"{records:,} ({percentage:.2f}%)", va="center")
        ax.set(xlabel="% bản ghi", xlim=(0, 100), title="Bộ split đã khóa — seed 42")
        ax.invert_yaxis()
        fig.tight_layout()
        display(fig)
        plt.close(fig)
        print(f"Nhóm nhiều nhãn được giữ: {v['conflicting_groups_preserved']:,}. "
              f"Lớp chỉ có 1 vector validation/test: {v['singleton_validation_classes']}/{v['singleton_test_classes']}.")
        ''').source
    artifacts.source = code('''
        # Manifest phải tồn tại; export_preprocessed chỉ kiểm chứng/tái sử dụng bộ đã khóa.
        manifest_sha_before = sha256_file(manifest_path)
        manifest = export_preprocessed(finalized, source_path, OUTPUT, expected_source_sha256=source_sha)
        assert sha256_file(manifest_path) == manifest_sha_before, "Manifest đã khóa thay đổi."
        assert sha256_file(source_path) == source_sha, "Raw thay đổi."
        assert finalized["processed_sha256"] == manifest["processed"]["sha256"]
        print(f"ĐÃ TÁI SỬ DỤNG bộ split đã khóa; {len(manifest['files'])} checksum artifact hợp lệ.")
        display(pd.DataFrame([
            {"Artifact": "Train / validation / test", "Vị trí": str(OUTPUT.processed_dir)},
            {"Artifact": "Schema, label mapping, policy, assignment và split metadata", "Vị trí": str(OUTPUT.metadata_dir / "phase2")},
            {"Artifact": "Manifest", "Vị trí": str(manifest_path)},
        ]))
        print("SHA-256 raw:", manifest["raw"]["sha256"])
        print("Fingerprint processed:", manifest["processed"]["sha256"])
        display(Markdown("**Phase 2 đã kiểm chứng, sẵn sàng đọc train/validation bằng `load_final_split()`.** "
                         "Test chỉ dùng đánh giá cuối. Chưa fit transformer, huấn luyện mô hình hoặc triển khai chatbot."))
        ''').source
    bodies = []
    for cell in history:
        tree = ast.parse(cell.source)
        branch = tree.body[0]
        lines = cell.source.splitlines()
        bodies.append(textwrap.dedent("\n".join(lines[branch.body[0].lineno - 1:branch.body[-1].end_lineno])))
    history_cell = history[0]
    body = '''from src.data.audit import audit_dataset
from src.data.preprocessing_inspection import (
    inspect_header, inspect_regurgitation, class_eligibility, group_split_feasibility,
    threshold_split_comparison, both_features_removal_impact, threshold_comparison_figure,
)
audit = audit_dataset(df, config)
s = audit["summary"]
header = inspect_header(read_path)
''' + "\n\n".join(bodies)
    body = body.replace("Mốc ban đầu: ≥5 vector/lớp; đề xuất cập nhật nằm ở mục 7 sau so sánh 1/3/5/10/15.",
                        "Lịch sử dùng mốc ≥5; chính sách đã duyệt ở trên dùng ≥10 sau bỏ hai cột.")
    body = body.replace("Rà soát lịch sử đã xong; báo cáo cuối chỉ do mục 8 ghi sau khi kiểm chứng pipeline.",
                        "Phân tích lịch sử hoàn tất; bộ split và chính sách đã khóa giữ nguyên.")
    history_cell.source = ("if RUN_HISTORICAL_INSPECTION:\n" + textwrap.indent(body, "    ")
                           + '\nelse:\n    print("Lịch sử đã tắt; kết quả chính nằm ở 5 mục trên. Bật RUN_HISTORICAL_INSPECTION=True và Run All nếu cần xem lại.")')
    result = [intro, configuration, md('''
        ## 2. Nạp dữ liệu và xác thực

        Bootstrap hiện có kiểm source trước khi import; mount chỉ theo yêu cầu và khả năng của runtime.
        Output root phải chứa `data/processed/` và `artifacts/metadata/phase2/` đã khóa.
        Thiếu storage/artifact sẽ dừng để chỉnh đường dẫn, không tạo lại dataset.
        '''), setup, approved, process,
        md("## 4. Kiểm chứng split và trực quan kết quả\n\nĐộ phủ lớp không bảo đảm metric từng bệnh ổn định; số liệu test ở đây chỉ phục vụ kiểm tra toàn vẹn."), verification,
        md("## 5. Kiểm chứng artifact và tổng kết\n\nĐối chiếu dữ liệu vừa tính với schema, mapping, assignment và checksum đã lưu; tái sử dụng nguyên bộ file."), artifacts,
        md('''
        ### Phụ lục tùy chọn — lịch sử trước phê duyệt

        Mặc định tắt. Chi tiết đã lưu trong [báo cáo Phase 2](../reports/preprocessing_decision_review.md),
        [bảng lịch sử](../reports/tables/) và [hình so sánh ngưỡng](../reports/figures/preprocessing_threshold_comparison.png).
        Cell dưới tái hiện phân tích trên schema gốc khi bật cờ; các mốc ≥5/≥15 là đối chiếu lịch sử.
        **Quyết định cuối đã duyệt:** bỏ hai cột mơ hồ, dedup sau bỏ cột, ngưỡng ≥10 và split seed 42.
        '''), history_cell]
    for cell in result:
        if cell.cell_type == "code":
            cell.metadata.setdefault("jupyter", {}).update(source_hidden=False, outputs_hidden=False)
            cell.metadata["collapsed"] = False
            cell.metadata["scrolled"] = False
            compile(cell.source, "phase2-cleanup-cell", "exec")
    return result


if __name__ == "__main__":
    write_notebook("02_preprocessing.ipynb", inspection_cells())
