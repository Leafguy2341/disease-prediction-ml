"""Offline approval proposal only. Dictionary activation occurs in owned fixtures, never production."""
from collections import Counter
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import tempfile

from scripts.build_synonyms_report import production_signature, review_rows, write_table
from src.agent.extraction import Catalog
from src.agent.offline import OfflineConversation, OfflineExtractor, OfflinePolicy, fold
from src.agent.conversation import Policy

ROOT=Path(__file__).resolve().parents[1]
PRODUCTION_SIGNATURE='5fcbf9e743088a41d009abc3ee9fb310ab040aa9e814dce72e3dae9953f5644e'
PACKETS={
 'symptom_dictionary_review.csv':'40aa98c794817ad7b2eaa56e39060fecd96d5231928e3737da0f9628a65b63dc',
 'symptom_dictionary_changes.csv':'98004eed3dbc9d33120a19ed103071343b078df7a42e037973248e1b41fb8f95',
 'symptom_dictionary_collisions.csv':'13a2f03e61f3b7c3fa4db0ec236fa95f40b9b4d049fd949d56aeb5072d915747'}
# Wording describes broad/composite observations, an unspecified subject or safety
# context; READY alone is insufficient for this narrower activation proposal.
REVISE_SCOPE={
 'abnormal involuntary movements','problems with shape or size of breast',
 'eye moves abnormally','abnormal movement of eyelid','spots or clouds in vision',
 'lower body pain','unusual color or odor to urine','abnormal size or shape of ear',
 'posture problems','disturbance of smell or taste','acne or pimples',
 'infant spitting up','apnea'}
BROAD={'đau','ngứa','sưng','yếu','tê','mệt','nóng','lạnh','khó chịu','không khỏe','vấn đề sức khỏe','bệnh'}
FAILURE_NOTES={
 'excessive urination at night':'bi tieu across the assertion prefix can match retention of urine; new phrase is then unmapped.',
 'fluid retention':'Accent removal makes co the (cơ thể) indistinguishable from the uncertainty cue có thể.',
 'incontinence of stool':'Intrinsic không in the symptom phrase is interpreted as negation, not loss of continence.',
 'pupils unequal':'Intrinsic không đều in the symptom phrase is interpreted as negation.'}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_inputs(root=ROOT):
    root=Path(root);catalog=Catalog.load(root)
    entries=json.loads((root/'configs/synonyms.json').read_text(encoding='utf-8'))
    if production_signature(entries)!=PRODUCTION_SIGNATURE:raise ValueError('Production dictionary identity mismatch')
    packets={}
    for name,expected in PACKETS.items():
        path=root/'reports/terminology'/name
        if sha(path)!=expected:raise ValueError('Review packet identity mismatch: '+name)
        with path.open(encoding='utf-8-sig',newline='') as stream:packets[name]=list(csv.DictReader(stream))
    rows=packets['symptom_dictionary_review.csv']
    for name in ('symptom_dictionary_review.csv','symptom_dictionary_changes.csv'):
        if [r['canonical_feature'] for r in packets[name]]!=list(catalog.features):
            raise ValueError('Review canonical order mismatch')
    current=review_rows(root)
    if any(any(old[k]!=str(new[k]) for k in old) for old,new in zip(rows,current)):
        raise ValueError('Review packet does not match source proposals')
    for r in packets['symptom_dictionary_collisions.csv']:
        if not set(r['features'].split('; '))<=set(catalog.features):raise ValueError('Unknown collision feature')
    path=root/'data/evaluation/vietnamese_symptom_semantic_cases.jsonl'
    cases=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    if len(cases)!=86 or len({c['id'] for c in cases})!=86:raise ValueError('Expected original 86 cases')
    for c in cases:
        if not set(c.get('expected_states') or {})<=set(catalog.features):raise ValueError('Unknown case feature')
        if not set(c['forbidden_features'])<=set(catalog.features):raise ValueError('Unknown forbidden feature')
    return catalog,entries,rows,cases,{'packets':dict(PACKETS),'synthetic_cases_sha256':sha(path),
        'production_config_sha256':sha(root/'configs/synonyms.json'),'production_signature':PRODUCTION_SIGNATURE,
        'qualification_script_sha256':sha(Path(__file__)),
        'runtime_policy_sha256':sha(root/'configs/phase5b.json'),
        'source_sha256':{f:sha(root/f) for f in ['src/agent/offline.py','src/agent/extraction.py','src/agent/conversation.py']}}


