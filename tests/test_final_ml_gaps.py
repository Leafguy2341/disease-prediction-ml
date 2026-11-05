"""Memory-only diagnostic tests: no fixtures/files/models/cleanup or real inference.

Run: python -B tests/test_final_ml_gaps.py
"""
import ast
import io
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.metrics import f1_score, accuracy_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
API = runpy.run_path(str(ROOT / "scripts/audit_final_ml_gaps.py"))
AUDIT = runpy.run_path(str(ROOT / "scripts/audit_post_tuning.py"))


class FinalEvidenceTests(unittest.TestCase):
    def test_fixed_587_macro_f1_and_accuracy_equal_weighted_sklearn(self):
        y, prediction, weights = np.array([0, 0, 1, 3]), np.array([0, 2, 1, 3]), np.array([2, 1, 3, 0])
        f1, accuracy, absent = API["weighted_scores"](y, prediction, weights, 587)
        self.assertAlmostEqual(f1, f1_score(y, prediction, sample_weight=weights, average="macro", labels=np.arange(587), zero_division=0))
        self.assertAlmostEqual(accuracy, accuracy_score(y, prediction, sample_weight=weights))
        self.assertEqual(int(absent.sum()), 585)

    def test_paired_groups_preserve_conflicting_labels_together(self):
        result = API["paired_group_bootstrap"](np.array([0, 1, 2]), np.array([0, 0, 2]),
            np.array([1, 1, 2]), np.array(["same", "same", "other"]), seed=7, replicates=50, n_classes=3)
        self.assertEqual(result["macro_f1"]["percentile95"], [0.0, 0.0])
        self.assertEqual(result["accuracy"]["percentile95"], [0.0, 0.0])
        self.assertEqual(result["groups"], 2)
        self.assertEqual(result["missing_classes"]["absent_replicates_per_class_id"][0],
                         result["missing_classes"]["absent_replicates_per_class_id"][1])
        self.assertGreater(result["missing_classes"]["replicates_with_any_missing"], 0)

    def test_bootstrap_is_deterministic_and_does_not_mutate_inputs(self):
        y=np.array([0, 1, 2, 0, 1, 2]);lr=np.array([0, 0, 2, 1, 1, 2]);hard=np.array([0, 1, 2, 0, 2, 2]);groups=np.array([0, 0, 1, 2, 3, 4])
        originals=[x.copy() for x in (y,lr,hard,groups)]
        left=API["paired_group_bootstrap"](y,lr,hard,groups,replicates=40,n_classes=3)
        self.assertEqual(left,API["paired_group_bootstrap"](y,lr,hard,groups,replicates=40,n_classes=3))
        for value,original in zip((y,lr,hard,groups),originals):np.testing.assert_array_equal(value,original)

    def test_invalid_bootstrap_inputs_are_rejected(self):
        from src.models.ensemble import IntegrityError
        for weights in ([0,0],[-1,2],[1,float("nan")],[1]):
            with self.subTest(weights=weights),self.assertRaises(IntegrityError):
                API["weighted_scores"](np.array([0,1]),np.array([0,1]),weights,3)
        with self.assertRaises(IntegrityError):API["paired_group_bootstrap"]([0,1],[0,1],[0,1],[0],replicates=5,n_classes=3)
        with self.assertRaises(IntegrityError):API["weighted_scores"]([0,1],[0,3],[1,1],3)

    def test_panel_is_reproducible_unique_group_first_rows_without_labels(self):
        groups=np.repeat(np.arange(12),2)
        left=API["panel_indices"](groups,count=8)
        np.testing.assert_array_equal(left,API["panel_indices"](groups,count=8))
        self.assertEqual(len(set(groups[left].tolist())),8)
        self.assertTrue((left%2==0).all())

    def test_percentiles_use_all_calls_and_reject_nonfinite(self):
        result=API["latency_summary"]([.001,.003,.002])
        self.assertEqual(result["calls"],3);self.assertEqual(result["p50_ms"],2.0)
        self.assertAlmostEqual(result["p95_ms"],2.9)
        from src.models.ensemble import IntegrityError
        with self.assertRaises(IntegrityError):API["latency_summary"]([float("inf")])

    def test_missing_artifacts_are_not_verified_without_filesystem_mutation(self):
        from types import SimpleNamespace
        # Existing source root lacks tuned artifacts. No temporary directory is created.
        session=SimpleNamespace(paths=SimpleNamespace(storage_root=ROOT,project_root=ROOT))
        with patch.object(sys,"stdout",io.StringIO()):result=API["run_final_ml_gaps"](session,audit_api=AUDIT)
        self.assertEqual(result["status"],"NOT VERIFIED");self.assertFalse(any(result["guards"].values()))

    def test_script_has_no_learning_runtime_setup_or_file_mutators(self):
        tree=ast.parse((ROOT/"scripts/audit_final_ml_gaps.py").read_text(encoding="utf-8"))
        forbidden={"fit","fit_transform","partial_fit","bootstrap_runtime","load_data","train_model","run_tuning",
                   "dump","save","savez","savez_compressed","write_text","write_bytes","mkdir","unlink","remove","rmtree","rename","replace"}
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                name=getattr(node.func,"attr",getattr(node.func,"id",""))
                self.assertNotIn(name,forbidden)
        self.assertEqual(API["BOOTSTRAP_PLAN"]["replicates"],2000)
        self.assertEqual(API["BOOTSTRAP_PLAN"]["seed"],20261029)
        self.assertEqual(API["BOOTSTRAP_PLAN"]["classes"],587)

    def test_benchmark_control_flow_uses_fakes_and_existing_vote_without_files(self):
        import pandas as pd
        class Step:
            def get_params(self,deep=False):return {}
            def get_support(self):return np.array([True,False])
        class FakePipeline:
            feature_names_in_=np.array(["a","b"]);classes_=np.arange(3)
            def __init__(self):
                self.steps=[("variance",Step()),("csr",Step()),("estimator",Step())]
                self.named_steps=dict(self.steps)
            def predict(self,x):return np.zeros(len(x),dtype=int)
            def predict_proba(self,x):return np.full((len(x),3),1/3)
        frames=[pd.DataFrame([[1,0]],columns=["a","b"]),pd.DataFrame([[0,1]],columns=["a","b"])]
        call=API["benchmark_condition"];fake_load=lambda *a,**k:FakePipeline()
        with AUDIT["read_only"](ROOT) as guard,patch.dict(call.__globals__,{"load_fitted_checkpoint":fake_load,"build_pipeline":lambda *a:FakePipeline()}):
            lr=call("lr_tuned",ROOT,{"config":{}},frames,["a","b"],["x","y","z"],np.array([True,False]))
            hard=call("hard_lr_svc_knn",ROOT,{"config":{}},frames,["a","b"],["x","y","z"],np.array([True,False]))
        self.assertFalse(any(guard.values()))
        self.assertEqual(lr["batch1"]["predict_top1"]["calls"],6)
        self.assertEqual(lr["batch1"]["predict_proba_and_top3"]["calls"],6)
        self.assertEqual(len(hard["member_verified_load_seconds"]),3)
        self.assertIn("UNAVAILABLE",hard["top3"])


if __name__=="__main__":
    unittest.main(verbosity=2)
