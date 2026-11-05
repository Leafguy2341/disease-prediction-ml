"""V2 scoped dialogue, real source dictionaries, synthetic checkpoint; no network."""
from dataclasses import replace
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient
from app.backend.main import create_app
from src.agent.offline import OfflineConversation, OfflineExtractor, OfflinePolicy
from src.agent.conversation import Policy
from test_offline_chat import offline_only
from test_prediction_api import deployment, get_service

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def v2():
    from src.agent.extraction import Catalog
    c=Catalog.load(ROOT)
    return OfflineConversation(c,OfflineExtractor(c,ROOT/'configs/synonyms.json'),Policy(),
                               offline_policy=OfflinePolicy.from_file(ROOT/'configs/phase5b.json'))

def pending(e,r): return e.batch_state(e.store.get(r.session_id))['pending']

def test_context_batch_and_no_premature_prediction(v2):
    r=v2.handle('Tôi bị ngứa âm đạo.')
    p=pending(v2,r)
    assert len(p['items'])==3
    assert all(v2.provider.synonyms[i['feature']]['question_group']=='genital' for i in p['items'])
    b=v2.handle('1 có, 2 không, 3 không rõ',session_id=r.session_id,batch_id=p['batch_id'])
    assert b.status!='extraction_ready'
    assert b.sidecar['states'][p['items'][0]['feature']]=='present'
    assert b.sidecar['states'][p['items'][1]['feature']]=='denied'
    assert b.sidecar['states'][p['items'][2]['feature']]=='uncertain'

def test_partial_answers_preserve_numbers_and_evidence(v2):
    r=v2.handle('Tôi bị ngứa âm đạo.');p=pending(v2,r)
    text='  1 có  '
    b=v2.handle(text,session_id=r.session_id,batch_id=p['batch_id'])
    assert b.status=='clarification_required'
    assert pending(v2,b)['batch_id']==p['batch_id']
    assert pending(v2,b)['items'][1]['state'] is None
    span=b.sidecar['evidence'][p['items'][0]['feature']][0]
    assert text[span['start']:span['end']]==span['text']
    end=v2.handle('2 có, 3 không',session_id=r.session_id,batch_id=p['batch_id'])
    assert end.status=='extraction_ready',end
    assert end.reason=='offline_v2_ready'
    assert len(v2.batch_state(v2.store.get(r.session_id))['answered'])==3

@pytest.mark.parametrize('answer',['có','1 có, 1 không','9 có','1 và 3 có'])
def test_ambiguous_invalid_answers_fail_closed(v2,answer):
    r=v2.handle('Tôi ho.');p=pending(v2,r)
    b=v2.handle(answer,session_id=r.session_id,batch_id=p['batch_id'])
    assert b.status=='clarification_required' and b.predictions is None
    assert all(i['state'] is None for i in p['items'])

def test_old_batch_and_cross_session_rejected(v2):
    a=v2.handle('Tôi ho.');b=v2.handle('Tôi bị ngứa âm đạo.')
    pa=pending(v2,a);pb=pending(v2,b)
    res=v2.handle('1 có',session_id=b.session_id,batch_id=pa['batch_id'])
    assert res.reason=='stale_batch'
    assert all(i['state'] is None for i in pb['items'])
    res=v2.handle('1 có',session_id=b.session_id)
    assert res.reason=='stale_batch'

@pytest.mark.parametrize('size',[1,3,5])
def test_budget_abstains_when_only_one_present(v2,size):
    v2.offline_policy=replace(v2.offline_policy,batch_size=size,max_question_batches=2)
    r=v2.handle('Tôi bị ngứa âm đạo.')
    for _ in range(2):
        p=pending(v2,r)
        r=v2.handle('Không có cái nào.',session_id=r.session_id,batch_id=p['batch_id'])
    assert r.status=='abstained' and r.reason=='offline_v2_insufficient',r

@pytest.mark.parametrize('text',['Tôi đột ngột khó nói.','toi dot ngot kho noi','Tôi khó thở nặng, thở không nổi.'])
def test_urgent_priority_in_batch(v2,text):
    r=v2.handle('Tôi ho.');p=pending(v2,r)
    b=v2.handle(text,session_id=r.session_id,batch_id=p['batch_id'])
    assert b.status=='urgent_redirect'

@pytest.mark.parametrize('text',['Khó nói đột ngột là gì?','Tôi trích dẫn "đột ngột khó nói".'])
def test_knowledge_quote_not_urgent(v2,text):
    assert v2.handle(text).status!='urgent_redirect'

