# Taste and Humanizer Phase 3 evaluation

This package defines the repeatable A/B protocol for the integration plan. It contains no generated decks, source fixtures, or promotion decision.

## 1. Evidence status

| Component | State |
|---|---|
| Variant pins and minimum scenario matrix | Ready in `corpus.json` |
| Blind-review and audit procedure | Ready in `rubric.md` |
| Machine-readable result contract | Ready in `results.schema.json` |
| Real source fixtures | Required outside this package |
| Generated variant artifacts | Pending |
| Independent blind review | Pending |
| Phase 4 promotion | Blocked |

Do not infer effectiveness from the existence of this protocol.

---

## 2. Variant isolation

Materialize each variant from the exact inputs in `corpus.json`.

| Variant | Runtime commit | Explicit workspace |
|---|---|---|
| `baseline` | `50779430c8be0fb6800b7a9c79c10756eae6ab78` | None |
| `naturalness` | `82a440ed271ea7381288cb311f4f0c181d44b269` | None |
| `taste` | `50779430c8be0fb6800b7a9c79c10756eae6ab78` | Copy `skills/ppt-master/experiments/taste-lab-style` from commit `1d50687779f90510d591025c0375a49a322e121a` to an explicit external workspace root |
| `combined` | `82a440ed271ea7381288cb311f4f0c181d44b269` | Use the same copied explicit workspace |

The Taste-only and Combined runs must use an exact external workspace root. Do not register the workspace or let Stage 1 library discovery select it.

---

## 3. Fixture preparation

For every scenario:

1. Prepare one source bundle with a stable SHA-256 digest.
2. Capture one complete Stage 1 and Stage 2 confirmation snapshot and its SHA-256 digest.
3. Fix the model, host, canvas, page-count boundary, image availability, generation mode, and production settings.
4. Run all four variants from clean project roots.
5. Keep generated projects and review files under a local evaluation directory; do not commit source material or deck binaries here.

A scenario is invalid when any variant receives a different source, confirmation value, template candidate, image pool, or production setting.

---

## 4. Run order

Randomize the four run labels per scenario before human review. Keep the label-to-variant map hidden until every reviewer submits scores.

For each variant:

1. Run the pinned Harness and its normal attribution guard.
2. Follow the normal route and confirmation sequence. Reuse the frozen confirmation values; do not let a recommendation difference change the test input.
3. For Taste variants, supply the exact unregistered workspace root.
4. Run normal validation and SVG quality checks.
5. Explicitly activate Visual Review for the evaluation run and retain its findings.
6. Record artifact hashes, factual audit, template audit, token counts when available, and rework count.
7. Export the final PPTX under its blind label.

The evaluation protocol does not bypass a blocking gate or treat a captured recommendation as user confirmation.

---

## 5. Result recording

Create one result document that validates against `results.schema.json`.

Required evidence includes:

- SHA-256 for the source bundle, confirmation snapshot, and final PPTX;
- runtime and explicit-workspace pins;
- attribution, project validation, SVG quality, and Visual Review status;
- protected-content, unsupported-claim, lost-claim, and literal-violation counts;
- template topology and identity regressions when applicable;
- token counts when available and rework count;
- at least two independent blind reviewer score sets;
- a preference rank within each scenario;
- an evidence-complete promotion decision.

A missing artifact, missing reviewer, failed validation, or incomplete scenario keeps `promotion_decision.status` at `blocked`.

---

## 6. Promotion boundary

Phase 4 may start only after all required scenarios are complete and the rubric's zero-regression gates pass. Promote individual rules with evidence, not the upstream skill, the entire pilot Style, or an overall aesthetic preference.
