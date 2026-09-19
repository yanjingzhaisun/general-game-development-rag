"""Run memory maintenance bound to this project, regardless of shell cwd."""

import sys
from pathlib import Path

from general_game_development_rag.cli import main

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    raise SystemExit(main(["--root", str(project_root), *sys.argv[1:]]))
