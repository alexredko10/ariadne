# Ariadne Anchors

## What are Anchors?

Anchors are machine-readable semantic landmarks embedded in source code
and documentation.  They mark entities, risks, invariants, owners, state
boundaries, transitions, and purposes for automatic discovery.

Anchors are used by:
- Context Compiler — to include relevant landmarks in Context Packs
- Conductor — to understand task context
- Rubric Generator — to build task-specific rubrics
- Rubric Judge — to verify that invariants are preserved
- Agents — to find stable reference points in the repository

## Canonical prefix

Canonical: `@ariadne-*`

Examples:
- `@ariadne-domain`
- `@ariadne-risk`
- `@ariadne-invariant`

## Compatibility aliases

`@ariadna-*` may be accepted as compatibility input if already present
in source materials.  New annotations should use `@ariadne-*`.

## Supported anchor kinds

| Kind           | Annotation example                                    |
|----------------|--------------------------------------------------------|
| domain         | `@ariadne-domain auth`                                 |
| risk           | `@ariadne-risk security`                               |
| invariant      | `@ariadne-invariant auth.refresh_token.rotation.atomic`|
| owner          | `@ariadne-owner auth-session`                          |
| state          | `@ariadne-state Invoice`                               |
| transition     | `@ariadne-transition invoice.post`                     |
| register       | `@ariadne-register stock`                              |
| derived-view   | `@ariadne-derived-view invoice.total`                  |
| purpose        | `@pcam-purpose preserve-session-security`              |
| non-goal       | `@pcam-non-goal do-not-weaken-token-validation`        |
| stop-condition | `@pcam-stop-condition protected-file-change-requires-approval` |

## Indexing behavior

Anchors must be discoverable by an indexer.  The AnchorIndexRecord stores
the anchor ID, kind, value, source path, symbol, hash, and associated
context pack IDs for fast lookup.

## Inclusion in Context Packs

When a Context Pack is assembled for a task, relevant anchors must be
included in SemanticContext.anchors.  Relevance is determined by matching
anchor scope to task domain and affected paths.

## Relationship to State-First annotations

State-First annotations (`@ariadne-state`, `@ariadne-transition`,
`@ariadne-register`, `@ariadne-derived-view`) are a subset of anchor kinds.
They are reused here without replacing existing State-First semantics.

## Relationship to PCAM annotations

PCAM annotations (`@pcam-purpose`, `@pcam-non-goal`,
`@pcam-stop-condition`) are also a subset of anchor kinds.
They are included for compatibility with future PCAM integration.

## Relationship to risks and invariants

Risks and invariants marked with `@ariadne-risk` and `@ariadne-invariant`
are semantic anchors.  They must be visible to the Rubric Judge and
included in Context Packs when the task scope intersects their domain.

## Authorization boundary

Anchors are:
- evidence
- context
- semantic landmarks

Anchors are NOT:
- execution authorization
- mutation permission
- runtime commands

Anchors must not contain secrets.
