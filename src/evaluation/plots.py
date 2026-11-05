"""Readable descriptive charts with bounded label counts; PNG and SVG exports."""
from __future__ import annotations

import textwrap
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from src.data.paths import output_paths


def configure_plots():
    sns.set_theme(style="whitegrid", context="notebook", font="DejaVu Sans")
    plt.rcParams.update({"figure.dpi": 100, "axes.unicode_minus": False, "svg.fonttype": "none"})


def wrap(value, width=32):
    return "\n".join(textwrap.wrap(str(value), width))


def save_figure(root, name, fig):
    folder = output_paths(root).figures_dir
    folder.mkdir(parents=True, exist_ok=True)
    for extension in ["png", "svg"]:
        fig.savefig(folder / f"{name}.{extension}", dpi=150, bbox_inches="tight", facecolor="white")
    return fig


def class_distribution(root, audit):
    counts = audit["class_distribution"]["samples"]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.5), layout="constrained")
    ax[0].hist(counts, bins=min(35, max(5, len(counts))), color="#356c9b", edgecolor="white")
    ax[0].set(xlabel="Số dòng mỗi lớp", ylabel="Số lớp", title="Phân bố kích thước lớp")
    ax[1].plot(np.arange(1, len(counts) + 1), counts.sort_values(ascending=False), color="#b55535")
    ax[1].set(xlabel="Hạng lớp theo số dòng", ylabel="Số dòng (log)", yscale="log", title="Tần suất toàn bộ lớp theo thứ hạng")
    return save_figure(root, "01_class_distribution", fig)


def extremes(root, table, label, value, name, titles, nonzero=False, count=15):
    data = table[table[value] > 0] if nonzero else table
    # Deterministic ties use the name; do not silently hide zero-frequency columns.
    ordered = data.sort_values([value, label], ascending=[False, True])
    selections = [ordered.head(count), ordered.sort_values([value, label]).head(count)]
    fig, axes = plt.subplots(1, 2, figsize=(16, max(6, .47 * min(count, len(data)))), layout="constrained")
    for ax, selected, title, color in zip(axes, selections, titles, ["#356c9b", "#a45441"]):
        ax.barh(np.arange(len(selected)), selected[value], color=color)
        ax.set_yticks(np.arange(len(selected)), [wrap(v) for v in selected[label]], fontsize=9)
        ax.invert_yaxis()
        ax.set(title=title, xlabel="Số dòng", ylabel="")
        ax.xaxis.grid(True, alpha=.3)
        ax.yaxis.grid(False)
    return save_figure(root, name, fig)


def active_symptoms(root, eda):
    table = eda["active_distribution"]
    fig, ax = plt.subplots(figsize=(10, 4.7), layout="constrained")
    ax.bar(table["active_symptoms"], table["rows"], color="#387d72")
    ax.set(title="Số triệu chứng hoạt động trên mỗi dòng", xlabel="Số đặc trưng bằng 1", ylabel="Số dòng")
    return save_figure(root, "04_active_symptoms", fig)


def symptom_relationships(root, eda, count=15):
    names = eda["symptom_frequency"].query("present_count > 0")["feature"].head(count).tolist()
    labels = [wrap(v, 20) for v in names]
    fig, axes = plt.subplots(1, 2, figsize=(18, 10), layout="constrained")
    for ax, matrix, title, cmap, vmin, vmax in [
        (axes[0], eda["jaccard"], "Đồng xuất hiện: Jaccard", "YlGnBu", 0, 1),
        (axes[1], eda["correlation"], "Tương quan nhị phân: phi", "vlag", -1, 1),
    ]:
        selected = matrix.loc[names, names].copy()
        np.fill_diagonal(selected.values, np.nan)
        sns.heatmap(selected, ax=ax, cmap=cmap, vmin=vmin, vmax=vmax, square=True,
                    xticklabels=labels, yticklabels=labels, cbar_kws={"shrink": .6})
        ax.tick_params(axis="both", labelsize=8)
        ax.set_xticklabels(labels, rotation=65, ha="right")
        ax.set_title(title + f"\n{len(names)} triệu chứng phổ biến nhất")
    return save_figure(root, "05_symptom_relationships", fig)


