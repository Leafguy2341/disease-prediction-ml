"""Phase 4 math, integrity boundaries and I/O with doubles; never fit a baseline."""
from pathlib import Path
from types import SimpleNamespace
import json
import sys

import numpy as np
import pandas as pd
import pytest

from src.data.paths import RuntimePaths
from src.models import ensemble as en
from src.models.runtime import MODEL_NAMES, read_training_config
from src.models.training import json_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_hard_majority_ties_follow_models_not_arbitrary_class_ids():
    p = {"logistic_regression": np.array([2, 0, 1]), "linear_svc": np.array([1, 2, 2]), "knn": np.array([0, 2, 2])}
    result, ties = en.hard_vote(p, tuple(reversed(p)), 3)
    np.testing.assert_array_equal(result, [2, 2, 2])
    assert ties == 1
    remap = np.array([2, 0, 1])
    mapped, _ = en.hard_vote({k: remap[v] for k, v in p.items()}, tuple(p), 3)
    np.testing.assert_array_equal(mapped, remap[result])


def test_soft_uniform_mean_and_documented_ties():
    p = {"logistic_regression": np.array([[.2, .6, .2], [.5, .5, 0]]),
         "bernoulli_nb": np.array([[.6, .2, .2], [.5, .5, 0]]),
         "random_forest": np.array([[.4, .4, .2], [.5, .5, 0]])}
    result, ties = en.soft_vote(p, tuple(p), ["Zulu", "Alpha", "Beta"], batch_size=1)
    np.testing.assert_array_equal(result, [1, 1])  # LR probability, then English label Alpha.
    assert ties == 2
    with pytest.raises(en.IntegrityError, match="LinearSVC"):
        en.soft_vote(p, ("logistic_regression", "linear_svc"), ["A", "B", "C"])


@pytest.mark.parametrize("problem", ["negative", "nan", "sum", "order", "shape"])
def test_invalid_probability_is_rejected(problem):
    p = np.array([[.25, .75]])
    classes = np.arange(2)
    if problem == "negative": p[0] = [-.1, 1.1]
    elif problem == "nan": p[0, 0] = np.nan
    elif problem == "sum": p[:] = .2
    elif problem == "order": classes = classes[::-1]
    else: p = p[:, :1]
    with pytest.raises(en.IntegrityError):
        en.validate_probabilities(p, 1, classes, 2)


def test_diversity_distinguishes_disagreement_from_rescue():
    y = np.array([0, 0, 0, 0])
    p = {"A": np.array([0, 1, 1, 0]), "B": np.array([1, 0, 2, 0])}
    d = en.error_diversity(p, y, ("A", "B"))
    assert d["disagreement"][0, 1] == .75
    assert d["joint_error"][0, 1] == .25
    assert d["a_wrong_b_correct"][0, 1] == .25
    assert d["joint_error"][0, 0] == .5
    np.testing.assert_array_equal(d["disagreement"], d["disagreement"].T)


def test_guard_preserves_settings_and_blocks_fit_test_old_artifact_writes(tmp_path):
    from sklearn.feature_selection import VarianceThreshold
    previous = sys.getprofile()
    with en.phase4_guard(tmp_path) as counts:
        with pytest.raises(en.IntegrityError, match="test"):
            (tmp_path / "test.csv.gz").read_bytes()
        with pytest.raises(en.IntegrityError, match="sửa"):
            (tmp_path / "data/train.csv").write_bytes(b"bad")
        with pytest.raises(en.FitForbidden):
            VarianceThreshold().fit([[0], [1]])  # Rejected before the function body.
    assert sys.getprofile() is previous
    assert all(counts[k] == 1 for k in counts)


