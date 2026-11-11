"""Pinned-download/cache mechanics with synthetic bytes; no network or model load."""
import json
from pathlib import Path

import pytest

from scripts.nlp_symptom_research import (prepare_embedding, verify_embedding_snapshot,
    MODEL_ID, MODEL_REVISION, candidate_metrics)
from scripts.plot_nlp_research import render_run


def test_embedding_preparation_pins_revision_and_reuses_verified_cache(tmp_path):
    cache=tmp_path/'download-cache';cache.mkdir();calls=[]
    def fetch(**kw):
        assert kw['repo_id']==MODEL_ID and kw['revision']==MODEL_REVISION
        calls.append(kw['filename']);p=cache/kw['filename'];p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(('synthetic unit-test bytes '+kw['filename']).encode());return p
    folder=prepare_embedding(tmp_path,fetch=fetch)
    manifest=verify_embedding_snapshot(folder)
    assert len(calls)==len(manifest['files'])==11
    assert folder==tmp_path/'artifacts/embeddings/multilingual-minilm-l12-v2'/MODEL_REVISION
    assert prepare_embedding(tmp_path,fetch=lambda **k:pytest.fail('No repeated download'))==folder
    (folder/'model.safetensors').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='checksum'):prepare_embedding(tmp_path,fetch=fetch)


def test_partial_embedding_download_never_appears_ready(tmp_path):
    def fetch(**kw):raise ConnectionError('synthetic download failure')
    with pytest.raises(ConnectionError):prepare_embedding(tmp_path,fetch=fetch)
    assert not (tmp_path/'artifacts/embeddings/multilingual-minilm-l12-v2'/MODEL_REVISION).exists()


def test_candidate_metrics_do_not_fake_confirmed_symptoms():
    cases=[dict(expected_states={'cough':'denied'}),dict(expected_states=None)]
    rows=[dict(states={},suggestions=[dict(state='denied',candidates=[dict(feature='fever'),dict(feature='cough')])]),dict(states={})]
    result=candidate_metrics(cases,rows)
    assert result['recall_at_1']==0 and result['recall_at_3']==1 and result['precision_at_3']==.5
    assert rows[0]['states']=={}


def test_run_figures_depend_on_this_runs_metrics_only(tmp_path):
    m=dict(precision=.5,recall=.6,micro_f1=.55,latency_p50_ms=1,latency_p95_ms=2)
    result=dict(results={'fixture_synthetic_split':{'rule_based':dict(metrics=m),
        'semantic':dict(metrics={**m,'micro_f1':0},candidate_metrics=dict(recall_at_1=.3,recall_at_3=.7,precision_at_3=.2))}})
    (tmp_path/'benchmark.json').write_text(json.dumps(result))
    manifest=render_run(tmp_path)
    assert len(manifest['figures'])==3
    assert all((tmp_path/name).is_file() for name in manifest['figures'])
    assert not (tmp_path/'context_after_fix.json').exists()  # No old report required.
