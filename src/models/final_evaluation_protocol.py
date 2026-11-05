"""Predeclared identities from audited evidence; no test payload was read.

Owner approved LR tuned C=2 on 2026-10-30. Execution remains separately gated.
"""
import json

FROZEN_PROTOCOL = json.loads(r'''
{
  "version": 1,
  "protocol_id": "final-locked-test-v1",
  "frozen_date": "2026-10-30",
  "deployment_decision": "OWNER APPROVED: LR tuned C=2 for research chatbot/API; no application default changed by this evaluation",
  "deployment_candidate": "lr_tuned_c2",
  "execution_authorized_in_preparation": false,
  "candidates": [
    "lr_baseline",
    "lr_tuned_c2",
    "hard_tuned_lr_svc_knn"
  ],
  "checkpoints": {
    "lr_baseline": {
      "model": "logistic_regression",
      "folder": "artifacts/models/phase3/baseline-v1-f8a5bfdb7b4c12cd/logistic_regression",
      "identity": {
        "phase": 3,
        "config": {
          "phase": 3,
          "seed": 42,
          "selection_metric": "macro_f1",
          "zero_division": 0,
          "run_tag": "baseline-v1",
          "expected_phase2": {
            "records": 187434,
            "classes": 587,
            "features": 375,
            "sha256": "afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3"
          },
          "resources": {
            "max_workers": 2,
            "blas_threads": 1,
            "working_memory_mb": 128,
            "prediction_batch_size": 64,
            "min_available_ram_gb": 2.0
          },
          "models": {
            "logistic_regression": {
              "solver": "saga",
              "C": 1.0,
              "max_iter": 200,
              "tol": 0.001
            },
            "random_forest": {
              "n_estimators": 100,
              "max_depth": 24,
              "max_leaf_nodes": 512,
              "min_samples_leaf": 2,
              "max_features": "sqrt"
            },
            "linear_svc": {
              "C": 1.0,
              "dual": "auto",
              "max_iter": 3000,
              "tol": 0.001
            },
            "knn": {
              "n_neighbors": 5,
              "weights": "distance",
              "algorithm": "brute",
              "metric": "manhattan"
            },
            "bernoulli_nb": {
              "alpha": 1.0,
              "binarize": null
            }
          }
        },
        "processed_fingerprint": "afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3",
        "phase2_manifest_sha256": "50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9",
        "training_data_fingerprint": "3dfd77eb71ad3a2917a3a390917953f437ae6afb5220ac9feb28fec132e11e12",
        "validation_data_fingerprint": "a203b9c0f1f124fa25d4cae6f5299d986bba23859ceca80660bc8bcb843570f2",
        "feature_schema_identity": "dd07a3c73dd41558daa9c08e816e0a93d9efc4155f98b7e2b73325bffe31c5c0",
        "label_mapping_identity": "d2ef711e5e04062e8b5b949ce434b1383e1ca2fef6eb31a0865acb2f470ab5b5",
        "versions": {
          "python": "3.13.18",
          "sklearn": "1.6.1",
          "numpy": "2.1.3",
          "scipy": "1.16.3",
          "joblib": "1.6.0"
        },
        "source_sha256": {
          "src/models/training.py": "d48022c38d06712e028387e99a1563da8782af408749f436da54d17c825dc652",
          "src/models/runtime.py": "ae3f4258bfd1029ed13aa1021e3905fee8cfdd53b5651a18f770e74e766ca500",
          "src/data/preprocessing.py": "648c43f722a1c30e49e7f3279431c8136bbc5396f42ec9b51212679663fb845d",
          "src/data/loader.py": "37397527ec5b5d48e233776fa5ef040a4bc476e23a45dd26d81ed5144c5ab17b",
          "src/data/paths.py": "89ab450a76fffe92bb30fd6aa11b69567d69293916da2fda78123a8f29249eeb",
          "src/data/audit.py": "41ff075c529ecf7200caf3717b660f655bc344e558d52d1448045aa2dd91672f"
        },
        "experiment_id": "baseline-v1-f8a5bfdb7b4c12cd"
      },
      "files": {
        "fit.json": {
          "sha256": "37168ee6148681bd4454fae02895ad62426c3682f2b2b0a5fdc05bfc5e167d92",
          "bytes": 4810
        },
        "metadata.json": {
          "sha256": "a647476b871a3f15e3251d3162541c53b269bed54aabd6e5192ad746dd8ad764",
          "bytes": 5813
        },
        "pipeline.joblib": {
          "sha256": "54f124240fd2bb8fb61c39594a55663e1b67f5f5b67595faeaa350504d0376da",
          "bytes": 1438385
        },
        "validation_predictions.npz": {
          "sha256": "1fb23e0505f4328be254d4efb14fe471287647882ad4c4329389269a8243aad4",
          "bytes": 109003
        }
      }
    },
    "lr_tuned_c2": {
      "model": "logistic_regression",
      "folder": "artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/logistic_regression",
      "identity": {
        "phase": 3,
        "config": {
          "phase": 3,
          "seed": 42,
          "selection_metric": "macro_f1",
          "zero_division": 0,
          "run_tag": "tuned-v1",
          "expected_phase2": {
            "records": 187434,
            "classes": 587,
            "features": 375,
            "sha256": "afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3"
          },
          "resources": {
            "max_workers": 2,
            "blas_threads": 1,
            "working_memory_mb": 128,
            "prediction_batch_size": 64,
            "min_available_ram_gb": 2.0
          },
          "models": {
            "bernoulli_nb": {
              "alpha": 0.5,
              "binarize": null
            },
            "knn": {
              "algorithm": "brute",
              "metric": "manhattan",
              "n_neighbors": 7,
              "weights": "distance"
            },
            "linear_svc": {
              "C": 2.0,
              "dual": "auto",
              "max_iter": 3000,
              "tol": 0.001
            },
            "logistic_regression": {
              "C": 2.0,
              "max_iter": 200,
              "solver": "saga",
              "tol": 0.001
            },
            "random_forest": {
              "max_depth": 32,
              "max_features": "sqrt",
              "max_leaf_nodes": 512,
              "min_samples_leaf": 2,
              "n_estimators": 100
            }
          }
        },
        "processed_fingerprint": "afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3",
        "phase2_manifest_sha256": "50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9",
        "training_data_fingerprint": "3dfd77eb71ad3a2917a3a390917953f437ae6afb5220ac9feb28fec132e11e12",
        "validation_data_fingerprint": "a203b9c0f1f124fa25d4cae6f5299d986bba23859ceca80660bc8bcb843570f2",
        "feature_schema_identity": "dd07a3c73dd41558daa9c08e816e0a93d9efc4155f98b7e2b73325bffe31c5c0",
        "label_mapping_identity": "d2ef711e5e04062e8b5b949ce434b1383e1ca2fef6eb31a0865acb2f470ab5b5",
        "versions": {
          "python": "3.13.18",
          "sklearn": "1.6.1",
          "numpy": "2.1.3",
          "scipy": "1.16.3",
          "joblib": "1.6.0"
        },
        "source_sha256": {
          "src/models/training.py": "d48022c38d06712e028387e99a1563da8782af408749f436da54d17c825dc652",
          "src/models/runtime.py": "ae3f4258bfd1029ed13aa1021e3905fee8cfdd53b5651a18f770e74e766ca500",
          "src/data/preprocessing.py": "648c43f722a1c30e49e7f3279431c8136bbc5396f42ec9b51212679663fb845d",
          "src/data/loader.py": "37397527ec5b5d48e233776fa5ef040a4bc476e23a45dd26d81ed5144c5ab17b",
          "src/data/paths.py": "89ab450a76fffe92bb30fd6aa11b69567d69293916da2fda78123a8f29249eeb",
          "src/data/audit.py": "41ff075c529ecf7200caf3717b660f655bc344e558d52d1448045aa2dd91672f",
          "src/models/tuning.py": "00a07b2d5a2e1754b3c63d32342cf54a8c781ee1df1af5c029c9e7289bc59f02",
          "src/models/tuned_ensemble.py": "a507f8cb9065009585b79a4f1275ca2c6d7c3ecf2690367d7a366f99c1ffcf3b"
        },
        "tuning_experiment": "tuning-v1-9c4dd013abbba14a",
        "selection_sha256": "6191034dcc4a9c2393645929ea8942bc6eedc40206942b8384f30921bf727703",
        "experiment_id": "tuned-v1-b8a5602679b3dc5c"
      },
      "files": {
        "pipeline.joblib": {
          "sha256": "4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6",
          "bytes": 1438563
        }
      }
    },
    "svc_tuned": {
      "model": "linear_svc",
      "folder": "artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/linear_svc",
      "identity": {
        "phase": 3,
        "config": {
          "phase": 3,
          "seed": 42,
          "selection_metric": "macro_f1",
          "zero_division": 0,
          "run_tag": "tuned-v1",
          "expected_phase2": {
            "records": 187434,
            "classes": 587,
            "features": 375,
            "sha256": "afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3"
          },
          "resources": {
            "max_workers": 2,
            "blas_threads": 1,
            "working_memory_mb": 128,
            "prediction_batch_size": 64,
            "min_available_ram_gb": 2.0
          },
          "models": {
            "bernoulli_nb": {
              "alpha": 0.5,
              "binarize": null
            },
            "knn": {
              "algorithm": "brute",
              "metric": "manhattan",
              "n_neighbors": 7,
              "weights": "distance"
            },
            "linear_svc": {
              "C": 2.0,
              "dual": "auto",
              "max_iter": 3000,
              "tol": 0.001
            },
            "logistic_regression": {
              "C": 2.0,
              "max_iter": 200,
              "solver": "saga",
              "tol": 0.001
            },
            "random_forest": {
              "max_depth": 32,
              "max_features": "sqrt",
              "max_leaf_nodes": 512,
              "min_samples_leaf": 2,
              "n_estimators": 100
            }
          }
        },
        "processed_fingerprint": "afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3",
        "phase2_manifest_sha256": "50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9",
        "training_data_fingerprint": "3dfd77eb71ad3a2917a3a390917953f437ae6afb5220ac9feb28fec132e11e12",
        "validation_data_fingerprint": "a203b9c0f1f124fa25d4cae6f5299d986bba23859ceca80660bc8bcb843570f2",
        "feature_schema_identity": "dd07a3c73dd41558daa9c08e816e0a93d9efc4155f98b7e2b73325bffe31c5c0",
        "label_mapping_identity": "d2ef711e5e04062e8b5b949ce434b1383e1ca2fef6eb31a0865acb2f470ab5b5",
        "versions": {
          "python": "3.13.18",
          "sklearn": "1.6.1",
          "numpy": "2.1.3",
          "scipy": "1.16.3",
          "joblib": "1.6.0"
        },
        "source_sha256": {
          "src/models/training.py": "d48022c38d06712e028387e99a1563da8782af408749f436da54d17c825dc652",
          "src/models/runtime.py": "ae3f4258bfd1029ed13aa1021e3905fee8cfdd53b5651a18f770e74e766ca500",
          "src/data/preprocessing.py": "648c43f722a1c30e49e7f3279431c8136bbc5396f42ec9b51212679663fb845d",
          "src/data/loader.py": "37397527ec5b5d48e233776fa5ef040a4bc476e23a45dd26d81ed5144c5ab17b",
          "src/data/paths.py": "89ab450a76fffe92bb30fd6aa11b69567d69293916da2fda78123a8f29249eeb",
          "src/data/audit.py": "41ff075c529ecf7200caf3717b660f655bc344e558d52d1448045aa2dd91672f",
          "src/models/tuning.py": "00a07b2d5a2e1754b3c63d32342cf54a8c781ee1df1af5c029c9e7289bc59f02",
          "src/models/tuned_ensemble.py": "a507f8cb9065009585b79a4f1275ca2c6d7c3ecf2690367d7a366f99c1ffcf3b"
        },
        "tuning_experiment": "tuning-v1-9c4dd013abbba14a",
        "selection_sha256": "6191034dcc4a9c2393645929ea8942bc6eedc40206942b8384f30921bf727703",
        "experiment_id": "tuned-v1-b8a5602679b3dc5c"
      },
      "files": {
        "pipeline.joblib": {
          "sha256": "1ac35a1e68225142c6ff60332d8fcf973a57cc0f84c18be320f396830c32fe89",
          "bytes": 1463321
        }
      }
    },
    "knn_tuned": {
      "model": "knn",
      "folder": "artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/knn",
      "identity": {
        "phase": 3,
        "config": {
          "phase": 3,
          "seed": 42,
          "selection_metric": "macro_f1",
          "zero_division": 0,
          "run_tag": "tuned-v1",
          "expected_phase2": {
            "records": 187434,
            "classes": 587,
            "features": 375,
            "sha256": "afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3"
          },
          "resources": {
            "max_workers": 2,
            "blas_threads": 1,
            "working_memory_mb": 128,
            "prediction_batch_size": 64,
            "min_available_ram_gb": 2.0
          },
          "models": {
            "bernoulli_nb": {
              "alpha": 0.5,
              "binarize": null
            },
            "knn": {
              "algorithm": "brute",
              "metric": "manhattan",
              "n_neighbors": 7,
              "weights": "distance"
            },
            "linear_svc": {
              "C": 2.0,
              "dual": "auto",
              "max_iter": 3000,
              "tol": 0.001
            },
            "logistic_regression": {
              "C": 2.0,
              "max_iter": 200,
              "solver": "saga",
              "tol": 0.001
            },
            "random_forest": {
              "max_depth": 32,
              "max_features": "sqrt",
              "max_leaf_nodes": 512,
              "min_samples_leaf": 2,
              "n_estimators": 100
            }
          }
        },
        "processed_fingerprint": "afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3",
        "phase2_manifest_sha256": "50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9",
        "training_data_fingerprint": "3dfd77eb71ad3a2917a3a390917953f437ae6afb5220ac9feb28fec132e11e12",
        "validation_data_fingerprint": "a203b9c0f1f124fa25d4cae6f5299d986bba23859ceca80660bc8bcb843570f2",
        "feature_schema_identity": "dd07a3c73dd41558daa9c08e816e0a93d9efc4155f98b7e2b73325bffe31c5c0",
        "label_mapping_identity": "d2ef711e5e04062e8b5b949ce434b1383e1ca2fef6eb31a0865acb2f470ab5b5",
        "versions": {
          "python": "3.13.18",
          "sklearn": "1.6.1",
          "numpy": "2.1.3",
          "scipy": "1.16.3",
          "joblib": "1.6.0"
        },
        "source_sha256": {
          "src/models/training.py": "d48022c38d06712e028387e99a1563da8782af408749f436da54d17c825dc652",
          "src/models/runtime.py": "ae3f4258bfd1029ed13aa1021e3905fee8cfdd53b5651a18f770e74e766ca500",
          "src/data/preprocessing.py": "648c43f722a1c30e49e7f3279431c8136bbc5396f42ec9b51212679663fb845d",
          "src/data/loader.py": "37397527ec5b5d48e233776fa5ef040a4bc476e23a45dd26d81ed5144c5ab17b",
          "src/data/paths.py": "89ab450a76fffe92bb30fd6aa11b69567d69293916da2fda78123a8f29249eeb",
          "src/data/audit.py": "41ff075c529ecf7200caf3717b660f655bc344e558d52d1448045aa2dd91672f",
          "src/models/tuning.py": "00a07b2d5a2e1754b3c63d32342cf54a8c781ee1df1af5c029c9e7289bc59f02",
          "src/models/tuned_ensemble.py": "a507f8cb9065009585b79a4f1275ca2c6d7c3ecf2690367d7a366f99c1ffcf3b"
        },
        "tuning_experiment": "tuning-v1-9c4dd013abbba14a",
        "selection_sha256": "6191034dcc4a9c2393645929ea8942bc6eedc40206942b8384f30921bf727703",
        "experiment_id": "tuned-v1-b8a5602679b3dc5c"
      },
      "files": {
        "pipeline.joblib": {
          "sha256": "1d84f44c5d3eec025d7f9fc574fb80eba58b0e38fbb6927ed7090ebe9446b976",
          "bytes": 652535
        }
      }
    }
  },
  "phase2_manifest_sha256": "50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9",
  "phase2_files": {
    "artifacts/metadata/phase2/feature_schema.json": {
      "bytes": 19501,
      "sha256": "dd07a3c73dd41558daa9c08e816e0a93d9efc4155f98b7e2b73325bffe31c5c0"
    },
    "artifacts/metadata/phase2/label_mapping.json": {
      "bytes": 48977,
      "sha256": "d2ef711e5e04062e8b5b949ce434b1383e1ca2fef6eb31a0865acb2f470ab5b5"
    },
    "artifacts/metadata/phase2/preprocessing_policy.json": {
      "bytes": 1741,
      "sha256": "ae4694b6a4fa7f32c6bee937b125d78f4053394933f90fe631b6a7475d2e5909"
    },
    "artifacts/metadata/phase2/split_assignments.csv.gz": {
      "bytes": 1415738,
      "sha256": "e2428a610019ddf62236e4a82bd39ae7dabd9b89a048bf63dd807fd8d9a42c51"
    },
    "artifacts/metadata/phase2/split_metadata.json": {
      "bytes": 164744,
      "sha256": "254aa34dd635f08d7037bd75d0e43148efe01bdfa13a9b6de20195b7dabf58c7"
    },
    "data/processed/test.csv.gz": {
      "bytes": 292558,
      "sha256": "d71a040a6ead853931cfc75452e456906e5277a3081dc97e8af5688ed4268dd0"
    },
    "data/processed/train.csv.gz": {
      "bytes": 1262444,
      "sha256": "3dfd77eb71ad3a2917a3a390917953f437ae6afb5220ac9feb28fec132e11e12"
    },
    "data/processed/validation.csv.gz": {
      "bytes": 292793,
      "sha256": "a203b9c0f1f124fa25d4cae6f5299d986bba23859ceca80660bc8bcb843570f2"
    }
  },
  "processed": {
    "classes": 587,
    "features": 375,
    "fingerprint_encoding": "SHA256(UTF8(json.dumps({features,target,classes}, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + LF) + packed X bits big-endian row-major + label IDs uint32 little-endian row-major)",
    "records": 187434,
    "schema_sha256": "441709695f8b878e65d848309361838fa0367b6c031ed665a1472a9aee43b734",
    "sha256": "afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3"
  },
  "test": {
    "relative": "data/processed/test.csv.gz",
    "records": 28066,
    "groups": 25128,
    "features": 375,
    "classes": 587,
    "sha256": "d71a040a6ead853931cfc75452e456906e5277a3081dc97e8af5688ed4268dd0",
    "bytes": 292558
  },
  "tuning": {
    "experiment_id": "tuning-v1-9c4dd013abbba14a",
    "manifest_sha256": "4a10ddd5deba5fff7927f84ea334196a3f6d127b9777ced2b127f5b5e9389355"
  },
  "ensemble": {
    "run_id": "tuned-ensemble-20261029T041701354242Z-6c84dbfe",
    "manifest_sha256": "858893c442f1966eb8c7508a74cf6318b820004278342a1b958942151c049060",
    "key": "hard_lr_svc_knn",
    "members": [
      "logistic_regression",
      "linear_svc",
      "knn"
    ],
    "priority": [
      "logistic_regression",
      "linear_svc",
      "knn",
      "bernoulli_nb",
      "random_forest"
    ],
    "engine_source_sha256": "ee3121f04b187845fbff937add77a527d2761df14e035e94f48100b1d647443c"
  },
  "scoring": {
    "labels": "fixed Phase2 IDs 0..586",
    "primary": "macro_f1",
    "zero_division": 0,
    "secondary": [
      "accuracy",
      "macro_precision",
      "macro_recall",
      "weighted_f1",
      "predicted_classes",
      "classes_f1_zero"
    ]
  },
  "analysis": {
    "pairs": [
      [
        "lr_baseline",
        "lr_tuned_c2"
      ],
      [
        "lr_tuned_c2",
        "hard_tuned_lr_svc_knn"
      ],
      [
        "lr_baseline",
        "hard_tuned_lr_svc_knn"
      ]
    ],
    "group_difference": "paired within-group mean correctness; groups equally weighted; descriptive only, no CI or new selection",
    "support_bins": [
      "0",
      "1",
      "2-5",
      "6-20",
      ">20"
    ],
    "no_additional_bootstrap_or_optimization": true
  },
  "validation_reference": {
    "lr_baseline": {
      "accuracy": 0.8370910384068279,
      "macro_f1": 0.7878081402467481,
      "macro_precision": 0.8274197939731976,
      "macro_recall": 0.7791885208694249,
      "weighted_f1": 0.836675385063782,
      "predicted_classes": 560,
      "classes_f1_zero": 28
    },
    "lr_tuned_c2": {
      "accuracy": 0.8376600284495022,
      "classes_f1_zero": 23,
      "macro_f1": 0.7931543818638241,
      "macro_precision": 0.8238666389449272,
      "macro_recall": 0.7924848742690451,
      "predicted_classes": 566,
      "weighted_f1": 0.838439717113135
    },
    "hard_tuned_lr_svc_knn": {
      "accuracy": 0.8369132290184922,
      "classes_f1_zero": 21,
      "macro_f1": 0.7965170720239344,
      "macro_precision": 0.8227126480439321,
      "macro_recall": 0.7981336562721902,
      "pipeline_bytes": 3554419,
      "predicted_classes": 567,
      "saved_validation_predict_seconds_sum": 300.7933576739997,
      "status": "PASS",
      "weighted_f1": 0.8376817578041393
    }
  },
  "evidence_sha256": {
    "artifacts/metadata/phase3_audit/colab_evidence.json": "41a4ad3b0c3b8c783382b807688fd0958b00666b6e46bb84c3d3fe1e8c16fb48",
    "artifacts/metadata/post_tuning_audit/colab_evidence.json": "70849a69a0d2cd571e2d93a938b98a9167b9d46ceb0db9d6cb1859f6a2e415e8",
    "artifacts/metadata/model_analysis/colab_supplement.json": "4ccfa85ac4639778ffae6d11a435fb78af825bb4e1c294792356bec7236b4d28",
    "artifacts/metadata/final_ml_gaps/colab_evidence.json": "7c2ed8e6705347a850bb90e88cdea54067d0d12ec5553588ce03fbd0a99725ac"
  }
}
''')