@pytest.mark.parametrize('text',['Tôi cảm thấy khó nói chuyện.','Tôi lo bị ung thư vú.',
    'Tôi thấy có khối bất thường.','Tôi bị đau nhưng không biết đau ở đâu.'])
def test_health_ambiguity_not_unrelated(v2,text):
    r=v2.handle(text)
    assert r.status in {'unsupported_health','clarification_required','abstained'},r
    assert r.predictions is None
    if 'khó nói chuyện' in text:
        assert 'difficulty speaking' not in (r.sidecar or {}).get('states',{})


def test_number_list_only_confirms_listed_items(v2):
    v2.offline_policy=replace(v2.offline_policy,batch_size=5)
    a=v2.handle('Tôi bị ngứa âm đạo.');p=pending(v2,a)
    b=v2.handle('Tôi có 1, 3 và 5.',session_id=a.session_id,batch_id=p['batch_id'])
    assert b.status!='extraction_ready'  # Two unanswered items still pending.
    assert pending(v2,b)['items'][1]['state'] is None
    assert pending(v2,b)['items'][3]['state'] is None
    assert all(b.sidecar['states'][p['items'][i]['feature']]=='present' for i in (0,2,4))


@pytest.mark.parametrize('reply',['Không có cái nào.','Tôi không biết.'])
def test_blanket_reply_after_partial_answer_requires_scope(v2,reply):
    a=v2.handle('Tôi bị ngứa âm đạo.');p=pending(v2,a)
    v2.handle('1 có',session_id=a.session_id,batch_id=p['batch_id'])
    b=v2.handle(reply,session_id=a.session_id,batch_id=p['batch_id'])
    assert b.reason=='ambiguous_batch_answer'
    assert p['items'][0]['state']=='present' and p['items'][1]['state'] is None


def test_invalid_batch_answers_are_bounded_by_user_turn_limit(v2):
    v2.policy=replace(v2.policy,max_user_turns=2)
    a=v2.handle('Tôi ho.');p=pending(v2,a)
    for _ in range(2):
        b=v2.handle('9 có',session_id=a.session_id,batch_id=p['batch_id'])
    assert b.reason=='conversation_limit' and b.status=='abstained'
    assert v2.store.get(a.session_id).ready_frame is None


def test_free_text_answer_syncs_only_explicit_feature(v2):
    a=v2.handle('Tôi bị ngứa âm đạo.');p=pending(v2,a)
    feature=p['items'][0]['feature'];name=p['items'][0]['text']
    b=v2.handle('Tôi không '+name+'.',session_id=a.session_id)
    assert b.status=='clarification_required'
    assert pending(v2,b)['items'][0]['state']=='denied'
    assert all(i['state'] is None for i in pending(v2,b)['items'][1:])
    assert b.sidecar['states'][feature]=='denied'


def test_prediction_can_be_updated_and_wrong_subject_cannot_supply_batch_evidence(v2):
    a=v2.handle('Tôi bị ngứa âm đạo.');p=pending(v2,a)
    b=v2.handle('1 có, 2 có, 3 không',session_id=a.session_id,batch_id=p['batch_id'])
    assert b.status=='extraction_ready'
    later=v2.handle('Tôi ho.',session_id=a.session_id)
    assert later.status=='extraction_ready' and later.sidecar['states']['cough']=='present'
    other=v2.handle('Tôi bị ngứa âm đạo.')
    p=pending(v2,other)
    changed=v2.handle('1 có',session_id=other.session_id,subject_id='mother',batch_id=p['batch_id'])
    assert changed.status!='extraction_ready'


def test_batch_proof_does_not_allow_arbitrary_contract_feature(v2):
    from src.agent.extraction import Turn, ExtractionError
    turn=Turn('u1','user','1 có','self')
    span={'turn_id':'u1','start':0,'end':4,'text':'1 có'}
    data={'contract_version':2,'schema_sha256':v2.catalog.schema_id,
          'present':[{'feature':'cough','evidence':[span]}],'denied':[],'uncertain':[],
          'unmapped':[],'clarification':{'needed':False,'reasons':[],'target_features':[]}}
    with pytest.raises(ExtractionError):
        v2.validator.validate(data,[turn],'self',answer_bindings={'u1':{'fever':{
            'state':'present','evidence':span,'subject_id':'self'}}})

