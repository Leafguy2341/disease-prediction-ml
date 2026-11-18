"""Owner-approved lexical index/config checks, not clinical validation."""
from pathlib import Path
import hashlib,json,socket
import pytest
from scripts.activate_full_symptom_dictionary import activate_entries,RELEASE,ROOT
from scripts.nlp_symptom_research import engine,rule_extract
from src.agent.extraction import Catalog


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    def blocked(*args,**kwargs):raise AssertionError('No network for offline dictionary')
    monkeypatch.setattr(socket.socket,'connect',blocked)
    monkeypatch.setattr(socket,'create_connection',blocked)


def test_exact_240_status_changes_preserve_all_existing_aliases():
    before=json.loads((RELEASE/'synonyms.before.json').read_text(encoding='utf-8'))
    actual=json.loads((ROOT/'configs/synonyms.json').read_text(encoding='utf-8'))
    after,activated=activate_entries(before,Catalog.load(ROOT).features)
    assert actual==after and len(activated)==240
    assert all(e['activation_status']=='ACTIVE_EXISTING' for e in actual.values())
    assert sum(len(e['aliases_vi']) for e in actual.values())==400
    for f in actual:
        assert {k:v for k,v in actual[f].items() if k!='activation_status'}=={k:v for k,v in before[f].items() if k!='activation_status'}


def test_complete_runtime_alias_index_and_release_hashes():
    e=engine();manifest=json.loads((RELEASE/'manifest.json').read_text(encoding='utf-8'))
    assert len(e.provider.synonyms)==375
    for feature,entry in e.provider.synonyms.items():
        assert entry['aliases_vi'] and entry['needs_review'] is True
        assert all(feature in e.provider.candidates(a) for a in entry['aliases_vi'])
    assert hashlib.sha256((ROOT/'configs/synonyms.json').read_bytes()).hexdigest()==manifest['current_sha256']
    for name,value in manifest['files'].items():
        assert hashlib.sha256((RELEASE/name).read_bytes()).hexdigest()==value['sha256']


@pytest.mark.parametrize('text,feature,state',[
    ('Tôi bị dịch trong tai.','fluid in ear','present'),
    ('Tôi không bị dịch trong tai.','fluid in ear','denied'),
    ('Tôi chưa chắc bị dịch trong tai.','fluid in ear','uncertain'),
    ('Tôi bị đau ở nướu.','pain in gums','present'),
    ('Tôi bị khối bất thường ở thận.','kidney mass','present'),
    ('Tôi ho và sốt.','cough','present'),
])
def test_known_new_alias_contexts(text,feature,state):
    assert rule_extract(text)['states'].get(feature)==state


@pytest.mark.parametrize('text',[
    'Mẹ tôi bị dịch trong tai.',
    'Nhân vật trong truyện bị hoang tưởng hoặc ảo giác.',
    'Giả sử tôi bị dịch trong tai thì sao?',
    'Tôi đọc câu "dịch trong tai" trong sách.',
])
def test_subject_and_fiction_guards_remain(text):
    assert rule_extract(text)['states']=={}


def test_collisions_clarify_without_fuzzy_mapping():
    e=engine();assert len(e.provider.candidates('dau co'))>1
    result=e.handle('Tôi bị dau co.')
    assert result.reason=='offline_alias_collision' and result.predictions is None


def test_not_infer_kidney_mass_from_regional_pain():
    assert rule_extract('Tôi bị đau vùng thận.')['states'].get('kidney mass')!='present'
