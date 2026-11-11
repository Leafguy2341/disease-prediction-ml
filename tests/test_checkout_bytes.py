"""Synthetic byte fixtures; no Git init, notebooks, model or dataset execution."""
import pytest
from scripts.verify_checkout_bytes import inspect,repair


def test_exact_bytes_are_clean(tmp_path):
    (tmp_path/'a.py').write_bytes(b'x=1\n')
    assert inspect(tmp_path,{'a.py':b'x=1\n'})==[]


def test_eol_repair_preserves_original_backup(tmp_path):
    root=tmp_path/'checkout';root.mkdir();p=root/'a.py';p.write_bytes(b'x=1\r\n')
    backup=tmp_path/'backup'
    assert inspect(root,{'a.py':b'x=1\n'})[0]['kind']=='EOL_ONLY'
    repair(root,{'a.py':b'x=1\n'},backup)
    assert p.read_bytes()==b'x=1\n'
    assert (backup/'a.py').read_bytes()==b'x=1\r\n'


def test_real_edits_prevent_all_writes(tmp_path):
    root=tmp_path/'checkout';root.mkdir()
    (root/'a.py').write_bytes(b'x=2\r\n');(root/'b.py').write_bytes(b'x=1\r\n')
    with pytest.raises(ValueError,match='Content changes'):
        repair(root,{'a.py':b'x=1\n','b.py':b'x=1\n'},tmp_path/'backup')
    assert (root/'b.py').read_bytes()==b'x=1\r\n'
    assert not (tmp_path/'backup').exists()


def test_in_checkout_backup_is_rejected(tmp_path):
    with pytest.raises(ValueError,match='outside'):
        repair(tmp_path,{},tmp_path/'backup')


def test_binary_is_never_repaired_as_text(tmp_path):
    (tmp_path/'a.png').write_bytes(b'PNG\r\n')
    assert inspect(tmp_path,{'a.png':b'PNG\n'})[0]['kind']=='CONTENT_CHANGE'