def test_http_registry_modes_reset_and_score_contract(deployment):
    service=get_service(deployment)
    with TestClient(create_app(service_loader=lambda:service)) as client:
        models=client.get('/api/v1/models').json()
        assert models['default_model_id']=='lr_tuned_c2'
        assert len(models['models'])==1 and models['models'][0]['available']
        assert client.post('/api/v1/chat',json={'message':'Tôi ho.','model_id':'knn'}).status_code==422
        assert client.post('/api/v1/chat',json={'message':'Tôi ho.','mode':'llm'}).status_code==409
        first=client.post('/api/v1/chat',json={'message':'Tôi bị ngứa âm đạo.','mode':'offline'}).json()
        p=first['pending_questions'];assert len(p['items'])==3
        ready=client.post('/api/v1/chat',json={'message':'1 có, 2 có, 3 không','session_id':first['session_id'],'batch_id':p['batch_id']}).json()
        assert ready['status']=='prediction_ready',ready
        assert [i['score_percent'] for i in ready['predictions']['top3']]==[40,30,10]
        reset=client.post('/api/v1/chat',json={'reset':True,'session_id':first['session_id']}).json()
        stale=client.post('/api/v1/chat',json={'message':'1 có','session_id':reset['session_id'],'batch_id':p['batch_id']}).json()
        assert stale['status']!='prediction_ready'

def test_dictionary_canonical_and_question_review_scope(v2):
    assert len(v2.provider.synonyms)==375
    assert v2.provider.synonyms['symptoms of infants']['question_eligible'] is False
    assert v2.provider.candidates('đau mắt')=={'pain in eye'}
    assert v2.provider.candidates('ngứa mắt')=={'itchiness of eye'}
    assert v2.provider.candidates('khó nói chuyện')==set()
    names=json.loads((ROOT/'configs/disease_names_vi.json').read_text(encoding='utf-8'))
    assert set(names)==set(v2.catalog.classes)
    assert names['threatened pregnancy']['terminology_status']=='AMBIGUOUS'


def test_explicit_one_feature_preview_preserves_input(v2):
    a=v2.handle('Tôi bị ngứa âm đạo.')
    assert a.status=='clarification_required'
    b=v2.handle('',session_id=a.session_id,action='preview')
    assert b.status=='extraction_ready' and b.reason=='offline_requested_preview',b
    frame=v2.ready_vector(b.session_id,b.turn_id)
    assert frame.shape==(1,375) and int(frame.to_numpy().sum())==1
    assert int(frame['vaginal itching'].iloc[0])==1


@pytest.mark.parametrize('text',['Tôi không ho.','Tôi chưa chắc có ho.','Tôi bị dau co.',
    'Tôi ho và có khối bất thường.'])
def test_preview_cannot_bypass_uncertainty_denial_ambiguity_unknown(v2,text):
    a=v2.handle(text)
    b=v2.handle('',session_id=a.session_id,action='preview')
    assert b.status!='extraction_ready',b
    assert v2.store.get(a.session_id).ready_frame is None


def test_old_validated_state_cannot_preview_after_unmapped_health(v2):
    a=v2.handle('Tôi ho.')
    b=v2.handle('Tôi lo bị ung thư vú.',session_id=a.session_id)
    assert b.status=='unsupported_health'
    for _ in range(2):
        b=v2.handle('',session_id=a.session_id,action='preview')
        assert b.status!='extraction_ready'


def test_new_round_preserves_state_no_repeated_questions_and_is_bounded(v2):
    v2.offline_policy=replace(v2.offline_policy,max_question_batches=1,max_total_questions=3)
    a=v2.handle('Tôi bị ngứa âm đạo.');p=pending(v2,a)
    asked1={i['feature'] for i in p['items']}
    b=v2.handle('Không có cái nào.',session_id=a.session_id,batch_id=p['batch_id'])
    assert b.status=='abstained'
    c=v2.handle('',session_id=a.session_id,action='more');p2=pending(v2,c)
    assert c.status=='clarification_required'
    assert not asked1 & {i['feature'] for i in p2['items']}
    assert c.sidecar['states']['vaginal itching']=='present'
    assert all(c.sidecar['states'][f]=='denied' for f in asked1)
    end=v2.handle('Không có cái nào.',session_id=a.session_id,batch_id=p2['batch_id'])
    assert end.status=='abstained'
    limit=v2.handle('',session_id=a.session_id,action='more')
    assert limit.reason=='question_round_limit'
    assert v2.handle('',session_id=a.session_id,action='preview').status=='extraction_ready'


def test_uncertain_batch_item_can_be_clarified_without_new_features(v2):
    a=v2.handle('Tôi bị ngứa âm đạo.');p=pending(v2,a)
    b=v2.handle('1 không rõ, 2 không, 3 không',session_id=a.session_id,batch_id=p['batch_id'])
    assert b.reason=='offline_resolve_uncertain'
    preview=v2.handle('',session_id=a.session_id,action='preview')
    assert preview.reason=='preview_requires_clarity'
    c=v2.handle('1 có',session_id=a.session_id,batch_id=p['batch_id'])
    assert c.sidecar['states'][p['items'][0]['feature']]=='present',c


