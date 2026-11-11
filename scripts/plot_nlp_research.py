"""Render only measured NLP results, never execute extraction or ML inference."""
import hashlib
import json
from pathlib import Path


def render(folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=Path(folder);result=json.loads((folder/'benchmark.json').read_text(encoding='utf-8'))
    metrics={k:v['rule_based']['metrics'] for k,v in result['results'].items()}
    labels=['Development (synthetic)','Reserved v1 (synthetic)']
    x=list(range(len(metrics)));fig,ax=plt.subplots(figsize=(9,4))
    for i,(key,name) in enumerate([('precision','Precision'),('recall','Recall'),('micro_f1','Micro F1')]):
        values=[m[key] for m in metrics.values()]
        bars=ax.bar([n+(i-1)*.23 for n in x],values,width=.23,label=name)
        ax.bar_label(bars,fmt='%.4f',fontsize=8)
    ax.set_xticks(x,labels);ax.set_ylim(0,1.14);ax.set_ylabel('Feature + assertion metric (0–1)');ax.legend(loc='lower left')
    ax.set_title('Rule-based initial baseline BEFORE guard repair; semantic/hybrid NOT RUN')
    fig.text(.02,.01,'Source: benchmark.json; synthetic, pending human review; fully annotated cases only.',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,1));fig.savefig(folder/'rule_metrics.png',dpi=140);plt.close(fig)
    counts=metrics['reserved_synthetic_evaluation']['false_positive_contexts']
    fig,ax=plt.subplots(figsize=(7,4));bars=ax.bar(list(counts),list(counts.values()));ax.bar_label(bars)
    ax.set_ylim(0,max([1,*counts.values()])+1);ax.set_ylabel('False positive feature-state pairs')
    ax.set_title('Reserved synthetic v1: initial rule context errors (before fix)')
    fig.text(.02,.01,'Source: benchmark.json; no post-fix held-out improvement claim.',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,1));fig.savefig(folder/'context_errors.png',dpi=140);plt.close(fig)
    inv=json.loads((folder/'context_after_fix.json').read_text(encoding='utf-8'))['summary']
    fig,ax=plt.subplots(figsize=(7,4));bars=ax.bar(['Active before','Active after','Canonical descriptions'],[135,inv['production_features'],inv['description_coverage']]);ax.bar_label(bars)
    ax.set_ylim(0,400);ax.set_ylabel('Canonical features (denominator 375)');ax.set_title('Vietnamese dictionary coverage: descriptions do not imply activation')
    fig.text(.02,.01,'Source: coverage inventory and context_after_fix.json; no new production aliases.',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,1));fig.savefig(folder/'activation_coverage.png',dpi=140);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4))
    for i,(key,name) in enumerate([('latency_p50_ms','p50'),('latency_p95_ms','p95')]):
        bars=ax.bar([n+(i-.5)*.3 for n in x],[m[key] for m in metrics.values()],width=.3,label=name);ax.bar_label(bars,fmt='%.2f')
    ax.set_xticks(x,labels);ax.set_ylim(bottom=0);ax.set_ylabel('Milliseconds per utterance');ax.legend();ax.set_title('Initial rule latency; single local pass, not API SLA')
    fig.text(.02,.01,'Source: benchmark.json; excludes model load, disease inference and network.',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,1));fig.savefig(folder/'rule_latency.png',dpi=140);plt.close(fig)
    files=['benchmark.json','coverage_inventory.json','context_after_fix.json','canonical_375.csv',
           'rule_metrics.png','context_errors.png','activation_coverage.png','rule_latency.png']
    manifest=dict(source='Measured synthetic NLP mechanics only; no semantic/hybrid result chart',
                  files={n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in files})
    (folder/'figure_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


if __name__=='__main__':
    from scripts.nlp_symptom_research import ROOT
    print(json.dumps(render(ROOT/'reports/nlp_research_v1'),indent=2))
