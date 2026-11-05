"""Read-only Phase 2 inspection. No fitted transforms or dataset/split exports."""
from __future__ import annotations

from collections import Counter
import csv
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from .audit import exact_pattern_ids
from .io import markdown_table
from .paths import OutputPaths


def inspect_header(path: Path) -> dict:
    """Read literal CSV names before any pandas name disambiguation."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        names = next(csv.reader(handle))
    counts = Counter(names)
    return {"columns": len(names), "duplicate_names": {k: v for k, v in counts.items() if v > 1},
            "regurgitation": counts["regurgitation"], "regurgitation.1": counts["regurgitation.1"]}


def inspect_regurgitation(frame: pd.DataFrame, audit: dict, target: str) -> dict:
    """Compare observed values/support; simulate projections without changing frame."""
    names = ["regurgitation", "regurgitation.1"]
    if not set(names).issubset(frame.columns):
        raise ValueError("Cần cả regurgitation và regurgitation.1 để kiểm tra; không tự tạo cột.")
    a, b = (frame[name].eq(1) for name in names)
    same = frame[names[0]].eq(frame[names[1]])
    counts = {"matching_rows": int(same.sum()), "differing_rows": int((~same).sum()),
              "regurgitation_ones": int(a.sum()), "regurgitation.1_ones": int(b.sum()),
              "both_ones": int((a & b).sum()), "exactly_one": int((a ^ b).sum())}
    support = pd.DataFrame({"disease": frame[target], "raw_rows": 1,
                            names[0] + "_raw_ones": a.astype(int), names[1] + "_raw_ones": b.astype(int),
                            "both_raw_ones": (a & b).astype(int), "xor_raw_ones": (a ^ b).astype(int)})
    support = support.groupby("disease", sort=True).sum()
    ids = audit["pattern_ids"]
    pairs = audit["pattern_labels"][["pattern_id", "disease"]]
    # Each (full vector, label) contributes one hypothetical deduplicated record.
    present = pd.DataFrame({"pattern_id": ids, "a": a, "b": b}).drop_duplicates("pattern_id").set_index("pattern_id")
    for name, key in zip(names, ["a", "b"]):
        unique_support = pairs.loc[pairs["pattern_id"].map(present[key])].groupby("disease").size()
        support[name + "_unique_vectors"] = unique_support.reindex(support.index, fill_value=0)
    support = support.loc[(support[names[0] + "_raw_ones"] + support[names[1] + "_raw_ones"]) > 0].reset_index()
    projections = projection_review(frame.drop(columns=target), ids, pairs,
                                    [(names[0],), (names[1],), tuple(names)])
    return {"counts": counts, "disease_support": support, "projections": projections}


def projection_review(features: pd.DataFrame, original_ids: np.ndarray,
                      pairs: pd.DataFrame, removals: list[tuple[str, ...]]) -> pd.DataFrame:
    """Quantify merges and new ambiguity after hypothetical column removal.

    new_conflicts_from_pure counts projected groups that become ambiguous although
    every constituent original vector had just one label. expanded_label_sets also
    includes already ambiguous groups whose union has more labels than any original.
    A change in the total conflict count alone can hide merges of existing conflicts.
    """
    original_groups, first = np.unique(original_ids, return_index=True)
    unique_x = features.iloc[first]
    original_labels = pairs.groupby("pattern_id")["disease"].nunique()
    rows = []
    for removed in removals:
        projected_x = unique_x.drop(columns=list(removed))
        if projected_x.shape[1]:
            projected, counts = exact_pattern_ids(projected_x)
        else:
            projected, counts = np.zeros(len(unique_x), dtype=np.int64), np.array([len(unique_x)])
        mapping = pd.Series(projected, index=original_groups)
        label_view = pairs.assign(projected=pairs["pattern_id"].map(mapping))
        labels = label_view.groupby("projected")["disease"].nunique().reindex(range(len(counts)))
        max_before = pd.DataFrame({"projected": projected,
                                   "labels_before": original_labels.reindex(original_groups).to_numpy()}).groupby("projected")["labels_before"].max().reindex(range(len(counts)))
        rows.append({"removed_columns": " + ".join(removed), "unique_vectors": len(counts),
                     "merged_groups": int((counts > 1).sum()),
                     "collapsed_original_vectors": int(len(original_groups) - len(counts)),
                     "conflicting_groups": int((labels > 1).sum()),
                     "new_conflicts_from_pure": int(((labels > 1) & (max_before == 1)).sum()),
                     "expanded_label_sets": int((labels > max_before).sum()),
                     "hypothetical_dedup_records": len(label_view.drop_duplicates(["projected", "disease"]))})
    return pd.DataFrame(rows)


def class_eligibility(pairs: pd.DataFrame, raw_rows: int, thresholds=(1, 3, 5, 10)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Unique-vector counts, not raw row counts. No class is actually removed."""
    if pairs.duplicated(["pattern_id", "disease"]).any():
        raise ValueError("pairs phải có đúng một dòng cho mỗi (vector, nhãn).")
    sizes = pairs.groupby("disease", sort=True).size().rename("unique_vectors")
    rows = []
    for minimum in thresholds:
        retained = sizes[sizes >= minimum]
        rows.append({"min_unique_vectors": minimum, "retained_classes": len(retained),
                     "excluded_classes": len(sizes) - len(retained), "dedup_records": int(retained.sum()),
                     "pct_of_dedup_records": float(retained.sum() / len(pairs) * 100),
                     "pct_of_raw_records": float(retained.sum() / raw_rows * 100),
                     "vectors_min": int(retained.min()) if len(retained) else 0,
                     "vectors_q25": float(retained.quantile(.25)) if len(retained) else 0,
                     "vectors_median": float(retained.median()) if len(retained) else 0,
                     "vectors_q75": float(retained.quantile(.75)) if len(retained) else 0,
                     "vectors_max": int(retained.max()) if len(retained) else 0})
    return pd.DataFrame(rows), sizes.reset_index()


