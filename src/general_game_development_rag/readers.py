"""Static probe reader registry. Readers must inspect source without executing it."""

from __future__ import annotations

import ast
import importlib
import importlib.metadata
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .documents import MemoryError


@dataclass(frozen=True)
class Reader:
    name: str
    kind: str
    module: str | None
    precision: str
    capabilities: tuple[str, ...]
    languages: tuple[str, ...]
    version: str
    entrypoint: str
    enabled: bool = True
    command: str | None = None
    dependency: str | None = None
    dependency_packages: tuple[str, ...] = ()

    def dependency_versions(self) -> dict[str, str]:
        """Report installed dependency versions; unavailable metadata stays absent."""
        versions = {}
        for package in self.dependency_packages:
            try:
                versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                continue
        return versions


class ProbeError(MemoryError):
    def __init__(self, message: str, action: str):
        super().__init__(message)
        self.action = action


REGISTRY = (
    Reader(
        "builtin-python",
        "python",
        "general_game_development_rag.graph",
        "syntactic",
        ("literal",),
        ("python",),
        "1",
        "python_literal",
    ),
    Reader(
        "ts-tree-sitter",
        "python",
        "general_game_development_rag.readers",
        "syntactic",
        ("literal",),
        ("typescript", "javascript"),
        "1",
        "_ts_literal",
        dependency="tree_sitter_typescript",
        dependency_packages=("tree-sitter", "tree-sitter-typescript"),
    ),
)

EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
}


def resolve(probe: dict) -> tuple[Reader, str]:
    language = probe.get("language") or EXTENSIONS.get(Path(probe["path"]).suffix.lower())
    if not language:
        raise ProbeError("Cannot infer probe language from path", "inspect_code")
    capability = probe["capability"]
    if probe.get("reader"):
        matches = [item for item in REGISTRY if item.name == probe["reader"]]
        if not matches:
            raise ProbeError(f"Reader {probe['reader']} is not registered", "inspect_reader")
        reader = matches[0]
        if not reader.enabled:
            raise ProbeError(f"Reader {reader.name} is disabled", "enable_reader")
        if capability not in reader.capabilities or language not in reader.languages:
            raise ProbeError(
                "Reader does not support requested capability/language", "inspect_reader"
            )
        if not available(reader):
            action = unavailable_action(reader)
            detail = reader.command if reader.kind == "command" else reader.module
            raise ProbeError(f"Reader dependency or command is missing: {detail}", action)
        return reader, language
    matches = [
        item for item in REGISTRY if capability in item.capabilities and language in item.languages
    ]
    active = [item for item in matches if item.enabled]
    enabled = [item for item in active if available(item)]
    if len(enabled) > 1:
        raise ProbeError(f"Multiple readers support {language}/{capability}", "disambiguate_reader")
    if not enabled:
        if not matches:
            action = "inspect_reader"
        elif not active:
            action = "enable_reader"
        elif any(not available(item) for item in active):
            action = next(unavailable_action(item) for item in active if not available(item))
        else:
            action = "inspect_reader"
        raise ProbeError(f"No enabled reader supports {language}/{capability}", action)
    return enabled[0], language


def available(reader: Reader) -> bool:
    if reader.kind == "command":
        return bool(reader.command and shutil.which(reader.command))
    module = reader.dependency or reader.module
    if not module:
        return True
    try:
        __import__(module)
    except ImportError:
        return False
    return True


def unavailable_action(reader: Reader) -> str:
    return "inspect_reader" if reader.kind == "command" else "install_reader"


def _strip_ts_assertion(source: str) -> str:
    source = re.sub(r"\s+satisfies\s+.+$", "", source).strip()
    source = re.sub(r"\s+as\s+(?:const|[\w.$<>[\]| &]+)$", "", source).strip()
    return source


def ts_literal_hits(path: Path, name: str):
    try:
        import tree_sitter_typescript as tsts
        from tree_sitter import Language, Parser
    except ImportError as exc:
        raise ProbeError("tree-sitter reader dependencies are missing", "install_reader") from exc
    grammar = (
        tsts.language_tsx()
        if path.suffix.lower() in {".tsx", ".jsx"}
        else tsts.language_typescript()
    )
    language = Language(grammar)
    parser = Parser(language)
    source = path.read_bytes()
    tree = parser.parse(source)
    root = tree.root_node
    declarations = []
    for child in root.children:
        candidate = child
        if candidate.type == "export_statement":
            candidate = next(
                (n for n in candidate.named_children if n.type == "lexical_declaration"), None
            )
        if candidate and candidate.type == "lexical_declaration":
            declarations.extend(candidate.named_children)
    hits = []
    for declaration in declarations:
        if declaration.type != "variable_declarator":
            continue
        identifier = declaration.child_by_field_name("name")
        value = declaration.child_by_field_name("value")
        if identifier is None or value is None:
            continue
        if source[identifier.start_byte : identifier.end_byte].decode() != name:
            continue
        raw = _strip_ts_assertion(source[value.start_byte : value.end_byte].decode())
        if not raw or raw.startswith(("(", "function", "new ")):
            raise MemoryError(f"Value for {name} is not a supported literal")
        raw = re.sub(r"\btrue\b", "True", raw)
        raw = re.sub(r"\bfalse\b", "False", raw)
        raw = re.sub(r"\bnull\b", "None", raw)
        try:
            parsed = ast.literal_eval(raw)
        except (SyntaxError, ValueError):
            try:
                parsed = json.loads(source[value.start_byte : value.end_byte].decode())
            except (json.JSONDecodeError, TypeError):
                raise MemoryError(f"Value for {name} is not a supported literal") from None
        hits.append(parsed)
    return hits


def _ts_literal(path: Path, name: str):
    hits = ts_literal_hits(path, name)
    if len(hits) != 1:
        raise MemoryError(f"Expected one top-level assignment for {name}")
    return hits[0]


def read(reader: Reader, path: Path, name: str):
    if reader.kind == "command":
        if not reader.command:
            raise ProbeError(f"Reader command is not configured: {reader.name}", "inspect_reader")
        payload = {
            "source": path.read_text(encoding="utf-8"),
            "name": name,
        }
        try:
            result = subprocess.run(
                [reader.command],
                input=json.dumps(payload),
                capture_output=True,
                check=False,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise ValueError(f"reader exited {result.returncode}")
            response = json.loads(result.stdout)
            if not isinstance(response, dict) or "value" not in response:
                raise ValueError("reader output must be a JSON object with value")
            return response["value"]
        except (OSError, subprocess.TimeoutExpired, ValueError, json.JSONDecodeError) as exc:
            raise ProbeError(f"Command reader contract failed: {exc}", "inspect_reader") from exc
    module_name = reader.module
    try:
        handler = getattr(importlib.import_module(module_name), reader.entrypoint)
    except (ImportError, AttributeError) as exc:
        raise ProbeError(
            f"Reader contract is unavailable: {reader.name}", "inspect_reader"
        ) from exc
    return handler(path, name)
