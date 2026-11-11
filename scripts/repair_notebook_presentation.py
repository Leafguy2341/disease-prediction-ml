"""Repair presentation Markdown and embed byte-identical PNG attachments only."""
import base64
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/academic_review_20261111/presentation_repair'
PATTERN = re.compile(r'!\[([^\]]*)\]\((?:<([^>]+)>|([^\s)]+))\)')
SEARCH = '''### Search space đã chạy (không mở rộng)

| Họ | Ba candidates; phần còn lại giữ baseline | Selected |
|---|---|---|
| LR | C=1/0.5/2 | C=2 |
| LinearSVC | C=1/0.5/2 | C=2 |
| RF | max_depth=24/16/32 | 32 |
| KNN | k=5/3/7 | 7 |
| BernoulliNB | alpha=1/0.5/2 | 0.5 |

Nguồn đầy đủ candidate parameters/fold scores: pinned `artifacts/metadata/model_analysis/colab_supplement.json`; phase3 config không bị sửa. Tuning train-only, validation không dùng search. Giới hạn: 3 candidates/family, không là exhaustive optimum; time budget kiểm giữa folds, warnings/resume lưu metadata. Không cần bật gate để xem bảng này.
'''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plans = []
    for name in ('03_model_training.ipynb', '04_ensemble.ipynb'):
        path = ROOT / 'notebooks' / name
        raw = path.read_bytes()
        snapshot = OUT / name
        if snapshot.exists():
            assert snapshot.read_bytes() == raw, 'Existing snapshot differs; do not overwrite'
        else:
            with snapshot.open('xb') as stream:
                stream.write(raw)
        nb = json.loads(raw)
        plans.append((path, raw, nb))
    save(OUT / 'before.json', [dict(path=str(p.relative_to(ROOT)), sha256=digest(raw), cells=nb['cells']) for p,raw,nb in plans])
    reports = []
    try:
        for path, raw, original in plans:
            nb = json.loads(raw)
            images = []
            for cell in nb['cells']:
                if cell.get('id') != 'academic-20261111-results':
                    continue
                text = ''.join(cell['source'])
                marker = '### Search space ?? ch?y (kh?ng m? r?ng)'
                if marker in text:
                    prefix, _ = text.split(marker, 1)
                    text = prefix + SEARCH
                def embed(match):
                    alt, target = match.group(1), match.group(2) or match.group(3)
                    source = (path.parent / target).resolve()
                    assert source.is_file(), source
                    payload = source.read_bytes()
                    assert payload.startswith(b'\x89PNG\r\n\x1a\n'), source
                    key = source.name
                    cell.setdefault('attachments', {})[key] = {'image/png': base64.b64encode(payload).decode('ascii')}
                    images.append(dict(source=str(source), attachment=key, sha256=digest(payload), bytes=len(payload)))
                    return f'![{alt}](attachment:{key})'
                text = PATTERN.sub(embed, text)
                assert not re.search(r'\w\?\w|\?\?', text), 'Unexpected corrupted presentation text'
                cell['source'] = text.splitlines(keepends=True)
            assert images, 'No figures found; do not apply twice'
            # Only presentation Markdown source/attachments may differ.
            assert len(nb['cells']) == len(original['cells'])
            for old, new in zip(original['cells'], nb['cells']):
                if old.get('id') == 'academic-20261111-results':
                    assert old['cell_type'] == new['cell_type'] == 'markdown'
                    assert {k:v for k,v in old.items() if k not in {'source','attachments'}} == {k:v for k,v in new.items() if k not in {'source','attachments'}}
                else:
                    assert old == new
            assert {k:v for k,v in original.items() if k != 'cells'} == {k:v for k,v in nb.items() if k != 'cells'}
            path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            loaded = json.loads(path.read_bytes())
            for cell in loaded['cells']:
                if cell.get('id') != 'academic-20261111-results':
                    continue
                for match in PATTERN.finditer(''.join(cell['source'])):
                    target = match.group(2) or match.group(3)
                    assert target.startswith('attachment:')
                    key = target[len('attachment:'):]
                    decoded = base64.b64decode(cell['attachments'][key]['image/png'], validate=True)
                    record = next(i for i in images if i['attachment'] == key)
                    assert digest(decoded) == record['sha256']
            reports.append(dict(notebook=path.name, before_sha256=digest(raw), after_sha256=digest(path.read_bytes()),
                                images=images, code_outputs_counts_metadata_unchanged=True, status='PASS'))
        # The same corrupted paragraph was copied into the consolidated ML page.
        doc = ROOT / 'docs/ML_EXPERIMENTS.md'
        raw = doc.read_bytes()
        text = raw.decode('utf-8')
        marker = '### Search space ?? ch?y (kh?ng m? r?ng)'
        if marker in text:
            (OUT/'ML_EXPERIMENTS.md.before').write_bytes(raw)
            text = text.split(marker, 1)[0] + SEARCH
            doc.write_text(text, encoding='utf-8')
        save(OUT/'verification.json', dict(status='PASS', notebooks=reports,
             notebooks_executed=False, model_calls=0, test_payload_opened=False,
             rendering='Standard notebook Markdown attachments; no external image path dependency; VS Code UI must refresh'))
        print(json.dumps([dict(notebook=r['notebook'], images=len(r['images']), status=r['status']) for r in reports]))
    except BaseException:
        for path, raw, _ in plans:
            path.write_bytes(raw)
        raise


if __name__ == '__main__':
    main()
