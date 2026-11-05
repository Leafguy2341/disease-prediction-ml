"""Regression for offline dialogue policy and collision resolution; no live API."""
import pytest
from dataclasses import replace
import json
import logging
from pathlib import Path
from fastapi.testclient import TestClient
from app.backend.main import create_app
from src.agent.conversation import Policy
from src.agent.offline import OfflinePolicy, OfflineConversation, OfflineExtractor
from test_prediction_api import deployment, get_service
from test_offline_chat import engine, offline_only, legacy_runtime


@pytest.mark.parametrize('text', ['Tôi bị sốt', 'Tôi bị ho và sốt'])
def test_first_turn_low_information_asks(engine, text):
    reply = engine.handle(text)
    assert reply.status == 'clarification_required', reply
    assert reply.predictions is None


@pytest.mark.parametrize('text,feature', [('đau cơ', 'muscle pain'), ('đau cổ', 'neck pain')])
def test_exact_accented_alias(engine, text, feature):
    reply = engine.handle(text)
    assert reply.sidecar['states'] == {feature: 'present'}


@pytest.mark.parametrize('text', ['dau co', 'Tôi bị dau co và sốt', 'Tôi không dau co'])
def test_collision_asks_specific_disambiguation(engine, text):
    reply = engine.handle(text)
    assert reply.status == 'clarification_required', reply
    assert 'đau cơ' in reply.message and 'đau cổ' in reply.message, reply
    assert not {'muscle pain', 'neck pain'} & set(reply.sidecar['states'])


@pytest.mark.parametrize('text,has_cough', [('ho', True), ('kho hàng', False), ('hoàng hôn', False)])
def test_cough_is_whole_phrase(engine, text, has_cough):
    reply = engine.handle(text)
    assert ((reply.sidecar or {}).get('states', {}).get('cough') == 'present') == has_cough


@pytest.mark.parametrize('answer,chosen', [('đau cơ','muscle pain'), ('đau cổ','neck pain'),
                                         ('cái đầu','muscle pain'), ('cái thứ hai','neck pain')])
def test_collision_choice_keeps_provenance(engine, answer, chosen):
    first = engine.handle('Tôi bị dau co và sốt')
    session = engine.store.get(first.session_id)
    pending = engine._state(session)['pending_clarification']
    assert pending['candidate_features'] == ['muscle pain','neck pain']
    second = engine.handle(answer, session_id=first.session_id)
    assert second.sidecar['states'][chosen] == 'present', second
    assert second.sidecar['states']['fever'] == 'present'
    assert ({'neck pain','muscle pain'} - {chosen}).isdisjoint(second.sidecar['states'])
    evidence = second.sidecar['evidence'][chosen][0]
    assert evidence['turn_id'] == first.turn_id and evidence['text'] == 'dau co'
    assert engine._state(session)['pending_clarification'] is None


@pytest.mark.parametrize('text,state', [('Tôi không dau co', 'denied'), ('Tôi chưa rõ dau co', 'uncertain')])
def test_collision_choice_never_promotes_denied_or_uncertain(engine, text, state):
    first = engine.handle(text)
    second = engine.handle('cái thứ hai', session_id=first.session_id)
    assert second.sidecar['states']['neck pain'] == state, second
    assert 'muscle pain' not in second.sidecar['states']
    assert second.status != 'extraction_ready'


@pytest.mark.parametrize('answer', ['có', 'không', 'dau co', 'thời tiết hôm nay'])
def test_collision_no_guess_from_unclear_reply(engine, answer):
    first = engine.handle('dau co')
    second = engine.handle(answer, session_id=first.session_id)
    assert second.status != 'extraction_ready'
    assert not {'muscle pain','neck pain'} & set((second.sidecar or {}).get('states', {}))


def test_pending_collision_session_isolation(engine):
    first = engine.handle('dau co')
    other = engine.handle('cái thứ hai')
    assert not {'neck pain','muscle pain'} & set((other.sidecar or {}).get('states', {}))
    selected = engine.handle('đau cổ', session_id=first.session_id)
    assert selected.sidecar['states']['neck pain'] == 'present'


def test_pending_collision_not_carried_across_subjects(engine):
    first = engine.handle('dau co')
    switched = engine.handle('cái thứ hai', session_id=first.session_id, subject_id='mother')
    assert switched.status != 'extraction_ready'
    assert not {'neck pain','muscle pain'} & set((switched.sidecar or {}).get('states', {}))