def group_split_feasibility(pairs: pd.DataFrame, minimum=5, seed=42,
                            ratios=(.70, .15, .15), *, include_assignments=False) -> dict:
    """The established deterministic split; no persistence or fitted transforms.

    Inspection returns aggregates by default. The approved finalization path can
    explicitly request the group assignment to materialize the very same split.

    Seeded group permutation sets approximately 70/15/15 group quotas. Repair
    absent classes in ascending class-support order, moving a group only when
    *all* its labels still occur in the donor split. Choose the move with the
    smallest change in per-class absolute deviation from the requested ratios;
    break ties by group id. This heuristic does not guarantee coverage: report
    actual missing classes, including when a repair cannot find a safe donor.
    Every edge is one hypothetical exact-deduplicated record, regardless of its
    raw duplicate multiplicity. All conflicting labels travel with their vector.
    """
    ratios = np.asarray(ratios, dtype=float)
    if len(ratios) != 3 or (ratios <= 0).any() or not np.isclose(ratios.sum(), 1):
        raise ValueError("Cần ba tỷ lệ dương có tổng bằng 1.")
    if pairs.duplicated(["pattern_id", "disease"]).any():
        raise ValueError("Không được dùng trọng số dòng trùng thay cho vector độc lập.")
    sizes = pairs.groupby("disease").size()
    eligible = sizes.index[sizes >= minimum]
    edges = pairs.loc[pairs["disease"].isin(eligible), ["pattern_id", "disease"]]
    if edges.empty:
        raise ValueError("Không có lớp đủ ngưỡng để kiểm tra split.")
    groups, group_names = pd.factorize(edges["pattern_id"], sort=True)
    labels, label_names = pd.factorize(edges["disease"], sort=True)
    n_groups, n_labels = len(group_names), len(label_names)
    group_sizes = np.bincount(groups, minlength=n_groups)
    class_sizes = np.bincount(labels, minlength=n_labels)
    # CSR-like indexes avoid building copies of feature matrices or datasets.
    by_group = np.argsort(groups, kind="stable")
    group_offsets = np.r_[0, np.cumsum(group_sizes)]
    by_class = np.argsort(labels, kind="stable")
    class_offsets = np.r_[0, np.cumsum(class_sizes)]
    group_labels = lambda g: labels[by_group[group_offsets[g]:group_offsets[g + 1]]]
    order = np.random.default_rng(seed).permutation(n_groups)
    cuts = np.floor(np.cumsum(ratios)[:2] * n_groups).astype(int)
    assignment = np.empty(n_groups, dtype=np.int8)
    for split, selected in enumerate(np.split(order, cuts)):
        assignment[selected] = split
    support = np.zeros((3, n_labels), dtype=np.int64)
    np.add.at(support, (assignment[groups], labels), 1)
    desired = ratios[:, None] * class_sizes
    repairs = 0
    for label in np.argsort(class_sizes, kind="stable"):
        candidates = groups[by_class[class_offsets[label]:class_offsets[label + 1]]]
        for target in range(3):
            if support[target, label]:
                continue
            moves = []
            for group in candidates:
                donor = assignment[group]
                affected = group_labels(group)
                if donor == target or (support[donor, affected] <= 1).any():
                    continue
                cost = (np.abs(support[target, affected] + 1 - desired[target, affected])
                        - np.abs(support[target, affected] - desired[target, affected])
                        + np.abs(support[donor, affected] - 1 - desired[donor, affected])
                        - np.abs(support[donor, affected] - desired[donor, affected])).sum()
                moves.append((float(cost), int(group)))
            if moves:
                _, group = min(moves)
                donor = assignment[group]
                affected = group_labels(group)
                support[donor, affected] -= 1
                support[target, affected] += 1
                assignment[group] = target
                repairs += 1
    names = ["train", "validation", "test"]
    # Independently recompute support and intersections from per-record assignments.
    check = np.zeros_like(support)
    record_splits = assignment[groups]
    np.add.at(check, (record_splits, labels), 1)
    np.testing.assert_array_equal(check, support)
    group_sets = [set(edges.loc[record_splits == i, "pattern_id"]) for i in range(3)]
    overlaps = {f"{names[a]} / {names[b]}": len(group_sets[a] & group_sets[b]) for a, b in combinations(range(3), 2)}
    assert not any(overlaps.values()), "Vector triệu chứng xuất hiện ở nhiều split!"
    summary = pd.DataFrame([{"split": name, "dedup_records": int((record_splits == i).sum()),
                             "pct_records": float((record_splits == i).mean() * 100),
                             "groups": len(group_sets[i]), "classes": int((support[i] > 0).sum())}
                            for i, name in enumerate(names)])
    per_class = pd.DataFrame({"disease": label_names, "unique_vectors": class_sizes,
                              **{name: support[i] for i, name in enumerate(names)}})
    missing = {name: per_class.loc[per_class[name] == 0, "disease"].tolist() for name in names}
    assert int(summary["dedup_records"].sum()) == len(edges)
    assert int(summary["groups"].sum()) == n_groups
    result = {"summary": summary, "class_support": per_class, "missing_classes": missing,
              "overlaps": overlaps, "seed": int(seed), "minimum": int(minimum),
              "ratios": ratios.tolist(), "repairs": repairs}
    if include_assignments:
        result["group_assignment"] = pd.DataFrame({"group_id": group_names,
                                                  "split": np.asarray(names)[assignment]})
    return result


def threshold_split_comparison(pairs: pd.DataFrame, raw_rows: int,
                               thresholds=(1, 3, 5, 10, 15), seed=42) -> dict:
    """Reuse the established splitter unchanged, once for each requested threshold.

    Percent retained always uses the same pre-filter exact-deduplicated records.
    Splits are reallocated on each eligible population, not nested across thresholds.
    Singleton counts exclude absent classes: report absences separately.
    """
    eligibility, _ = class_eligibility(pairs, raw_rows, thresholds=thresholds)
    splits, rows = {}, []
    for minimum in thresholds:
        split = group_split_feasibility(pairs, minimum=minimum, seed=seed)
        support = split["class_support"]
        row = eligibility.loc[eligibility["min_unique_vectors"] == minimum].iloc[0].to_dict()
        for name in ("train", "validation", "test"):
            row[f"missing_{name}_classes"] = len(split["missing_classes"][name])
        for name in ("validation", "test"):
            row[f"singleton_{name}_classes"] = int(support[name].eq(1).sum())
        row["maximum_pairwise_group_overlap"] = max(split["overlaps"].values())
        assert split["summary"]["dedup_records"].sum() == row["dedup_records"]
        rows.append(row)
        splits[int(minimum)] = split
    table = pd.DataFrame(rows)
    for column in table.columns:
        if column.startswith(("pct_", "vectors_q", "vectors_median")):
            continue
        table[column] = table[column].astype(int)
    return {"comparison": table, "splits": splits, "seed": int(seed),
            "denominator_records": len(pairs), "original_classes": pairs["disease"].nunique()}


