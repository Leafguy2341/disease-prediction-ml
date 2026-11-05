> ARCHIVE — Bản tại thời điểm trước hợp nhất tài liệu. Các trạng thái và lệnh cũ không phải hướng dẫn hiện hành. Xem [chỉ mục hiện hành](../../README.md) và [triển khai](../../DEPLOYMENT_GUIDE.md). Đường dẫn trong code block vẫn tính từ project root.

# Preflight notebook 03 — 2026-10-28

**Kết luận: PASS trong phạm vi review code, unit test không huấn luyện và smoke local. Không phát hiện lỗi chức năng cần sửa.** Chưa xác nhận end-to-end training/resume, hội tụ hoặc RAM thực tế trên Colab. Giữ nguyên 14 cell notebook, config, model, bootstrap và checkpoint hiện có.

## Kết quả theo yêu cầu

| Mục | Trạng thái | Bằng chứng và giới hạn |
|---|---|---|
| 1. Config và dependency | **PASS local** | Đọc toàn bộ config và module model; import thành công. Cả 5 estimator và các bước pipeline qua kiểm parameter mà không fit. Phiên bản local nằm trong các khoảng requirements. |
| 2. Shared bootstrap | **PASS review/unit** | Cell setup gọi `runpy.run_path(<Drive root>/src/data/colab_runtime.py)['bootstrap_runtime'](..., phase=3)`, dùng canonical config và workspace `/content/disease-prediction-ml-runtime`. Không có dependency colab-session/receipt/archive trong luồng 03. Legacy adapter/package còn trong repo nhưng không được notebook gọi. |
| 3. Nạp train/validation | **PASS dữ liệu thật local** | `session.load_data()` → cache whitelist → `load_training_data()` → `load_final_split` với đúng tên train và validation. Checksum, thứ tự 375 feature, dtype uint8, mapping đủ 587 mã nhãn và group alignment đạt. Không mở/copy/hash CSV test. |
| 4. Checkpoint Drive/reuse | **PASS review/unit; Colab pending** | Output root canonical nằm trong Drive; checkpoint ở `artifacts/models/phase3/<experiment_id>/<model>/`. Unit xác nhận checksum/identity/alignment/metrics được kiểm trước reuse và completed reuse không deserialize/fit. Chưa thử reset Colab rồi nạp một model đã fit thật. |
| 5. Nhánh fit, thời gian, metrics, lưu | **PASS review; fit thực chưa chạy** | `train_model` gọi `run_model_safely` → `run_model`. Chưa có checkpoint thì gọi callback `.fit(X_train,y_train)` trong cell, hoặc `pipeline.fit` của batch API. `perf_counter` đo fit/predict; metrics dùng y_validation và predictions; model/predictions/metadata lưu sau từng bước. Không gọi nhánh fit trong review này. |
| 6. Tài nguyên | **PASS cấu hình/unit batch; tải thực pending** | KNN batch 64, single worker; RF tối đa 2 worker, 100 cây, depth24, ≤512 lá/cây; LinearSVC `dual=auto`, max_iter3000. Context BLAS1/working_memory128MiB và guard RAM≥2GiB có trong code. Đây không phải cam kết không OOM hoặc bảo đảm hội tụ. |
| 7. Chống leakage preprocessing | **PASS review** | Notebook và batch API cùng pipeline `VarianceThreshold(0) → CSR → estimator`. Fit chỉ nhận X_train/y_train; validation chỉ `.predict` và tính metric. `to_csr` không học tham số. Loader không fit/rebuild schema hoặc label mapping. Chưa fit variance nên chưa có số feature thực tế sau mask training. |
| 8. Serialization custom function | **PASS local fresh process; Colab pending** | Năm pipeline **chưa fit** được joblib dump/load trong process mới, import từ bản copy source khác đường dẫn. Transformer gọi đúng `src.models.training.to_csr`, transform mẫu nhỏ ra CSR float64. Không dùng lambda làm `FunctionTransformer.func`; lambda callback fit của notebook không nằm trong object được serialize. Chưa load fitted pipeline trên Colab thật. |
| 9. Hình/bảng từ kết quả thực | **PASS review/unit rỗng** | Records chỉ được thêm từ kết quả run/reuse. Chart đọc checkpoint, kiểm checksum/row/group/predictions và tính lại metric; không có metric/performance giả khi thiếu kết quả. Unit failure-only trả metric NA, không sinh hình/file. Không tạo hình model-performance trong review này. |
| 10. Bảo toàn/phạm vi | **PASS** | Không thêm model, không tạo môi trường, không sửa Phase2, không chạy ensemble hoặc evaluate test. Hash code/notebook/config/dataset và stat file test được đối chiếu cuối review; không mở payload test để băm. |

## File/dependency đã rà soát

