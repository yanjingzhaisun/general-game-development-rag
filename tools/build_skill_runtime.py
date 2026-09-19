"""Build the distributable, project-local runtime bundled with the skill."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "skills/project-code-memory/assets/runtime"


def main():
    package = "general_game_development_rag"
    target_src = TARGET / "src" / package
    target_src.mkdir(parents=True, exist_ok=True)
    source_names = set()
    for source in (ROOT / "src" / package).glob("*.py"):
        source_names.add(source.name)
        shutil.copyfile(source, target_src / source.name)
    for stale in target_src.glob("*.py"):
        if stale.name not in source_names:
            stale.unlink()
    (TARGET / "pyproject.toml").write_text(
        """[project]
name = "general-game-development-rag"
version = "0.1.0"
description = "Project-owned ForAI memory runtime"
requires-python = ">=3.12"
dependencies = ["pyyaml>=6.0.2,<7"]

[project.scripts]
ggrag = "general_game_development_rag.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
""",
        encoding="utf-8",
        newline="\n",
    )
    (TARGET / ".python-version").write_text("3.12\n", encoding="utf-8", newline="\n")
    (TARGET / ".gitignore").write_text(
        ".venv/\n.cache/\n__pycache__/\n", encoding="utf-8", newline="\n"
    )
    (TARGET / "manage.py").write_text(
        '''"""Run memory maintenance bound to this project, regardless of shell cwd."""

import sys
from pathlib import Path

from general_game_development_rag.cli import main

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    raise SystemExit(main(["--root", str(project_root), *sys.argv[1:]]))
''',
        encoding="utf-8",
        newline="\n",
    )
    print(TARGET)


if __name__ == "__main__":
    main()