def both_features_removal_impact(frame: pd.DataFrame, audit: dict, target: str,
                                 minimum: int) -> dict:
    """Counterfactual on ALL (full original vector, label) pairs, before class filtering.

    Symptom columns are never used as labels. Duplicate multiplicity contributes
    no weight here. Projection also collapses same-label pairs that become equal;
    that extra hypothetical dedup count is reported separately from row selection.
    Only aggregates leave this function; source frame/schema are unchanged.
    """
    removed = ["regurgitation", "regurgitation.1"]
    if not set(removed).issubset(frame.columns) or target in removed:
        raise ValueError("Cần hai cột triệu chứng và nhãn bệnh riêng biệt.")
    pairs = audit["pattern_labels"][["pattern_id", "disease"]]
    if pairs.duplicated(["pattern_id", "disease"]).any():
        raise ValueError("Phải tính trên các cặp (vector đầy đủ, nhãn) duy nhất.")
    original_groups, first = np.unique(audit["pattern_ids"], return_index=True)
    x = frame.drop(columns=target).iloc[first]
    reduced = x.drop(columns=removed)
    if reduced.shape[1]:
        projected_ids, multiplicities = exact_pattern_ids(reduced)
    else:
        projected_ids, multiplicities = np.zeros(len(x), dtype=np.int64), np.array([len(x)])
    projection_map = pd.Series(projected_ids, index=original_groups)
    either_present = pd.Series(x[removed].eq(1).any(axis=1).to_numpy(), index=original_groups)
    edges = pairs.assign(projected=pairs["pattern_id"].map(projection_map),
                         either_present=pairs["pattern_id"].map(either_present))
    class_counts = edges.groupby("disease", sort=True).agg(
        unique_vectors_before=("pattern_id", "nunique"),
        unique_vectors_after=("projected", "nunique"),
        dedup_records_with_either=("either_present", "sum"),
    )
    class_counts["vectors_lost"] = class_counts["unique_vectors_before"] - class_counts["unique_vectors_after"]
    class_counts["pct_vectors_lost"] = class_counts["vectors_lost"] / class_counts["unique_vectors_before"] * 100
    class_counts["eligible_before"] = class_counts["unique_vectors_before"] >= minimum
    class_counts["eligible_after"] = class_counts["unique_vectors_after"] >= minimum
    affected = class_counts.loc[class_counts["dedup_records_with_either"] > 0].reset_index()
    affected = affected.sort_values(["vectors_lost", "disease"], ascending=[False, True]).reset_index(drop=True)
    lost = class_counts.index[class_counts["eligible_before"] & ~class_counts["eligible_after"]].tolist()
    gained = class_counts.index[~class_counts["eligible_before"] & class_counts["eligible_after"]].tolist()
    projection = projection_review(frame.drop(columns=target), audit["pattern_ids"], pairs, [tuple(removed)]).iloc[0]
    before_labels = pairs.groupby("pattern_id")["disease"].nunique()
    summary = {
        "class_filter_applied": False, "minimum_for_eligibility_comparison": int(minimum),
        "comparison_denominator_records": len(pairs), "disease_classes": len(class_counts),
        "records_with_either_feature_one": int(edges["either_present"].sum()),
        "raw_records_with_either_feature_one": int(frame[removed].eq(1).any(axis=1).sum()),
        "pct_records_with_either_feature_one": float(edges["either_present"].mean() * 100),
        "associated_disease_classes": len(affected),
        "unique_vectors_before": len(original_groups), "unique_vectors_after": len(multiplicities),
        "collapsed_original_vectors": len(original_groups) - len(multiplicities),
        "merged_projected_groups": int((multiplicities > 1).sum()),
        "original_vectors_in_merged_groups": int(multiplicities[multiplicities > 1].sum()),
        "conflicting_groups_before": int((before_labels > 1).sum()),
        "conflicting_groups_after": int(projection["conflicting_groups"]),
        "new_conflicts_from_pure": int(projection["new_conflicts_from_pure"]),
        "expanded_label_sets": int(projection["expanded_label_sets"]),
        "hypothetical_dedup_records_after_projection": int(projection["hypothetical_dedup_records"]),
        "classes_losing_independent_vectors": int(class_counts["vectors_lost"].gt(0).sum()),
        "eligible_classes_before": int(class_counts["eligible_before"].sum()),
        "eligible_classes_after": int(class_counts["eligible_after"].sum()),
        "eligible_records_before": int(class_counts.loc[class_counts["eligible_before"], "unique_vectors_before"].sum()),
        "eligible_records_after_projection": int(class_counts.loc[class_counts["eligible_after"], "unique_vectors_after"].sum()),
    }
    assert not gained, "Bỏ đặc trưng không thể làm tăng số vector độc lập trong một lớp."
    assert (class_counts["vectors_lost"] >= 0).all()
    assert int(class_counts["unique_vectors_before"].sum()) == len(pairs)
    assert int(class_counts["unique_vectors_after"].sum()) == summary["hypothetical_dedup_records_after_projection"]
    return {"summary": summary, "class_impact": affected,
            "associated_disease_names": sorted(affected["disease"].tolist()),
            "lost_eligible_classes": lost, "gained_eligible_classes": gained}


