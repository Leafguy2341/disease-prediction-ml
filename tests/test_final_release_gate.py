"""Final-release checks: no fitting, dataset payloads, notebook execution or LLM."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from src.models import final_evaluation as final
from src.models.ensemble import IntegrityError

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/release_final_gate'


def test_all_historical_failures_have_equivalent_traces_and_classification():
    rows=json.loads((OUT/'regression_triage.json').read_text(encoding='utf-8'))['tests']
    assert len(rows)==len({r['test_id'] for r in rows})==34
    assert sum(r['test_id'].startswith('tests/test_phase2_notebook.py') for r in rows)==13
    assert all(r['reproduced_after_rollback'] and r['normalized_exception_and_frames_equivalent'] for r in rows)
    assert all(r['classification'] in {'BLOCKER','ENVIRONMENT','OPTIONAL'} and r['root_cause'] for r in rows)


def test_notebook_default_gate_is_disabled_without_changing_outputs():
    notebook=json.loads((ROOT/'notebooks/06_final_model_evaluation.ipynb').read_text(encoding='utf-8'))
    gate=''.join(notebook['cells'][8]['source'])
    assert 'RUN_FINAL_LOCKED_TEST = False' in gate and 'OWNER_AUTHORIZATION = ""' in gate
    assert 'AUTHORIZE ONE-TIME LOCKED TEST' not in gate
    # Execute only this isolated disabled gate; never execute notebook setup or evaluation.
    state={}
    exec(compile(gate,'disabled-gate-only','exec'),state)
    assert state['final_result'] is None and state['RUN_FINAL_LOCKED_TEST'] is False
    evidence=json.loads((OUT/'notebook06_gate_freeze.json').read_text(encoding='utf-8'))
    assert evidence['outputs_and_counts_unchanged'] and evidence['changed_cells']==[8]


def test_reenabled_gate_with_empty_authorization_fails_before_preflight(monkeypatch):
    def forbidden(*a,**k):pytest.fail('Must fail before preflight/model/payload access')
    monkeypatch.setattr(final,'preflight',forbidden)
    monkeypatch.setattr(final,'_load_models',forbidden)
    monkeypatch.setattr(final,'load_final_split',forbidden)
    with pytest.raises(IntegrityError,match='Separate explicit owner authorization'):
        final.evaluate(SimpleNamespace(),enabled=True,owner_authorization='')


@pytest.mark.parametrize('status',['COMPLETED','STARTED','PARTIAL'])
def test_existing_evaluation_slot_blocks_before_loading_models_or_test(monkeypatch,status):
    fresh={'execution_status':status}
    monkeypatch.setattr(final,'preflight',lambda session:fresh)
    def forbidden(*a,**k):pytest.fail('Existing evaluation marker must prevent model/payload access')
    monkeypatch.setattr(final,'_load_models',forbidden)
    monkeypatch.setattr(final,'load_final_split',forbidden)
    with pytest.raises(IntegrityError,match='No automatic rerun/resume'):
        final.evaluate(SimpleNamespace(),enabled=True,owner_authorization=final.authorization_text(),prepared=fresh)


def test_real_smoke_evidence_and_unchanged_dictionary():
    from hashlib import sha256
    evidence=json.loads((OUT/'real_runtime_smoke.json').read_text(encoding='utf-8'))
    assert evidence['status']=='PASS' and evidence['checkpoint']=='REAL CHECKPOINT VERIFIED'
    assert evidence['real_tcp_http']['health']==evidence['real_tcp_http']['predict']==200
    assert evidence['reference_comparison']['probabilities']==8*587
    assert evidence['reference_comparison']['labels_and_top3_exact']
    assert not any(evidence['guard_counts'].values()) and not any(evidence['network_and_fit_counts'].values())
    assert sha256((ROOT/'configs/synonyms.json').read_bytes()).hexdigest()==evidence['production_synonyms_sha256']=='036d756fb202612122a31e8a041e60e98a33cc632a7caa41df25ccfe2689d527'


def test_final_candidates_were_not_activated_after_context_failures():
    evidence=json.loads((OUT/'candidate_contexts.json').read_text(encoding='utf-8'))
    s=evidence['summary']
    assert s['cases']==720 and s['failed']==288 and s['affected_features']==127
    assert s['status']=='CANDIDATE_REJECTED' and not s['production_activation_attempted']
    assert s['original_semantic_cases_passed']==86 and s['active_features']==135
    assert s['retained_new_features']==0
