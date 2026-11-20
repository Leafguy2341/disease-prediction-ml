# Phase 4 — phase4-20261028T091711786379Z-c1c66643

LR/SVC: disagreement=7.6387%; joint error=14.4488%; LR sai, SVC đúng=1.8421%; SVC sai, LR đúng=2.4716%.
hard_lr_svc_knn: sửa 152 hàng LR sai, làm sai 170 hàng LR đúng. hard_lr_svc_nb: sửa 160 hàng LR sai, làm sai 187 hàng LR đúng. hard_lr_svc_rf: sửa 153 hàng LR sai, làm sai 199 hàng LR đúng.
Ứng viên theo validation: single_logistic_regression, Macro F1=0.78780814; delta so LR=+0.00000000. Chưa có ensemble vượt LR trên split này. Chênh lệch không chứng minh ý nghĩa thống kê. Chỉ thử 3 hard/2 soft đã định, không tìm trọng số. Xác suất được kiểm đúng cấu trúc, chưa chứng minh calibration; đây là giới hạn của soft voting. Ba vote với ưu tiên LR khi hòa không cứu được hàng cả LR/SVC cùng sai, ngay cả khi model thứ ba đúng; model thứ ba chỉ đổi quyết định khi tạo đa số hoặc phá tình huống LR/SVC bất đồng. Chi phí prediction cộng của baseline chỉ là tham chiếu, không phải benchmark ensemble hoặc latency chatbot. KNN chậm trên toàn validation; số byte checkpoint nén không phải peak RAM. Support lớp nhỏ và việc dùng lại validation để lựa chọn hạn chế kết luận tổng quát hóa. Không mở test.

```text
               combination   mode    status  base_models  accuracy  macro_precision  macro_recall  macro_f1  weighted_f1  predicted_classes  classes_f1_zero  tie_rows  delta_macro_f1_vs_lr  pipeline_bytes  original_base_predict_seconds_sum reason
single_logistic_regression single completed            1  0.837091         0.827420      0.779189  0.787808     0.836675                560               28         0              0.000000         1438385                           2.157469       
           hard_lr_svc_knn   hard completed            3  0.836451         0.821900      0.781083  0.787334     0.835979                559               29      1000             -0.000474         3554613                         298.208127       
            hard_lr_svc_nb   hard completed            3  0.836131         0.827957      0.771870  0.784789     0.835346                558               30       659             -0.003019         3004702                           9.730969       
            hard_lr_svc_rf   hard completed            3  0.835455         0.825147      0.773429  0.784053     0.834776                558               30      1263             -0.003755        17322971                          24.667872       
             soft_lr_nb_rf   soft completed            3  0.825427         0.819365      0.685326  0.724694     0.821102                532               56         0             -0.063114        15961902                          28.588366       
            soft_lr_knn_nb   soft completed            3  0.826991         0.831142      0.741390  0.763243     0.827000                548               39         0             -0.024566         2193544                         302.128620       
```

Single input: {'status': 'PASS', 'input_features': 375, 'matches_validation_row_0': True}.

Limitations: [].

Uniform voting; no training/calibration/tuning or test evaluation. Probabilities are validated model outputs, not clinically calibrated confidence.
