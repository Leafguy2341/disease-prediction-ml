"""Paired synthetic challenge: semantic recovery of rule-missed symptoms.

Research only. No classifier, LLM API, production mutation or automatic acceptance.
The gold-confirmation calculation is an explicitly labelled oracle upper bound.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from time import perf_counter

import numpy as np

from scripts.nlp_symptom_research import (
    ROOT, MODEL_ID, MODEL_REVISION, engine, rule_extract, load_semantic,
    Catalog, Turn, evidence_context, ExtractionError, NEGATIVE, UNCERTAIN, fold,
)

GROUPS = ('known_alias', 'novel_expression', 'multiple_symptoms',
          'negation_subject', 'ambiguous')
CASE_FILE = 'data/evaluation/vietnamese_nlp_missed_v1.jsonl'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_challenge(root=ROOT):
    cases = [json.loads(s) for s in (Path(root)/CASE_FILE).read_text(encoding='utf-8').splitlines() if s.strip()]
    features = set(Catalog.load(root).features)
    assert len({c['id'] for c in cases}) == len(cases)
    assert set(c['group'] for c in cases) == set(GROUPS)
    for c in cases:
        assert c['synthetic'] and c['review_status'] == 'pending_human_review'
        assert set(c['expected_states']) <= features
        assert set(c['expected_states'].values()) <= {'present', 'denied', 'uncertain'}
        for s in c['gold_spans']:
            assert c['text'][s['start']:s['end']] == s['text']
            assert s['feature'] in features
    return cases


def unresolved_proposals(text, matcher, catalog, base=None, k=3):
    """Same segmenter/context gate for Semantic and Hybrid.

    Hybrid masks only rule evidence spans, never the whole utterance or a whole
    TopK list. Remaining text retains original offsets/context. Already resolved
    features are excluded individually before TopK. No similarity cutoff is fit.
    """
    base = base or {'states': {}, 'evidence': {}}
    masked = list(text)
    for spans in base.get('evidence', {}).values():
        for s in spans:
            assert text[s['start']:s['end']] == s['text']
            masked[s['start']:s['end']] = ' ' * (s['end']-s['start'])
    masked = ''.join(masked)
    turn = Turn('u1', 'user', text, 'self')
    proposals, calls, milliseconds = [], 0, 0.
    # Coordinating conjunctions split multiple symptoms without losing offsets.
    boundaries = list(re.finditer(r'[,;.!?\n]+|\b(?:và|với lại|nhưng)\b', text, re.I))
    begin = 0
    for end, following in [(m.start(), m.end()) for m in boundaries]+[(len(text), len(text))]:
        original = text[begin:end]
        query = masked[begin:end].strip()
        start = begin
        begin = following
        # Do not embed subject/filler remaining after a fully matched rule span.
        residual = fold(query)
        residual = re.sub(r'\b(?:toi|bi|dang|hien tai|co|thay|cam thay|tu sang nay)\b', ' ', residual)
        if not re.search(r'[a-z0-9]', residual):
            continue
        span = dict(turn_id='u1', start=start, end=end, text=original)
        state = 'uncertain' if UNCERTAIN.search(original) else 'denied' if NEGATIVE.search(original) else 'present'
        try:
            evidence_context(turn, span, 'self', state)
        except ExtractionError:
            continue
        # Existing research quarantine: never treat fiction/quoted text as self.
        if re.search(r'\b(nhan vat|trong truyen|trich dan|trong sach|ban toi|nguoi khac)\b', fold(text)):
            continue
        tick = perf_counter()
        vector = np.asarray(matcher.encode([query]), dtype=float)[0]
        calls += 1
        milliseconds += (perf_counter()-tick)*1000
        if vector.shape != (matcher.vectors.shape[1],) or not np.isfinite(vector).all() or np.linalg.norm(vector) == 0:
            raise ValueError('invalid_query_embedding')
        scores = matcher.vectors @ (vector/np.linalg.norm(vector))
        ids = [i for i in np.argsort(-scores, kind='stable') if matcher.features[i] not in base['states']][:k]
        proposals.append(dict(evidence=span, query=query, state=state,
            candidates=[dict(feature=matcher.features[i], cosine_similarity=float(scores[i])) for i in ids],
            requires_confirmation=True))
    return proposals, calls, milliseconds


def pairs(proposals, k=3, present_only=False):
    return {(c['feature'], p['state']) for p in proposals
            if not present_only or p['state'] == 'present' for c in p['candidates'][:k]}


def oracle_confirmation(case, base, proposals):
    """Perfect annotation-based answers, NOT real users or measured accuracy."""
    gold = set(case['expected_states'].items())
    accepted = pairs(proposals) & gold
    states = dict(base)
    for feature, state in accepted:
        if feature not in states:
            states[feature] = state
    return states


def summarize(rows):
    result = []
    for group in ('all', *GROUPS):
        subset = [r for r in rows if group == 'all' or r['group'] == group]
        for method in ('rule_based', 'semantic', 'hybrid'):
            denom = sum(len(r['missed_present']) for r in subset)
            at1 = at3 = feature_hits = candidate_fp = proposed_present = tp = fp = retained_loss = 0
            ambiguous_questions = ambiguous_committed = 0
            calls = queries = questions = oracle_tp = oracle_fp = oracle_fn = 0
            protected = [r for r in subset if r['group'] == 'negation_subject']
            exposed = committed_exposed = 0
            for r in subset:
                m = r['methods'][method]
                gold = set(r['expected_states'].items())
                missed = {tuple(v) for v in r['missed_present']}
                p1, p3 = pairs(m['suggestions'], 1, True), pairs(m['suggestions'], 3, True)
                at1 += len(missed & p1); at3 += len(missed & p3)
                feature_hits += len({f for f, _ in missed} & {f for f, _ in pairs(m['suggestions'])})
                committed = set(m['states'].items())
                # Ambiguous gold={} means abstain, NOT exhaustive feature negatives.
                if r['group'] != 'ambiguous':
                    candidate_fp += len(p3-gold); proposed_present += len(p3)
                    tp += len(committed & gold); fp += len(committed-gold)
                else:
                    ambiguous_questions += len(m['suggestions'])
                    ambiguous_committed += bool(committed)
                retained_loss += len(set(r['methods']['rule_based']['states'].items())-committed)
                calls += m['embedding_calls']; queries += int(m['embedding_calls'] > 0)
                questions += len(m['suggestions'])  # one candidate-list question per segment
                oracle = set(m['oracle_states'].items())
                oracle_tp += len(oracle & gold); oracle_fp += len(oracle-gold); oracle_fn += len(gold-oracle)
                if r['group'] == 'negation_subject':
                    exposed += bool(p3-gold)
                    committed_exposed += bool({p for p in committed-gold if p[1] == 'present'})
            latencies = [r['methods'][method]['latency_ms'] for r in subset]
            result.append(dict(group=group, method=method, cases=len(subset),
                rule_missed_present_pairs=denom, missed_hits_at_1=at1, missed_hits_at_3=at3,
                missed_recall_at_1=at1/denom if denom else None,
                missed_recall_at_3=at3/denom if denom else None,
                feature_only_missed_recall_at_3=feature_hits/denom if denom else None,
                candidate_present_pairs=proposed_present, candidate_false_present_pairs=candidate_fp,
                candidate_false_discovery_fraction=candidate_fp/proposed_present if proposed_present else None,
                protected_cases=len(protected), protected_candidate_exposure_rate=exposed/len(protected) if protected else None,
                protected_committed_false_positive_rate=committed_exposed/len(protected) if protected else None,
                committed_precision=tp/(tp+fp) if tp+fp else None,
                committed_true_pairs=tp, committed_false_pairs=fp,
                rule_states_lost=retained_loss,
                ambiguous_candidate_questions=ambiguous_questions,
                ambiguous_automatic_assignment_cases=ambiguous_committed,
                oracle_precision=oracle_tp/(oracle_tp+oracle_fp) if oracle_tp+oracle_fp else None,
                oracle_recall=oracle_tp/(oracle_tp+oracle_fn) if oracle_tp+oracle_fn else None,
                real_user_post_confirmation_precision=None,
                embedding_calls=calls, utterances_requiring_embedding=queries,
                candidate_list_questions=questions, questions_per_utterance=questions/len(subset) if subset else None,
                latency_p50_ms=float(np.percentile(latencies, 50)) if latencies else None,
                latency_p95_ms=float(np.percentile(latencies, 95)) if latencies else None))
    return result


def analyze(cases, matcher, root=ROOT):
    e = engine(root); rows = []
    for case in cases:
        base = rule_extract(case['text'], root, e)
        methods = dict(rule_based=dict(states=base['states'], suggestions=[],
            embedding_calls=0, embedding_ms=0., latency_ms=base['latency_ms'], oracle_states=base['states']))
        for name in ('semantic', 'hybrid'):
            tick = perf_counter()
            proposals, calls, embedding_ms = unresolved_proposals(
                case['text'], matcher, e.catalog, base if name == 'hybrid' else None)
            states = base['states'] if name == 'hybrid' else {}
            methods[name] = dict(states=dict(states), suggestions=proposals, embedding_calls=calls,
                embedding_ms=embedding_ms, latency_ms=(perf_counter()-tick)*1000+(base['latency_ms'] if name == 'hybrid' else 0),
                oracle_states=oracle_confirmation(case, states, proposals))
        missed = {(f, s) for f, s in case['expected_states'].items()
                  if s == 'present' and base['states'].get(f) != s}
        rows.append(dict(**case, missed_present=sorted(missed), methods=methods))
    return dict(protocol='rule-missed-recovery-v1', rows=rows, summary=summarize(rows),
        confirmation='Actual states unchanged; oracle_states use perfect gold answers: upper bound only, no real user confirmation',
        question_unit='One candidate-list question per unresolved segment; not number of conversation turns or measured user answers',
        latency_scope='Warm-up separate; one sequential local pass, no SLA; excludes model load and catalog encoding',
        limitations='Small authored diagnostic challenge, not independent clinical validation. Groups fixed before inference; rule misses measured, not selected after scores.',
        models_fitted=0, disease_predictions_called=False, locked_test_opened=False, llm_api_calls=0)


def render(folder, packet):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    summary = packet['summary']
    for method in ('rule_based', 'semantic', 'hybrid'):
        vals = [next(v for v in summary if v['group'] == g and v['method'] == method) for g in GROUPS]
        x = np.arange(len(GROUPS)) + {'rule_based':-.24, 'semantic':0, 'hybrid':.24}[method]
        for ax, key in zip(axes, ('missed_recall_at_3', 'questions_per_utterance', 'utterances_requiring_embedding')):
            ax.bar(x, [v[key] if v[key] is not None else 0 for v in vals], .23, label=method)
    for ax, title in zip(axes, ('Recall@3 on rule-missed present symptoms', 'Candidate-list questions / utterance', 'Utterances using query embedding')):
        ax.set_title(title, fontsize=9); ax.set_xticks(np.arange(5), GROUPS, rotation=35, ha='right'); ax.set_ylim(bottom=0)
    axes[0].set_ylim(0, 1.08)
    axes[0].text(0, 1.01, 'No missed pairs: N/A (drawn at zero)', fontsize=8)
    axes[0].legend(fontsize=8)
    fig.suptitle('Authored synthetic challenge | retrieval candidates, NOT confirmed additions')
    fig.tight_layout(); fig.savefig(folder/'missed_recovery.png', dpi=145); plt.close(fig)


def run(output, embedding_snapshot, root=ROOT):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Never overwrite previous evidence')
    tick = perf_counter()
    records = json.loads((Path(root)/'reports/nlp_research_v1/coverage_inventory.json').read_text(encoding='utf-8'))['features']
    matcher, environment = load_semantic(embedding_snapshot, records)
    if matcher is None:
        raise RuntimeError('Verified local embedding required')
    load_ms = (perf_counter()-tick)*1000
    tick = perf_counter(); matcher.encode(['Câu khởi động tổng hợp.']); warmup_ms = (perf_counter()-tick)*1000
    packet = analyze(load_challenge(root), matcher, root)
    packet.update(semantic_environment=environment, model_load_and_catalog_ms=load_ms, warmup_ms=warmup_ms,
        model_id=MODEL_ID, revision=MODEL_REVISION,
        inputs_sha256={name:digest(Path(root)/name) for name in (CASE_FILE,
            'configs/synonyms.json', 'configs/phase5b.json', 'scripts/nlp_missed_symptom_analysis.py',
            'scripts/nlp_symptom_research.py', 'src/agent/extraction.py', 'src/agent/offline.py',
            'reports/nlp_research_v1/coverage_inventory.json')})
    output.mkdir(parents=True)
    (output/'missed_analysis.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    render(output, packet)
    manifest = dict(complete=True, protocol=packet['protocol'],
        files={p.name:digest(p) for p in output.iterdir() if p.is_file()})
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return packet


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--embedding-snapshot', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output, args.embedding_snapshot)
    print(json.dumps(dict(summary=result['summary'], output=str(args.output)), ensure_ascii=False))
