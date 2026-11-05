"""Synthetic health-intent and presentation checks; no live APIs or dataset access."""
import pytest
from copy import deepcopy
from dataclasses import replace
import json
import logging
from pathlib import Path
import unicodedata
from fastapi.testclient import TestClient
from app.backend.main import create_app
from src.agent.offline import HealthIntentDetector, OfflinePolicy
from src.agent.presentation import PredictionPresenter
from test_prediction_api import deployment, get_service
from test_offline_chat import engine, offline_only, legacy_runtime


@pytest.mark.parametrize('text', ['ngực tôi có khối u thì bị bệnh gì',
    'tôi lo mình bị ung thư vú', 'tôi có bầu không'])
def test_unsupported_health_not_unrelated(engine, text):
    result = engine.handle(text)
    assert result.status == 'unsupported_health', result
    assert result.predictions is None
    assert not (result.sidecar or {}).get('states', {})


def test_supported_symptom_still_asks(engine):
    assert engine.handle('tôi bị sốt').status == 'clarification_required'


@pytest.mark.parametrize('text', ['hôm nay ngày mấy', 'quả trứng hay con gà có trước', 'asdf'])
def test_non_health_remains_outside(engine, text):
    assert engine.handle(text).status == 'out_of_scope'


@pytest.mark.parametrize('text', ['nguc toi co khoi u thi bi benh gi', 'toi lo minh bi ung thu vu',
    'toi co bau khong', 'thuốc này dùng thế nào', 'trieu chung cua benh la gi', 'Ho là gì?',
    unicodedata.normalize('NFD','tôi có bầu không')])
def test_health_variants_no_feature_invention(engine, text):
    result = engine.handle(text)
    assert result.status == 'unsupported_health', result
    assert not (result.sidecar or {}).get('states', {})
    assert '587' in result.message and 'khẳng định hoặc loại trừ' in result.message


@pytest.mark.parametrize('text,context', [('tôi có bầu không','self'), ('mẹ tôi có khối u','other'),
                                        ('nếu tôi có khối u','hypothetical'), ('khối u là gì','unspecified')])
def test_detector_context_independent_of_catalog(text, context):
    info=HealthIntentDetector(OfflinePolicy()).detect(text)
    assert info['is_health'] and info['context']==context


@pytest.mark.parametrize('text', ['họp hôm nay', 'họ đang học', 'tôi thuộc bài', 'asdf', 'quả trứng hay con gà có trước'])
def test_detector_whole_word_and_accents(text):
    assert not HealthIntentDetector(OfflinePolicy()).detect(text)['is_health']


def test_health_patterns_are_configured():
    root=Path(__file__).resolve().parents[1]
    policy=OfflinePolicy.from_file(root/'configs/phase5b.json')
    assert policy.health_keywords and policy.health_body_terms and policy.health_question_patterns
    disabled=replace(policy,health_keywords=(),health_body_terms=(),health_question_patterns=())
    assert not HealthIntentDetector(disabled).detect('ngực tôi có khối u')['is_health']


@pytest.mark.parametrize('text', ['Tôi ho và lo mình bị ung thư vú.', 'Tôi ho và sốt, ngực tôi có khối u.'])
def test_mixed_health_preserves_confirmed_symptoms(engine,text):
    result=engine.handle(text)
    assert result.status=='unsupported_health',result
    assert result.sidecar['states']['cough']=='present'
    assert result.sidecar['unmapped']
    assert not {'recent pregnancy','lump or mass of breast'} & set(result.sidecar['states'])


def test_health_session_does_not_relabel_new_unrelated_turn(engine):
    first=engine.handle('tôi lo mình bị ung thư vú')
    second=engine.handle('hôm nay ngày mấy',session_id=first.session_id)
    assert second.status=='out_of_scope'
    other=engine.handle('có')
    assert other.status=='out_of_scope'


def test_pending_answer_keeps_precedence_and_urgent_bypasses(engine):
    first=engine.handle('Tôi sốt.')
    second=engine.handle('có',session_id=first.session_id)
    assert second.sidecar['states']['cough']=='present'
    urgent=engine.handle('Khó thở nặng và ngực có khối u.',session_id=first.session_id)
    assert urgent.status=='urgent_redirect' and urgent.predictions is None


def test_presentation_reviewed_fallback_and_no_numeric_changes():
    labels=('example disease','rare example','another example')
    names={labels[0]:{'display_vi':'Bệnh minh họa','needs_review':False},
           labels[1]:{'display_vi':'Bản nháp chưa duyệt','needs_review':True}}
    presenter=PredictionPresenter(labels,names)
    original={'top3':[{'class_id':i,'label':label,'score_percent':score} for i,(label,score) in
                         enumerate(zip(labels,[6.78912345,2.0,0.123456789]))]}
    frozen=deepcopy(original); result=presenter.render(original)
    assert original==frozen and result['top3']==original['top3']
    rows=result['presentation']['top3']
    assert [r['score_text'] for r in rows]==['6.7891%','2.0000%','0.1235%']
    assert [r['display_label'] for r in rows]==['Bệnh minh họa',labels[1],labels[2]]
    assert [r['translation_status'] for r in rows]==['reviewed','needs_review','missing']
    assert result['presentation']['warnings']


