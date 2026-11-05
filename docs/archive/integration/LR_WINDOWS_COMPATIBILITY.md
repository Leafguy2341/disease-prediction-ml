> ARCHIVE — Bản tại thời điểm trước hợp nhất tài liệu. Các trạng thái và lệnh cũ không phải hướng dẫn hiện hành. Xem [chỉ mục hiện hành](../../README.md) và [triển khai](../../DEPLOYMENT_GUIDE.md). Đường dẫn trong code block vẫn tính từ project root.

# Kiểm chứng LR tuned trên Windows Python 3.13.17

Ngày 2026-10-30: qualification và **real Prediction API PASS** cho Windows CPython3.13.17/AMD64.
Allowlist chỉ áp dụng checkpoint LR tuned C=2 đã kiểm, với đúng năm ML/runtime versions bên dưới.
Identity training Python3.13.18 và các checksum/schema/source guards được giữ nguyên.
Không dùng Python3.11.9/sklearn1.8.0 để deserialize checkpoint.

**Cập nhật sau khi nhận reference local:** file `artifacts/metadata/runtime_compatibility/lr-31318-synthetic-reference.json`
có SHA-256 `5fe06a3637c471403d46cdb87b2e5cce2a742e8fff1c99aa4a6cb7caef53d0dc`.
Đã so sánh đủ4.696 probabilities theo protocol: PASS, max absolute difference
`2.168404344971009e-19`, max relative difference `2.567201261121586e-16`, không có phần tử
ngoài tolerance. Exact8 labels, Top3 IDs/names, input hash, schema/mapping,8 source pins,
7 artifact hashes và checkpoint identity đều PASS; hai bên không có load warnings.
Owner đã gửi đúng checksum trên từ Colab: **transfer integrity PASS**.
`windows31317-v1/reference_comparison_verified.json` ghi đối chiếu hoàn tất;
`real_api_smoke_verified.json` ghi actual TestClient và `uvicorn_http_smoke_verified.json`
ghi HTTP TCP thật trên localhost: health200/REAL CHECKPOINT VERIFIED và predict200,
Top3 khớp reference, scores không chuẩn hóa lại. Không gọi Gemini.
Các evidence pending/negative trước approval được giữ nguyên như lịch sử;
không cần sinh lại reference hoặc chạy notebook06.

Interpreter đã phát hiện: `D:\Program Files (x86)\Python\python.exe`, Python3.13.17/Windows AMD64.
Môi trường riêng `.venv-web` dùng numpy2.1.3, pandas2.2.3, scipy1.16.3, sklearn1.6.1,
joblib1.6.0 và các API dependencies trong `requirements-api.txt`. `pip check` PASS.
Python3.11.9 và packages toàn cục không thay đổi. `.venv-web` không được đưa vào repository.

Kiểm môi trường đã chuẩn bị từ PowerShell tại root project:

```powershell
$ApiPython = (Resolve-Path -LiteralPath '.\.venv-web\Scripts\python.exe').Path
& $ApiPython --version
& $ApiPython -m pip check
```

Lệnh chuẩn bị đã chạy là `py -3.13 -m venv .venv-web`, rồi dùng chính interpreter trong
`.venv-web` chạy `-m pip install --disable-pip-version-check --no-input -r requirements-api.txt`.
Không chạy lại lệnh tạo venv lên folder đã tồn tại; không cài các pin này vào Python3.11 toàn cục.

## Protocol chốt trước inference

Protocol lưu ở `artifacts/metadata/runtime_compatibility/windows31317-v1/protocol.json`, SHA-256
`4109e06228c46cd7fddd59bbabfd6cf694ffdd26b7dca3203c569857e151e604`.
Chỉ experiment `tuning-v1-9c4dd013abbba14a`, selected identity `tuned-v1-b8a5602679b3dc5c`,
LR C=2; pipeline SHA-256 `4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6`.

- Tám vector cố định: all-zero; cough; fever; cough+fever; nausea+vomiting;
  headache+fatigue; cough+fever+shortness of breath; all-one. Không lấy từ bất kỳ split nào.
- Dựng uint8 theo đúng 375 feature; 587 cột probability theo thứ tự Phase2; một BLAS thread.
- So toàn bộ `predict_proba`: `rtol=1e-10`, `atol=1e-12`, công thức
  `abs(candidate-reference) <= atol + rtol * abs(reference)` cho từng phần tử.
- `predict()` labels và Top3 class IDs phải giống hoàn toàn; tie dùng stable Phase2 class order.
  Điểm là model scores chưa calibration, không chuẩn hóa lại Top3.
