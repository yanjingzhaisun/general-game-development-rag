"""Rebuildable SQLite relation index and deterministic conflict checks."""

from __future__ import annotations

import ast
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from .documents import MemoryError, digest, load_documents, project_path
from .embeddings import load_config, semantic_search, status
from .readers import ProbeError, read, resolve


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def python_literal(path: Path, name: str):
    """Read a single top-level literal assignment without importing/executing code."""
    tree = ast.parse(path.read_bytes(), filename=str(path))
    matches = []
    permitted_targets = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            matches.append(node.value)
            permitted_targets.update(id(target) for target in targets)
    if len(matches) != 1 or matches[0] is None:
        raise MemoryError(f"Expected one top-level assignment for {name}")
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id == name
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and id(node) not in permitted_targets
        ):
            raise MemoryError(f"Additional writes make {name} ambiguous")
        if isinstance(node, ast.alias) and (
            node.name == "*" or (node.asname or node.name.split(".")[0]) == name
        ):
            raise MemoryError(f"Imported binding makes {name} ambiguous")
    return ast.literal_eval(matches[0])


def build(root: Path) -> dict:
    root = root.resolve()
    docs = load_documents(root)
    nodes: dict[str, dict] = {}
    edges: set[tuple[str, str, str]] = set()
    issues: dict[str, dict] = {}
    sources: dict[str, str | None] = {}
    groups: dict[tuple, list] = {}

    def issue(kind, objects, message, action, **details):
        identity = digest(canonical([kind, sorted(objects)]).encode())[:20]
        issues[identity] = {
            "id": identity,
            "kind": kind,
            "objects": objects,
            "message": message,
            "action": action,
            **details,
        }

    def code(path: str) -> tuple[str, str | None]:
        target = project_path(root, path)
        node_id = "code:" + path
        if path not in sources:
            sources[path] = digest(target.read_bytes()) if target.is_file() else None
        nodes[node_id] = {
            "id": node_id,
            "kind": "code",
            "path": path,
            "sha256": sources[path],
            "text": path,
        }
        return node_id, sources[path]

    for doc in docs:
        doc_id = "doc:" + doc.id
        kind = doc.memory["kind"]
        nodes[doc_id] = {
            "id": doc_id,
            "kind": kind,
            "path": doc.path,
            "summary": doc.meta["summary"],
            "keywords": doc.meta["keywords_en"] + doc.meta["keywords_zh"],
            "text": doc.text,
        }
        if kind == "functional" and not doc.memory.get("sources"):
            issue("unverified_description", [doc_id], "功能文档没有代码来源", "add_sources")
        for source in doc.memory.get("sources", []):
            code_id, current = code(source["path"])
            relation = (
                "DESCRIBES"
                if kind == "functional"
                else ("IMPLEMENTED_BY" if kind == "design" else "REFERENCES")
            )
            edges.add((doc_id, relation, code_id))
            if current is None:
                issue("missing_source", [doc_id, code_id], "来源文件已消失", "review_reference")
            elif kind == "functional" and source.get("sha256") != current:
                issue(
                    "needs_review",
                    [doc_id, code_id],
                    "代码指纹与上次核验不一致；尚不能判定功能发生变化",
                    "read_code_then_update_doc",
                    expected=source.get("sha256"),
                    observed=current,
                )
        for claim in doc.memory.get("claims", []):
            claim_id = f"claim:{doc.id}:{claim['id']}"
            nodes[claim_id] = {
                **claim,
                "id": claim_id,
                "kind": "claim",
                "memory_kind": kind,
                "path": doc.path,
                "text": canonical(claim),
            }
            entity_id = "entity:" + claim["subject"]
            nodes[entity_id] = {"id": entity_id, "kind": "entity", "text": claim["subject"]}
            edges.add((doc_id, "ASSERTS", claim_id))
            edges.add((claim_id, "ABOUT", entity_id))
            if claim.get("status", "active") != "active":
                continue
            key = (claim["subject"], claim["predicate"], claim["scope"], kind)
            groups.setdefault(key, []).append((claim_id, claim["value"]))
            if "probe" not in claim:
                continue
            probe = claim["probe"]
            code_id, current = code(probe["path"])
            edges.add(
                (claim_id, "SUPPORTED_BY" if kind == "functional" else "IMPLEMENTED_BY", code_id)
            )
            try:
                if current is None:
                    raise MemoryError("Source file does not exist")
                reader, language = resolve(probe)
                observed = read(reader, project_path(root, probe["path"]), probe["name"])
            except ProbeError as exc:
                issue("probe_unresolved", [claim_id, code_id], str(exc), exc.action)
                continue
            except (MemoryError, OSError, SyntaxError, ValueError, TypeError) as exc:
                issue("probe_unresolved", [claim_id, code_id], str(exc), "inspect_code")
                continue
            except Exception as exc:  # noqa: BLE001 - plugin failures must become unresolved issues.
                issue("probe_unresolved", [claim_id, code_id], str(exc), "inspect_reader")
                continue
            nodes[claim_id]["observed"] = observed
            evidence = {
                "reader": reader.name,
                "version": reader.version,
                "precision": reader.precision,
                "language": language,
                "capability": probe["capability"],
                "dependencies": reader.dependency_versions(),
            }
            nodes[claim_id]["probe_evidence"] = evidence
            if canonical(observed) != canonical(claim["value"]):
                issue(
                    "description_drift" if kind == "functional" else "design_deviation",
                    [claim_id, code_id],
                    "声明值与代码中的静态字面值不同",
                    "update_functional_doc" if kind == "functional" else "review_design_or_code",
                    expected=claim["value"],
                    observed=observed,
                    scope=claim["scope"],
                    reader=reader.name,
                    reader_version=reader.version,
                    precision=reader.precision,
                )

    for key, claims in groups.items():
        if len({canonical(value) for _, value in claims}) > 1:
            issue(
                "claim_conflict_candidate",
                [node_id for node_id, _ in claims],
                "同类文档在相同主体、属性、范围下声明了不同值；需核实条件是否完整",
                "inspect_sources",
                subject=key[0],
                predicate=key[1],
                scope=key[2],
            )
    for entry in issues.values():
        node_id = "issue:" + entry["id"]
        nodes[node_id] = {**entry, "id": node_id, "kind": "issue", "text": canonical(entry)}
        for related in entry["objects"]:
            edges.add((node_id, "AFFECTS", related))
    snapshot = digest(
        canonical(
            {
                "docs": {doc.path: digest(doc.text.encode()) for doc in docs},
                "sources": sources,
            }
        ).encode()
    )
    cache = project_path(root, "ForAI/rag/.cache")
    cache.mkdir(parents=True, exist_ok=True)
    db_path = project_path(root, "ForAI/rag/.cache/graph.sqlite3")
    with closing(sqlite3.connect(db_path)) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT, relation TEXT, target TEXT, PRIMARY KEY(source, relation, target));
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        with connection:
            connection.execute("DELETE FROM nodes")
            connection.execute("DELETE FROM edges")
            connection.executemany(
                "INSERT INTO nodes VALUES (?, ?)",
                ((node_id, canonical(data)) for node_id, data in sorted(nodes.items())),
            )
            connection.executemany("INSERT INTO edges VALUES (?, ?, ?)", sorted(edges))
            connection.execute(
                "INSERT OR REPLACE INTO metadata VALUES ('snapshot', ?)", (snapshot,)
            )
    return {
        "snapshot": snapshot,
        "documents": len(docs),
        "nodes": len(nodes),
        "edges": len(edges),
        "issues": sorted(issues.values(), key=lambda item: item["id"]),
    }