@pytest.mark.parametrize('score',[float('nan'),float('inf'),-1,101,True,'6.7'])
def test_invalid_score_never_displayed(score):
    with pytest.raises(ValueError):
        PredictionPresenter(('example',)).render({'top3':[{'class_id':0,'label':'example','score_percent':score}]})


def test_canonical_identity_not_translated_or_remapped():
    with pytest.raises(ValueError):
        PredictionPresenter(('canonical',)).render({'top3':[{'class_id':0,'label':'changed','score_percent':1.0}]})


def test_actual_translation_coverage_not_falsely_reviewed(engine):
    root=Path(__file__).resolve().parents[1]
    presenter=PredictionPresenter.load(root,engine.catalog)
    assert set(presenter.translations)==set(engine.catalog.classes) and len(presenter.translations)==587
    report=presenter.coverage()
    assert set(report['reviewed'])=={'meningitis','white blood cell disease','flu'}
    assert len(report['needs_review'])==584 and not report['missing']
    assert not report['invalid_canonical_keys']
    assert presenter.score_decimals==4


def test_missing_translation_file_keeps_canonical_warning(engine,tmp_path):
    (tmp_path/'configs').mkdir()
    (tmp_path/'configs/phase5b.json').write_text(json.dumps({'presentation':{'SCORE_DECIMALS':4}}))
    presenter=PredictionPresenter.load(tmp_path,engine.catalog)
    assert len(presenter.coverage()['missing'])==587


def test_http_health_and_display_contract(deployment):
    service=get_service(deployment)
    with TestClient(create_app(service_loader=lambda:service, chat_factory=legacy_runtime)) as client:
        health=client.post('/api/v1/chat',json={'message':'tôi có bầu không'})
        assert health.status_code==200 and health.json()['status']=='unsupported_health'
        assert health.json()['predictions'] is None and not deployment[2].calls
        mixed=client.post('/api/v1/chat',json={'message':'Tôi ho và lo mình bị ung thư vú.'}).json()
        assert mixed['symptom_states']=={'cough':'present'} and mixed['state_summary']['unmatched_count']>0
        assert not deployment[2].calls
        prediction=client.post('/api/v1/predict',json={'present_features':['cough','fever']}).json()
        assert [i['score_percent'] for i in prediction['top3']]==[40,30,10]
        assert [i['score_text'] for i in prediction['presentation']['top3']]==['40.0000%','30.0000%','10.0000%']
        chat=client.post('/api/v1/chat',json={'message':'Tôi ho và sốt và đau đầu.'}).json()
        assert chat['status']=='prediction_ready'
        assert chat['state_summary']['top3_display']==chat['predictions']['presentation']['top3']
        assert all(i['canonical_label']==j['label'] for i,j in zip(chat['state_summary']['top3_display'],chat['predictions']['top3']))


def test_safe_health_logs(engine,caplog):
    engine.offline_policy=replace(engine.offline_policy,debug_logging=True)
    with caplog.at_level(logging.INFO,logger='src.agent.offline'):
        engine.handle('tôi có bầu không')
    row=json.loads([r.message for r in caplog.records if r.name=='src.agent.offline'][-1])
    assert row['action']=='UNSUPPORTED_HEALTH' and row['health_intent']['is_health']
    assert row['matched_count']==0 and row['unsupported_health_reason']
    assert 'tôi có bầu' not in caplog.text


def test_halfway_rounding_and_frontend_uses_authoritative_text():
    presenter=PredictionPresenter(('example',))
    result=presenter.render({'top3':[{'class_id':0,'label':'example','score_percent':1.03125}]})
    assert result['presentation']['top3'][0]['score_text']=='1.0312%'
    source=(Path(__file__).resolve().parents[1]/'app/frontend/app.js').read_text(encoding='utf-8')
    assert 'format.test(display.score_text)' in source
    assert '? display.score_text :' in source
    assert 'Number.isFinite(item.score_percent)' in source


def test_code_inventory_includes_presentation_dictionary():
    from scripts.package_handover import code_files
    files=code_files(Path(__file__).resolve().parents[1])
    assert {'configs/disease_names_vi.json','src/agent/presentation.py'} <= set(files)


