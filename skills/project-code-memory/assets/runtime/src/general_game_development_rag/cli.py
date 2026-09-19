"""Project memory CLI with explicit embedding setup and local graph storage."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .coverage import coverage
from .documents import MemoryError, digest, project_path
from .embeddings import (
    DEFAULT_CONFIG,
    RUNTIME_GITIGNORE,
    embed,
    load_config,
    save_config,
    status,
    sync_project,
)
from .graph import build, query

ENTRY = """---
id: project-memory
keywords_en: [project, memory, navigation]
keywords_zh: [项目, 记忆, 导航]
summary: 项目 AI 阅读入口，连接实现记忆与设计记忆。
---

# 项目记忆

功能说明以当前代码和配置为准；设计要求保存意图，不因代码变化自动改写。
在 modules/ 维护功能说明，在 decisions/ 维护设计要求，在 changes/ 记录变更覆盖。
查询后阅读来源代码；代码指纹变化只表示需要核验，不能证明行为变化。

```rag
kind: index
```
"""


def initialize(root: Path) -> dict:
    if not root.is_dir():
        raise MemoryError(f"Project directory does not exist: {root}")
    created = []
    files = {
        "ForAI/index.md": ENTRY,
        "ForAI/rag/.gitignore": RUNTIME_GITIGNORE,
        "ForAI/rag/embedding.example.toml": DEFAULT_CONFIG,
        "ForAI/rag/embedding.toml": DEFAULT_CONFIG,
    }
    for relative, content in files.items():
        path = project_path(root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8", newline="\n")
            created.append(relative)
    for folder in ("modules", "decisions", "changes", "conflicts"):
        project_path(root, "ForAI/" + folder).mkdir(parents=True, exist_ok=True)
    return {"root": str(root), "created": created, "embedding": status(load_config(root))}


def write_report(root: Path, result: dict) -> str:
    relative = "ForAI/conflicts/scan.md"
    target = project_path(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "id: generated-conflict-scan",
        "keywords_en: [conflict, scan, evidence]",
        "keywords_zh: [冲突, 扫描, 证据]",
        "summary: 当前项目的确定性核验结果，不代表完整语义审计。",
        "---",
        "",
        "# 当前扫描结果",
        "",
        "```rag",
        "kind: report",
        "```",
        "",
        f"快照：`{result['snapshot']}`",
        "",
        "此文件是可再生报告；长期处理决策另存设计或冲突记录。扫描不覆盖未结构化自然语言。",
        "",
    ]
    if not result["issues"]:
        lines.append("本次检查范围内未发现问题。")
    for issue in result["issues"]:
        lines.extend(
            [
                f"## {issue['kind']} · {issue['id']}",
                "",
                issue["message"],
                "",
                "```json",
                json.dumps(issue, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return relative


def main(argv: list[str] | None = None) -> int:
    # JSON is a UTF-8 protocol, including redirected Windows console output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Code-authoritative ForAI graph memory")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create ForAI entrypoint without overwriting existing files")
    commands.add_parser(
        "sync", help="Rebuild graph and incrementally embed changed document chunks"
    )
    scan = commands.add_parser("scan", help="Check references, fingerprints and structured claims")
    scan.add_argument("--write-report", action="store_true")
    scan.add_argument("--fail-on-issues", action="store_true")
    search = commands.add_parser(
        "query", help="Hybrid semantic/keyword retrieval and graph expansion"
    )
    search.add_argument("text")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--hops", type=int, default=2)
    search.add_argument("--max-nodes", type=int, default=40)
    search.add_argument("--keyword-only", action="store_true", help="Explicitly skip embeddings")
    embedding = commands.add_parser("embedding", help="Configure API or local Ollama embeddings")
    embedding_commands = embedding.add_subparsers(dest="embedding_command", required=True)
    embedding_commands.add_parser("status", help="Show configuration without contacting a model")
    embedding_commands.add_parser("doctor", help="Probe the provider using a short test string")
    configure = embedding_commands.add_parser(
        "configure", help="Write local embedding.toml, without saving secrets"
    )
    configure.add_argument("--provider", choices=["api", "ollama", "disabled"], required=True)
    configure.add_argument("--model", default="")
    configure.add_argument("--endpoint")
    configure.add_argument("--api-key-env", default="GGRAG_EMBEDDING_API_KEY")
    configure.add_argument("--revision", default="1")
    configure.add_argument("--dimensions", type=int)
    configure.add_argument("--timeout-seconds", type=int, default=30)
    configure.add_argument("--batch-size", type=int, default=16)
    configure.add_argument("--chunk-chars", type=int, default=1200)
    configure.add_argument("--chunk-overlap", type=int, default=150)
    configure.add_argument("--document-prefix", default="")
    configure.add_argument("--query-prefix", default="")
    fingerprint = commands.add_parser(
        "hash", help="Hash source evidence after reading and verifying it"
    )
    fingerprint.add_argument("paths", nargs="+")
    cover = commands.add_parser(
        "coverage", help="Check change records against staged code or a commit range"
    )
    selection = cover.add_mutually_exclusive_group()
    selection.add_argument("--staged", action="store_true", help="Default; uses only staged blobs")
    selection.add_argument("--base", help="Compare a commit/ref with HEAD")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    exit_code = 0
    try:
        if args.command == "init":
            result = initialize(root)
        elif args.command in {"sync", "scan"}:
            result = build(root)
            if args.command == "sync":
                result["embedding"] = sync_project(root)
            if args.command == "scan":
                if args.write_report:
                    result["report"] = write_report(root, result)
                if args.fail_on_issues and result["issues"]:
                    exit_code = 1
        elif args.command == "query":
            result = query(
                root, args.text, args.limit, args.hops, args.max_nodes, args.keyword_only
            )
        elif args.command == "embedding":
            if args.embedding_command == "configure":
                keys = (
                    "provider",
                    "model",
                    "api_key_env",
                    "revision",
                    "dimensions",
                    "timeout_seconds",
                    "batch_size",
                    "chunk_chars",
                    "chunk_overlap",
                    "document_prefix",
                    "query_prefix",
                )
                values = {key: getattr(args, key) for key in keys}
                values["endpoint"] = args.endpoint or (
                    "http://127.0.0.1:11434/api/embed" if args.provider == "ollama" else ""
                )
                result = save_config(root, **values)
            else:
                config = load_config(root)
                result = status(config)
                if args.embedding_command == "doctor":
                    if not config.enabled:
                        exit_code = 1
                    else:
                        vector = embed(config, [config.query_prefix + "embedding connection test"])[
                            0
                        ]
                        result = {
                            "provider": config.provider,
                            "model": config.model,
                            "ok": True,
                            "dimensions": len(vector),
                        }
        elif args.command == "hash":
            result = {path: digest(project_path(root, path).read_bytes()) for path in args.paths}
        else:
            result = coverage(root, args.base)
            exit_code = 0 if result["ok"] else 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return exit_code
    except (MemoryError, OSError, UnicodeError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
