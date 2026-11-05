"""Activation proposals are exercised only in an owned temporary dictionary."""
from collections import Counter,defaultdict
import csv
import json
from pathlib import Path
import pytest
from scripts.review_symptom_activation import (ROOT,read_inputs,fixture_dictionary,engine_for,
    production_signature,PRODUCTION_SIGNATURE,propose,sha)
from test_offline_chat import offline_only
from symptom_activation_history import original_dictionary
from scripts import review_symptom_activation as historical

# The immutable proposal pins refer to the BEFORE dictionary. Replay historical
# proposal tests explicitly; production activation is tested in its own module.
def read_inputs(*args,**kwargs):
    with original_dictionary():return historical.read_inputs(*args,**kwargs)

def propose(*args,**kwargs):
    with original_dictionary():return historical.propose(*args,**kwargs)

with (ROOT/'reports/terminology/symptom_activation_decisions.csv').open(encoding='utf-8-sig',newline='') as stream:
    DECISIONS=list(csv.DictReader(stream))
CASES=[json.loads(line) for line in (ROOT/'data/evaluation/vietnamese_symptom_activation_cases.jsonl').read_text(encoding='utf-8').splitlines()]
EVIDENCE=json.loads((ROOT/'reports/terminology/symptom_activation_validation.json').read_text(encoding='utf-8'))
APPROVED={r['canonical_feature'] for r in DECISIONS if r['decision']=='APPROVE'}

@pytest.fixture(scope='module')
def hypothetical(tmp_path_factory):
    catalog,entries,_,_,_=read_inputs()
    path=tmp_path_factory.mktemp('activation-proposal')/'hypothetical.json'
    return engine_for(catalog,fixture_dictionary(entries,APPROVED),path)


@pytest.mark.parametrize('case',CASES,ids=[c['id']+'-'+c['kind'] for c in CASES])
def test_fixture_case(hypothetical,case):
    assert case['scope']=='HYPOTHETICAL_FIXTURE_ONLY' and case['synthetic']
    assert case['feature'] in APPROVED
    result=hypothetical.handle(case['text'])
    try:
        assert result.reason!='invalid_session'
        states=(result.sidecar or {}).get('states',{})
        if case['expected_states'] is not None:assert states==case['expected_states'],result
        assert not set(case['forbidden_features']) & set(states),result
        assert result.predictions is None
        if result.sidecar:
            session=hypothetical.store.get(result.session_id)
            turns={t.turn_id:t.text for t in session.turns}
            for spans in result.sidecar['evidence'].values():
                for s in spans:assert turns[s['turn_id']][s['start']:s['end']]==s['text']
    finally:
        if result.session_id:hypothetical.store.discard(result.session_id)


def test_all_375_decisions_and_forecast():
    catalog,_,rows,old_cases,identities=read_inputs()
    assert [r['canonical_feature'] for r in DECISIONS]==list(catalog.features)
    assert len(DECISIONS)==len({r['canonical_feature'] for r in DECISIONS})==375
    assert Counter(r['decision'] for r in DECISIONS)=={'APPROVE':128,'REVISE':73,'CLARIFY':26,'HOLD':148}
    source={r['canonical_feature']:r for r in rows}
    for f in APPROVED:
        assert source[f]['review_status']=='READY' and source[f]['production_activation']=='PENDING_REVIEW'
        assert not source[f]['collision_risks']
    assert len(old_cases)==86
    assert EVIDENCE['summary']['projected_active_features']==135+len(APPROVED)==263
    assert EVIDENCE['summary']['production_changed'] is False
    assert identities==EVIDENCE['summary']['input_identities']


def test_every_approved_alias_has_required_cases():
    kinds=defaultdict(set)
    for c in CASES:
        if c['alias']:kinds[c['feature'],c['alias']].add(c['kind'])
    _,entries,_,_,_=read_inputs()
    for f in APPROVED:
        for alias in entries[f]['proposed_aliases_vi']:
            assert kinds[f,alias]>={'affirmed','denied','unaccented','substring_boundary'}
        assert any(c['feature']==f and c['kind']=='near_feature_negative' for c in CASES)


def test_production_and_scope_unchanged():
    _,entries,_,_,identities=read_inputs()
    assert production_signature(entries)==PRODUCTION_SIGNATURE
    with original_dictionary():
        assert sha(ROOT/'configs/synonyms.json')==identities['production_config_sha256']
    assert Counter(e['activation_status'] for e in entries.values())=={'ACTIVE_EXISTING':135,'PENDING_REVIEW':240}
    trial=fixture_dictionary(entries,APPROVED)
    assert Counter(e['activation_status'] for e in trial.values())=={'ACTIVE_EXISTING':263,'PENDING_REVIEW':112}
    assert Counter(e['activation_status'] for e in entries.values())=={'ACTIVE_EXISTING':135,'PENDING_REVIEW':240}


def test_special_groups_and_failed_candidates_not_approved():
    by={r['canonical_feature']:r for r in DECISIONS}
    for f in ['gum pain','pain in gums','shortness of breath','difficulty breathing']:
        assert by[f]['decision']=='HOLD'
    for f in ['difficulty speaking','slurring words','stuttering or stammering','frequent urination',
              'polyuria','heartburn','burning chest pain','neck pain','muscle pain']:
        assert by[f]['decision']=='CLARIFY'
    for f in ['excessive urination at night','fluid retention','incontinence of stool','pupils unequal']:
        assert by[f]['decision']=='REVISE' and int(by[f]['test_failures'])>0


def test_evidence_reports_observed_failures_without_false_safety_claim():
    initial=EVIDENCE['initial_results'];final=EVIDENCE['final_results'];s=EVIDENCE['summary']
    assert len(initial)==s['initial_fixture_cases']==844
    assert sum(not r['pass'] for r in initial)==s['initial_failures']==8
    assert sum(bool(r['wrong_feature_ids']) for r in initial)==1
    assert len(final)==len(CASES)==s['final_fixture_cases']==821
    assert all(r['pass'] and not r['wrong_feature_ids'] for r in final)
    assert s['status']=='PROPOSED_NOT_ACTIVATED'
    assert not any(s['guard_counts'].values())


def test_proposal_reproduces_without_editing_production():
    decisions,cases,evidence=propose()
    assert {r['canonical_feature'] for r in decisions if r['decision']=='APPROVE'}==APPROVED
    assert cases==CASES
    assert evidence['initial_results']==EVIDENCE['initial_results']
    assert evidence['final_results']==EVIDENCE['final_results']