- Không nới tolerance sau khi xem kết quả. Zero/all-one chỉ là boundary checks, không phải input
  API hợp lệ hoặc ví dụ lâm sàng. Không đặt nhãn bệnh kỳ vọng cho các vector synthetic.
- Reference bắt buộc được sinh mới trên **Colab Linux Python3.13.18** cùng đúng các ML versions.
  Packet inference baseline cũ, saved validation/test predictions hoặc inference chạy lại trên
  chính Windows3.13.17 đều không thay thế được reference độc lập.

## Bước tiếp theo: lấy reference từ Colab gốc

Chỉ chạy setup/import shared bootstrap đã có trên Colab và mount canonical Drive.
Không Run All notebook03/04/06, không bật tuning/final-test switch.
Biến `ROOT` phải trỏ source runtime đã verify; `DRIVE_ROOT` dưới đây là storage đã mount.
Không cần upload riêng một file `.py`, thay source release, cài packages trên kernel hoặc copy dataset.

Dán **một cell riêng** dưới đây vào notebook/scratch notebook dùng kernel Colab gốc.
Cell kiểm đủ bảy artifact và source pins trước trusted load; không gọi dataset loader,
không fit, không đọc saved split predictions và không ghi Drive. Chỉ tạo một JSON mới trong `/content`.
Nếu Python không còn là3.13.18 hoặc ML versions khác, **dừng và gửi lỗi**; không sửa guard,
metadata hoặc tự dùng kernel khác làm reference đã duyệt.