def threshold_comparison_figure(analysis: dict, output: OutputPaths, recommended=10, *, save=True):
    """Two panels; save=False renders in memory without touching existing reports."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator

    table = analysis["comparison"]
    x = np.arange(len(table))
    thresholds = table["min_unique_vectors"].to_numpy()
    colors = ["#d97706" if t == recommended else "#2563a6" for t in thresholds]
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10}):
        fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.2), gridspec_kw={"wspace": .3})
        fig.subplots_adjust(top=.8, bottom=.23, left=.07, right=.97)
        fig.suptitle("Ngưỡng vector triệu chứng độc lập: độ phủ lớp và bản ghi", fontsize=14, y=.96)
        fig.text(.5, .88, f"Cùng thuật toán chia group • seed {analysis['seed']} • màu cam: đề xuất ≥{recommended}", ha="center", fontsize=10)
        axes[0].bar(x, table["retained_classes"], color=colors, width=.6)
        axes[0].axhline(analysis["original_classes"], color="#64748b", linestyle="--", linewidth=1)
        axes[0].set_ylim(0, analysis["original_classes"] * 1.12)
        axes[0].set_title("Số lớp bệnh được giữ")
        axes[0].set_ylabel(f"Số lớp (ban đầu: {analysis['original_classes']})")
        for i, count in enumerate(table["retained_classes"]):
            axes[0].text(i, count + 14, f"{count:,}", ha="center", fontsize=11)
        pct = table["pct_of_dedup_records"].to_numpy()
        axes[1].plot(x, pct, color="#2563a6", linewidth=1.8)
        axes[1].scatter(x, pct, c=colors, s=65, zorder=3)
        axes[1].set_ylim(float(pct.min()) - .20, 100.22)
        axes[1].set_title("Tỷ lệ bản ghi được giữ — trục y thu hẹp")
        axes[1].set_ylabel("% bản ghi sau exact dedup, trước lọc lớp")
        axes[1].yaxis.set_major_locator(MultipleLocator(.2))
        for i, (percentage, records) in enumerate(zip(pct, table["dedup_records"])):
            axes[1].annotate(f"{percentage:.4f}%\n{records:,} bản ghi", (i, percentage),
                             xytext=(0, 12), textcoords="offset points", ha="center", fontsize=9,
                             bbox={"facecolor": "white", "edgecolor": "none", "alpha": .94, "pad": 1.5})
        for ax in axes:
            ax.set_xticks(x, [f"≥{t}" for t in thresholds])
            ax.set_xlabel("Số vector tối thiểu mỗi bệnh")
            ax.grid(axis="y", alpha=.2)
            ax.set_axisbelow(True)
            ax.spines[["top", "right"]].set_visible(False)
        fig.text(.5, .09, f"Mẫu số cố định: {analysis['denominator_records']:,} bản ghi sau exact dedup; chưa bỏ hai cột regurgitation.", ha="center", fontsize=9)
        fig.text(.5, .04, "Độ phủ lớp không bảo đảm đánh giá ổn định. Support validation/test được báo riêng; chưa huấn luyện mô hình.", ha="center", fontsize=9, color="#475569")
        path = output.figures_dir / "preprocessing_threshold_comparison.png"
        if save:
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path, dpi=160, facecolor="white", metadata={"Title": "Preprocessing threshold comparison"})
    return fig, path


def decision_table(minimum=5, seed=42, differing_columns=True) -> pd.DataFrame:
    return pd.DataFrame([
        {"Quy tắc": "1 = ghi nhận hiện diện; 0 = chưa ghi nhận hiện diện", "Trạng thái": "Giả định tạm thời đã thống nhất; thiếu định nghĩa từ nguồn"},
        {"Quy tắc": "Bỏ bản sao cùng vector và cùng nhãn; giữ khác nhãn", "Trạng thái": "Chính sách đã thống nhất; chưa áp dụng/lưu dữ liệu"},
        {"Quy tắc": "Không thay nhãn xung đột bằng nhãn đa số", "Trạng thái": "Đã thống nhất; giữ như giới hạn bài toán"},
        {"Quy tắc": "Tạm giữ hai cột regurgitation với tên gốc" if differing_columns else "Giữ một cột regurgitation, bỏ bản sao", "Trạng thái": "Cần người dùng duyệt schema trước triển khai"},
        {"Quy tắc": f"Ngưỡng ≥{minimum} vector đầy đủ/lớp", "Trạng thái": "Ứng viên đề xuất; cần người dùng duyệt"},
        {"Quy tắc": f"Group split khoảng 70/15/15, seed {seed}, bảo vệ độ phủ lớp", "Trạng thái": "Phép thử hoàn tất; cần duyệt trước khóa split"},
        {"Quy tắc": "Loại cột hằng bằng bước chỉ fit trên train", "Trạng thái": "Đề xuất cho pipeline sau; cần duyệt, chưa fit"},
    ])


def review_markdown(source_name: str, digest: str, audit: dict, header: dict,
                    reg: dict, eligibility: pd.DataFrame, split: dict) -> str:
    """Short, deterministic Vietnamese report derived only from measured results."""
    s, r = audit["summary"], reg["counts"]
    dedup = s["rows"] - s["exact_duplicate_excess_rows"]
    candidate = eligibility.loc[eligibility["min_unique_vectors"] == split["minimum"]].iloc[0]
    threshold_view = eligibility[["min_unique_vectors", "retained_classes", "excluded_classes", "dedup_records", "pct_of_dedup_records"]].round(4)
    threshold_view.columns = ["Ngưỡng vector/lớp", "Lớp giữ", "Lớp loại", "Dòng sau dedup", "% so với sau dedup"]
    distribution = eligibility[["min_unique_vectors", "vectors_min", "vectors_q25", "vectors_median", "vectors_q75", "vectors_max"]]
    projection = reg["projections"][["removed_columns", "unique_vectors", "merged_groups", "conflicting_groups", "new_conflicts_from_pure", "expanded_label_sets"]]
    support = split["class_support"]
    singleton_val = int(support["validation"].eq(1).sum())
    singleton_test = int(support["test"].eq(1).sum())
    reference = {"rows": 246945, "classes": 773, "features": 377, "constant_features": 49,
                 "conflicting_pattern_groups": 12634, "classes_with_lt5_patterns": 115}
    matches = sum(s[key] == value for key, value in reference.items())
    reg_recommendation = ("Hai cột khác nhau: đề xuất tạm giữ cả hai với đúng tên gốc, gắn cờ ngữ nghĩa chưa xác minh; không tự gộp/loại."
                          if r["differing_rows"] else "Hai cột giống nhau: đề xuất giữ một cột và bỏ bản sao sau khi được duyệt.")
    return f"""# Phase 2 — Kiểm tra và rà soát quyết định tiền xử lý

