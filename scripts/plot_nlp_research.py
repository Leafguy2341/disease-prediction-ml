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


def render_activation(folder, dictionary):
    """Current dictionary coverage, independent of frozen NLP benchmark figures."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=Path(folder);dictionary=Path(dictionary)
    manifest_path=folder/'manifest.json'
    release=json.loads(manifest_path.read_text(encoding='utf-8'))
    before_raw=(folder/'synonyms.before.json').read_bytes()
    after_raw=dictionary.read_bytes()
    if (hashlib.sha256(before_raw).hexdigest()!=release['before_sha256']
            or hashlib.sha256(after_raw).hexdigest()!=release['current_sha256']):
        raise ValueError('Activation dictionary/release checksum mismatch')
    before=json.loads(before_raw);after=json.loads(after_raw)
    if list(before)!=list(after) or len(after)!=375:
        raise ValueError('Canonical order mismatch')
    counts=[sum(e['activation_status']=='ACTIVE_EXISTING' for e in d.values()) for d in (before,after)]
    aliases=[sum(len(e['aliases_vi']) for e in d.values() if e['activation_status']=='ACTIVE_EXISTING') for d in (before,after)]
    pending=[len(after)-n for n in counts]
    fig,ax=plt.subplots(figsize=(9,5.5))
    labels=['Trước kích hoạt','Hiện tại']
    ax.bar(labels,counts,color='#247d75',label='Feature active',width=.5)
    ax.bar(labels,pending,bottom=counts,color='#d7dee2',label='Feature pending',width=.5)
    for i,(active,wait) in enumerate(zip(counts,pending)):
        ax.text(i,active/2,f'{active} active\n{active/375:.0%}',ha='center',va='center',color='white',weight='bold',fontsize=12)
        if wait:ax.text(i,active+wait/2,f'{wait} pending',ha='center',va='center',color='#26343e')
        ax.text(i,383,f'{aliases[i]} alias Việt',ha='center',fontsize=10)
    ax.set_ylim(0,425);ax.set_yticks([0,75,150,225,300,375]);ax.set_ylabel('Số feature trong schema 375')
    ax.set_title('Activation Coverage — từ điển hiện hành',pad=12)
    ax.legend(loc='upper center',ncol=2,fontsize=9,frameon=False)
    ax.spines[['top','right']].set_visible(False)
    fig.text(.03,.05,'Nguồn: configs/synonyms.json và activation-20261118/manifest.json.',fontsize=9)
    fig.text(.03,.015,'Coverage từ điển, không phải độ chính xác extraction hoặc thẩm định y khoa.',fontsize=9)
    fig.tight_layout(rect=(0,.09,1,1))
    figure=folder/'activation_coverage.png';fig.savefig(figure,dpi=150);plt.close(fig)
    receipt=dict(kind='current_dictionary_activation_coverage',active_before=counts[0],active_after=counts[1],
        pending_after=pending[1],active_aliases_before=aliases[0],active_aliases_after=aliases[1],
        dictionary_sha256=release['current_sha256'],before_sha256=release['before_sha256'],
        figure='activation_coverage.png',figure_sha256=hashlib.sha256(figure.read_bytes()).hexdigest(),
        historical_benchmark_figures_modified=False,models_fitted=0,locked_test_opened=False)
    receipt_path=folder/'activation_figure_manifest.json'
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for p in (figure,receipt_path):
        release['files'][p.name]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    manifest_path.write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return receipt


def render_run(folder):
    """Figures use only benchmark.json from THIS run; no historical snapshot reuse."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=Path(folder);data=json.loads((folder/'benchmark.json').read_text(encoding='utf-8'))
    figures=[]
    fig,ax=plt.subplots(figsize=(12,4));ax.set_xlim(0,10);ax.set_ylim(0,3);ax.axis('off')
    pipelines=[('Rule-based',('Exact aliases','Context validator','Validated states')),
               ('Semantic',('Clause embeddings','Top-K + context','Candidates; confirm')),
               ('Hybrid',('Validated rules','Retrieve residuals','States + candidates'))]
    for y,(label,steps) in zip((2.5,1.5,.5),pipelines):
        ax.text(.1,y,label,ha='left',va='center',weight='bold')
        for x,step in zip((3,5.9,8.8),steps):
            ax.text(x,y,step,ha='center',va='center',bbox=dict(boxstyle='round,pad=.5',fc='#e9f2f1',ec='#43817b'))
        for x in (4.1,7):ax.annotate('',xy=(x+.7,y),xytext=(x,y),arrowprops=dict(arrowstyle='->'))
    ax.set_title('Method overview — conceptual flow, not measured performance')
    fig.tight_layout();name='methods_overview.png';fig.savefig(folder/name,dpi=140);plt.close(fig);figures.append(name)
    for split,methods in data['results'].items():
        available={k:v for k,v in methods.items() if 'metrics' in v}
        names=list(available);x=list(range(len(names)))
        fig,ax=plt.subplots(figsize=(9,4))
        for i,(key,label) in enumerate([('precision','Precision'),('recall','Recall'),('micro_f1','Micro F1')]):
            bars=ax.bar([j+(i-1)*.24 for j in x],[v['metrics'][key] for v in available.values()],width=.24,label=label)
            ax.bar_label(bars,fmt='%.3f',fontsize=8)
        ax.set_xticks(x,names);ax.set_ylim(0,1.15);ax.legend(loc='lower left');ax.set_ylabel('Feature-state metric')
        ax.set_title(split+' — confirmed extraction states')
        fig.text(.02,.01,'Synthetic evaluation. Semantic candidates are not confirmed states; see retrieval chart.',fontsize=8)
        fig.tight_layout(rect=(0,.06,1,1));name=split+'_extraction.png';fig.savefig(folder/name,dpi=140);plt.close(fig);figures.append(name)
        candidates={k:v['candidate_metrics'] for k,v in available.items() if 'candidate_metrics' in v}
        if candidates:
            fig,ax=plt.subplots(figsize=(8,4));names=list(candidates);x=list(range(len(names)))
            for i,(key,label) in enumerate([('recall_at_1','Recall@1'),('recall_at_3','Recall@3'),('precision_at_3','Precision@3')]):
                bars=ax.bar([j+(i-1)*.24 for j in x],[v[key] or 0 for v in candidates.values()],width=.24,label=label);ax.bar_label(bars,fmt='%.3f',fontsize=8)
            ax.set_xticks(x,names);ax.set_ylim(0,1.15);ax.legend(loc='lower left');ax.set_ylabel('Retrieval metric')
            ax.set_title(split+' — unconfirmed feature-state candidates')
            fig.text(.02,.01,'Measured top-K retrieval; cosine similarity is not a medical probability.',fontsize=8)
            fig.tight_layout(rect=(0,.06,1,1));name=split+'_retrieval.png';fig.savefig(folder/name,dpi=140);plt.close(fig);figures.append(name)
        fig,axes=plt.subplots(1,2,figsize=(10,4))
        for ax,key,title in zip(axes,('latency_p50_ms','latency_p95_ms'),('p50 latency','p95 latency')):
            bars=ax.bar(list(available),[v['metrics'][key] for v in available.values()]);ax.bar_label(bars,fmt='%.2f');ax.set_ylim(bottom=0);ax.set_title(title);ax.set_ylabel('ms / utterance')
        fig.suptitle(split+' — one measured local pass');fig.tight_layout();name=split+'_latency.png';fig.savefig(folder/name,dpi=140);plt.close(fig);figures.append(name)
        fig,axes=plt.subplots(1,2,figsize=(11,4))
        names=list(available);x=list(range(len(names)))
        for ax,key,title in zip(axes,('mapped_features','confirmation_rate'),('Mapped canonical features / 375','Clarification or confirmation rate')):
            values=[v['metrics'].get(key,0) for v in available.values()]
            bars=ax.bar(names,values);ax.bar_label(bars,fmt='%.2f');ax.set_ylim(0,375 if key=='mapped_features' else 1.15);ax.set_title(title)
        fig.suptitle(split+' — coverage and dialogue needs');fig.tight_layout();name=split+'_coverage_confirmation.png';fig.savefig(folder/name,dpi=140);plt.close(fig);figures.append(name)
    manifest=dict(source='benchmark.json in the same run folder',
        benchmark_sha256=hashlib.sha256((folder/'benchmark.json').read_bytes()).hexdigest(),
        figures={n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in figures})
    comparison=folder/'case_comparison.json'
    manifest['comparison_sha256']=hashlib.sha256(comparison.read_bytes()).hexdigest() if comparison.is_file() else None
    manifest['complete']=comparison.is_file()
    (folder/'run_figures.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


if __name__=='__main__':
    import argparse
    from scripts.nlp_symptom_research import ROOT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activation-release',type=Path)
    args=parser.parse_args()
    result=render_activation(args.activation_release,ROOT/'configs/synonyms.json') if args.activation_release else render(ROOT/'reports/nlp_research_v1')
    print(json.dumps(result,ensure_ascii=False,indent=2))