```python
from pathlib import Path
import hashlib, json, platform, sys, warnings
import numpy as np
import pandas as pd
from sklearn.utils.validation import check_is_fitted
from threadpoolctl import threadpool_limits
from src.agent.extraction import Catalog
from src.data.loader import sha256_file
from src.models.ensemble import phase4_guard, validate_probabilities
from src.models.final_evaluation import protocol, versions
from src.models.training import build_pipeline, load_fitted_checkpoint

# These private globals are only for the isolated Windows diagnostic run.
# Leave them unset in Colab; they never change the production API's guard.
reference_mode = globals().get('_LR_REFERENCE_MODE', True)
SOURCE = Path(ROOT).resolve()
DRIVE_ROOT = Path(globals().get('_LR_STORAGE_ROOT',
    '/content/drive/MyDrive/ML_Projects/disease-prediction-ml')).resolve()
OUTPUT = Path(globals().get('_LR_OUTPUT', '/content/lr-31318-synthetic-reference.json'))
assert not OUTPUT.exists(), 'Output exists; do not overwrite previous evidence.'
assert not OUTPUT.resolve().is_relative_to(DRIVE_ROOT), 'Output must be outside storage.'
frozen = protocol()
cp, ti = frozen['checkpoints']['lr_tuned_c2'], frozen['tuning']
identity = cp['identity']
expected_versions = dict(identity['versions'])
if not reference_mode:
    expected_versions['python'] = '3.13.17'
assert versions() == expected_versions, ('Unexpected environment', versions(), expected_versions)
assert platform.system() == ('Linux' if reference_mode else 'Windows')
if reference_mode:
    import google.colab  # Reject a plain Linux kernel as an original-Colab reference.
else:
    assert platform.machine().upper() in ('AMD64', 'X86_64')
assert ti['experiment_id'] == 'tuning-v1-9c4dd013abbba14a'
assert identity['experiment_id'] == 'tuned-v1-b8a5602679b3dc5c'
assert identity['config']['models']['logistic_regression']['C'] == 2
assert cp['files']['pipeline.joblib']['sha256'] == '4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6'

checked = {}
def verify(relative, expected, source=False):
    base = SOURCE if source else DRIVE_ROOT
    path = (base / relative).resolve()
    assert path.is_relative_to(base) and path.is_file(), relative
    actual = sha256_file(path)
    assert actual == expected['sha256'], ('Checksum mismatch', relative)
    assert 'bytes' not in expected or path.stat().st_size == expected['bytes'], relative
    checked[('source:' if source else '') + relative] = actual
    return path

cases = [('zero_boundary', []), ('cough_only', ['cough']), ('fever_only', ['fever']),
    ('cough_fever', ['cough', 'fever']), ('gastro', ['nausea', 'vomiting']),
    ('headache_fatigue', ['headache', 'fatigue']),
    ('respiratory', ['cough', 'fever', 'shortness of breath']), ('all_one_boundary', 'ALL')]
with phase4_guard(DRIVE_ROOT) as guard:
    for name, value in identity['source_sha256'].items():
        verify(name, {'sha256': value}, source=True)
        module = sys.modules.get(name[:-3].replace('/', '.'))
        assert module is None or Path(module.__file__).resolve() == SOURCE / name, name
    phase = json.loads(verify('artifacts/metadata/phase2/dataset_manifest.json',
        {'sha256': frozen['phase2_manifest_sha256']}).read_text(encoding='utf-8-sig'))
    assert phase['status'] == 'finalized' and phase['test_locked']
    assert phase['files'] == frozen['phase2_files'] and phase['processed'] == frozen['processed']
    for name in ('feature_schema.json', 'label_mapping.json'):
        relative = 'artifacts/metadata/phase2/' + name
        verify(relative, frozen['phase2_files'][relative])
    catalog = Catalog.load(SOURCE, DRIVE_ROOT)
    assert len(catalog.features) == 375 and len(catalog.classes) == 587
    assert catalog.schema_id == phase['processed']['schema_sha256']
    tm = json.loads(verify('artifacts/metadata/tuning/' + ti['experiment_id'] + '/manifest.json',
        {'sha256': ti['manifest_sha256']}).read_text(encoding='utf-8-sig'))
    assert tm['status'] == 'completed' and tm['experiment_id'] == ti['experiment_id']
    assert tm['identity'] == identity
    for name in ('pipeline.joblib', 'fit.json', 'metadata.json'):
        relative = cp['folder'] + '/' + name
        if name == 'pipeline.joblib':
            assert tm['files'][relative] == cp['files'][name]
        verify(relative, tm['files'][relative])
    folder = DRIVE_ROOT / cp['folder']
    fit = json.loads((folder / 'fit.json').read_text())
    meta = json.loads((folder / 'metadata.json').read_text())
    assert fit['status'] == 'fitted' and meta['status'] == 'completed'
    assert fit['identity'] == meta['identity'] == identity
    assert fit['model'] == meta['model'] == 'logistic_regression'
    assert fit['n_input_features'] == 375 and fit['n_retained_features'] == 318
    assert fit['pipeline_sha256'] == meta['pipeline_sha256'] == cp['files']['pipeline.joblib']['sha256']
    assert meta['fit_metadata_sha256'] == sha256_file(folder / 'fit.json')
    assert meta['predictions_sha256'] == tm['files'][cp['folder'] + '/validation_predictions.npz']['sha256']
    # Compare metadata strings only; do not open validation_predictions.npz.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model = load_fitted_checkpoint(folder, identity, trusted=True)
    expected = build_pipeline('logistic_regression', identity['config'])
    assert model.feature_names_in_.tolist() == list(catalog.features)
    assert np.array_equal(model.classes_, np.arange(587))
    assert [k for k, _ in model.steps] == [k for k, _ in expected.steps]
    assert all(type(a) is type(b) and a.get_params(deep=False) == b.get_params(deep=False)
        for (_, a), (_, b) in zip(model.steps, expected.steps))
    lr = model.named_steps['estimator']
    check_is_fitted(lr, attributes=['coef_', 'intercept_', 'classes_', 'n_features_in_'])
    assert lr.coef_.shape == (587, 318) and lr.intercept_.shape == (587,) and lr.n_features_in_ == 318
    assert np.isfinite(lr.coef_).all() and np.isfinite(lr.intercept_).all()
    assert all(p == 'ALL' or set(p) <= set(catalog.features) for _, p in cases)
    x = pd.DataFrame([[int(p == 'ALL' or f in p) for f in catalog.features] for _, p in cases],
        columns=catalog.features, dtype='uint8')
    with threadpool_limits(limits=1):
        proba = np.asarray(model.predict_proba(x), dtype=np.float64)
        labels = np.asarray(model.predict(x))
    validate_probabilities(proba, len(cases), model.classes_, 587)
    assert np.issubdtype(labels.dtype, np.integer) and labels.shape == (len(cases),)
    assert np.array_equal(labels, proba.argmax(axis=1))
    rank = np.argsort(-proba, axis=1, kind='stable')[:, :3]
    assert not any(guard.values()), guard
    packet = dict(protocol_id='lr-windows31317-synthetic-v1',
        status='REFERENCE GENERATED' if reference_mode else 'NOT VERIFIED',
        kind='original_colab_reference' if reference_mode else 'windows_candidate_probe',
        versions=versions(), platform=platform.platform(), executable=sys.executable,
        feature_count=375, class_count=587, retained_features=318,
        tuning_experiment=ti['experiment_id'], selected_identity=identity['experiment_id'],
        checkpoint_sha256=cp['files']['pipeline.joblib']['sha256'],
        schema_sha256=catalog.schema_id, checked=checked,
        cases=[{'id': n, 'present': p} for n, p in cases],
        input_sha256=hashlib.sha256(x.to_numpy().tobytes(order='C')).hexdigest(),
        predict_labels=labels.tolist(), top3_class_ids=rank.tolist(),
        top3_labels=[[catalog.classes[i] for i in row] for row in rank],
        predict_proba=proba.tolist(), probability_rtol=1e-10, probability_atol=1e-12,
        warnings=[type(w.message).__name__ + ': ' + str(w.message) for w in caught],
        guards=dict(guard), models_fitted=0, dataset_payload_opened=False,
        independently_compared=False, production_runtime_approved=False)
raw = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
with OUTPUT.open('xb') as out:
    out.write(raw)
print(json.dumps({'output': str(OUTPUT), 'sha256': hashlib.sha256(raw).hexdigest(),
    'status': packet['status'], 'versions': packet['versions'], 'cases': len(cases),
    'checked_artifacts': sum(not k.startswith('source:') for k in checked),
    'source_pins': sum(k.startswith('source:') for k in checked), 'guards': dict(guard)}, indent=2))
```

