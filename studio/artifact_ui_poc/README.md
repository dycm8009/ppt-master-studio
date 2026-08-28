# Chat-inline Artifact Gate PoC

This experiment targets the **chat-embedded interactive UI artifact** host surface only.

It is intentionally separate from:

- ChatGPT Sites
- MCP Apps / Apps SDK
- WebMCP
- Cloudflare or any external domain/runtime
- standalone HTML handoff pages

## Goal

Use a chat-embedded artifact as the realtime editing frontend for PPT Master confirmation/review surfaces while preserving the existing Harness validator as the only authority that may create an accepted receipt.

```text
Harness data
   ↓
real project adapter
   ↓
chat-inline artifact
   ↕ local realtime edits
preview / controls / undo / reset
   ↓
canonical confirmation snapshot
   ↓
Gate Handoff bridge
   ↓
static_ui_adapter.py validate
   ↓
accepted.*.json
```

## Verified host boundary

Human acceptance on 2026-08-28 verified:

- embedded interactive artifact rendering works;
- local form and SVG edits are reactive;
- undo / redo / reset can run inside the artifact;
- Confirm can freeze a canonical local capture;
- the current host does **not** expose a supported artifact → assistant callback or a suspended assistant turn that resumes on Confirm.

Therefore `captured` is never treated as `delivered` or `accepted`.

See:

- `HOST_CAPABILITIES.json`
- `HOST_ACCEPTANCE_2026-08-28.md`
- `HANDOFF_DECISION.md`

## Real Studio data path

The PoC no longer depends on mock Stage 1 data or mock slides.

`project_models.py` reads the same project inputs used by the current Static UI:

### Stage 1

Inputs:

- `<project>/confirm_ui/recommendations.stage1.json`
- `<project>/confirm_ui/template_options.json`
- the official canvas catalog and bundled template indexes

Output model:

- `ppt-master-chat-inline-stage1-model/v1`

The model carries the **same** `recommendation_sha256` and `options_sha256` consumed by the existing Stage 1 validator.

### Deck Review

Input:

- `<project>/svg_output/*.svg`

Output model:

- `ppt-master-chat-inline-deck-review-model/v1`

For chat rendering, local raster/SVG image references are converted to data URIs so the artifact remains self-contained. Remote/file/unresolved references fail closed. SVG `<script>` blocks and inline event handlers are removed from the artifact rendering copy.

The authoritative `svg_roster_sha256` is still calculated with the exact semantics of `studio.static_ui.review.deck_review_html`, so rendering transformations do not change validator freshness authority.

## Real artifact renderer

`renderer.py` converts the real project models into self-contained inline HTML fragments suitable for the chat interactive UI artifact host.

Stage 1 includes:

- all communication fields;
- language and canvas;
- free-design / templates mode;
- bundled template candidates and explicit workspace candidates;
- local canonical `ppt-master-chat-confirm/v1` capture.

Deck Review includes:

- real SVG slides;
- element selection by stable SVG `id`;
- live text / fill / opacity / transform / X / Y editing;
- generic SVG attribute editing;
- AI annotations;
- undo / redo / reset;
- live `changes[]` manifest;
- local canonical `ppt-master-static-deck-review-response/v1` capture.

The renderer produces an HTML **fragment**, not a standalone page. It intentionally contains no domain, fetch, MCP, iframe, or external runtime dependency.

## Host-ready package

Build a complete package with:

```bash
python -m studio.artifact_ui_poc.build_artifact stage1 <project>
python -m studio.artifact_ui_poc.build_artifact deck-review <project>
```

The package schema is:

- `ppt-master-chat-inline-artifact-package/v1`

It contains:

- the real project model;
- the inline HTML fragment;
- host render metadata;
- the current `ArtifactHostProfile` Gate plan;
- the explicit authority boundary.

For inspection/debugging:

```bash
python -m studio.artifact_ui_poc.build_artifact stage1 <project> --format model
python -m studio.artifact_ui_poc.build_artifact deck-review <project> --format html
```

## Authority boundary

An artifact may construct the existing canonical response envelopes:

- Stage 1: `ppt-master-chat-confirm/v1`
- Deck Review: `ppt-master-static-deck-review-response/v1`

But only the existing Studio validator may produce `ppt-master-static-ui-accepted/v1`.

The Gate state machine is:

```text
editing → captured → delivered → validated → accepted
```

The currently observed chat artifact host reaches `captured`. `handoff.py` requires a trusted `delivered` receipt with a matching canonical payload digest before a validator may be invoked.

## Acceptance ladder

- **A0 Render** — artifact is embedded in the chat and all controls render. **Verified.**
- **A1 Local interaction** — edits update local UI/preview immediately; undo/reset work. **Verified.**
- **A2 Canonical capture** — Confirm freezes an envelope compatible with the existing validator contract. **Verified.**
- **A2.5 Real project data** — the artifact consumes real Stage 1 inputs / real `svg_output` while preserving validator hashes. **Automated contract verified.**
- **A3 Host handoff** — the host provides a supported artifact → assistant/tool callback carrying the frozen envelope. **Currently unavailable.**
- **A4 Harness acceptance** — `static_ui_adapter.py validate` verifies hashes/fields and creates `accepted.*.json`.

A0–A2.5 are usable now. A3 remains the only missing host capability for a zero-copy end-to-end Gate. A4 must never be bypassed.

## Branch policy

This is an experiment branch from `studio-dev`. Do not merge it directly to `studio-main`. If this architecture is adopted, migrate the proven pieces into `studio-dev`, run the full Studio regression suite, and promote by PR.
