# Commands

From the adopting project's root, use only its copied runtime:

```text
uv run --directory ForAI/rag python manage.py init
uv run --directory ForAI/rag python manage.py embedding status
uv run --directory ForAI/rag python manage.py embedding doctor
uv run --directory ForAI/rag python manage.py hash src/session.py
uv run --directory ForAI/rag python manage.py sync
uv run --directory ForAI/rag python manage.py query "session 会话" --limit 5 --hops 2 --max-nodes 40
uv run --directory ForAI/rag python manage.py scan --write-report --fail-on-issues
uv run --directory ForAI/rag python manage.py coverage --staged
uv run --directory ForAI/rag python manage.py coverage --base <base-commit>
```

Output is JSON. Exit 0 is successful execution, exit 1 is failed coverage or findings
with `--fail-on-issues`, exit 2 is invalid input or operational error. `embedding doctor`
also exits 1 when no provider is enabled. `sync` reports graph findings without failing,
but a configured embedding provider failure is an error. `scan` checks all ForAI documents,
source fingerprints, explicit claims and supported probes without contacting models.
Query combines token-substring and embedding cosine rankings with graph traversal;
answer generation is performed by the calling agent. See [embedding setup](embeddings.md).
Use short feature keywords; Chinese natural-language segmentation is not implemented.

Source, pyproject.toml and uv.lock under ForAI/rag are owned and versioned by this
project; `.venv` is its independent environment. SQLite lives in
`ForAI/rag/.cache/graph.sqlite3`. No command needs the distribution repository after
bootstrap. All sync/query/scan commands rebuild
the graph projection; sync/query reuse content-addressed vectors and embed changed
document chunks. Unconfigured/disabled embeddings are visible in query output; a
configured provider outage fails unless `--keyword-only` explicitly skips embeddings.
Generated `kind: report`
documents are validated but excluded from retrieval to prevent feedback loops.

Coverage defaults to known code suffixes (.py, .cs, .cpp, .c, .h, .hpp, .gd, .rs, .js,
.ts, .tsx, .jsx, .lua, .shader, .hlsl, .glsl, .go, .java, .swift). Configuration files,
binary assets and unlisted languages require manual review in v0.2. `--base` verifies
the aggregate base-to-HEAD change, not every intermediate commit. Test each commit's
staged state to enforce per-commit coverage. Hooks and timers are not auto-installed.
