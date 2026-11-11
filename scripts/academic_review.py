"""Offline presentation audit; never imports estimators or reads dataset payloads.

Snapshot first; preservation verification compares complete original cell objects.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'reports/academic_review_20261111'


def storage_root():
    return Path(os.environ.get('DISEASE_API_STORAGE_ROOT') or ROOT).expanduser().resolve()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def source(cell):
    value = cell.get('source', [])
    return ''.join(value) if isinstance(value, list) else value


def inventory():
    assert not (AUDIT / 'snapshot_manifest.json').exists(), 'Snapshot already exists; do not overwrite.'
    books = []
    for path in sorted((ROOT / 'notebooks').glob('*.ipynb')):
        raw = path.read_bytes()
        snapshot = AUDIT / 'snapshots' / path.name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        with snapshot.open('xb') as stream:
            stream.write(raw)
        nb = json.loads(raw)
        cells = []
        names = []
        for cell in nb['cells']:
            try:
                tree = ast.parse(source(cell)) if cell['cell_type'] == 'code' else ast.Module(body=[], type_ignores=[])
                loads = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)})
                stores = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)})
            except SyntaxError:
                loads, stores = [], []
            names.append((loads, stores))
        for i, cell in enumerate(nb['cells']):
            text = source(cell)
            protected = cell['cell_type'] == 'code' or bool(cell.get('outputs'))
            consumers = [j for j in range(i + 1, len(names)) if set(names[i][1]) & set(names[j][0])]
            empty = not text.strip()
            cells.append(dict(index=i, cell_id=cell.get('id'), cell=cell,
                classification='PROTECTED' if protected else ('REMOVE_CANDIDATE' if empty else 'KEEP'),
                role=('execution/results' if protected else 'explanation'),
                loads=names[i][0], defines=names[i][1], downstream_cell_indices=consumers,
                dependency_limit='AST name flow only; magics/dynamic imports/Drive paths require manual inspection',
                source_sha256=sha(encoded(cell.get('source'))),
                outputs_sha256=sha(encoded(cell.get('outputs', []))),
                execution_count=cell.get('execution_count'), metadata=cell.get('metadata', {})))
        books.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(raw), cells=cells,
                          metadata=nb.get('metadata'), nbformat=nb['nbformat'], nbformat_minor=nb['nbformat_minor']))
    save(AUDIT / 'snapshot_manifest.json', books)
    # Byte identities of runtime/config/source/docs before presentation work; no dataset reads.
    files = {}
    for folder in ('src', 'app', 'configs', 'scripts', 'tests', 'docs', 'reports/figures'):
        for p in (ROOT / folder).rglob('*'):
            if p.is_file() and not {'__pycache__', '.pytest_cache'} & set(p.parts):
                files[p.relative_to(ROOT).as_posix()] = sha(p.read_bytes())
    save(AUDIT / 'initial_source_sha256.json', files)
    print(json.dumps({'notebooks': len(books), 'cells': sum(len(b['cells']) for b in books)}))


def verify():
    results = []
    for book in json.loads((AUDIT / 'snapshot_manifest.json').read_text(encoding='utf-8')):
        old = json.loads((AUDIT / 'snapshots' / Path(book['path']).name).read_bytes())
        current = json.loads((ROOT / book['path']).read_bytes())
        assert sha((AUDIT / 'snapshots' / Path(book['path']).name).read_bytes()) == book['sha256']
        # New explanatory Markdown may surround original cells; no original cell can change.
        original_ids = [c.get('id') for c in old['cells']]
        retained = [c for c in current['cells'] if c.get('id') in original_ids]
        assert retained == old['cells'], book['path']
        assert {k: v for k, v in current.items() if k != 'cells'} == {k: v for k, v in old.items() if k != 'cells'}
        assert all(c['cell_type'] == 'markdown' for c in current['cells'] if c.get('id') not in original_ids)
        per_cell = []
        for before, after in zip(old['cells'], retained):
            per_cell.append(dict(cell_id=before.get('id'),
                source_sha256=sha(encoded(after.get('source'))),
                outputs_sha256=sha(encoded(after.get('outputs', []))),
                execution_count_sha256=sha(encoded(after.get('execution_count'))),
                metadata_sha256=sha(encoded(after.get('metadata', {}))),
                unchanged=before == after))
        results.append(dict(path=book['path'], original_cells=len(old['cells']),
                            added_markdown=len(current['cells'])-len(old['cells']), status='PASS',
                            current_sha256=sha((ROOT / book['path']).read_bytes()), cells=per_cell))
    save(AUDIT / 'preservation_verification.json', results)
    print(json.dumps([{k:v for k,v in r.items() if k != 'cells'} for r in results], indent=2))


def presentation():
    from scripts.presentation_figures import prepare
    data = storage_root()
    tables, _, _ = prepare(data)

    def table(rows, key='model'):
        metrics = ['accuracy', 'macro_precision', 'macro_recall', 'macro_f1', 'weighted_f1']
        return '| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 | Weighted F1 |\n|---|---:|---:|---:|---:|---:|\n' + '\n'.join(
            '| ' + r[key] + ' | ' + ' | '.join(f'{float(r[k]):.8f}' for k in metrics) + ' |' for r in rows)

    provenance = ('\n\nNguồn: saved CSV đối chiếu packets/manifests đã pin SHA; [figure_manifest.json](../reports/academic_review_20261111/figure_manifest.json) '
                  'ghi checksum đầy đủ. **Validation 28.120 dòng, cố định 587 labels, zero_division=0**; không trộn final test. '
                  'Chỉ đọc Markdown/output để trình bày; không Run All.\n')
    base_image = f'../../{data.name}/reports/figures/phase3_baseline-v1-f8a5bfdb7b4c12cd_validation_performance.png'
    tuning_image = f'../../{data.name}/reports/tuning/tuning-v1-9c4dd013abbba14a/baseline_vs_tuned.png'
    ens_image = f'../../{data.name}/reports/runs/phase4-20261028T091711786379Z-c1c66643/figures/macro_f1_comparison.png'
    baseline = ('## Experiment 1 — Baseline: đọc kết quả đã lưu\n\n'
        '**Câu hỏi:** năm họ tuyến tính/margin/cây/láng giềng/Bernoulli khác nhau thế nào trên dữ liệu nhị phân? '
        'Giả thuyết so sánh thực nghiệm, không khẳng định ưu thế trước khi đo. Train 131.248 dòng, group-disjoint với validation; '
        'VarianceThreshold(0) fit train → 318/375 cột → CSR → classifier. Không fit trên validation. '
        'Cấu hình gốc: [phase3.json](../configs/phase3.json). LR C1/saga, SVC C1, RF depth24/100 cây, KNN k5/Manhattan/distance, NB alpha1.\n\n'
        + table(tables['baseline']) + '\n\n'
        f'![Baseline: Accuracy, Macro F1, Weighted F1](<{base_image}>)\n\n'
        'Hình đã có được giữ nguyên; giá trị chính xác và nguồn nằm trong bảng/caption này. LR là best baseline single theo Macro F1. '
        'Thời gian fit/predict cả validation và RSS đã lưu trong CSV; không diễn giải như batch1 latency.\n')
    tuning_rows = tables['tuning']
    tuning = ('## Experiment 3 — Hyperparameter Tuning: xem kết quả không chạy search\n\n'
        'Train-only StratifiedGroupKFold3, shuffle/seed42; 15 candidates × 3 folds. '
        'Scorer đủ587 labels/zero_division0; VT fit riêng train fold. Train coverage587/587/587, holdout586/586/587. '
        'Selection bằng CV trước đánh giá validation. Giữ search-space/selected-config trong manifest pin; '
        'LR C2, SVC C2, RF depth32, KNN k7, NB alpha0.5. Không phải neural-network fine-tuning.\n\n'
        '| Model | Baseline Macro F1 | Tuned Macro F1 | Delta | Diễn giải |\n|---|---:|---:|---:|---|\n' + '\n'.join(
        f"| {r['model']} | {float(r['baseline_macro_f1']):.8f} | {float(r['tuned_macro_f1']):.8f} | {float(r['delta_macro_f1']):+.8f} | {'Tăng' if float(r['delta_macro_f1']) > 0 else 'Giảm/không đổi'} |" for r in tuning_rows)
        + f'\n\n![Macro F1 trước/sau tuning](<{tuning_image}>)\n\n'
        'Cả5 tăng trong search space đã thử, không có model giảm Macro F1 validation. NB tăng nhiều nhất nhưng LR vẫn tốt nhất trong single models. '
        '45 attempts hoàn tất, không convergence warning; fold predictions không persist nên không tuyên bố tái tính độc lập fold scores. '
        'State/resume khác training: chỉ xem saved manifest/report không chạy `run_tuning`. '
        '**Đính chính gate:** tài liệu gốc mô tả mặc định OFF; cell `tuning-switch` đang giữ True từ owner execution. '
        'Không sửa source đã chạy hoặc gán output cũ cho code mới. Đọc phần Markdown này để xem kết quả, không chạy cell tuning.\n')
    base_ensemble = ('## Experiment 2 — Baseline Ensemble: đối chứng có kiểm soát\n\n'
        'Giả thuyết: kết hợp sai số có thể tăng Macro F1; không mặc định majority tốt hơn LR. '
        'Ba hard combos LR+SVC+{KNN,NB,RF}; hai soft LR+{KNN+NB,NB+RF}. '
        'Hard uniform1vote/member, tie ưu tiên LR→SVC→KNN→NB→RF trong members; '
        'soft mean predict_proba của LR/KNN/NB/RF, tie theo LR probability rồi label Unicode. SVC không soft/calibration.\n\n'
        + table(tables['baseline_ensemble'], 'combination') + f'\n\n![Baseline ensemble](<{ens_image}>)\n\n'
        'Hard LR+SVC+KNN là best baseline ensemble nhưng F1 thấp hơn LR baseline: cứu152/làm sai170 soLR. '
        'Model errors tương quan; voting không bảo đảm cải thiện.\n')
    tuned_ensemble = ('## Experiment 4 — Tuned Ensemble: kết quả và lựa chọn ứng dụng\n\n'
        'Cùng3hard/2soft combos, uniform weights và tie policy đã khóa, dùng fitted tuned checkpoints của experiment '
        '`tuning-v1-9c4dd013abbba14a`; không fit/calibrate hoặc tìm tổ hợp mới. '
        'Giả thuyết kiểm tra: tuned members có thay đổi lợi ích voting so baseline không?\n\n'
        + table(tables['tuned_ensemble'], 'combination') + '\n\n'
        '![Tuned ensemble](../reports/academic_review_20261111/experiment4_tuned_ensembles.png)\n\n'
        'Hard tuned LR+SVC+KNN đạt best observed validation Macro F1; cứu173/làm sai194 soLR tuned (net−21 về số hàng đúng). '
        '115 lớp tăng F1,128 giảm,344 không đổi;93,82% net Macro F1 gain đến từ lớp support≤5. Không suy ưu thế thống kê từ chênh lệch nhỏ.\n\n'
        '### Overall Model Selection — chỉ validation\n\n'
        '![Overall selection](../reports/academic_review_20261111/overall_validation_selection.png)\n\n')
    selected = [tables['baseline_ensemble'][0], max((r for r in tables['baseline_ensemble'] if r['mode'] != 'single'), key=lambda r: float(r['macro_f1'])),
                next(r for r in tables['tuned_ensemble'] if r['combination'] == 'single_logistic_regression'),
                max((r for r in tables['tuned_ensemble'] if r['mode'] != 'single'), key=lambda r: float(r['macro_f1']))]
    tuned_ensemble += '| Ứng viên | Accuracy | Macro F1 | Weighted F1 | Top3 / triển khai |\n|---|---:|---:|---:|---|\n'
    labels = ['LR baseline', 'Best baseline hard', 'LR tuned C=2', 'Best tuned hard']
    for label, row in zip(labels, selected):
        tuned_ensemble += f"| {label} | {float(row['accuracy']):.8f} | {float(row['macro_f1']):.8f} | {float(row['weighted_f1']):.8f} | {'predict_proba chưa calibration' if row['mode']=='single' else 'Hard label/votes; không có class probability Top3'} |\n"
    tuned_ensemble += ('\n**LR tuned C=2 là default ứng dụng được duyệt trước test**, không phải best Macro F1 validation. '
        'Benchmark Colab cùng input: LR Top3 p50/p95=12,853849/15,073229ms; hard Top1=48,704676/88,124780ms; '
        'file pipelines1.438.563 vs3.554.419bytes. Load0,036802s vs0,111631s; warm-up đo riêng trong ML_GAPS. '
        'Đây là chi phí pipeline đã đo, không là latency REST/LLM hoặc SLA. '
        'Paired group bootstrap2000/seed20261029: delta hard−LR0,00336269,95%CI[−0,00003807;0,00622337] chứa0. '
        'LR chọn vì Top3 thật, đơn giản và chi phí; synthetic data, rare classes, identical vectors nhiều nhãn và uncalibrated scores giới hạn diễn giải. '
        'Final test là đánh giá held-out riêng trong notebook06, không chọn lại model.\n')
    overview = {
        '03_model_training.ipynb': '## Hướng dẫn trình bày hiện hành — 2026-11-11\n\nExperiment1=baseline; Experiment3=tuning. Kết quả Colab đã có evidence pin; các dòng NOT YET VERIFIED cũ là lịch sử lúc tạo. **Không Run All**. Cell tuning-switch hiện True do owner bật từ lần chạy trước; source/output giữ nguyên. Xem hai phần tổng hợp Markdown cuối notebook để xem kết quả không fit/predict. Hướng dẫn runtime hiện hành: [deployment](../docs/DEPLOYMENT_GUIDE.md).',
        '04_ensemble.ipynb': '## Hướng dẫn trình bày hiện hành — 2026-11-11\n\nExperiment2=baseline ensemble; Experiment4=tuned ensemble. Output lịch sử chưa verified lúc tạo đã được bổ sung bằng packets pin SHA. Switch tuned ensemble hiện False; **không cần bật switch để xem bảng/hình cuối notebook**. Không Run All: các cell cũ có thể tạo run mới/predict probabilities. LR tuned C2 đã được chọn trước test; PENDING/default baseline trong output cũ là lịch sử.',
        '05_structured_inference_check.ipynb': '## Đọc notebook05 trước khi chạy\n\nĐây là kiểm tra kỹ thuật cầu nối training→ứng dụng: reload5baseline checkpoints Phase3 (không phải5tuned), kiểm checksum/env/schema375/class order587 và input nhị phân đúng thứ tự. Dùng4ca validation chọn có chủ đích (LR đúng/sai, bất đồng, support thấp) và5vector giả lập thêm/bớt triệu chứng; không dùng làm metric tổng thể.\n\nLR/RF/KNN/NB Top3 từ predict_proba thật, SVC chỉ label/decision score. Bảng đúng/sai có nhãn thật; bảng giả lập không ground truth. Load+integrity/warm-up tách thời gian predict7lần, không phải cam kết API latency. Evidence structured-inference-v1 đã được Colab chạy, technical_pass=True; checksum nằm trong figure_manifest. Không fit/train/tune/test.\n\nKhác FastAPI: notebook là công cụ đối chứng5baseline; API hiện chỉ serve approved LR tunedC2, load1lần startup và áp quality gate/session qua chat. Giữ notebook như bằng chứng mapping/inference, không thay thế API. Output nhắc Phase5A chưa làm là trạng thái lịch sử. **Không chạy lại để trình bày; đọc outputs có sẵn.** Tất cả14cell gốc giữ nguyên, không có đề xuất xóa cell khoa học.',
    }
    extras = {'03_model_training.ipynb': baseline + provenance + tuning + provenance,
              '04_ensemble.ipynb': base_ensemble + provenance + tuned_ensemble + provenance}
    for name, intro in overview.items():
        path = ROOT / 'notebooks' / name
        raw = path.read_bytes()
        original = json.loads((AUDIT / 'snapshots' / name).read_bytes())
        assert json.loads(raw) == original, 'Only apply once to snapshotted notebook'
        def md(suffix, text):
            return dict(cell_type='markdown', id='academic-20261111-'+suffix, metadata={}, source=text.splitlines(keepends=True))
        current = dict(original)
        current['cells'] = [md('overview', intro)] + original['cells']
        if name in extras:
            current['cells'].append(md('results', extras[name]))
        try:
            path.write_text(json.dumps(current, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            ids = {c.get('id') for c in original['cells']}
            assert [c for c in json.loads(path.read_bytes())['cells'] if c.get('id') in ids] == original['cells']
        except Exception:
            path.write_bytes(raw)
            raise
    verify()
    # Reuse existing consolidated ML page rather than authoring another Markdown report.
    doc = ROOT / 'docs/ML_EXPERIMENTS.md'
    text = '\n\n## Academic presentation review — 2026-11-11\n\n' + baseline + provenance + base_ensemble + provenance + tuning + provenance + tuned_ensemble + provenance
    # notebook and docs are sibling directories: their relative report/config/data paths agree.
    doc.write_text(doc.read_text(encoding='utf-8') + text, encoding='utf-8')


def landscape():
    import os
    import re
    initial = json.loads((AUDIT / 'initial_source_sha256.json').read_bytes())
    frozen_path = ROOT.parent / 'handover-final-20261105-release/frozen_members.json'
    frozen = json.loads(frozen_path.read_bytes())['code']
    before = {**initial, **{b['path']: b['sha256'] for b in json.loads((AUDIT / 'snapshot_manifest.json').read_bytes())}}
    differences = [dict(path=n, release_sha256=v['sha256'], initial_sha256=before.get(n), status='MATCH' if before.get(n)==v['sha256'] else 'REVIEW')
                   for n,v in frozen.items() if n in before]
    save(AUDIT / 'release_comparison.json', dict(frozen_release=str(frozen_path), files=differences,
                                               limitation='Pre-edit comparison for inventoried source/config/docs/notebooks; no archive rewritten'))
    books = json.loads((AUDIT / 'snapshot_manifest.json').read_bytes())
    candidates = []
    for book in books:
        for c in book['cells']:
            text = source(c['cell'])
            if not text.strip() or (book['path'].endswith('03_model_training.ipynb') and c['index'] >= 17) or (book['path'].endswith('06_final_model_evaluation.ipynb') and c['index']>=15) or (book['path'].endswith('colab_smoke_test.ipynb') and c['index'] in (3,10)):
                candidates.append(dict(notebook=book['path'], cell_id=c['cell_id'], original_index=c['index'],
                    classification='REMOVE_CANDIDATE' if c['index'] in (17,15,16) or not text.strip() else 'MOVE_CANDIDATE',
                    reason='Historical diagnostic/audit supplement; not required for main presentation. May carry provenance/output.',
                    defines=c['defines'], downstream=c['downstream_cell_indices'], outputs=len(c['cell'].get('outputs',[])),
                    risk='Loss of execution evidence or variables; approval required. Preserved unchanged.', action='KEEP_PENDING_OWNER_REVIEW'))
    save(AUDIT / 'cell_candidates.json', candidates)
    docs = sorted(p for p in ROOT.rglob('*.md') if not set(p.relative_to(ROOT).parts) & {
        '.venv-web', '.venv', 'venv', '__pycache__', '.pytest_cache', 'dist', '.git', 'node_modules', '.cache'})
    texts = {p: p.read_text(encoding='utf-8') for p in docs}
    inventory = []
    for path, text in texts.items():
        classification = 'KEEP'
        if 'archive' in path.parts:
            classification = 'ARCHIVE_CANDIDATE'
        elif path.name in {'MODEL_SELECTION_RATIONALE.md','PROJECT_DEVELOPMENT_LOG.md','LOCAL_PREDICTION_API.md','phase3_colab.md','phase4_ensemble.md','portable_runtime.md','portability_validation.md'}:
            classification = 'MERGE_CANDIDATE'
        refs = [p.relative_to(ROOT).as_posix() for p,t in texts.items() if p != path and path.name in t]
        inventory.append(dict(path=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size, sha256=sha(path.read_bytes()), classification=classification,
                              inbound_text_references=refs, action='KEEP; no deletion/merge without owner approval',
                              reason='Historical evidence' if 'archive' in path.parts else 'Primary guide or compatibility redirect; links must survive consolidation'))
    save(AUDIT/'documentation_inventory.json', inventory)
    # Inventory exclusions/candidates without removing files; do not read secrets, CSV datasets or model payloads.
    candidates = []
    references = {n:(ROOT/n).read_text(encoding='utf-8-sig', errors='replace') for n in initial if Path(n).suffix in {'.py','.json','.md','.ps1'}}
    for parent, dirs, files in os.walk(ROOT):
        base = Path(parent)
        for name in list(dirs):
            if name in {'.venv-web','.venv','__pycache__','.pytest_cache','.git','dist'}:
                p = base/name
                dirs.remove(name)
                members = [f for f in p.rglob('*') if f.is_file()]
                # SHA inventory per member is recorded only for non-environment caches/archives.
                items = [dict(path=f.relative_to(ROOT).as_posix(),bytes=f.stat().st_size,
                              sha256=sha(f.read_bytes()) if name in {'__pycache__','.pytest_cache','dist'} and f.suffix.lower() not in {'.gz','.csv','.joblib','.npz','.zip','.pyz'} else 'NOT_READ') for f in members]
                candidates.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=sum(f['bytes'] for f in items),members=items,
                    action='KEEP_RUNTIME_ENV' if name.startswith('.venv') else 'REVIEW_NO_DELETE',
                    consumers=[n for n,t in references.items() if p.relative_to(ROOT).as_posix() in t][:30],
                    reason='Installed runtime or generated staging/cache; may support current deployment/rollback',
                    rollback='No operation performed; snapshot/export and dependency review required before future cleanup'))
    save(AUDIT/'cleanup_candidates.json', candidates)
    print(json.dumps({'release_compared':len(differences),'pre_edit_differences':sum(r['status']!='MATCH' for r in differences),
                      'cell_candidates':len(json.loads((AUDIT/'cell_candidates.json').read_bytes())), 'documents':len(inventory), 'cleanup_groups':len(candidates)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['inventory', 'verify', 'presentation', 'landscape'])
    args = parser.parse_args()
    {'inventory': inventory, 'verify': verify, 'presentation': presentation, 'landscape': landscape}[args.action]()
