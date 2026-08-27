# PPT Master Studio — Static UI Rules

Preserve upstream human-in-the-loop semantics on hosts that cannot maintain localhost servers.

- Static HTML is an adapter for the upstream chat-confirmation branch; it must never manufacture official Flask receipts.
- A returned response becomes authoritative only after `studio/scripts/static_ui_adapter.py validate` succeeds against current artifact digests.
- Default Generate uses static Stage 1, static Stage 2, post-SVG Deck Review, and conditional Motion Review when custom motion is active. Plain-chat confirmation and explicit delegation remain allowed.
- Stage 2 must show whole-page visual evidence for each design direction; fixed visual styles reuse upstream preview SVGs, custom directions use clearly labeled comparison proxies.
- Fixed icon systems show real bundled SVG samples.
- Mode is a communication/narrative structure axis, separate from Visual Style; `custom` is valid. Fixed-mode changes should visibly change the structure preview, not pretend to change the visual skin.
- `image_usage` changes must not silently rewrite user-authored `image_notes`; show allowed-source readout and warn on likely contradictions. `none` is exclusive.
- Static HTML does not preserve the project filesystem; Portable Recovery checkpoints remain mandatory on serverless hosts.

## Revision-safe HTML filenames

- Every Static UI build must return a unique, versioned HTML filename containing a UTC build stamp and content digest. Reusing `confirm_stage1.html`, `confirm_stage2.html`, `deck_review.html`, or `motion_review.html` for mutable content is forbidden.
- `static_ui/latest.json` is the machine-readable pointer to the current build for each surface. ChatGPT must surface/open the exact path returned by the latest `static_ui_adapter.py build` call, not a remembered earlier attachment or fixed alias.
- Rebuilding a surface removes its legacy fixed-name HTML alias and retains only a bounded recent history (default 4 versions) to avoid stale-page ambiguity and uncontrolled Recovery growth.
- Accepted receipts remain canonical fixed names (`accepted.stage1.json`, etc.) because they represent the current accepted state, not a browsable HTML revision. Digest validation remains authoritative even when an old HTML revision still exists.
