"""Synthetic comparison mechanics; passing these does not approve real runtimes."""
import hashlib,json
from copy import deepcopy
import numpy as np
import pytest
from scripts.qualify_web_models import compare_baseline,BASELINE_CASES
from src.agent.extraction import Catalog
from src.models.final_evaluation import protocol
from pathlib import Path


@pytest.fixture
def packets(tmp_path):
    cp=protocol()['checkpoints']['lr_baseline'];catalog=Catalog.load(Path(__file__).resolve().parents[1])
    p=dict(protocol_id='lr-baseline-windows31317-v1',kind='original_colab_reference',
        schema_sha256=catalog.schema_id,checkpoint_sha256=cp['files']['pipeline.joblib']['sha256'],identity=cp['identity'],
        feature_count=375,retained_features=318,class_count=587,features=list(catalog.features),classes=list(catalog.classes),
        cases=json.loads(json.dumps(BASELINE_CASES)),input_sha256=hashlib.sha256(np.asarray([[int(p=='ALL' or f in p) for f in catalog.features] for _,p in BASELINE_CASES],dtype='uint8').tobytes()).hexdigest(),probability_rtol=1e-10,probability_atol=1e-12,
        versions=cp['identity']['versions'],platform_system='Linux',predict_labels=[0]*8,top3_class_ids=[[0,1,2]]*8,
        predict_proba=np.full((8,587),1/587).tolist(),guards={},models_fitted=0,locked_test_opened=False)
    w=deepcopy(p);w.update(kind='windows_candidate_probe',platform_system='Windows',versions={**p['versions'],'python':'3.13.17'})
    return tmp_path,p,w


def compare(packets):
    folder,p,w=packets;a=folder/'reference.json';b=folder/'candidate.json'
    a.write_text(json.dumps(p));b.write_text(json.dumps(w))
    return compare_baseline(a,b,hashlib.sha256(a.read_bytes()).hexdigest())


def test_all_probabilities_labels_and_top3_compared_without_approval_side_effect(packets):
    r=compare(packets)
    assert r['status']=='PASS' and r['probabilities_checked']==4696
    assert r['production_allowlist_changed'] is False


@pytest.mark.parametrize('change',['probability','label','top3','checkpoint','schema','environment','tolerance'])
def test_mismatch_never_approves(packets,change):
    folder,p,w=packets
    if change=='probability':w['predict_proba'][0][0]+=.01;w['predict_proba'][0][1]-=.01
    if change=='label':w['predict_labels'][0]=1
    if change=='top3':w['top3_class_ids'][0]=[0,1,3]
    if change=='checkpoint':w['checkpoint_sha256']='wrong'
    if change=='schema':w['features'][0]='unknown'
    if change=='environment':w['versions']['sklearn']='1.8.0'
    if change=='tolerance':w['probability_atol']=1
    with pytest.raises(ValueError):compare((folder,p,w))


def test_missing_or_wrong_reference_checksum_fails(packets):
    folder,p,w=packets;a=folder/'r.json';b=folder/'w.json';a.write_text(json.dumps(p));b.write_text(json.dumps(w))
    with pytest.raises(ValueError,match='checksum'):compare_baseline(a,b,'0'*64)
