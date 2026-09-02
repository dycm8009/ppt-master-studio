# Deck Review Stage

A blocking human review of every final SVG page before export. This stage uses a
self-contained HTML handoff and the real SVG markup; it does not render review
screenshots and does not require Flask, a localhost server, or runtime network.

## Entry gate

- All published pages exist in `<project_path>/svg_output/`.
- The final SVG quality report is current and has zero blocking errors.
- If Speaker Notes are enabled and already generated, they remain coupled to the
  current SVG roster and must be revalidated after any requested page changes.

## 1. Build the review surface

```bash
python3 ${SKILL_DIR}/scripts/deck_review_handoff.py build <project_path>
```

The command writes:

- `<project_path>/live_preview/deck_review.html`
- `<project_path>/live_preview/deck_review_manifest.json`

The HTML is self-contained and embeds sanitized copies of the actual SVG pages.
It requires an explicit decision on every page: **通过** or **需要修改**. A
change request requires a concrete comment. The final action generates one
`ppt-master-static-deck-review-response/v1` JSON object and never auto-closes the
page.

Present `launch_path` through the host's normal user-accessible file transport.
Do not replace it with PNG/JPEG screenshots or a contact sheet.

## 2. Apply the user's copied response

Materialize the copied JSON unchanged, then run:

```bash
python3 ${SKILL_DIR}/scripts/deck_review_handoff.py apply-response <project_path> --response-file <response.json>
```

The pinned Harness validates the exact SVG roster hash and writes:

- `<project_path>/live_preview/deck_review_response.json`
- `<project_path>/live_preview/deck_review_receipt.json`

A response is not authoritative until this command succeeds.

## 3. Blocking outcomes

- `result: approved` / `changes_count: 0` → Deck Review Gate passes; proceed to
  Step 7.
- `result: changes-requested` → return to Executor. Apply only supported user
  changes, rerun the final SVG quality gate, reconcile Speaker Notes when
  enabled, then rebuild this Deck Review surface. Because the SVG roster hash
  changes, the prior receipt cannot approve the revised deck.

Never self-confirm this gate and never infer approval from silence, page visits,
or an empty browser session.
