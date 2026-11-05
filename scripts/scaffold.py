"""Create missing Phase 1 folders without replacing existing files."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
directories = ["data/raw", "data/interim", "data/processed", "notebooks", "src/features", "src/models",
               "src/evaluation", "src/agent", "app/backend", "app/frontend", "artifacts/models",
               "artifacts/metadata", "reports/figures", "reports/tables", "tests", "configs"]
for directory in directories:
    folder = root / directory
    folder.mkdir(parents=True, exist_ok=True)
    keep = folder / ("__init__.py" if directory.startswith("src/") else ".gitkeep")
    if not keep.exists():
        keep.write_text("", encoding="utf-8")
print("Created missing directories; existing files preserved.")
