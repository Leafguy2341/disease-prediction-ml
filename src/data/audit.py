"""Exact duplicate analysis and descriptive quality checks; no learned transforms."""
from __future__ import annotations

from collections import defaultdict
import re

import numpy as np
import pandas as pd


def exact_pattern_ids(features: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Exact equality, not a probabilistic hash; NA is a value for grouping.

    Binary vectors are losslessly packed into fixed-width byte strings. The
    fallback uses pandas MultiIndex equality for mixed/non-binary audit inputs.
    IDs depend on this file's row order and feature order; retain its SHA-256.
    """
    if features.isin([0, 1]).all().all():
        values = features.to_numpy(dtype=np.uint8)
        packed = np.ascontiguousarray(np.packbits(values, axis=1))
        keys = packed.view(np.dtype((np.void, packed.shape[1]))).ravel()
        codes, _ = pd.factorize(keys, sort=False)
    else:
        codes, _ = pd.factorize(pd.MultiIndex.from_frame(features), sort=False)
    codes = codes.astype(np.int64)
    return codes, np.bincount(codes)


def audit_dataset(frame: pd.DataFrame, config: dict) -> dict:
    target = config["target"]
    x, y = frame.drop(columns=target), frame[target]
    n = len(frame)
    features = []
    for name, col in x.items():
        counts = col.value_counts(dropna=False)
        numeric = pd.api.types.is_numeric_dtype(col)
        valid_binary = bool(col.dropna().isin([0, 1]).all())
        invalid = col.notna() & ~col.isin([0, 1])
        features.append({
            "feature": name, "input_dtype": frame.attrs.get("input_dtypes", {}).get(name, str(col.dtype)),
            "memory_dtype": str(col.dtype), "meaning": "Symptom indicator; English name, no verified clinical dictionary",
            "n_unique_nonmissing": int(col.nunique()), "missing_count": int(col.isna().sum()),
            "missing_pct": float(col.isna().mean() * 100), "is_binary_observed": valid_binary,
            "invalid_binary_count": int(invalid.sum()),
            "invalid_examples": "; ".join(map(str, col[invalid].unique()[:5])),
            "min": float(col.min()) if numeric and col.notna().any() else None,
            "max": float(col.max()) if numeric and col.notna().any() else None,
            "dominant_fraction": float(counts.iloc[0] / n),
            "constant": bool(col.nunique(dropna=False) == 1),
            "near_constant": bool(counts.iloc[0] / n >= config["near_constant_threshold"]),
            "present_count": int(col.eq(1).sum()) if valid_binary else None,
            "present_fraction": float(col.eq(1).mean()) if valid_binary else None,
        })
    feature_table = pd.DataFrame(features)
    missing = frame.isna().sum().rename_axis("column").reset_index(name="missing_count")
    missing["missing_pct"] = missing["missing_count"] / n * 100
    missing["blank_string_count"] = [
        int(frame[c].map(lambda v: isinstance(v, str) and not v.strip()).sum())
        if not pd.api.types.is_numeric_dtype(frame[c]) else 0 for c in missing["column"]
    ]
    missing["invalid_or_blank_count"] = missing["missing_count"] + missing["blank_string_count"]
    ids, counts = exact_pattern_ids(x)
    pairs = pd.DataFrame({"pattern_id": ids, "disease": y}).groupby(
        ["pattern_id", "disease"], dropna=False, sort=False
    ).size().reset_index(name="rows")
    pairs["missing_label_rows"] = np.where(pairs["disease"].isna(), pairs["rows"], 0)
    groups = pairs.groupby("pattern_id", sort=True).agg(
        rows=("rows", "sum"), distinct_labels=("disease", lambda s: s.nunique(dropna=True)),
        majority_label_rows=("rows", "max"),
        missing_label_rows=("missing_label_rows", "sum"),
    ).reset_index()
    # Count known labels only; missing labels are a separate quality issue.
    conflict = groups[groups["distinct_labels"] > 1]
    repeated = counts > 1
    distribution = y.value_counts(dropna=True).rename_axis("disease").reset_index(name="samples")
    distribution["fraction_all_rows"] = distribution["samples"] / n
    class_patterns = pairs[pairs["disease"].notna()].groupby("disease").agg(
        unique_patterns=("pattern_id", "nunique"), total_rows=("rows", "sum")
    ).reset_index()
    conflicted_ids = set(conflict["pattern_id"])
    class_conflicts = pairs[pairs["pattern_id"].isin(conflicted_ids)].groupby("disease")["rows"].sum()
    class_patterns["rows_in_conflicting_patterns"] = class_patterns["disease"].map(class_conflicts).fillna(0).astype(int)
    duplicate_columns = defaultdict(list)
    for name in x:
        if x[name].isin([0, 1]).all():
            duplicate_columns[np.packbits(x[name].to_numpy(dtype=np.uint8)).tobytes()].append(name)
    column_groups = pd.DataFrame([
        {"group_id": i, "n_features": len(names), "features": " | ".join(names),
         "constant": bool(x[names[0]].nunique(dropna=False) == 1)}
        for i, names in enumerate(duplicate_columns.values()) if len(names) > 1
    ], columns=["group_id", "n_features", "features", "constant"])
    aliases = []
    for name in x:
        base = re.sub(r"\.\d+$", "", name)
        if base != name and base in x:
            aliases.append({"feature": name, "base_name": base, "equal_values": bool(x[name].equals(x[base])),
                            "different_rows": int(x[name].ne(x[base]).sum())})
    leakage_names = [c for c in x if re.search(r"(^|[_\s])(label|target|diagnosis|disease|patient_id|record_id)($|[_\s])", c, re.I)]
    label_text = y.dropna().astype(str)
    normalized = label_text.str.strip().str.casefold()
    normalized_counts = pd.DataFrame({"original": label_text, "normalized": normalized}).drop_duplicates()
    label_collisions = normalized_counts.groupby("normalized")["original"].agg(list)
    label_collisions = label_collisions[label_collisions.map(len) > 1].reset_index(name="original_labels")
    blank_labels = int(y.map(lambda v: isinstance(v, str) and not v.strip()).sum())
    binary_complete = bool(feature_table["is_binary_observed"].all() and x.notna().all().all())
    summary = {
        "rows": n, "columns": len(frame.columns), "features": x.shape[1], "target": target,
        "classes": int(y.nunique()), "missing_cells": int(frame.isna().sum().sum()),
        "missing_target_rows": int(y.isna().sum()), "blank_target_rows": blank_labels,
        "invalid_binary_cells": int(feature_table["invalid_binary_count"].sum()), "binary_complete": binary_complete,
        "constant_features": int(feature_table["constant"].sum()),
        "near_constant_features_including_constant": int(feature_table["near_constant"].sum()),
        "exact_duplicate_excess_rows": int(n - len(pairs)),
        "rows_in_exact_duplicate_groups": int(pairs.loc[pairs["rows"] > 1, "rows"].sum()),
        "unique_feature_vectors": len(counts), "repeated_pattern_groups": int(repeated.sum()),
        "rows_in_repeated_patterns": int(counts[repeated].sum()),
        "repeated_pattern_excess_rows": int(n - len(counts)),
        "conflicting_pattern_groups": len(conflict), "rows_in_conflicting_patterns": int(conflict["rows"].sum()),
        "min_class_samples": int(distribution["samples"].min()) if len(distribution) else 0,
        "max_class_samples": int(distribution["samples"].max()) if len(distribution) else 0,
        "median_class_samples": float(distribution["samples"].median()) if len(distribution) else 0,
        "classes_with_lt5_rows": int((distribution["samples"] < 5).sum()),
        "classes_with_lt5_patterns": int((class_patterns["unique_patterns"] < 5).sum()),
        "classes_with_one_pattern": int((class_patterns["unique_patterns"] == 1).sum()),
        "name_leakage_candidates": leakage_names, "normalized_label_collisions": len(label_collisions),
    }
    if not (y.isna().any() or blank_labels):
        summary["empirical_pattern_majority_ceiling"] = float(groups["majority_label_rows"].sum() / n)
    else:
        summary["empirical_pattern_majority_ceiling"] = None
    fatal = summary["classes"] < 2 or not binary_complete or summary["missing_target_rows"] > 0 or blank_labels > 0
    concerns = (summary["constant_features"] or summary["conflicting_pattern_groups"] or
                summary["repeated_pattern_excess_rows"] or summary["classes_with_lt5_patterns"])
    summary["recommendation"] = "NO-GO" if fatal else "CONDITIONAL GO" if concerns else "GO"
    return {"summary": summary, "features": feature_table, "missing": missing,
            "pattern_ids": ids, "pattern_groups": groups, "pattern_labels": pairs,
            "class_distribution": distribution, "class_patterns": class_patterns,
            "duplicate_columns": column_groups,
            "alias_candidates": pd.DataFrame(aliases, columns=["feature", "base_name", "equal_values", "different_rows"]),
            "label_collisions": label_collisions}