Chỉ kiểm tra trên toàn bộ CSV `{source_name}`; không fit transformer/mô hình, không xuất dữ liệu đã xử lý hay phân bổ từng dòng vào split.
SHA-256: `{digest}`. Đếm lại từ dữ liệu: **{s['rows']:,} dòng, {s['classes']} lớp, {s['features']} triệu chứng nhị phân, {s['constant_features']} cột hằng, {s['conflicting_pattern_groups']:,} vector có nhiều nhãn, {s['classes_with_lt5_patterns']} lớp dưới 5 vector**. Đối chiếu {matches}/{len(reference)} mốc đã báo cáo Phase 1 khớp; nếu không khớp đủ phải rà soát bằng số hiện tại.

Giả định tạm thời: 1 = triệu chứng được ghi nhận hiện diện; 0 = chưa được ghi nhận hiện diện, không chứng minh vắng mặt lâm sàng. Nguồn mô tả dữ liệu tổng hợp, thiếu định nghĩa mã hóa và từ điển triệu chứng; không gán thêm ý nghĩa y khoa.

## Dòng trùng và nhãn xung đột

Có **{s['exact_duplicate_excess_rows']:,} dòng dư** khi xét cả vector và nhãn ({s['rows_in_exact_duplicate_groups']:,} dòng nằm trong các nhóm bản sao, tính cả bản đầu). Theo chính sách đã thống nhất, dự kiến còn **{dedup:,} dòng**, trên **{s['unique_feature_vectors']:,} vector**. Giữ các nhãn khác nhau của cùng vector; không bỏ phiếu đa số. {s['conflicting_pattern_groups']:,} nhóm xung đột là giới hạn của bài toán. Các con số sau dedup chỉ được tính từ bảng tổng hợp (vector, nhãn), không tạo CSV đã làm sạch.

## Hai cột regurgitation

Đọc header CSV thô: {header['columns']} tên cột; tên trùng nguyên văn: `{header['duplicate_names']}`. `regurgitation` và `regurgitation.1` mỗi tên xuất hiện đúng một lần; hậu tố `.1` có sẵn trong file này, không phải pandas thêm khi đọc. Không đủ lịch sử để kết luận cách tên đó được tạo trước đây.

Hai cột khớp **{r['matching_rows']:,}** dòng, khác **{r['differing_rows']:,}** dòng. Số 1 lần lượt **{r['regurgitation_ones']:,} / {r['regurgitation.1_ones']:,}**; cả hai = 1: **{r['both_ones']:,}**; chỉ một = 1: **{r['exactly_one']:,}**. Support theo bệnh (dòng raw và vector độc lập) nằm trong `tables/preprocessing_regurgitation_support.csv`; notebook hiển thị toàn bộ {len(reg['disease_support'])} bệnh liên quan. Metadata hiện có không phân biệt được nghĩa của hai tên.

Các phép bỏ cột sau chỉ là giả lập trong RAM, vẫn giữ mọi lớp:

{markdown_table(projection)}

`merged_groups`: nhóm chiếu chứa nhiều vector gốc. `new_conflicts_from_pure`: nhóm mới có nhiều nhãn dù mọi vector gốc cấu thành chỉ có một nhãn. `expanded_label_sets`: số nhóm chiếu có nhiều nhãn hơn bất kỳ vector gốc cấu thành. Tổng nhóm xung đột còn chịu tác động gộp các nhóm đã xung đột, vì vậy không thể dùng riêng chênh lệch tổng để đếm xung đột mới. Bỏ cả hai mất {int(reg['projections'].iloc[-1]['collapsed_original_vectors']):,} phân biệt vector; không có cơ sở tự động loại.

**{reg_recommendation}** Cần người dùng duyệt trước khi xử lý schema.

## Điều kiện đủ lớp

Vector đầy đủ được dùng làm đơn vị độc lập theo dữ liệu quan sát; không chứng minh độc lập bệnh nhân. Mỗi (vector, nhãn) chỉ tính một lần. Mẫu số tỷ lệ chính là **{dedup:,} dòng sau exact dedup**, không phải {s['rows']:,} dòng raw. Bảng CSV kèm thêm tỷ lệ trên raw.

{markdown_table(threshold_view)}

Phân bố vector/lớp còn lại (phân vị nội suy của pandas):

{markdown_table(distribution)}

Đề xuất **≥{split['minimum']} vector/lớp**: giữ {int(candidate['retained_classes'])} lớp và {float(candidate['pct_of_dedup_records']):.4f}% dòng sau dedup. Ngưỡng 1 có lớp chỉ một vector, không thể phủ ba tập độc lập; ngưỡng 3 chỉ vừa đủ tối thiểu 1/1/1, rất ít thông tin cho train/đánh giá. Ngưỡng 10 loại thêm lớp so với 5 trong khi chia thử ở 5 đã phủ đủ lớp. Đây là cân nhắc độ phủ và khả năng đánh giá, không dựa vào điểm mô hình. Chưa áp dụng loại lớp.

## Khả thi chia nhóm

Chưa có thay đổi schema được duyệt: group dùng **đủ {s['features']} cột gốc**, gồm cả hai cột regurgitation. Sau khi giả định exact dedup và eligibility ≥{split['minimum']}, một lần thử với seed **{split['seed']}**: hoán vị group, chia hạn ngạch khoảng 70/15/15 theo số group; sau đó sửa thiếu lớp theo thứ tự support tăng dần. Chỉ chuyển group nếu mọi nhãn của nó vẫn còn trong tập cho; chọn chuyển có mức tăng sai lệch support so với tỷ lệ mục tiêu nhỏ nhất, hòa thì theo group ID. Có {split['repairs']} lần chuyển để bảo vệ độ phủ. Không tối ưu theo điểm mô hình. Thuật toán heuristic không bảo đảm mọi dữ liệu đều khả thi; số đo thực tế:

