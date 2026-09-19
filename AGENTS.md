# Project workflow

Use uv for Python dependencies and commands. The reusable skill lives at
`skills/project-code-memory/SKILL.md`; read it for memory-related development.

The repository distributes a skill, not a central runtime service. Each adopter
owns ForAI/rag source, uv.lock, environment and database. Regenerate the skill bundle
with `uv run python tools/build_skill_runtime.py` after changing core source. Keep
this repository's ForAI/rag runtime copy in sync by explicitly reviewing/merging
the generated changes; bootstrap refuses to overwrite differing project files.

Read `ForAI/index.md` before changing implementation. Functional documentation
describes the current code; design records describe intent. Never rewrite code
solely to match a stale functional description, or silently rewrite design intent.

For each code change, update the relevant ForAI document and its reviewed evidence
fingerprints, and add/update a `kind: change` record with exact code hashes and
impact reasons. Do not refresh reviewed fingerprints without reading the code.

Before finishing run `uv run ruff check .`, `uv run ruff format --check .`,
`uv run pytest -q`, and `uv run ggrag scan --fail-on-issues`.
Before committing, stage the intended changes and run `uv run ggrag coverage --staged`.
The coverage check checks records, not the truth of their prose.
