"""Read-only dictionary review inventory; never translates or edits schema."""
import json
import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path
from src.agent.extraction import Catalog
from src.agent.offline import OfflineExtractor, fold
from src.agent.presentation import PredictionPresenter

STATUS_DEFINITIONS = {
    'READY':'Đề xuất rõ nghĩa và qua kiểm tra kỹ thuật; chưa phải phê duyệt kích hoạt hoặc chuyên gia y khoa thẩm định.',
    'REVIEW':'Cần người duyệt cách diễn đạt, phạm vi hoặc tương đương ngữ nghĩa trước khi kích hoạt.',
    'AMBIGUOUS':'Chưa rõ nghĩa/phạm vi nhãn nguồn, nhãn tổng hợp hoặc chưa phân biệt được với nhãn khác.',
    'HIGH_RISK_COLLISION':'Có collision từ vựng/bỏ dấu hoặc rủi ro chồng lấn; cần câu trả lời cụ thể hoặc định nghĩa nguồn.'}

NEAR_GROUPS = [
    {'polyuria','frequent urination'}, {'gum pain','pain in gums'},
    {'swollen abdomen','abdominal distention','stomach bloating'},
    {'shortness of breath','difficulty breathing'},
    {'difficulty speaking','slurring words','stuttering or stammering'},
    {'heartburn','burning chest pain'}, {'paresthesia','loss of sensation'},
    {'nasal congestion','sinus congestion','coryza'},
    {'eye deviation','cross-eyed'}]


def production_signature(entries):
    fields=('display_vi','aliases_vi','aliases_en','activation_status','question_eligible','question_group')
    value=[(f,{k:e.get(k) for k in fields}) for f,e in entries.items()]
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def collision_rows(entries, *, proposed=True):
    index={}
    for f,e in entries.items():
        if not proposed and e.get('activation_status')=='PENDING_REVIEW':
            continue
        aliases=e.get('proposed_aliases_vi',e['aliases_vi']) if proposed else e['aliases_vi']
        for alias in aliases:index.setdefault(fold(alias),set()).add(f)
    rows=[]
    for key,features in sorted(index.items()):
        if len(features)<2:continue
        rows.append({'kind':'FOLDED_ALIAS_COLLISION','alias_or_group':key,
            'features':'; '.join(sorted(features)),
            'handling':'Ưu tiên exact có dấu; khi nhiều candidate phải hỏi rõ, không fuzzy-map.',
            'scope':'proposed_only' if proposed else 'current_aliases'})
    for features in NEAR_GROUPS:
        rows.append({'kind':'SEMANTIC_OVERLAP_RISK','alias_or_group':' / '.join(sorted(features)),
            'features':'; '.join(sorted(features)),
            'handling':'Không gộp; hỏi mô tả cụ thể. Nhãn trùng nghĩa cần publisher giải thích, không tự tạo khác biệt.',
            'scope':'semantic_review_not_runtime_collision'})
    return rows


