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
复制并继续  (current fallback transport)
   ↓
paste/send to ChatGPT
   ↓
static_ui_adapter.py validate
   ↓
accepted.*.json
```

The long-term zero-copy architecture keeps the same artifact models and replaces only the fallback transport if a supported host-native artifact callback becomes available.

## Official parity contract

The artifact is a **presentation host adapter**, not a second PPT Master product model.

Contract-level behavior remains sourced from the existing Static UI / validator. The artifact may reorganize controls and make previews reactive, but it must not invent canonical fields, enums, hashes, candidate IDs, animation effects, or accepted receipts.

See `PARITY_CONTRACT.md` for the locked parity rules.

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

### Stage 1

Inputs:

- `<project>/confirm_ui/recommendations.stage1.json`
- `<project>/confirm_ui/template_options.json`
- official canvas catalog and bundled template indexes

Output model:

- `ppt-master-chat-inline-stage1-model/v1`

The model carries the same `recommendation_sha256` and `options_sha256` consumed by the existing Stage 1 validator.

### Stage 2

Input:

- `<project>/confirm_ui/recommendations.stage2.json`
- official catalogs / preview helpers

Output model:

- `ppt-master-chat-inline-stage2-model/v1`

The adapter directly reuses PPT Master's current Mode / Visual Style / Icons / Fonts / Image Usage / Image AI Path / Generation Mode catalogs and the official direction/style/icon preview helpers. The response uses the official `ppt-master-chat-confirm/v1`, `surface=stage2`, `values.stage=final` contract.

Parity CI passes the artifact-produced default capture directly to the **unmodified** `validate_stage2()`.

### Deck Review

Input:

- `<project>/svg_output/*.svg`

Output model:

- `ppt-master-chat-inline-deck-review-model/v1`

For chat rendering, local image references are converted to data URIs so the artifact remains self-contained. Remote/file/unresolved references fail closed. SVG `<script>` blocks and inline event handlers are removed from the artifact rendering copy.

The authoritative `svg_roster_sha256` is still calculated with the exact semantics of `studio.static_ui.review.deck_review_html`, so rendering transformations do not change validator freshness authority.

### Motion Review

Input:

- `<project>/static_ui/motion_plan.json`
- official transition / object-animation registry from `pptx_animations.py --list`

Output model:

- `ppt-master-chat-inline-motion-review-model/v1`

Motion Review is conditional: it is only buildable when the official motion plan exists. The canonical response is `ppt-master-static-motion-review-response/v1` and parity CI passes the artifact-produced default capture directly to the **unmodified** `validate_motion()`.

## Artifact interaction

### Stage 1

- all communication fields;
- language and canvas;
- free-design / templates mode;
- bundled template candidates and explicit workspace candidates;
- local canonical capture;
- `复制并继续` fallback handoff.

### Stage 2

- exactly three whole-page visual direction samples;
- official Mode / Visual Style / Icons / Font / Image Strategy controls;
- official direction/style/icon preview semantics;
- palette and typography editing;
- production options;
- official local canonical capture;
- `复制并继续` fallback handoff.

### Deck Review

- real SVG slides;
- element selection by stable SVG `id`;
- live text / fill / opacity / transform / X / Y editing;
- generic SVG attribute editing;
- AI annotations;
- undo / redo / reset;
- live `changes[]` manifest;
- local canonical `ppt-master-static-deck-review-response/v1` capture;
- `复制并继续` fallback handoff.

### Motion Review

- official transition-effect options;
- official object-animation options;
- duration editing;
- keep/disable object motion per slide;
- group effect editing;
- reason / override comments;
- local canonical capture;
- `复制并继续` fallback handoff.

## Copy-and-continue fallback

`copy_handoff.py` provides the common Stage 1 / Deck Review / Motion Review handoff panel. Stage 2 implements the same pattern directly because its parity renderer already exposes the full canonical output.

The enhancer preserves the empirically verified **single `<script>` artifact rule** by injecting a second IIFE inside the existing script element instead of adding another script element.

Clicking `复制并继续` copies the exact frozen canonical JSON. The user then pastes and sends it to ChatGPT. This is transport only; it does not create an accepted receipt.

## Host-ready package

Build a complete package with:

```bash
python -m studio.artifact_ui_poc.build_artifact stage1 <project>
python -m studio.artifact_ui_poc.build_artifact stage2 <project>
python -m studio.artifact_ui_poc.build_artifact deck-review <project>
python -m studio.artifact_ui_poc.build_artifact motion-review <project>
```

The package schema is:

- `ppt-master-chat-inline-artifact-package/v1`

It contains:

- the real project model;
- the inline HTML fragment;
- host render metadata;
- the current `ArtifactHostProfile` Gate plan;
- the explicit authority boundary;
- `manual_handoff=copy-paste-canonical-json` while native handoff is unavailable.

For inspection/debugging:

```bash
python -m studio.artifact_ui_poc.build_artifact stage1 <project> --format model
python -m studio.artifact_ui_poc.build_artifact stage2 <project> --format html
python -m studio.artifact_ui_poc.build_artifact deck-review <project> --format html
python -m studio.artifact_ui_poc.build_artifact motion-review <project> --format model
```

## Authority boundary

An artifact may construct the existing canonical response envelopes:

- Stage 1: `ppt-master-chat-confirm/v1`
- Stage 2: `ppt-master-chat-confirm/v1`
- Deck Review: `ppt-master-static-deck-review-response/v1`
- Motion Review: `ppt-master-static-motion-review-response/v1`

But only the existing Studio validator may produce `ppt-master-static-ui-accepted/v1`.

The Gate state machine remains:

```text
editing → captured → delivered → validated → accepted
```

The currently observed chat artifact host reaches `captured`. Copy/paste is the explicit current fallback transport. `handoff.py` still prevents local capture, screenshot evidence, or short tokens from being treated as a trusted host-native delivery receipt.

## Acceptance ladder

- **A0 Render** — artifact is embedded in the chat and all controls render. **Verified.**
- **A1 Local interaction** — edits update local UI/preview immediately; undo/reset work. **Verified.**
- **A2 Canonical capture** — Confirm freezes an envelope compatible with the existing validator contract. **Verified.**
- **A2.5 Real project data / official parity** — Stage 1, Stage 2, Deck Review and conditional Motion Review consume official Studio inputs and preserve validator semantics. **Automated contract verified.**
- **A3 Host-native handoff** — a supported artifact → assistant/tool callback carries the frozen envelope. **Currently unavailable.**
- **A3-fallback Manual handoff** — `复制并继续` → paste/send canonical JSON. **Implemented.**
- **A4 Harness acceptance** — `static_ui_adapter.py validate` verifies hashes/fields and creates `accepted.*.json`.

## Branch policy

This is an experiment branch from `studio-dev`. Do not merge it directly to `studio-main`. If this architecture is adopted, migrate the proven pieces into `studio-dev`, run the full Studio regression suite, and promote by PR.
