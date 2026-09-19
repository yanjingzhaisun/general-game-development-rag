import json
import sqlite3
import threading
from contextlib import closing
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from general_game_development_rag import embeddings as em
from general_game_development_rag.cli import initialize, main
from general_game_development_rag.documents import MemoryError
from general_game_development_rag.graph import query


@pytest.fixture
def project(tmp_path):
    initialize(tmp_path)
    return tmp_path


@pytest.fixture
def provider(monkeypatch):
    calls = []

    def fake(config, texts):
        calls.extend(texts)
        return [[1.0, 0.0] if "respawn" in text or "倒地" in text else [0.0, 1.0] for text in texts]

    monkeypatch.setattr(em, "embed", fake)
    return calls


def node(body, name="respawn"):
    return {
        "id": "doc:" + name,
        "kind": "functional",
        "summary": "Feature documentation",
        "path": "ForAI/" + name + ".md",
        "text": body,
    }


def config(**kwargs):
    return em.Config(
        provider="api",
        model="test-model",
        endpoint="https://example.invalid/v1/embeddings",
        **kwargs,
    )


def test_unconfigured_is_visible_and_doctor_fails(project, capsys):
    assert initialize(project)["embedding"]["setup_required"]
    result = query(project, "nothing")
    assert result["retrieval"]["mode"] == "keyword_graph"
    assert result["retrieval"]["embedding"]["setup_required"]
    assert main(["--root", str(project), "embedding", "doctor"]) == 1
    assert json.loads(capsys.readouterr().out)["setup_required"]


def test_configure_local_and_disabled_preserves_no_secrets(project, capsys, monkeypatch):
    monkeypatch.setenv("GGRAG_EMBEDDING_API_KEY", "must-never-persist")
    assert (
        main(
            [
                "--root",
                str(project),
                "embedding",
                "configure",
                "--provider",
                "ollama",
                "--model",
                "my-model",
            ]
        )
        == 0
    )
    saved = em.load_config(project)
    assert saved.endpoint == "http://127.0.0.1:11434/api/embed"
    assert "must-never-persist" not in (project / em.CONFIG_PATH).read_text()
    assert "must-never-persist" not in capsys.readouterr().out
    em.save_config(project, provider="disabled")
    assert query(project, "nothing")["retrieval"]["embedding"]["provider"] == "disabled"


@pytest.mark.parametrize(
    "values",
    [
        {"provider": "api", "model": "x", "endpoint": "http://remote.invalid/v1/embeddings"},
        {"provider": "ollama", "model": "x", "endpoint": "https://remote.invalid/api/embed"},
        {"provider": "api", "model": "x", "endpoint": "https://a:b@host.invalid/v1/embeddings"},
        {
            "provider": "api",
            "model": "x",
            "endpoint": "https://host.invalid/v1/embeddings?key=secret",
        },
        {"chunk_overlap": 1200},
        {"batch_size": 0},
        {"provider": "unknown"},
    ],
)
def test_invalid_config_is_rejected(project, values):
    with pytest.raises(MemoryError):
        em.save_config(project, **values)


def test_keyword_miss_is_found_by_semantic_retrieval(project, provider):
    (project / "ForAI/respawn.md").write_text(
        "---\nid: respawn\nkeywords_en: [respawn]\nkeywords_zh: [重生]\nsummary: respawn behavior\n---\n\nThe respawn module restores a defeated player.\n",
        encoding="utf-8",
    )
    assert query(project, "角色倒地后怎么恢复")["seeds"] == []
    em.save_config(
        project, provider="api", model="test", endpoint="https://example.invalid/v1/embeddings"
    )
    result = query(project, "角色倒地后怎么恢复")
    assert "doc:respawn" in result["seeds"]
    assert result["retrieval"]["mode"] == "hybrid_graph"
    assert result["retrieval"]["semantic_hits"][0]["path"] == "ForAI/respawn.md"


def test_cache_reuses_content_and_invalidates_model_revision(project, provider):
    nodes = {"doc:respawn": node("respawn behavior")}
    _, _, first = em.sync_vectors(project, nodes, config())
    assert first["embedded"] == 1
    _, _, second = em.sync_vectors(project, nodes, config())
    assert second["embedded"] == 0 and second["reused"] == 1
    em.sync_vectors(project, nodes, replace(config(), revision="2"))
    assert len(provider) == 2
    nodes["doc:respawn"]["text"] += " updated"
    _, _, changed = em.sync_vectors(project, nodes, replace(config(), revision="2"))
    assert changed["embedded"] == 1
    em.sync_vectors(project, {}, config())
    with closing(sqlite3.connect(project / "ForAI/rag/.cache/embeddings.sqlite3")) as db:
        assert db.execute("SELECT COUNT(*) FROM vectors").fetchone()[0] == 0


def test_embeddings_exclude_code_reports_and_source_hashes(project, provider):
    nodes = {
        "doc:respawn": node(
            "respawn\n\n```rag\nkind: functional\nsources:\n  - sha256: secret-hash\n```\n"
        ),
        "code:x": {"kind": "code", "text": "raw-code-must-not-be-sent"},
        "doc:report": {"kind": "report", "text": "report-must-not-be-sent"},
    }
    em.sync_vectors(project, nodes, config())
    assert not any("secret-hash" in text or "must-not-be-sent" in text for text in provider)
    nodes["doc:respawn"]["text"] = nodes["doc:respawn"]["text"].replace("secret-hash", "new-hash")
    assert em.sync_vectors(project, nodes, config())[2]["embedded"] == 0


