"""Mechanical synthetic extraction checks, not clinical or human review evidence."""
import csv
import json
from pathlib import Path
from collections import Counter
import pytest
from scripts.build_synonyms_report import review_rows,production_signature,collision_rows,write_review_csv
from src.agent.presentation import PredictionPresenter
from test_offline_v2 import v2
from test_offline_chat import offline_only
from symptom_activation_history import activation_manifest

ROOT=Path(__file__).resolve().parents[1]
CASES=[json.loads(line) for line in (ROOT/'data/evaluation/vietnamese_symptom_semantic_cases.jsonl').read_text(encoding='utf-8').splitlines()]

@pytest.mark.parametrize('case',CASES,ids=[c['id']+'-'+c['kind'] for c in CASES])
def test_synthetic_case(v2,case):
    assert case['synthetic'] and case['review_status']=='pending_human_review'
    r=v2.handle(case['text'])
    states=(r.sidecar or {}).get('states',{})
    if case['id']=='semantic-084' and 'elbow swelling' in activation_manifest()['activated_features']:
        # Original packet is unchanged; its old "pending alias must not match"
        # expectation is explicitly superseded by owner-approved activation.
        assert states=={'elbow swelling':'present'} and r.status!='extraction_ready'
        assert r.predictions is None
        return
    if case['expected_states'] is not None: assert states==case['expected_states'],r
    assert not set(case['forbidden_features']) & set(states),r
    assert r.status!='extraction_ready' and r.predictions is None
    if case.get('expected_reason'):assert r.reason==case['expected_reason'],r
    if r.sidecar:
        session=v2.store.get(r.session_id)
        turns={turn.turn_id:turn.text for turn in session.turns}
        for spans in r.sidecar['evidence'].values():
            for span in spans:assert turns[span['turn_id']][span['start']:span['end']]==span['text']


def test_all_375_rows_and_normalized_status_semantics(v2,tmp_path):
    rows=review_rows(ROOT)
    assert [r['canonical_feature'] for r in rows]==list(v2.catalog.features)
    assert len(rows)==len({r['canonical_feature'] for r in rows})==375
    assert all(r['needs_review'] is True and r['clinical_review']=='NOT_CLINICALLY_VALIDATED' for r in rows)
    assert all(r['confidence']=='HIGH' for r in rows if r['review_status']=='READY')
    assert all(r['confidence']=='LOW' for r in rows if r['review_status']=='AMBIGUOUS')
    assert all(r['production_activation'] in {'ACTIVE_EXISTING','PENDING_REVIEW'} for r in rows)
    assert all(r['source_status'] in {'REFERENCE_FOR_TERM_OR_DISTINCTION','REFERENCE_LISTED_NOT_RECHECKED','NOT_INDEPENDENTLY_VERIFIED'} for r in rows)
    receipt=write_review_csv(ROOT,tmp_path/'review.csv');assert receipt['rows']==375
    with (tmp_path/'review.csv').open(encoding='utf-8-sig',newline='') as stream:
        assert len(list(csv.DictReader(stream)))==375


def test_production_aliases_and_display_only_change_when_authorized(v2):
    entries=v2.provider.synonyms
    n=len(activation_manifest()['activated_features'])
    assert Counter(e['activation_status'] for e in entries.values())=={'ACTIVE_EXISTING':135+n,'PENDING_REVIEW':240-n}
    for feature,e in entries.items():
        for alias in set(e['proposed_aliases_vi'])-set(e['aliases_vi']):
            assert feature not in v2.provider.candidates(alias),(feature,alias)


def test_collisions_and_unresolved_source_labels_are_explicit(v2):
    rows={r['canonical_feature']:r for r in review_rows(ROOT)}
    for feature in ['shortness of breath','difficulty breathing','gum pain','pain in gums','symptoms of infants','hesitancy']:
        assert rows[feature]['review_status']=='AMBIGUOUS'
        assert rows[feature]['activation_recommendation']=='SOURCE_DEFINITION_REQUIRED'
    risks=collision_rows(v2.provider.synonyms)
    assert any(r['kind']=='FOLDED_ALIAS_COLLISION' and r['alias_or_group']=='dau co' for r in risks)
    assert any(r['kind']=='FOLDED_ALIAS_COLLISION' and r['alias_or_group']=='dau mat' for r in risks)
    assert any(r['kind']=='SEMANTIC_OVERLAP_RISK' for r in risks)
    current=[r['alias_or_group'] for r in collision_rows(v2.provider.synonyms,proposed=False)
             if r['kind']=='FOLDED_ALIAS_COLLISION']
    assert current==['dau co','dau mat']


def test_global_accuracy_is_separate_from_each_raw_prediction(v2):
    ref=PredictionPresenter.evaluation(ROOT)
    presenter=PredictionPresenter(v2.catalog.classes,evaluation_reference=ref)
    prediction={'model_id':'lr_tuned_c2','checkpoint_sha256':ref['checkpoint_sha256'],
        'top3':[{'rank':i+1,'class_id':i,'label':v2.catalog.classes[i],'score_percent':s}
                for i,s in enumerate([4.0,3.0,2.0])]}
    output=presenter.render(prediction)
    assert output['top3']==prediction['top3']
    assert output['presentation']['model_evaluation']['accuracy']==0.8440818071688163
    assert all('accuracy' not in item for item in output['presentation']['top3'])
    source=(ROOT/'app/frontend/app.js').read_text(encoding='utf-8')
    assert source.index("benchmark.className='evaluation-reference'")<source.index('for (const item of prediction.top3)')
    assert 'Accuracy là metric toàn tập test' in source
