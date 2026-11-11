"""Offline NLP research only. Never imported by the website or disease classifier.

Uses the actual production conversation/extraction/validator for rule baseline.
Semantic suggestions require confirmation: they cannot become clinical facts.
No network or model download; optional embeddings come from a pinned local snapshot.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics
import tempfile
from time import perf_counter

from src.agent.extraction import (Catalog, Turn, ExtractionValidator, ExtractionError,
                                  evidence_context, extraction_schema, NEGATIVE, UNCERTAIN)
from src.agent.offline import OfflineConversation, OfflineExtractor, OfflinePolicy, fold
from src.agent.conversation import Policy

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
MODEL_REVISION = 'e8f8c211226b894fcb81acc59f3b34ba3efd5f42'
MODEL_SOURCE = 'https://huggingface.co/' + MODEL_ID


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def engine(root=ROOT, dictionary=None):
    root = Path(root)
    catalog = Catalog.load(root)
    return OfflineConversation(catalog, OfflineExtractor(catalog, dictionary or root/'configs/synonyms.json'),
        Policy.from_file(root/'configs/phase5b.json'), offline_policy=OfflinePolicy.from_file(root/'configs/phase5b.json'))


def rule_extract(text, root=ROOT, instance=None):
    e = instance or engine(root)
    start = perf_counter()
    result = e.handle(text)  # No prediction service supplied, no disease model loaded.
    try:
        sidecar = result.sidecar or {}
        states = sidecar.get('states', {})
        evidence = sidecar.get('evidence', {})
        if result.session_id and evidence:
            turns = {t.turn_id:t.text for t in e.store.get(result.session_id).turns}
            for spans in evidence.values():
                for s in spans:
                    assert turns[s['turn_id']][s['start']:s['end']] == s['text']
        assert result.predictions is None
        return dict(states=dict(states), evidence=evidence, status=result.status, reason=result.reason,
            confirmation_required=result.status == 'clarification_required',
            latency_ms=(perf_counter()-start)*1000)
    finally:
        if result.session_id:
            e.store.discard(result.session_id)


def candidate_contexts(alias, feature):
    """Development-only qualification templates; never the reserved NLP evaluation."""
    return [
        ('affirmed', 'Tôi bị '+alias+'.', {feature:'present'}),
        ('denied', 'Tôi không bị '+alias+'.', {feature:'denied'}),
        ('uncertain', 'Tôi chưa chắc bị '+alias+'.', {feature:'uncertain'}),
        ('unaccented', 'Toi bi '+fold(alias)+'.', {feature:'present'}),
        ('other_subject', 'Mẹ tôi bị '+alias+'.', {}),
        ('hypothetical', 'Giả sử tôi bị '+alias+' thì sao?', {}),
        ('fiction', 'Nhân vật trong truyện bị '+alias+'.', {}),
        ('quoted', 'Tôi đọc câu "'+alias+'" trong sách.', {}),
        ('knowledge', alias+' là gì?', {}),
        ('boundary', 'Tôi bị x'+alias+'x.', {}),
    ]


def inventory(root=ROOT):
    """Complete canonical descriptions + per-alias tests in disposable dictionaries.

    Passing templates is CONTEXT_TESTED, never authorization to mutate production.
    Old collisions/semantic decisions remain authoritative review blockers.
    """
    root = Path(root); catalog = Catalog.load(root)
    entries = json.loads((root/'configs/synonyms.json').read_text(encoding='utf-8'))
    with (root/'reports/terminology/symptom_dictionary_review.csv').open(encoding='utf-8-sig',newline='') as f:
        reviews = {r['canonical_feature']:r for r in csv.DictReader(f)}
    with (root/'reports/terminology/symptom_activation_decisions.csv').open(encoding='utf-8-sig',newline='') as f:
        decisions = {r['canonical_feature']:r for r in csv.DictReader(f)}
    assert list(entries) == list(catalog.features) == list(reviews) == list(decisions)
    collisions = defaultdict(set)
    for feature, entry in entries.items():
        for alias in entry['proposed_aliases_vi']:
            collisions[fold(alias)].add(feature)
    rows, qualification = [], []
    before = sha(root/'configs/synonyms.json')
    with tempfile.TemporaryDirectory(prefix='nlp-qualification-') as tmp:
        for feature in catalog.features:
            entry = entries[feature]; review = reviews[feature]; decision = decisions[feature]
            aliases = entry['proposed_aliases_vi']
            assert entry['display_vi'] and entry['semantic_notes'] and aliases
            # Activate exactly one proposed feature only in a disposable fixture.
            candidate = deepcopy(entries)
            candidate[feature]['aliases_vi'] = aliases
            candidate[feature]['activation_status'] = 'ACTIVE_EXISTING'
            path = Path(tmp)/'dictionary.json'
            path.write_text(json.dumps(candidate,ensure_ascii=False),encoding='utf-8')
            probe = engine(root,path); tested = []
            for alias in aliases:
                checks=[]
                for kind,text,expected in candidate_contexts(alias,feature):
                    out=rule_extract(text,root,probe)
                    checks.append(dict(kind=kind,text=text,expected_states=expected,actual_states=out['states'],
                                       passed=out['states']==expected))
                collision_with=sorted(collisions[fold(alias)]-{feature})
                passed=all(c['passed'] for c in checks) and not collision_with
                tested.append(dict(alias_vi=alias,lifecycle='CONTEXT_TESTED' if passed else 'REVIEW_REQUIRED',
                    collision_features=collision_with,checks=checks))
            active = entry['activation_status']=='ACTIVE_EXISTING'
            blockers=[]
            if not active:
                if decision['decision']!='APPROVE':blockers.append('existing_decision_'+decision['decision'])
                if any(t['collision_features'] for t in tested):blockers.append('folded_alias_collision')
                if any(not all(c['passed'] for c in t['checks']) for t in tested):blockers.append('context_or_mapping_regression')
                if review['collision_risks']:blockers.append('semantic_overlap_review')
                blockers.append('activation_requires_batch_qualification_and_explicit_release_review')
            rows.append(dict(order=len(rows),canonical_feature=feature,display_vi=entry['proposed_display_vi'],
                description_vi=entry['semantic_notes'],aliases_vi=aliases,production_aliases_vi=entry['aliases_vi'] if active else [],
                easily_confused_features=[v for v in review['collision_risks'].split('; ') if v],
                forbidden_contexts=['other_subject','hypothetical','fiction','quoted','knowledge','past_without_current','word_substring'],
                reference_sources=entry.get('reference_sources',[]),source_status=entry.get('source_status','NOT_INDEPENDENTLY_VERIFIED'),
                reference_scope=entry.get('reference_scope','No independent term source verified'),
                lexical_review=review['review_status'],clinical_review='NOT_CLINICALLY_VALIDATED',
                review_decision=decision['decision'],lifecycle='PRODUCTION_ACTIVE' if active else
                    'CONTEXT_TESTED' if all(t['lifecycle']=='CONTEXT_TESTED' for t in tested) else 'REVIEW_REQUIRED',
                production_active=active,activation_blockers=blockers))
            qualification.append(dict(canonical_feature=feature,aliases=tested))
    assert sha(root/'configs/synonyms.json')==before
    summary=dict(canonical_features=len(rows),description_coverage=sum(bool(r['display_vi'] and r['description_vi']) for r in rows),
        proposed_aliases=sum(len(r['aliases_vi']) for r in rows),proposed_lexical_feature_coverage=sum(bool(r['aliases_vi']) for r in rows),
        production_features=sum(r['production_active'] for r in rows),
        production_vi_aliases=sum(len(r['production_aliases_vi']) for r in rows),
        lifecycle=dict(Counter(r['lifecycle'] for r in rows)),
        pending_context_tested=sum(not r['production_active'] and r['lifecycle']=='CONTEXT_TESTED' for r in rows),
        pending_context_failed=sum(not r['production_active'] and r['lifecycle']=='REVIEW_REQUIRED' for r in rows),
        alias_context_checks=sum(len(a['checks']) for q in qualification for a in q['aliases']),
        failed_checks=sum(not c['passed'] for q in qualification for a in q['aliases'] for c in a['checks']),
        proposed_folded_collisions=[dict(alias=k,features=sorted(v)) for k,v in collisions.items() if len(v)>1],
        activation='NONE; disposable tests do not constitute a production release',synonyms_sha256_before=before,synonyms_sha256_after=before)
    for r in rows:
        r['lexical_lifecycle']='LEXICALLY_REVIEWED' if r['lexical_review']=='READY' else 'REVIEW_REQUIRED'
        r['stages_completed']=['DRAFT']
        if r['lexical_lifecycle']=='LEXICALLY_REVIEWED':r['stages_completed'].append('LEXICALLY_REVIEWED')
        if r['lifecycle']=='CONTEXT_TESTED':r['stages_completed'].append('CONTEXT_TESTED')
        if r['production_active']:r['stages_completed'].append('PRODUCTION_ACTIVE')
    return dict(summary=summary,features=rows,qualification=qualification,
        stage_semantics='Internal lexical review and finite synthetic context checks only; no clinical validation, no auto-activation')


def load_cases(root=ROOT):
    root=Path(root)
    development=[json.loads(s) for s in (root/'data/evaluation/vietnamese_symptom_semantic_cases.jsonl').read_text(encoding='utf-8').splitlines()]
    reserved=[json.loads(s) for s in (root/'data/evaluation/vietnamese_nlp_reserved_v1.jsonl').read_text(encoding='utf-8').splitlines()]
    assert not {fold(c['text']) for c in development}&{fold(c['text']) for c in reserved}
    catalog=Catalog.load(root)
    protocol=json.loads((root/'configs/nlp_research.json').read_text(encoding='utf-8'))
    if sha(root/protocol['reserved'])!=protocol['reserved_sha256']:
        raise ValueError('reserved_nlp_fixture_identity_mismatch')
    for case in development+reserved:
        assert case['synthetic'] and case['review_status']=='pending_human_review'
        assert set(case.get('expected_states') or {})<=set(catalog.features)
        for span in case.get('expected_evidence',[]):
            assert case['text'][span['start']:span['end']]==span['text']
    return dict(development=development,reserved_synthetic_evaluation=reserved)


def metrics(cases, results):
    assert len(cases)==len(results)
    tp=fp=fn=exact=0; classes=defaultdict(lambda:[0,0,0]); errors=Counter(); forbidden=0
    complete=0; covered=set(); latencies=[]
    for c,r in zip(cases,results):
        predicted=r['states'];covered.update(predicted);latencies.append(r['latency_ms'])
        forbidden+=len(set(c.get('forbidden_features',[]))&set(predicted))
        if c.get('expected_states') is None:continue  # Partial labels never treated as exhaustive negatives.
        complete+=1
        gold=set(c['expected_states'].items()); pred=set(predicted.items())
        tp+=len(gold&pred);fp+=len(pred-gold);fn+=len(gold-pred);exact+=gold==pred
        for feature,state in gold|pred:
            a=classes[(feature,state)]
            a[0]+=int((feature,state) in gold&pred);a[1]+=int((feature,state) in pred-gold);a[2]+=int((feature,state) in gold-pred)
        if pred-gold:errors[c['kind']]+=len(pred-gold)
    precision=tp/(tp+fp) if tp+fp else 0.;recall=tp/(tp+fn) if tp+fn else 0.
    supported=[2*a/(2*a+b+c) if 2*a+b+c else 0. for a,b,c in classes.values()]
    ordered=sorted(latencies)
    return dict(cases=len(cases),fully_annotated_cases=complete,partial_label_cases=len(cases)-complete,
        tp=tp,fp=fp,fn=fn,precision=precision,recall=recall,micro_f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.,
        macro_f1_observed_feature_state_pairs=sum(supported)/len(supported) if supported else None,
        macro_denominator=len(supported),macro_definition='union of gold/predicted (feature, assertion) pairs on fully annotated cases; zero_division=0, not disease labels',
        exact_set_match=exact/complete if complete else None,exact_denominator=complete,
        false_positive_contexts=dict(errors),forbidden_feature_violations=forbidden,
        mapped_features=len(covered),canonical_feature_denominator=375,
        confirmation_rate=sum(r['confirmation_required'] for r in results)/len(results) if results else None,
        confirmation_definition='clarification_required or semantic suggestion awaiting user confirmation; not successful user resolution',
        latency_p50_ms=statistics.median(ordered) if ordered else None,
        latency_p95_ms=ordered[min(len(ordered)-1,int(.95*len(ordered)))] if ordered else None)


class SemanticCandidates:
    """Research retrieval on clause spans. No guessed threshold or silent activation."""
    def __init__(self, records, encode):
        import numpy as np
        self.features=[r['canonical_feature'] for r in records]
        if self.features!=list(Catalog.load(ROOT).features):raise ValueError('semantic_catalog_schema_order_mismatch')
        self.encode=encode
        self.vectors=np.asarray(encode([r['display_vi']+'. '+r['description_vi'] for r in records]),dtype=float)
        if self.vectors.ndim!=2 or len(self.vectors)!=375 or not np.isfinite(self.vectors).all():raise ValueError('invalid_embedding_matrix')
        norms=np.linalg.norm(self.vectors,axis=1,keepdims=True)
        if (norms<=0).any():raise ValueError('zero_embedding')
        self.vectors=self.vectors/norms

    def retrieve(self,text,catalog,k=3):
        import numpy as np
        suggestions=[]
        # Whole clauses preserve assertion and subject cues; offsets stay in original text.
        for m in re.finditer(r'[^,;.!?\n]+',text):
            span=dict(turn_id='u1',start=m.start(),end=m.end(),text=m.group())
            turn=Turn('u1','user',text,'self')
            state='uncertain' if UNCERTAIN.search(m.group()) else 'denied' if NEGATIVE.search(m.group()) else 'present'
            try:evidence_context(turn,span,'self',state)
            except ExtractionError:continue
            # Conservative research-only quarantine in addition to existing validator.
            if re.search(r'\b(nhan vat|trong truyen|trich dan|trong sach|ban toi|nguoi khac)\b',fold(text)):continue
            vector=np.asarray(self.encode([m.group()]),dtype=float)[0]
            if not np.isfinite(vector).all() or np.linalg.norm(vector)==0:raise ValueError('invalid_query_embedding')
            scores=self.vectors@(vector/np.linalg.norm(vector))
            ids=np.argsort(-scores,kind='stable')[:k]
            suggestions.append(dict(evidence=span,state=state,candidates=[dict(feature=self.features[i],cosine_similarity=float(scores[i])) for i in ids],requires_confirmation=True))
        return suggestions


def verify_embedding_snapshot(folder):
    folder=Path(folder).resolve();manifest=json.loads((folder/'research_snapshot.json').read_text(encoding='utf-8'))
    if manifest.get('model_id')!=MODEL_ID or manifest.get('revision')!=MODEL_REVISION:raise ValueError('embedding_identity_mismatch')
    listed=manifest.get('files',{})
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name!='research_snapshot.json'}
    if not listed or set(listed)!=actual or not any(n.endswith('.safetensors') for n in listed):raise ValueError('incomplete_snapshot')
    for name,expected in listed.items():
        path=folder/name
        if path.is_symlink() or not path.resolve().is_relative_to(folder) or sha(path)!=expected:raise ValueError('embedding_checksum_mismatch')
    return manifest


def load_semantic(folder,records):
    if not folder:return None,dict(status='NOT RUN',reason='No pinned local embedding snapshot configured',model_id=MODEL_ID,revision=MODEL_REVISION)
    manifest=verify_embedding_snapshot(folder)
    try:from sentence_transformers import SentenceTransformer
    except ImportError:return None,dict(status='NOT RUN',reason='sentence-transformers missing in research interpreter',model_id=MODEL_ID,revision=MODEL_REVISION)
    start=perf_counter()
    model=SentenceTransformer(str(Path(folder).resolve()),local_files_only=True,trust_remote_code=False,device='cpu')
    matcher=SemanticCandidates(records,lambda texts:model.encode(texts,show_progress_bar=False,convert_to_numpy=True))
    return matcher,dict(status='LOADED',model_id=MODEL_ID,revision=MODEL_REVISION,snapshot_manifest=manifest,load_and_catalog_ms=(perf_counter()-start)*1000)


def benchmark(root=ROOT, matcher=None):
    splits=load_cases(root); e=engine(root); all_results={}
    for split,cases in splits.items():
        rows=[dict(id=c['id'],**rule_extract(c['text'],root,e)) for c in cases]
        methods={'rule_based':dict(status='RUN',metrics=metrics(cases,rows),rows=rows)}
        if matcher is None:
            methods.update({name:dict(status='NOT RUN',reason='No verified local embedding model loaded') for name in ('semantic','hybrid')})
        else:
            for name in ('semantic','hybrid'):
                candidate_rows=[]
                for c,base in zip(cases,rows):
                    start=perf_counter();proposals=matcher.retrieve(c['text'],e.catalog)
                    # No unvalidated similarity threshold: suggestions remain unconfirmed.
                    # Hybrid preserves explicit rule states; semantic alone abstains.
                    proposals=[p for p in proposals if not any(v['feature'] in base['states'] for v in p['candidates'])] if name=='hybrid' else proposals
                    candidate_rows.append(dict(id=c['id'],states=base['states'] if name=='hybrid' else {},
                        suggestions=proposals,confirmation_required=bool(proposals),latency_ms=(perf_counter()-start)*1000+(base['latency_ms'] if name=='hybrid' else 0)))
                methods[name]=dict(status='RUN_CONFIRMATION_ONLY',metrics=metrics(cases,candidate_rows),rows=candidate_rows,
                    note='Candidate retrieval only; no automatic threshold, no simulated user confirmation, no semantic production activation')
        all_results[split]=methods
    return dict(protocol='vietnamese-nlp-research-v1',synthetic=True,human_review='pending_human_review',
        threshold_selection='NONE; candidate-only semantic mode, no test optimization',
        split_policy='86 historical fixtures development only; new reserved synthetic cases excluded from alias/context qualification',
        results=all_results,models_fitted=0,disease_predictions_called=False,locked_test_opened=False,network_calls=0)


def run(output,root=ROOT,embedding_snapshot=None):
    output=Path(output)
    if output.exists():raise FileExistsError('Use a new research output folder; never overwrite evidence')
    packet=inventory(root);matcher,semantic=load_semantic(embedding_snapshot,packet['features'])
    result=benchmark(root,matcher);result['semantic_environment']=semantic
    result['inputs_sha256']={n:sha(Path(root)/n) for n in ('configs/synonyms.json','configs/phase5b.json','artifacts/metadata/phase2/feature_schema.json','artifacts/metadata/phase2/label_mapping.json','data/evaluation/vietnamese_symptom_semantic_cases.jsonl','data/evaluation/vietnamese_nlp_reserved_v1.jsonl','scripts/nlp_symptom_research.py')}
    output.mkdir(parents=True)
    for name,data in [('coverage_inventory.json',packet),('benchmark.json',result)]:
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (output/'canonical_375.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(packet['features'][0]));writer.writeheader()
        writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()} for row in packet['features'])
    return packet,result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--embedding-snapshot',type=Path)
    args=parser.parse_args();packet,result=run(args.output,embedding_snapshot=args.embedding_snapshot)
    print(json.dumps(dict(coverage=packet['summary'],rule_based={k:v['rule_based']['metrics'] for k,v in result['results'].items()},semantic=result['semantic_environment']),ensure_ascii=False,indent=2))
