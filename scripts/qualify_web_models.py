"""Isolated synthetic checkpoint probe; cannot approve production runtimes.

No CSV, fitting, metric selection or API/LLM calls. Missing original-runtime
references remain NOT VERIFIED even when the candidate pipeline executes.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import platform
import time
import warnings


def run(root, output):
    import numpy as np
    import pandas as pd
    import psutil
    from threadpoolctl import threadpool_limits
    from sklearn.utils.validation import check_is_fitted
    from src.agent.extraction import Catalog
    from src.models.final_evaluation import protocol, versions
    from src.models.training import load_fitted_checkpoint, build_pipeline
    from src.models.ensemble import phase4_guard, hard_vote, HARD, PRIORITY, validate_probabilities
    from app.backend.prediction import _file, _read, PROJECT_ROOT, _runtime_compatible
    from app.backend.models import MEMBERS
    root=root.resolve();output=output.resolve()
    assert not output.is_relative_to(root), 'Evidence output must be outside protected storage'
    frozen=protocol();rows={};models={};raw_probes={};checked={}
    cases=[('zero_boundary',[]),('cough_only',['cough']),('fever_only',['fever']),
        ('cough_fever',['cough','fever']),('gastro',['nausea','vomiting']),('headache_fatigue',['headache','fatigue']),
        ('respiratory',['cough','fever','shortness of breath']),('all_one_boundary','ALL')]
    trained=frozen['checkpoints']['lr_tuned_c2']['identity']['versions']
    assert versions() == {**trained,'python':'3.13.17'} and platform.system()=='Windows', 'Probe only approved Windows candidate environment'
    with ExitStack() as stack:
        guard=stack.enter_context(phase4_guard(root))
        sourceguard=stack.enter_context(phase4_guard(PROJECT_ROOT))
        stack.enter_context(threadpool_limits(limits=1))
        _file(root,'artifacts/metadata/phase2/dataset_manifest.json',{'sha256':frozen['phase2_manifest_sha256']})
        catalog=Catalog.load(PROJECT_ROOT,root)
        x=pd.DataFrame([[int(p=='ALL' or f in p) for f in catalog.features] for _,p in cases],columns=catalog.features,dtype='uint8')
        manifest=_read(_file(root,f"artifacts/metadata/tuning/{frozen['tuning']['experiment_id']}/manifest.json",{'sha256':frozen['tuning']['manifest_sha256']}))
        for key,cp in frozen['checkpoints'].items():
            tick=time.perf_counter();identity=cp['identity'];files=(cp['files'] if key=='lr_baseline' else {
                name:manifest['files'][cp['folder']+'/'+name] for name in ('pipeline.joblib','fit.json','metadata.json')})
            assert identity['versions']==trained
            for relative,digest in identity['source_sha256'].items():_file(PROJECT_ROOT,relative,{'sha256':digest})
            for name,expected in files.items():_file(root,cp['folder']+'/'+name,expected)
            assert files['pipeline.joblib']==cp['files']['pipeline.joblib']
            fit=_read(root/cp['folder']/'fit.json');meta=_read(root/cp['folder']/'metadata.json')
            assert fit['identity']==meta['identity']==identity and fit['n_retained_features']==318
            assert meta['pipeline_sha256']==cp['files']['pipeline.joblib']['sha256']
            assert meta['fit_metadata_sha256']==hashlib.sha256((root/cp['folder']/'fit.json').read_bytes()).hexdigest()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                model=load_fitted_checkpoint(root/cp['folder'],identity,trusted=True)
            expected=build_pipeline(cp['model'],identity['config'])
            assert model.feature_names_in_.tolist()==list(catalog.features) and np.array_equal(model.classes_,np.arange(587))
            assert all(type(a) is type(b) and a.get_params(deep=False)==b.get_params(deep=False) for (_,a),(_,b) in zip(model.steps,expected.steps))
            check_is_fitted(model.named_steps['estimator'])
            assert model.named_steps['variance'].get_support().sum()==318
            models[key]=model
            load_seconds=time.perf_counter()-tick
            tick=time.perf_counter();model.predict(x.iloc[3:4]);warmup=time.perf_counter()-tick
            timings=[]
            for _ in range(10):
                tick=time.perf_counter();model.predict(x.iloc[3:4]);timings.append((time.perf_counter()-tick)*1000)
            labels=model.predict(x);rank=None;proba=None
            if hasattr(model,'predict_proba'):
                proba=np.asarray(model.predict_proba(x));validate_probabilities(proba,8,model.classes_,587)
                rank=np.argsort(-proba,axis=1,kind='stable')[:,:3]
                assert np.array_equal(labels,proba.argmax(axis=1))
            raw_probes[key]=dict(checkpoint_sha256=cp['files']['pipeline.joblib']['sha256'],
                input_sha256=hashlib.sha256(x.to_numpy().tobytes()).hexdigest(),predict_labels=labels.tolist(),
                predict_proba=proba.tolist() if proba is not None else None,top3_class_ids=rank.tolist() if rank is not None else None)
            reference='NOT VERIFIED: no independent original-runtime synthetic reference for this checkpoint'
            if key=='lr_tuned_c2':
                ref=_read(_file(root,'artifacts/metadata/runtime_compatibility/lr-31318-synthetic-reference.json',
                    {'sha256':'5fe06a3637c471403d46cdb87b2e5cce2a742e8fff1c99aa4a6cb7caef53d0dc'}))
                assert ref['checkpoint_sha256']==raw_probes[key]['checkpoint_sha256'] and ref['input_sha256']==raw_probes[key]['input_sha256']
                assert ref['predict_labels']==labels.tolist() and ref['top3_class_ids']==rank.tolist()
                assert np.allclose(proba,np.asarray(ref['predict_proba']),rtol=1e-10,atol=1e-12)
                reference='PASS: all 8x587 probabilities, exact labels and Top3; original Colab reference checksum verified'
            rows[key]=dict(checksum='PASS',pipeline_schema='PASS',synthetic_execution='PASS',
                production_runtime_qualified=_runtime_compatible(cp,versions()),independent_reference=reference,
                load_integrity_seconds=load_seconds,warmup_seconds=warmup,batch1_predict_p50_ms=float(np.percentile(timings,50)),
                batch1_predict_p95_ms=float(np.percentile(timings,95)),process_rss_mib=psutil.Process().memory_info().rss/1024**2,
                checkpoint_sha256=cp['files']['pipeline.joblib']['sha256'],warnings=[type(w.message).__name__ for w in caught])
        ensemble=frozen['ensemble'];_file(PROJECT_ROOT,'src/models/ensemble.py',{'sha256':ensemble['engine_source_sha256']})
        em=_read(_file(root,f"artifacts/metadata/runs/{ensemble['run_id']}/tuned_ensemble_manifest.json",{'sha256':ensemble['manifest_sha256']}))
        assert em['hard'][ensemble['key']]==ensemble['members']==list(HARD[ensemble['key']])
        assert em['hard_tie_priority']==ensemble['priority']==list(PRIORITY)
        def vote(frame):
            return hard_vote({n:models[k].predict(frame) for n,k in MEMBERS.items()},HARD[ensemble['key']],587)
        tick=time.perf_counter();vote(x.iloc[3:4]);warmup=time.perf_counter()-tick;timings=[]
        for _ in range(10):
            tick=time.perf_counter();vote(x.iloc[3:4]);timings.append((time.perf_counter()-tick)*1000)
        labels,ties=vote(x)
        rows['hard_tuned_lr_svc_knn']=dict(policy_checksum='PASS',engine='existing src.models.ensemble.hard_vote',
            independent_reference='NOT VERIFIED: missing original-runtime member synthetic references',
            production_runtime_qualified=False,synthetic_execution='PASS',labels=labels.tolist(),tie_rows=ties,
            warmup_seconds=warmup,batch1_predict_p50_ms=float(np.percentile(timings,50)),batch1_predict_p95_ms=float(np.percentile(timings,95)),
            process_rss_mib=psutil.Process().memory_info().rss/1024**2,ensemble_manifest_sha256=ensemble['manifest_sha256'])
        assert not any(guard.values()) and not any(sourceguard.values())
        packet=dict(status='REVIEW',kind='isolated_windows_candidate_probe_not_approval',versions=versions(),
            cases=cases,rows=rows,probes=raw_probes,probability_rtol=1e-10,probability_atol=1e-12,
            models_fitted=0,locked_test_opened=False,network_calls=0,production_allowlist_changed=False,
            timing_limits='First process load includes integrity, OS cache uncontrolled; ten synthetic batch1 observations; no latency SLA; RSS is a process observation, not peak.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:json.dump(packet,stream,ensure_ascii=False,indent=2)
    print(json.dumps({'status':packet['status'],'rows':rows,'output':str(output)},ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--storage-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.storage_root,args.output)