def fixture_dictionary(entries, approved):
    """Return an in-memory hypothetical dictionary. Caller writes only temp files."""
    value=deepcopy(entries)
    for feature in approved:
        value[feature]['aliases_vi']=list(entries[feature]['proposed_aliases_vi'])
        value[feature]['display_vi']=entries[feature]['proposed_display_vi']
        value[feature]['activation_status']='ACTIVE_EXISTING'
    return value


def engine_for(catalog, dictionary, path):
    Path(path).write_text(json.dumps(dictionary,ensure_ascii=False),encoding='utf-8')
    return OfflineConversation(catalog,OfflineExtractor(catalog,path),Policy.from_file(ROOT/'configs/phase5b.json'),
                               offline_policy=OfflinePolicy.from_file(ROOT/'configs/phase5b.json'))


def nearby_features(feature, features):
    explicit={
        'flatulence':['stomach bloating','abdominal distention'],
        'leg pain':['knee pain','foot or toe pain'],
        'hip pain':['groin pain','lower abdominal pain'],
        'suprapubic pain':['lower abdominal pain','pelvic pain'],
        'skin swelling':['skin rash','itching of skin'],
        'groin mass':['groin pain','lump or mass of breast'],
        'swelling of scrotum':['pain in testicles','itching of scrotum'],
        'mass in scrotum':['swelling of scrotum','pain in testicles'],
        'throat feels tight':['sore throat','difficulty in swallowing']}
    if feature in explicit:return explicit[feature]
    tokens=set(feature.replace(',','').split())-{'or','and','of','in','the','on'}
    generic={'pain','swelling','mass','lump','weakness','stiffness','tightness','cramps','spasms','symptoms','problems','abnormal'}
    scored=[(len(tokens & set(other.replace(',','').split()))+
             3*len((tokens-generic) & set(other.replace(',','').split())),other)
            for other in features if other!=feature]
    result=[f for n,f in sorted(scored,key=lambda p:(-p[0],features.index(p[1]))) if n>0][:2]
    return result or ['fever' if feature!='fever' else 'cough']


def generate_cases(catalog,entries,approved):
    cases=[]
    for feature in catalog.features:
        if feature not in approved:continue
        aliases=entries[feature]['proposed_aliases_vi']
        for alias in aliases:
            for kind,prefix,text,state in [
              ('affirmed','Tôi bị ',alias,'present'),('denied','Tôi không bị ',alias,'denied'),
              ('unaccented','Toi bi ',fold(alias),'present')]:
                cases.append({'feature':feature,'alias':alias,'kind':kind,'text':prefix+text+'.',
                              'expected_states':{feature:state},'forbidden_features':[]})
            cases.append({'feature':feature,'alias':alias,'kind':'substring_boundary',
                'text':'Tôi bị x'+alias+'x.','expected_states':None,'forbidden_features':[feature]})
        for neighbor in nearby_features(feature,list(catalog.features)):
            cases.append({'feature':feature,'alias':'','kind':'near_feature_negative',
                'text':'Tôi bị '+entries[neighbor]['proposed_aliases_vi'][0]+'.',
                'expected_states':None,'forbidden_features':[feature],'neighbor_feature':neighbor})
    for i,c in enumerate(cases):
        c.update(id='activation-'+str(i+1).zfill(4),synthetic=True,
                 scope='HYPOTHETICAL_FIXTURE_ONLY',review_status='pending_human_review')
    return cases


def execute_cases(engine,cases):
    results=[]
    for case in cases:
        r=engine.handle(case['text'])
        if r.reason=='invalid_session':raise RuntimeError('Fixture session capacity/expiry error, not a semantic failure')
        states=(r.sidecar or {}).get('states',{})
        exact=case['expected_states'] is None or states==case['expected_states']
        forbidden=set(case['forbidden_features']) & set(states)
        wrong=set(states)-set(case['expected_states'] or {}) if case['expected_states'] is not None else forbidden
        results.append({'id':case['id'],'feature':case['feature'],'alias':case['alias'],'kind':case['kind'],
            'pass':exact and not forbidden,'actual_states':states,'status':r.status,'reason':r.reason,
            'wrong_feature_ids':sorted(wrong)})
        if r.session_id:engine.store.discard(r.session_id)
    return results


