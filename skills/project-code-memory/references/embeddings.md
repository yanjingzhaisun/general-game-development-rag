# Embedding setup and operation

During installation, explicitly ask the user to choose:

1. An embedding API: model, complete endpoint and API-key environment-variable name.
2. A local model: install Ollama and download the user's selected embedding model.
3. Configure later: leave unconfigured or explicitly disabled, and state that semantic
   retrieval is not enabled. Do not silently choose a paid provider or download a model.

Present the installer's `embedding.prompt` to the user. The installer is noninteractive
so an agent can manage this question; it does not claim embeddings are ready. Never ask
the user to paste a secret into chat or commit one to a file.

Run all commands from the adopting project's root. Configuration lives in
`ForAI/rag/embedding.toml` (gitignored). The versioned `embedding.example.toml` provides
team defaults without secrets. Each project owns its vector cache.

## API option

The api provider accepts the OpenAI-compatible embeddings request/response format.
Specify the **full** embeddings endpoint; a base URL alone is not enough. For example:

```text
uv run --directory ForAI/rag python manage.py embedding configure --provider api --model text-embedding-3-small --endpoint https://api.openai.com/v1/embeddings --api-key-env GGRAG_EMBEDDING_API_KEY
```

Set `GGRAG_EMBEDDING_API_KEY` in the process environment through the user's shell or
secret manager. Only the variable name is stored. Other compatible services may use
different model names/endpoints. An unauthenticated local compatible API can use an
empty `api_key_env` in TOML. Remote endpoints require HTTPS; redirects are rejected.

API mode sends the query and ForAI navigation/functional/design prose to that configured
service. It does not read or upload raw source files for embedding; document snippets
written by the project are part of the document text. Confirm provider choice before use.

Protocol reference: [OpenAI embeddings API](https://developers.openai.com/api/reference/resources/embeddings/methods/create).

## Local option: Ollama

Install [Ollama](https://ollama.com/download) if absent and ensure its local service is
running. Ask which embedding model to use; the official documentation uses embeddinggemma
as an example. After the user chooses it:

```text
ollama pull embeddinggemma
uv run --directory ForAI/rag python manage.py embedding configure --provider ollama --model embeddinggemma
```

Default endpoint: `http://127.0.0.1:11434/api/embed`. This provider accepts loopback
addresses only and bypasses HTTP proxy environment variables for local traffic.
Ollama owns model weights; the Python runtime needs no torch or sentence-transformers
installation. Normal chat-only models are not interchangeable with embedding models.

Protocol reference: [Ollama embed API](https://docs.ollama.com/api/embed).

## Validate and index

```text
uv run --directory ForAI/rag python manage.py embedding status
uv run --directory ForAI/rag python manage.py embedding doctor
uv run --directory ForAI/rag python manage.py sync
uv run --directory ForAI/rag python manage.py query "角色倒地后怎么恢复"
```

Doctor sends only a small test string and checks vector shape. It does not measure
semantic quality. Sync embeds document chunks; query combines cosine similarity and
keyword rankings using reciprocal-rank fusion, then expands graph relationships.

No configuration means keyword-only results with `setup_required: true`. A configured
provider failure returns an error instead of silently degrading. To intentionally work
without it, pass `query ... --keyword-only`, or configure `--provider disabled`.
Scan remains deterministic and makes no embedding requests.

## Cache, model changes and limits

- Vectors are in `ForAI/rag/.cache/embeddings.sqlite3`; do not commit them.
- Unchanged content uses cached vectors. Removed document chunks leave the active cache.
- Provider, endpoint, model, revision, dimensions, prefixes and chunk settings identify
  the vector space; changes rebuild the corresponding vectors. Keep `revision` up to
  date when replacing weights behind the same model name.
- `document_prefix` and `query_prefix` support models requiring instruction prefixes.
  Set these according to the chosen model's own instructions. Both default to empty.
- Chunking uses characters, not model tokens: defaults are 1200 characters and 150
  overlap, 16 inputs per request. Adjust to provider limits. Ollama truncation is disabled.
- `dimensions` is optional and only works when the chosen API/model supports it.
- Configuring via CLI writes a complete config; to retain custom advanced settings,
  pass their options or edit TOML directly. API keys are never written by the CLI.
- Vectors use exact cosine search in SQLite-backed local storage, not an ANN service.
  Full graph rebuilding remains separate from incremental vector computation.
- Embedding similarity is a retrieval signal, not proof of correctness or conflict.