@pytest.fixture
def phase(tmp_path, monkeypatch):
    """Tiny validation arrays and prediction doubles, not project results/fitted models."""
    storage = tmp_path / "drive"
    features = [f"unit_{i}" for i in range(375)]
    classes = ["A", "B", "C"]
    meta = storage / "artifacts/metadata/phase2"
    meta.mkdir(parents=True)
    (meta / "feature_schema.json").write_bytes(json_bytes({"features": features}))
    (meta / "label_mapping.json").write_bytes(json_bytes({"classes": classes}))
    config = read_training_config(ROOT)
    config["resources"]["min_available_ram_gb"] = 0
    paths = RuntimePaths(ROOT, storage, storage / "data/raw", storage, "unit fixture", tmp_path / "mount", tmp_path / "cache", False, {})
    obj = en.Phase4(SimpleNamespace(paths=paths, config=config))
    obj.x = pd.DataFrame(np.zeros((6, 375), dtype=np.uint8), columns=features)
    obj.y, obj.groups, obj.features, obj.classes = np.array([0, 1, 2, 0, 1, 2]), np.arange(6), features, classes
    obj.predictions = dict(zip(MODEL_NAMES, map(np.array, ([0,1,2,0,1,2], [1,1,0,0,1,2], [0,2,2,0,0,2], [1,1,2,0,1,0], [0,1,1,2,1,2]))))
    import platform, joblib, scipy, sklearn
    from src.models import training
    versions = {"python": platform.python_version(), "sklearn": sklearn.__version__, "numpy": np.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__}
    obj.identity = {"experiment_id": en.EXPERIMENT, "versions": versions, "source_sha256": {}, "validation_data_fingerprint": "unit-only"}
    obj.current = {"versions": versions}
    obj.identities, obj.metadata = {}, {}
    for name in MODEL_NAMES:
        folder = obj.run / name
        folder.mkdir(parents=True)
        (folder / "pipeline.joblib").write_bytes(b"unit only, never deserialize")
        prediction_file = folder / "validation_predictions.npz"
        np.savez_compressed(prediction_file, y_pred=obj.predictions[name])
        obj.metadata[name] = {"pipeline_sha256": en.sha256_file(folder / "pipeline.joblib"), "predictions_sha256": en.sha256_file(prediction_file), "prediction_seconds": 1.0}
        obj.identities[name] = obj.identity
    obj.identity.update(feature_schema_identity=en.sha256_file(meta / "feature_schema.json"), label_mapping_identity=en.sha256_file(meta / "label_mapping.json"))
    obj.records[en.BASELINE] = {"id": en.BASELINE, "mode": "single", "members": ["logistic_regression"], "status": "completed", "tie_rows": 0,
                                **en.score_prediction(obj.y, obj.predictions["logistic_regression"], 3)}
    obj.diversity = en.error_diversity(obj.predictions, obj.y)

    class PredictionDouble:
        classes_ = np.arange(3)
        n_features_in_ = 375
        def __init__(self, name): self.name = name
        def predict_proba(self, frame):
            p = np.full((len(frame), 3), .1)
            p[np.arange(len(frame)), obj.predictions[self.name][frame.index]] = .8
            return p
        def predict(self, frame): return obj.predictions[self.name][frame.index]

    monkeypatch.setattr(en, "load_fitted_checkpoint", lambda path, *a, **kw: PredictionDouble(path.name))
    monkeypatch.setattr(training, "load_fitted_checkpoint", lambda path, *a, **kw: PredictionDouble(path.name))
    yield obj
    obj.close()


def test_fixed_combinations_probability_provenance_and_memory_cache(phase):
    phase.evaluate_hard()
    with pytest.raises(en.IntegrityError, match="trusted"):
        phase.prepare_probabilities()
    summary = phase.prepare_probabilities(trusted=True)
    assert summary["available"].all() and "linear_svc" not in phase.probabilities
    phase.evaluate_soft()
    assert set(phase.records) == {en.BASELINE, *en.HARD, *en.SOFT}
    assert phase.best()["id"] == en.BASELINE  # Never invent an ensemble win.
    assert all(isinstance(p, np.memmap) for p in phase.probabilities.values())
    assert all(p["method"] == "trusted_fitted_pipeline.predict_proba" and not p["persistent_probability_written"] for p in phase.probability_sources.values())
    directory = Path(phase._temporary.name)
    phase.close()
    assert not directory.exists()


def test_probability_limitations_leave_empty_metrics(phase, monkeypatch):
    phase.evaluate_hard()
    monkeypatch.setattr(phase, "_load", lambda *a, **kw: (_ for _ in ()).throw(en.ProbabilityUnavailable("unit: different environment")))
    phase.prepare_probabilities(trusted=True)
    table = phase.evaluate_soft()
    soft = table.loc[table["mode"].eq("soft")]
    assert soft["macro_f1"].isna().all() and soft["status"].eq("not_available").all()
    assert len(phase.limitations) == 4
    phase.close()


