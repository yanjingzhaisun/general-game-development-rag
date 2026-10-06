# Document contract

All target-project AI documents live in `ForAI/` and use UTF-8. The frontmatter has
four required fields. Stable IDs survive file renames; duplicate IDs are rejected.

````markdown
---
id: session-behavior
keywords_en: [session, expiration]
keywords_zh: [会话, 过期]
summary: 说明当前实现中的会话有效期。
---

# 会话有效期

当前静态默认值为 30 分钟。运行环境是否覆盖该值需另查配置和调用链。

```rag
kind: functional
sources:
  - path: src/session.py
    # After reading the file, add sha256 from local manage.py hash.
claims:
  - id: ttl-default
    subject: session
    predicate: ttl_minutes
    scope: static-default
    value: 30
    status: active
    probe:
      capability: literal
      language: typescript
      reader: ts-tree-sitter
      path: src/session.ts
      name: TTL_MINUTES
```
````

Allowed kinds: `index`, `functional`, `design`, `change`, `report`. No rag block means
`index`. Claims are supported only in functional and design documents. A design
document uses the same claim shape but `kind: design`. Functional sources without
reviewed SHA-256 hashes produce `needs_review`. Design sources do not require hashes.

Paths are project-relative with `/`; absolute paths, parent traversal and escaping
symlinks are rejected. `sources` binds whole files in v0.2 (symbols are not resolved).
Probe paths also create code relationships. Code text is read from disk, not stored
in the graph. New probes name a language-independent `capability` (currently `literal`),
an optional `language` (otherwise inferred from the path extension), and an optional
`reader`. Without an explicit reader, exactly one enabled reader must support the
capability and language. An explicit reader that is missing, disabled, or incompatible
produces `probe_unresolved`; ambiguity requires `disambiguate_reader`. Every unresolved
probe carries an action (`inspect_code`, `install_reader`, `enable_reader`,
`inspect_reader`, or `disambiguate_reader`), and must never be treated as a pass.
An unregistered reader name requires `inspect_reader`; `enable_reader` applies only
when a matching reader is registered but disabled.
Successful evidence includes reader name, version, language, capability, precision
(`syntactic` or `semantic`),
and a `dependencies` mapping of reader-declared package names to installed versions.
Unavailable dependency version metadata is omitted; no known versions produces `{}`.
Syntactic evidence is not semantic proof.
Readers are registered in `general_game_development_rag.readers.REGISTRY` with a unique
name, `kind` (`python` or `command`), module/entrypoint or executable, declared version,
precision, capabilities, languages, and enabled state. Python entrypoints accept `(path,
name)` and return a JSON-compatible value. A command receives one JSON object on stdin
with `source` and `name`, then returns `{"value": ...}` on stdout. Command readers have a
10-second timeout; missing commands, timeouts, nonzero exits, or malformed output require
`inspect_reader`. The reader process receives source text, never an instruction to execute it.
Python readers can opt into `reports_evidence` to accept an optional keyword `evidence`
mapping and populate additional observations; the returned literal value is unchanged.

The `type` field is deprecated; including it raises an error.
`builtin-python` supports `capability: literal` with `language: python` and uses AST
literal evaluation. Optional
`ts-tree-sitter` reads top-level JavaScript/TypeScript `const`, `let`, and `var` literal
declarations, including exports, type annotations, `as const`, and `satisfies`. Readers
must inspect source text only; they never import or execute target-project code. These
are syntactic observations, not evidence that a value wins at runtime.

Optional `ts-kotlin` uses the same tree-sitter traversal with a Kotlin grammar for `.kt`
and `.kts`. It reads `val`/`var` initializers (including `const val` and type annotations)
and simple identifier assignments in Gradle Kotlin DSL blocks. It skips function/class
bodies, rejects multiple matching writes and unsupported dynamic expressions, and does
not evaluate Gradle, resolve references or choose between build variants. Install the
optional readers with `uv sync --extra readers`; missing grammar dependencies require
`install_reader`. For example, `versionCode = 36` inside `defaultConfig`:

```yaml
probe:
  capability: literal
  language: kotlin       # inferred from .kt or .kts if omitted
  reader: ts-kotlin      # optional when it is the only enabled Kotlin reader
  path: app/build.gradle.kts
  name: versionCode
```

`builtin-xml` uses Python's standard-library ElementTree with no extra dependencies.
For `.xml`, `name` is an attribute name: `versionName` matches a local attribute name,
and `android:versionName` matches the namespace prefix declared in the XML. Values are
strings, without resource substitution. The first matching attribute in document order
wins; evidence always includes `matches: N`. If multiple matches have different values,
it also includes `ambiguous: true`; duplicate identical values do not set that flag.
An absent attribute requires `inspect_code`; malformed XML requires `inspect_reader`.

```yaml
probe:
  capability: literal
  language: xml          # inferred from .xml if omitted
  path: app/src/main/AndroidManifest.xml
  name: android:versionName  # versionName also matches
```

Each claim requires stable local `id`, `subject`, `predicate`, `scope`, and `value`.
Use exact normalized units in the predicate, such as `ttl_minutes`; automatic unit
conversion is not implemented. Status is `active`, `proposed`, or `superseded`.
Only active claims participate in conflict checks. Scope must include relevant
environment/version conditions; v0.2 compares scope strings exactly.

Change record body:

```yaml
kind: change
covers:
  - path: src/session.py
    sha256: <64-character SHA-256 of the changed code blob>
    reason: 将默认会话有效期调整为 30 分钟，并同步会话功能说明。
  - path: src/obsolete.py
    sha256: deleted
    reason: 删除旧会话实现，调用方已迁移。
```

Put this in a rag fence in a normal frontmatter-bearing Markdown document. The
coverage document itself must be changed in the staged set or checked commit range.
Git line-ending filters affect blob hashes: use LF via project `.gitattributes`, or
calculate the exact staged blob hash when the working file differs from the index.
No generated record should claim evidence review that did not happen.