def test_urgent_session_cannot_preview(v2):
    a=v2.handle('Tôi ho.');u=v2.handle('Khó thở nặng, thở không nổi.',session_id=a.session_id)
    assert u.status=='urgent_redirect'
    assert v2.handle('',session_id=a.session_id,action='preview').status!='extraction_ready'


def test_review_packet_complete_and_candidates_not_active(v2,tmp_path):
    from scripts.build_synonyms_report import review_rows,write_review_csv
    import csv
    rows=review_rows(ROOT)
    assert [r['canonical_feature'] for r in rows]==list(v2.catalog.features)
    assert len({r['canonical_feature'] for r in rows})==375
    assert all(r['proposed_display_vi'] and json.loads(r['proposed_aliases_vi']) for r in rows)
    assert all(r['needs_review'] for r in rows)
    inactive=[f for f,e in v2.provider.synonyms.items() if e.get('activation_status')=='PENDING_REVIEW']
    from symptom_activation_history import activation_manifest
    assert len(inactive)==240-len(activation_manifest()['activated_features'])
    for f in inactive:
        for alias in v2.provider.synonyms[f]['aliases_vi']:
            assert f not in v2.provider.candidates(alias)
    output=tmp_path/'review.csv';receipt=write_review_csv(ROOT,output)
    assert receipt['rows']==375
    with output.open(encoding='utf-8-sig',newline='') as stream:
        assert len(list(csv.DictReader(stream)))==375


def test_http_controls_low_scores_and_no_features(deployment,monkeypatch):
    service=get_service(deployment)
    original=service.predict
    def low(frame,**kw):
        r=original(frame,**kw)
        for item,score in zip(r['top3'],[4.0,3.0,2.0]):item['score_percent']=score
        return r  # Synthetic fixture only, not an actual-checkpoint metric.
    monkeypatch.setattr(service,'predict',low)
    with TestClient(create_app(service_loader=lambda:service)) as client:
        fresh=client.post('/api/v1/chat',json={'action':'preview'}).json()
        assert fresh['predictions'] is None
        a=client.post('/api/v1/chat',json={'message':'Tôi ho.'}).json()
        b=client.post('/api/v1/chat',json={'session_id':a['session_id'],'action':'preview'}).json()
        assert b['status']=='prediction_ready' and b['reason']=='offline_requested_preview',b
        assert [r['score_percent'] for r in b['predictions']['top3']]==[4.0,3.0,2.0]
        assert b['predictions']['presentation']['confidence_label']=='Điểm tự tin dự đoán (%)'
        assert b['predictions']['presentation']['model_evaluation'] is None  # Synthetic checkpoint not real identity.
        assert b['dialogue']['user_requested_preview']
        assert b['available_actions']==['more','add','preview']


def test_accuracy_reference_bound_to_frozen_evidence_and_checkpoint(v2,tmp_path):
    from src.agent.presentation import PredictionPresenter
    ref=PredictionPresenter.evaluation(ROOT)
    assert ref['accuracy']==0.8440818071688163 and ref['records']==28066
    assert PredictionPresenter.evaluation(tmp_path) is None
    path=tmp_path/'artifacts/metadata/final_evaluation_audit/colab_evidence.json'
    path.parent.mkdir(parents=True);path.write_text('{"accuracy":1.0}')
    assert PredictionPresenter.evaluation(tmp_path) is None
    p=PredictionPresenter(v2.catalog.classes,evaluation_reference=ref)
    value={'model_id':'lr_tuned_c2','checkpoint_sha256':ref['checkpoint_sha256'],
           'top3':[{'class_id':0,'label':v2.catalog.classes[0],'score_percent':4.0}]}
    assert p.render(value)['presentation']['model_evaluation']==ref
    value['checkpoint_sha256']='0'*64
    assert p.render(value)['presentation']['model_evaluation'] is None


@pytest.mark.parametrize('text,feature',[('đau mắt','pain in eye'),('đau mặt','facial pain')])
def test_accented_eye_face_alias_and_unaccented_collision(v2,text,feature):
    r=v2.handle('Tôi bị '+text+'.')
    assert r.sidecar['states']=={feature:'present'}
    collision=v2.handle('Tôi bị dau mat.')
    assert collision.reason=='offline_alias_collision'
    assert collision.predictions is None
