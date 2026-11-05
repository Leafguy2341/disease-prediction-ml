"""Concise validation-only comparisons, three figures and Phase 4 handoff metadata."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

from src.data.loader import sha256_file
from src.models.runtime import MODEL_NAMES
from src.models.training import atomic_bytes, json_bytes, read_completed_checkpoint

METRICS = ("accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1")


def comparison_table(records: list[dict]) -> pd.DataFrame:
    rows = []
    for record in records:
        rows.append({"model": record["model"], "status": record["status"],
                     **{name: record.get("metrics", {}).get(name) for name in METRICS},
                     **{name: record.get(name) for name in ("fit_seconds", "prediction_seconds", "n_retained_features", "sampled_peak_rss_mb")},
                     "warnings": len(record.get("warnings", [])), "error": record.get("error", "")})
    return pd.DataFrame(rows)


def save_comparison(records, output, identity) -> Path:
    path = output.tables_dir / f"phase3_{identity['experiment_id']}_validation_comparison.csv"
    atomic_bytes(path, comparison_table(records).to_csv(index=False, lineterminator="\n").encode("utf-8"))
    return path


def validation_figures(records, output, identity, data, inputs) -> list[tuple[str, object, Path]]:
    import matplotlib.pyplot as plt
    complete = [r for r in records if r["status"] in {"completed", "reused"}]
    if not complete:
        return []
    # Recalculate metrics from verified prediction payloads, including reused runs.
    predictions = {}
    for record in complete:
        folder = output.models_dir / "phase3" / identity["experiment_id"] / record["model"]
        verified, prediction = read_completed_checkpoint(folder, identity, data["validation"][1], data["validation"][2])
        if record["metrics"] != verified["metrics"]:
            raise ValueError("Comparison row khác validation predictions đã lưu.")
        predictions[record["model"]] = prediction
    table = comparison_table(complete).sort_values("macro_f1", ascending=False, kind="stable")
    names = table["model"].tolist()
    figures = []
    with plt.rc_context({"font.size": 10}):
        fig, ax = plt.subplots(figsize=(10, 4.6))
        x = np.arange(len(table))
        for offset, metric, color in [(-.25, "macro_f1", "#2563a6"), (0, "accuracy", "#15803d"), (.25, "weighted_f1", "#d97706")]:
            ax.bar(x + offset, table[metric], width=.24, label=metric, color=color)
        ax.set(xticks=x, xticklabels=names, ylim=(0, 1.06), ylabel="Validation score",
               title="Phase 3 — validation; primary metric: macro F1")
        ax.tick_params(axis="x", rotation=18)
        ax.legend(loc="upper right")
        fig.tight_layout()
        figures.append(("validation_performance", fig))
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
        for ax, column, title in zip(axes, ("fit_seconds", "prediction_seconds"), ("Fit trên train", "Predict validation")):
            ax.barh(names, table[column], color="#2563a6")
            ax.set(xlabel="Seconds (measured)", title=title)
            ax.invert_yaxis()
        fig.suptitle("Thời gian thực; checkpoint reused giữ thời gian của lần chạy gốc")
        fig.tight_layout()
        figures.append(("fit_prediction_time", fig))
        best = names[0]
        _, _, f1, support = precision_recall_fscore_support(
            data["validation"][1], predictions[best], labels=np.arange(len(inputs["labels"]["classes"])), zero_division=0)
        selected = np.argsort(f1, kind="stable")[:12]
        labels = [f"{inputs['labels']['classes'][i]} (n={int(support[i])})" for i in selected]
        fig, ax = plt.subplots(figsize=(11, max(3, len(selected) * .34 + 1.2)))
        ax.barh(labels, f1[selected], color="#d97706")
        ax.set(xlim=(0, 1.05), xlabel="Validation F1; n = support độc lập trong validation",
               title=f"Các lớp F1 thấp nhất — {best}; support nhỏ cần diễn giải thận trọng")
        ax.invert_yaxis()
        fig.tight_layout()
        figures.append(("difficult_classes", fig))
    result = []
    for name, fig in figures:
        path = output.figures_dir / f"phase3_{identity['experiment_id']}_{name}.png"
        stream = io.BytesIO()
        fig.savefig(stream, format="png", dpi=150, facecolor="white")
        atomic_bytes(path, stream.getvalue())
        result.append((name, fig, path))
    return result


def save_handoff(records, figures, output, identity, environment, comparison_path: Path) -> dict:
    complete = [r for r in records if r["status"] in {"completed", "reused"}]
    ready = {r["model"] for r in complete} == set(MODEL_NAMES)
    payload = {"phase": 3, "experiment_id": identity["experiment_id"], "identity": identity,
               "environment": environment, "phase4_ready": ready, "validation_only": True,
               "test_payload_opened": False, "selection_metric": "macro_f1", "zero_division": 0,
               "comparison_csv": str(comparison_path), "comparison_sha256": sha256_file(comparison_path),
               "models": [{"model": r["model"], "status": r["status"],
                           "checkpoint_dir": r.get("checkpoint_dir"), "metrics": r.get("metrics"),
                           "supports_predict_proba": r.get("supports_predict_proba"), "error": r.get("error")}
                          for r in records],
               "figures": [{"name": name, "path": str(path), "sha256": sha256_file(path)} for name, _, path in figures],
               "soft_voting": "LinearSVC has no predict_proba. Use compatible probability models or training-only group-aware calibration in a later phase; no fabricated probabilities."}
    path = output.metadata_dir / "phase3" / identity["experiment_id"] / "run_summary.json"
    atomic_bytes(path, json_bytes(payload))
    best = max(complete, key=lambda r: r["metrics"]["macro_f1"])["model"] if complete else "chưa có kết quả hoàn tất"
    table = comparison_table(records)
    # to_string avoids a notebook-only dependency on tabulate.
    report = (f"# Phase 3 — {identity['experiment_id']}\n\n"
              f"Runtime: {environment.get('runtime', 'not Colab verified')}; Drive read/write: {environment.get('drive_read_write_verified', False)}.\n\n"
              f"Hoàn tất {len(complete)}/{len(MODEL_NAMES)} mô hình. Macro F1 validation cao nhất: {best}. "
              f"Phase 4 ready: {ready}. Chưa mở/evaluate test; chưa huấn luyện ensemble.\n\n"
              f"```text\n{table.to_string(index=False)}\n```\n\n"
              "zero_division=0; macro scores tính trên đầy đủ label mapping. Thời gian reused thuộc lần fit/predict gốc. "
              "GPU không được các estimator sklearn CPU này sử dụng. Lớp có ít support validation cần diễn giải thận trọng.\n\n"
              f"Manifest Phase 3: `{path}`. Mỗi model có pipeline.joblib, fit.json, validation_predictions.npz và metadata.json "
              "khi validation hoàn tất. Pipeline fit-only vẫn giữ nếu predict lỗi. Chỉ deserialize pipeline do chính bạn tạo và tin cậy.\n\n"
              + payload["soft_voting"] + "\n")
    atomic_bytes(output.reports_dir / f"phase3_{identity['experiment_id']}.md", report.encode("utf-8"))
    return {"path": path, **payload}
