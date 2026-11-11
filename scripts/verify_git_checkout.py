"""Real offline HTTP proof from a checkout, forbidding the old PC source tree."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forbid-source',type=Path,required=True)
    parser.add_argument('--storage-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    source=args.forbid_source.resolve();checkout=Path(__file__).resolve().parents[1]
    dependencies=source/'.venv-web'
    assert not checkout.is_relative_to(source), 'Run from the separate checkout'
    blocked=[]
    def audit(event,values):
        if event not in {'open','os.listdir','os.scandir'} or not values or not isinstance(values[0],(str,bytes,os.PathLike)):return
        p=Path(os.fsdecode(values[0])).resolve()
        if p.name=='test.csv.gz':
            blocked.append('locked-test');raise RuntimeError('Locked test access forbidden')
        if p.is_relative_to(source) and not p.is_relative_to(dependencies):
            blocked.append('original-source');raise RuntimeError('Original PC source/artifact access forbidden')
    sys.addaudithook(audit)
    os.environ['DISEASE_API_STORAGE_ROOT']=str(args.storage_root.resolve())
    os.environ['DISEASE_CHAT_MODE']='offline'
    os.environ['DISEASE_SMOKE_OUTPUT']=str(args.output.resolve())
    from scripts.academic_runtime_smoke import main as smoke
    smoke()
    paths={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
           if n.startswith(('src.','app.','scripts.')) and getattr(m,'__file__',None)}
    assert all(Path(p).is_relative_to(checkout) for p in paths.values()), paths
    assert not blocked,blocked
    proof=json.loads(args.output.read_text(encoding='utf-8'))
    proof.update(checkout=str(checkout),old_pc_source_access_attempts=blocked,loaded_project_modules=paths,
                 dependency_environment_reused=str(dependencies),no_old_pc_project_dependency=True)
    args.output.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
