"""Synthetic mechanics; fake embeddings never represent measured retrieval quality."""
import json
import socket
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.nlp_symptom_research import Catalog, ROOT
from scripts.nlp_missed_symptom_analysis import (
    GROUPS, load_challenge, unresolved_proposals, oracle_confirmation, summarize,
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No network in research regression')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


def matcher():
    features = list(Catalog.load(ROOT).features)
    vectors = np.zeros((375, 2)); vectors[:, 1] = 1
    for feature, score in [('fever', 1.), ('shortness of breath', .99), ('nausea', .98)]:
        vectors[features.index(feature)] = [score, 0]
    queries = []
    def encode(texts):
        queries.extend(texts)
        return np.array([[1., 0.] for _ in texts])
    return SimpleNamespace(features=features, vectors=vectors, encode=encode, queries=queries)


def test_all_groups_are_fixed_and_evidence_slices_are_valid():
    cases = load_challenge()
    assert len(cases) == 30
    assert all(sum(c['group'] == g for c in cases) == 6 for g in GROUPS)
    assert all(not c['used_for_threshold_selection'] for c in cases)


def test_hybrid_keeps_partial_sentence_and_removes_only_individual_known_features():
    text = 'Tôi bị sốt, với lại mỗi lần vận động cứ thấy không lấy đủ hơi.'
    start = text.index('sốt')
    base = dict(states={'fever': 'present'}, evidence={'fever': [dict(start=start, end=start+3, text='sốt')]})
    m = matcher()
    proposals, calls, _ = unresolved_proposals(text, m, Catalog.load(ROOT), base)
    assert calls == 1
    assert any('không lấy đủ hơi' in q for q in m.queries)
    assert all('fever' not in [v['feature'] for v in p['candidates']] for p in proposals)
    assert any('shortness of breath' in [v['feature'] for v in p['candidates']] for p in proposals)
    assert base['states'] == {'fever': 'present'}
    assert all(text[p['evidence']['start']:p['evidence']['end']] == p['evidence']['text'] for p in proposals)


def test_fully_matched_alias_needs_no_query_embedding():
    text = 'Tôi bị ho.'; start = text.index('ho')
    base = dict(states={'cough': 'present'}, evidence={'cough':[dict(start=start, end=start+2, text='ho')]})
    proposals, calls, _ = unresolved_proposals(text, matcher(), Catalog.load(ROOT), base)
    assert proposals == [] and calls == 0


@pytest.mark.parametrize('text', ['Mẹ tôi cứ có cảm giác sắp ói ra.',
    'Nhân vật trong truyện rã rời hết sức.', 'Giả sử tôi có cảm giác sắp ói ra thì sao?',
    'Tôi đọc câu "không lấy đủ hơi" trong sách.'])
def test_context_does_not_become_user_fact(text):
    proposals, calls, _ = unresolved_proposals(text, matcher(), Catalog.load(ROOT))
    assert proposals == [] and calls == 0


def test_oracle_is_only_upper_bound_and_never_changes_base_or_candidates():
    base = {'fever':'present'}
    proposals = [dict(state='present', candidates=[dict(feature='nausea'), dict(feature='cough')])]
    case = dict(expected_states={'fever':'present', 'nausea':'present'})
    assert oracle_confirmation(case, base, proposals) == case['expected_states']
    assert base == {'fever':'present'} and len(proposals[0]['candidates']) == 2


def test_missing_denominator_is_not_zero_recall_and_no_real_confirmation_is_invented():
    m = dict(states={}, suggestions=[], oracle_states={}, embedding_calls=0, latency_ms=1.)
    rows = [dict(group='ambiguous', expected_states={}, missed_present=[],
                 methods={name:dict(m) for name in ('rule_based','semantic','hybrid')})]
    summary = summarize(rows)
    assert all(v['missed_recall_at_3'] is None for v in summary)
    assert all(v['real_user_post_confirmation_precision'] is None for v in summary)


def test_ambiguous_candidates_are_not_labelled_exhaustive_false_positives():
    m = dict(states={}, suggestions=[dict(state='present',candidates=[dict(feature='cough')])],
             oracle_states={}, embedding_calls=1, latency_ms=1.)
    row = dict(group='ambiguous', expected_states={}, missed_present=[],
               methods={name:dict(m) for name in ('rule_based','semantic','hybrid')})
    result = next(v for v in summarize([row]) if v['group']=='all' and v['method']=='hybrid')
    assert result['candidate_false_discovery_fraction'] is None
    assert result['ambiguous_candidate_questions'] == 1
    assert result['ambiguous_automatic_assignment_cases'] == 0


def test_feature_hit_with_wrong_assertion_is_not_successful_recovery():
    m = dict(states={},suggestions=[dict(state='denied',candidates=[dict(feature='shortness of breath')])],
             oracle_states={},embedding_calls=1,latency_ms=1.)
    row = dict(group='multiple_symptoms',expected_states={'shortness of breath':'present'},
               missed_present=[('shortness of breath','present')],
               methods={name:dict(m) for name in ('rule_based','semantic','hybrid')})
    result = next(v for v in summarize([row]) if v['group']=='all' and v['method']=='hybrid')
    assert result['feature_only_missed_recall_at_3'] == 1
    assert result['missed_recall_at_3'] == 0


def test_recall_counts_only_present_missed_by_rule_not_all_gold():
    proposal = dict(state='present', candidates=[dict(feature='nausea')])
    methods = {name:dict(states={'fever':'present'},suggestions=[proposal], oracle_states={},embedding_calls=1,latency_ms=2.)
               for name in ('rule_based','semantic','hybrid')}
    row = dict(group='multiple_symptoms', expected_states={'fever':'present','nausea':'present'},
               missed_present=[('nausea','present')], methods=methods)
    result = next(v for v in summarize([row]) if v['group']=='all' and v['method']=='hybrid')
    assert result['rule_missed_present_pairs'] == 1 and result['missed_recall_at_3'] == 1.


def test_old_executed_cells_have_not_been_relabelled():
    nb = json.loads((ROOT/'notebooks/07_vietnamese_symptom_extraction.ipynb').read_text(encoding='utf-8'))
    code = ''.join(next(c for c in nb['cells'] if c['id']=='nlp07-missed-evaluation')['source'])
    assert 'scripts.nlp_missed_symptom_analysis' in code
    assert "MISSED_FOLDER/'manifest.json'" in code
    assert 'oracle chỉ là cận trên' in code