def test_failed_refresh_keeps_previous_vectors(project, provider, monkeypatch):
    em.sync_vectors(project, {"doc:a": node("respawn")}, config())

    def fail(*args):
        raise MemoryError("provider offline")

    monkeypatch.setattr(em, "embed", fail)
    with pytest.raises(MemoryError, match="offline"):
        em.sync_vectors(project, {"doc:b": node("inventory")}, config())
    with closing(sqlite3.connect(project / "ForAI/rag/.cache/embeddings.sqlite3")) as db:
        assert db.execute("SELECT COUNT(*) FROM vectors").fetchone()[0] == 1


def test_configured_failure_is_not_silently_downgraded(project, monkeypatch):
    em.save_config(
        project, provider="api", model="test", endpoint="https://example.invalid/v1/embeddings"
    )

    def fail(*args):
        raise MemoryError("provider offline")

    monkeypatch.setattr(em, "embed", fail)
    with pytest.raises(MemoryError):
        query(project, "project")
    assert (
        query(project, "project", keyword_only=True)["retrieval"]["embedding"]["status"]
        == "skipped_explicitly"
    )


@pytest.fixture
def http_provider():
    state = {"requests": [], "status": 200, "reply": None}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["requests"].append(
                {"path": self.path, "body": body, "auth": self.headers.get("Authorization")}
            )
            reply = state["reply"]
            if reply is None:
                vectors = [[3.0, 4.0] for _ in body["input"]]
                reply = (
                    {"embeddings": vectors}
                    if self.path == "/api/embed"
                    else {
                        "data": [
                            {"index": index, "embedding": value}
                            for index, value in reversed(list(enumerate(vectors)))
                        ]
                    }
                )
            self.send_response(state["status"])
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(reply).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state["url"] = f"http://127.0.0.1:{server.server_port}"
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_api_http_contract_and_response_indexes(http_provider, monkeypatch):
    monkeypatch.setenv("TEST_EMBEDDING_KEY", "dummy-test-key")
    http_provider["reply"] = {
        "data": [
            {"index": 1, "embedding": [0.0, 5.0]},
            {"index": 0, "embedding": [3.0, 0.0]},
        ]
    }
    cfg = replace(
        config(), endpoint=http_provider["url"] + "/v1/embeddings", api_key_env="TEST_EMBEDDING_KEY"
    )
    assert em.embed(cfg, ["one", "two"]) == [[1.0, 0.0], [0.0, 1.0]]
    request = http_provider["requests"][0]
    assert request["auth"] == "Bearer dummy-test-key"
    assert request["body"]["encoding_format"] == "float"


def test_ollama_http_contract(http_provider):
    cfg = em.Config(
        provider="ollama", model="local-model", endpoint=http_provider["url"] + "/api/embed"
    )
    assert em.embed(cfg, ["test"]) == [[0.6, 0.8]]
    request = http_provider["requests"][0]
    assert request["body"]["truncate"] is False
    assert request["auth"] is None


@pytest.mark.parametrize(
    "reply",
    [
        {"data": [{"index": 1, "embedding": [1, 0]}]},
        {"data": [{"index": 0, "embedding": [0, 0]}]},
        {"data": [{"index": 0, "embedding": [float("nan"), 1]}]},
        {"data": [{"index": 0, "embedding": [True, 1]}]},
        {"data": []},
    ],
)
def test_invalid_provider_responses_rejected(http_provider, reply):
    http_provider["reply"] = reply
    cfg = replace(config(), endpoint=http_provider["url"] + "/v1/embeddings", api_key_env="")
    with pytest.raises(MemoryError):
        em.embed(cfg, ["test"])


def test_http_error_does_not_echo_sensitive_response(http_provider):
    http_provider["status"] = 401
    http_provider["reply"] = {"error": "server-echoed-secret"}
    cfg = replace(config(), endpoint=http_provider["url"] + "/v1/embeddings", api_key_env="")
    with pytest.raises(MemoryError, match="HTTP 401") as error:
        em.embed(cfg, ["test"])
    assert "server-echoed-secret" not in str(error.value)


def test_invalid_key_does_not_leak_into_error(http_provider, monkeypatch):
    monkeypatch.setenv("TEST_KEY", "sensitive-key\n")
    cfg = replace(
        config(), endpoint=http_provider["url"] + "/v1/embeddings", api_key_env="TEST_KEY"
    )
    with pytest.raises(MemoryError) as error:
        em.embed(cfg, ["test"])
    assert "sensitive-key" not in str(error.value)
    assert http_provider["requests"] == []


def test_changed_query_dimensions_are_rejected(project, provider, monkeypatch):
    nodes = {"doc:respawn": node("respawn")}
    em.sync_vectors(project, nodes, config())
    monkeypatch.setattr(em, "embed", lambda *_: [[1.0, 0.0, 0.0]])
    with pytest.raises(MemoryError, match="Query dimensions"):
        em.semantic_search(project, nodes, "query", config(), 5)
