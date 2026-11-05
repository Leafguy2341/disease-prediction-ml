"""Read-only tuned-checkpoint evaluation using the original Phase 4 voting engine."""
from __future__ import annotations

from copy import deepcopy
import gc
import io
import json

import numpy as np
import pandas as pd

from src.data.loader import sha256_file
from src.models.ensemble import BASELINE, HARD, SOFT, PRIORITY, Phase4, require, score_prediction
from src.models.runtime import MODEL_NAMES
from src.models.training import (atomic_bytes, build_pipeline, experiment_identity,
                                 json_bytes, read_completed_checkpoint)
from src.models.tuning import (SOURCE_FILES, _paths, digest, read_tuning_result, search_plan)


class TunedPhase4(Phase4):
    """Reuse Phase4 hard/soft methods, probability memmaps, guards and checkpoint loader.

    Do not export the inherited Phase3-specific PrefittedVoting definition: this
    experiment produces a recommendation only, never a replacement application model.
    """
    def definition(self, key):
        raise NotImplementedError("Tuned run chỉ xuất kết quả/đề xuất; không xuất wrapper tham chiếu namespace Phase3.")

    def verify_tuned(self, result, baseline, *, trusted=False):
        require(trusted, "Chỉ load checkpoint tuned của chính dự án; trusted=True.")
        self.result, self.baseline = result, baseline
        self.inputs, self.x, self.y, self.groups = baseline.inputs, baseline.x, baseline.y, baseline.groups
        self.features, self.classes = baseline.features, baseline.classes
        self.experiment = result["experiment_id"]
        meta, self.run, _ = _paths(self.paths.storage_root, self.experiment)
        descriptor = json.loads((meta / "experiment.json").read_text(encoding="utf-8"))
        plan = search_plan(self.session.config)
        require(result["plan"] == descriptor["plan"] == plan, "Tuning search plan khác source hiện tại.")
        config = deepcopy(self.session.config)
        config["resources"] = plan["resources"]
        expected_base = experiment_identity(self.paths.project_root, config, self.inputs)
        require(descriptor["base"] == expected_base and descriptor["baseline_experiment"] == baseline.experiment,
                "Tuning khác input/source/library/config baseline hiện tại.")
        source = {name: sha256_file(self.paths.project_root / name) for name in SOURCE_FILES}
        require(source == descriptor["source_sha256"], "Source tuning/ensemble thay đổi; không load nhầm run.")
        config["models"] = {name: result["selection"][name]["parameters"] for name in MODEL_NAMES}
        config["run_tag"] = "tuned-v1"
        identity = experiment_identity(self.paths.project_root, config, self.inputs)
        identity.pop("experiment_id")
        identity["source_sha256"].update(source)
        identity["tuning_experiment"] = self.experiment
        identity["selection_sha256"] = sha256_file(meta / "selection.json")
        identity["experiment_id"] = config["run_tag"] + "-" + digest(identity)[:16]
        require(result["identity"] == identity, "Selected identity không khớp schema/mapping/CV/config/source/environment.")
        self.identity, self.config = identity, config
        self.current = experiment_identity(self.paths.project_root, config, self.inputs)
        self.metadata, self.predictions, self.identities = {}, {}, {}
        rows = []
        with self.guard():
            for name in MODEL_NAMES:
                metadata, prediction = read_completed_checkpoint(self.run / name, identity, self.y, self.groups)
                self.metadata[name], self.predictions[name], self.identities[name] = metadata, prediction, identity
                # Sequential load, then release. Verify actual pipeline feature/class order.
                model = self._load(name, trusted=True)
                try:
                    require(model.feature_names_in_.tolist() == self.features, "Tuned pipeline feature ordering sai.")
                    expected = build_pipeline(name, config)
                    require([key for key, _ in model.steps] == [key for key, _ in expected.steps]
                            and all(type(actual) is type(reference) and actual.get_params(deep=False) == reference.get_params(deep=False)
                                    for (_, actual), (_, reference) in zip(model.steps, expected.steps)),
                            "Tuned pipeline khác tham số đã chọn/VarianceThreshold(0).")
                finally:
                    del model
                    gc.collect()
                rows.append({"model": name, "checkpoint": "PASS", "schema": "PASS", "classes": len(self.classes),
                             "validation_alignment": "PASS", "macro_f1": metadata["metrics"]["macro_f1"]})
        self.records = {BASELINE: {"id": BASELINE, "mode": "single", "members": ["logistic_regression"],
            "status": "completed", "tie_rows": 0,
            **score_prediction(self.y, self.predictions["logistic_regression"], len(self.classes))}}
        for name in MODEL_NAMES:
            if name != "logistic_regression":
                key = "single_" + name
                self.records[key] = {"id": key, "mode": "single", "members": [name], "status": "completed", "tie_rows": 0,
                                    **score_prediction(self.y, self.predictions[name], len(self.classes))}
        return pd.DataFrame(rows)

    def table(self):
        table = super().table()  # Original metrics and selected checkpoint byte/time references.
        table["source"] = "tuned"
        table["delta_macro_f1_vs_lr"] = table["macro_f1"] - self.baseline.records[BASELINE]["macro_f1"]
        row = self.baseline.table().iloc[0].to_dict()
        row.update(combination="baseline_logistic_regression", source="verified_baseline", delta_macro_f1_vs_lr=0.0)
        return pd.concat([pd.DataFrame([row]), table], ignore_index=True)

    def recommendation(self):
        """Metric first; exact ties use explicit cost proxies, never an invented F1 tolerance."""
        table = self.table()
        ready = table.loc[table["status"] == "completed"].copy()
        members = {key: value["members"] for key, value in self.records.items()}
        ready["knn_cost_proxy"] = ready["combination"].map(lambda key: int("knn" in members.get(key, ())))
        best = ready.sort_values(["macro_f1", "base_models", "knn_cost_proxy", "pipeline_bytes", "combination"],
                                 ascending=[False, True, True, True, True], kind="stable").iloc[0]
        return {"candidate": best["combination"], "source": best["source"], "macro_f1": float(best["macro_f1"]),
                "policy": "validation Macro F1; exact tie -> fewer pipelines -> no KNN -> fewer compressed bytes -> stable ID",
                "cost_limitation": "Resource proxies, not latency. Saved prediction-time sums can come from different runtime sessions; no SLA.",
                "application_model_changed": False, "locked_test_evaluated": False}


