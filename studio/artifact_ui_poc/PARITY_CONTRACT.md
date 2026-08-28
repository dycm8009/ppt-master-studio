# Chat-inline Artifact Official Parity Contract

The chat-inline artifact is a **presentation host adapter**, not a second PPT Master product model.

## Must stay 1:1 with PPT Master authority

The following are contract-level and must not be invented, renamed, removed, or silently normalized by the artifact layer:

- canonical schema IDs and `surface` IDs;
- recommendation / options / plan / SVG freshness hashes;
- canonical enum / catalog IDs;
- required editable fields and validation rules;
- template candidate keys and template-selection semantics;
- Stage 2 three-direction requirement and selected direction source;
- Stage 2 Mode / Visual Style / Icons / Fonts / Image Usage / Generation Mode option universes;
- Stage 2 palette roles and typography response shape;
- Deck Review `changes[]` semantics and `svg_roster_sha256` semantics;
- Motion Review transition and object-animation registries;
- accepted receipt schema and authority.

Sources of truth remain the existing Studio Static UI modules and validator:

- `studio/static_ui/stage1.py`
- `studio/static_ui/stage2.py`
- `studio/static_ui/stage2_js.py`
- `studio/static_ui/previews.py`
- `studio/static_ui/review.py`
- `studio/static_ui/assets.py`
- `studio/static_ui/validators.py`
- `studio/scripts/static_ui_adapter.py validate`

## Allowed host adaptations

The artifact host may improve interaction without changing the canonical result:

- reorganize fields for a narrower inline viewport;
- use tabs, inspectors, disclosure panels, responsive grids, or sticky controls;
- update previews immediately while the user edits;
- provide undo / redo / reset;
- select SVG elements directly and apply edits to a local preview;
- show richer semantic feedback for Mode / Visual Style / Icons / Image Strategy;
- inline project-local visual assets for self-contained chat rendering;
- sanitize executable SVG content from the rendering copy;
- expose the canonical payload in a read-only handoff panel;
- provide `复制并继续` as the current manual transport fallback.

These adaptations must not alter the payload that is later passed to the validator.

## Surface parity

### Stage 1

Canonical response: `ppt-master-chat-confirm/v1`, `surface=stage1`.

Must preserve:

- primary language;
- canvas;
- audience;
- communication intent;
- audience outcome;
- core message;
- delivery context;
- artifact afterlife;
- content divergence;
- template mode and candidate keys;
- `recommendation_sha256`;
- `options_sha256`.

### Stage 2

Canonical response: `ppt-master-chat-confirm/v1`, `surface=stage2`, `values.stage=final`.

Must preserve the exact official catalogs and response fields for:

- exactly three design directions and their recommendation selection;
- page count and delivery purpose;
- Mode and custom `mode_behavior`;
- Visual Style and custom `visual_style_behavior`;
- palette roles;
- icon system;
- typography and size fields;
- image usage, image notes, optional AI image path / strategy;
- proactive speaker notes / custom animations / narration;
- generation mode;
- refine-spec choice;
- template application when present;
- `recommendation_sha256`.

### Deck Review

Canonical response: `ppt-master-static-deck-review-response/v1`.

The artifact may provide direct local editing, but must express the result with the existing `changes[]` operations and the exact validator-compatible `svg_roster_sha256`.

### Motion Review

Canonical response: `ppt-master-static-motion-review-response/v1`.

The surface exists only when `static_ui/motion_plan.json` exists. Transition and object effects come from the official animation registry. The artifact must preserve slide IDs, group IDs, duration, keep-object-motion semantics, reason/comment fields, and `plan_sha256`.

## Handoff and authority

Current host flow:

```text
edit → local preview → confirm → captured → 复制并继续 → paste/send → validate → accepted
```

`复制并继续` is a transport convenience only. It does not create a delivered or accepted receipt by itself.

Only `studio/scripts/static_ui_adapter.py validate` may create the accepted receipt.

## Regression rule

Any change to an artifact surface must keep the corresponding parity test green. Where practical, tests pass the artifact-produced canonical response directly into the unmodified official validator.
