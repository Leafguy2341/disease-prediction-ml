"""Render validation presentation only from pinned saved reports; no inference.

Existing baseline, baseline ensemble and tuning figures are reused unchanged.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/academic_review_20261111'
BASE = 'baseline-v1-f8a5bfdb7b4c12cd'
TUNING = 'tuning-v1-9c4dd013abbba14a'
RUN = 'phase4-20261028T091711786379Z-c1c66643'
TUNED = 'tuned-ensemble-20261029T041701354242Z-6c84dbfe'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(data):
    policy = json.loads((ROOT / 'configs/handover_data_requirements.json').read_bytes())
    assert sha((ROOT / 'configs/handover_data_requirements.json').read_bytes()) == '66a2c43728b44aef7f59917079fdcdd9a5297d8f2b43b4ae21a676f5b6a85f65'
    checked = {}

    def read(base, name, expected):
        raw = (base / name).read_bytes()
        digest = expected if isinstance(expected, str) else expected['sha256']
        assert sha(raw) == digest, name
        if isinstance(expected, dict) and 'bytes' in expected:
            assert len(raw) == expected['bytes'], name
        checked[name] = dict(sha256=sha(raw), bytes=len(raw), root='code' if base == ROOT else 'data')
        return raw

    evidence = {n: json.loads(read(ROOT, n, v)) for n, v in policy['evidence_files'].items()}
    manifests = {n: json.loads(read(data, n, v)) for n, v in policy['manifests'].items()}
    p3 = evidence['artifacts/metadata/phase3_audit/colab_evidence.json']
    post = evidence['artifacts/metadata/post_tuning_audit/colab_evidence.json']
    tables = {}
    sources = [
        ('baseline', f'reports/tables/phase3_{BASE}_validation_comparison.csv'),
        ('baseline_ensemble', f'reports/runs/{RUN}/tables/validation_comparison.csv'),
        ('tuning', f'reports/tuning/{TUNING}/baseline_vs_tuned.csv'),
        ('tuned_ensemble', f'reports/runs/{TUNED}/tables/tuned_validation_comparison.csv'),
    ]
    for key, name in sources:
        if key == 'baseline':
            raw = (data / name).read_bytes()
            checked[name] = dict(sha256=sha(raw), bytes=len(raw), root='data',
                                 verification='every metric checked against pinned Phase3 evidence')
        else:
            files = next(m.get('files', m.get('artifact_files', {})) for m in manifests.values()
                         if name in m.get('files', m.get('artifact_files', {})))
            raw = read(data, name, files[name])
        tables[key] = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    metrics = ['accuracy', 'macro_precision', 'macro_recall', 'macro_f1', 'weighted_f1']
    for row in tables['baseline']:
        assert row['status'] == 'completed'
        assert all(abs(float(row[k]) - p3['models'][row['model']]['metrics'][k]) < 1e-12 for k in metrics)
    for row in tables['tuned_ensemble']:
        if row['combination'].startswith('single_'):
            name = row['combination'].removeprefix('single_')
            assert all(abs(float(row[k]) - post['models'][name]['metrics'][k]) < 1e-12 for k in metrics)
    for row in tables['tuning']:
        name = row['model']
        assert abs(float(row['baseline_macro_f1']) - p3['models'][name]['metrics']['macro_f1']) < 1e-12
        assert abs(float(row['tuned_macro_f1']) - post['models'][name]['metrics']['macro_f1']) < 1e-12
    existing = [
        f'reports/figures/phase3_{BASE}_validation_performance.png',
        f'reports/figures/phase3_{BASE}_fit_prediction_time.png',
        f'reports/figures/phase3_{BASE}_difficult_classes.png',
        f'reports/runs/{RUN}/figures/macro_f1_comparison.png',
        f'reports/runs/{RUN}/figures/error_diversity.png',
        f'reports/tuning/{TUNING}/baseline_vs_tuned.png',
    ]
    for name in existing:
        raw = (data / name).read_bytes()
        files = next((m.get('files', m.get('artifact_files', {})) for m in manifests.values()
                      if name in m.get('files', m.get('artifact_files', {}))), {})
        if name in files:
            read(data, name, files[name])
        else:
            checked[name] = dict(sha256=sha(raw), bytes=len(raw), root='data',
                                 verification='current-byte inventory; figure provenance in Phase3 packet; table values independently matched')
    OUT.mkdir(parents=True, exist_ok=True)
    return tables, checked, existing


def render(data):
    tables, checked, existing = prepare(data)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    outputs = {}

    def bars(rows, names, title, filename, footnote):
        fig, ax = plt.subplots(figsize=(12, 7))
        vals = [float(r['macro_f1']) for r in rows]
        rects = ax.barh(names, vals, color=['#2674a6' if 'LR tuned' not in n else '#19734a' for n in names])
        ax.bar_label(rects, labels=[f'{v:.8f}' for v in vals], padding=4, fontsize=9)
        ax.set_xlim(0, 1)
        ax.set_xlabel('Validation Macro F1 — fixed 587 labels; zero_division=0')
        ax.set_title(title)
        ax.invert_yaxis()
        fig.text(.03, .015, footnote, fontsize=8)
        fig.tight_layout(rect=(0, .07, 1, 1))
        target = OUT / filename
        fig.savefig(target, dpi=180)
        plt.close(fig)
        outputs[filename] = dict(sha256=sha(target.read_bytes()), bytes=target.stat().st_size)

    b = tables['baseline_ensemble']
    t = tables['tuned_ensemble']
    best_b = max((r for r in b if r['mode'] != 'single'), key=lambda r: float(r['macro_f1']))
    lr_b = next(r for r in b if r['mode'] == 'single')
    lr_t = next(r for r in t if r['combination'] == 'single_logistic_regression')
    ensembles = [r for r in t if r['mode'] != 'single']
    best_t = max(ensembles, key=lambda r: float(r['macro_f1']))
    bars([lr_t, best_b, *ensembles], ['LR tuned C=2 (best tuned single)', 'Baseline '+best_b['combination'],
         *['Tuned '+r['combination'] for r in ensembles]], 'Experiment 4 — Tuned ensemble comparison (validation)',
         'experiment4_tuned_ensembles.png', f'Sources: {TUNED}/tuned_validation_comparison.csv\nBaseline: {RUN}/validation_comparison.csv; full SHA-256 in figure_manifest.json')
    selected = [lr_b, best_b, lr_t, best_t]
    labels = ['LR baseline (best baseline single)', 'Baseline hard LR+SVC+KNN (best baseline ensemble)',
              'LR tuned C=2 (deployment default)', 'Tuned hard LR+SVC+KNN (best observed validation)']
    bars(selected, labels, 'Overall selection — validation only; not final-test selection', 'overall_validation_selection.png',
         f'Sources: frozen {RUN} and {TUNED} comparison CSVs.\nScores are uncalibrated; bootstrap CI of hard-minus-LR includes zero. See figure_manifest.json.')
    with (OUT / 'overall_validation_selection.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=['candidate', 'accuracy', 'macro_f1', 'weighted_f1', 'pipeline_bytes', 'top3_contract'])
        writer.writeheader()
        for name, row in zip(labels, selected):
            writer.writerow(dict(candidate=name, **{k: row[k] for k in ['accuracy', 'macro_f1', 'weighted_f1', 'pipeline_bytes']},
                                 top3_contract='predict_proba; uncalibrated' if row['mode'] == 'single' else 'N/A; hard label and member votes only'))
    manifest = dict(split='validation', rows=28120, classes=587, zero_division=0,
        sources=checked, reused_figures=existing, new_figures=outputs,
        all_five_tuning_macro_f1_improved=(len(tables['tuning']) == 5 and all(float(r['delta_macro_f1']) > 0 for r in tables['tuning'])),
        inference_calls=0, fit_calls=0, test_payload_opened=False,
        limitation='Saved metric/report verification only; no re-execution of notebooks or model evaluation.')
    (OUT / 'figure_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'reused': len(existing), 'new': len(outputs), 'sources': len(checked)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    render(parser.parse_args().data_root.resolve())