def evaluate_tuned_ensemble(session, *, enabled=False, experiment=None, trusted=False):
    """Disabled/missing runs do not affect the baseline notebook. Never calls fit."""
    if not enabled:
        print("SKIPPED: RUN_TUNED_ENSEMBLE=False; không load tuned/predict/ghi artifact.")
        return None
    try:
        result = read_tuning_result(session.paths.storage_root, experiment)
    except FileNotFoundError as exc:
        print(str(exc))
        return None
    baseline = Phase4(session)
    baseline.verify()
    phase = TunedPhase4(session)
    try:
        verification = phase.verify_tuned(result, baseline, trusted=trusted)
        phase.evaluate_hard()
        probability_summary = phase.prepare_probabilities(trusted=trusted)
        phase.evaluate_soft()
        table, recommendation = phase.table(), phase.recommendation()
        with phase.guard():
            output = phase.paths.new_run("tuned-ensemble")
            files = {}

            def save(path, payload):
                require(not path.exists(), f"Không ghi đè artifact: {path}")
                atomic_bytes(path, payload)
                files[path.relative_to(phase.output.root).as_posix()] = {
                    "sha256": sha256_file(path), "bytes": path.stat().st_size}

            save(output.tables_dir / "tuned_validation_comparison.csv", table.to_csv(index=False, lineterminator="\n").encode("utf-8"))
            stream = io.BytesIO()
            np.savez_compressed(stream, y_true=phase.y, group_id=phase.groups, row_0based=np.arange(len(phase.y)), **phase.ensemble_predictions)
            save(output.metadata_dir / "tuned_ensemble_predictions.npz", stream.getvalue())
            report = {"run_id": output.run_id, "tuning_experiment": phase.experiment,
                "tuning_manifest_sha256": sha256_file(_paths(phase.paths.storage_root, phase.experiment)[0] / "manifest.json"),
                "selected_identity": phase.identity, "records": table.astype(object).where(pd.notna(table), None).to_dict(orient="records"),
                "recommendation": recommendation, "limitations": phase.limitations, "probability_sources": phase.probability_sources,
                "hard": HARD, "soft": SOFT, "hard_tie_priority": list(PRIORITY),
                "soft_tie_rule": "exact mean tie -> LR probability -> English label Unicode order",
                "base_models_fitted": 0, "test_payload_opened": False, "guards": dict(phase.guards)}
            save(output.metadata_dir / "tuned_results.json", json_bytes(report))
            save(output.reports_dir / "tuned_ensemble_validation.md",
                 ("# Tuned ensemble validation\n\n" + json.dumps(recommendation, ensure_ascii=False, indent=2)
                  + "\n\nChưa thay model mặc định hoặc mở locked test. Xác suất chưa được calibration.\n").encode("utf-8"))
            report["files"] = files
            atomic_bytes(output.metadata_dir / "tuned_ensemble_manifest.json", json_bytes(report))
        print("Tuned ensemble đã lưu:", output.metadata_dir / "tuned_ensemble_manifest.json")
        return {"verification": verification, "probabilities": probability_summary, "comparison": table,
                "recommendation": recommendation, "manifest": str(output.metadata_dir / "tuned_ensemble_manifest.json")}
    finally:
        phase.close()
        baseline.close()