def selected_diseases(root, audit, eda):
    # Four common classes plus two supported similar classes: explicit illustrative subset.
    diseases = audit["class_distribution"]["disease"].head(4).tolist()
    if len(eda["supported_similar_diseases"]):
        pair = eda["supported_similar_diseases"].iloc[0]
        diseases += [pair["disease_a"], pair["disease_b"]]
    diseases = list(dict.fromkeys(diseases))
    table = eda["class_profiles"].loc[diseases]
    names = table.max().sort_values(ascending=False).head(20).index
    counts = audit["class_distribution"].set_index("disease")["samples"]
    fig, ax = plt.subplots(figsize=(15, max(5.5, len(diseases) * .8)), layout="constrained")
    sns.heatmap(table[names], ax=ax, cmap="YlGnBu", vmin=0, vmax=1,
                xticklabels=[wrap(v, 20) for v in names],
                yticklabels=[wrap(f"{d} (n={counts[d]})", 32) for d in diseases],
                cbar_kws={"label": "Tỷ lệ triệu chứng = 1 trong lớp"})
    ax.set_xticklabels(ax.get_xticklabels(), rotation=60, ha="right", fontsize=8)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=9)
    ax.set(xlabel="Triệu chứng có tỷ lệ cao nhất trong nhóm minh họa", ylabel="Bệnh (tên nhãn nguyên gốc)",
           title="Profile triệu chứng: bốn lớp phổ biến và cặp gần nhau đủ support")
    return save_figure(root, "06_selected_disease_profiles", fig)


def similar_diseases(root, eda):
    table = eda["supported_similar_diseases"].head(12)
    fig, ax = plt.subplots(figsize=(13, 8), layout="constrained")
    labels = [wrap(f"{r.disease_a} / {r.disease_b}", 48) for r in table.itertuples()]
    ax.barh(np.arange(len(table)), table["cosine_similarity"], color="#6a548b")
    ax.set_yticks(np.arange(len(table)), labels, fontsize=9)
    ax.invert_yaxis()
    ax.set(xlim=(0, 1.02), xlabel="Cosine giữa profile trung bình (0–1)", ylabel="",
           title="Các cặp bệnh có profile gần nhau\nChỉ xét mỗi bệnh ≥20 dòng và ≥5 vector khác nhau")
    if table.empty:
        ax.text(.5, .5, "Không có cặp thỏa ngưỡng support", ha="center", transform=ax.transAxes)
    return save_figure(root, "07_similar_disease_profiles", fig)


def redundancy(root, audit):
    groups = audit["pattern_groups"]
    classes = audit["class_patterns"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    sizes = groups["rows"].value_counts().sort_index()
    axes[0].scatter(sizes.index, sizes.values, s=18, color="#356c9b")
    axes[0].set(xscale="log", yscale="log", xlabel="Số dòng trong một vector (log)",
                ylabel="Số vector (log)", title="Mức lặp của vector triệu chứng")
    colors = np.where(classes["rows_in_conflicting_patterns"] > 0, "#b55535", "#356c9b")
    axes[1].scatter(classes["total_rows"], classes["unique_patterns"], c=colors, s=17, alpha=.65)
    upper = max(classes["total_rows"].max(), classes["unique_patterns"].max())
    axes[1].plot([1, upper], [1, upper], "k--", alpha=.5, label="1 dòng / vector")
    axes[1].set(xscale="log", yscale="log", xlabel="Số dòng mỗi lớp (log)", ylabel="Số vector mỗi lớp (log)",
                title="Support theo dòng và theo vector\nCam: lớp có dòng thuộc vector xung đột")
    axes[1].legend(fontsize=8)
    return save_figure(root, "08_redundancy", fig)
