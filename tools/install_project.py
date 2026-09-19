"""Install the skill and its independent runtime into one existing project."""

import argparse
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
UPSTREAM = "https://github.com/yanjingzhaisun/general-game-development-rag"
VERSION = "0.2.0"
MARKER = "<!-- project-code-memory:start -->"
ROUTE = """<!-- project-code-memory:start -->
## Project-owned AI memory

Read `.agents/skills/project-code-memory/SKILL.md` when reading or maintaining
project AI memory, and before completing code changes in this project.
Read `ForAI/index.md` for project context. Current functionality is authoritative
in code/configuration; design requirements retain their intent separately.
Use this project's runtime: `uv run --directory ForAI/rag python manage.py query "keywords"`.
At installation, ask the user to select an embedding API or a local Ollama model.
Configure ForAI/rag/embedding.toml and run embedding doctor; do not save API keys in files.
If the user postpones setup, report that semantic retrieval is not enabled.
After changes, update the relevant ForAI documents and change coverage, then run
`uv run --directory ForAI/rag python manage.py scan --write-report`.
Before committing, run `uv run --directory ForAI/rag python manage.py coverage --staged`.
Do not refresh evidence hashes without reading the source. Do not use a central
repository runtime or another project's database.
<!-- project-code-memory:end -->
"""


def install(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Project directory does not exist: {root}")
    skill = SOURCE / "skills/project-code-memory"
    if not (skill / "assets/runtime/uv.lock").is_file():
        raise ValueError("Incomplete skill bundle")
    plans = []
    for source, destination in (
        (skill, root / ".agents/skills/project-code-memory"),
        (skill / "assets/runtime", root / "ForAI/rag"),
    ):
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if (
                any(
                    part in {".venv", ".cache", ".models", "__pycache__"} for part in relative.parts
                )
                or path.name == "embedding.toml"
            ):
                continue
            if not path.is_file():
                continue
            target = destination / relative
            if not target.resolve().is_relative_to(root):
                raise ValueError(f"Destination escapes project: {target}")
            if target.exists():
                if not target.is_file() or target.read_bytes() != path.read_bytes():
                    raise ValueError(
                        f"Local file differs; review and merge before upgrading: {target}"
                    )
            else:
                plans.append((path, target))
    agents = root / "AGENTS.md"
    manifest = root / "ForAI/rag/install.json"
    embedding_config = root / "ForAI/rag/embedding.toml"
    for path in (agents, manifest, embedding_config):
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"Destination escapes project: {path}")
    previous = agents.read_text(encoding="utf-8-sig") if agents.exists() else ""
    provider = (
        tomllib.loads(embedding_config.read_text(encoding="utf-8-sig")).get(
            "provider", "unconfigured"
        )
        if embedding_config.exists()
        else "unconfigured"
    )
    if MARKER in previous and ROUTE.strip() not in previous:
        raise ValueError("Existing memory routing block differs; merge explicitly")
    revision = subprocess.run(
        ["git", "-C", str(SOURCE), "rev-parse", "HEAD"], capture_output=True, check=False
    )
    metadata = {
        "upstream": UPSTREAM,
        "version": VERSION,
        "source_revision": revision.stdout.decode().strip()
        if revision.returncode == 0
        else "uncommitted",
        "ownership": "project-local",
    }
    # All conflicts are checked before writing any file.
    for path, target in plans:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    if MARKER not in previous:
        agents.write_text(
            previous.rstrip() + ("\n\n" if previous else "") + ROUTE, encoding="utf-8", newline="\n"
        )
    if not manifest.exists():
        manifest.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
    if not embedding_config.exists():
        shutil.copyfile(skill / "assets/runtime/embedding.example.toml", embedding_config)
    return {
        "project": str(root),
        "copied_files": len(plans),
        "runtime": "ForAI/rag",
        **metadata,
        "embedding": {
            "provider": provider,
            "setup_required": provider == "unconfigured",
            "config": "ForAI/rag/embedding.toml",
            "prompt": "请选择 embedding：API 服务，或安装 Ollama 并下载本地 embedding 模型。未选择时语义检索未启用。",
            "options": {
                "api": "uv run --directory ForAI/rag python manage.py embedding configure --provider api --model <model> --endpoint <full-embedding-url>",
                "local": "uv run --directory ForAI/rag python manage.py embedding configure --provider ollama --model <model>",
                "later": "uv run --directory ForAI/rag python manage.py embedding configure --provider disabled",
            },
            "instructions": ".agents/skills/project-code-memory/references/embeddings.md",
        },
    }


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.project), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
