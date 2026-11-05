"""Bounded, reversible dictionary activation; never changes parser or ML artifacts."""
from collections import Counter
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import argparse
import subprocess
import sys
import os

from scripts.review_symptom_activation import ROOT, read_inputs, engine_for, sha

RELEASE = ROOT / 'reports/terminology/activation-20261104'
DECISIONS_SHA = '2909bd6e639736cb0c7a3b33505009a891a23e727f2722c6a55910d2d0f08c90'


def context_cases(entries, features):
    cases=[]
    for f in features:
        for alias in entries[f]['proposed_aliases_vi']:
            for kind,text,expected in [
                ('uncertain','Tôi chưa chắc bị '+alias+'.',{f:'uncertain'}),
                ('other','Mẹ tôi bị '+alias+'.',{}),
                ('knowledge',alias+' là gì?',{}),
                ('hypothetical','Giả sử tôi bị '+alias+' thì sao?',{}),
                ('quoted','Tôi đọc câu "'+alias+'" trong sách.',{}),
            ]:
                cases.append(dict(feature=f,alias=alias,kind=kind,text=text,expected_states=expected))
    for f,text,forbidden in [
        ('feeling hot','Tôi cảm thấy nóng nhưng không sốt.',['fever']),
        ('feeling hot','Tôi sốt.',['feeling hot']),
        ('pain during pregnancy','Tôi bị đau bụng.',['pain during pregnancy']),
        ('pain during pregnancy','Tôi không mang thai, tôi bị đau bụng.',['pain during pregnancy']),
        ('pain during pregnancy','Tôi bị đau, tôi hỏi về đau trong thai kỳ.',['pain during pregnancy']),
        ('kidney mass','Tôi bị đau vùng thận.',['kidney mass']),
        ('fluid in ear','Tôi bị chảy dịch từ tai.',['fluid in ear']),
        ('fluid in ear','Tôi bị dịch chảy ra từ tai.',['fluid in ear']),
        ('delusions or hallucinations','Bạn tôi bị hoang tưởng hoặc ảo giác.',['delusions or hallucinations']),
        ('delusions or hallucinations','Nhân vật trong truyện bị hoang tưởng hoặc ảo giác.',['delusions or hallucinations']),
    ]:
        cases.append(dict(feature=f,alias='',kind='special_context',text=text,forbidden_present=forbidden))
    for i,c in enumerate(cases):c['id']='context-'+str(i+1).zfill(4)
    return cases


def run_cases(engine,cases):
    result=[]
    for c in cases:
        r=engine.handle(c['text'])
        if r.reason=='invalid_session':raise RuntimeError('Fixture session capacity exceeded')
        states=(r.sidecar or {}).get('states',{})
        ok=(c.get('expected_states') is None or states==c['expected_states'])
        ok=ok and not (set(c.get('forbidden_features',[])) & set(states))
        ok=ok and not any(states.get(f)=='present' for f in c.get('forbidden_present',[]))
        if c.get('expected_no_prediction'):ok=ok and r.status!='extraction_ready'
        if c.get('expected_reason'):ok=ok and r.reason==c['expected_reason']
        evidence_ok=True
        if r.sidecar:
            session=engine.store.get(r.session_id)
            turns={t.turn_id:t.text for t in session.turns}
            for spans in r.sidecar['evidence'].values():
                for s in spans:evidence_ok &= turns[s['turn_id']][s['start']:s['end']]==s['text']
        result.append(dict(id=c['id'],feature=c.get('feature'),kind=c['kind'],text=c['text'],
            passed=bool(ok and evidence_ok and r.predictions is None),states=states,
            reason=r.reason,status=r.status,evidence_ok=evidence_ok))
        if r.session_id:engine.store.discard(r.session_id)
    return result


def qualified_dictionary(entries,features):
    value=deepcopy(entries)
    for f in features:
        assert entries[f]['activation_status']=='PENDING_REVIEW'
        value[f]['aliases_vi']=list(entries[f]['proposed_aliases_vi'])
        # Preserve display, review metadata, question flags and all existing fields.
        value[f]['activation_status']='ACTIVE_EXISTING'
    return value


