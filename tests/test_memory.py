import json
import os
import sqlite3
import subprocess
import sys

import pytest

from general_game_development_rag.cli import initialize, main, write_report
from general_game_development_rag.coverage import coverage
from general_game_development_rag.documents import MemoryError, digest, parse_document, project_path
from general_game_development_rag.graph import build, query


def document(
    root, name, kind="functional", value=60, scope="production", fingerprint=None, probe=None
):
    import yaml

    path = root / f"ForAI/{name}.md"
    record = {
        "kind": kind,
        "sources": [{"path": "session.py"}],
        "claims": [
            {
                "id": "ttl",
                "subject": "session",
                "predicate": "ttl_minutes",
                "scope": scope,
                "value": value,
                "probe": probe
                or {
                    "capability": "literal",
                    "language": "python",
                    "path": "session.py",
                    "name": "TTL",
                },
            }
        ],
    }
    if fingerprint:
        record["sources"][0]["sha256"] = fingerprint
    meta = {
        "id": name,
        "keywords_en": ["session"],
        "keywords_zh": ["会话"],
        "summary": "会话有效期",
    }
    path.write_text(
        "---\n"
        + yaml.safe_dump(meta, allow_unicode=True)
        + "---\n\n```rag\n"
        + yaml.safe_dump(record, allow_unicode=True)
        + "```\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def project(tmp_path):
    initialize(tmp_path)
    (tmp_path / "session.py").write_text("TTL = 30\n", encoding="utf-8")
    return tmp_path


def test_code_authority_and_design_are_separate(project):
    document(project, "function")
    document(project, "design", kind="design")
    result = build(project)
    issues = {issue["kind"]: issue for issue in result["issues"]}
    assert issues["description_drift"]["action"] == "update_functional_doc"
    assert issues["design_deviation"]["action"] == "review_design_or_code"
    assert issues["description_drift"]["observed"] == 30


def test_hash_change_means_review_not_behavior_change(project):
    source = project / "session.py"
    document(project, "function", value=30, fingerprint=digest(source.read_bytes()))
    assert build(project)["issues"] == []
    source.write_text("# refactor comment\nTTL = 30\n", encoding="utf-8")
    assert {item["kind"] for item in build(project)["issues"]} == {"needs_review"}


def test_rebuild_idempotence_and_report_not_reingested(project):
    document(project, "function")
    first = build(project)
    write_report(project, first)
    assert build(project) == first
    (project / "ForAI/rag/.cache/graph.sqlite3").unlink()
    assert build(project) == first


def test_query_refreshes_changed_sources_and_returns_conflicts(project):
    document(
        project, "function", value=30, fingerprint=digest((project / "session.py").read_bytes())
    )
    old = query(project, "会话")
    (project / "session.py").write_text("TTL = 10\n", encoding="utf-8")
    new = query(project, "会话")
    assert old["snapshot"] != new["snapshot"]
    assert any(item["kind"] == "description_drift" for item in new["issues"])
    assert any(edge[1] == "DESCRIBES" for edge in new["edges"])
    assert len(query(project, "session", max_nodes=2)["nodes"]) <= 2


def test_scope_separates_claims(project):
    document(project, "dev", kind="design", value=30, scope="dev")
    document(project, "prod", kind="design", value=60, scope="production")
    assert not any(item["kind"] == "claim_conflict_candidate" for item in build(project)["issues"])
    document(project, "prod2", kind="design", value=90, scope="production")
    assert any(item["kind"] == "claim_conflict_candidate" for item in build(project)["issues"])


def test_delete_and_rename_document_removes_old_projection(project):
    path = document(project, "function")
    first = build(project)
    path.rename(project / "ForAI/renamed.md")
    assert build(project)["nodes"] == first["nodes"]
    (project / "ForAI/renamed.md").unlink()
    build(project)
    with sqlite3.connect(project / "ForAI/rag/.cache/graph.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM nodes WHERE id LIKE 'claim:%'").fetchone()[0] == 0


def test_missing_source_and_dynamic_probe_are_not_assumed(project):
    document(project, "function")
    (project / "session.py").write_text("TTL = calculate()\n", encoding="utf-8")
    kinds = {item["kind"] for item in build(project)["issues"]}
    assert "probe_unresolved" in kinds
    assert "description_drift" not in kinds
    (project / "session.py").unlink()
    assert "missing_source" in {item["kind"] for item in build(project)["issues"]}


@pytest.mark.parametrize("path", ["../secret", "C:/secret", "/secret", "x\\secret"])
def test_paths_cannot_escape(project, path):
    with pytest.raises(MemoryError):
        project_path(project, path)


def test_bad_document_does_not_destroy_previous_index(project):
    document(project, "valid")
    before = build(project)
    (project / "ForAI/bad.md").write_text("no frontmatter", encoding="utf-8")
    with pytest.raises(MemoryError):
        build(project)
    with sqlite3.connect(project / "ForAI/rag/.cache/graph.sqlite3") as db:
        assert (
            db.execute("SELECT value FROM metadata WHERE key='snapshot'").fetchone()[0]
            == before["snapshot"]
        )


def test_cli_nonzero_on_issues(project, capsys):
    document(project, "function")
    assert main(["--root", str(project), "scan", "--fail-on-issues"]) == 1
    assert json.loads(capsys.readouterr().out)["issues"]


def run_git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def change_record(project, paths):
    import yaml

    covers = [
        {
            "path": path,
            "sha256": digest((project / path).read_bytes())
            if (project / path).exists()
            else "deleted",
            "reason": "测试变更覆盖",
        }
        for path in paths
    ]
    text = "---\nid: change\nkeywords_en: [change]\nkeywords_zh: [变更]\nsummary: 测试变更\n---\n\n```rag\n"
    (project / "ForAI/change.md").write_text(
        text + yaml.safe_dump({"kind": "change", "covers": covers}, allow_unicode=True) + "```\n",
        encoding="utf-8",
    )


def test_staged_coverage_ignores_unstaged_document_and_stale_hash(project):
    run_git(project, "init")
    run_git(project, "config", "core.autocrlf", "false")
    run_git(project, "add", "session.py")
    change_record(project, ["session.py"])
    assert not coverage(project)["ok"]
    run_git(project, "add", "ForAI/change.md")
    assert coverage(project)["ok"]
    (project / "session.py").write_text("TTL = 40\n", encoding="utf-8")
    assert coverage(project)["ok"]  # Unstaged source edits are not part of this commit.
    run_git(project, "add", "session.py")
    assert not coverage(project)["ok"]


def test_committed_range_and_deleted_files(project):
    run_git(project, "init")
    run_git(project, "config", "core.autocrlf", "false")
    run_git(project, "config", "user.name", "Test")
    run_git(project, "config", "user.email", "test@example.invalid")
    run_git(project, "add", "session.py")
    run_git(project, "commit", "-m", "baseline")
    (project / "session.py").unlink()
    change_record(project, ["session.py"])
    run_git(project, "add", "session.py", "ForAI/change.md")
    assert coverage(project)["ok"]
    run_git(project, "commit", "-m", "delete")
    assert coverage(project, "HEAD~1")["ok"]


def test_invalid_frontmatter():
    with pytest.raises(MemoryError):
        parse_document("x.md", "---\nid: x\nsummary: x\n---\n")


@pytest.mark.parametrize("code", ["TTL = 30\nTTL += 1\n", "TTL = 30\nTTL = 40\n"])
def test_probe_rejects_multiple_writes(project, code):
    document(project, "function", value=30)
    (project / "session.py").write_text(code, encoding="utf-8")
    assert "probe_unresolved" in {item["kind"] for item in build(project)["issues"]}


def test_probe_never_executes_project_code(project):
    document(project, "function", value=30)
    (project / "session.py").write_text(
        "raise RuntimeError('must not run')\nTTL = 30\n", encoding="utf-8"
    )
    assert not any(item["kind"] == "probe_unresolved" for item in build(project)["issues"])


@pytest.mark.parametrize(
    "probe",
    [
        {
            "capability": "literal",
            "language": "typescript",
            "reader": "ts-tree-sitter",
            "path": "session.ts",
            "name": "TTL",
        },
        {"capability": "literal", "language": "typescript", "path": "session.ts", "name": "TTL"},
        {"capability": "literal", "path": "session.ts", "name": "TTL"},
    ],
)
def test_typescript_probe_routes_and_records_provenance(project, probe):
    from importlib.metadata import version

    document(project, "function", value=30, probe=probe)
    (project / "session.ts").write_text("export const TTL = 30 as const;\n", encoding="utf-8")
    result = build(project)
    assert not any(node["kind"] == "probe_unresolved" for node in result["issues"])
    import sqlite3

    with sqlite3.connect(project / "ForAI/rag/.cache/graph.sqlite3") as db:
        nodes = dict(db.execute("SELECT id, data FROM nodes"))
    item = json.loads(nodes["claim:function:ttl"])
    assert item["observed"] == 30
    assert item["probe_evidence"] == {
        "reader": "ts-tree-sitter",
        "version": "1",
        "precision": "syntactic",
        "language": "typescript",
        "capability": "literal",
        "dependencies": {
            "tree-sitter": version("tree-sitter"),
            "tree-sitter-typescript": version("tree-sitter-typescript"),
        },
    }


@pytest.mark.parametrize(
    "source, expected",
    [
        ("export const TTL: number = 30;", 30),
        ("const TTL = 30 satisfies number;", 30),
        ('let TTL = "30" as const;', "30"),
    ],
)
def test_typescript_literal_forms(project, source, expected):
    from general_game_development_rag.readers import _ts_literal

    path = project / "session.ts"
    path.write_text(source, encoding="utf-8")
    assert _ts_literal(path, "TTL") == expected


def test_javascript_literal_reader(project):
    from general_game_development_rag.readers import _ts_literal

    path = project / "session.js"
    path.write_text("export const TTL = 30;", encoding="utf-8")
    assert _ts_literal(path, "TTL") == 30


def test_typescript_missing_name_is_unresolved(project):
    from general_game_development_rag.readers import ts_literal_hits

    document(
        project,
        "function",
        value=30,
        probe={
            "capability": "literal",
            "language": "typescript",
            "path": "session.ts",
            "name": "TTL",
        },
    )
    (project / "session.ts").write_text("export const OTHER = 30;", encoding="utf-8")
    assert ts_literal_hits(project / "session.ts", "TTL") == []
    issue = next(item for item in build(project)["issues"] if item["kind"] == "probe_unresolved")
    assert issue["action"] == "inspect_code"


@pytest.mark.parametrize("explicit_reader", [False, True])
def test_missing_tree_sitter_dependency_is_explicitly_unresolved(
    project, monkeypatch, explicit_reader
):
    import builtins

    original_import = builtins.__import__

    def missing_tree_sitter(name, *args, **kwargs):
        if name == "tree_sitter":
            raise ModuleNotFoundError("Simulated missing tree_sitter dependency", name=name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_tree_sitter)
    probe = {"capability": "literal", "path": "session.ts", "name": "TTL"}
    if explicit_reader:
        probe["reader"] = "ts-tree-sitter"
    document(project, "function", value=30, probe=probe)
    (project / "session.ts").write_text("export const TTL = 30;", encoding="utf-8")
    result = build(project)
    issues = [item for item in result["issues"] if item["kind"] == "probe_unresolved"]
    assert len(issues) == 1
    assert issues[0]["objects"] == ["claim:function:ttl", "code:session.ts"]
    assert issues[0]["action"] == "install_reader"
    assert not any(item["kind"] == "description_drift" for item in result["issues"])
    with sqlite3.connect(project / "ForAI/rag/.cache/graph.sqlite3") as db:
        claim = json.loads(
            db.execute("SELECT data FROM nodes WHERE id = 'claim:function:ttl'").fetchone()[0]
        )
    assert "observed" not in claim
    assert "probe_evidence" not in claim


def test_probe_router_failure_actions(project, monkeypatch):
    from general_game_development_rag import readers

    probe = {"capability": "literal", "language": "typescript", "path": "x.ts", "name": "X"}
    monkeypatch.setattr(readers, "available", lambda reader: reader.name == "builtin-python")
    with pytest.raises(readers.ProbeError) as missing:
        readers.resolve(probe)
    assert missing.value.action == "install_reader"
    with pytest.raises(readers.ProbeError) as explicit:
        readers.resolve({**probe, "reader": "unknown"})
    assert explicit.value.action == "inspect_reader"
    with pytest.raises(readers.ProbeError) as unsupported:
        readers.resolve({**probe, "reader": "builtin-python"})
    assert unsupported.value.action == "inspect_reader"


def test_probe_router_disambiguates_competing_readers(monkeypatch):
    from general_game_development_rag import readers

    extra = readers.Reader(
        "other-ts",
        "python",
        "tree_sitter_typescript",
        "syntactic",
        ("literal",),
        ("typescript",),
        "9",
        "_ts_literal",
    )
    monkeypatch.setattr(readers, "REGISTRY", (*readers.REGISTRY, extra))
    with pytest.raises(readers.ProbeError) as error:
        readers.resolve(
            {"capability": "literal", "language": "typescript", "path": "x.ts", "name": "X"}
        )
    assert error.value.action == "disambiguate_reader"


@pytest.mark.parametrize(
    "routing", [{}, {"language": "python"}, {"language": "python", "reader": "builtin-python"}]
)
def test_python_probe_records_complete_evidence(project, routing):
    from general_game_development_rag.graph import canonical

    probe = {"capability": "literal", "path": "session.py", "name": "TTL", **routing}
    path = document(project, "function", value=30, probe=probe)
    assert not any(item["kind"] == "probe_unresolved" for item in build(project)["issues"])
    claim = parse_document("ForAI/function.md", path.read_text(encoding="utf-8")).memory["claims"][
        0
    ]
    expected = {
        **claim,
        "id": "claim:function:ttl",
        "kind": "claim",
        "memory_kind": "functional",
        "path": "ForAI/function.md",
        "text": canonical(claim),
        "observed": 30,
        "probe_evidence": {
            "reader": "builtin-python",
            "version": "1",
            "precision": "syntactic",
            "language": "python",
            "capability": "literal",
            "dependencies": {},
        },
    }
    with sqlite3.connect(project / "ForAI/rag/.cache/graph.sqlite3") as db:
        actual = db.execute("SELECT data FROM nodes WHERE id = ?", (expected["id"],)).fetchone()[0]
    assert actual.encode("utf-8") == canonical(expected).encode("utf-8")


@pytest.mark.parametrize("probe_type", ["python_literal", "unknown", None])
@pytest.mark.parametrize("include_capability", [False, True])
def test_probe_type_is_rejected_with_migration_guidance(project, probe_type, include_capability):
    probe = {"type": probe_type, "path": "session.py", "name": "TTL"}
    if include_capability:
        probe.update(capability="literal", language="python")
    document(project, "function", value=30, probe=probe)
    with pytest.raises(
        MemoryError,
        match=r"probe\.type is no longer supported; use capability: literal with language: python",
    ):
        build(project)


def test_every_successful_probe_claim_has_evidence(project):
    from importlib.metadata import version

    for language, suffix in [("python", "py"), ("typescript", "ts"), ("javascript", "js")]:
        if suffix != "py":
            (project / f"session.{suffix}").write_text("export const TTL = 30;", encoding="utf-8")
        document(
            project,
            language,
            value=30,
            probe={
                "capability": "literal",
                "language": language,
                "path": f"session.{suffix}",
                "name": "TTL",
            },
        )
    assert not any(item["kind"] == "probe_unresolved" for item in build(project)["issues"])
    with sqlite3.connect(project / "ForAI/rag/.cache/graph.sqlite3") as db:
        claims = [
            json.loads(row[0])
            for row in db.execute("SELECT data FROM nodes WHERE id LIKE 'claim:%'")
        ]
    assert len(claims) == 3
    for claim in claims:
        evidence = claim["probe_evidence"]
        assert claim["observed"] == 30
        assert evidence["capability"] == "literal"
        assert evidence["version"] == "1"
        assert evidence["precision"] == "syntactic"
        assert evidence["language"] == claim["probe"]["language"]
        if evidence["language"] == "python":
            assert evidence["reader"] == "builtin-python"
            assert evidence["dependencies"] == {}
        else:
            assert evidence["reader"] == "ts-tree-sitter"
            assert evidence["dependencies"] == {
                "tree-sitter": version("tree-sitter"),
                "tree-sitter-typescript": version("tree-sitter-typescript"),
            }


def test_unexpected_reader_failure_uses_inspect_reader(project, monkeypatch):
    from general_game_development_rag import graph

    def failed_reader(*args, **kwargs):
        raise RuntimeError("Unexpected reader failure")

    monkeypatch.setattr(graph, "read", failed_reader)
    document(project, "function", value=30)
    issues = [item for item in build(project)["issues"] if item["kind"] == "probe_unresolved"]
    assert len(issues) == 1
    assert issues[0]["action"] == "inspect_reader"


@pytest.mark.parametrize(
    "registered, expected_action", [(False, "inspect_reader"), (True, "enable_reader")]
)
def test_unregistered_and_disabled_readers_are_distinct_graph_issues(
    project, monkeypatch, registered, expected_action
):
    from dataclasses import replace

    from general_game_development_rag import readers

    reader_name = "no-such-reader"
    if registered:
        reader = replace(readers.REGISTRY[0], enabled=False)
        monkeypatch.setattr(readers, "REGISTRY", (reader,))
        reader_name = reader.name
    document(
        project,
        "function",
        probe={
            "capability": "literal",
            "language": "python",
            "reader": reader_name,
            "path": "session.py",
            "name": "TTL",
        },
    )
    issues = [item for item in build(project)["issues"] if item["kind"] == "probe_unresolved"]
    assert len(issues) == 1
    assert issues[0]["action"] == expected_action


@pytest.mark.parametrize("available_package", [None, "tree-sitter"])
def test_reader_dependency_versions_do_not_invent_missing_metadata(monkeypatch, available_package):
    from general_game_development_rag import readers

    def metadata_version(package):
        if package == available_package:
            return "0.26.0"
        raise readers.importlib.metadata.PackageNotFoundError(package)

    monkeypatch.setattr(readers.importlib.metadata, "version", metadata_version)
    reader = next(item for item in readers.REGISTRY if item.name == "ts-tree-sitter")
    expected = {available_package: "0.26.0"} if available_package else {}
    assert reader.dependency_versions() == expected


def test_disabled_reader_has_enable_action(monkeypatch):
    from general_game_development_rag import readers

    item = readers.Reader(
        "disabled-ts",
        "python",
        "tree_sitter_typescript",
        "syntactic",
        ("literal",),
        ("typescript",),
        "1",
        "_ts_literal",
        False,
    )
    monkeypatch.setattr(readers, "REGISTRY", (item,))
    with pytest.raises(readers.ProbeError) as error:
        readers.resolve(
            {"capability": "literal", "language": "typescript", "path": "x.ts", "name": "X"}
        )
    assert error.value.action == "enable_reader"


def test_command_reader_contract_failure_is_inspect_reader(tmp_path, monkeypatch):
    from general_game_development_rag import readers

    reader = readers.Reader(
        "external",
        "command",
        None,
        "syntactic",
        ("literal",),
        ("typescript",),
        "2",
        "",
        command="reader",
    )

    def invalid_contract(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="{}", stderr="")

    monkeypatch.setattr(readers.subprocess, "run", invalid_contract)
    path = tmp_path / "x.ts"
    path.write_text("const X = 1;", encoding="utf-8")
    with pytest.raises(readers.ProbeError) as error:
        readers.read(reader, path, "X")
    assert error.value.action == "inspect_reader"


def test_missing_command_reader_has_inspect_action(monkeypatch):
    from general_game_development_rag import readers

    reader = readers.Reader(
        "missing-command",
        "command",
        None,
        "syntactic",
        ("literal",),
        ("typescript",),
        "2",
        "",
        command="definitely-not-installed",
    )
    monkeypatch.setattr(readers, "REGISTRY", (reader,))
    with pytest.raises(readers.ProbeError) as error:
        readers.resolve(
            {
                "capability": "literal",
                "language": "typescript",
                "reader": reader.name,
                "path": "x.ts",
                "name": "X",
            }
        )
    assert error.value.action == "inspect_reader"


def test_malformed_record_is_not_silently_ignored(project):
    path = document(project, "function")
    path.write_text(path.read_text(encoding="utf-8").removesuffix("```\n"), encoding="utf-8")
    with pytest.raises(MemoryError, match="unclosed"):
        build(project)


def test_init_preserves_existing_entrypoint(project):
    entry = project / "ForAI/index.md"
    before = entry.read_bytes()
    assert initialize(project)["created"] == []
    assert entry.read_bytes() == before


def test_cli_json_is_utf8_even_with_legacy_console_encoding(project):
    document(project, "function", value=30)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "general_game_development_rag.cli",
            "--root",
            str(project),
            "query",
            "会话",
        ],
        capture_output=True,
        check=True,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )
    payload = json.loads(result.stdout.decode("utf-8"))
    assert any(node.get("summary") == "会话有效期" for node in payload["nodes"])