{markdown_table(split['summary'].round(4))}

Lớp vắng train: `{split['missing_classes']['train']}`; validation: `{split['missing_classes']['validation']}`; test: `{split['missing_classes']['test']}`.
Giao group kiểm tra trực tiếp từng cặp: `{split['overlaps']}`. Một vector và tất cả nhãn của nó luôn đi cùng tập. Bảng `preprocessing_class_support.csv` lưu support tổng hợp từng bệnh, gồm các lớp bị loại theo ứng viên; không lưu group/row assignment.

Đủ mặt lớp không đồng nghĩa đánh giá ổn định: {singleton_val} lớp chỉ có 1 vector ở validation, {singleton_test} lớp chỉ có 1 vector ở test. Báo cáo support cùng metric sau này; không tuyên bố độ tin cậy lâm sàng. Nếu đổi schema/ngưỡng phải đếm và kiểm tra chia lại; khóa test trước chọn mô hình. Phase 1 đã thăm dò toàn CSV nên đây không phải test hoàn toàn chưa từng được xem.

## Cột hằng và quyết định

Xác nhận **{s['constant_features']} cột hằng**; notebook liệt kê đủ tên và giá trị. Cùng giá trị ở mọi dòng nên không phân biệt lớp trong dữ liệu quan sát. Đề xuất `VarianceThreshold(0)` hoặc tương đương **chỉ fit trên train** trong pipeline sau khi chia, rồi áp dụng mask đã học cho validation/test; không fit trên toàn bộ CSV, không xóa raw. Không loại cột gần hằng ở bước này.

{markdown_table(decision_table(split['minimum'], split['seed'], bool(r['differing_rows'])))}

**Dừng tại rà soát; chờ người dùng duyệt.** Chưa tạo dữ liệu processed/interim, train/validation/test, chưa huấn luyện, chọn đặc trưng, PCA, ensemble hay chatbot. Môi trường chạy được ghi ở cell thiết lập notebook. Dùng bootstrap/config chung và hướng dẫn runtime hiện có khi chạy trên Colab; kiểm thử mô phỏng filesystem/capability không thay thế một lần chạy Colab thật.
"""


def final_decision_markdown(source_name: str, digest: str, audit: dict,
                            thresholds: dict, impact: dict, recommended=10) -> str:
    """Exactly the two requested analyses, replacing the earlier provisional review."""
    table, summary = thresholds["comparison"], impact["summary"]
    indexed = table.set_index("min_unique_vectors")
    candidate, five, fifteen = indexed.loc[recommended], indexed.loc[5], indexed.loc[15]
    split = thresholds["splits"][recommended]
    comparison = table[["min_unique_vectors", "retained_classes", "excluded_classes", "dedup_records",
                        "pct_of_dedup_records", "singleton_validation_classes", "singleton_test_classes"]].copy()
    comparison["missing_train_val_test"] = [
        f"{row.missing_train_classes}/{row.missing_validation_classes}/{row.missing_test_classes}"
        for row in table.itertuples()
    ]
    comparison["pct_of_dedup_records"] = comparison["pct_of_dedup_records"].round(4)
    comparison.columns = ["Ngưỡng", "Lớp giữ", "Lớp loại", "Bản ghi giữ", "% sau dedup",
                          "Lớp chỉ 1 vector val", "Lớp chỉ 1 vector test", "Lớp vắng train/val/test"]
    affected = impact["class_impact"].copy()
    affected["pct_vectors_lost"] = affected["pct_vectors_lost"].round(2)
    affected["eligibility_before_after"] = [
        f"{'có' if a else 'không'} → {'có' if b else 'không'}"
        for a, b in zip(affected["eligible_before"], affected["eligible_after"])
    ]
    affected = affected[["disease", "dedup_records_with_either", "unique_vectors_before", "unique_vectors_after",
                         "vectors_lost", "pct_vectors_lost", "eligibility_before_after"]]
    affected.columns = ["Bệnh", "Bản ghi có ≥1 cột=1", "Vector trước", "Vector sau", "Vector giảm", "% giảm", f"Đủ ≥{recommended} trước→sau"]
    top_absolute = "; ".join(f"{r.disease}: {r.unique_vectors_before} → {r.unique_vectors_after} (−{r.vectors_lost})"
                             for r in impact["class_impact"].head(3).itertuples())
    top_relative = impact["class_impact"].sort_values(["pct_vectors_lost", "disease"], ascending=[False, True]).iloc[0]
    s = audit["summary"]
    policies = pd.DataFrame([
        {"Chính sách đề xuất": "Exact dedup theo toàn bộ vector và nhãn; giữ các nhãn khác nhau", "Trạng thái": "Đã thống nhất; chưa áp dụng/lưu dataset"},
        {"Chính sách đề xuất": f"Ngưỡng ≥{recommended} vector đầy đủ/lớp", "Trạng thái": "Đề xuất mới thay ứng viên ≥5; chờ duyệt"},
        {"Chính sách đề xuất": "Hai cột regurgitation: hoãn quyết định bỏ/giữ cho pipeline cuối", "Trạng thái": "Tạm giữ schema hiện tại để kiểm tra; cần xác minh mapping"},
        {"Chính sách đề xuất": "Group split khoảng 70/15/15, seed 42; cùng vector cùng tập", "Trạng thái": "Đã thống nhất; chạy lại và khóa sau khi chốt schema/ngưỡng"},
        {"Chính sách đề xuất": "Mọi phép biến đổi học tham số chỉ fit trên train", "Trạng thái": "Đã thống nhất; chưa fit transformer hoặc mô hình"},
    ])
    return f"""# Phase 2 — Final Preprocessing Decision Analysis

Bản rà soát được cập nhật theo yêu cầu với **đúng hai phân tích A/B**; chưa thực hiện pipeline cuối cùng. CSV `{source_name}`, SHA-256 `{digest}`. Xác minh lại {s['rows']:,} dòng raw, {s['classes']} bệnh, {s['features']} đặc trưng nhị phân, {s['constant_features']} cột hằng, {s['conflicting_pattern_groups']:,} vector nhiều nhãn; {s['exact_duplicate_excess_rows']:,} dòng trùng dư và **{thresholds['denominator_records']:,} bản ghi sau exact dedup giả định**. Raw và mọi kết quả Phase 1 được giữ nguyên.

