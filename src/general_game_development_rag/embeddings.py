"""Project-owned embedding configuration, providers and content-addressed vectors."""

from __future__ import annotations

import ipaddress
import json
import math
import os
import re
import sqlite3
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path

from .documents import MemoryError, digest, project_path

CONFIG_PATH = "ForAI/rag/embedding.toml"
RUNTIME_GITIGNORE = """.venv/
.cache/
.models/
__pycache__/
*.py[cod]
*.log
.env
.env.*
!.env.example
!.env.template
embedding.toml
"""
DEFAULT_CONFIG = """# Choose api, ollama, or explicitly disabled. No network calls until configured.
provider = "unconfigured"
model = ""
endpoint = ""
# Store the environment-variable NAME, never an API key.
api_key_env = "GGRAG_EMBEDDING_API_KEY"
# Bump when model weights behind the same name change.
revision = "1"
timeout_seconds = 30
batch_size = 16
chunk_chars = 1200
chunk_overlap = 150
document_prefix = ""
query_prefix = ""
# Optional: dimensions = 768 (only if the provider supports it)
"""


@dataclass(frozen=True)
class Config:
    provider: str = "unconfigured"
    model: str = ""
    endpoint: str = ""
    api_key_env: str = "GGRAG_EMBEDDING_API_KEY"
    revision: str = "1"
    timeout_seconds: int = 30
    batch_size: int = 16
    chunk_chars: int = 1200
    chunk_overlap: int = 150
    document_prefix: str = ""
    query_prefix: str = ""
    dimensions: int | None = None

    @property
    def enabled(self) -> bool:
        return self.provider in {"api", "ollama"}

    @property
    def signature(self) -> str:
        values = asdict(self)
        for key in ("api_key_env", "timeout_seconds", "batch_size"):
            values.pop(key)
        return digest(json.dumps({"schema": 1, **values}, sort_keys=True).encode())


def is_loopback(host: str | None) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host or "").is_loopback
    except ValueError:
        return False


def validate(config: Config) -> Config:
    if config.provider not in {"unconfigured", "disabled", "api", "ollama"}:
        raise MemoryError("Embedding provider must be api, ollama, disabled or unconfigured")
    for key in ("model", "endpoint", "api_key_env", "revision", "document_prefix", "query_prefix"):
        if not isinstance(getattr(config, key), str):
            raise MemoryError(f"Embedding {key} must be a string")
    for key, low, high in (
        ("timeout_seconds", 1, 60),
        ("batch_size", 1, 128),
        ("chunk_chars", 100, 8000),
        ("chunk_overlap", 0, 7999),
    ):
        if type(getattr(config, key)) is not int or not low <= getattr(config, key) <= high:
            raise MemoryError(f"Embedding {key} must be an integer in {low}..{high}")
    if config.chunk_overlap >= config.chunk_chars:
        raise MemoryError("chunk_overlap must be smaller than chunk_chars")
    if config.dimensions is not None and (
        type(config.dimensions) is not int or not 1 <= config.dimensions <= 16384
    ):
        raise MemoryError("dimensions must be an integer in 1..16384")
    if not config.enabled:
        return config
    if not config.model.strip() or not config.revision.strip():
        raise MemoryError("Embedding model and revision are required")
    try:
        url = urllib.parse.urlsplit(config.endpoint)
        _ = url.port
    except ValueError as exc:
        raise MemoryError("Invalid embedding endpoint") from exc
    if not url.hostname or url.scheme not in {"http", "https"} or not url.path:
        raise MemoryError(
            "Use a complete embedding endpoint, including /v1/embeddings or /api/embed"
        )
    if url.username or url.password or url.query or url.fragment:
        raise MemoryError("Endpoint must not contain credentials, query parameters or fragments")
    if url.scheme != "https" and not is_loopback(url.hostname):
        raise MemoryError("Remote API endpoints require HTTPS")
    if config.provider == "ollama" and not is_loopback(url.hostname):
        raise MemoryError("The ollama provider is local-only; use a loopback endpoint")
    if config.api_key_env and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", config.api_key_env):
        raise MemoryError("api_key_env must be an environment-variable name, not a key")
    return config


def load_config(root: Path) -> Config:
    path = project_path(root, CONFIG_PATH)
    if not path.exists():
        return Config()
    try:
        values = tomllib.loads(path.read_text(encoding="utf-8-sig"))
        return validate(Config(**values))
    except (tomllib.TOMLDecodeError, TypeError) as exc:
        raise MemoryError("Invalid embedding.toml; check field names and TOML types") from exc