def write_table(path, rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return {'path':str(path.resolve()),'rows':len(rows),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def review_rows(root):
    root=Path(root)
    catalog=Catalog.load(root)
    entries=json.loads((root/'configs/synonyms.json').read_text(encoding='utf-8'))
    if set(entries)!=set(catalog.features): raise ValueError('review_schema_mismatch')
    index={}
    for f,e in entries.items():
        for a in e.get('proposed_aliases_vi',e['aliases_vi']):
            index.setdefault(fold(a),set()).add(f)
    near=NEAR_GROUPS
    rows=[]
    for f in catalog.features:
        e=entries[f]
        proposed=e.get('proposed_aliases_vi',e['aliases_vi'])
        risks=set().union(*(index[fold(a)]-{f} for a in proposed))
        for pair in near:
            if f in pair: risks.update(pair-{f})
        status='HIGH_RISK_COLLISION' if risks and e['review_status']!='AMBIGUOUS' else e['review_status']
        if status=='READY' and e['confidence']!='HIGH':
            raise ValueError('ready_requires_high_linguistic_confidence')
        rows.append({'canonical_feature':f,'proposed_display_vi':e.get('proposed_display_vi',e['display_vi']),
            'proposed_aliases_vi':json.dumps(proposed,ensure_ascii=False),
            'semantic_notes':e['semantic_notes'],'confidence':e['confidence'],
            'collision_risks':'; '.join(sorted(risks)),'needs_review':e['needs_review'],
            'review_status':status,'production_activation':e['activation_status'],
            'reference_sources':'; '.join(e.get('reference_sources',[])),
            'source_status':e.get('source_status','NOT_INDEPENDENTLY_VERIFIED'),
            'reference_scope':e.get('reference_scope','Chưa xác minh định nghĩa nhãn dataset với nhà phát hành.'),
            'activation_recommendation':'ELIGIBLE_AFTER_OWNER_APPROVAL' if status=='READY' else
                'SOURCE_DEFINITION_REQUIRED' if status=='AMBIGUOUS' else 'CLARIFY_OR_REVIEW_FIRST',
            'clinical_review':'NOT_CLINICALLY_VALIDATED',
            'production_aliases_vi':json.dumps(e['aliases_vi'],ensure_ascii=False)})
    if len(rows)!=375 or any(not r['proposed_display_vi'] or json.loads(r['proposed_aliases_vi'])==[] for r in rows):
        raise ValueError('incomplete_review_packet')
    return rows


def write_review_csv(root, destination):
    rows=review_rows(root)
    return {**write_table(destination,rows),
            'status_counts':dict(Counter(r['review_status'] for r in rows)),
            'production_activation_counts':dict(Counter(r['production_activation'] for r in rows))}


def main(review_csv=None):
    root = Path(__file__).resolve().parents[1]
    extractor = OfflineExtractor(Catalog.load(root), root / 'configs/synonyms.json')
    entries = extractor.synonyms
    covered = sum(bool(e['aliases_vi']) for e in entries.values())
    report = {'features': len(entries), 'features_with_vi_alias': covered,
              'vi_coverage_percent': 100 * covered / len(entries),
              'needs_review': [f for f, e in entries.items() if e['needs_review']],
              'missing_vi_alias': [f for f, e in entries.items() if not e['aliases_vi']],
              'missing_display_vi': [f for f, e in entries.items() if not e['display_vi'].strip()],
              'untranslated_display_placeholders': [f for f, e in entries.items() if e['display_vi'] == f],
              'alias_collisions': {a: sorted(fs) for a, fs in extractor.aliases.items() if len(fs) > 1},
              'dangerous_short_aliases': {a: sorted(fs) for a, fs in extractor.aliases.items() if len(a) <= 3},
              'fuzzy_risk_note': 'Short and colliding aliases require review; fuzzy assignment is disabled.',
              'fuzzy_matching': False}
    report['disease_translations'] = PredictionPresenter.load(root, extractor.catalog).coverage()
    names = json.loads((root / 'configs/disease_names_vi.json').read_text(encoding='utf-8'))
    report['terminology_feature_status'] = dict(Counter(e.get('terminology_status','MISSING') for e in entries.values()))
    report['terminology_disease_status'] = dict(Counter(e.get('terminology_status','MISSING') for e in names.values()))
    report['question_eligible'] = [f for f,e in entries.items() if e.get('question_eligible')]
    report['reference_sources'] = {f:e['reference_sources'] for f,e in entries.items() if e.get('reference_sources')}
    report['review_scope'] = 'Terminology references and owner display approval are not clinical validation.'
    report['active_vi_features']=[f for f,e in entries.items() if e['aliases_vi'] and e.get('activation_status')!='PENDING_REVIEW']
    report['review_status_counts']=dict(Counter(r['review_status'] for r in review_rows(root)))
    report['candidate_coverage_note']='375 proposals are not 375 active production aliases; new candidates require review.'
    report['status_definitions']=STATUS_DEFINITIONS
    report['needs_review_definition']='Cần người duyệt/phê duyệt trước thay đổi production; độc lập với readiness và medical validation.'
    report['confidence_definition']='Đánh giá tương đương ngôn ngữ HIGH/MEDIUM/LOW; không phải score model hoặc clinical confidence.'
    report['production_signature']=production_signature(entries)
    report['source_status_counts']=dict(Counter(r['source_status'] for r in review_rows(root)))
    report['proposed_collisions']=collision_rows(entries)
    if review_csv:
        report['review_packet']=write_review_csv(root,review_csv)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-csv',help='Export all 375 proposed terms without activating aliases')
    main(parser.parse_args().review_csv)
