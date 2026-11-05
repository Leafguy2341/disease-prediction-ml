"""Update only the setup cell; back up originals and keep all other cells intact."""
from datetime import datetime, timezone
import json
import ast
from pathlib import Path
import re

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def preserve_settings(existing: str, template: str) -> str:
    """Keep user-selected settings, including MOUNT_DRIVE=True and explicit paths."""
    names = {"PROJECT_ROOT", "PATH_CONFIG", "MOUNT_DRIVE", "SOURCE_ARCHIVE", "SOURCE_DIRECTORY"}
    for node in ast.parse(existing).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in names:
            name = node.targets[0].id
            expression = ast.get_source_segment(existing, node.value)
            template = re.sub(r"^" + name + r" = .*?$", lambda _: name + " = " + expression, template, count=1, flags=re.MULTILINE)
    return template


def main():
    from scripts.update_colab_notebooks import main as migrate_colab
    migrate_colab()


if __name__ == "__main__":
    main()
