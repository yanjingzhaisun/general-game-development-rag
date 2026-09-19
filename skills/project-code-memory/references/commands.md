# Commands

From the adopting project's root, use only its copied runtime:

```text
uv run --directory ForAI/rag python manage.py init
uv run --directory ForAI/rag python manage.py hash src/session.py
uv run --directory ForAI/rag python manage.py sync
uv run --directory ForAI/rag python manage.py query "session 会话" --limit 5 --hops 2 --max-nodes 40
uv run --directory ForAI/rag python manage.py scan --write-report --fail-on-issues
uv run --directory ForAI/rag python manage.py coverage --staged
uv run --directory ForAI/rag python manage.py coverage --base <base-commit>
```

Output is JSON. Exit 0 is successful execution, exit 1 is failed coverage or findings
with `--fail-on-issues`, exit 2 is invalid input or operational error. `sync` reports
findings without failing. `scan` checks all ForAI documents, source fingerprints,
explicit claims and supported probes. Query is token-substring retrieval plus bounded
bidirectional graph traversal, not vector retrieval or automatic answer generation.
Use short feature keywords; Chinese natural-language segmentation is not implemented.

Source, pyproject.toml and uv.lock under ForAI/rag are owned and versioned by this
project; `.venv` is its independent environment. SQLite lives in
`ForAI/rag/.cache/graph.sqlite3`. No command needs the distribution repository after
bootstrap. All sync/query/scan commands rebuild
the current projection; incremental indexing is deferred. Generated `kind: report`
documents are validated but excluded from retrieval to prevent feedback loops.

Coverage defaults to known code suffixes (.py, .cs, .cpp, .c, .h, .hpp, .gd, .rs, .js,
.ts, .tsx, .jsx, .lua, .shader, .hlsl, .glsl, .go, .java, .swift). Configuration files,
binary assets and unlisted languages require manual review in v0.1. `--base` verifies
the aggregate base-to-HEAD change, not every intermediate commit. Test each commit's
staged state to enforce per-commit coverage. Hooks and timers are not auto-installed.