`1` = ghi nhận triệu chứng hiện diện; `0` = chưa ghi nhận hiện diện, không chứng minh vắng mặt lâm sàng. Đây là giả định tạm thời trên dữ liệu tổng hợp có tài liệu chưa đầy đủ. Hai tên `regurgitation` là **đặc trưng triệu chứng**, nhãn duy nhất vẫn là `{s['target']}`.

## A. So sánh ngưỡng số vector độc lập mỗi bệnh

Mẫu số tỷ lệ giữ là **{thresholds['denominator_records']:,} bản ghi sau exact dedup, trước lọc lớp**, cố định cho cả năm ngưỡng; một cặp (vector, nhãn) được tính một lần. Group dùng đủ {s['features']} cột gốc, chưa bỏ hai cột mơ hồ. Giữ nguyên thuật toán đã dùng: hoán vị group, hạn ngạch khoảng 70/15/15, sửa lớp vắng khi có chuyển group không làm mất lớp ở tập cho, tối thiểu sai lệch support rồi phá hòa theo group ID. Mỗi ngưỡng chạy đúng một lần với **seed {thresholds['seed']}**; không tìm seed tốt hơn, không dùng accuracy.

{markdown_table(comparison)}

![So sánh độ phủ lớp và bản ghi](figures/preprocessing_threshold_comparison.png)

Hình duy nhất gồm hai panel; **trục % bên phải được thu hẹp và ghi rõ** để thấy chênh lệch nhỏ. Số lớp chỉ có 1 vector không bao gồm lớp vắng; hai vấn đề được báo riêng trong bảng. Cả ba giao group đều bằng 0 ở mọi ngưỡng. Các tập đủ điều kiện được chia lại riêng theo cùng seed, không phải những split lồng nhau; thay đổi singleton còn chịu tác động tái phân bổ, không chứng minh quan hệ nhân quả riêng của việc loại lớp.

**Đề xuất ≥{recommended} vector/lớp** để cân bằng độ phủ bệnh và support đánh giá. So với ≥5, ≥{recommended} giữ ít hơn {int(five['retained_classes'] - candidate['retained_classes'])} lớp nhưng chỉ giảm {int(five['dedup_records'] - candidate['dedup_records'])} bản ghi, vẫn giữ {float(candidate['pct_of_dedup_records']):.4f}% bản ghi sau dedup; số lớp chỉ 1 vector val/test giảm từ {int(five['singleton_validation_classes'])}/{int(five['singleton_test_classes'])} xuống {int(candidate['singleton_validation_classes'])}/{int(candidate['singleton_test_classes'])} trong phép thử này. ≥15 giữ {int(fifteen['retained_classes'])} lớp và {float(fifteen['pct_of_dedup_records']):.4f}% bản ghi, còn {int(fifteen['singleton_validation_classes'])}/{int(fifteen['singleton_test_classes'])} lớp singleton; đổi từ {recommended} lên 15 mất thêm {int(candidate['retained_classes'] - fifteen['retained_classes'])} lớp/{int(candidate['dedup_records'] - fifteen['dedup_records'])} bản ghi. Chọn {recommended} là đánh đổi để giữ độ phủ lớp rộng hơn 15, không phải ngưỡng bảo đảm độ tin cậy thống kê. Ngưỡng 1 còn lớp vắng; ngưỡng 3 và 5 có nhiều singleton dù phủ đủ lớp.

Ở ứng viên ≥{recommended}, kết quả chia thử:

{markdown_table(split['summary'].round(4))}

Lớp vắng: `{split['missing_classes']}`. Giao group từng cặp: `{split['overlaps']}`. {int(candidate['singleton_validation_classes'])}/{int(candidate['singleton_test_classes'])} lớp chỉ có một vector validation/test vẫn là hạn chế đáng kể; metric từng bệnh cần báo kèm support, không suy ra đánh giá ổn định chỉ từ việc đủ mặt lớp. Kết quả chỉ mô tả một split seed 42, không phải kiểm chứng nhiều lần chia hay xác thực lâm sàng.

## B. Bỏ đồng thời hai đặc trưng regurgitation — chỉ giả định

**Phạm vi cố định:** toàn bộ {summary['comparison_denominator_records']:,} cặp (vector đầy đủ ban đầu, nhãn) sau exact dedup giả định, đủ {summary['disease_classes']} bệnh; **chưa áp dụng bất kỳ class filter nào**. Phần trăm trong phân tích B luôn lấy phạm vi này làm mẫu số. Bỏ cột chỉ được chiếu trong RAM; không xóa cột nguồn, không lưu bảng dữ liệu đã chiếu.

Có **{summary['records_with_either_feature_one']:,}/{summary['comparison_denominator_records']:,} bản ghi ({summary['pct_records_with_either_feature_one']:.4f}%)** có ít nhất một trong hai cột bằng 1, thuộc **{summary['associated_disease_classes']} bệnh**, được liệt kê đầy đủ bên dưới. Số này khác {summary['raw_records_with_either_feature_one']:,} dòng raw vì đã bỏ trọng số bản sao; con số raw chỉ đối chiếu lịch sử, không dùng làm mẫu số của phân tích B.