- [phase3.json](../../../configs/phase3.json), [notebook03](../../../notebooks/03_model_training.ipynb), [models/notebook.py](../../../src/models/notebook.py), [training.py](../../../src/models/training.py), [runtime.py](../../../src/models/runtime.py), [reporting.py](../../../src/models/reporting.py).
- Luồng runtime/data trực tiếp: [colab_runtime.py](../../../src/data/colab_runtime.py), [integrity.py](../../../src/data/integrity.py), [paths.py](../../../src/data/paths.py), [loader.py](../../../src/data/loader.py), `load_final_split` trong [preprocessing.py](../../../src/data/preprocessing.py); kiểm các import/helper trực tiếp của chúng. Không thay code preprocessing.
- [requirements-training.txt](../../../requirements-training.txt), [requirements-notebooks.txt](../../../requirements-notebooks.txt). Dependency model trực tiếp: NumPy, pandas, SciPy sparse, scikit-learn, joblib, psutil, threadpoolctl, matplotlib và IPython. Không cài/download package trong review.

Interpreter hiện có: **Windows Python 3.11.9**; NumPy2.3.5, pandas2.3.3, SciPy1.17.1, sklearn1.8.0, matplotlib3.10.8, joblib1.5.3, psutil7.2.2, threadpoolctl3.6.0, IPython9.10.1. Không dùng `.venv` hoặc giả lập một lần chạy Colab thành công.

## Checkpoint và giới hạn phục hồi

Identity bao gồm config, fingerprint train/validation/schema/mapping, manifest, phiên bản Python/sklearn/NumPy/SciPy/joblib và checksum source liên quan. Khác identity tạo experiment khác; không hứa reuse checkpoint qua thay đổi source/config/library. `pipeline.joblib` được tạo tại thư mục tạm, copy/check SHA lên persistent folder rồi publish; `fit.json` ghi danh tính và model SHA. Predictions và `metadata.json` được ghi tiếp sau khi validation thành công.

- **Đã completed:** kiểm model SHA, fit-metadata SHA, predictions SHA, labels/groups/row order và tính lại metric; trả REUSED mà không deserialize hoặc fit. Unit đã kiểm nhánh này bằng fixture metadata/bytes trong tmp.
- **Fit hoàn tất, validation chưa hoàn tất:** giữ `pipeline.joblib`/`fit.json`. Sau restart cần gọi model cell với **`trust_own_checkpoints=True`** trong `session.train_model(...)` cho checkpoint của chính người dùng; mặc định False nên việc deserialize bị từ chối rõ. Đây là tùy chọn hiện có, không thêm cơ chế mới. `fit` callback được bỏ qua khi resume nhánh này.
- **VM mất khi đang fit, trước publish:** chưa có checkpoint cho model đang chạy; phải fit lại model đó trong một nhiệm vụ training được cho phép. Các model đã publish trước vẫn nằm trên Drive. Không có phục hồi giữa các iteration/tree.

