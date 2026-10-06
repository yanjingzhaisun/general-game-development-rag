"""Build the distributable, project-local runtime bundled with the skill."""

import shutil
from pathlib import Path

from general_game_development_rag.embeddings import DEFAULT_CONFIG, RUNTIME_GITIGNORE

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
version = "0.3.0"
description = "Project-owned ForAI memory runtime"
license = "MIT"
license-files = ["LICENSE"]
requires-python = ">=3.12"
dependencies = ["pyyaml>=6.0.2,<7"]

[project.scripts]
ggrag = "general_game_development_rag.cli:main"

[project.optional-dependencies]
readers = ["tree-sitter>=0.25,<0.27", "tree-sitter-typescript>=0.23,<0.24", "tree-sitter-kotlin>=1.1,<1.2"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
""",
        encoding="utf-8",
        newline="\n",
    )
    shutil.copyfile(ROOT / "LICENSE", TARGET / "LICENSE")
    # 依赖锁同样属于分发件：忘同步会让目标项目拿到过期的依赖集。
    # ForAI/rag/uv.lock 由 `uv lock` 在该目录生成，这里只做复制。
    shutil.copyfile(ROOT / "ForAI/rag/uv.lock", TARGET / "uv.lock")
    (TARGET / ".python-version").write_text("3.12\n", encoding="utf-8", newline="\n")
    (TARGET / ".gitignore").write_text(RUNTIME_GITIGNORE, encoding="utf-8", newline="\n")
    (TARGET / "embedding.example.toml").write_text(DEFAULT_CONFIG, encoding="utf-8", newline="\n")
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