- Vector phân biệt toàn bộ dữ liệu: **{summary['unique_vectors_before']:,} → {summary['unique_vectors_after']:,}**.
- **{summary['original_vectors_in_merged_groups']:,} vector gốc** rơi vào **{summary['merged_projected_groups']:,} nhóm sau chiếu** chứa nhiều vector gốc; mất **{summary['collapsed_original_vectors']:,} phân biệt vector** (hiệu số trước/sau). Ba đại lượng này có nghĩa khác nhau.
- Nhóm nhiều nhãn: **{summary['conflicting_groups_before']:,} → {summary['conflicting_groups_after']:,}**. Có **{summary['new_conflicts_from_pure']} nhóm xung đột mới** dù mọi vector gốc cấu thành chỉ có một nhãn; **{summary['expanded_label_sets']} nhóm** có tập nhãn lớn hơn bất kỳ vector gốc cấu thành. Chênh lệch tổng {summary['conflicting_groups_after'] - summary['conflicting_groups_before']:+,} không phải số xung đột mới, vì một số nhóm đã xung đột cũng bị gộp.
- Nếu tiếp tục gộp các cặp chiếu cùng nhãn nay trở thành trùng, còn **{summary['hypothetical_dedup_records_after_projection']:,} cặp**, giảm {summary['comparison_denominator_records'] - summary['hypothetical_dedup_records_after_projection']:,}. Đây là kết quả giả định trên cùng tập bản ghi gốc, không phải dữ liệu processed đã xuất.

Support độc lập mỗi bệnh liên quan (không lọc lớp):

{markdown_table(affected, limit=len(affected))}

Giảm tuyệt đối lớn nhất: **{top_absolute}**. Giảm tương đối lớn nhất: **{top_relative['disease']}, {float(top_relative['pct_vectors_lost']):.2f}%**. {summary['classes_losing_independent_vectors']} bệnh mất vector độc lập trong nội bộ lớp; bệnh còn lại trong danh sách vẫn chỉ có 1 vector. Mất phân biệt toàn cục lớn hơn tổng giảm nội bộ lớp vì nhiều vector khác nhãn bị gộp mà cặp (vector, nhãn) vẫn được giữ. Các lớp luôn có hai bit bằng 0 không tự mất số vector nội bộ, nhưng vẫn có thể tham gia xung đột mới với lớp khác.

**Eligibility theo ứng viên ≥{recommended}: {summary['eligible_classes_before']} → {summary['eligible_classes_after']} lớp.** Lớp đang đủ ngưỡng bị mất eligibility: `{impact['lost_eligible_classes']}`; lớp mới đủ: `{impact['gained_eligible_classes']}`. Số cặp thuộc các lớp đủ ngưỡng trước/sau chiếu: {summary['eligible_records_before']:,} → {summary['eligible_records_after_projection']:,}, vẫn xét trên cùng phạm vi trước lọc. Trên CSV này, bỏ hai cột **không làm lớp nào trước đó đủ ngưỡng trở thành không đủ**; điều đó không có nghĩa thông tin không bị mất. Bảng duy nhất mới: `tables/preprocessing_regurgitation_removal_impact.csv`.

**Đề xuất: hoãn quyết định bỏ/giữ cho pipeline cuối; tạm giữ schema hiện tại khi kiểm tra.** Bỏ cả hai làm mất thông tin có thể đo được và tăng mơ hồ nhãn; giữ cả hai đòi hỏi xác minh được cách thu nhận hai bit. Chưa có từ điển nguồn phân biệt hai tên, nên không tự đặt hai định nghĩa y khoa. Chưa huấn luyện nên chưa thể kết luận accuracy sẽ tăng hay giảm sau bỏ cột.

Với chatbot tiếng Việt tương lai, không được tự tạo hai câu hỏi khác nghĩa từ hậu tố `.1`, hoặc gán cùng một mô tả người dùng vào cả hai cột. Cần mapping triệu chứng–đặc trưng đã xác minh và schema thống nhất giữa train và suy luận. Nếu mapping không thể xác minh, phải duyệt lại schema/nguồn dữ liệu trước tích hợp chatbot; không ngầm đặt các bit chưa biết thành kết luận vắng mặt lâm sàng.

## Chính sách đề xuất và điểm chưa chốt

{markdown_table(policies)}

Vector độc lập ở đây chỉ là vector phân biệt theo equality, không chứng minh độc lập bệnh nhân. Phase 1 đã xem toàn CSV nên chưa có final test hoàn toàn chưa từng thăm dò. Việc chạy notebook và test của bản cập nhật được kiểm tra trên Windows Python; **chưa có thực thi Colab thật**. Source/config/optional Drive mount dùng cơ chế portable hiện có, không cài gói hoặc tải file ngầm. Năm CSV Phase 2 cũ giữ như bằng chứng ban đầu (ứng viên ≥5); bảng ngưỡng và đề xuất cập nhật nằm trong notebook/báo cáo này, không xuất thêm CSV ngưỡng.

**DỪNG chờ duyệt:** chưa bỏ cột, lọc lớp thực tế, lưu tập train/validation/test, fit transformer, huấn luyện mô hình hay triển khai chatbot.
"""


def write_review(output: OutputPaths, report: str, tables: dict[str, pd.DataFrame], *, update_report=False) -> Path:
    """Write only Phase 2 aggregates; refuse to clobber differing prior results.

    An identical rerun is a no-op. Check every destination before writing any.
    update_report explicitly permits revising ONLY the named Phase 2 Markdown;
    existing CSVs and all Phase 1 files remain protected against content changes.
    No row IDs, split assignments or processed features are accepted here.
    """
    payloads = {output.reports_dir / "preprocessing_decision_review.md": report}
    for name, table in tables.items():
        if not name.startswith("preprocessing_") or Path(name).name != name:
            raise ValueError("Tên bảng phải là preprocessing_* trong reports/tables/.")
        if {"pattern_id", "projected", "assignment"}.intersection(table.columns):
            raise ValueError("Chỉ lưu bảng tổng hợp; không lưu phân bổ từng vector.")
        payloads[output.tables_dir / f"{name}.csv"] = table.to_csv(index=False, lineterminator="\n")
    for path, content in payloads.items():
        permitted_report_update = update_report and path == output.reports_dir / "preprocessing_decision_review.md"
        if path.exists() and path.read_text(encoding="utf-8-sig") != content and not permitted_report_update:
            raise FileExistsError(f"Giữ kết quả cũ: {path}. Chọn DISEASE_OUTPUT_DIR khác để tạo review mới.")
    for path, content in payloads.items():
        if not path.exists() or (update_report and path.suffix == ".md" and path.read_text(encoding="utf-8") != content):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8-sig" if path.suffix == ".csv" else "utf-8", newline="")
    return output.reports_dir / "preprocessing_decision_review.md"
