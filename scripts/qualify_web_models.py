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

BASELINE_CASES=[('zero_boundary',[]),('cough_only',['cough']),('fever_only',['fever']),
    ('cough_fever',['cough','fever']),('gastro',['nausea','vomiting']),
    ('headache_fatigue',['headache','fatigue']),('respiratory',['cough','fever','shortness of breath']),('all_one_boundary','ALL')]


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


def baseline_probe(root, output, *, original_reference=False):
    """LR baseline only, isolated from API guards; never SVC/KNN/ensemble or data CSV."""
    import numpy as np
    import pandas as pd
    from threadpoolctl import threadpool_limits
    from src.models.final_evaluation import protocol, versions
    from src.models.training import load_fitted_checkpoint, build_pipeline
    from src.models.ensemble import phase4_guard, validate_probabilities
    from src.agent.extraction import Catalog
    from app.backend.prediction import PROJECT_ROOT, _file, _read
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists() or output.is_relative_to(root):raise ValueError('Use a new output path outside protected storage')
    frozen=protocol();cp=frozen['checkpoints']['lr_baseline'];identity=cp['identity']
    current=versions();expected=dict(identity['versions'])
    if original_reference:
        if current!=expected or platform.system()!='Linux':raise ValueError('Original reference requires exact trained Linux versions')
        import google.colab  # Reject a plain Linux candidate as a Colab original reference.
    else:
        expected['python']='3.13.17'
        if current!=expected or platform.system()!='Windows':raise ValueError('Windows candidate requires pinned 3.13.17/ML versions')
    cases=BASELINE_CASES
    with phase4_guard(root) as guard,threadpool_limits(limits=1):
        _file(root,'artifacts/metadata/phase2/dataset_manifest.json',{'sha256':frozen['phase2_manifest_sha256']})
        for name,value in identity['source_sha256'].items():_file(PROJECT_ROOT,name,{'sha256':value})
        catalog=Catalog.load(PROJECT_ROOT,root)
        for name in ('pipeline.joblib','fit.json','metadata.json'):_file(root,cp['folder']+'/'+name,cp['files'][name])
        fit=_read(root/cp['folder']/'fit.json');meta=_read(root/cp['folder']/'metadata.json')
        if fit['identity']!=identity or meta['identity']!=identity:raise ValueError('Baseline identity mismatch')
        model=load_fitted_checkpoint(root/cp['folder'],identity,trusted=True)
        blueprint=build_pipeline(cp['model'],identity['config'])
        if [(n,type(s),s.get_params(deep=False)) for n,s in model.steps]!=[(n,type(s),s.get_params(deep=False)) for n,s in blueprint.steps]:raise ValueError('Pipeline/config mismatch')
        if model.feature_names_in_.tolist()!=list(catalog.features) or not np.array_equal(model.classes_,np.arange(587)):raise ValueError('Schema/class mapping mismatch')
        if model.named_steps['variance'].get_support().sum()!=318:raise ValueError('Fitted preprocessing mismatch')
        x=pd.DataFrame([[int(p=='ALL' or f in p) for f in catalog.features] for _,p in cases],columns=catalog.features,dtype='uint8')
        proba=np.asarray(model.predict_proba(x),dtype=np.float64);labels=model.predict(x)
        validate_probabilities(proba,8,model.classes_,587)
        if not np.array_equal(labels,proba.argmax(axis=1)):raise ValueError('Prediction/probability mismatch')
        rank=np.argsort(-proba,axis=1,kind='stable')[:,:3]
        packet=dict(protocol_id='lr-baseline-windows31317-v1',
            kind='original_colab_reference' if original_reference else 'windows_candidate_probe',
            versions=current,platform_system=platform.system(),schema_sha256=catalog.schema_id,
            checkpoint_sha256=cp['files']['pipeline.joblib']['sha256'],identity=identity,
            feature_count=375,retained_features=318,class_count=587,
            features=list(catalog.features),classes=list(catalog.classes),cases=cases,
            input_sha256=hashlib.sha256(x.to_numpy().tobytes()).hexdigest(),
            predict_labels=labels.tolist(),top3_class_ids=rank.tolist(),predict_proba=proba.tolist(),
            probability_rtol=1e-10,probability_atol=1e-12,
            models_fitted=0,locked_test_opened=False,guards=dict(guard),production_allowlist_changed=False)
        if any(guard.values()):raise ValueError('Forbidden operation observed')
    output.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(packet,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    with output.open('xb') as stream:stream.write(raw)
    print(json.dumps(dict(kind=packet['kind'],output=str(output),sha256=hashlib.sha256(raw).hexdigest(),
        status='REFERENCE GENERATED' if original_reference else 'CANDIDATE EXECUTION PASS; REFERENCE COMPARISON PENDING'),ensure_ascii=False))
    return packet


def compare_baseline(reference, candidate, expected_reference_sha256):
    """Verify the user-confirmed Colab hash and all 8x587 probabilities; no approval side effects."""
    import numpy as np
    from src.models.final_evaluation import protocol
    from src.agent.extraction import Catalog
    from src.models.ensemble import validate_probabilities
    raw=Path(reference).read_bytes()
    if len(expected_reference_sha256)!=64 or hashlib.sha256(raw).hexdigest()!=expected_reference_sha256:raise ValueError('Reference checksum mismatch')
    ref=json.loads(raw);win=json.loads(Path(candidate).read_text(encoding='utf-8'))
    frozen=protocol();cp=frozen['checkpoints']['lr_baseline']
    for key in ('protocol_id','schema_sha256','checkpoint_sha256','identity','feature_count','retained_features','class_count','features','classes','cases','input_sha256','probability_rtol','probability_atol'):
        if ref[key]!=win[key]:raise ValueError('Reference/candidate identity mismatch: '+key)
    if ref['identity']!=cp['identity'] or ref['checkpoint_sha256']!=cp['files']['pipeline.joblib']['sha256']:raise ValueError('Wrong frozen checkpoint')
    catalog=Catalog.load(Path(__file__).resolve().parents[1])
    if (ref['schema_sha256']!=frozen['processed']['schema_sha256'] or ref['feature_count']!=375 or
        ref['retained_features']!=318 or ref['class_count']!=587 or ref['features']!=list(catalog.features) or ref['classes']!=list(catalog.classes)):
        raise ValueError('Frozen catalog mismatch')
    matrix=np.asarray([[int(p=='ALL' or f in p) for f in catalog.features] for _,p in BASELINE_CASES],dtype='uint8')
    if ref['cases']!=json.loads(json.dumps(BASELINE_CASES)) or ref['input_sha256']!=hashlib.sha256(matrix.tobytes()).hexdigest():
        raise ValueError('Frozen synthetic inputs mismatch')
    if ref['kind']!='original_colab_reference' or ref['versions']!=cp['identity']['versions'] or ref['platform_system']!='Linux':raise ValueError('Invalid original reference environment')
    if win['kind']!='windows_candidate_probe' or win['versions']!={**ref['versions'],'python':'3.13.17'} or win['platform_system']!='Windows':raise ValueError('Invalid candidate environment')
    a=np.asarray(ref['predict_proba']);b=np.asarray(win['predict_proba'])
    if a.shape!=(8,587) or b.shape!=a.shape or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('Invalid probability matrix')
    validate_probabilities(a,8,np.arange(587),587);validate_probabilities(b,8,np.arange(587),587)
    if ref['predict_labels']!=win['predict_labels'] or ref['top3_class_ids']!=win['top3_class_ids']:raise ValueError('Labels/Top3 differ')
    if ref['probability_rtol']!=1e-10 or ref['probability_atol']!=1e-12 or not np.allclose(a,b,rtol=1e-10,atol=1e-12):raise ValueError('Probabilities exceed frozen tolerance')
    if any(ref['guards'].values()) or any(win['guards'].values()) or any(p['models_fitted'] or p['locked_test_opened'] for p in (ref,win)):raise ValueError('Forbidden operations in evidence')
    return dict(status='PASS',model_id='lr_baseline',reference_sha256=expected_reference_sha256,
        candidate_sha256=hashlib.sha256(Path(candidate).read_bytes()).hexdigest(),
        max_abs_difference=float(np.max(np.abs(a-b))),probabilities_checked=8*587,
        exact_labels=True,exact_top3=True,production_allowlist_changed=False)


HARD_MEMBERS = {'logistic_regression':'lr_tuned_c2', 'linear_svc':'svc_tuned', 'knn':'knn_tuned'}


def hard_tuned_probe(root, output, *, original_reference=False):
    """Isolated member inference, reusing fitted loaders and the frozen voting engine."""
    import numpy as np
    import pandas as pd
    from threadpoolctl import threadpool_limits
    from src.agent.extraction import Catalog
    from src.models.final_evaluation import protocol, versions
    from src.models.training import load_fitted_checkpoint, build_pipeline
    from src.models.ensemble import phase4_guard, hard_vote, HARD, PRIORITY, validate_probabilities
    from app.backend.prediction import PROJECT_ROOT, _file, _read
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists() or output.is_relative_to(root):raise ValueError('Use new evidence path outside protected storage')
    frozen=protocol();expected=dict(frozen['checkpoints']['lr_tuned_c2']['identity']['versions'])
    if original_reference:
        if versions()!=expected or platform.system()!='Linux':raise ValueError('Original reference requires trained Linux versions')
        import google.colab
    else:
        expected['python']='3.13.17'
        if (versions()!=expected or platform.system()!='Windows' or platform.machine()!='AMD64'
                or platform.python_implementation()!='CPython'):raise ValueError('Unqualified Windows probe environment')
    with phase4_guard(root) as guard,threadpool_limits(limits=1):
        _file(root,'artifacts/metadata/phase2/dataset_manifest.json',{'sha256':frozen['phase2_manifest_sha256']})
        for name in ('feature_schema.json','label_mapping.json'):
            relative='artifacts/metadata/phase2/'+name
            _file(root,relative,frozen['phase2_files'][relative])
        catalog=Catalog.load(PROJECT_ROOT,root)
        tuning=_read(_file(root,'artifacts/metadata/tuning/'+frozen['tuning']['experiment_id']+'/manifest.json',
            {'sha256':frozen['tuning']['manifest_sha256']}))
        e=frozen['ensemble']
        _file(PROJECT_ROOT,'src/models/ensemble.py',{'sha256':e['engine_source_sha256']})
        manifest=_read(_file(root,'artifacts/metadata/runs/'+e['run_id']+'/tuned_ensemble_manifest.json',
            {'sha256':e['manifest_sha256']}))
        if (manifest['hard'][e['key']]!=e['members'] or manifest['hard_tie_priority']!=e['priority']
                or list(HARD[e['key']])!=e['members'] or list(PRIORITY)!=e['priority']
                or manifest['selected_identity']!=frozen['checkpoints']['lr_tuned_c2']['identity']
                or manifest['tuning_experiment']!=frozen['tuning']['experiment_id']
                or manifest['tuning_manifest_sha256']!=frozen['tuning']['manifest_sha256']):
            raise ValueError('Frozen voting policy mismatch')
        x=pd.DataFrame([[int(p=='ALL' or f in p) for f in catalog.features] for _,p in BASELINE_CASES],
            columns=catalog.features,dtype='uint8')
        probes={};predictions={}
        for name,key in HARD_MEMBERS.items():
            cp=frozen['checkpoints'][key];identity=cp['identity']
            if tuning['status']!='completed' or tuning['experiment_id']!=frozen['tuning']['experiment_id'] or tuning['identity']!=identity:
                raise ValueError('Tuning identity mismatch')
            for relative,value in identity['source_sha256'].items():_file(PROJECT_ROOT,relative,{'sha256':value})
            for filename in ('pipeline.joblib','fit.json','metadata.json'):
                relative=cp['folder']+'/'+filename
                _file(root,relative,tuning['files'][relative])
                if filename=='pipeline.joblib' and tuning['files'][relative]!=cp['files'][filename]:raise ValueError('Checkpoint mismatch')
            folder=root/cp['folder'];fit=_read(folder/'fit.json');meta=_read(folder/'metadata.json')
            if (fit['identity']!=identity or meta['identity']!=identity or fit['status']!='fitted' or meta['status']!='completed'
                    or fit['model']!=cp['model'] or meta['model']!=cp['model'] or fit['n_input_features']!=375
                    or fit['n_retained_features']!=318 or meta['fit_metadata_sha256']!=hashlib.sha256((folder/'fit.json').read_bytes()).hexdigest()
                    or meta['pipeline_sha256']!=cp['files']['pipeline.joblib']['sha256']
                    or meta['predictions_sha256']!=tuning['files'][cp['folder']+'/validation_predictions.npz']['sha256']):
                raise ValueError('Fitted metadata mismatch')
            model=load_fitted_checkpoint(folder,identity,trusted=True)
            blueprint=build_pipeline(cp['model'],identity['config'])
            if (model.feature_names_in_.tolist()!=list(catalog.features) or not np.array_equal(model.classes_,np.arange(587))
                    or model.named_steps['variance'].get_support().sum()!=318
                    or [(n,type(s),s.get_params(deep=False)) for n,s in model.steps]!=[(n,type(s),s.get_params(deep=False)) for n,s in blueprint.steps]):
                raise ValueError('Fitted pipeline/schema mismatch')
            labels=np.asarray(model.predict(x));predictions[name]=labels
            probe=dict(checkpoint=cp,predict_labels=labels.tolist())
            if hasattr(model,'predict_proba'):
                probabilities=np.asarray(model.predict_proba(x))
                validate_probabilities(probabilities,8,model.classes_,587)
                probe.update(predict_proba=probabilities.tolist(),top3_class_ids=np.argsort(-probabilities,axis=1,kind='stable')[:,:3].tolist())
            else:
                scores=np.asarray(model.decision_function(x))
                if scores.shape!=(8,587) or not np.isfinite(scores).all():raise ValueError('Invalid decision scores')
                probe['decision_scores']=scores.tolist()
            probes[name]=probe
        voted,ties=hard_vote(predictions,tuple(e['members']),587)
        if any(guard.values()):raise ValueError('Forbidden operation observed')
        packet=dict(protocol_id='hard-tuned-windows31317-synthetic-v1',
            kind='original_colab_reference' if original_reference else 'windows_candidate_probe',
            versions=versions(),platform_system=platform.system(),ensemble=e,phase2_manifest_sha256=frozen['phase2_manifest_sha256'],
            schema_sha256=catalog.schema_id,features=list(catalog.features),classes=list(catalog.classes),cases=BASELINE_CASES,
            input_sha256=hashlib.sha256(x.to_numpy().tobytes()).hexdigest(),members=probes,
            hard_vote_labels=voted.tolist(),tie_rows=ties,numeric_rtol=1e-10,numeric_atol=1e-12,
            models_fitted=0,locked_test_opened=False,production_allowlist_changed=False,guards=dict(guard))
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as out:json.dump(packet,out,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return packet


def compare_hard_tuned(reference, candidate, expected_reference_sha256):
    """Compare all member outputs, identities and real tie rows, without approval side effects."""
    import numpy as np
    from src.models.final_evaluation import protocol
    from src.agent.extraction import Catalog
    from src.models.ensemble import hard_vote,validate_probabilities,class_predictions
    raw=Path(reference).read_bytes()
    if len(expected_reference_sha256)!=64 or hashlib.sha256(raw).hexdigest()!=expected_reference_sha256:raise ValueError('Reference checksum mismatch')
    ref=json.loads(raw);win=json.loads(Path(candidate).read_text(encoding='utf-8'));frozen=protocol()
    catalog=Catalog.load(Path(__file__).resolve().parents[1])
    matrix=np.asarray([[int(p=='ALL' or f in p) for f in catalog.features] for _,p in BASELINE_CASES],dtype='uint8')
    fixed=dict(protocol_id='hard-tuned-windows31317-synthetic-v1',ensemble=frozen['ensemble'],
        phase2_manifest_sha256=frozen['phase2_manifest_sha256'],schema_sha256=frozen['processed']['schema_sha256'],
        features=list(catalog.features),classes=list(catalog.classes),cases=json.loads(json.dumps(BASELINE_CASES)),
        input_sha256=hashlib.sha256(matrix.tobytes()).hexdigest(),numeric_rtol=1e-10,numeric_atol=1e-12)
    results={};trained=frozen['checkpoints']['lr_tuned_c2']['identity']['versions']
    for packet,kind,system,version in ((ref,'original_colab_reference','Linux',trained),
                                     (win,'windows_candidate_probe','Windows',{**trained,'python':'3.13.17'})):
        if any(packet.get(k)!=v for k,v in fixed.items()):raise ValueError('Frozen protocol/schema/input mismatch')
        if packet.get('kind')!=kind or packet.get('platform_system')!=system or packet.get('versions')!=version:raise ValueError('Reference/candidate environment mismatch')
        if set(packet['members'])!=set(HARD_MEMBERS):raise ValueError('Member set mismatch')
        if packet['models_fitted'] or packet['locked_test_opened'] or packet['production_allowlist_changed'] or any(packet['guards'].values()):raise ValueError('Forbidden operations in evidence')
        predictions={}
        for name,key in HARD_MEMBERS.items():
            member=packet['members'][name]
            if member['checkpoint']!=frozen['checkpoints'][key]:raise ValueError('Member checkpoint identity mismatch')
            labels=class_predictions(member['predict_labels'],8,587);predictions[name]=labels
            field='decision_scores' if name=='linear_svc' else 'predict_proba'
            values=np.asarray(member[field])
            if values.shape!=(8,587) or not np.isfinite(values).all():raise ValueError('Invalid member numeric matrix')
            if field=='predict_proba':
                validate_probabilities(values,8,np.arange(587),587)
                if member['top3_class_ids']!=np.argsort(-values,axis=1,kind='stable')[:,:3].tolist():raise ValueError('Invalid member Top3')
            if not np.array_equal(labels,values.argmax(axis=1)):raise ValueError('Member labels/score mismatch')
        voted,ties=hard_vote(predictions,tuple(frozen['ensemble']['members']),587)
        if packet['hard_vote_labels']!=voted.tolist() or packet['tie_rows']!=ties:raise ValueError('Frozen voting result/tie mismatch')
    for name in HARD_MEMBERS:
        a=ref['members'][name];b=win['members'][name];field='decision_scores' if name=='linear_svc' else 'predict_proba'
        x=np.asarray(a[field]);y=np.asarray(b[field])
        if a['predict_labels']!=b['predict_labels'] or a.get('top3_class_ids')!=b.get('top3_class_ids'):raise ValueError('Member labels/Top3 differ')
        if not np.allclose(x,y,rtol=1e-10,atol=1e-12):raise ValueError('Member numeric tolerance exceeded')
        results[name]=dict(numeric_field=field,values_checked=int(x.size),max_abs_difference=float(np.max(np.abs(x-y))),exact_labels=True,exact_top3=field=='predict_proba')
    if ref['hard_vote_labels']!=win['hard_vote_labels'] or ref['tie_rows']!=win['tie_rows']:raise ValueError('Ensemble results differ')
    return dict(status='PASS',protocol_id=fixed['protocol_id'],reference_sha256=expected_reference_sha256,
        candidate_sha256=hashlib.sha256(Path(candidate).read_bytes()).hexdigest(),members=results,
        hard_vote_labels=ref['hard_vote_labels'],tie_rows=ref['tie_rows'],exact_voting=True,production_allowlist_changed=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--storage-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--lr-baseline-only',action='store_true')
    parser.add_argument('--hard-tuned-only',action='store_true')
    parser.add_argument('--original-reference',action='store_true')
    args=parser.parse_args()
    if args.lr_baseline_only and args.hard_tuned_only:parser.error('Select exactly one probe scope')
    if args.original_reference and not (args.lr_baseline_only or args.hard_tuned_only):parser.error('Original-reference mode requires an explicit scope')
    if args.lr_baseline_only:baseline_probe(args.storage_root,args.output,original_reference=args.original_reference)
    elif args.hard_tuned_only:hard_tuned_probe(args.storage_root,args.output,original_reference=args.original_reference)
    else:run(args.storage_root,args.output)
