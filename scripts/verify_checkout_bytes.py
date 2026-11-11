"""Check Git working bytes; optionally repair only proven CRLF/LF drift.

No reset/clean/renormalize, no dataset access, no model or notebook execution.
Default is read-only. Repair requires a clean index, external backup and zero
content changes. Reviewed HEAD bytes remain the authority, never a new hash.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

TEXT = {'.py','.json','.jsonl','.ipynb','.md','.txt','.toml','.ps1','.csv','.yml','.yaml','.js','.css','.html'}


def digest(value):return hashlib.sha256(value).hexdigest()


def inspect(root, blobs):
    rows=[]
    for name,expected in blobs.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()) or path.is_symlink() or not path.is_file():
            rows.append(dict(path=name,kind='MISSING_OR_UNSAFE'));continue
        actual=path.read_bytes()
        if actual==expected:continue
        text=path.suffix in TEXT or path.name in {'.gitignore','.gitattributes'}
        kind=('EOL_ONLY' if text and actual.replace(b'\r\n',b'\n')==expected.replace(b'\r\n',b'\n') else 'CONTENT_CHANGE')
        rows.append(dict(path=name,kind=kind,actual_sha256=digest(actual),head_sha256=digest(expected)))
    return rows


def repair(root, blobs, backup):
    root=root.resolve();backup=backup.resolve()
    if backup.is_relative_to(root) or backup.exists():
        raise ValueError('Use a new backup directory outside the checkout')
    rows=inspect(root,blobs)
    if any(row['kind']!='EOL_ONLY' for row in rows):
        raise ValueError('Content changes or missing files: stop, back up and review manually')
    originals={r['path']:(root/r['path']).read_bytes() for r in rows}
    backup.mkdir(parents=True,exist_ok=False)
    for row in rows:
        dest=backup/row['path'];dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as stream:stream.write(originals[row['path']])
        assert digest(dest.read_bytes())==row['actual_sha256']
    (backup/'receipt.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    changed=[]
    try:
        for row in rows:
            p=root/row['path']
            assert p.read_bytes()==originals[row['path']], 'File changed during repair'
            p.write_bytes(blobs[row['path']]);changed.append(row['path'])
        assert not inspect(root,blobs)
    except BaseException:
        for name in changed:(root/name).write_bytes(originals[name])
        raise
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repair-eol',action='store_true')
    parser.add_argument('--backup-root',type=Path)
    args=parser.parse_args()
    root=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip()).resolve()
    # Read committed blobs, not the possibly converted working copy or staged content.
    entries=subprocess.check_output(['git','ls-tree','-rz','HEAD'],cwd=root).split(b'\0')
    blobs={}
    for entry in entries:
        if not entry:continue
        meta,name=entry.split(b'\t',1);mode,kind,oid=meta.decode().split()
        if kind!='blob' or mode not in {'100644','100755'}:raise ValueError('Unsupported Git entry')
        blobs[name.decode('utf-8')]=subprocess.check_output(['git','cat-file','blob',oid],cwd=root)
    rows=inspect(root,blobs)
    if args.repair_eol:
        if args.backup_root is None:parser.error('--repair-eol requires --backup-root outside checkout')
        if subprocess.run(['git','diff','--quiet'],cwd=root).returncode or subprocess.run(['git','diff','--cached','--quiet'],cwd=root).returncode:
            raise ValueError('Git has local/staged changes: stop, preserve them first')
        rows=repair(root,blobs,args.backup_root)
        print(json.dumps(dict(status='PASS',repaired_files=len(rows),backup=str(args.backup_root.resolve()))))
    else:
        print(json.dumps(dict(status='PASS' if not rows else 'REVIEW',files=len(blobs),differences=rows),indent=2))
        if rows:raise SystemExit(2)


if __name__=='__main__':main()
