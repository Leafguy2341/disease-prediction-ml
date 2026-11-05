"""Two-root handover audit/build. Reuse package_handover; never modify ML runtime.

Run audit, stage, build, verify, publish in order with an external --work folder.
The clean-smoke mode is run FROM EXTRACTED CODE in a fresh Python process.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from scripts import package_handover as pack

ROOT=Path(__file__).resolve().parents[1]
DOC_RECEIPTS=('reports/release_final_gate/packaging_artifact_manifest.json',
              'reports/handover_blocker_fix/packaging_manifest.json')
SCIENTIFIC_SUPPLEMENTS=('reports/figures/model_selection_tuned_error_analysis.png',
    'reports/figures/preprocessing_threshold_comparison.png',
    'reports/tables/preprocessing_class_eligibility.csv','reports/tables/preprocessing_class_support.csv',
    'reports/tables/preprocessing_regurgitation_projection.csv','reports/tables/preprocessing_regurgitation_removal_impact.csv',
    'reports/tables/preprocessing_regurgitation_support.csv','reports/tables/preprocessing_split_summary.csv')


def write(path,value):
    pack.exclusive(path,pack.encoded(value))


def roots(args):
    code=pack.no_links(args.code_root or ROOT)
    data=pack.no_links(args.data_root or code.parent/'disease-prediction-ml-data')
    work=pack.no_links(args.work)
    assert code.is_dir() and data.is_dir() and code!=data, 'Both independent source roots must exist'
    assert not work.is_relative_to(code) and not work.is_relative_to(data), 'Staging must be external'
    return code,data,work


def selection(code,data):
    pack.validate_pins(code)
    code_files=pack.code_files(code)
    data_files,req=pack.verify_data(code,data,evidence_root=code,allow_locked_bytes=True)
    for name in DOC_RECEIPTS:
        assert (code/name).is_file()
        pack.secret_check(name,(code/name).read_bytes())
        code_files[name]=code/name
    # Source-only scientific figures/tables referenced by frozen project docs.
    # Keep byte-for-byte, never replace a different downloaded variant.
    for name in SCIENTIFIC_SUPPLEMENTS:
        assert (code/name).is_file()
        if name in data_files:assert pack.entry(data_files[name])==pack.entry(code/name), 'Scientific variant conflict: '+name
        else:data_files[name]=code/name
    # Identical dual-role evidence is preserved where both frozen contracts need it.
    for name in set(code_files)&set(data_files):
        assert pack.entry(code_files[name])==pack.entry(data_files[name]), 'Cross-package conflict: '+name
    return code_files,data_files,req


def audit(args):
    code,data,work=roots(args)
    assert not work.exists(), 'Fresh staging only; preserve previous attempts'
    work.mkdir(parents=True)
    codes,datas,req=selection(code,data)
    frozen=pack.read(code/'reports/handover_blocker_fix/packaging_manifest.json')
    permitted={'README.md','docs/HANDOVER_GUIDE.md','docs/DEPLOYMENT_GUIDE.md','docs/DEVELOPMENT_LOG.md',
               'configs/runtime.local.example.json','scripts/package_handover.py'}
    differences=[]
    for name,expected in frozen['code_package_files'].items():
        assert name in codes, 'Frozen member missing: '+name
        if pack.entry(codes[name])!=expected:
            assert name in permitted or name.startswith('docs/') and name.endswith('.md'), 'Unapproved frozen-source change: '+name
            differences.append(name)
    references={n:p.read_text(encoding='utf-8-sig',errors='replace') for n,p in codes.items()
                if p.suffix in {'.py','.md','.json','.ipynb','.ps1','.toml'}}
    rows=[];hashes=defaultdict(list);by_name={};secrets=[]
    signatures=[__import__('re').compile(p) for p in pack.SECRET_PATTERNS]
    for root_id,root in [('code',code),('download',data)]:
        for base,dirs,names in os.walk(root,followlinks=False):
            for name in sorted(names):
                path=Path(base)/name;relative=path.relative_to(root).as_posix()
                assert not path.is_symlink(), 'Inventory symlink requires review: '+relative
                h=hashlib.sha256();found=False;tail=b''
                with path.open('rb') as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):
                        h.update(block);chunk=tail+block
                        found |= any(p.search(chunk) is not None for p in signatures)
                        tail=chunk[-256:]
                info=dict(bytes=path.stat().st_size,sha256=h.hexdigest())
                in_code=relative in codes and codes[relative]==path
                in_data=relative in datas and datas[relative]==path
                decision='CODE+DATA' if in_code and in_data else 'CODE' if in_code else 'DATA' if in_data else 'EXCLUDE'
                parts=Path(relative).parts
                if in_code:
                    role='approved source/config/fixture/evidence';reason='Current source authority; frozen allowlist plus documented packaging edits'
                    provenance='code freeze; pinned code supplement policy' if relative in pack.code_supplements(code) else 'code freeze/current source allowlist'
                elif in_data:
                    role=('trained checkpoint' if relative.startswith('artifacts/models/') else
                          'dataset payload (opaque bytes)' if relative.startswith(('data/raw/','data/processed/')) else
                          'scientific metadata/results/evidence')
                    reason='Verified data-side identity and existing experiment namespace';provenance='pinned data requirements and scientific bundle manifests'
                    if relative in SCIENTIFIC_SUPPLEMENTS:
                        reason='Source-only scientific report used by frozen docs/notebooks; no downloaded variant replaced'
                        provenance='explicit source scientific supplement; byte/hash inventory'
                else:
                    role='excluded workspace material';provenance='outside approved package contracts'
                    reason=('Reproducible environment/cache/build/archive; not source deliverable' if
                            any(p in pack.BLOCKED_PARTS for p in parts) or path.suffix.lower() in {'.zip','.pyz','.pyc'} else
                            'Published source on downloaded Drive tree is stale transport; Windows source is authoritative' if
                            root_id=='download' and (parts[0] in {'src','scripts','configs'} or relative.startswith('requirements-') or relative=='source_manifest.json') else
                            'Repo-side scientific mirror; data download is authoritative' if root_id=='code' and relative in datas else
                            'Unfrozen control/personal/temporary material; original retained, not needed by approved runtime')
                if found:
                    secrets.append(dict(root=root_id,path=relative,included=in_code or in_data,reason='Known credential signature; values suppressed'))
                    assert not(in_code or in_data), 'Possible credential in selected file: '+relative
                    reason+='; potential credential signature excluded'
                required=[]
                if in_code or in_data:
                    required=[n for n,text in references.items() if n!=relative and (relative in text or path.name in text)][:12]
                    if in_data:required+=['configs/handover_data_requirements.json; scientific manifest closure']
                row=dict(relative_path=relative,source_root=root_id,bytes=info['bytes'],sha256=info['sha256'],
                    file_type=path.suffix or 'no suffix',role=role,package=decision,reason=reason,
                    manifest_provenance=provenance,required_by='; '.join(required) or 'No packaged runtime dependency',duplicate_status='')
                rows.append(row);hashes[info['sha256']].append((root_id,relative));by_name[root_id,relative]=row
        print('INVENTORIED',root_id,sum(r['source_root']==root_id for r in rows),flush=True)
    conflicts=[]
    for row in rows:
        group=hashes[row['sha256']]
        row['duplicate_status']='unique content' if len(group)==1 else 'identical content in '+str(len(group))+' paths'
        if row['source_root']=='download' and ('code',row['relative_path']) in by_name:
            other=by_name['code',row['relative_path']]
            if other['sha256']!=row['sha256']:
                assert not (row['package']!='EXCLUDE' and other['package'] in {'CODE','CODE+DATA'}), 'Unresolved canonical conflict: '+row['relative_path']
                conflicts.append(dict(path=row['relative_path'],code_sha256=other['sha256'],download_sha256=row['sha256'],
                    resolution='Windows code authority; downloaded published source excluded' if row['package']=='EXCLUDE' else 'Downloaded scientific authority; repo mirror excluded'))
    with (work/'file_inventory.csv').open('x',encoding='utf-8-sig',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    inventory={k:{r['relative_path']:{'bytes':r['bytes'],'sha256':r['sha256']} for r in rows if r['source_root']==k} for k in ['code','download']}
    write(work/'source_inventory.json',inventory)
    write(work/'audit.json',dict(status='AUDIT_PASS',source_roots={'code':str(code),'download':str(data)},
        original_freeze_members=len(frozen['code_package_files']),authorized_changed_members=differences,
        added_code_members=sorted(set(codes)-set(frozen['code_package_files'])),
        code_files=len(codes),data_files=len(datas),data_files_from_code_provenance=[n for n,p in datas.items() if p.is_relative_to(code)],
        windows_mirror_present=Path('D:/ML_Artifacts/disease-prediction-ml').is_dir(),
        disposition_counts=dict(Counter(r['package'] for r in rows)),conflicts_resolved=conflicts,
        secret_findings=secrets,selected_secrets=0,unresolved_critical_conflicts=[],
        shared_paths=sorted(set(codes)&set(datas)),locked_payload_handling='opaque hashing/copy only, never parsed/evaluated'))


def stage(args):
    code,data,work=roots(args);codes,datas,_=selection(code,data)
    inventories={}
    for kind,files,prefix in [('code',codes,'disease-prediction-ml'),('data',datas,'disease-prediction-ml-data')]:
        folder=work/'staging'/prefix;folder.mkdir(parents=True,exist_ok=False)
        inventories[kind]={}
        for name,path in sorted(files.items()):
            target=folder/name;target.parent.mkdir(parents=True,exist_ok=True)
            with path.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst,1024*1024)
            expected=pack.entry(path);assert pack.entry(target)==expected
            inventories[kind][name]=expected
    write(work/'frozen_members.json',inventories)


def build(args):
    code,data,work=roots(args);frozen=pack.read(work/'frozen_members.json')
    for kind,prefix,control in [('code','disease-prediction-ml','handover_code_inventory.json'),('data','disease-prediction-ml-data','handover_data_inventory.json')]:
        inventory=dict(version=3,kind=kind,archive_prefix=prefix+'/',files=frozen[kind],models_fitted=0,test_evaluated=False)
        archive_path=work/('project-'+kind+'.zip')
        with archive_path.open('xb') as output,zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name,expected in frozen[kind].items():
                source=work/'staging'/prefix/name
                assert pack.entry(source)==expected
                pack._zip_write(archive,prefix+'/'+name,source)
            archive.writestr(prefix+'/'+control,pack.encoded(inventory))
        verified=pack.verify_archive(archive_path,expected_sha256=pack.sha(archive_path))
        with zipfile.ZipFile(archive_path) as z:assert z.testzip() is None
        write(work/(kind+'-archive.json'),dict(path=str(archive_path),**pack.entry(archive_path),
            files=verified['files'],payload_files=len(frozen[kind]),crc='PASS',member_sha256='PASS',prefix=prefix))


def verify(args):
    code,data,work=roots(args)
    clean=work/'clean-extraction';clean.mkdir(exist_ok=False)
    for kind in ('code','data'):
        pack.extract(work/('project-'+kind+'.zip'),clean,pack.sha(work/('project-'+kind+'.zip')),allow_locked_bytes=kind=='data')
    code_clone=clean/'disease-prediction-ml';data_clone=clean/'disease-prediction-ml-data'
    # Check actual Markdown links, excluding fenced/inline code and anchors.
    import re
    unresolved=[]
    for path in code_clone.rglob('*.md'):
        fence=False
        for line in path.read_text(encoding='utf-8-sig',errors='replace').splitlines():
            if line.lstrip().startswith(chr(96)*3):fence=not fence;continue
            if fence:continue
            line=re.sub(chr(96)+r'[^`]*'+chr(96),'',line)
            for target in re.findall(r'\[[^\]\n]+\]\(([^)\n]+)\)',line):
                target=target.strip('<>').split('#')[0]
                if not target or '://' in target or target.startswith(('/', 'mailto:')):continue
                if not (path.parent/target).exists():unresolved.append(dict(document=path.relative_to(code_clone).as_posix(),target=target))
    write(work/'extracted_documentation_links.json',dict(unresolved=unresolved))
    assert not [r for r in unresolved if not r['document'].startswith('docs/archive/')], 'Broken current documentation link; do not publish'
    environment={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ['API_KEY','PYTHONPATH','PYTHONHOME'])}
    environment.update(DISEASE_API_STORAGE_ROOT=str(data_clone),DISEASE_CHAT_MODE='offline',DISEASE_GEMINI_LIVE='0',DISEASE_GROQ_LIVE='0',DISEASE_OPENROUTER_LIVE='0')
    command=[args.python,'-B','-X','utf8','-m','scripts.final_handover','clean-smoke','--data-root',str(data_clone),
             '--code-root',str(code_clone),'--work',str(work),'--original-code',str(code),'--original-data',str(data)]
    run=subprocess.run(command,cwd=code_clone,env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (work/'clean-runtime.log').write_text(run.stdout+'\n'+run.stderr,encoding='utf-8')
    assert run.returncode==0, 'Clean runtime failed; see clean-runtime.log; do not publish'
    # Recheck every original byte after packaging (including excluded files).
    original=pack.read(work/'source_inventory.json')
    # Only documented packaging docs/config/driver may have changed since audit.
    files=pack.read(work/'frozen_members.json')
    for name,expected in files['data'].items():
        path=(code/name) if name in pack.read(work/'audit.json')['data_files_from_code_provenance'] else data/name
        assert pack.entry(path)==expected,'Original data changed: '+name
    for name,expected in original['download'].items():assert pack.entry(data/name)==expected
    for name,expected in original['code'].items():
        if name not in files['code']:assert pack.entry(code/name)==expected,'Excluded original changed: '+name
    for name,expected in files['code'].items():assert pack.entry(code/name)==expected,'Frozen source changed: '+name
    write(work/'verification.json',dict(status='VERIFIED',crc='PASS',member_sha256='PASS',clean_runtime='PASS',
        originals_preserved=True,locked_test_evaluated=False,models_fitted=0,llm_requests=0,
        approved_dependency_environment_only=args.python))


def publish(args):
    code,data,work=roots(args)
    assert pack.read(work/'verification.json')['status']=='VERIFIED'
    destinations=[code.parent/'project-code.zip',code.parent/'project-data.zip']
    assert not any(p.exists() for p in destinations), 'Existing deliverables preserved; review before replacement'
    receipts={}
    for kind,dest in zip(('code','data'),destinations):
        source=work/('project-'+kind+'.zip')
        with source.open('rb') as src,dest.open('xb') as dst:shutil.copyfileobj(src,dst,1024*1024)
        assert pack.entry(dest)==pack.entry(source)
        receipts[kind]=dict(path=str(dest),**pack.entry(dest),**{k:v for k,v in pack.read(work/(kind+'-archive.json')).items() if k not in {'path','bytes','sha256'}})
    write(work/'handover_receipt.json',dict(status='HANDOVER_READY',archives=receipts,verification=pack.read(work/'verification.json'),
        coverage={'active':135,'features':375},mirror_status='MISSING (not required; actual downloaded data verified)',
        no_source_deletion=True,no_drive_modification=True))
    print(json.dumps(receipts,indent=2))


def clean_smoke(args):
    # Do not import any project business module before forbidding original roots.
    original=[Path(args.original_code).resolve(),Path(args.original_data).resolve()]
    dependency_env=original[0]/'.venv-web'
    counters=dict(original_source_or_data_access=0,outbound_network=0,llm=0,fit=0)
    def audit_hook(event,values):
        if event in {'open','os.listdir','os.scandir'} and values and isinstance(values[0],(str,bytes,os.PathLike)):
            path=Path(os.fsdecode(values[0])).resolve()
            if any(path.is_relative_to(p) for p in original) and not path.is_relative_to(dependency_env):
                counters['original_source_or_data_access']+=1
                raise RuntimeError('Original source/data access forbidden during clean smoke')
            if event=='open' and path.name=='test.csv.gz':raise RuntimeError('Locked test must not be opened by runtime')
    sys.addaudithook(audit_hook)
    import socket
    from unittest.mock import patch
    from contextlib import ExitStack
    from fastapi.testclient import TestClient
    from app.backend.main import create_app
    from src.agent import provider
    from src.models.ensemble import phase4_guard
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LogisticRegression
    from sklearn.feature_selection import VarianceThreshold
    def no_llm(*a,**k):counters['llm']+=1;raise AssertionError('LLM forbidden')
    def no_fit(*a,**k):counters['fit']+=1;raise AssertionError('Fit forbidden')
    connect=socket.socket.connect
    def safe_connect(sock,address):
        if not isinstance(address,tuple) or address[0] not in {'127.0.0.1','::1'}:
            counters['outbound_network']+=1;raise AssertionError('Outbound forbidden')
        return connect(sock,address)
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket,'connect',safe_connect))
        for name in ('_post','_post_groq','_post_openrouter','create_provider'):stack.enter_context(patch.object(provider,name,no_llm))
        for kind in (Pipeline,LogisticRegression,VarianceThreshold):stack.enter_context(patch.object(kind,'fit',no_fit))
        guard=stack.enter_context(phase4_guard(Path(args.code_root)))
        app=create_app()
        with TestClient(app) as client:
            health=client.get('/health');assert health.status_code==200,health.text
            service=app.state.predictor
            assert service.verification=='REAL CHECKPOINT VERIFIED' and service._model.named_steps['estimator'].coef_.shape==(587,318)
            prediction=client.post('/api/v1/predict',json={'present_features':['cough','fever']});assert prediction.status_code==200
            def chat(value):
                r=client.post('/api/v1/chat',json=value);assert r.status_code==200,r.text;return r.json()
            first=chat({'message':'Tôi bị ngứa âm đạo.'});p=first['pending_questions'];assert len(p['items'])==3 and first['predictions'] is None
            answer=chat({'message':'1 có, 2 có, 3 không','session_id':first['session_id'],'batch_id':p['batch_id']});assert answer['status']=='prediction_ready',answer
            another=chat({'message':'Tôi bị ngứa âm đạo.'});preview=chat({'session_id':another['session_id'],'action':'preview'});assert preview['status']=='prediction_ready' and preview['reason']=='offline_requested_preview'
            for text in ['Tôi không ho.','Tôi chưa chắc có ho.','Khó thở nặng, thở không nổi.','Giả sử tôi ho và sốt thì sao?']:
                r=chat({'message':text});assert r['predictions'] is None
            assert client.get('/').status_code==200 and client.get('/static/app.js').status_code==200
            identity=service.identity()
            assert all(Path(m.__file__).resolve().is_relative_to(Path(args.code_root).resolve()) for n,m in list(sys.modules.items()) if n.startswith(('src.','app.','scripts.')) and getattr(m,'__file__',None))
        import ast
        notebook=json.loads((Path(args.code_root)/'notebooks/06_final_model_evaluation.ipynb').read_text(encoding='utf-8'))
        tree=ast.parse('\n'.join(''.join(c['source']) for c in notebook['cells'] if c['cell_type']=='code'))
        assert not any(isinstance(n,ast.Call) and getattr(n.func,'attr',getattr(n.func,'id','')) in {'evaluate','predict','predict_proba','fit','copy2','load_final_split','load_fitted_checkpoint'} for n in ast.walk(tree))
        import uvicorn,threading,time,http.client
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(32)
        port=listener.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,workers=1,log_level='error',access_log=False))
        thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True)
        try:
            thread.start();deadline=time.monotonic()+15
            while not server.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.02)
            assert server.started,'Extracted Uvicorn startup failed'
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=15)
            conn.request('GET','/health');response=conn.getresponse();assert response.status==200
            assert json.loads(response.read())['checkpoint_status']=='REAL CHECKPOINT VERIFIED'
            conn.request('POST','/api/v1/predict',body=json.dumps({'present_features':['cough','fever']}),headers={'Content-Type':'application/json'})
            response=conn.getresponse();assert response.status==200
            tcp=json.loads(response.read());assert len(tcp['top3'])==3 and tcp['checkpoint_sha256']==identity['checkpoint_sha256']
            conn.close()
        finally:
            server.should_exit=True;thread.join(timeout=15);listener.close()
        assert not any(counters.values()) and not any(guard.values()),(counters,guard)
    write(Path(args.work)/'clean-runtime.json',dict(status='PASS',identity=identity,health_http=200,predict_http=200,
        chat_batch='PASS',preview='PASS',code_root=str(args.code_root),storage_root=str(args.data_root),
        no_original_source_or_data_dependency=True,installed_dependencies_reused=str(dependency_env),counters=counters,
        protected_guards=dict(guard),real_uvicorn_tcp_http={'health':200,'predict':200,'port':port},locked_test_opened=False,models_fitted=0))
    print('CLEAN EXTRACTION RUNTIME PASS')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['audit','stage','build','verify','publish','clean-smoke'])
    for name in ('code-root','data-root','work','original-code','original-data','python'):p.add_argument('--'+name)
    args=p.parse_args()
    assert args.work
    globals()[args.action.replace('-','_')](args)


if __name__=='__main__':main()
