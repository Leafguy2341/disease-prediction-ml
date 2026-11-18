"""Owner-authorized lexical activation, not clinical validation or model training."""
from collections import Counter
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path

from src.agent.extraction import Catalog
from src.agent.offline import OfflineExtractor, fold

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT/'reports/terminology/activation-20261118'
BEFORE_SHA256 = '036d756fb202612122a31e8a041e60e98a33cc632a7caa41df25ccfe2689d527'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def activate_entries(before, features):
    """Activate the existing Vietnamese aliases; preserve meanings and all other fields."""
    if list(before) != list(features) or len(before) != 375:
        raise ValueError('Canonical schema/order mismatch')
    if Counter(e['activation_status'] for e in before.values()) != {'ACTIVE_EXISTING':135,'PENDING_REVIEW':240}:
        raise ValueError('Unexpected dictionary state; do not overwrite a different release')
    after = deepcopy(before)
    activated = []
    for feature, entry in after.items():
        if not entry['display_vi'].strip() or not entry['aliases_vi'] or not all(isinstance(a,str) and a.strip() for a in entry['aliases_vi']):
            raise ValueError('Missing Vietnamese aliases: '+feature)
        if entry['activation_status'] == 'PENDING_REVIEW':
            entry['activation_status'] = 'ACTIVE_EXISTING'
            activated.append(feature)
    return after, activated


def run(root=ROOT, release=RELEASE):
    root=Path(root);release=Path(release);path=root/'configs/synonyms.json'
    original=path.read_bytes()
    if release.exists():
        manifest=json.loads((release/'manifest.json').read_text(encoding='utf-8'))
        if sha(original) != manifest['current_sha256']:
            raise ValueError('Release exists but production differs; refusing to overwrite')
        return manifest
    if sha(original) != BEFORE_SHA256:
        raise ValueError('Production dictionary differs from the owner-authorized starting state')
    catalog=Catalog.load(root)
    before=json.loads(original)
    after,activated=activate_entries(before,catalog.features)
    raw=(json.dumps(after,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    release.mkdir(parents=True)
    with (release/'synonyms.before.json').open('xb') as out:out.write(original)
    # No aliases are added/reworded; the 240 existing runtime entries become active.
    with (release/'synonyms.after.json').open('xb') as out:out.write(raw)
    provider=OfflineExtractor(catalog,release/'synonyms.after.json')
    for feature,entry in after.items():
        for alias in entry['aliases_vi']:
            if feature not in provider.candidates(alias):raise ValueError('Alias is absent from runtime index: '+feature)
    folded={}
    for feature,entry in after.items():
        for alias in entry['aliases_vi']:folded.setdefault(fold(alias),set()).add(feature)
    collisions=[dict(folded_alias=a,features=sorted(fs)) for a,fs in sorted(folded.items()) if len(fs)>1]
    # A release inventory rather than a medical review packet. Historical packets stay intact.
    with (release/'feature_coverage.csv').open('w',encoding='utf-8-sig',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=['order','canonical_feature','display_vi','aliases_vi','previous_status','current_status','newly_activated','clinical_review'])
        writer.writeheader()
        for i,(feature,entry) in enumerate(after.items()):
            writer.writerow(dict(order=i,canonical_feature=feature,display_vi=entry['display_vi'],
                aliases_vi=json.dumps(entry['aliases_vi'],ensure_ascii=False),previous_status=before[feature]['activation_status'],
                current_status=entry['activation_status'],newly_activated=feature in activated,clinical_review='NOT_CLINICALLY_VALIDATED'))
    manifest=dict(status='ACTIVATED_BY_OWNER',version=2,release_id='activation-20261118',
        owner_authorization='Owner requested all 375 features active, waived per-term human approval; no clinical validation claimed.',
        before_sha256=sha(original),current_sha256=sha(raw),activated_features=activated,
        active_features_before=135,active_features_after=375,pending_features_after=0,
        active_vi_aliases_before=sum(len(e['aliases_vi']) for e in before.values() if e['activation_status']=='ACTIVE_EXISTING'),
        active_vi_aliases_after=sum(len(e['aliases_vi']) for e in after.values()),
        aliases_reworded=0,clinical_review='NOT_CLINICALLY_VALIDATED',
        collision_policy='Existing accented precedence; unaccented multi-candidate aliases ask clarification, never arbitrary mapping.',
        folded_collisions=collisions,validation_scope='Canonical order/complete alias index/config integrity; not clinical evaluation or natural-language accuracy.',
        full_suite_run=False,models_fitted=0,llm_api_calls=0,locked_test_opened=False)
    # Write production only after snapshot and index integrity have succeeded.
    path.write_bytes(raw)
    if path.read_bytes()!=raw:raise RuntimeError('Dictionary write verification failed; original bytes retained in release snapshot')
    manifest['files']={p.name:dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size) for p in release.iterdir() if p.is_file()}
    with (release/'manifest.json').open('x',encoding='utf-8') as out:json.dump(manifest,out,ensure_ascii=False,indent=2)
    return manifest


if __name__=='__main__':
    result=run()
    print(json.dumps({k:result[k] for k in ('status','active_features_before','active_features_after','active_vi_aliases_after','pending_features_after','current_sha256')},indent=2))
