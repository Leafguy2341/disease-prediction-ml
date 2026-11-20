"""Small opaque fixtures only; no actual dataset, weights, or held-out evaluation."""
import hashlib
import pytest
from scripts.verify_repository_data import verify_inventory,verify


def fixture(tmp_path,storage='git'):
    p=tmp_path/'data/processed/train.csv.gz';p.parent.mkdir(parents=True)
    raw=b'opaque synthetic fixture, not parsed';p.write_bytes(raw)
    manifest={'files':{'data/processed/train.csv.gz':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'git_storage':storage}}}
    return p,manifest


def test_opaque_checksum_roundtrip_without_parsing(tmp_path):
    p,m=fixture(tmp_path,'lfs');r=verify_inventory(tmp_path,m)
    assert r['status']=='PASS' and r['lfs_payloads_verified']==1 and r['payloads_parsed'] is False


@pytest.mark.parametrize('fault',['missing','size','hash','pointer','path'])
def test_missing_corrupt_or_pointer_payload_fails(tmp_path,fault):
    p,m=fixture(tmp_path,'lfs')
    if fault=='missing':p.unlink()
    if fault=='size':p.write_bytes(b'x')
    if fault=='hash':p.write_bytes(b'x'*p.stat().st_size)
    if fault=='pointer':p.write_bytes(b'version https://git-lfs.github.com/spec/v1\noid sha256:000\nsize 123\n')
    if fault=='path':m['files']['../outside.bin']=m['files'].pop('data/processed/train.csv.gz')
    with pytest.raises(ValueError):verify_inventory(tmp_path,m)


def test_locked_byte_access_requires_explicit_opt_in(tmp_path):
    with pytest.raises(ValueError,match='allow-locked-bytes'):verify(tmp_path)
