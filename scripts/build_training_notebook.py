"""Build only the new Phase 3 notebook, using the standard library; no local env setup."""
from pathlib import Path
import json
import sys
import textwrap
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def cell(kind, source):
    result = {"cell_type": kind, "id": uuid.uuid4().hex[:8], "metadata": {},
              "source": textwrap.dedent(source).strip().splitlines(keepends=True)}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
        result["metadata"] = {"jupyter": {"source_hidden": False, "outputs_hidden": False}}
    return result




def training_cells():
    from scripts.update_colab_notebooks import entry_source, TRAINING_INTRO
    bootstrap = "from src.models.notebook import ColabTraining\nsession = ColabTraining.open(RUNTIME)"
    return [
        cell("markdown", TRAINING_INTRO),
        cell("code", entry_source(3)),
        cell("code", bootstrap),
        cell("markdown", '''
        ## 2. Đọc train/validation đã khóa

        Kiểm checksum và schema; cache cần thiết nằm ở ổ tạm Colab. Không đọc/copy CSV test.
        '''),
        cell("code", '''
        session.load_data()
        X_train, y_train, groups_train = session.data["train"]
        X_val, y_val, groups_val = session.data["validation"]
        '''),
        cell("markdown", '''
        ## 3. Huấn luyện 5 mô hình

        Mỗi mô hình có một cell riêng bên dưới. Pipeline chung gồm `VarianceThreshold(0)` và CSR;
        lệnh `.fit(X_train, y_train)` hiển thị ngay trong mỗi cell, được helper thực thi khi cần fit mới.
        Helper chỉ lo giới hạn tài nguyên, thời gian, checkpoint và predict validation theo batch.
        Nếu checkpoint đã hoàn tất và khớp cấu hình, log ghi **REUSED**, không gọi lại `.fit()`.
        Tham số lấy từ `configs/phase3.json`; muốn đổi tham số thì cập nhật config để tránh reuse nhầm.
        '''),
        cell("code", '''
        import os
        from IPython.display import display
        from sklearn.pipeline import Pipeline
        from sklearn.feature_selection import VarianceThreshold
        from sklearn.preprocessing import FunctionTransformer
        from sklearn.linear_model import LogisticRegression
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.svm import LinearSVC
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.naive_bayes import BernoulliNB
        from src.models.training import to_csr

        seed = session.config["seed"]
        workers = min(session.config["resources"]["max_workers"], os.cpu_count() or 1)

        def make_pipeline(estimator):
            return Pipeline([
                ("variance", VarianceThreshold(threshold=0)),
                ("csr", FunctionTransformer(to_csr, validate=False, feature_names_out="one-to-one")),
                ("estimator", estimator),
            ])
        '''),
        cell("code", '''
        # 1/5 — Logistic Regression
        lr_pipeline = make_pipeline(LogisticRegression(
            random_state=seed, **session.config["models"]["logistic_regression"]))
        display(lr_pipeline)
        lr_result = session.train_model(
            "logistic_regression", lr_pipeline,
            fit=lambda model: model.fit(X_train, y_train))
        del lr_pipeline  # Pipeline đã lưu trên Drive; giải phóng RAM.
        '''),
        cell("code", '''
        # 2/5 — Random Forest
        rf_pipeline = make_pipeline(RandomForestClassifier(
            random_state=seed, n_jobs=workers, **session.config["models"]["random_forest"]))
        display(rf_pipeline)
        rf_result = session.train_model(
            "random_forest", rf_pipeline,
            fit=lambda model: model.fit(X_train, y_train))
        del rf_pipeline
        '''),
        cell("code", '''
        # 3/5 — Linear Support Vector Machine
        svm_pipeline = make_pipeline(LinearSVC(
            random_state=seed, **session.config["models"]["linear_svc"]))
        display(svm_pipeline)
        svm_result = session.train_model(
            "linear_svc", svm_pipeline,
            fit=lambda model: model.fit(X_train, y_train))
        del svm_pipeline
        '''),
        cell("code", '''
        # 4/5 — K-Nearest Neighbors (predict theo batch để giảm RAM)
        knn_pipeline = make_pipeline(KNeighborsClassifier(
            n_jobs=1, **session.config["models"]["knn"]))
        display(knn_pipeline)
        knn_result = session.train_model(
            "knn", knn_pipeline,
            fit=lambda model: model.fit(X_train, y_train))
        del knn_pipeline
        '''),
        cell("code", '''
        # 5/5 — Bernoulli Naive Bayes
        nb_pipeline = make_pipeline(BernoulliNB(**session.config["models"]["bernoulli_nb"]))
        display(nb_pipeline)
        nb_result = session.train_model(
            "bernoulli_nb", nb_pipeline,
            fit=lambda model: model.fit(X_train, y_train))
        del nb_pipeline
        '''),
        cell("markdown", '''
        ## 4. Kết quả validation và artifact trên Drive

        Macro F1 là metric chính (`zero_division=0`). Hiển thị bảng và 3 hình từ kết quả thực;
        model lỗi có metric trống. Pipeline, predictions, metadata, bảng và hình được lưu trên Drive.
        **Dừng sau Phase 3:** chưa ensemble, evaluate test hoặc chatbot.

        **COLAB NOT YET VERIFIED:** bản bàn giao chưa được chạy trên Colab thật của người dùng.
        '''),
        cell("code", "handoff = session.show_results()"),
    ]


def main():
    destination = ROOT / "notebooks/03_model_training.ipynb"
    notebook = {"nbformat": 4, "nbformat_minor": 5,
                "metadata": {"kernelspec": {"name": "python3", "display_name": "Colab", "language": "python"},
                             "language_info": {"name": "python"}}, "cells": training_cells()}
    for item in notebook["cells"]:
        if item["cell_type"] == "code":
            compile("".join(item["source"]), "phase3-cell", "exec")
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(notebook, stream, ensure_ascii=False, indent=1)
        stream.write("\n")
    print(destination)


if __name__ == "__main__":
    main()
