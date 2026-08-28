# Realtime Deck Review Artifact Spec

## Purpose

Move all high-frequency Deck Review editing into the chat-inline artifact runtime so user edits do not require model turns.

## Data model

The artifact receives immutable source data:

- `slides[]`: `{file, svg}`
- `svg_roster_sha256`

It keeps mutable local state:

- `current_slide`
- `selected_element_id`
- `draft_by_element`
- `changes[]`
- `undo_stack[]`
- `redo_stack[]`
- `capture_status`: `draft | captured`

## Edit loop

1. User selects a slide.
2. Artifact injects that slide SVG into the preview surface.
3. User selects an SVG element by stable `id`.
4. Inspector reads current text and supported attributes from the live SVG DOM.
5. Every inspector edit updates only local draft state and the live SVG DOM immediately.
6. Committing an element edit normalizes it into one change object and coalesces duplicate edits for the same slide/element/property.
7. Undo/redo restores both manifest state and preview DOM.
8. Switching slides preserves local edits and replays them when the slide is shown again.
9. Confirm freezes the manifest and creates the canonical Deck Review response locally.

No model turn is required for steps 1–9.

## Supported first-wave edits

The first implementation should support only transformations that can be previewed deterministically in the SVG DOM:

- text replacement
- `fill`
- `stroke`
- `opacity`
- `transform`
- `x`, `y`, `width`, `height` when the selected element exposes them
- freeform AI annotation (record-only; no local visual mutation)

Do not add arbitrary CSS/JS mutation or image generation to the first wave.

## Canonical capture

Confirm creates exactly:

```json
{
  "schema": "ppt-master-static-deck-review-response/v1",
  "surface": "deck-review",
  "status": "user-confirmed",
  "svg_roster_sha256": "<64-hex>",
  "changes": []
}
```

The artifact may display `Captured · not validated`. It must never display `Accepted`.

## Handoff boundary

Current chat-inline artifact host: no supported artifact → assistant/tool callback.

Therefore `Confirm` currently ends at a frozen local capture. A future bridge implementation must accept only the frozen canonical envelope and transport it unchanged to `static_ui_adapter.py validate`.

The bridge is a transport layer, not an authority layer.

## UX target

The Deck Review artifact should feel like a small inspector rather than a form:

- slide rail on the left on wide layouts; compact slide selector on narrow layouts
- main SVG preview as the primary visual surface
- inspector on the right/below
- selected object clearly outlined
- text/attribute changes visible on every keystroke
- undo / redo / reset available without leaving the artifact
- change count and affected-slide count always visible
- Confirm visually distinct from local editing actions

## Acceptance

A Deck Review artifact passes the realtime-edit PoC when:

1. changing selected text updates the SVG preview before blur/submit;
2. changing a supported attribute updates the same preview immediately;
3. switching slides and returning preserves edits;
4. undo and redo affect both preview and `changes[]` consistently;
5. Confirm freezes a validator-compatible response with the original roster hash;
6. no code path claims that the frozen response has reached ChatGPT or been accepted.
