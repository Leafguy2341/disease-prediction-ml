"""Read-only Git/LFS data integrity checks. Never parse CSV/NPZ/joblib or fit models."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
MANIFEST='artifacts/metadata/repository_data_manifest.json'


def sha_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def verify_inventory(root, manifest):
    root=Path(root).resolve();checked=0;size=0;lfs=0
    for name,expected in manifest['files'].items():
        relative=PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
            raise ValueError('Invalid manifest path: '+name)
        path=root.joinpath(*relative.parts)
        if not path.resolve().is_relative_to(root) or path.is_symlink():raise ValueError('Linked/outside artifact: '+name)
        if not path.is_file():raise ValueError('Missing repository data: '+name+'; run git lfs pull if needed')
        if expected.get('git_storage')=='lfs':
            with path.open('rb') as stream:prefix=stream.read(160)
            if prefix.startswith(b'version https://git-lfs.github.com/spec/v1'):
                raise ValueError('LFS pointer without payload: '+name+'; run git lfs pull')
            lfs+=1
        if path.stat().st_size!=expected['bytes'] or sha_file(path)!=expected['sha256']:
            raise ValueError('Data checksum/size mismatch: '+name)
        checked+=1;size+=expected['bytes']
    return dict(status='PASS',files_checked=checked,bytes_checked=size,lfs_payloads_verified=lfs,
                payloads_parsed=False,models_fitted=0,test_evaluated=False)


def verify(root=ROOT, *, allow_locked_bytes=False):
    if not allow_locked_bytes:
        raise ValueError('Explicit --allow-locked-bytes required: checksum-only access, never test evaluation')
    root=Path(root).resolve()
    manifest=json.loads((root/MANIFEST).read_text(encoding='utf-8'))
    result=verify_inventory(root,manifest)
    # Reuse the audited data-release verifier instead of a parallel model loader.
    from scripts.package_handover import verify_data,_verify_current_final_bundle
    files,_=verify_data(root,root,allow_locked_bytes=True)
    result['frozen_data_files_verified']=len(files)
    result['final_bundle']=_verify_current_final_bundle(root,files)
    result['locked_test_bytes_hashed_only']=True
    result['split_or_model_payload_parsed']=False
    result['notebooks_executed']=0
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--allow-locked-bytes',action='store_true')
    args=parser.parse_args()
    print(json.dumps(verify(args.root,allow_locked_bytes=args.allow_locked_bytes),indent=2))
