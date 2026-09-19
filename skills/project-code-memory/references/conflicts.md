# Conflict handling

| Finding | Meaning | Action |
|---|---|---|
| unverified_description | Functional document has no sources | Locate code and add evidence |
| needs_review | Missing or changed reviewed hash | Read code; update prose if needed, then hash |
| missing_source | Referenced file does not exist | Investigate deletion/rename; repair references |
| description_drift | Functional claim differs from static literal probe | Correct functional description after inspecting code |
| design_deviation | Design claim differs from static literal probe | Determine whether implementation or design should change |
| probe_unresolved | Probe cannot determine a literal | Inspect code; never invent a value |
| claim_conflict_candidate | Same-kind active claims disagree within identical scope | Check evidence, units, missing conditions and duplicate claims |

Functional claims without probes remain authored descriptions, not mechanically
verified semantics. Cross-kind claims are not automatically compared: stale functional
prose is insufficient evidence that code violates design. Direct code probes provide
the implemented comparison; other comparisons require reading actual code.

Generated issues have stable IDs derived from kind and participants. `scan --write-report`
replaces the current report; it is not a history database. Preserve meaningful resolutions
in a separate frontmatter-bearing conflict document with issue ID, evidence, decision,
and validation. State whether resolved, excluded, or still awaiting evidence. Change
the source documents, then rebuild; never repair only SQLite rows.

No automatic semantic overwrite or timestamp-based winner selection. A scan finding
that disappears because its document was deleted is not proof of resolution; consult
the change record. Scope checks are exact string matching, not environment inference.