def propose(root=ROOT):
    root=Path(root);catalog,entries,rows,old_cases,identities=read_inputs(root)
    initial=[];decisions=[]
    for row in rows:
        f=row['canonical_feature'];aliases=json.loads(row['proposed_aliases_vi']);status=row['review_status']
        if status=='AMBIGUOUS':decision,reason='HOLD','Source definition or distinct meaning unresolved; do not invent a mapping.'
        elif status=='HIGH_RISK_COLLISION':decision,reason='CLARIFY','Lexical or semantic overlap; preserve current clarification, no expansion.'
        elif row['production_activation']=='ACTIVE_EXISTING':decision,reason='HOLD','Already active: preserve existing aliases only; new variants outside activation scope.'
        elif status!='READY':decision,reason='REVISE','Not READY: wording, context or source review required.'
        elif f in REVISE_SCOPE:decision,reason='REVISE','Broad/composite, subject or safety context requires more precise wording/policy review.'
        elif row['collision_risks'] or any(a.strip() in BROAD or len(fold(a).split())<2 for a in aliases):
            decision,reason='REVISE','Broad or colliding alias; exact matching is not semantic proof.'
        else:
            decision,reason='APPROVE','Proposed for owner approval only, subject to isolated extraction qualification.'
            initial.append(f)
        decisions.append({'canonical_feature':f,'review_status':status,'current_activation':row['production_activation'],
            'decision':decision,'reason':reason,'proposed_aliases_vi':row['proposed_aliases_vi'],
            'display_vi_retained':entries[f]['display_vi'],'production_changed':False,
            'test_cases':0,'test_failures':0,'clinical_review':'NOT_CLINICALLY_VALIDATED'})
    special={
        'gum pain':'Cần publisher phân biệt gum pain/pain in gums; không tự gán hai nghĩa cho cùng đau nướu.',
        'pain in gums':'Cần publisher phân biệt gum pain/pain in gums; không tự gán hai nghĩa cho cùng đau nướu.',
        'shortness of breath':'Chưa xác minh khác biệt với difficulty breathing; giữ guard/alias hiện có, không mở rộng.',
        'difficulty breathing':'Chưa xác minh khác biệt với shortness of breath; không tự tạo mapping khác bằng bản dịch.',
        'difficulty speaking':'Phân biệt nói khó, nói líu, nói lắp và khó giao tiếp; không tự thêm alias nói không rõ.',
        'slurring words':'Cần mô tả phát âm/líu tiếng cụ thể, không gộp với nói khó hoặc nói lắp.',
        'stuttering or stammering':'Cần mô tả nói lắp cụ thể; không gộp mọi khó khăn giao tiếp.',
        'frequent urination':'Phân biệt số lần đi tiểu với tổng lượng; không dùng tiểu nhiều đơn thuần.',
        'polyuria':'Phân biệt tổng lượng với số lần đi tiểu; giữ pending tới khi mapping đủ rõ.',
        'heartburn':'Không tự gộp ợ nóng với mọi đau ngực kiểu nóng rát hoặc suy ra bệnh trào ngược.',
        'burning chest pain':'Cần mô tả vị trí/tính chất, không tự xem là heartburn.',
        'neck pain':'Giữ phân biệt cổ/cơ có dấu và hỏi lại khi không dấu; không mở rộng alias mới.',
        'muscle pain':'Giữ phân biệt cơ/cổ có dấu và hỏi lại khi không dấu; không mở rộng alias mới.'}
    for row in decisions:
        if row['canonical_feature'] in special:row['reason']=special[row['canonical_feature']]
    with tempfile.TemporaryDirectory(prefix='symptom-activation-review-') as tmp:
        engine=engine_for(catalog,fixture_dictionary(entries,initial),Path(tmp)/'hypothetical.json')
        initial_cases=generate_cases(catalog,entries,set(initial))
        initial_results=execute_cases(engine,initial_cases)
        failed={r['feature'] for r in initial_results if not r['pass']}
        for row in decisions:
            results=[r for r in initial_results if r['feature']==row['canonical_feature']]
            row['test_cases']=len(results);row['test_failures']=sum(not r['pass'] for r in results)
            if row['canonical_feature'] in failed:
                row.update(decision='REVISE',reason='Isolated fixture failed: '+FAILURE_NOTES.get(row['canonical_feature'],
                    'extraction/state/context/boundary incompatibility.')+' No production fix or bypass.')
        approved={r['canonical_feature'] for r in decisions if r['decision']=='APPROVE'}
        final_cases=generate_cases(catalog,entries,approved)
        final_engine=engine_for(catalog,fixture_dictionary(entries,approved),Path(tmp)/'final-proposal.json')
        final_results=execute_cases(final_engine,final_cases)
        if any(not r['pass'] for r in final_results):raise ValueError('Final hypothetical batch does not pass; stop')
        # Existing cases remain production expectations; do not rewrite their
        # forbidden pending features just to qualify a hypothetical activation.
        production=engine_for(catalog,entries,Path(tmp)/'unchanged-production.json')
        for c in old_cases:
            r=production.handle(c['text']);states=(r.sidecar or {}).get('states',{})
            if (c['expected_states'] is not None and states!=c['expected_states'] or
                    set(c['forbidden_features']) & set(states) or r.status=='extraction_ready'):
                raise ValueError('Existing production synthetic regression failed: '+c['id'])
    broad_or_overlap=[]
    for row in rows:
        for alias in json.loads(row['proposed_aliases_vi']):
            if row['collision_risks'] or alias in BROAD:
                broad_or_overlap.append((row['canonical_feature'],alias))
    summary={'status':'PROPOSED_NOT_ACTIVATED','input_identities':identities,
        'decision_counts':dict(Counter(r['decision'] for r in decisions)),
        'ready_pending_initial':sum(r['review_status']=='READY' and r['production_activation']=='PENDING_REVIEW' for r in rows),
        'static_candidates':len(initial),'qualified_new_features':len(approved),
        'current_active_features':135,'projected_active_features':135+len(approved),
        'current_pending_features':240,'projected_pending_features':240-len(approved),
        'initial_fixture_cases':len(initial_results),'initial_failures':sum(not r['pass'] for r in initial_results),
        'final_fixture_cases':len(final_results),'final_fixture_failures':sum(not r['pass'] for r in final_results),
        'proposed_new_aliases':sum(len(entries[f]['proposed_aliases_vi']) for f in approved),
        'observed_wrong_feature_events_initial':sum(bool(r['wrong_feature_ids']) for r in initial_results),
        'observed_wrong_feature_events_final':sum(bool(r['wrong_feature_ids']) for r in final_results),
        'new_context_risk_aliases':len({(r['feature'],r['alias']) for r in initial_results if not r['pass']}),
        'risk_flagged_feature_alias_pairs':len(broad_or_overlap),'risk_flagged_features':len({f for f,a in broad_or_overlap}),
        'production_existing_cases_passed':len(old_cases),'production_changed':False,
        'models_fitted':0,'predictions_called':False,'test_payload_opened':False,
        'limitation':'Synthetic mechanics only, not a clinical false-positive rate or proof of semantic safety.'}
    if production_signature(json.loads((root/'configs/synonyms.json').read_text(encoding='utf-8')))!=PRODUCTION_SIGNATURE:
        raise ValueError('Production dictionary was changed')
    if sha(root/'configs/synonyms.json')!=identities['production_config_sha256']:
        raise ValueError('Production source file changed')
    return decisions,final_cases,{'summary':summary,'initial_results':initial_results,'final_results':final_results}


def main():
    from src.models.ensemble import phase4_guard
    from scripts.package_handover import validate_pins
    validate_pins(ROOT)
    with phase4_guard(ROOT) as guard:
        decisions,cases,evidence=propose()
        if any(guard.values()):raise ValueError('Protected operation attempted')
        evidence['summary']['guard_counts']=dict(guard)
    folder=ROOT/'reports/terminology'
    receipt=write_table(folder/'symptom_activation_decisions.csv',decisions)
    (ROOT/'data/evaluation/vietnamese_symptom_activation_cases.jsonl').write_text(
        ''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in cases),encoding='utf-8')
    (folder/'symptom_activation_validation.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'decisions':receipt,**evidence['summary']},ensure_ascii=True))


if __name__=='__main__':main()