Chỉ byte fixture không phải model được dùng cho unit integrity; không deserialize byte giả đó. Không có fitted artifact của dự án trong workspace để kiểm resume thật mà vẫn tuân thủ lệnh không training. Cần đúng module tùy biến và phiên bản thư viện tương thích khi load; xem [model persistence](https://scikit-learn.org/stable/model_persistence.html) và [FunctionTransformer](https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.FunctionTransformer.html).

## Tài nguyên và cách diễn giải

KNN `_predict` cắt từng `x.iloc[start:start+64]`; unit spy nhận đúng batch **64/64/7**, prediction ghép đúng hàng. Spy chỉ kiểm điều phối, không phải dự đoán bệnh hoặc kết quả model thật. Với 131.248 dòng train, riêng một block khoảng cách 64×131.248 float64 khoảng 64 MiB nếu materialize; còn train/CSR/index/buffer khác. Batch không làm mất chi phí brute-force hoặc biến tổng RAM thành 64 MiB.

`working_memory=128` là gợi ý giới hạn một số mảng tạm của sklearn, **không phải trần RSS của toàn process**. RF có thể tốn RAM theo số node và 587 lớp; LinearSVC đa lớp vẫn cần thời gian/hội tụ thực. Guard RAM đầu bước và log RSS không chứng minh mọi model vừa runtime. Không tự đổi hyperparameter đã duyệt để né một OOM chưa được quan sát. [Ý nghĩa working_memory](https://scikit-learn.org/1.8/modules/generated/sklearn.set_config.html).

## Unit test thực hiện

**42 passed, 12 deselected**, không có failure cuối cùng. Bổ sung [test_phase3_preflight.py](../../../tests/test_phase3_preflight.py): constructor notebook/API khớp, tham số hợp lệ, batch/order, metric trên nhãn unit nhỏ, completed reuse và chống checksum/identity/metric/alignment sai, trust gate, fresh-process serialization pipeline chưa fit và failure-only không tạo hình.

```powershell
python -m pytest -q -p no:cacheprovider tests/test_phase3_preflight.py tests/test_phase3_training.py tests/test_canonical_colab_runtime.py tests/test_manifest_deployment.py -k "not each_pipeline and not real_synthetic_fits and not bad_identity and not prediction_failure and not failure_rows and not compact_notebook_interface and not visible_fit_callback and not source_bundle"
```

Đã chạy lệnh lựa chọn trên qua Python runner có guard: **0 lần gọi fit classifier/feature transformer và 0 lần mở test CSV đã khóa**. Mười một test có fit và một test packaging ZIP lịch sử được bỏ chọn; không gọi toàn bộ suite. Fixtures preprocessing của test cũ chỉ tạo dữ liệu tổng hợp trong tmp, không sửa bộ Phase2 dự án.

Lượt đầu guard chặn quá rộng, dẫn đến 9 failure do sklearn metrics dùng `LabelEncoder.fit` tạm bên trong `multilabel_confusion_matrix`. Chưa có model nào được fit. Đã sửa guard của test để chỉ cho phép thao tác mã hóa nội bộ trong call stack metrics, không cho phép fit mapper/transformer/model. Lượt cuối ghi **11 lần mã hóa nhãn nội bộ cho metrics**, không thay mapping Phase 2. Đây là lỗi guard kiểm thử, không phải lỗi code training; không sửa helper production để làm test qua.

## Smoke trên dữ liệu thật local

Chạy trong process mới: import → `ColabTraining.open` với context **local-preflight được ghi rõ** → `session.load_data` qua cache tạm → tạo 5 pipeline và kiểm chúng chưa fit. Không gọi bootstrap Colab trên Windows; không đánh dấu Stage A/B hoặc Drive write PASS giả. Cache được xóa khi process kết thúc, không ghi report/model vào project.

| Tập | Dòng | Feature theo schema | Nhãn | Group |
|---|---:|---:|---:|---:|
| Train | 131248 | 375 | 587 | 117211 |
| Validation | 28120 | 375 | 587 | 25127 |

Stage C local đạt 7 checksums; manifest `ca20a551b1bf773c3dac59af40a56efa6552919e84136d44dd7117c39d038e02`; processed fingerprint `afde00ce35bf4fd31c9c76edcc3c8b64104e53fb81dd98d4a56d7b3a884b16b3`. Smoke có guard chặn **mọi** sklearn fit/fit_transform/partial_fit và mọi file tên `test.csv.gz`: **fit_calls=0, test_csv_open_attempts=0**, đủ 5 pipeline chưa fit, records rỗng. Smoke không tính model metrics, không gọi predict hoặc sinh hình.

## Chưa xác minh trong lần này trên Colab thật

[Smoke A/B/C cũ do người dùng gửi](../runtime/portability_validation.md) vẫn là bằng chứng môi trường/Drive/import/data-loading; không chứng minh model đã fit hoặc resume được. Không có kết nối trực tiếp đến kernel Colab ở lần review hiện tại. Chưa kiểm: fit 5 model, hội tụ/peak RSS/timing thực; fitted pipeline serialize/reload sau VM reset; copy/publish checkpoint lớn trên Drive và tạo chart từ predictions model thật.

Khi chỉ muốn lặp preflight trên Colab, chọn/mount đúng kernel theo [hướng dẫn hiện hành](../runtime/phase3_colab.md), chạy các cell setup, mở session, load_data và imports/make_pipeline. **Không Run All notebook 03 và không chạy 5 cell `session.train_model` hoặc `show_results`.** Có thể dùng scratch cell sau; không cần thêm notebook:

```python
from sklearn.exceptions import NotFittedError
from sklearn.utils.validation import check_is_fitted
from src.models.runtime import MODEL_NAMES
from src.models.training import build_pipeline

pipelines = {name: build_pipeline(name, session.config) for name in MODEL_NAMES}
for name, pipeline in pipelines.items():
    for key in ("variance", "estimator"):
        try:
            check_is_fitted(pipeline.named_steps[key])
        except NotFittedError:
            continue
        raise AssertionError(f"{name}/{key} đã fit ngoài dự kiến")
print("Pipelines created, none fitted:", list(pipelines))
del pipelines
```

Không đổi source/config nên fingerprint vẫn `95b01d6ea67d68f9bbc48b647ca15b3c38219baac15639ae78637f184806bd61`; không cần tạo lại deployment hoặc upload source cho lần review này. Chỉ thêm file test/báo cáo này và cập nhật [nhật ký chung](../planning/PROJECT_DEVELOPMENT_LOG.md). **Dừng trước training.**
