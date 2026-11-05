"""Short Colab notebook interface; existing loaders, training and reporting do the work."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from IPython.display import display
import matplotlib.pyplot as plt
import pandas as pd

from src.data.paths import OutputPaths, RuntimePaths
from src.data.colab_runtime import phase2_preflight
from src.models.runtime import (cache_training_inputs,
                                load_training_data, read_training_config, phase3_resources)
from src.models.training import experiment_identity, run_model_safely, train_models
from src.models.reporting import comparison_table, save_comparison, save_handoff, validation_figures


@dataclass
class ColabTraining:
    paths: RuntimePaths
    config: dict
    environment: dict
    inputs: dict
    data: dict | None = None
    identity: dict | None = None
    records: list = field(default_factory=list)
    comparison_path: Path | None = None

    @property
    def output(self) -> OutputPaths:
        return OutputPaths(self.paths.output_root)

    @classmethod
    def open(cls, runtime) -> "ColabTraining":
        if not all(hasattr(runtime, key) for key in ("paths", "environment", "inputs", "source_fingerprint")):
            raise TypeError("Chạy bootstrap_runtime dùng chung trước, rồi ColabTraining.open(RUNTIME).")
        paths = runtime.paths
        config = read_training_config(paths.project_root)
        inputs = phase2_preflight(runtime)
        if any(inputs["manifest"]["processed"].get(k) != v for k, v in config["expected_phase2"].items()):
            raise ValueError("Dữ liệu đã kiểm chứng khác fingerprint/số lượng Phase 3 được duyệt.")
        environment = {**runtime.environment, **phase3_resources(config)}
        session = cls(paths, config, environment, inputs)
        fields = {"Runtime": "runtime", "Python": "python", "Scikit-learn": "sklearn",
                  "RAM khả dụng (GiB)": "ram_available_gb", "CPU": "cpu", "GPU phát hiện": "gpu",
                  "Drive đọc/ghi": "drive_read_write_verified"}
        display(pd.DataFrame([{"Thông tin": label, "Giá trị": str(environment[key])} for label, key in fields.items()]))
        print("Source workspace:", paths.project_root)
        print("Source fingerprint:", runtime.source_fingerprint)
        print("Dữ liệu / đầu ra Drive:", paths.output_root)
        print("Checksum input hợp lệ; chỉ đọc train/validation, không mở CSV test.")
        return session

    def load_data(self, *, cache: bool = True) -> None:
        print("Đang đọc train/validation và kiểm tra schema/group...", flush=True)
        source = cache_training_inputs(self.output, self.paths.cache_dir, self.inputs) if cache else self.output
        self.data = load_training_data(source, self.inputs)
        display(pd.DataFrame([{"Tập": name, "Bản ghi": len(x), "Lớp bệnh": len(set(y.tolist())),
                               "Triệu chứng trước variance": x.shape[1], "Group": len(set(groups.tolist()))}
                              for name, (x, y, groups) in self.data.items()]))
        print("Fingerprint processed:", self.inputs["manifest"]["processed"]["sha256"])
        print("VarianceThreshold chỉ fit khi train; cache ở ổ tạm:", source.root)

    def train(self, *, trust_own_checkpoints: bool = False) -> None:
        if self.data is None:
            raise RuntimeError("Chạy session.load_data() trước khi huấn luyện.")
        self.identity = experiment_identity(self.paths.project_root, self.config, self.inputs)
        self.records = []
        print("Experiment:", self.identity["experiment_id"], flush=True)
        for result in train_models(self.config, self.identity, self.data, self.output,
                                   trust_own_checkpoints=trust_own_checkpoints,
                                   progress=lambda message: print(message, flush=True)):
            self.records.append(result)
            self.comparison_path = save_comparison(self.records, self.output, self.identity)
            display(comparison_table([result]).round(5))

    def train_model(self, name, pipeline, *, fit, trust_own_checkpoints: bool = False) -> dict:
        """Execute the fit callback visible in one notebook cell, with common safeguards."""
        if self.data is None:
            raise RuntimeError("Chạy session.load_data() trước khi huấn luyện.")
        current = experiment_identity(self.paths.project_root, self.config, self.inputs)
        if self.identity != current:
            self.identity, self.records, self.comparison_path = current, [], None
            print("Experiment:", self.identity["experiment_id"], flush=True)
        model_root = self.output.models_dir / "phase3" / self.identity["experiment_id"]
        result = run_model_safely(name, self.config, self.identity, self.data, model_root,
                                  pipeline=pipeline, fit=fit, trust_own_checkpoints=trust_own_checkpoints,
                                  progress=lambda message: print(message, flush=True))
        self.records = [r for r in self.records if r["model"] != name] + [result]
        self.comparison_path = save_comparison(self.records, self.output, self.identity)
        display(comparison_table([result]).round(5))
        return result

    def show_results(self) -> dict:
        if not self.records or self.identity is None or self.comparison_path is None:
            raise RuntimeError("Chạy session.train() trước khi xem kết quả.")
        display(comparison_table(self.records).round(5))
        figures = validation_figures(self.records, self.output, self.identity, self.data, self.inputs)
        for name, fig, path in figures:
            display(fig)
            plt.close(fig)
            print(name, "→", path)
        if not figures:
            print("Chưa có mô hình hoàn tất; xem lỗi đã lưu, không có metric hoặc hình giả.")
        handoff = save_handoff(self.records, figures, self.output, self.identity,
                               self.environment, self.comparison_path)
        print("Comparison CSV:", self.comparison_path)
        print("Run metadata:", handoff["path"])
        print("Phase 4 ready:", handoff["phase4_ready"])
        print("Dừng sau Phase 3. Chưa mở/evaluate test hoặc train ensemble.")
        return handoff
