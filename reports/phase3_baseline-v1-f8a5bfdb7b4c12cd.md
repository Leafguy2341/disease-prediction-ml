# Phase 3 — baseline-v1-f8a5bfdb7b4c12cd

Runtime: colab; Drive read/write: True.

Hoàn tất 5/5 mô hình. Macro F1 validation cao nhất: logistic_regression. Phase 4 ready: True. Chưa mở/evaluate test; chưa huấn luyện ensemble.

```text
              model    status  accuracy  macro_precision  macro_recall  macro_f1  weighted_f1  fit_seconds  prediction_seconds  n_retained_features  sampled_peak_rss_mb  warnings error
logistic_regression completed  0.837091         0.827420      0.779189  0.787808     0.836675    91.594202            2.157469                  318          1167.636719         6      
      random_forest completed  0.700533         0.659651      0.441230  0.491997     0.699311    15.100765           20.683900                  318          1169.132812         3      
         linear_svc completed  0.830797         0.815206      0.781399  0.784222     0.829866    80.596166            1.826504                  318          1313.382812         5      
                knn completed  0.783144         0.783620      0.731920  0.731034     0.786804     1.090415          294.224154                  318          1266.726562        31      
       bernoulli_nb completed  0.814865         0.672297      0.573875  0.599341     0.805250     1.836178            5.746997                  318          1569.343750         2      
```

zero_division=0; macro scores tính trên đầy đủ label mapping. Thời gian reused thuộc lần fit/predict gốc. GPU không được các estimator sklearn CPU này sử dụng. Lớp có ít support validation cần diễn giải thận trọng.

Manifest Phase 3: `/content/drive/MyDrive/ML_Projects/disease-prediction-ml/artifacts/metadata/phase3/baseline-v1-f8a5bfdb7b4c12cd/run_summary.json`. Mỗi model có pipeline.joblib, fit.json, validation_predictions.npz và metadata.json khi validation hoàn tất. Pipeline fit-only vẫn giữ nếu predict lỗi. Chỉ deserialize pipeline do chính bạn tạo và tin cậy.

LinearSVC has no predict_proba. Use compatible probability models or training-only group-aware calibration in a later phase; no fabricated probabilities.
