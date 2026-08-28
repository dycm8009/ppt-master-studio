# Gate Handoff Decision — Chat-Inline Artifact PoC

Status: **experiment decision / not production authority**

## Observed host behavior

Human host acceptance on 2026-08-28 established all of the following:

- chat-inline artifact renders inside the conversation;
- local form/SVG state remains interactive after the assistant turn ends;
- Deck Review can update the preview immediately while the user edits;
- local undo/redo/reset can work;
- Confirm can freeze a canonical capture inside the artifact;
- the artifact does **not** automatically deliver that capture to the assistant;
- Confirm does **not** trigger the next assistant turn.

Therefore these states are distinct and must never be collapsed:

```text
editing -> captured -> delivered -> validated -> accepted
```

For the currently observed app-block host, the flow stops at `captured`.

## Rejected pseudo-solutions

### Short confirmation code

Rejected as a default handoff. A short hash can prove that some local state existed, but the Harness cannot reconstruct `changes[]` or Stage 1 values from the hash. If the whole state is encoded into the token, the result is merely JSON copy/paste in another representation.

### Screenshot as machine handoff

Rejected. A screenshot is useful human acceptance evidence, but it is not a lossless canonical Gate payload and must not be used to mint an accepted receipt.

### Assume the next user message exposes artifact state

Rejected by host test. A following message such as `已确认` did not carry the artifact local payload to the assistant.

### Hidden/undocumented host bridge

Rejected. Do not depend on unexposed APIs or attempt to infer private host methods.

## Viable transports

A Gate handoff transport is viable only when it can losslessly deliver the canonical capture to the Harness/assistant boundary.

| Transport | Lossless | Zero external runtime | Current artifact host | Decision |
|---|---:|---:|---:|---|
| Future host-native artifact submit | yes | yes | unavailable | preferred future path |
| Existing Static UI JSON return | yes | yes | available outside artifact | legacy fallback |
| Apps SDK / MCP App tool call | yes | no | different host model | optional alternate host, not this PoC |
| External state service | yes | no | app-block cannot fetch | rejected for this PoC |
| Short token without state store | no | yes | possible visually | rejected |
| Screenshot | no | yes | possible | human evidence only |

## Contract

The experimental artifact layer may create a canonical **capture**, but it may not create `accepted.stage1.json`, `accepted.deck-review.json`, or any other accepted receipt.

A future transport must produce an explicit handoff receipt containing at least:

- schema;
- `status=delivered`;
- transport identifier;
- SHA-256 of the exact canonical payload delivered;
- transport evidence suitable for host-level debugging.

Only after delivery may the existing official validator process the canonical payload. The existing validator remains the authority for `accepted`.

## Product implication

The realtime Deck Review editor is still useful and technically viable. Its architecture should remain:

```text
artifact local state
   <-> controls
   <-> realtime SVG preview
   -> canonical capture
   -> GateHandoff (pluggable; unavailable today)
   -> static_ui_adapter.py validate
   -> accepted receipt
```

Do not redesign the realtime editor around MCP or a remote service solely to make the experiment appear closed-loop.
