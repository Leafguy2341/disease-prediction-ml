"""Synthetic numeric/tie contracts, no real weights, training or network."""
from copy import deepcopy
from pathlib import Path
import hashlib,json
import numpy as np
import pytest
from scripts.qualify_web_models import compare_hard_tuned,BASELINE_CASES,HARD_MEMBERS
from src.models.final_evaluation import protocol
from src.agent.extraction import Catalog


@pytest.fixture
def packets(tmp_path):
    frozen=protocol();catalog=Catalog.load(Path(__file__).resolve().parents[1])
    matrix=np.asarray([[int(p=='ALL' or f in p) for f in catalog.features] for _,p in BASELINE_CASES],dtype='uint8')
    members={}
    for name,label in [('logistic_regression',7),('linear_svc',0),('knn',1)]:
        values=np.zeros((8,587));values[:,label]=1
        m=dict(checkpoint=frozen['checkpoints'][HARD_MEMBERS[name]],predict_labels=[label]*8)
        if name=='linear_svc':m['decision_scores']=values.tolist()
        else:m.update(predict_proba=values.tolist(),top3_class_ids=np.argsort(-values,axis=1,kind='stable')[:,:3].tolist())
        members[name]=m
    p=dict(protocol_id='hard-tuned-windows31317-synthetic-v1',kind='original_colab_reference',
        versions=frozen['checkpoints']['lr_tuned_c2']['identity']['versions'],platform_system='Linux',
        ensemble=frozen['ensemble'],phase2_manifest_sha256=frozen['phase2_manifest_sha256'],
        schema_sha256=frozen['processed']['schema_sha256'],features=list(catalog.features),classes=list(catalog.classes),
        cases=json.loads(json.dumps(BASELINE_CASES)),input_sha256=hashlib.sha256(matrix.tobytes()).hexdigest(),
        members=members,hard_vote_labels=[7]*8,tie_rows=8,numeric_rtol=1e-10,numeric_atol=1e-12,
        models_fitted=0,locked_test_opened=False,production_allowlist_changed=False,guards={})
    w=deepcopy(p);w.update(kind='windows_candidate_probe',platform_system='Windows',versions={**p['versions'],'python':'3.13.17'})
    return tmp_path,p,w


def compare(packets):
    folder,p,w=packets;a=folder/'ref.json';b=folder/'win.json'
    a.write_text(json.dumps(p));b.write_text(json.dumps(w))
    return compare_hard_tuned(a,b,hashlib.sha256(a.read_bytes()).hexdigest())


def test_all_member_values_and_priority_ties_without_approval(packets):
    result=compare(packets)
    assert result['status']=='PASS' and result['production_allowlist_changed'] is False
    assert sum(m['values_checked'] for m in result['members'].values())==3*8*587
    assert result['tie_rows']==8 and result['hard_vote_labels']==[7]*8  # LR priority, not smallest ID.


@pytest.mark.parametrize('fault',['numeric','nan','label','top3','tie','vote','priority','member',
    'checkpoint','schema','input','environment','tolerance','fit','locked_test'])
def test_mismatches_fail_closed(packets,fault):
    folder,p,w=packets
    if fault=='numeric':w['members']['linear_svc']['decision_scores'][0][1]=1e-4
    if fault=='nan':w['members']['linear_svc']['decision_scores'][0][1]=float('nan')
    if fault=='label':w['members']['linear_svc']['predict_labels'][0]=3
    if fault=='top3':w['members']['knn']['top3_class_ids'][0]=[2,1,0]
    if fault=='tie':w['tie_rows']=0
    if fault=='vote':w['hard_vote_labels']=[0]*8
    if fault=='priority':w['ensemble']['priority'].reverse()
    if fault=='member':del w['members']['knn']
    if fault=='checkpoint':w['members']['knn']['checkpoint']['files']['pipeline.joblib']['sha256']='0'*64
    if fault=='schema':w['classes'].reverse()
    if fault=='input':w['input_sha256']='0'*64
    if fault=='environment':w['versions']['numpy']='2.4.6'
    if fault=='tolerance':w['numeric_atol']=1.
    if fault=='fit':w['models_fitted']=1
    if fault=='locked_test':w['locked_test_opened']=True
    with pytest.raises(ValueError):compare((folder,p,w))


def test_bad_reference_checksum_rejected(packets):
    folder,p,w=packets;a=folder/'ref.json';b=folder/'win.json'
    a.write_text(json.dumps(p));b.write_text(json.dumps(w))
    with pytest.raises(ValueError,match='checksum'):compare_hard_tuned(a,b,'0'*64)
