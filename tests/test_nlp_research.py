"""Synthetic mechanics only; never clinical/semantic model qualification."""
import hashlib
import json
from pathlib import Path
import socket

import numpy as np
import pytest

from scripts.nlp_symptom_research import (ROOT, Catalog, SemanticCandidates, engine,
    load_cases, metrics, rule_extract, verify_embedding_snapshot)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*a,**k):raise AssertionError('Research must not access network')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)


def test_protocol_reserved_identity_and_disjointness():
    p=json.loads((ROOT/'configs/nlp_research.json').read_text(encoding='utf-8'))
    splits=load_cases();path=ROOT/p['reserved']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==p['reserved_sha256']
    assert len(splits['development'])==86 and len(splits['reserved_synthetic_evaluation'])==p['reserved_rows']
    assert p['production_activation'] is False
    assert all(not c['used_for_alias_development'] and not c['used_for_threshold_selection'] for c in splits['reserved_synthetic_evaluation'])


def test_inventory_order_status_and_production_unchanged():
    packet=json.loads((ROOT/'reports/nlp_research_v1/coverage_inventory.json').read_text(encoding='utf-8'))
    assert [r['canonical_feature'] for r in packet['features']]==list(Catalog.load(ROOT).features)
    assert packet['summary']['description_coverage']==375
    assert packet['summary']['production_features']==135
    assert all(r['display_vi'] and r['description_vi'] and r['clinical_review']=='NOT_CLINICALLY_VALIDATED' for r in packet['features'])
    assert all(r['activation_blockers'] for r in packet['features'] if not r['production_active'])
    assert hashlib.sha256((ROOT/'configs/synonyms.json').read_bytes()).hexdigest()==packet['summary']['synonyms_sha256_before']==packet['summary']['synonyms_sha256_after']


@pytest.mark.parametrize('text,expected',[
    ('Tôi bị buồn nôn.',{'nausea':'present'}),
    ('Tôi không buồn nôn.',{'nausea':'denied'}),
    ('Tôi chưa chắc có buồn nôn.',{'nausea':'uncertain'}),
    ('Mẹ tôi bị buồn nôn.',{}),
    ('Giả sử tôi bị buồn nôn thì sao?',{}),
    ('Tôi đọc câu "buồn nôn" trong sách.',{}),
    ('Nhân vật trong truyện bị buồn nôn.',{}),
    ('Trong truyện, nhân vật đang ho liên tục.',{}),
    ('Nhan vat trong truyen bi buon non.',{}),
    ('Tôi bị buồn nôoon.',{}),
])
def test_actual_production_rule_interface(text,expected):
    assert rule_extract(text)['states']==expected


def test_fiction_evidence_rejection_is_sentence_scoped():
    from src.agent.extraction import Turn,evidence_context,ExtractionError
    text='Nhân vật trong truyện bị ho. Hiện tại tôi bị buồn nôn.'
    turn=Turn('u1','user',text,'self')
    start=text.index('buồn nôn')
    evidence_context(turn,dict(turn_id='u1',start=start,end=start+8,text='buồn nôn'),'self','present')
    start=text.index('ho')
    with pytest.raises(ExtractionError,match='fictional_subject_evidence'):
        evidence_context(turn,dict(turn_id='u1',start=start,end=start+2,text='ho'),'self','present')


def fake_matcher():
    records=json.loads((ROOT/'reports/nlp_research_v1/coverage_inventory.json').read_text(encoding='utf-8'))['features']
    # Deliberate fake embeddings for deterministic unit mechanics, never reported as benchmark semantic scores.
    def encode(texts):return np.asarray([[1.,float(i%7+1),2.] for i,_ in enumerate(texts)])
    return SemanticCandidates(records,encode)


@pytest.mark.parametrize('text',['Mẹ tôi bị buồn nôn.','Giả sử tôi bị buồn nôn.','Nhân vật trong truyện bị buồn nôn.','Tôi đọc "buồn nôn" trong sách.'])
def test_semantic_cannot_bypass_subject_fiction_or_hypothesis(text):
    assert fake_matcher().retrieve(text,Catalog.load(ROOT))==[]


@pytest.mark.parametrize('text,state',[('Tôi không ho.','denied'),('Tôi chưa chắc bị ho.','uncertain'),('Tôi bị ho.','present')])
def test_semantic_candidates_are_unconfirmed_and_assertion_scoped(text,state):
    result=fake_matcher().retrieve(text,Catalog.load(ROOT))
    assert result and all(r['state']==state and r['requires_confirmation'] for r in result)
    assert all(len(r['candidates'])==3 for r in result)
    assert all(text[r['evidence']['start']:r['evidence']['end']]==r['evidence']['text'] for r in result)


def test_partial_labels_are_not_exhaustive_negatives():
    cases=[dict(kind='affirmed',expected_states={'cough':'present'}),dict(kind='partial',expected_states=None,forbidden_features=['fever'])]
    rows=[dict(states={'cough':'present'},latency_ms=1.,confirmation_required=False),
          dict(states={'fever':'present'},latency_ms=2.,confirmation_required=True)]
    r=metrics(cases,rows)
    assert r['micro_f1']==1 and r['partial_label_cases']==1 and r['exact_denominator']==1
    assert r['forbidden_feature_violations']==1 and r['confirmation_rate']==.5


def test_embedding_snapshot_mismatch_fails_before_load(tmp_path):
    (tmp_path/'research_snapshot.json').write_text(json.dumps(dict(model_id='wrong',revision='wrong',files={})))
    with pytest.raises(ValueError,match='identity'):verify_embedding_snapshot(tmp_path)


def test_semantic_catalog_rejects_unknown_or_reordered_feature():
    records=json.loads((ROOT/'reports/nlp_research_v1/context_after_fix.json').read_text(encoding='utf-8'))['features']
    records[0]['canonical_feature']='invented feature'
    with pytest.raises(ValueError,match='schema_order'):
        SemanticCandidates(records,lambda _:None)


def test_notebook07_valid_json_and_safe_gates():
    nb=json.loads((ROOT/'notebooks/07_vietnamese_symptom_extraction.ipynb').read_text(encoding='utf-8'))
    assert nb['nbformat']==4
    assert len({c['id'] for c in nb['cells']})==len(nb['cells'])
    code='\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code')
    assert 'RUN_RESEARCH = False' in code and 'RUN_SEMANTIC = False' in code
    assert '.fit(' not in code and 'trust_remote_code=True' not in code
    for c in nb['cells']:
        if c['cell_type']=='code':compile(''.join(c['source']),'notebook07','exec')


def test_no_production_module_imports_research():
    for directory in ('src','app'):
        for p in (ROOT/directory).rglob('*.py'):
            assert 'nlp_symptom_research' not in p.read_text(encoding='utf-8')
