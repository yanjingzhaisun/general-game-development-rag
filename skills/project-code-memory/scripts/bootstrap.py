"""Copy the bundled runtime into one project; never overwrite a differing file."""

import argparse
import json
import shutil
from pathlib import Path


def bootstrap(root: Path) -> list[str]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Project directory does not exist: {root}")
    source = Path(__file__).resolve().parents[1] / "assets/runtime"
    if not (source / "uv.lock").is_file():
        raise ValueError("Skill runtime bundle is incomplete: uv.lock is missing")
    plans = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if (
            any(part in {".venv", ".cache", ".models", "__pycache__"} for part in relative.parts)
            or path.name == "embedding.toml"
        ):
            continue
        if not path.is_file():
            continue
        target = root / "ForAI/rag" / relative
        if not target.resolve().is_relative_to(root):
            raise ValueError(f"Runtime destination escapes project: {target}")
        if target.exists():
            if not target.is_file() or target.read_bytes() != path.read_bytes():
                raise ValueError(f"Existing project-owned file differs; merge explicitly: {target}")
        else:
            plans.append((path, target))
    for path, target in plans:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    return [target.relative_to(root).as_posix() for _, target in plans]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                {
                    "created": bootstrap(args.project),
                    "embedding_setup": "Run local manage.py init, then ask the user to select API or local Ollama embeddings; see references/embeddings.md.",
                },
                ensure_ascii=True,
                indent=2,
            )
        )
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
