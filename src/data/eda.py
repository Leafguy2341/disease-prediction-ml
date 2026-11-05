"""Full-dataset descriptive EDA. Nothing here fits a predictive model."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .io import DatasetError, save_json, save_table
from .paths import output_paths


def analyze_eda(frame: pd.DataFrame, audit: dict, config: dict) -> dict:
    if not audit["summary"]["binary_complete"]:
        raise DatasetError("EDA triệu chứng yêu cầu đặc trưng 0/1 không thiếu. Xem audit; không tự impute hoặc ép giá trị.")
    if audit["summary"]["missing_target_rows"] or audit["summary"]["blank_target_rows"]:
        raise DatasetError("Nhãn thiếu/trống: cần quyết định dữ liệu trước khi EDA theo bệnh.")
    x = frame.drop(columns=config["target"])
    y = frame[config["target"]]
    n = len(frame)
    counts = y.value_counts().sort_index()
    active = x.sum(axis=1).astype(int)
    class_sums = x.groupby(y, sort=True).sum().astype(np.int64)
    class_profiles = class_sums.div(counts, axis=0)
    frequency = pd.DataFrame({"feature": x.columns, "present_count": x.sum().to_numpy(dtype=np.int64)})
    frequency["present_fraction"] = frequency["present_count"] / n
    frequency["diseases_with_symptom"] = (class_sums > 0).sum().to_numpy()
    frequency["dominant_disease"] = class_sums.idxmax().to_numpy()
    frequency.loc[frequency["present_count"] == 0, "dominant_disease"] = None
    frequency["dominant_disease_rows"] = class_sums.max().to_numpy()
    frequency["dominant_disease_share_when_present"] = np.divide(
        frequency["dominant_disease_rows"], frequency["present_count"],
        out=np.zeros(len(frequency), dtype=float), where=frequency["present_count"] > 0,
    )
    frequency = frequency.sort_values(["present_count", "feature"], ascending=[False, True]).reset_index(drop=True)
    active_distribution = active.value_counts().sort_index().rename_axis("active_symptoms").reset_index(name="rows")
    active_distribution["fraction"] = active_distribution["rows"] / n
    active_by_class = active.groupby(y).agg(["min", "median", "mean", "max", "std"]).reset_index()
    class_quantiles = counts.quantile([0, .01, .05, .25, .5, .75, .95, .99, 1]).rename_axis("quantile").reset_index(name="samples")
    # float64 accumulation: uint8 matrix multiplication would overflow silently.
    a = x.to_numpy(dtype=np.float64)
    cooccurrence = a.T @ a
    del a
    present = x.sum().to_numpy(dtype=np.float64)
    joint_probability = cooccurrence / n
    prevalence = present / n
    denominator = np.sqrt(np.outer(prevalence * (1 - prevalence), prevalence * (1 - prevalence)))
    correlation = np.divide(joint_probability - np.outer(prevalence, prevalence), denominator,
                            out=np.full_like(cooccurrence, np.nan), where=denominator > 0)
    union = present[:, None] + present[None, :] - cooccurrence
    jaccard = np.divide(cooccurrence, union, out=np.zeros_like(cooccurrence), where=union > 0)
    left, right = np.triu_indices(len(x.columns), 1)
    pairs = pd.DataFrame({
        "symptom_a": x.columns[left], "symptom_b": x.columns[right],
        "joint_rows": cooccurrence[left, right].astype(np.int64),
        "phi_correlation": correlation[left, right], "jaccard": jaccard[left, right],
    })
    strong = pairs[pairs["phi_correlation"].abs() >= config["correlation_threshold"]].sort_values(
        "phi_correlation", ascending=False)
    # Mean symptom profiles are descriptive, not a trained nearest-centroid classifier.
    profiles = class_profiles.to_numpy()
    lengths = np.linalg.norm(profiles, axis=1)
    product_lengths = np.outer(lengths, lengths)
    cosine = np.divide(profiles @ profiles.T, product_lengths,
                       out=np.zeros((len(profiles), len(profiles))), where=product_lengths > 0)
    i, j = np.triu_indices(len(profiles), 1)
    disease_pairs = pd.DataFrame({"disease_a": class_profiles.index[i], "disease_b": class_profiles.index[j],
                                  "cosine_similarity": np.clip(cosine[i, j], -1, 1)})
    group_support = audit["class_patterns"].set_index("disease")["unique_patterns"]
    for suffix in ["a", "b"]:
        disease_pairs["rows_" + suffix] = disease_pairs["disease_" + suffix].map(counts)
        disease_pairs["patterns_" + suffix] = disease_pairs["disease_" + suffix].map(group_support)
    disease_pairs = disease_pairs.sort_values(["cosine_similarity", "disease_a", "disease_b"], ascending=[False, True, True])
    supported_pairs = disease_pairs.query("rows_a >= 20 and rows_b >= 20 and patterns_a >= 5 and patterns_b >= 5")
    single_class_features = frequency.query("diseases_with_symptom == 1 and present_count > 0").copy()
    single_class_features["support_at_least_5"] = single_class_features["present_count"] >= 5
    one = class_sums.eq(counts, axis=0) & class_sums.gt(0)
    class_always_symptoms = one.stack()
    class_always_symptoms = class_always_symptoms[class_always_symptoms].index.to_frame(index=False)
    class_always_symptoms.columns = ["disease", "symptom"]
    class_always_symptoms["class_rows"] = class_always_symptoms["disease"].map(counts)
    groups = audit["pattern_groups"]
    conflicts = groups.query("distinct_labels > 1").sort_values(["distinct_labels", "rows"], ascending=False)
    first_rows = pd.DataFrame({"pattern_id": audit["pattern_ids"], "row_position": np.arange(n)}).drop_duplicates("pattern_id").set_index("pattern_id")["row_position"]
    examples = []
    for group in conflicts.head(20).itertuples(index=False):
        position = int(first_rows.loc[group.pattern_id])
        names = x.columns[x.iloc[position].to_numpy() == 1].tolist()
        labels = audit["pattern_labels"].loc[audit["pattern_labels"]["pattern_id"] == group.pattern_id]
        examples.append({"pattern_id": group.pattern_id, "active_symptoms": " | ".join(names),
                         "rows": group.rows, "distinct_labels": group.distinct_labels,
                         "label_counts": " | ".join(f"{row.disease}: {row.rows}" for row in labels.itertuples())})
    conflict_examples = pd.DataFrame(examples, columns=["pattern_id", "active_symptoms", "rows", "distinct_labels", "label_counts"])
    summary = {
        "class_count_quantiles": {str(q): float(v) for q, v in counts.quantile([0, .01, .05, .25, .5, .75, .95, .99, 1]).items()},
        "imbalance_max_min_ratio": float(counts.max() / counts.min()),
        "majority_class_fraction": float(counts.max() / n),
        "top20_class_fraction": float(counts.nlargest(20).sum() / n),
        "class_sample_mean": float(counts.mean()),
        "active_symptoms_quantiles": {str(q): float(v) for q, v in active.quantile([0, .25, .5, .75, .95, 1]).items()},
        "active_symptoms_mean": float(active.mean()), "all_zero_rows": int(active.eq(0).sum()),
        "single_symptom_rows": int(active.eq(1).sum()),
        "always_absent_symptoms": int((present == 0).sum()), "always_present_symptoms": int((present == n).sum()),
        "single_class_symptoms": len(single_class_features),
        "single_class_symptoms_support_ge5": int(single_class_features["support_at_least_5"].sum()),
        "high_absolute_correlation_pairs": len(strong),
        "high_correlation_pairs_joint_ge10": int((strong["joint_rows"] >= 10).sum()),
        "rows_in_repeated_patterns_fraction": audit["summary"]["rows_in_repeated_patterns"] / n,
        "excess_repeated_patterns_fraction": audit["summary"]["repeated_pattern_excess_rows"] / n,
        "conflicting_rows_fraction": audit["summary"]["rows_in_conflicting_patterns"] / n,
        "recommendation": audit["summary"]["recommendation"],
    }
    return {"summary": summary, "symptom_frequency": frequency, "active_distribution": active_distribution,
            "active_by_class": active_by_class, "class_quantiles": class_quantiles,
            "class_profiles": class_profiles, "class_profile_counts": class_sums,
            "cooccurrence": pd.DataFrame(cooccurrence.astype(np.int64), index=x.columns, columns=x.columns),
            "correlation": pd.DataFrame(correlation, index=x.columns, columns=x.columns),
            "jaccard": pd.DataFrame(jaccard, index=x.columns, columns=x.columns),
            "symptom_pairs": pairs.sort_values("joint_rows", ascending=False), "strong_correlations": strong,
            "similar_diseases": disease_pairs.head(1000), "supported_similar_diseases": supported_pairs.head(100),
            "single_class_features": single_class_features, "class_always_symptoms": class_always_symptoms,
            "conflict_examples": conflict_examples}


def export_eda(root, eda):
    save_json(output_paths(root).reports_dir / "eda_metrics.json", eda["summary"])
    for name, table in eda.items():
        if isinstance(table, pd.DataFrame):
            save_table(root, "eda_" + name, table,
                       index=name in {"class_profiles", "class_profile_counts", "cooccurrence", "correlation", "jaccard"})
