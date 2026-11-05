"""Read-only runtime release checks plus a source-only notebook execution-gate freeze.

No packaging, fitting, LLM calls, dataset loading or alias activation.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/release_final_gate'
HISTORY=ROOT/'reports/terminology/activation-20261104'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name,value):
    OUT.mkdir(exist_ok=True)
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def freeze_notebook():
    path=ROOT/'notebooks/06_final_model_evaluation.ipynb'
    before=path.read_bytes();old=json.loads(before);text=before.decode('utf-8')
    for cell in old['cells']:
        if cell['cell_type']!='code':continue
        for line in cell['source']:
            replacement=None
            if line.startswith('RUN_FINAL_LOCKED_TEST = True'):
                replacement=line.replace('RUN_FINAL_LOCKED_TEST = True','RUN_FINAL_LOCKED_TEST = False',1)
            elif line.startswith('OWNER_AUTHORIZATION = ') and 'AUTHORIZE ONE-TIME LOCKED TEST' in line:
                replacement='OWNER_AUTHORIZATION = ""'+ ('\n' if line.endswith('\n') else '')
            if replacement is not None:
                encoded=json.dumps(line,ensure_ascii=False)
                assert text.count(encoded)==1, 'Ambiguous source replacement'
                text=text.replace(encoded,json.dumps(replacement,ensure_ascii=False),1)
    new=json.loads(text)
    assert [(c.get('outputs'),c.get('execution_count')) for c in old['cells']]==[(c.get('outputs'),c.get('execution_count')) for c in new['cells']]
    changed=[i for i,(a,b) in enumerate(zip(old['cells'],new['cells'])) if a!=b]
    assert changed==[8], changed
    path.write_bytes(text.encode('utf-8'))
    save('notebook06_gate_freeze.json',dict(before_sha256=hashlib.sha256(before).hexdigest(),
        after_sha256=sha(path),changed_cells=changed,outputs_and_counts_unchanged=True,
        enabled=False,owner_authorization_empty=True,notebook_executed=False))


def log_sections(path):
    text=path.read_text(encoding='utf-8')
    all_headers=list(re.finditer(r'(?m)^_+ ([^\r\n]+?) _+[ \t]*\r?$',text))
    headers=[m for m in all_headers if m[1].startswith(('test_','ERROR at setup of test_'))]
    parts={}
    for i,m in enumerate(headers):
        end=headers[i+1].start() if i+1<len(headers) else text.find('=== warnings summary',m.end())
        if end<0:end=len(text)
        body=text[m.end():end].split('---------------------------- Captured stdout')[0]
        parts[m[1].removeprefix('ERROR at setup of ')]=dict(body=body,
            start_line=text.count('\n',0,m.start())+1,end_line=text.count('\n',0,end)+1)
    ids=[line.split(' ',1)[1] for line in text.splitlines() if line.startswith(('FAILED tests/','ERROR tests/'))]
    assert len(ids)==34 and len(parts)==34,(len(ids),len(parts))
    return text,parts,ids


def normalize(text):
    text=re.sub(r'pytest-\d+','pytest-RUN',text)
    text=re.sub(r'0x[0-9A-Fa-f]+','0xADDRESS',text)
    return text


def triage():
    _,first,ids=log_sections(HISTORY/'batch-1.tests.txt')
    _,second,ids2=log_sections(HISTORY/'baseline.tests.txt')
    assert ids==ids2
    rows=[]
    for test_id in ids:
        key=test_id.split('::')[-1];a,b=first[key],second[key]
        def trace(part):
            return '\n'.join(l for l in part['body'].splitlines() if l.startswith('E ') or re.match(r'^(?:tests|scripts|src|app)[\\/].+:\d+:',l))
        ta,tb=normalize(trace(a)),normalize(trace(b))
        body=b['body']
        errors=[l.strip() for l in body.splitlines() if l.startswith('E ') and re.search(r'Error|Exception|StopIteration|assert ',l)]
        cls='OPTIONAL';impact='Không nằm trong đường chạy website offline/predict hiện hành.'
        if "No module named 'nbformat'" in body:
            scope='Notebook generator / fixtures'
            cause='Import scripts/build_notebooks.py:8 thiếu nbformat trong interpreter test Python3.11; setup lỗi trước assertion.'
            cls='ENVIRONMENT'
        elif 'random_forest' in key:
            scope='Training RandomForest synthetic fixture'
            cause='joblib/multiprocessing dùng Windows named pipe; _winapi.CreateFile phát sinh PermissionError WinError5. Không phải load LR đã fit.'
            cls='ENVIRONMENT'
        elif 'allowlist_has_no' in key:
            scope='Source publication inventory'
            cause='Test assert payload count45, make_publication thực47; các assertion allowlist/security trước đó đã đi qua. Số47 cần đối chiếu inventory theo nội dung.'
        elif 'test_manifest_deployment.py' in test_id:
            scope='Source staging PowerShell fixture'
            cause='editing_project chỉ copy prepare_colab_source.ps1, không copy package_handover.py mà helper hiện gọi; subprocess exit2 (file not found).'
        elif 'compact_notebook_interface' in key:
            scope='Notebook03 historical baseline teaching fixture'
            cause='Test exec mọi code cell sau setup; notebook chủ ý bật tuning, synthetic7features/ít lớp bị baseline.verify() chặn trước tuning. Không fit tuning hoặc đọc test thật.'
        elif 'protocol_evidence_and_notebook_gate' in key:
            scope='Notebook06 execution authorization'
            cause='Notebook06 lưu RUN_FINAL_LOCKED_TEST=True và authorization text. Đây là unsafe release default thật; gate đã được đặt False và authorization rỗng, giữ output.'
            cls='BLOCKER';impact='Không ảnh hưởng API nhưng chặn phát hành notebook an toàn. Đã sửa mặc định source, cần kiểm receipt.'
        elif 'closeout_notebook_blocks' in key:
            scope='Notebook06 closeout guard'
            cause='Test tìm cell có RuntimeError+read_completed nhưng không còn cell dạng đó; StopIteration. Source chưa thể hiện closeout-only guard mà test yêu cầu.'
            cls='BLOCKER';impact='Không ảnh hưởng local web; bảo vệ RunAll notebook06 chưa được xác minh đầy đủ. Không chạy notebook để chứng minh.'
        elif "No module named 'google.colab'" in body:
            scope='Colab smoke notebook fixture'
            cause='Notebook smoke có cell import google.colab; harness Windows không mock module này/không giới hạn setup cells. ImportError trước điều kiện giả lập.'
            cls='ENVIRONMENT'
        elif 'Preparation must not evaluate/train/predict' in body:
            scope='Notebook06 preparation / evaluation gate'
            cause='Harness chạy cell đánh giá vì gate trong source=True; stub evaluate cố ý ném AssertionError trước mọi payload. Unsafe default đã sửa, không thay assertion.'
            cls='BLOCKER';impact='Chặn phát hành notebook trước safe-default fix; không chứng minh test thật đã bị mở trong regression.'
        elif 'preflight' in body and 'BLOCKED:' in body:
            scope='Notebook06 synthetic prerequisite/closeout harness'
            cause='Source raise RuntimeError khi PREFLIGHT_OK=False; harness execute toàn notebook không bắt fail-closed exception. Không đạt stage mà assertion cuối mong đợi.'
        else:raise AssertionError('Unclassified failure '+test_id)
        frames=[l for l in trace(b).splitlines() if not l.startswith('E ')]
        row=dict(test_id=test_id,scope=scope,exception=' | '.join(errors)[:1600],
            traceback_frames=' | '.join(frames),reproduced_after_rollback=True,
            normalized_exception_and_frames_equivalent=ta==tb,
            full_trace_context_equivalent=normalize(a['body'])==normalize(b['body']),
            before_log_lines=[a['start_line'],a['end_line']],after_log_lines=[b['start_line'],b['end_line']],
            normalized_before_trace_sha256=hashlib.sha256(ta.encode()).hexdigest(),
            normalized_after_trace_sha256=hashlib.sha256(tb.encode()).hexdigest(),
            root_cause=cause,website_impact=impact,classification=cls)
        rows.append(row)
    save('regression_triage.json',dict(log_sha256={n:sha(HISTORY/n) for n in ['batch-1.tests.txt','baseline.tests.txt']},
        normalization='Only pytest run directory numbers and Python object memory addresses; compare exception lines + source frames separately from full context.',tests=rows))
    with (OUT/'regression_triage.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(tests=len(rows),non_equivalent_traces=[r['test_id'] for r in rows if not r['normalized_exception_and_frames_equivalent']])))


def smoke():
    """Actual checkpoint, in-process HTTP and loopback TCP; fictional inputs only."""
    import socket
    import http.client
    import threading
    import time
    from unittest.mock import patch
    import numpy as np
    import pandas as pd
    from fastapi.testclient import TestClient
    from app.backend.main import create_app
    from app.backend.prediction import LRPredictionService
    from src.models.ensemble import phase4_guard
    from src.models.training import sha256_file
    from src.agent import provider
    from sklearn.pipeline import Pipeline
    from sklearn.feature_selection import VarianceThreshold
    from sklearn.linear_model import LogisticRegression
    from contextlib import ExitStack
    import uvicorn

    environment=dict(os.environ)
    blocked=dict(outbound_network_attempts=0,llm_calls=0,fit_attempts=0)
    original_connect=socket.socket.connect
    def connect(sock,address):
        if not isinstance(address,tuple) or address[0] not in {'127.0.0.1','::1'}:
            blocked['outbound_network_attempts']+=1
            raise AssertionError('Outbound network forbidden')
        return original_connect(sock,address)
    def no_llm(*a,**k):
        blocked['llm_calls']+=1
        raise AssertionError('Offline release smoke must not call an LLM')
    def no_fit(*a,**k):
        blocked['fit_attempts']+=1
        raise AssertionError('Release smoke must not fit')
    endpoints=[]
    server=None;thread=None;listener=None
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ,{'DISEASE_CHAT_MODE':'offline','DISEASE_API_STORAGE_ROOT':str(ROOT)}))
        stack.enter_context(patch.object(socket.socket,'connect',connect))
        for name in ('_post','_post_groq','_post_openrouter','create_provider'):
            stack.enter_context(patch.object(provider,name,no_llm))
        for klass in (Pipeline,VarianceThreshold,LogisticRegression):
            stack.enter_context(patch.object(klass,'fit',no_fit))
        guard=stack.enter_context(phase4_guard(ROOT))
        service=LRPredictionService.load(ROOT)
        assert service.verification=='REAL CHECKPOINT VERIFIED'
        model=service._model
        assert model.named_steps['estimator'].C==2
        assert model.named_steps['estimator'].coef_.shape==(587,318)
        assert len(service.catalog.features)==375 and len(service.catalog.classes)==587
        reference_path=ROOT/'artifacts/metadata/runtime_compatibility/lr-31318-synthetic-reference.json'
        assert sha(reference_path)=='5fe06a3637c471403d46cdb87b2e5cce2a742e8fff1c99aa4a6cb7caef53d0dc'
        reference=json.loads(reference_path.read_text(encoding='utf-8'))
        x=pd.DataFrame([[int(c['present']=='ALL' or f in c['present']) for f in service.catalog.features]
                        for c in reference['cases']],columns=service.catalog.features,dtype='uint8')
        from threadpoolctl import threadpool_limits
        with threadpool_limits(limits=1):
            proba=model.predict_proba(x);labels=model.predict(x)
        expected=np.asarray(reference['predict_proba'])
        assert proba.shape==(8,587) and np.allclose(proba,expected,rtol=1e-10,atol=1e-12)
        assert labels.tolist()==reference['predict_labels']
        assert np.argsort(-proba,axis=1,kind='stable')[:,:3].tolist()==reference['top3_class_ids']
        assert [[service.catalog.classes[i] for i in row] for row in np.argsort(-proba,axis=1,kind='stable')[:,:3]]==reference['top3_labels']
        app=create_app(service_loader=lambda:service)
        with TestClient(app) as client:
            def request(method,path,payload=None):
                r=client.request(method,path,json=payload) if payload is not None else client.request(method,path)
                endpoints.append(dict(method=method,path=path,http_status=r.status_code))
                return r
            health=request('GET','/health');assert health.status_code==200,health.text
            assert health.json()['chat']['mode']=='offline',health.json()
            pred=request('POST','/api/v1/predict',{'present_features':['cough','fever']})
            assert pred.status_code==200,pred.text
            assert pred.json()['checkpoint_sha256']==service.identity()['checkpoint_sha256']
            assert len(pred.json()['top3'])==3 and pred.json()['calibrated'] is False
            index=next(i for i,c in enumerate(reference['cases']) if c['id']=='cough_fever')
            rank=np.argsort(-proba[index],kind='stable')[:3]
            assert [r['class_id'] for r in pred.json()['top3']]==rank.tolist()
            assert np.allclose([r['score_percent'] for r in pred.json()['top3']],proba[index,rank]*100,rtol=1e-10,atol=1e-12)
            def chat(payload):
                r=request('POST','/api/v1/chat',payload);assert r.status_code==200,r.text
                return r.json()
            first=chat({'message':'Tôi bị ngứa âm đạo.'})
            assert first['predictions'] is None and first['status']=='clarification_required'
            pending=first['pending_questions'];assert len(pending['items'])==3
            answered=chat({'message':'1 có, 2 có, 3 không','session_id':first['session_id'],'batch_id':pending['batch_id']})
            assert answered['status']=='prediction_ready' and answered['predictions'],answered
            for i,state in enumerate(['present','present','denied']):
                assert answered['symptom_states'][pending['items'][i]['feature']]==state
            start=chat({'message':'Tôi bị ngứa âm đạo.'})
            preview=chat({'session_id':start['session_id'],'action':'preview'})
            assert preview['status']=='prediction_ready' and preview['reason']=='offline_requested_preview',preview
            reset=chat({'session_id':start['session_id'],'reset':True})
            assert reset['status']=='new_session' and not reset['symptom_states'] and reset['predictions'] is None
            negatives=[]
            for text in ['Tôi không ho.','Tôi chưa chắc có ho.','Tôi bị dau co.',
                         'Tôi ho và có khối bất thường.','Khó thở nặng, thở không nổi.',
                         'Giả sử tôi ho và sốt thì sao?','Mẹ tôi ho và sốt.',
                         'Nhân vật trong truyện bị ho và sốt.']:
                state=chat({'message':text})
                assert state['predictions'] is None,state
                after=chat({'session_id':state['session_id'],'action':'preview'})
                assert after['predictions'] is None,after
                negatives.append(dict(synthetic_text=text,status=state['status'],reason=state['reason'],preview_reason=after['reason']))
            invalid=request('POST','/api/v1/predict',{'present_features':['not-a-feature']})
            assert invalid.status_code==422
            assert request('GET','/').status_code==200
            for path in ['/static/app.js','/static/styles.css','/openapi.json']:
                assert request('GET',path).status_code==200
        # Real TCP HTTP; bind port0 so an existing user's 8000 process is untouched.
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(32)
        port=listener.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,workers=1,log_level='error',access_log=False))
        thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True)
        try:
            thread.start();deadline=time.monotonic()+15
            while not server.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.02)
            assert server.started, 'Actual Uvicorn startup failed'
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=15)
            conn.request('GET','/health');r=conn.getresponse();assert r.status==200
            tcp_health=json.loads(r.read());assert tcp_health['checkpoint_status']=='REAL CHECKPOINT VERIFIED'
            conn.request('POST','/api/v1/predict',body=json.dumps({'present_features':['cough','fever']}),headers={'Content-Type':'application/json'})
            r=conn.getresponse();assert r.status==200
            tcp_prediction=json.loads(r.read());assert tcp_prediction['top3']==pred.json()['top3']
            conn.close()
        finally:
            server.should_exit=True
            if thread:thread.join(timeout=15)
            listener.close()
        assert not any(blocked.values()) and not any(guard.values()),(blocked,guard)
        result=dict(status='PASS',checkpoint='REAL CHECKPOINT VERIFIED',health=health.json(),
            identity=service.identity(),features=375,retained_features=318,classes=587,
            reference_comparison=dict(cases=8,probabilities=4696,rtol=1e-10,atol=1e-12,
                max_abs_difference=float(np.max(np.abs(proba-expected))),labels_and_top3_exact=True),
            endpoints=endpoints,real_tcp_http=dict(health=200,predict=200,loopback_only=True,ephemeral_port=port),
            batch_questions='PASS',requested_preview='PASS',negative_gates=negatives,
            guard_counts=dict(guard),network_and_fit_counts=blocked,models_fitted=0,test_payload_opened=False,
            synthetic_only=True,score_not_renormalized=True,production_synonyms_sha256=sha(ROOT/'configs/synonyms.json'))
        from src.models.final_evaluation import versions
        import platform
        result['actual_versions']=versions()
        result['actual_system']=platform.system()
        from scripts.package_handover import secret_check
        rendered=json.dumps(result,ensure_ascii=False).encode('utf-8')
        secret_check('release-smoke-response',rendered)
        assert all(v.encode() not in rendered for k,v in os.environ.items() if k.endswith('API_KEY') and len(v)>=12)
        result['response_credential_check']='PASS (known patterns and configured API-key values; no values retained)'
    save('real_runtime_smoke.json',result)
    print(json.dumps(dict(status='PASS',checkpoint=result['checkpoint'],tcp_http=result['real_tcp_http'],reference=result['reference_comparison'])))


def candidate_contexts():
    """Final candidate check in a temp dictionary, never activate production."""
    import tempfile
    from collections import Counter
    from scripts.activate_reviewed_symptoms import qualified_dictionary,run_cases
    from scripts.review_symptom_activation import engine_for
    from src.agent.extraction import Catalog
    from src.models.ensemble import phase4_guard
    baseline=json.loads((HISTORY/'synonyms.before.json').read_text(encoding='utf-8'))
    release=json.loads((HISTORY/'manifest.json').read_text(encoding='utf-8'))
    config=ROOT/'configs/synonyms.json';before=sha(config)
    assert before==release['before_sha256']
    features=release['qualified_features']
    assert len(features)==127 and 'delusions or hallucinations' not in features
    cases=[]
    for f in features:
        for alias in baseline[f]['proposed_aliases_vi']:
            for kind,text in [
                ('fiction','Nhân vật trong truyện bị '+alias+'.'),
                ('third_person','Anh ấy bị '+alias+'.'),
                ('friend','Bạn tôi bị '+alias+'.'),
                ('hypothetical','Nếu tôi bị '+alias+' thì sao?'),
                ('knowledge','Tôi muốn hỏi '+alias+' có nghĩa gì?'),
            ]:
                cases.append(dict(id='final-context-'+str(len(cases)+1).zfill(4),feature=f,alias=alias,
                    kind=kind,text=text,expected_states={},expected_no_prediction=True))
    with phase4_guard(ROOT) as guard,tempfile.TemporaryDirectory(prefix='release-context-') as tmp:
        engine=engine_for(Catalog.load(ROOT),qualified_dictionary(baseline,features),Path(tmp)/'candidate.json')
        results=run_cases(engine,cases)
        original=[json.loads(l) for l in (ROOT/'data/evaluation/vietnamese_symptom_semantic_cases.jsonl').read_text(encoding='utf-8').splitlines()]
        production=engine_for(Catalog.load(ROOT),baseline,Path(tmp)/'production.json')
        original_results=run_cases(production,original)
        assert len(original_results)==86 and all(r['passed'] for r in original_results)
        assert not any(guard.values()) and sha(config)==before
    failed=[r for r in results if not r['passed']]
    summary=dict(status='CANDIDATE_REJECTED' if failed else 'CANDIDATE_CONTEXT_PASS',
        cases=len(cases),passed=sum(r['passed'] for r in results),failed=len(failed),
        failure_kinds=dict(Counter(r['kind'] for r in failed)),
        affected_features=len({r['feature'] for r in failed}),
        affected_aliases=len({(c['feature'],c['alias']) for c,r in zip(cases,results) if not r['passed']}),
        original_semantic_cases_passed=86,production_unchanged=True,production_sha256=before,
        retained_new_features=0,active_features=135,pending_features=240,
        production_activation_attempted=False,guard_counts=dict(guard),models_fitted=0,predictions_called=False,
        test_payload_opened=False,limitation='Fixture failures show incorrect states even if unmapped gate still blocks inference; no guard changes authorized to force PASS.')
    save('candidate_contexts.json',dict(summary=summary,cases=cases,results=results,original_semantic_results=original_results))
    print(json.dumps(summary))


def inventory():
    """Freeze relative names/hashes only. Do not invoke ZIP/data verification."""
    from scripts.package_handover import code_files,secret_check,runtime_api
    from src.models.final_evaluation import protocol
    from pathlib import PurePosixPath
    selected=code_files(ROOT)  # Existing allowlist and credential scanner, no archive.
    supplemental=set()
    for folder in ('reports/terminology','reports/release_final_gate'):
        supplemental.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file())
    supplemental.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'data/evaluation').glob('vietnamese_symptom_*cases.jsonl'))
    supplemental.difference_update({n for n in supplemental if n.endswith('packaging_artifact_manifest.json')})
    missing_from_allowlist=sorted(supplemental-set(selected))
    files=dict(selected)
    files.update({n:ROOT/n for n in supplemental})
    def record(p):return dict(bytes=p.stat().st_size,sha256=sha(p))
    for name,path in files.items():
        assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
        assert path.resolve().is_relative_to(ROOT) and not path.is_symlink()
        secret_check(name,path.read_bytes())
    payloads,publication=runtime_api(ROOT)['make_publication'](ROOT)
    assert len(payloads)==47
    assert not any(n.startswith(('data/','artifacts/','reports/')) for n in payloads)
    frozen=protocol();cp=frozen['checkpoints']['lr_tuned_c2'];ti=frozen['tuning']
    deployment={}
    for name in ['artifacts/metadata/phase2/dataset_manifest.json','artifacts/metadata/phase2/feature_schema.json',
        'artifacts/metadata/phase2/label_mapping.json',f"artifacts/metadata/tuning/{ti['experiment_id']}/manifest.json",
        *[cp['folder']+'/'+n for n in ('pipeline.joblib','fit.json','metadata.json')]]:
        deployment[name]=record(ROOT/name)
    assert len(deployment)==7 and deployment[cp['folder']+'/pipeline.joblib']['sha256']==cp['files']['pipeline.joblib']['sha256']
    req=json.loads((ROOT/'configs/handover_data_requirements.json').read_text(encoding='utf-8'))
    expected_paths=set(req['baseline_files'])|set(req['phase2_files'])|set(req['manifests'])|set(req['evidence_files'])
    expected_paths.add('data/raw/'+req['raw']['filename'])
    expected_paths.add('artifacts/metadata/phase2/dataset_manifest.json')
    for model in req['model_names']:
        expected_paths.update(f"artifacts/models/tuning/{req['tuning_id']}/{model}/{n}" for n in ('pipeline.joblib','fit.json','metadata.json','validation_predictions.npz'))
    source_config={n:record(p) for n,p in files.items() if n.startswith(('src/','app/','configs/'))}
    freeze_sha=hashlib.sha256(json.dumps(source_config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    result=dict(status='BLOCKER',local_offline_demo='RELEASE_READY',coverage=dict(active=135,pending=240,newly_activated=0),
        source_config_sha256=freeze_sha,source_config_files=source_config,
        code_package_files={n:record(p) for n,p in sorted(files.items())},
        existing_packager_selected_count=len(selected),required_supplemental_files_omitted_by_current_packager=missing_from_allowlist,
        packaging_blocker='Current code_files allowlist omits terminology/evaluation fixtures required by shipped tests; this manifest enumerates them, but the packager was NOT changed or executed.',
        approved_lr_local_deployment_files=deployment,
        data_package_expected_paths_only=sorted(expected_paths),
        data_package_requirements_sha256=sha(ROOT/'configs/handover_data_requirements.json'),
        data_package_canonical_root='/content/drive/MyDrive/ML_Projects/disease-prediction-ml',
        data_package_verification='NOT VERIFIED in this task; expected inventory from pinned requirements only, no Drive access or dataset hashing',
        runtime_publication=dict(files=len(payloads),sha256=publication['sha256'],published=False,drive_sync_verified=False),
        portable_relative_members=True,secrets_known_pattern_scan='PASS',secrets_scope='Allowlisted source and listed supplemental evidence only; no environment key values collected',
        excludes=['.venv','.venv-web','.env','credentials','caches','dist','local runtime paths'],
        test_payload_opened=False,models_fitted=0,llm_requests=0,zip_created=False)
    save('packaging_artifact_manifest.json',result)
    print(json.dumps(dict(status=result['status'],local_demo=result['local_offline_demo'],code_files=len(files),
        supplemental_files=len(missing_from_allowlist),source_config_sha256=freeze_sha,secret_scan='PASS')))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['triage','freeze','smoke','contexts','inventory'])
    args=parser.parse_args()
    {'triage':triage,'freeze':freeze_notebook,'smoke':smoke,'contexts':candidate_contexts,'inventory':inventory}[args.stage]()


if __name__=='__main__':main()
