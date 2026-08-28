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

## Host capability observed in ChatGPT

The current inline artifact host supports a self-contained HTML/CSS/JavaScript app with local runtime state. This is enough for reactive Stage 1 forms and for a Deck Review editor where an SVG preview changes immediately as the user edits text, attributes, positions, or annotations.

The current host surface exposed to this project does **not** expose a supported callback that lets JavaScript submit a payload to the assistant, resume a suspended assistant turn, call a tool, or invoke the Harness. Therefore the PoC must not pretend that a local `Confirm` click has reached ChatGPT.

See `HOST_CAPABILITIES.json` for the machine-readable capability record.

## Authority boundary

`captured` is not `accepted`.

An artifact may construct the existing canonical response envelopes:

- Stage 1: `ppt-master-chat-confirm/v1`
- Deck Review: `ppt-master-static-deck-review-response/v1`

But only the existing Studio validator may produce `ppt-master-static-ui-accepted/v1`.

## Deck Review design

Deck Review is the strongest fit for the artifact host even before a handoff bridge exists.

1. Load the slide SVGs into local artifact state.
2. Select an element by stable SVG `id`.
3. Edit text / selected attributes / annotations in local draft state.
4. Apply the draft immediately to a cloned SVG DOM so the preview changes without another model turn.
5. Maintain an undoable `changes[]` manifest using the same semantics as the current static review UI.
6. `Confirm` freezes a canonical review response locally.
7. A future host handoff bridge transports that response to ChatGPT/Harness.
8. Harness validates the SVG roster hash before applying anything.

This separates realtime editing from authority and avoids making model latency part of the edit loop.

## Acceptance ladder

- **A0 Render** — artifact is embedded in the chat and all controls render.
- **A1 Local interaction** — edits update local UI/preview immediately; undo/reset work.
- **A2 Canonical capture** — Confirm freezes an envelope byte-for-byte compatible with the existing validator contract.
- **A3 Host handoff** — the host provides a supported artifact → assistant/tool callback carrying the frozen envelope. **Currently unavailable.**
- **A4 Harness acceptance** — `static_ui_adapter.py validate` verifies hashes/fields and creates `accepted.*.json`.

A0–A2 are useful now. A3 is the only missing host capability for a zero-copy end-to-end Gate. A4 must never be bypassed.

## Branch policy

This is an experiment branch from `studio-dev`. Do not merge it directly to `studio-main`. If a supported host handoff appears, migrate the proven adapter into `studio-dev`, run regression, and promote by PR.
