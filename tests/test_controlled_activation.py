"""Real dictionary activation against frozen proposal, offline only; no ML weights."""
import json
from collections import Counter
from pathlib import Path
import pytest
from scripts.activate_reviewed_symptoms import ROOT,RELEASE,qualified_dictionary,run_cases,context_cases
from scripts.review_symptom_activation import engine_for,sha
from scripts.build_synonyms_report import collision_rows
from src.agent.extraction import Catalog
from test_offline_chat import offline_only

M=json.loads((RELEASE/'manifest.json').read_text(encoding='utf-8'))
BASE=json.loads((RELEASE/'synonyms.before.json').read_text(encoding='utf-8'))
CASES=[json.loads(l) for l in (ROOT/'data/evaluation/vietnamese_symptom_activation_cases.jsonl').read_text(encoding='utf-8').splitlines()]
CONTEXTS=context_cases(BASE,M['qualified_features'])

@pytest.fixture(scope='module')
def production(tmp_path_factory):
    return engine_for(Catalog.load(ROOT),json.loads((ROOT/'configs/synonyms.json').read_text(encoding='utf-8')),
        tmp_path_factory.mktemp('activated-dictionary')/'production.json')

@pytest.fixture(scope='module')
def hypothetical(tmp_path_factory):
    return engine_for(Catalog.load(ROOT),qualified_dictionary(BASE,M['approved_features']),
        tmp_path_factory.mktemp('original-qualification')/'hypothetical.json')

@pytest.fixture(scope='module')
def qualified(tmp_path_factory):
    return engine_for(Catalog.load(ROOT),qualified_dictionary(BASE,M['qualified_features']),
        tmp_path_factory.mktemp('context-qualified')/'qualified.json')

def test_exact_authorized_delta_and_source_pins():
    actual=json.loads((ROOT/'configs/synonyms.json').read_text(encoding='utf-8'))
    assert actual==qualified_dictionary(BASE,M['activated_features'])
    assert list(actual)==list(BASE) and set(actual)==set(Catalog.load(ROOT).features)
    assert sha(RELEASE/'synonyms.before.json')==M['before_sha256']
    assert sha(ROOT/'configs/synonyms.json')==M['current_sha256']
    assert len(M['qualified_features'])==127 and M['excluded_features']==['delusions or hallucinations']
    assert len(M['approved_features'])==128
    assert set(M['activated_features'])<=set(M['qualified_features'])<=set(M['approved_features'])
    assert all(actual[f]==e for f,e in BASE.items() if f not in M['activated_features'])
    assert all(actual[f]['needs_review'] for f in actual)
    for name,expected in M['input_identities']['source_sha256'].items():assert sha(ROOT/name)==expected
    assert sha(ROOT/'configs/phase5b.json')==M['input_identities']['runtime_policy_sha256']
    for name,expected in M['input_identities']['packets'].items():assert sha(ROOT/'reports/terminology'/name)==expected
    assert sha(ROOT/'reports/terminology/symptom_activation_decisions.csv')==M['decisions_sha256']
    assert Counter(e['activation_status'] for e in actual.values())=={'ACTIVE_EXISTING':135+len(M['activated_features']),'PENDING_REVIEW':240-len(M['activated_features'])}

def test_no_new_folded_collision():
    actual=json.loads((ROOT/'configs/synonyms.json').read_text(encoding='utf-8'))
    def collisions(d):return [r for r in collision_rows(d,proposed=False) if r['kind']=='FOLDED_ALIAS_COLLISION']
    assert collisions(actual)==collisions(BASE)

@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_821_current_or_historical_qualification(production,hypothetical,case):
    if case['feature'] in M['activated_features']:
        result=run_cases(production,[case])[0]
        assert result['passed'],result
    else:
        # Exercise the unchanged 821-case qualification even for not-yet-active
        # or explicitly rejected features, but never claim production activation.
        result=run_cases(hypothetical,[case])[0]
        assert result['passed'],result

@pytest.mark.parametrize('case',CONTEXTS,ids=lambda c:c['id'])
def test_new_contexts_on_qualified_subset(production,qualified,case):
    engine=production
    if case['feature'] not in M['activated_features']:
        engine=qualified
    result=run_cases(engine,[case])[0]
    assert result['passed'],result

def test_excluded_alias_remains_inactive(production):
    assert production.provider.synonyms['delusions or hallucinations']['activation_status']=='PENDING_REVIEW'
    r=production.handle('Nhân vật trong truyện bị hoang tưởng hoặc ảo giác.')
    assert 'delusions or hallucinations' not in (r.sidecar or {}).get('states',{})
    assert r.status!='extraction_ready' and r.predictions is None
