"""Read-only packaging dependency checks; no datasets, archive creation or models."""
from pathlib import Path
import pytest
from scripts.package_handover import code_files

ROOT = Path(__file__).resolve().parents[1]


def test_launcher_is_shipped_without_unreviewed_report_promotion():
    files = code_files(ROOT)
    assert 'run_api.py' in files
    assert not any(n.startswith('reports/academic_review_20261111/') for n in files)
    assert not any('/snapshots/' in n for n in files)


def test_historical_supplement_identity_is_unchanged():
    import json
    from scripts.package_handover import code_supplements
    policy = json.loads((ROOT/'configs/handover_code_supplements.json').read_bytes())
    assert code_supplements(ROOT) == policy['files']
