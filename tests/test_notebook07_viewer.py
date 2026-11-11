"""Execute viewer cells without project source or Colab credentials; no research runs."""
import base64
import builtins
import hashlib
import json
from pathlib import Path
import socket

import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def viewer(tmp_path,monkeypatch):
    def forbidden(*a,**k):raise AssertionError('No outbound requests allowed')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(Path,'cwd',lambda:tmp_path)
    monkeypatch.delenv('NLP_PROJECT_ROOT',raising=False)
    original=builtins.__import__
    def imports(name,*a,**k):
        if name.startswith(('src.','app.','scripts.nlp_symptom_research','sentence_transformers')):
            raise AssertionError('Viewer must not execute project/research imports: '+name)
        return original(name,*a,**k)
    monkeypatch.setattr(builtins,'__import__',imports)
    return json.loads((ROOT/'notebooks/07_vietnamese_symptom_extraction.ipynb').read_text(encoding='utf-8'))


def test_all_viewer_cells_run_with_no_project_or_drive(viewer,monkeypatch):
    import IPython.display
    shown=[]
    monkeypatch.setattr(IPython.display,'display',lambda *args,**kw:shown.extend(args))
    namespace={}
    for c in viewer['cells']:
        if c['cell_type']=='code':exec(compile(''.join(c['source']),'07-viewer','exec'),namespace)
    assert namespace['ROOT'] is None
    assert namespace['RUN_RESEARCH'] is namespace['RUN_SEMANTIC'] is False
    assert len(namespace['after']['features'])==375
    assert namespace['saved']['semantic_environment']['status']=='NOT RUN'
    images=[v for v in shown if isinstance(v,IPython.display.Image)]
    assert len(images)==4 and all(v.data.startswith(b'\x89PNG') for v in images)
    assert namespace['saved']['results']['reserved_synthetic_evaluation']['rule_based']['metrics']['tp']==22


def test_snapshot_matches_reviewed_report_sources(viewer):
    namespace={}
    setup=next(c for c in viewer['cells'] if c['id']=='nlp07-01')
    exec(''.join(setup['source']),namespace)
    for name,asset in namespace['VIEWER_ASSETS'].items():
        path=ROOT/('configs' if name=='nlp_research.json' else 'reports/nlp_research_v1')/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==asset['source_sha256']
        assert hashlib.sha256(base64.b64decode(asset['base64'])).hexdigest()==asset['sha256']
    namespace['VIEWER_ASSETS']['benchmark.json']['base64']=base64.b64encode(b'corrupt').decode()
    with pytest.raises(ValueError,match='checksum'):namespace['snapshot_bytes']('benchmark.json')


def test_research_opt_in_without_source_has_clear_error(viewer):
    namespace={}
    exec(''.join(next(c for c in viewer['cells'] if c['id']=='nlp07-01')['source']),namespace)
    gate=''.join(next(c for c in viewer['cells'] if c['id']=='nlp07-07')['source'])
    with pytest.raises(RuntimeError,match='research source'):
        exec(gate.replace('RUN_RESEARCH = False','RUN_RESEARCH = True'),namespace)