def test_http_reviewed_display_fixture_keeps_canonical_and_scores(deployment):
    service=get_service(deployment)
    # Fictional review flags only in a test object; production translations unchanged.
    names={label:{'display_vi':'Nhãn thử '+str(i+1),'needs_review':False}
           for i,label in enumerate(service.catalog.classes[:3])}
    with TestClient(create_app(service_loader=lambda:service, chat_factory=legacy_runtime)) as client:
        presenter=PredictionPresenter(service.catalog.classes,names)
        client.app.state.presenter=presenter
        client.app.state.chat.presenter=presenter
        body=client.post('/api/v1/predict',json={'present_features':['cough','fever']}).json()
        assert [r['display_label'] for r in body['presentation']['top3']]==['Nhãn thử 1','Nhãn thử 2','Nhãn thử 3']
        assert [r['score_text'] for r in body['presentation']['top3']]==['40.0000%','30.0000%','10.0000%']
        assert [r['label'] for r in body['top3']]==list(service.catalog.classes[:3])
        chat=client.post('/api/v1/chat',json={'message':'Tôi ho và sốt và đau đầu.'}).json()
        assert chat['state_summary']['top3_display']==body['presentation']['top3']


def test_owner_enabled_drafts_are_displayed_without_false_review(engine):
    root=Path(__file__).resolve().parents[1]
    presenter=PredictionPresenter.load(root,engine.catalog)
    assert presenter.allow_draft_translations
    assert presenter.label('oral mucosal lesion')==('Tổn thương niêm mạc miệng','draft')
    assert presenter.label('meningitis')==('Viêm màng não','reviewed')
    owner_approved={'top3':[{'class_id':engine.catalog.classes.index('meningitis'),
                             'label':'meningitis','score_percent':35.3182}]}
    assert 'chưa được chuyên gia y tế rà soát' in presenter.render(owner_approved)['presentation']['warnings'][0]
    assert presenter.label('threatened pregnancy')==('threatened pregnancy','needs_review')
    coverage=presenter.coverage()
    assert len(coverage['reviewed'])==3 and len(coverage['needs_review'])==584
    assert len(coverage['draft_vi'])==580 and len(coverage['original_label_fallback'])==4


def test_draft_mode_can_be_disabled_and_always_warns():
    names={'example':{'display_vi':'Tên Việt tham khảo','needs_review':True}}
    raw={'top3':[{'class_id':0,'label':'example','score_percent':6.78912345}]}
    strict=PredictionPresenter(('example',),names)
    assert strict.label('example')==('example','needs_review')
    allowed=PredictionPresenter(('example',),names,allow_draft_translations=True)
    output=allowed.render(raw)
    assert output['top3']==raw['top3']
    assert output['presentation']['top3'][0]['translation_status']=='draft'
    assert output['presentation']['top3'][0]['score_text']=='6.7891%'
    assert 'chưa được chuyên gia y tế rà soát' in output['presentation']['warnings'][0]
    assert names['example']['needs_review'] is True


@pytest.mark.parametrize('text', ['tôi bị sốt và ho thì bị bệnh gì', 'tôi bị sốt và ho là bệnh gì?',
    'tôi sốt và ho, tôi có bệnh gì không?', 'toi sot va ho thi bi benh gi'])
def test_prediction_question_suffix_is_not_unsupported_health(engine,text):
    result=engine.handle(text)
    assert result.status=='clarification_required' and result.reason=='offline_collect_more',result
    assert result.sidecar['states']=={'fever':'present','cough':'present'}
    assert not result.sidecar['unmapped']


@pytest.mark.parametrize('text', ['tôi bị buồn nôn, ho và sốt nặng', 'toi bi buon non, ho va sot nang'])
def test_reported_symptoms_with_severity_are_not_unmapped(engine,text):
    result=engine.handle(text)
    assert result.status=='extraction_ready',result
    assert result.sidecar['states']=={'nausea':'present','cough':'present','fever':'present'}
    assert not result.sidecar['unmapped']


@pytest.mark.parametrize('text', ['Tôi ho và sốt nặng, có khối u.',
    'Tôi ho và sốt, có phải ung thư không?', 'Tôi ho và sốt, có u nang.',
    'Tôi ho và sốt, tôi có bầu không?', 'Tôi ho và sốt, nặng ngực.'])
def test_modifier_fix_does_not_discard_unsupported_health_concepts(engine,text):
    result=engine.handle(text)
    assert result.status != 'extraction_ready'
    assert result.predictions is None


@pytest.mark.parametrize('text', ['Tôi không ho và không sốt nặng.',
    'Tôi chưa chắc có ho và sốt nặng.', 'Nếu tôi ho và sốt nặng thì bị bệnh gì?',
    'bệnh gì gây sốt và ho?', 'Tôi bị bệnh gì?'])
def test_question_tail_does_not_create_confirmed_symptoms(engine,text):
    assert engine.handle(text).status != 'extraction_ready'


