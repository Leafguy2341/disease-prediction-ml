"""Normal project-file viewing and automatic Colab source preparation, no live network."""
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
    monkeypatch.setenv('NLP_PROJECT_ROOT',str(ROOT))
    original=builtins.__import__
    def imports(name,*a,**k):
        if name.startswith(('src.','app.','scripts.nlp_symptom_research','sentence_transformers')):
            raise AssertionError('Viewer must not execute project/research imports: '+name)
        return original(name,*a,**k)
    monkeypatch.setattr(builtins,'__import__',imports)
    return json.loads((ROOT/'notebooks/07_vietnamese_symptom_extraction.ipynb').read_text(encoding='utf-8'))


def test_all_viewer_cells_read_normal_project_files(viewer,monkeypatch):
    import IPython.display
    shown=[]
    monkeypatch.setattr(IPython.display,'display',lambda *args,**kw:shown.extend(args))
    namespace={'RUN_RESEARCH':False,'RUN_SEMANTIC':False}
    for c in viewer['cells']:
        if c['cell_type']=='code' and c['id']!='nlp07-controls':exec(compile(''.join(c['source']),'07-viewer','exec'),namespace)
    assert namespace['ROOT']==ROOT
    assert namespace['RUN_RESEARCH'] is namespace['RUN_SEMANTIC'] is False
    assert len(namespace['after']['features'])==375
    assert namespace['saved']['semantic_environment']['status']=='NOT RUN'
    images=[v for v in shown if isinstance(v,IPython.display.Image)]
    assert len(images)==4 and all(v.data.startswith(b'\x89PNG') for v in images)
    assert namespace['saved']['results']['reserved_synthetic_evaluation']['rule_based']['metrics']['tp']==22


def test_snapshot_matches_reviewed_report_sources(viewer):
    namespace={'RUN_RESEARCH':False,'RUN_SEMANTIC':False}
    setup=next(c for c in viewer['cells'] if c['id']=='nlp07-01')
    exec(''.join(setup['source']),namespace)
    for name,expected in namespace['reference_manifest']['files'].items():
        assert hashlib.sha256(namespace['snapshot_bytes'](name)).hexdigest()==expected
    namespace['reference_manifest']['files']['benchmark.json']='0'*64
    with pytest.raises(ValueError,match='checksum'):namespace['snapshot_bytes']('benchmark.json')


def test_research_opt_in_without_source_has_clear_error(viewer,monkeypatch):
    monkeypatch.delenv('NLP_PROJECT_ROOT',raising=False)
    namespace={'RUN_RESEARCH':True,'RUN_SEMANTIC':False}
    with pytest.raises(RuntimeError,match='project'):
        exec(''.join(next(c for c in viewer['cells'] if c['id']=='nlp07-01')['source']),namespace)


def test_colab_source_preparation_is_automatic(viewer,monkeypatch,tmp_path):
    import subprocess,sys,shutil
    monkeypatch.delenv('NLP_PROJECT_ROOT',raising=False)
    target=tmp_path/'colab-source';calls=[]
    original_is_dir=Path.is_dir
    monkeypatch.setattr(Path,'is_dir',lambda p:True if p.as_posix()=='/content' else original_is_dir(p))
    monkeypatch.setattr(sys,'platform','linux')
    def run(args,**kwargs):
        calls.append(args)
        assert args[:2]==['git','clone']
        target.mkdir();(target/'.git').mkdir()
        for name in ('configs/nlp_research.json','scripts/nlp_symptom_research.py','scripts/plot_nlp_research.py',
                     'requirements-nlp-research.txt','data/evaluation/vietnamese_nlp_reserved_v1.jsonl',
                     'artifacts/metadata/phase2/feature_schema.json','artifacts/metadata/phase2/label_mapping.json'):
            p=target/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
        shutil.copytree(ROOT/'reports/nlp_research_v1',target/'reports/nlp_research_v1')
        return type('Completed',(),{'returncode':0})()
    monkeypatch.setattr(subprocess,'run',run)
    monkeypatch.setattr(subprocess,'check_output',lambda *a,**k:'fixture-commit\n')
    source=''.join(next(c for c in viewer['cells'] if c['id']=='nlp07-01')['source'])
    source=source.replace("Path('/content/disease-prediction-ml-nlp')",'Path('+repr(str(target))+')')
    namespace={'RUN_RESEARCH':True,'RUN_SEMANTIC':False}
    exec(source,namespace)
    assert namespace['ROOT']==target and len(calls)==1


def test_notebook_tables_and_images_use_current_run():
    nb=json.loads((ROOT/'notebooks/07_vietnamese_symptom_extraction.ipynb').read_text(encoding='utf-8'))
    code={c['id']:''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code'}
    assert 'evaluated = research if research is not None else saved' in code['nlp07-10']
    assert "RESULT_FOLDER / 'benchmark.json'" in code['nlp07-07']
    assert "RESULT_FOLDER / 'run_figures.json'" in code['nlp07-12']
