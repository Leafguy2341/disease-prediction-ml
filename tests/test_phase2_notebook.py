"""Source preflight, visible outputs and complete source bundles for remote kernels."""
import builtins
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from src.data.bootstrap import bootstrap_project, unpack_source_archive


@pytest.fixture
def templates(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    from build_preprocessing_notebook import inspection_cells, PHASE2_REQUIRED_FILES
    return root, inspection_cells(), PHASE2_REQUIRED_FILES


def bundle(path, files):
    contents = {name: "# test source\n" if name.endswith(".py") else "{}" for name in files}
    hashes = {k: hashlib.sha256(v.encode()).hexdigest() for k, v in contents.items()}
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in contents.items():
            archive.writestr("disease-prediction-ml/" + name, value)
        archive.writestr("disease-prediction-ml/bundle_manifest.json", json.dumps(hashes))
    return path


def test_old_phase1_source_zip_is_rejected_before_extraction(templates, tmp_path):
    _, _, required = templates
    archive = bundle(tmp_path / "old.zip", ["configs/phase1.json", "configs/runtime.json", "src/data/paths.py", "src/data/audit.py"])
    with pytest.raises(ValueError, match="preprocessing_inspection.py"):
        unpack_source_archive(archive, tmp_path / "extracted", required_files=required)
    assert not (tmp_path / "extracted").exists()


def test_old_checked_out_source_has_actionable_message_without_importing_src(templates, tmp_path):
    _, _, required = templates
    old = tmp_path / "old-source"; (old / "configs").mkdir(parents=True)
    (old / "configs/phase1.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="SOURCE_ARCHIVE") as exc:
        bootstrap_project({"drive_mount": str(tmp_path / "drive"), "project_relative": "MyDrive/project"}, root_override=old, required_files=required)
    assert "preprocessing_inspection.py" in str(exc.value)


def test_phase2_zip_bootstraps_in_content_without_src_and_preserves_old_checkout(templates, tmp_path, monkeypatch):
    _, cells, required = templates
    content = tmp_path / "content"; content.mkdir(); monkeypatch.chdir(content)
    for name in ["DISEASE_PROJECT_ROOT", "DISEASE_DRIVE_MOUNT", "DISEASE_DRIVE_PROJECT"]:
        monkeypatch.delenv(name, raising=False)
    old = content / "disease-prediction-ml"; old.mkdir()
    sentinel = old / "user_file.py"; sentinel.write_text("keep user edits", encoding="utf-8")
    archive = bundle(content / "new-source.zip", required)
    config = next(c.source for c in cells if "PHASE2_PRESENTATION_V2" in c.source)
    setup = next(c.source for c in cells if "source_path = dataset_path" in c.source)
    namespace = {}
    exec(compile(config, "config", "exec"), namespace)
    namespace["SOURCE_ARCHIVE"] = str(archive)
    importer = builtins.__import__
    def no_project_import(name, *args, **kwargs):
        if name == "src" or name.startswith("src.") or name in {"numpy", "pandas"}:
            pytest.fail("Pre-source bootstrap must work without project imports or dependencies")
        return importer(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_project_import)
    exec(compile(setup.split("if str(ROOT) not in sys.path:", 1)[0], "standalone_preflight", "exec"), namespace)
    assert namespace["ROOT"].is_relative_to(content / ".phase2-source")
    assert all((namespace["ROOT"] / name).is_file() for name in required)
    assert sentinel.read_text(encoding="utf-8") == "keep user edits"


def test_visible_main_workflow_precedes_optional_history(templates):
    _, cells, _ = templates
    history_index = next(i for i, c in enumerate(cells) if "### Phụ lục" in c.source)
    process = next(i for i, c in enumerate(cells) if "finalized = preprocess_dataset" in c.source)
    validation = next(i for i, c in enumerate(cells) if 'v = finalized["validation"]' in c.source)
    export = next(i for i, c in enumerate(cells) if "manifest = export_preprocessed" in c.source)
    assert process < validation < export < history_index
    for i in [process, validation, export]:
        assert not cells[i].source.startswith("if RUN_HISTORICAL_INSPECTION")
        assert "display(" in cells[i].source
    for c in cells:
        if c.cell_type == "code":
            compile(c.source, "generated-cell", "exec")


def test_history_defaults_to_disabled_and_main_outputs_remain_visible(templates, capsys):
    import nbformat

    root, generated, _ = templates
    stored = nbformat.read(root / "notebooks/02_preprocessing.ipynb", as_version=4).cells
    for cells in (generated, stored):
        configuration = next(c.source for c in cells if "PHASE2_PRESENTATION_V2" in c.source)
        namespace = {}
        exec(compile(configuration, "configuration", "exec"), namespace)
        assert namespace["RUN_HISTORICAL_INSPECTION"] is False
        headings = [line for c in cells if c.cell_type == "markdown" for line in c.source.splitlines() if line.startswith("## ")]
        assert len(headings) == 5
        capsys.readouterr()
        history = [c for c in cells if c.cell_type == "code" and c.source.startswith("if RUN_HISTORICAL_INSPECTION:")]
        assert len(history) == 1
        for cell in history:
            assert cell.metadata.get("jupyter", {}).get("outputs_hidden") is not True
            # With analysis disabled, the user still gets a useful message, without preparing any data.
            exec(compile(cell.source, "disabled-analysis", "exec"), {"RUN_HISTORICAL_INSPECTION": False})
            assert "RUN_HISTORICAL_INSPECTION=True" in capsys.readouterr().out
        for marker in ("source_path = dataset_path", "finalized = preprocess_dataset", 'v = finalized["validation"]', "manifest = export_preprocessed"):
            cell = next(c for c in cells if c.cell_type == "code" and marker in c.source)
            assert not cell.source.startswith("if RUN_HISTORICAL_INSPECTION")
            assert "display(" in cell.source
            assert not cell.metadata.get("jupyter", {}).get("outputs_hidden", False)


@pytest.mark.parametrize("stored", [False, True])
@pytest.mark.parametrize("older_source_api", [False, True])
def test_threshold_cell_displays_tables_and_figure_without_report_png(templates, tmp_path, stored, older_source_api, monkeypatch):
    import matplotlib
    matplotlib.use("Agg", force=True)
    import nbformat
    import pandas as pd
    from matplotlib.figure import Figure
    from src.data.paths import OutputPaths
    from src.data.audit import audit_dataset
    from src.data.preprocessing_inspection import (
        threshold_split_comparison, threshold_comparison_figure, inspect_header,
        inspect_regurgitation, class_eligibility, group_split_feasibility, both_features_removal_impact,
    )

    root, cells, _ = templates
    if stored:
        cells = nbformat.read(root / "notebooks/02_preprocessing.ipynb", as_version=4).cells
    source = next(c.source for c in cells if "threshold_analysis = threshold_split_comparison" in c.source)
    rows, start = [], 0
    for disease, count in [("A", 1), ("B", 3), ("C", 5), ("D", 10), ("E", 15)]:
        rows.extend((group, disease) for group in range(start, start + count))
        start += count
    frame = pd.DataFrame({"diseases": [disease for _, disease in rows],
                          **{f"symptom_{bit}": [(group >> bit) & 1 for group, _ in rows] for bit in range(6)},
                          "regurgitation": [group % 2 for group, _ in rows],
                          "regurgitation.1": [int(group % 3 == 0) for group, _ in rows],
                          "constant": [0] * len(rows)})
    raw = tmp_path / "fixture.csv"
    frame.to_csv(raw, index=False)
    before = raw.read_bytes()
    shown = []
    previews = []
    def plot_from_older_zip(analysis, output, recommended=10):
        # Earlier Phase 2 source ZIPs always save the PNG and do not accept save=False.
        result = threshold_comparison_figure(analysis, output, recommended=recommended)
        assert result[1].is_file()
        previews.append(result[1])
        return result
    if older_source_api:
        monkeypatch.setattr("src.data.preprocessing_inspection.threshold_comparison_figure", plot_from_older_zip)
    namespace = {"RUN_HISTORICAL_INSPECTION": True, "df": frame, "read_path": raw,
                 "config": {"target": "diseases", "seed": 42, "near_constant_threshold": .99},
                 "pd": pd, "json": json, "OUTPUT": OutputPaths(tmp_path), "display": shown.append,
                 "threshold_split_comparison": threshold_split_comparison,
                 "threshold_comparison_figure": plot_from_older_zip if older_source_api else threshold_comparison_figure,
                 "OutputPaths": OutputPaths, "Path": Path, "audit_dataset": audit_dataset,
                 "inspect_header": inspect_header, "inspect_regurgitation": inspect_regurgitation,
                 "class_eligibility": class_eligibility, "group_split_feasibility": group_split_feasibility,
                 "both_features_removal_impact": both_features_removal_impact}
    exec(compile(source, "threshold-cell", "exec"), namespace)
    figures = [item for item in shown if isinstance(item, Figure)]
    comparisons = [item for item in shown if isinstance(item, pd.DataFrame) and "singleton_validation_classes" in item]
    assert len(figures) == 1 and len(figures[0].axes) == 2
    assert comparisons[0]["min_unique_vectors"].tolist() == [1, 3, 5, 10, 15]
    figures[0].canvas.draw()
    assert list(tmp_path.iterdir()) == [raw] and raw.read_bytes() == before
    assert all(not path.exists() for path in previews)  # Older ZIP previews are removed from local temp storage.


def test_missing_locked_manifest_stops_before_export(templates, tmp_path):
    from src.data.loader import sha256_file
    _, cells, _ = templates
    source = next(c.source for c in cells if c.cell_type == "code" and "manifest = export_preprocessed" in c.source)
    def forbidden_export(*args, **kwargs):
        pytest.fail("Presentation must never recreate a missing locked export")
    with pytest.raises(FileNotFoundError):
        exec(compile(source, "missing-manifest", "exec"), {
            "manifest_path": tmp_path / "missing.json", "sha256_file": sha256_file, "export_preprocessed": forbidden_export})


@pytest.mark.parametrize("configured_in_content", [False, True])
def test_drive_is_mounted_before_reading_source_zip_on_drive(templates, tmp_path, monkeypatch, configured_in_content):
    _, cells, required = templates
    content = tmp_path / "content"; content.mkdir(); monkeypatch.chdir(content)
    drive = content / "drive"
    archive = drive / "MyDrive/source.zip"
    monkeypatch.setenv("DISEASE_DRIVE_MOUNT", str(drive))
    monkeypatch.delenv("DISEASE_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("DISEASE_DRIVE_PROJECT", raising=False)
    namespace = {}
    config = next(c.source for c in cells if "PHASE2_PRESENTATION_V2" in c.source)
    setup = next(c.source for c in cells if "source_path = dataset_path" in c.source)
    exec(compile(config, "config", "exec"), namespace)
    configured = content / archive.name if configured_in_content else archive
    namespace.update(MOUNT_DRIVE=True, SOURCE_ARCHIVE=str(configured), SOURCE_DIRECTORY=content / "source")
    definitions, execution = setup.split('print("[2/5]', 1)
    exec(compile(definitions, "definitions", "exec"), namespace)
    # The ZIP does not even exist before the supported mount makes Drive accessible.
    from types import SimpleNamespace
    namespace["detect_capabilities"] = lambda: SimpleNamespace(colab_runtime_detected=True, drive_api_available=True)
    calls = []
    def mount(point):
        calls.append(point)
        archive.parent.mkdir(parents=True)
        bundle(archive, required)
    namespace["mount_drive_at"] = mount
    preimport = ('print("[2/5]' + execution).split("if str(ROOT) not in sys.path:", 1)[0]
    exec(compile(preimport, "preimport", "exec"), namespace)
    assert calls == [drive]
    assert namespace["SOURCE_ARCHIVE"] == archive.resolve()
    assert all((namespace["ROOT"] / name).is_file() for name in required)


def test_current_bundle_contains_phase2_and_strips_outputs(templates, tmp_path, monkeypatch):
    root, _, required = templates
    monkeypatch.syspath_prepend(str(root / "scripts"))
    from package_colab import build_bundle
    destination = tmp_path / "phase2-source.zip"
    build_bundle(root, destination)
    with zipfile.ZipFile(destination) as archive:
        names = set(archive.namelist())
        assert all("disease-prediction-ml/" + name in names for name in required)
        notebook = json.loads(archive.read("disease-prediction-ml/notebooks/02_preprocessing.ipynb"))
        assert any("PHASE2_PRESENTATION_V2" in "".join(c["source"]) for c in notebook["cells"])
        assert all(not c.get("outputs") for c in notebook["cells"] if c["cell_type"] == "code")
        assert not any("/data/processed/" in name or "/artifacts/" in name or name.endswith(".env") for name in names)
