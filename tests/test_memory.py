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


def document(root, name, kind="functional", value=60, scope="production", fingerprint=None):
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
                "probe": {"type": "python_literal", "path": "session.py", "name": "TTL"},
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