def save_config(root: Path, **values) -> dict:
    config = validate(Config(**values))
    path = project_path(root, CONFIG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Project-owned embedding settings. Secrets belong in environment variables."]
    lines.extend(
        f"{key} = {json.dumps(value, ensure_ascii=False)}"
        for key, value in asdict(config).items()
        if value is not None
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return status(config)


def status(config: Config) -> dict:
    return {
        "provider": config.provider,
        "model": config.model,
        "setup_required": config.provider == "unconfigured",
        "config": CONFIG_PATH,
        "message": (
            "请选择并配置 embedding：API 服务，或安装 Ollama 并下载本地 embedding 模型；也可显式 disabled 暂缓。"
            if config.provider == "unconfigured"
            else "Embedding 已显式禁用，仅提供关键词与图关系检索。"
            if not config.enabled
            else "配置已保存；运行 embedding doctor 检查服务，再运行 sync 构建项目向量索引。"
        ),
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise MemoryError("Embedding endpoint redirected; configure its final URL explicitly")


def normalized(vector) -> list[float]:
    if not isinstance(vector, list) or not vector or len(vector) > 16384:
        raise MemoryError("Embedding response contains an invalid vector")
    if any(type(value) not in {float, int} or not math.isfinite(value) for value in vector):
        raise MemoryError("Embedding response contains non-finite or non-numeric values")
    norm = math.hypot(*vector)
    if norm == 0 or not math.isfinite(norm):
        raise MemoryError("Embedding response contains a zero or invalid vector")
    return [value / norm for value in vector]


def embed(config: Config, texts: list[str]) -> list[list[float]]:
    validate(config)
    if not config.enabled:
        raise MemoryError("Configure an embedding provider first")
    if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
        raise MemoryError("Embedding inputs must be nonempty strings")
    payload = {"model": config.model, "input": texts}
    headers = {"Content-Type": "application/json"}
    if config.provider == "api":
        payload["encoding_format"] = "float"
        if config.api_key_env:
            secret = os.environ.get(config.api_key_env)
            if not secret:
                raise MemoryError(
                    f"Set the {config.api_key_env} environment variable before using the API"
                )
            if "\r" in secret or "\n" in secret:
                raise MemoryError("API key contains invalid header characters")
            headers["Authorization"] = "Bearer " + secret
    else:
        payload["truncate"] = False
    if config.dimensions is not None:
        payload["dimensions"] = config.dimensions
    request = urllib.request.Request(
        config.endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    handlers = [NoRedirect()]
    if is_loopback(urllib.parse.urlsplit(config.endpoint).hostname):
        handlers.append(urllib.request.ProxyHandler({}))
    try:
        with urllib.request.build_opener(*handlers).open(
            request, timeout=config.timeout_seconds
        ) as response:
            raw = response.read(32 * 1024 * 1024 + 1)
        if len(raw) > 32 * 1024 * 1024:
            raise MemoryError("Embedding response exceeds the size limit")
        data = json.loads(raw)
        if config.provider == "api":
            items = data["data"]
            if not isinstance(items, list) or any(
                not isinstance(item, dict) or type(item.get("index")) is not int for item in items
            ):
                raise MemoryError("API response has invalid embedding indexes")
            if sorted(item["index"] for item in items) != list(range(len(texts))):
                raise MemoryError("API response indexes do not match the requested inputs")
            vectors = [item["embedding"] for item in sorted(items, key=lambda item: item["index"])]
        else:
            vectors = data["embeddings"]
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise MemoryError("Embedding response count does not match the requested inputs")
        result = [normalized(vector) for vector in vectors]
        dimensions = {len(vector) for vector in result}
        if len(dimensions) != 1 or (
            config.dimensions is not None and dimensions != {config.dimensions}
        ):
            raise MemoryError("Embedding response dimensions are inconsistent")
        return result
    except urllib.error.HTTPError as exc:
        raise MemoryError(
            f"Embedding service returned HTTP {exc.code}; check endpoint, model, credentials and input limits"
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise MemoryError(
            "Embedding service unavailable; check the service and endpoint, or explicitly use --keyword-only"
        ) from None
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError, UnicodeError):
        raise MemoryError("Embedding service returned an invalid response") from None


def chunks_for(nodes: dict, config: Config) -> list[dict]:
    chunks = []
    for node_id, node in sorted(nodes.items()):
        if node["kind"] not in {"index", "functional", "design"}:
            continue
        prose = re.sub(
            r"\A\ufeff?---\r?\n.*?\r?\n---\r?\n", "", node["text"], count=1, flags=re.DOTALL
        )
        prose = re.sub(r"^```rag\s*\n.*?^```\s*$", "", prose, flags=re.MULTILINE | re.DOTALL)
        prose = (
            node.get("summary", "") + "\n" + " ".join(node.get("keywords", [])) + "\n" + prose
        ).strip()
        for start in range(0, len(prose), config.chunk_chars - config.chunk_overlap):
            text = prose[start : start + config.chunk_chars].strip()
            if not text:
                continue
            content = config.document_prefix + text
            chunks.append(
                {
                    "node_id": node_id,
                    "path": node["path"],
                    "text": text,
                    "input": content,
                    "key": digest((config.signature + "\0" + content).encode()),
                }
            )
            if start + config.chunk_chars >= len(prose):
                break
    return chunks


def sync_vectors(root: Path, nodes: dict, config: Config) -> tuple[list, dict, dict]:
    chunks = chunks_for(nodes, config)
    wanted = {chunk["key"]: chunk["input"] for chunk in chunks}
    path = project_path(root, "ForAI/rag/.cache/embeddings.sqlite3")
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, vector TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        meta = dict(connection.execute("SELECT key, value FROM metadata"))
        cached = (
            dict(connection.execute("SELECT key, vector FROM vectors"))
            if meta.get("signature") == config.signature
            else {}
        )
        vectors = {
            key: normalized(json.loads(value)) for key, value in cached.items() if key in wanted
        }
        dimension = (
            int(meta["dimensions"])
            if meta.get("signature") == config.signature and meta.get("dimensions")
            else None
        )
        missing = sorted(set(wanted) - set(vectors))
        for start in range(0, len(missing), config.batch_size):
            keys = missing[start : start + config.batch_size]
            batch = embed(config, [wanted[key] for key in keys])
            for key, vector in zip(keys, batch, strict=True):
                if dimension is not None and len(vector) != dimension:
                    raise MemoryError(
                        "Model dimensions changed; update revision in embedding.toml and rebuild"
                    )
                dimension = len(vector)
                vectors[key] = vector
        if dimension is not None and any(len(vector) != dimension for vector in vectors.values()):
            raise MemoryError("Cached vector dimensions are inconsistent; rebuild the vector cache")
        with connection:
            connection.execute("DELETE FROM vectors")
            connection.executemany(
                "INSERT INTO vectors VALUES (?, ?)",
                ((key, json.dumps(vector)) for key, vector in sorted(vectors.items())),
            )
            connection.execute(
                "INSERT OR REPLACE INTO metadata VALUES ('signature', ?)", (config.signature,)
            )
            connection.execute(
                "INSERT OR REPLACE INTO metadata VALUES ('dimensions', ?)",
                (str(dimension) if dimension else "",),
            )
    return (
        chunks,
        vectors,
        {
            "provider": config.provider,
            "model": config.model,
            "signature": config.signature,
            "chunks": len(chunks),
            "embedded": len(missing),
            "reused": len(wanted) - len(missing),
            "dimensions": dimension,
        },
    )


def semantic_search(
    root: Path, nodes: dict, text: str, config: Config, limit: int
) -> tuple[list, dict]:
    chunks, vectors, stats = sync_vectors(root, nodes, config)
    if not chunks:
        return [], stats
    query_vector = embed(config, [config.query_prefix + text])[0]
    if len(query_vector) != stats["dimensions"]:
        raise MemoryError(
            "Query dimensions differ from the index; check model revision and rebuild"
        )
    best = {}
    for chunk in chunks:
        score = sum(a * b for a, b in zip(query_vector, vectors[chunk["key"]], strict=True))
        if score > 0 and (
            chunk["node_id"] not in best or score > best[chunk["node_id"]]["similarity"]
        ):
            best[chunk["node_id"]] = {
                "node_id": chunk["node_id"],
                "path": chunk["path"],
                "similarity": score,
                "excerpt": chunk["text"][:300],
            }
    return sorted(best.values(), key=lambda item: (-item["similarity"], item["node_id"]))[
        :limit
    ], stats


def sync_project(root: Path) -> dict:
    config = load_config(root)
    if not config.enabled:
        return status(config)
    with closing(
        sqlite3.connect(project_path(root, "ForAI/rag/.cache/graph.sqlite3"))
    ) as connection:
        nodes = {
            key: json.loads(value)
            for key, value in connection.execute("SELECT id, data FROM nodes")
        }
    return sync_vectors(root, nodes, config)[2]
