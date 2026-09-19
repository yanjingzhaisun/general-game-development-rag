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
      type: python_literal
      path: src/session.py
      name: TTL_MINUTES
```
````

Allowed kinds: `index`, `functional`, `design`, `change`, `report`. No rag block means
`index`. Claims are supported only in functional and design documents. A design
document uses the same claim shape but `kind: design`. Functional sources without
reviewed SHA-256 hashes produce `needs_review`. Design sources do not require hashes.

Paths are project-relative with `/`; absolute paths, parent traversal and escaping
symlinks are rejected. `sources` binds whole files in v0.1 (symbols are not resolved).
Probe paths also create code relationships. Code text is read from disk, not stored
in the graph. `python_literal` reads exactly one top-level assignment using AST and
literal evaluation, never imports or executes the file. It is a syntactic observation,
not evidence that the value is the final runtime value.

Each claim requires stable local `id`, `subject`, `predicate`, `scope`, and `value`.
Use exact normalized units in the predicate, such as `ttl_minutes`; automatic unit
conversion is not implemented. Status is `active`, `proposed`, or `superseded`.
Only active claims participate in conflict checks. Scope must include relevant
environment/version conditions; v0.1 compares scope strings exactly.

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
