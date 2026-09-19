"""Check code-change coverage using exactly the staged blobs or a commit range."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .documents import MemoryError, digest, parse_document

CODE_SUFFIXES = {
    ".py",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".gd",
    ".rs",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".lua",
    ".shader",
    ".hlsl",
    ".glsl",
    ".go",
    ".java",
    ".swift",
}


def git(root: Path, *args: str, optional: bool = False) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if result.returncode and not optional:
        raise MemoryError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout if result.returncode == 0 else b""


def coverage(root: Path, base: str | None = None) -> dict:
    """Default: index versus HEAD (also works on an unborn branch). Base: HEAD versus base."""
    if base:
        revision = (
            git(root, "rev-parse", "--verify", "--end-of-options", base + "^{commit}")
            .decode()
            .strip()
        )
        changed_raw = git(root, "diff", "--no-renames", "--name-only", "-z", revision, "HEAD", "--")
        files_raw = git(root, "ls-tree", "-r", "--name-only", "-z", "HEAD")
        prefix = "HEAD:"
    else:
        changed_raw = git(root, "diff", "--cached", "--no-renames", "--name-only", "-z", "--")
        files_raw = git(root, "ls-files", "-z")
        prefix = ":"
    changed = {p.decode("utf-8") for p in changed_raw.split(b"\0") if p}
    available = {p.decode("utf-8") for p in files_raw.split(b"\0") if p}
    code_paths = sorted(path for path in changed if Path(path).suffix.lower() in CODE_SUFFIXES)
    records = {}
    for path in sorted(changed & available):
        if not (path.startswith("ForAI/") and path.endswith(".md")):
            continue
        doc = parse_document(path, git(root, "show", prefix + path).decode("utf-8-sig"))
        if doc.memory["kind"] != "change":
            continue
        for item in doc.memory.get("covers", []):
            records.setdefault(item["path"], []).append({**item, "document": path})
    results = []
    for path in code_paths:
        expected = digest(git(root, "show", prefix + path)) if path in available else "deleted"
        matches = [item for item in records.get(path, []) if item["sha256"] == expected]
        results.append(
            {"path": path, "sha256": expected, "covered": bool(matches), "records": matches}
        )
    return {
        "mode": "committed_range" if base else "staged",
        "files": results,
        "ok": all(item["covered"] for item in results),
        "scope": "Known code suffixes; verifies coverage records, not semantic correctness. See coverage.py CODE_SUFFIXES.",
    }
