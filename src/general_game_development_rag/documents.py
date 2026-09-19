"""Strict, compact frontmatter and explicit memory records in Markdown bodies."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml


class MemoryError(ValueError):
    """Actionable input or project-state error."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def project_path(root: Path, relative: str) -> Path:
    """Only portable, repository-relative paths, including symlink containment."""
    path = PurePosixPath(relative)
    if not relative or "\\" in relative or ":" in relative or path.is_absolute():
        raise MemoryError(f"Expected a relative POSIX path: {relative!r}")
    if ".." in path.parts:
        raise MemoryError(f"Path escapes project: {relative}")
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise MemoryError(f"Path escapes project: {relative}")
    return target


@dataclass
class Document:
    path: str
    text: str
    meta: dict
    memory: dict

    @property
    def id(self) -> str:
        return self.meta["id"]


def parse_document(path: str, text: str) -> Document:
    match = re.match(r"\A\ufeff?---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
    if not match:
        raise MemoryError(f"{path}: missing YAML frontmatter")
    try:
        meta = yaml.safe_load(match[1])
        body = text[match.end() :]
        blocks = re.findall(r"^```rag\s*\r?\n(.*?)^```\s*$", body, re.MULTILINE | re.DOTALL)
        if len(re.findall(r"^```rag\b", body, re.MULTILINE)) != len(blocks):
            raise MemoryError(f"{path}: unclosed or malformed rag block")
        if len(blocks) > 1:
            raise MemoryError(f"{path}: only one rag block is allowed")
        memory = yaml.safe_load(blocks[0]) if blocks else {"kind": "index"}
    except yaml.YAMLError as exc:
        raise MemoryError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(meta, dict) or not isinstance(memory, dict):
        raise MemoryError(f"{path}: metadata and rag block must be mappings")
    for key in ("id", "summary"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise MemoryError(f"{path}: {key} must be a nonempty string")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", meta["id"]):
        raise MemoryError(f"{path}: id must be a stable ASCII identifier")
    for key in ("keywords_en", "keywords_zh"):
        value = meta.get(key)
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, str) and item.strip() for item in value)
        ):
            raise MemoryError(f"{path}: {key} must be a nonempty string list")
    if memory.get("kind") not in {"index", "functional", "design", "change", "report"}:
        raise MemoryError(f"{path}: invalid memory kind")
    if memory.get("claims") and memory["kind"] not in {"functional", "design"}:
        raise MemoryError(f"{path}: claims require functional or design kind")
    for key in ("sources", "claims", "covers"):
        if not isinstance(memory.get(key, []), list):
            raise MemoryError(f"{path}: {key} must be a list")
    for source in memory.get("sources", []):
        if not isinstance(source, dict) or not isinstance(source.get("path"), str):
            raise MemoryError(f"{path}: each source needs a path")
        if "sha256" in source and not re.fullmatch(r"[0-9a-f]{64}", str(source["sha256"])):
            raise MemoryError(f"{path}: invalid source sha256")
    seen = set()
    for claim in memory.get("claims", []):
        if not isinstance(claim, dict):
            raise MemoryError(f"{path}: claim must be a mapping")
        for key in ("id", "subject", "predicate", "scope"):
            if not isinstance(claim.get(key), str) or not claim[key].strip():
                raise MemoryError(f"{path}: claim needs string {key}")
        if claim["id"] in seen or "value" not in claim:
            raise MemoryError(f"{path}: duplicate claim id or missing value")
        seen.add(claim["id"])
        if claim.get("status", "active") not in {"active", "superseded", "proposed"}:
            raise MemoryError(f"{path}: invalid claim status")
        if "probe" in claim:
            probe = claim["probe"]
            if not isinstance(probe, dict) or probe.get("type") != "python_literal":
                raise MemoryError(f"{path}: supported probe type is python_literal")
            if not all(isinstance(probe.get(k), str) and probe[k] for k in ("path", "name")):
                raise MemoryError(f"{path}: probe needs path and name")
    for cover in memory.get("covers", []):
        if not isinstance(cover, dict) or not all(
            isinstance(cover.get(key), str) and cover[key].strip()
            for key in ("path", "reason", "sha256")
        ):
            raise MemoryError(f"{path}: coverage needs path, reason, sha256")
        if cover["sha256"] != "deleted" and not re.fullmatch(r"[0-9a-f]{64}", cover["sha256"]):
            raise MemoryError(f"{path}: coverage sha256 must be a hash or deleted")
    return Document(path, text, meta, memory)


def load_documents(root: Path) -> list[Document]:
    if not (root / "ForAI").is_dir():
        raise MemoryError("No ForAI directory; run ggrag init first")
    docs = []
    ids = set()
    for path in sorted((root / "ForAI").rglob("*.md")):
        relative = path.relative_to(root).as_posix()
        if any(part in {".cache", ".venv", ".models", "__pycache__"} for part in path.parts):
            continue
        project_path(root, relative)
        doc = parse_document(relative, path.read_text(encoding="utf-8-sig"))
        if doc.id in ids:
            raise MemoryError(f"Duplicate document id: {doc.id}")
        ids.add(doc.id)
        if doc.memory["kind"] != "report":
            docs.append(doc)
    return docs
