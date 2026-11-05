"""Explicit historical packet replay; current production is checked separately."""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import json
from scripts.activate_reviewed_symptoms import ROOT, RELEASE


def activation_manifest():
    path=RELEASE/'manifest.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'activated_features':[]}


@contextmanager
def original_dictionary():
    backup=RELEASE/'synonyms.before.json'
    if not backup.exists():
        yield
        return
    raw=backup.read_bytes()
    read_text,read_bytes=Path.read_text,Path.read_bytes
    target=ROOT/'configs/synonyms.json'
    def text(path,*a,**k):
        return raw.decode('utf-8') if path==target else read_text(path,*a,**k)
    def binary(path,*a,**k):
        return raw if path==target else read_bytes(path,*a,**k)
    with patch.object(Path,'read_text',text),patch.object(Path,'read_bytes',binary):
        yield
