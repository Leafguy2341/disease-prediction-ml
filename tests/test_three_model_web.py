"""Three-model routing/session/display contracts with synthetic services only."""
from copy import copy, deepcopy
from types import SimpleNamespace
import numpy as np
from fastapi.testclient import TestClient
import pytest
from app.backend.main import create_app
from app.backend.models import HardVotingService, HARD_ID, MEMBERS
from app.backend.schemas import HardVoteResponse
from app.backend.prediction import ModelLoadError, LRPredictionService
from src.models.final_evaluation import protocol
from test_prediction_api import deployment, get_service


def extras(tuned):
    baseline=copy(tuned);baseline.model_id='lr_baseline';baseline._tuning_experiment=None
    baseline._checkpoint=protocol()['checkpoints']['lr_baseline']
    members={}
    for i,name in enumerate(MEMBERS):
        members[name]=SimpleNamespace(catalog=tuned.catalog,_model=SimpleNamespace(predict=lambda x,i=i:np.array([i])),
            identity=lambda:{'checkpoint_sha256':'SYNTHETIC_ONLY'},frame_from_features=tuned.frame_from_features)
    return {'lr_baseline':baseline,HARD_ID:HardVotingService(members,protocol())},{}


def test_three_model_http_outputs_and_no_implicit_fallback(deployment):
    tuned=get_service(deployment)
    with TestClient(create_app(service_loader=lambda:tuned,optional_loader=extras)) as client:
        rows=client.get('/api/v1/models').json()
        assert rows['default_model_id']=='lr_tuned_c2'
        assert all(m['available'] for m in rows['models'])
        for key in ('lr_tuned_c2','lr_baseline'):
            reply=client.post('/api/v1/predict',json={'model_id':key,'present_features':['cough']})
            assert reply.status_code==200,reply.text
            assert reply.json()['model_id']==key
            assert sum(r['score_percent'] for r in reply.json()['top3'])==80
        reply=client.post('/api/v1/predict',json={'model_id':HARD_ID,'present_features':['cough']})
        assert reply.status_code==200,reply.text
        body=reply.json();assert 'top3' not in body and 'score_label' not in body
        assert body['hard_vote_result']['tie'] and body['hard_vote_result']['class_id']==0
        assert body['hard_vote_result']['votes']==1
        assert HardVoteResponse.model_validate(body)


def test_blocked_candidate_is_503_without_calling_tuned(deployment):
    tuned=get_service(deployment)
    with TestClient(create_app(service_loader=lambda:tuned)) as client:
        for key in ('lr_baseline',HARD_ID):
            assert client.post('/api/v1/predict',json={'model_id':key,'present_features':['cough']}).status_code==503
            assert client.post('/api/v1/chat',json={'model_id':key,'message':'Tôi ho.'}).status_code==503
        assert not deployment[2].calls
        assert client.post('/api/v1/predict',json={'model_id':'unknown','present_features':['cough']}).status_code==422


def test_switch_requires_reset_and_old_session_is_discarded(deployment):
    tuned=get_service(deployment)
    with TestClient(create_app(service_loader=lambda:tuned,optional_loader=extras)) as client:
        first=client.post('/api/v1/chat',json={'message':'Tôi ho.'}).json()
        sid=first['session_id'];assert first['requested_model_id']=='lr_tuned_c2'
        rejected=client.post('/api/v1/chat',json={'session_id':sid,'model_id':'lr_baseline','message':'Tôi sốt.'})
        assert rejected.status_code==409
        reset=client.post('/api/v1/chat',json={'session_id':sid,'model_id':'lr_baseline','reset':True}).json()
        assert reset['session_id']!=sid and reset['predictions'] is None
        result=client.post('/api/v1/chat',json={'session_id':reset['session_id'],'model_id':'lr_baseline','message':'Tôi ho.'}).json()
        assert result['requested_model_id']=='lr_baseline'
        preview=client.post('/api/v1/chat',json={'session_id':result['session_id'],'model_id':'lr_baseline','action':'preview'}).json()
        assert preview['predictions']['model_id']=='lr_baseline'
        assert preview['processed_model_id']=='lr_baseline'


def test_hard_vote_chat_does_not_claim_top3_or_probabilities(deployment):
    tuned=get_service(deployment)
    with TestClient(create_app(service_loader=lambda:tuned,optional_loader=extras)) as client:
        first=client.post('/api/v1/chat',json={'model_id':HARD_ID,'message':'Tôi ho.'}).json()
        preview=client.post('/api/v1/chat',json={'model_id':HARD_ID,'session_id':first['session_id'],'action':'preview'})
        assert preview.status_code==200,preview.text
        result=preview.json();assert result['status']=='prediction_ready'
        assert result['processed_model_id']==HARD_ID and 'top3' not in result['predictions']
        assert result['state_summary']['top3_display']==[]


def test_windows_guard_still_blocks_other_frozen_weights(monkeypatch):
    from app.backend.prediction import _runtime_compatible
    import app.backend.prediction as module
    p=protocol()
    monkeypatch.setattr(module.platform,'system',lambda:'Windows')
    monkeypatch.setattr(module.platform,'machine',lambda:'AMD64')
    monkeypatch.setattr(module.platform,'python_implementation',lambda:'CPython')
    candidate={**p['checkpoints']['lr_tuned_c2']['identity']['versions'],'python':'3.13.17'}
    for key,cp in p['checkpoints'].items():
        assert _runtime_compatible(cp,candidate)==(key=='lr_tuned_c2')