def query(
    root: Path,
    text: str,
    limit: int = 5,
    hops: int = 2,
    max_nodes: int = 40,
    keyword_only: bool = False,
) -> dict:
    if not text.strip() or not 1 <= limit <= 50 or not 0 <= hops <= 3 or not 1 <= max_nodes <= 200:
        raise MemoryError("Query required; limit 1..50, hops 0..3, max-nodes 1..200")
    state = build(root)  # Correctness first: no stale answers after branch/worktree changes.
    with closing(sqlite3.connect(root / "ForAI/rag/.cache/graph.sqlite3")) as connection:
        nodes = {
            node_id: json.loads(data)
            for node_id, data in connection.execute("SELECT id, data FROM nodes")
        }
        edges = list(
            connection.execute(
                "SELECT source, relation, target FROM edges ORDER BY source, relation, target"
            )
        )
    terms = re.findall(r"[\w.-]+", text.casefold())
    scored = []
    for node_id, node in nodes.items():
        if node["kind"] == "issue" or node.get("status", "active") != "active":
            continue
        haystack = node["text"].casefold()
        score = sum(haystack.count(term) for term in terms)
        if score:
            scored.append((-score, node_id))
    candidates = max(10, limit * 3)
    keyword_ids = [node_id for _, node_id in sorted(scored)[:candidates]]
    config = load_config(root)
    retrieval = {"mode": "keyword_graph", "embedding": status(config)}
    ranking = keyword_ids
    if config.enabled and not keyword_only:
        hits, stats = semantic_search(root, nodes, text, config, candidates)
        scores = {}
        for channel in (keyword_ids, [hit["node_id"] for hit in hits]):
            for rank, node_id in enumerate(channel, 1):
                scores[node_id] = scores.get(node_id, 0) + 1 / (60 + rank)
        ranking = sorted(scores, key=lambda key: (-scores[key], key))
        retrieval = {"mode": "hybrid_graph", "embedding": stats, "semantic_hits": hits[:limit]}
    elif keyword_only:
        retrieval["embedding"] = {
            "status": "skipped_explicitly",
            "message": "仅执行关键词与图关系检索。",
        }
    seeds = ranking[: min(limit, max_nodes)]
    selected = set(seeds)
    frontier = set(seeds)
    for _ in range(hops):
        adjacent = set()
        for source, _, target in edges:
            if source in frontier:
                adjacent.add(target)
            if target in frontier:
                adjacent.add(source)
        adjacent -= selected
        frontier = set(sorted(adjacent)[: max(0, max_nodes - len(selected))])
        selected |= frontier
    relevant_issues = [item for item in state["issues"] if selected.intersection(item["objects"])]
    return {
        "snapshot": state["snapshot"],
        "retrieval": retrieval,
        "seeds": seeds,
        "nodes": [{k: v for k, v in nodes[key].items() if k != "text"} for key in sorted(selected)],
        "edges": [list(edge) for edge in edges if edge[0] in selected and edge[2] in selected],
        "issues": relevant_issues,
        "guidance": "Read the cited source files. Functional descriptions derive from code; design deviations require a decision.",
    }