def test_dialogue_budget_counts_present_only(engine):
    first = engine.handle('Tôi ho và sốt.')
    assert first.reason == 'offline_collect_more' and 'đau đầu' in first.message
    session = engine.store.get(first.session_id)
    assert session.questions == 1 and engine._remaining(session) == 1
    second = engine.handle('không', session_id=first.session_id)
    assert second.sidecar['states'] == {'cough':'present','fever':'present','headache':'denied'}
    assert second.status == 'clarification_required' and 'buồn nôn' in second.message
    third = engine.handle('không', session_id=first.session_id)
    assert third.status == 'extraction_ready' and third.reason == 'offline_limited_question_budget'
    assert engine.store.get(first.session_id).questions == 2
    assert sum(s == 'present' for s in third.sidecar['states'].values()) == 2


def test_one_present_after_budget_abstains(engine):
    first = engine.handle('Tôi ho.')
    second = engine.handle('không', session_id=first.session_id)
    third = engine.handle('không', session_id=first.session_id)
    assert third.status == 'abstained' and third.reason == 'offline_insufficient_question_budget'


def test_more_symptoms_policy_is_configurable(engine):
    text = 'Tôi ho và sốt và đau đầu.'
    assert engine.handle(text).status == 'extraction_ready'
    engine.offline_policy = replace(engine.offline_policy, ask_when_present_at_most=3)
    reply = engine.handle(text)
    assert reply.status == 'clarification_required' and reply.reason == 'offline_collect_more'


def test_primary_empty_uses_display_fallback_not_alias_requirement(engine):
    engine.offline_policy = replace(engine.offline_policy, question_priority=())
    # A Vietnamese display is sufficient for asking; no feature is asserted by asking.
    for f, entry in engine.provider.synonyms.items():
        entry['display_vi'] = f
    engine.provider.synonyms['cough']['display_vi'] = 'ho'
    engine.provider.synonyms['cough']['aliases_vi'] = []
    reply = engine.handle('Tôi sốt.')
    assert reply.status == 'clarification_required' and 'ho' in reply.message
    assert engine._state(engine.store.get(reply.session_id))['selector'] == 'display_catalog_fallback'
    assert reply.sidecar['states'] == {'fever':'present'}


@pytest.mark.parametrize('text,expected', [('Tôi ho và sốt.','offline_limited_no_eligible_question'),
                                         ('Tôi ho.','offline_insufficient_no_eligible_question')])
def test_no_eligible_candidate_terminal_reason(engine, text, expected):
    engine.offline_policy = replace(engine.offline_policy, question_priority=(), fallback_to_display_catalog=False)
    result = engine.handle(text)
    assert result.reason == expected
    assert (result.status == 'extraction_ready') == ('limited' in expected)


def test_missing_display_filtered_and_fallback_keeps_schema_order(engine):
    engine.provider.synonyms['headache']['display_vi'] = ''
    reply = engine.handle('Tôi ho và sốt.')
    assert 'buồn nôn' in reply.message
    assert engine.catalog.features.index('cough') == 15
    assert len(engine.catalog.features) == 375


def test_urgent_beats_pending_ask(engine):
    first = engine.handle('Tôi ho và sốt.')
    result = engine.handle('Khó thở nặng, thở không nổi.', session_id=first.session_id)
    assert result.status == 'urgent_redirect'


def test_logs_off_by_default_then_sanitized(engine, caplog):
    with caplog.at_level(logging.INFO, logger='src.agent.offline'):
        first = engine.handle('Tôi bị ho và sốt.')
        assert not [r for r in caplog.records if r.name == 'src.agent.offline']
        engine.offline_policy = replace(engine.offline_policy, debug_logging=True)
        engine.handle('Tôi bị ho và sốt.')
    records = [json.loads(r.message) for r in caplog.records if r.name == 'src.agent.offline']
    assert records[-1]['action'] == 'ASK' and records[-1]['present_count'] == 2
    assert records[-1]['remaining_question_budget'] == 1
    assert records[-1]['top3_model_scores'] is None
    assert 'Tôi bị ho' not in caplog.text and first.session_id not in caplog.text
    assert len(records[-1]['session']) == 12