Sau khi cell thành công, download JSON từ runtime về Windows bằng giao diện VS Code/Colab Files.
Gửi đường dẫn local tuyệt đối tới `lr-31318-synthetic-reference.json` và SHA-256 cell in ra.
File chỉ chứa synthetic vectors/predictions và identity, không có patient data hoặc API key.
Không đổi reference thành `PASS`: chưa so sánh hai môi trường tại bước sinh reference.

Nếu Colab hiện không cung cấp đúng3.13.18 cùng các ML versions, ghi **reference NOT VERIFIED**
và dừng. Không build Python3.13.18, sửa manifest hoặc dùng predictions đã lưu để lấp thiếu bằng chứng.

## Kết quả Windows và Prediction API

Kết quả candidate probe, comparison và real API smoke lưu riêng trong namespace audit ở trên:

| Kiểm tra | Kết quả thực trên Windows |
| --- | --- |
| Bảy artifact / tám source pins | PASS, đọc đúng7 artifact, không đọc dataset/saved predictions |
| Trusted loader, variance/CSR/LR C=2 | PASS; 375 input →318 fitted variance features;587 classes đúng thứ tự |
| Tám synthetic vectors | PASS kiểm tra thực thi;8×587 finite probabilities, tổng hàng hợp lệ; predict khớp argmax |
| Load warnings | Không có warning |
| Fit/test/protected writes | Cả ba guard counters bằng0; process audit bổ sung cấm mọi dataset/split-prediction open |
| Đối chiếu original Colab3.13.18 | PASS; checksum owner xác nhận,8×587 probabilities/labels/Top3/identity khớp |
| Production API | PASS: actual TestClient và Uvicorn HTTP health200/predict200 với checkpoint thật |
| Compatibility scope | Chỉ Windows/AMD64/CPython3.13.17 và exact ML versions/checkpoint;3.11.9 vẫn bị chặn |
| API/chat regression | 71 tests PASS với synthetic fixtures;1 TestClient deprecation warning |

`windows_candidate_probe.json` SHA-256
`a06487b71ab6ff7d44210bace9665d999103cedac6cf6b055ac6738267cadfdc` chứa toàn bộ candidate
probabilities và identity. `production_guard_check.json` ghi negative HTTP check riêng.
Candidate probe được chạy bằng chính cell tài liệu ở trên trong process `.venv-web` mới,
với `_LR_REFERENCE_MODE=False`, root local thật và output tạm ngoài storage; sau đó lưu evidence mới
vào namespace audit. Không monkeypatch version hoặc sửa production code.

Production API chấp nhận exact training identity gốc hoặc allowlist hẹp trong
`app/backend/prediction.py`. Sai bất kỳ dependency version, OS/architecture/implementation,
selected identity hoặc checkpoint SHA thì ngoại lệ không áp dụng. Không có flag bypass.
Không sửa `identity['versions']`, monkeypatch `versions()` hoặc tắt checksum để chạy web.

Để mở API sau khi dừng server cũ bằng Ctrl+C, chạy từ PowerShell tại root project:

```powershell
$ApiPython = (Resolve-Path -LiteralPath '.\.venv-web\Scripts\python.exe').Path
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
& $ApiPython -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Root trên đúng với7artifact hiện có trong project này. Máy khác phải đặt artifact root thật,
giữ nguyên relative paths. Mở `http://127.0.0.1:8000/health` hoặc `/docs` để kiểm Prediction API.
Gemini live/schema chưa được xác minh lại trong nhiệm vụ này; API model PASS không đồng nghĩa chat live PASS.
