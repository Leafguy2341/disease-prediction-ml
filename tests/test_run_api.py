"""Launcher contract only; no model loads, server, dataset or network."""
import runpy
import sys
from pathlib import Path
from unittest.mock import Mock
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_launcher_environment(monkeypatch):
    monkeypatch.delenv('DISEASE_API_STORAGE_ROOT', raising=False)


def test_local_launcher_contract(monkeypatch):
    import uvicorn
    run = Mock()
    monkeypatch.setattr(uvicorn, 'run', run)
    monkeypatch.setattr(sys, 'argv', ['run_api.py'])
    runpy.run_path(str(ROOT/'run_api.py'), run_name='__main__')
    run.assert_called_once_with('app.backend.main:app', host='127.0.0.1', port=8000, workers=1, reload=False)
    import os
    assert os.environ['DISEASE_API_STORAGE_ROOT']==str(ROOT.resolve())


def test_explicit_storage_override_is_preserved(monkeypatch,tmp_path):
    import os,uvicorn
    monkeypatch.setenv('DISEASE_API_STORAGE_ROOT',str(tmp_path))
    monkeypatch.setattr(uvicorn,'run',Mock())
    monkeypatch.setattr(sys,'argv',['run_api.py'])
    runpy.run_path(str(ROOT/'run_api.py'),run_name='__main__')
    assert os.environ['DISEASE_API_STORAGE_ROOT']==str(tmp_path)


@pytest.mark.parametrize('port', ['0','65536','bad'])
def test_invalid_port_rejected(monkeypatch, port):
    import uvicorn
    run = Mock()
    monkeypatch.setattr(uvicorn, 'run', run)
    monkeypatch.setattr(sys, 'argv', ['run_api.py','--port',port])
    with pytest.raises(SystemExit):
        runpy.run_path(str(ROOT/'run_api.py'), run_name='__main__')
    run.assert_not_called()