def test_http_no_prediction_before_policy_and_limited_warning(deployment):
    service = get_service(deployment)
    with TestClient(create_app(service_loader=lambda:service, chat_factory=legacy_runtime)) as client:
        first = client.post('/api/v1/chat',json={'message':'Tôi bị ho và sốt'}).json()
        assert first['status'] == 'clarification_required' and first['predictions'] is None
        assert not deployment[2].calls
        second = client.post('/api/v1/chat',json={'message':'không','session_id':first['session_id']}).json()
        assert second['predictions'] is None and not deployment[2].calls
        third = client.post('/api/v1/chat',json={'message':'không','session_id':first['session_id']}).json()
        assert third['status'] == 'prediction_ready' and third['reason'] == 'offline_limited_question_budget'
        assert 'Thông tin còn hạn chế' in third['message']
        assert [r['score_percent'] for r in third['predictions']['top3']] == [40,30,10]
        reset = client.post('/api/v1/chat',json={'reset':True,'session_id':first['session_id']}).json()
        assert reset['session_id'] != first['session_id'] and reset['symptom_states'] == {}
    assert len(deployment[2].calls) == 1


def test_http_collision_reset_drops_pending(deployment):
    service = get_service(deployment)
    with TestClient(create_app(service_loader=lambda:service)) as client:
        first = client.post('/api/v1/chat',json={'message':'dau co'}).json()
        reset = client.post('/api/v1/chat',json={'reset':True,'session_id':first['session_id']}).json()
        reply = client.post('/api/v1/chat',json={'message':'cái thứ hai','session_id':reset['session_id']}).json()
        assert reply['predictions'] is None and not reply['symptom_states']
    assert not deployment[2].calls


def test_config_keeps_safety_gate_and_explicit_question_budget():
    root = Path(__file__).resolve().parents[1]
    cfg = json.loads((root/'configs/phase5b.json').read_text(encoding='utf-8'))
    settings = OfflinePolicy.from_file(root/'configs/phase5b.json')
    assert settings.ask_when_present_at_most == 2 and not settings.debug_logging
    assert cfg['conversation']['max_clarification_turns'] == 2
    assert cfg['conversation']['min_present_features'] == 2
    with pytest.raises(ValueError):
        OfflinePolicy(ask_when_present_at_most=1)


def test_report_missing_display_collision_and_short_aliases(engine, tmp_path):
    dictionary = engine.provider.synonyms
    del dictionary['headache']['display_vi']
    path = tmp_path/'synonyms.json'
    path.write_text(json.dumps(dictionary,ensure_ascii=False),encoding='utf-8')
    provider = OfflineExtractor(engine.catalog,path)
    assert not provider.synonyms['headache']['display_vi']
    assert provider.accented_aliases['đau cơ'] == {'muscle pain'}
    assert provider.aliases['dau co'] == {'muscle pain','neck pain'}


def test_debug_prediction_scores_are_numeric_and_no_labels(engine, caplog):
    engine.offline_policy = replace(engine.offline_policy,debug_logging=True)
    with caplog.at_level(logging.INFO,logger='src.agent.offline'):
        result = engine.handle('Tôi ho và sốt và đau đầu.')
        engine.log_debug(result,scores=[4.0,3.0,2.0])
    row = json.loads([r.message for r in caplog.records if r.name == 'src.agent.offline'][-1])
    assert row['event'] == 'offline_prediction' and row['top3_model_scores'] == [4.0,3.0,2.0]
    assert not {'message','text','states','labels','api_key'} & set(row)


@pytest.mark.parametrize('answer', ['dau cô', 'dau coo'])
def test_no_fuzzy_resolution_of_collision(engine, answer):
    first=engine.handle('dau co')
    result=engine.handle(answer,session_id=first.session_id)
    assert result.status != 'extraction_ready'
    assert not {'neck pain','muscle pain'} & set((result.sidecar or {}).get('states',{}))


def test_three_feature_frame_remains_ordered_after_asking(engine):
    first=engine.handle('Tôi ho.')
    second=engine.handle('có',session_id=first.session_id)
    third=engine.handle('có',session_id=first.session_id)
    assert second.status == 'clarification_required' and third.status == 'extraction_ready'
    frame=engine.ready_vector(third.session_id,third.turn_id)
    assert frame.shape == (1,375) and tuple(frame.columns) == engine.catalog.features
    assert int(frame.to_numpy().sum()) == 3
    assert frame[['cough','fever','headache']].to_numpy().tolist() == [[1,1,1]]