def prepare():
    catalog,entries,rows,old,ids=read_inputs()
    prior=json.loads((ROOT/'reports/terminology/symptom_activation_validation.json').read_text(encoding='utf-8'))
    assert ids==prior['summary']['input_identities'], 'Review source pins changed'
    path=ROOT/'reports/terminology/symptom_activation_decisions.csv'
    assert sha(path)==DECISIONS_SHA
    with path.open(encoding='utf-8-sig',newline='') as stream:decisions=list(csv.DictReader(stream))
    assert [r['canonical_feature'] for r in decisions]==list(catalog.features)
    selected=[r['canonical_feature'] for r in decisions if r['decision']=='APPROVE']
    assert len(selected)==128 and sum(len(entries[f]['proposed_aliases_vi']) for f in selected)==145
    assert all(entries[f]['activation_status']=='PENDING_REVIEW' and entries[f]['review_status']=='READY' for f in selected)
    cases=[json.loads(l) for l in (ROOT/'data/evaluation/vietnamese_symptom_activation_cases.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(cases)==821
    contexts=context_cases(entries,selected)
    with tempfile.TemporaryDirectory(prefix='activation-context-') as tmp:
        engine=engine_for(catalog,qualified_dictionary(entries,selected),Path(tmp)/'candidate.json')
        context_results=run_cases(engine,contexts)
        excluded={r['feature'] for r in context_results if not r['passed']}
        # No parser repairs: fail an entire feature closed if any context fails.
        safe=[f for f in selected if f not in excluded]
        engine=engine_for(catalog,qualified_dictionary(entries,safe),Path(tmp)/'safe.json')
        original_results=run_cases(engine,old)
        # One historical pending-only assertion is superseded by owner-approved
        # activation; retain the original packet and test its exact new state.
        overrides={'semantic-084': {'elbow swelling':'present'}} if 'elbow swelling' in safe else {}
        for r in original_results:
            if r['id'] in overrides:
                r['passed']=r['states']==overrides[r['id']] and r['evidence_ok'] and r['status']!='extraction_ready'
        failed_old={r['id'] for r in original_results if not r['passed']}
        if failed_old:raise RuntimeError('Original 86 production cases regress: '+str(sorted(failed_old)))
        active_cases=[c for c in cases if c['feature'] in safe]
        final=run_cases(engine,active_cases)
        assert all(r['passed'] for r in final), 'Safe qualification failed'
    return catalog,entries,selected,safe,cases,old,contexts,context_results,ids


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--batch',type=int)
    parser.add_argument('--rollback',type=int)
    args=parser.parse_args()
    config=ROOT/'configs/synonyms.json'
    manifest_path=RELEASE/'manifest.json'
    if args.prepare:
        assert not RELEASE.exists(), 'Release exists; never overwrite evidence'
        catalog,entries,selected,safe,cases,old,contexts,results,ids=prepare()
        from scripts.build_synonyms_report import collision_rows
        assert [r for r in collision_rows(qualified_dictionary(entries,safe),proposed=False)
                if r['kind']=='FOLDED_ALIAS_COLLISION']==[r for r in collision_rows(entries,proposed=False)
                if r['kind']=='FOLDED_ALIAS_COLLISION'], 'New folded collision'
        RELEASE.mkdir()
        raw=config.read_bytes()
        (RELEASE/'synonyms.before.json').write_bytes(raw)
        m=dict(status='PREPARED',before_sha256=sha(config),current_sha256=sha(config),
            input_identities=ids,decisions_sha256=DECISIONS_SHA,approved_features=selected,
            qualified_features=safe,activated_features=[],
            batches=[safe[i:i+32] for i in range(0,len(safe),32)],completed_batches=[],
            excluded_features=sorted(set(selected)-set(safe)),
            excluded_contexts=[r for r in results if not r['passed']],
            semantic_case_overrides={'semantic-084':{'elbow swelling':'present'}},
            original_decision_counts=dict(APPROVE=128,REVISE=73,CLARIFY=26,HOLD=148),
            clinical_validation=False,models_fitted=0,predictions_called=False,test_payload_opened=False)
        (RELEASE/'context_validation.json').write_text(json.dumps(dict(cases=contexts,results=results),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        manifest_path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(status=m['status'],qualified=len(safe),excluded=m['excluded_features'],batches=list(map(len,m['batches'])))))
        return
    assert manifest_path.is_file(), 'Run --prepare first'
    m=json.loads(manifest_path.read_text(encoding='utf-8'))
    assert sha(config)==m['current_sha256'], 'Current dictionary mismatch; stop'
    assert sha(RELEASE/'synonyms.before.json')==m['before_sha256']
    assert not m['status'].startswith('FAILED'), 'Failed batch: stop; independent review is required before a new activation attempt'
    for relative,expected in m['input_identities']['source_sha256'].items():
        assert sha(ROOT/relative)==expected, 'Source pin mismatch: '+relative
    assert sha(ROOT/'configs/phase5b.json')==m['input_identities']['runtime_policy_sha256']
    assert sha(ROOT/'reports/terminology/symptom_activation_decisions.csv')==m['decisions_sha256']
    if args.rollback is not None:
        index=args.rollback
        assert m['completed_batches'] and index==m['completed_batches'][-1], 'Only last applied batch may roll back'
        backup=RELEASE/f'batch-{index}.before.json'
        prior=json.loads((RELEASE/f'batch-{index}.manifest.json').read_text(encoding='utf-8'))
        assert sha(backup)==prior['before_sha256']
        config.write_bytes(backup.read_bytes())
        m['activated_features']=[f for f in m['activated_features'] if f not in m['batches'][index-1]]
        m['completed_batches'].pop();m['current_sha256']=sha(config);m['status']='ROLLED_BACK'
        manifest_path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return
    index=args.batch
    assert index==len(m['completed_batches'])+1 and 1<=index<=len(m['batches']), 'Batches must apply once in order'
    backup=RELEASE/f'batch-{index}.before.json'
    assert not backup.exists(), 'Batch already attempted; review evidence before retry'
    before=config.read_bytes();backup.write_bytes(before)
    baseline=json.loads((RELEASE/'synonyms.before.json').read_text(encoding='utf-8'))
    features=m['activated_features']+m['batches'][index-1]
    new=qualified_dictionary(baseline,features)
    prior=deepcopy(m)
    record=dict(batch=index,features=m['batches'][index-1],before_sha256=sha(config),status='APPLIED_PENDING_TEST')
    config.write_text(json.dumps(new,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    m.update(activated_features=features,current_sha256=sha(config),status='APPLIED_PENDING_TEST')
    m['completed_batches'].append(index)
    manifest_path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    command=[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','tests']
    try:
        environment=dict(os.environ)
        for key in list(environment):
            if key.endswith('API_KEY'):environment.pop(key)
        environment.update(DISEASE_RUN_DATA_REGRESSION='0',DISEASE_BROWSER_SMOKE='0',
            DISEASE_GEMINI_LIVE='0',DISEASE_GROQ_LIVE='0',DISEASE_OPENROUTER_LIVE='0',
            OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',env=environment)
        (RELEASE/f'batch-{index}.tests.txt').write_text(run.stdout+'\n'+run.stderr,encoding='utf-8')
        record.update(after_sha256=sha(config),test_exit_code=run.returncode,command=command)
        assert run.returncode==0, 'Regression failed; rollback batch'
        assert sha(config)==m['current_sha256'], 'Tests changed dictionary'
    except BaseException:
        config.write_bytes(before)
        prior['status']='FAILED_BATCH_ROLLED_BACK'
        manifest_path.write_text(json.dumps(prior,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        record['status']='FAILED_ROLLED_BACK'
        (RELEASE/f'batch-{index}.manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        raise
    record['status']='PASS'
    (RELEASE/f'batch-{index}.manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    m['status']='COMPLETE' if index==len(m['batches']) else 'BATCH_PASS'
    manifest_path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(batch=index,status=m['status'],active=135+len(features),sha256=sha(config),test_summary=run.stdout[-800:]),ensure_ascii=True))


if __name__=='__main__':main()