def test_urgent_before_modifiers_and_question_suffix(engine):
    result=engine.handle('Tôi buồn nôn, ho, sốt và khó thở nặng thì bị bệnh gì?')
    assert result.status=='urgent_redirect'


def test_http_reported_sentence_keeps_original_evidence(deployment):
    service=get_service(deployment)
    text='tôi bị buồn nôn, ho và sốt nặng'
    with TestClient(create_app(service_loader=lambda:service, chat_factory=legacy_runtime)) as client:
        response=client.post('/api/v1/chat',json={'message':text})
        assert response.status_code==200
        body=response.json()
        assert body['status']=='prediction_ready'
        assert body['symptom_states']=={'nausea':'present','cough':'present','fever':'present'}
        frame=deployment[2].calls[-1]
        assert int(frame.to_numpy().sum())==3 and frame[['nausea','cough','fever']].to_numpy().tolist()==[[1,1,1]]
        session=client.app.state.chat.engine.store.get(body['session_id'])
        assert session.turns[0].text==text
        for spans in session.validated.sidecar(service.catalog)['evidence'].values():
            for span in spans:
                assert text[span['start']:span['end']]==span['text']


@pytest.mark.parametrize('text', ['tôi bị ngứa âm đạo','toi bi ngua am dao'])
def test_supported_vaginal_symptom_not_blocked_as_health(engine,text):
    result=engine.handle(text)
    assert result.status=='clarification_required',result
    assert result.sidecar['states']=={'vaginal itching':'present'}
    assert result.reason=='insufficient'


@pytest.mark.parametrize('feature,text', [
    ('vaginal itching','ngứa âm đạo'), ('vaginal dryness','khô âm đạo'),
    ('vaginal discharge','khí hư'), ('vaginal pain','đau âm đạo'),
    ('vaginal redness','đỏ âm đạo'),
    ('vaginal bleeding after menopause','chảy máu âm đạo sau mãn kinh'),
    ('vulvar irritation','kích ứng âm hộ'), ('vulvar sore','vết loét âm hộ'),
    ('pain during intercourse','đau khi giao hợp'), ('pain in testicles','đau tinh hoàn'),
    ('penis pain','đau dương vật'), ('penile discharge','dịch tiết dương vật'),
    ('itching of scrotum','ngứa bìu'),
])
@pytest.mark.parametrize('accented', [True, False])
def test_genital_aliases_follow_schema_and_keep_evidence(engine,feature,text,accented):
    if not accented:
        text=''.join(c for c in unicodedata.normalize('NFD',text.replace('đ','d'))
                     if not unicodedata.combining(c))
    message='Tôi bị '+text
    result=engine.handle(message)
    assert result.status=='clarification_required',result
    assert result.sidecar['states']=={feature:'present'}
    assert result.predictions is None
    session=engine.store.get(result.session_id)
    turns={turn.turn_id:turn.text for turn in session.turns}
    for spans in result.sidecar['evidence'].values():
        for span in spans:
            assert turns[span['turn_id']][span['start']:span['end']]==span['text']


@pytest.mark.parametrize('text', ['Tôi bị ngứa vùng kín.', 'Tôi bị chảy máu âm đạo.',
    'Tôi bị ho, sốt và ngứa xyz ở âm đạo.'])
def test_unsupported_or_anatomically_ambiguous_is_not_guessed(engine,text):
    result=engine.handle(text)
    assert result.status!='extraction_ready'
    assert result.predictions is None
    assert 'vaginal bleeding after menopause' not in (result.sidecar or {}).get('states',{})


@pytest.mark.parametrize('text,state', [('Tôi không ngứa âm đạo.','denied'),
    ('Tôi có lẽ ngứa âm đạo.','uncertain')])
def test_genital_denial_uncertainty_are_not_confirmed(engine,text,state):
    result=engine.handle(text)
    assert result.status=='clarification_required',result
    assert result.sidecar['states']=={'vaginal itching':state}
    assert result.predictions is None


def test_http_known_genital_symptom_asks_then_accepts_supported_features(deployment):
    service=get_service(deployment)
    with TestClient(create_app(service_loader=lambda:service, chat_factory=legacy_runtime)) as client:
        first=client.post('/api/v1/chat',json={'message':'Tôi bị ngứa âm đạo.'}).json()
        assert first['status']=='clarification_required'
        assert not deployment[2].calls
        second=client.post('/api/v1/chat',json={'session_id':first['session_id'],
            'message':'Tôi bị ngứa âm đạo, ho và sốt.'}).json()
        assert second['status']=='prediction_ready',second
        assert second['symptom_states']=={'vaginal itching':'present','cough':'present','fever':'present'}
        frame=deployment[2].calls[-1]
        assert frame.shape==(1,375)
        assert int(frame.to_numpy().sum())==3