def test_publish_is_namespaced_preserves_phase3_and_detects_definition_tampering(phase):
    class FigureDouble:
        def savefig(self, stream, **kwargs): stream.write(b"unit figure placeholder, not model results")
    before = {str(p): (en.sha256_file(p), p.stat().st_mtime_ns) for p in phase.run.rglob('*') if p.is_file()}
    phase.evaluate_hard()
    phase.evaluate_soft()  # Missing probabilities are explicitly not_available.
    result = en.save_phase4(phase, FigureDouble(), FigureDouble())
    manifest = phase.output.root / result["manifest_relative"]
    assert en.sha256_file(manifest) == result["manifest_sha256"]
    for relative, expected in result["artifact_files"].items():
        assert en.sha256_file(phase.output.root / relative) == expected["sha256"]
    assert before == {str(p): (en.sha256_file(p), p.stat().st_mtime_ns) for p in phase.run.rglob('*') if p.is_file()}
    assert result["base_models_fitted"] == 0 and not result["test_payload_opened"]
    definition = phase.output.root / result["definition_relative"]
    wrapper = en.load_voting_definition(definition, phase.output.root, trusted=True)
    assert len(wrapper.definition["features"]) == 375 and not hasattr(wrapper, "fit")
    with pytest.raises(en.IntegrityError, match="thứ tự"):
        wrapper._input(phase.x.iloc[:1, ::-1])
    definition.write_text("{}", encoding="utf-8")
    with pytest.raises(en.IntegrityError, match="checksum"):
        en.load_voting_definition(definition, phase.output.root, trusted=True)


def test_prefitted_wrapper_single_hard_soft_match_evaluation_and_have_no_fit(phase):
    phase.evaluate_hard()
    phase.prepare_probabilities(trusted=True)
    phase.evaluate_soft()
    for key in (en.BASELINE, "hard_lr_svc_knn", "soft_lr_nb_rf"):
        wrapper = en.PrefittedVoting(phase.definition(key), phase.output.root, trusted=True)
        predicted = wrapper.predict(phase.x)
        expected = phase.predictions["logistic_regression"] if key == en.BASELINE else phase.ensemble_predictions[key]
        np.testing.assert_array_equal(predicted, expected)
        np.testing.assert_array_equal(wrapper.predict(phase.x.iloc[0].to_numpy()), expected[:1])
        assert not hasattr(wrapper, "fit")
        wrapper.close()
    assert phase.single_input_check(trusted=True)["status"] == "PASS"


def test_real_locked_inputs_are_read_only_and_missing_phase3_stops_without_fit(tmp_path):
    from src.data.integrity import read_baseline, verify_training_inputs
    from src.data.paths import OutputPaths
    if (ROOT / "artifacts/models/phase3" / en.EXPERIMENT).is_dir():
        pytest.skip("Real Phase 3 data now available; do not assume a missing checkpoint.")
    inputs = verify_training_inputs(OutputPaths(ROOT), baseline=read_baseline(ROOT / "configs/phase2_integrity.json"))
    paths = RuntimePaths(ROOT, ROOT, ROOT / "data/raw", ROOT, "Windows preflight", tmp_path / "mount", tmp_path / "cache", False, {})
    session = SimpleNamespace(paths=paths, config=read_training_config(ROOT), inputs=inputs)
    check = en.Phase4(session)
    with pytest.raises(en.IntegrityError, match="Thiếu completed checkpoint"):
        check.verify()
    assert all(v == 0 for v in check.guards.values())


def test_notebook_uses_shared_setup_and_never_calls_fit_or_voting_classifier():
    nb = json.loads((ROOT / "notebooks/04_ensemble.ipynb").read_text(encoding="utf-8"))
    sources = [''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code']
    import ast
    for source in sources:
        compile(source, "notebook04", "exec")
        calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)]
        assert not any(isinstance(n.func, ast.Attribute) and n.func.attr in {"fit", "fit_transform", "train", "train_model"} for n in calls)
    assert any("bootstrap_runtime" in s and "phase=3" in s for s in sources)
    assert not any("colab-session" in s or "test.csv.gz" in s or "VotingClassifier(" in s for s in sources)
    # A user may retain real Colab output; source checks must not require deleting it.
    assert any("phase.verify()" in s for s in sources)
    assert any("save_phase4(phase," in s for s in sources)
