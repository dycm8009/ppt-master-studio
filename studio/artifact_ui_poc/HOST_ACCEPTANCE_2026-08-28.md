# Chat Inline Artifact Host Acceptance — 2026-08-28

Branch: `feature/chat-inline-artifact-gate-poc`

## Scope

Human host acceptance for the ChatGPT inline UI artifact Deck Review proof of concept.

This test intentionally separates:

1. realtime editing inside the artifact,
2. local canonical capture inside the artifact,
3. artifact-to-assistant handoff,
4. Harness acceptance.

Only (1) and (2) are implemented by the artifact PoC. Harness acceptance remains outside the artifact and continues to belong to the existing validator path.

## Observed result

### A. Realtime edit loop — PASS

The tester edited the mock Deck Review directly inside the chat-embedded artifact. The SVG-like preview updated during editing and the inspector remained interactive.

The final captured review showed **6 changes across 2 slides**:

1. `slide-01.svg` / `#title`: set attribute `x = 82`
2. `slide-01.svg` / `#accent`: set attribute `opacity = 0.7`
3. `slide-02.svg` / `#subtitle`: replace text with `输入、约束、工具、输出形成稳定边界哈哈`
4. `slide-02.svg` / `#subtitle`: set attribute `x = 99`
5. `slide-02.svg` / `#subtitle`: set attribute `y = 124`
6. `slide-02.svg` / `#accent`: set attribute `fill = #4c1bf5`

The UI correctly reported `Captured · 6 changes` after confirmation.

### B. Local capture / freeze — PASS

After clicking `确认 Deck Review`, the artifact:

- froze the canonical review locally,
- displayed the captured state,
- disabled ordinary edit controls until `继续编辑`,
- preserved the distinction `captured · not validated`.

This is acceptable behavior for an artifact-local draft/capture layer.

### C. Artifact -> assistant callback — NOT AVAILABLE / FAIL FOR GATE HANDOFF

After the user clicked confirmation, no structured artifact state, callback event, or `changes[]` payload was delivered to the assistant automatically.

The assistant only learned the final six changes because the user sent a screenshot in a later chat turn. The screenshot is human-visible evidence, not a host callback and not a valid Harness receipt.

Therefore the tested host does **not** currently provide the required semantic bridge equivalent to:

```text
artifact.submit(payload)
    -> wake assistant
    -> deliver structured payload
```

Do not infer or simulate this bridge in production code.

### D. Harness acceptance — NOT TESTED

No `accepted.deck-review.json` was created by this host test. The existing validator remains the only authority for acceptance.

## Decision

The chat-inline artifact is suitable for:

- realtime Deck Review editing,
- local visual preview,
- local undo / redo / reset,
- local change-manifest construction,
- local capture before handoff.

It is **not currently sufficient by itself as a Gate transport** because the host does not return the captured payload to the assistant.

Production architecture must therefore preserve a separate `Gate Handoff` abstraction:

```text
Interactive Artifact
  = realtime editor + preview + local capture

Gate Handoff
  = host-supported structured return path (currently unavailable in this host)

Harness Validator
  = sole accepted-receipt authority
```

## Regression rule

A future host capability may upgrade the handoff from `unavailable` to a real structured callback. Until that is observed in a human host acceptance test, automated tests and documentation must continue to treat artifact-to-assistant handoff as unavailable and must never mark local capture as `accepted`.
